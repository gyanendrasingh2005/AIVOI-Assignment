import uuid
import copy
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User
from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.ai_execution import AIExecution
from app.models.incident_extraction import IncidentExtraction
from app.models.enums import (
    AuditAction,
    ExtractionStatus,
    ExtractionReviewStatus,
    FieldExtractionStatus,
    FieldReviewDecision,
)
from app.repositories.investigation_repository import investigation_repo, incident_repo
from app.repositories.ai_execution_repository import ai_execution_repo
from app.repositories.incident_extraction_repository import incident_extraction_repo
from app.repositories.approval_audit_repository import audit_repo
from app.services.document_context_service import document_context_service
from app.ai.providers.base import BaseAIProvider
from app.ai.services.ai_service import get_ai_service
from app.ai.graphs.extraction_state import IncidentExtractionWorkflowState
from app.ai.graphs.extraction_builder import create_incident_extraction_graph
from app.ai.prompts.base import PROMPT_VERSIONS
from app.ai.schemas.execution import AIExecutionCreate
from app.schemas.extraction import (
    IncidentExtractionRequest,
    IncidentExtractionResponse,
    FieldReviewUpdateRequest,
    ExtractionReviewPatchRequest,
    FieldAcceptanceRequest,
    FieldRejectionRequest,
    ExtractionReviewViewResponse,
    ExtractedField,
    MissingInformationItem,
    ConflictingInformationItem,
    DocumentProcessingSummary,
)

logger = logging.getLogger(__name__)


def _parse_datetime_safely(val: Any) -> Optional[datetime]:
    """Safely converts string or date object to timezone-aware UTC datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str):
        val_str = val.strip()
        # Handle ISO format
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(val_str, fmt)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


class IncidentExtractionService:
    """
    Orchestration service for AI-powered document understanding, structured
    incident extraction, human review workflows, and controlled field acceptance.
    Enforces 21 CFR Part 11 ALCOA+ standards:
    - AI extractions are unconfirmed drafts until explicitly accepted by human quality professionals.
    - Confirmed Incident records in the database are never modified by the AI directly.
    - Complete before-and-after audit history is transactionally maintained.
    """

    async def start_incident_extraction(
        self,
        session: AsyncSession,
        user: Optional[User],
        investigation_id: str,
        request: IncidentExtractionRequest,
        provider_override: Optional[BaseAIProvider] = None,
    ) -> IncidentExtraction:
        """
        Retrieves authorized source documents, stages text context, runs LangGraph extraction,
        persists unconfirmed structured results, and logs audit entries.
        """
        investigation = await investigation_repo.get(session, investigation_id)
        if not investigation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation {investigation_id} not found.",
            )

        # Context Preparation & Security Check
        compiled_context, doc_summaries, analyzable_docs = await document_context_service.prepare_context(
            session=session,
            investigation_id=investigation_id,
            document_ids=request.document_ids,
        )

        valid_doc_map = {d.id: d.original_filename for d in analyzable_docs}
        workflow_id = str(uuid.uuid4())
        prompt_version = PROMPT_VERSIONS.get("incident_extraction", "1.0.0")
        provider = provider_override or get_ai_service().get_provider()

        # Step 1: Record AIExecution start
        execution_create = AIExecutionCreate(
            workflow_id=workflow_id,
            workflow_type="incident_extraction",
            investigation_id=investigation_id,
            user_id=user.id if user else None,
            provider="groq" if getattr(provider, "model", "") != "mock-analytical-model" else "mock",
            model=provider.model,
            prompt_version=prompt_version,
            input_context_summary={
                "document_ids": request.document_ids,
                "analyzable_count": len(analyzable_docs),
                "total_requested": len(request.document_ids),
            },
        )
        ai_execution = await ai_execution_repo.record_execution_start(session, execution_create)

        # Step 2: Initialize IncidentExtraction record (PENDING)
        extraction = await incident_extraction_repo.create_extraction_record(
            session=session,
            investigation_id=investigation_id,
            ai_execution_id=ai_execution.id,
            created_by=user.id if user else None,
            source_document_ids=request.document_ids,
            provider=ai_execution.provider,
            model=provider.model,
            prompt_version=prompt_version,
            document_summaries=[s.model_dump() for s in doc_summaries],
        )

        # Step 3: Audit log extraction request
        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=investigation_id,
            action=AuditAction.AI_EXTRACTION_REQUESTED,
            entity_type="IncidentExtraction",
            entity_id=extraction.id,
            new_values={
                "workflow_id": workflow_id,
                "document_ids": request.document_ids,
                "extraction_instructions": request.extraction_instructions,
            },
        )

        # Step 4: Compile and execute LangGraph workflow
        graph = create_incident_extraction_graph(provider)
        initial_state: IncidentExtractionWorkflowState = {
            "extraction_id": extraction.id,
            "workflow_id": workflow_id,
            "investigation_id": investigation_id,
            "user_id": user.id if user else None,
            "document_ids": request.document_ids,
            "extraction_instructions": request.extraction_instructions,
            "prompt_version": prompt_version,
            "document_context": compiled_context,
            "document_summaries": [s.model_dump() for s in doc_summaries],
            "valid_document_map": valid_doc_map,
            "system_prompt": "",
            "user_prompt": "",
            "errors": [],
            "status": ExtractionStatus.PENDING.value,
        }

        try:
            final_state = await graph.ainvoke(initial_state)
            exec_status = final_state.get("status", ExtractionStatus.COMPLETED.value)
            extracted_fields = final_state.get("extracted_fields", {})
            missing_info = final_state.get("missing_information", [])
            conflicting_info = final_state.get("conflicting_information", [])
            token_usage = final_state.get("token_usage")
            latency_ms = final_state.get("latency_ms")
            errors = final_state.get("errors", [])
            error_message = "; ".join(errors) if errors else None
        except Exception as e:
            logger.error(f"LangGraph execution exception for extraction {extraction.id}: {str(e)}")
            exec_status = ExtractionStatus.FAILED.value
            extracted_fields = {}
            missing_info = []
            conflicting_info = []
            token_usage = None
            latency_ms = None
            error_message = f"Orchestration failure: {str(e)}"

        # Step 5: Update AIExecution in DB
        await ai_execution_repo.record_execution_completion(
            session=session,
            execution_id=ai_execution.id,
            status=exec_status,
            structured_output={
                "fields_count": len(extracted_fields),
                "missing_count": len(missing_info),
                "conflicts_count": len(conflicting_info),
            },
            error_message=error_message,
            token_usage=token_usage,
            latency_ms=latency_ms,
        )

        # Step 6: Update IncidentExtraction in DB
        updated_extraction = await incident_extraction_repo.update_extraction_completion(
            session=session,
            extraction_id=extraction.id,
            status=exec_status,
            extracted_fields=extracted_fields,
            missing_information=missing_info,
            conflicting_information=conflicting_info,
            document_summaries=[s.model_dump() for s in doc_summaries],
        )

        # Step 7: Audit log completion
        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=investigation_id,
            action=AuditAction.AI_EXTRACTION_COMPLETED,
            entity_type="IncidentExtraction",
            entity_id=extraction.id,
            new_values={
                "status": exec_status,
                "fields_extracted": len(extracted_fields),
                "missing_identified": len(missing_info),
                "conflicts_identified": len(conflicting_info),
                "latency_ms": latency_ms,
            },
        )

        return updated_extraction or extraction

    async def get_extraction_review_view(
        self,
        session: AsyncSession,
        user: User,
        extraction_id: str,
    ) -> ExtractionReviewViewResponse:
        """Constructs human-review representation with original suggestions vs edits."""
        extraction = await incident_extraction_repo.get(session, extraction_id)
        if not extraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident extraction {extraction_id} not found.",
            )

        fields_list: List[ExtractedField] = []
        for f_name, f_dict in (extraction.extracted_fields or {}).items():
            try:
                fields_list.append(ExtractedField.model_validate(f_dict))
            except Exception as e:
                logger.warning(f"Failed to parse field '{f_name}': {str(e)}")

        missing_list = [MissingInformationItem.model_validate(m) for m in (extraction.missing_information or [])]
        conflict_list = [ConflictingInformationItem.model_validate(c) for c in (extraction.conflicting_information or [])]
        doc_summaries = [DocumentProcessingSummary.model_validate(d) for d in (extraction.document_summaries or [])]

        return ExtractionReviewViewResponse(
            extraction_id=extraction.id,
            investigation_id=extraction.investigation_id,
            status=extraction.status,
            review_status=extraction.review_status,
            fields=fields_list,
            missing_information=missing_list,
            conflicting_information=conflict_list,
            document_summaries=doc_summaries,
        )

    async def update_review_decisions(
        self,
        session: AsyncSession,
        user: User,
        extraction_id: str,
        patch_req: ExtractionReviewPatchRequest,
    ) -> IncidentExtraction:
        """
        Updates human review decisions (accept/reject/edit) for extracted fields.
        Does NOT touch the confirmed Incident record until formal acceptance is triggered.
        """
        extraction = await incident_extraction_repo.get(session, extraction_id)
        if not extraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident extraction {extraction_id} not found.",
            )

        current_fields: Dict[str, Any] = copy.deepcopy(extraction.extracted_fields or {})
        now_iso = datetime.now(timezone.utc).isoformat()

        for item in patch_req.fields:
            key = item.field_name.strip().lower()
            field_entry = current_fields.get(key, {
                "field_name": key,
                "value": None,
                "confidence": 0.0,
                "source_references": [],
                "status": FieldExtractionStatus.NOT_FOUND.value,
            })

            # Check if human changed the suggested value
            original_val = field_entry.get("value")
            reviewed_val = item.reviewed_value if item.reviewed_value is not None else original_val
            is_mod = (reviewed_val != original_val) and (item.reviewed_value is not None)

            field_entry["reviewed_value"] = reviewed_val
            field_entry["review_decision"] = item.review_decision.value
            field_entry["reviewed_by"] = user.id
            field_entry["reviewed_at"] = now_iso
            field_entry["is_modified"] = is_mod

            current_fields[key] = field_entry

        # Compute updated overall review_status
        decisions = [f.get("review_decision") for f in current_fields.values()]
        if all(d == FieldReviewDecision.ACCEPTED.value for d in decisions) and decisions:
            new_review_status = ExtractionReviewStatus.ACCEPTED.value
        elif any(d == FieldReviewDecision.ACCEPTED.value for d in decisions):
            new_review_status = ExtractionReviewStatus.PARTIALLY_ACCEPTED.value
        elif all(d == FieldReviewDecision.REJECTED.value for d in decisions) and decisions:
            new_review_status = ExtractionReviewStatus.REJECTED.value
        else:
            new_review_status = ExtractionReviewStatus.PENDING_REVIEW.value

        updated = await incident_extraction_repo.save_review_state(
            session=session,
            extraction_id=extraction.id,
            review_status=new_review_status,
            extracted_fields=current_fields,
            reviewed_by=user.id,
        )

        # Audit review update
        await audit_repo.record_action(
            session=session,
            user_id=user.id,
            investigation_id=extraction.investigation_id,
            action=AuditAction.AI_EXTRACTION_REVIEWED,
            entity_type="IncidentExtraction",
            entity_id=extraction.id,
            new_values={
                "review_status": new_review_status,
                "reviewed_fields": [f.field_name for f in patch_req.fields],
            },
        )

        return updated or extraction

    async def accept_incident_fields(
        self,
        session: AsyncSession,
        user: User,
        extraction_id: str,
        accept_req: FieldAcceptanceRequest,
    ) -> Tuple[IncidentExtraction, Incident]:
        """
        Accepts selected reviewed fields and applies ONLY authorized, validated changes
        to the confirmed Incident record in the database.
        Maintains 21 CFR Part 11 ALCOA+ audit history for every accepted attribute.
        """
        extraction = await incident_extraction_repo.get(session, extraction_id)
        if not extraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident extraction {extraction_id} not found.",
            )

        investigation = await investigation_repo.get(session, extraction.investigation_id)
        if not investigation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation {extraction.investigation_id} not found.",
            )

        incident = await incident_repo.get_by_investigation(session, investigation.id)
        if not incident:
            # If incident row was somehow missing, create one
            incident = Incident(
                investigation_id=investigation.id,
                api_product_name="Unknown API",
                batch_number="PENDING-BATCH",
                manufacturing_stage="Unknown Stage",
                incident_date=datetime.now(timezone.utc),
                incident_description="Pending extraction confirmation",
            )
            session.add(incident)
            await session.flush()
            await session.refresh(incident)

        current_fields: Dict[str, Any] = copy.deepcopy(extraction.extracted_fields or {})
        target_keys = set(accept_req.field_names) if accept_req.field_names else set(current_fields.keys())
        now_iso = datetime.now(timezone.utc).isoformat()
        accepted_any = False

        for key, field_data in current_fields.items():
            if key not in target_keys:
                continue

            # Resolve effective value (reviewed_value takes precedence over original suggestion)
            eff_val = field_data.get("reviewed_value")
            if eff_val is None:
                eff_val = field_data.get("value")

            if eff_val is None:
                # Do not overwrite confirmed incident data with null
                continue

            old_incident_val = None
            applied = False

            # Map to Incident entity columns
            if key == "api_product_name":
                old_incident_val = incident.api_product_name
                incident.api_product_name = str(eff_val)[:150]
                applied = True
            elif key == "batch_number":
                old_incident_val = incident.batch_number
                incident.batch_number = str(eff_val)[:50]
                applied = True
            elif key == "manufacturing_stage":
                old_incident_val = incident.manufacturing_stage
                incident.manufacturing_stage = str(eff_val)[:100]
                applied = True
            elif key == "incident_date":
                old_incident_val = incident.incident_date.isoformat() if incident.incident_date else None
                parsed_dt = _parse_datetime_safely(eff_val)
                if parsed_dt:
                    incident.incident_date = parsed_dt
                    applied = True
            elif key in ("incident_description", "observed_event"):
                old_incident_val = incident.incident_description
                incident.incident_description = str(eff_val)
                applied = True
            elif key == "equipment_id":
                old_incident_val = incident.equipment_id
                incident.equipment_id = str(eff_val)[:50]
                applied = True
            elif key in ("actual_parameter_value", "actual_condition"):
                old_incident_val = incident.actual_parameter
                incident.actual_parameter = str(eff_val)[:255]
                applied = True
            elif key in ("expected_parameter_value", "expected_condition"):
                old_incident_val = incident.expected_parameter
                incident.expected_parameter = str(eff_val)[:255]
                applied = True
            elif key == "immediate_actions":
                old_incident_val = incident.immediate_actions
                incident.immediate_actions = str(eff_val)
                applied = True
            elif key == "affected_batches":
                old_incident_val = incident.affected_batches
                incident.affected_batches = eff_val if isinstance(eff_val, list) else [str(eff_val)]
                applied = True
            elif key == "potential_quality_impact":
                old_incident_val = incident.potential_quality_impact
                incident.potential_quality_impact = str(eff_val)
                applied = True
            elif key == "incident_title":
                old_incident_val = investigation.title
                investigation.title = str(eff_val)[:255]
                applied = True

            if applied:
                accepted_any = True
                field_data["review_decision"] = FieldReviewDecision.ACCEPTED.value
                field_data["reviewed_by"] = user.id
                field_data["reviewed_at"] = now_iso

                # ALCOA+ Audit Log for specific accepted attribute
                await audit_repo.record_action(
                    session=session,
                    user_id=user.id,
                    investigation_id=investigation.id,
                    action=AuditAction.AI_FIELD_ACCEPTED,
                    entity_type="Incident",
                    entity_id=incident.id,
                    old_values={"field": key, "value": old_incident_val},
                    new_values={
                        "field": key,
                        "value": eff_val,
                        "original_ai_suggestion": field_data.get("value"),
                        "was_edited_by_human": field_data.get("is_modified", False),
                        "source_references": field_data.get("source_references", []),
                    },
                )

        if accepted_any:
            session.add(incident)
            session.add(investigation)
            await session.flush()
            await session.refresh(incident)

        # Update extraction status
        new_review_status = (
            ExtractionReviewStatus.ACCEPTED.value if len(target_keys) >= len(current_fields)
            else ExtractionReviewStatus.PARTIALLY_ACCEPTED.value
        )
        updated_extraction = await incident_extraction_repo.save_review_state(
            session=session,
            extraction_id=extraction.id,
            review_status=new_review_status,
            extracted_fields=current_fields,
            reviewed_by=user.id,
        )

        return (updated_extraction or extraction, incident)

    async def reject_incident_extraction(
        self,
        session: AsyncSession,
        user: User,
        extraction_id: str,
        reject_req: FieldRejectionRequest,
    ) -> IncidentExtraction:
        """
        Rejects specific fields or the entire extraction result.
        Does NOT alter confirmed Incident records in any way.
        """
        extraction = await incident_extraction_repo.get(session, extraction_id)
        if not extraction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident extraction {extraction_id} not found.",
            )

        current_fields: Dict[str, Any] = copy.deepcopy(extraction.extracted_fields or {})
        now_iso = datetime.now(timezone.utc).isoformat()

        if reject_req.field_names:
            # Reject specific fields
            for key in reject_req.field_names:
                k = key.strip().lower()
                if k in current_fields:
                    current_fields[k]["review_decision"] = FieldReviewDecision.REJECTED.value
                    current_fields[k]["reviewed_by"] = user.id
                    current_fields[k]["reviewed_at"] = now_iso
            new_review_status = ExtractionReviewStatus.PARTIALLY_ACCEPTED.value
            audit_action = AuditAction.AI_FIELD_REJECTED
        else:
            # Reject complete extraction
            for f_data in current_fields.values():
                f_data["review_decision"] = FieldReviewDecision.REJECTED.value
                f_data["reviewed_by"] = user.id
                f_data["reviewed_at"] = now_iso
            new_review_status = ExtractionReviewStatus.REJECTED.value
            audit_action = AuditAction.AI_EXTRACTION_REJECTED

        updated = await incident_extraction_repo.save_review_state(
            session=session,
            extraction_id=extraction.id,
            review_status=new_review_status,
            extracted_fields=current_fields,
            reviewed_by=user.id,
        )

        await audit_repo.record_action(
            session=session,
            user_id=user.id,
            investigation_id=extraction.investigation_id,
            action=audit_action,
            entity_type="IncidentExtraction",
            entity_id=extraction.id,
            new_values={
                "review_status": new_review_status,
                "rejected_fields": reject_req.field_names or "ALL",
                "reason": reject_req.reason,
            },
        )

        return updated or extraction


incident_extraction_service = IncidentExtractionService()
