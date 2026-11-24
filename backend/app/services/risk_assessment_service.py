import uuid
import copy
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import User
from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.risk_assessment import RiskAssessment
from app.models.enums import (
    AuditAction,
    RiskAssessmentStatus,
    RiskAssessmentReviewStatus,
    RiskClassification,
    RiskLevel,
    PriorityLevel,
)
from app.repositories.investigation_repository import investigation_repo, incident_repo
from app.repositories.ai_execution_repository import ai_execution_repo
from app.repositories.incident_extraction_repository import incident_extraction_repo
from app.repositories.risk_assessment_repository import risk_assessment_repo
from app.repositories.approval_audit_repository import audit_repo
from app.services.document_context_service import document_context_service
from app.ai.providers.base import BaseAIProvider
from app.ai.services.ai_service import get_ai_service
from app.ai.graphs.risk_state import RiskAssessmentWorkflowState
from app.ai.graphs.risk_builder import create_risk_assessment_graph
from app.ai.schemas.execution import AIExecutionCreate
from app.core.risk_framework import RiskFramework
from app.schemas.risk_assessment import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    RiskAssessmentReviewPatchRequest,
    RiskAssessmentAcceptRequest,
    RiskAssessmentRejectRequest,
    RiskAssessmentInfoRequest,
    RiskAssessmentReviewViewResponse,
)

logger = logging.getLogger(__name__)


class RiskAssessmentService:
    """
    Orchestration service for AI-assisted Quality Impact and Risk Assessment.
    Complies with 21 CFR Part 11 ALCOA+ standards:
    - AI evaluations are unconfirmed drafts until explicitly reviewed and accepted by authorized QA.
    - Historical assessments are preserved upon new acceptance (superseded), ensuring complete audit traceability.
    - Synchronizes confirmed risk levels and priority to the parent Investigation when authorized QA accepts.
    """

    async def start_risk_assessment(
        self,
        session: AsyncSession,
        user: Optional[User],
        investigation_id: str,
        request: RiskAssessmentRequest,
        provider_override: Optional[BaseAIProvider] = None,
    ) -> RiskAssessment:
        """
        Gathers confirmed incident data and document evidence, runs LangGraph risk evaluation,
        persists unconfirmed structured results, and logs audit events.
        """
        investigation = await investigation_repo.get(session, investigation_id)
        if not investigation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation {investigation_id} not found.",
            )

        # Step 1: Gather Incident Snapshot (Confirmed vs Draft)
        incident = await incident_repo.get_by_investigation(session, investigation_id)
        has_unreviewed_incident_data = False
        incident_snapshot: Dict[str, Any] = {}

        if incident and (incident.api_product_name or incident.incident_description):
            incident_snapshot = {
                "api_product_name": incident.api_product_name,
                "batch_number": incident.batch_number,
                "manufacturing_stage": incident.manufacturing_stage,
                "incident_date": incident.incident_date.isoformat() if incident.incident_date else None,
                "equipment_id": incident.equipment_id,
                "expected_parameter": incident.expected_parameter,
                "actual_parameter": incident.actual_parameter,
                "incident_description": incident.incident_description,
                "immediate_actions": incident.immediate_actions,
                "affected_batches": incident.affected_batches,
                "potential_quality_impact": incident.potential_quality_impact,
                "source": "confirmed_incident_record",
            }
        else:
            # Check latest extraction for draft intake
            extractions = await incident_extraction_repo.get_by_investigation(session, investigation_id, limit=1)
            if extractions and extractions[0].extracted_fields:
                has_unreviewed_incident_data = True
                ef = extractions[0].extracted_fields
                incident_snapshot = {
                    "api_product_name": (ef.get("api_product_name") or {}).get("value"),
                    "batch_number": (ef.get("batch_number") or {}).get("value"),
                    "manufacturing_stage": (ef.get("manufacturing_stage") or {}).get("value"),
                    "incident_date": (ef.get("incident_date") or {}).get("value"),
                    "equipment_id": (ef.get("equipment_id") or {}).get("value"),
                    "expected_parameter": (ef.get("expected_parameter_value") or {}).get("value"),
                    "actual_parameter": (ef.get("actual_parameter_value") or {}).get("value"),
                    "incident_description": (ef.get("incident_description") or {}).get("value")
                    or (ef.get("observed_event") or {}).get("value"),
                    "immediate_actions": (ef.get("immediate_actions") or {}).get("value"),
                    "affected_batches": (ef.get("affected_batches") or {}).get("value"),
                    "potential_quality_impact": (ef.get("potential_quality_impact") or {}).get("value"),
                    "source": "unconfirmed_ai_extraction_draft",
                }

        if not incident_snapshot or not (incident_snapshot.get("api_product_name") or incident_snapshot.get("incident_description")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot run risk assessment: no incident information or intake data found for this investigation.",
            )

        # Step 2: Context Preparation & Document Staging
        compiled_context = ""
        valid_doc_map: Dict[str, str] = {}
        if request.use_documents:
            compiled_context, doc_summaries, analyzable_docs = await document_context_service.prepare_context(
                session=session,
                investigation_id=investigation_id,
            )
            valid_doc_map = {doc.id: doc.original_filename for doc in analyzable_docs}

        # Step 3: Provider selection
        ai_service = get_ai_service()
        provider = provider_override or ai_service.provider

        # Step 4: AIExecution tracking record
        workflow_id = str(uuid.uuid4())
        execution_create = AIExecutionCreate(
            investigation_id=investigation_id,
            workflow_id=workflow_id,
            workflow_type="risk_assessment",
            provider="groq" if provider.__class__.__name__ == "GroqProvider" else "mock",
            model=provider.model,
            prompt_version="1.0.0",
            input_context_summary={
                "has_unreviewed_incident_data": has_unreviewed_incident_data,
                "use_documents": request.use_documents,
                "documents_count": len(valid_doc_map),
            },
        )
        ai_execution = await ai_execution_repo.record_execution_start(session, execution_create)

        # Step 5: Initialize RiskAssessment in DB (PENDING)
        assessment = await risk_assessment_repo.create_assessment_record(
            session=session,
            investigation_id=investigation_id,
            ai_execution_id=ai_execution.id,
            created_by=user.id if user else None,
            framework_version=RiskFramework.VERSION,
            incident_snapshot=incident_snapshot,
        )

        # Step 6: Audit log request
        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=investigation_id,
            action=AuditAction.RISK_ASSESSMENT_REQUESTED,
            entity_type="RiskAssessment",
            entity_id=assessment.id,
            new_values={
                "workflow_id": workflow_id,
                "has_unreviewed_incident_data": has_unreviewed_incident_data,
                "use_documents": request.use_documents,
            },
        )

        # Step 7: Execute LangGraph workflow
        graph = create_risk_assessment_graph(provider)
        initial_state: RiskAssessmentWorkflowState = {
            "assessment_id": assessment.id,
            "workflow_id": workflow_id,
            "investigation_id": investigation_id,
            "user_id": user.id if user else None,
            "framework_version": RiskFramework.VERSION,
            "incident_snapshot": incident_snapshot,
            "has_unreviewed_incident_data": has_unreviewed_incident_data,
            "unreviewed_fields_warning": (
                "Incident information is derived from unconfirmed AI draft extractions."
                if has_unreviewed_incident_data
                else None
            ),
            "document_context": compiled_context,
            "valid_document_map": valid_doc_map,
            "additional_instructions": request.additional_instructions,
            "system_prompt": "",
            "user_prompt": "",
            "errors": [],
            "status": RiskAssessmentStatus.PENDING.value,
        }

        try:
            final_state = await graph.ainvoke(initial_state)
            exec_status = final_state.get("status", RiskAssessmentStatus.COMPLETED.value)
            token_usage = final_state.get("token_usage")
            latency_ms = final_state.get("latency_ms")
            errors = final_state.get("errors", [])
            error_message = "; ".join(errors) if errors else None
        except Exception as e:
            logger.error(f"LangGraph execution exception for risk assessment {assessment.id}: {str(e)}", exc_info=True)
            exec_status = RiskAssessmentStatus.FAILED.value
            token_usage = None
            latency_ms = None
            error_message = f"Orchestration failure: {str(e)}"
            final_state = {}

        # Step 8: Update AIExecution in DB
        await ai_execution_repo.record_execution_completion(
            session=session,
            execution_id=ai_execution.id,
            status=exec_status,
            structured_output={
                "overall_risk": final_state.get("overall_risk", "Undetermined"),
                "severity": final_state.get("severity", "Undetermined"),
                "likelihood": final_state.get("likelihood", "Undetermined"),
                "urgency": final_state.get("urgency_recommendation", "Additional Information Required"),
            },
            error_message=error_message,
            token_usage=token_usage,
            latency_ms=latency_ms,
        )

        # Step 9: Update RiskAssessment in DB
        updated_assessment = await risk_assessment_repo.update_assessment_completion(
            session=session,
            assessment_id=assessment.id,
            quality_impact=final_state.get("quality_impact", {}),
            patient_impact=final_state.get("patient_impact", {}),
            batch_impact=final_state.get("batch_impact", {}),
            process_impact=final_state.get("process_impact", {}),
            equipment_impact=final_state.get("equipment_impact", {}),
            data_integrity_impact=final_state.get("data_integrity_impact", {}),
            severity=final_state.get("severity", "Undetermined"),
            likelihood=final_state.get("likelihood", "Undetermined"),
            detectability=final_state.get("detectability"),
            overall_risk=final_state.get("overall_risk", "Undetermined"),
            risk_rationale=final_state.get("risk_rationale", "No rationale generated"),
            urgency_recommendation=final_state.get("urgency_recommendation", "Additional Information Required"),
            supporting_references=final_state.get("supporting_references", []),
            missing_information=final_state.get("missing_information", []),
            conflicting_evidence=final_state.get("conflicting_evidence", []),
            uncertainty_notes=final_state.get("uncertainty_notes"),
            confidence_score=final_state.get("confidence_score", 0.0),
            status=exec_status,
        )

        # Step 10: Audit log completion
        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=investigation_id,
            action=AuditAction.RISK_ASSESSMENT_COMPLETED,
            entity_type="RiskAssessment",
            entity_id=assessment.id,
            new_values={
                "status": exec_status,
                "overall_risk": final_state.get("overall_risk"),
                "urgency": final_state.get("urgency_recommendation"),
            },
        )

        return updated_assessment or assessment

    async def get_assessment(self, session: AsyncSession, assessment_id: str) -> RiskAssessment:
        """Retrieves single risk assessment by UUID."""
        assessment = await risk_assessment_repo.get(session, assessment_id)
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Risk assessment {assessment_id} not found.",
            )
        return assessment

    async def get_assessments_by_investigation(
        self, session: AsyncSession, investigation_id: str, skip: int = 0, limit: int = 50
    ) -> List[RiskAssessment]:
        """Lists all risk assessments for an investigation ordered newest first."""
        return await risk_assessment_repo.get_by_investigation(session, investigation_id, skip=skip, limit=limit)

    async def get_review_view(
        self, session: AsyncSession, assessment_id: str
    ) -> RiskAssessmentReviewViewResponse:
        """Constructs dedicated review payload for human QA investigator."""
        assessment = await self.get_assessment(session, assessment_id)
        investigation = await investigation_repo.get(session, assessment.investigation_id)

        has_unreviewed = assessment.incident_snapshot.get("source") == "unconfirmed_ai_extraction_draft"

        is_active = (
            assessment.review_status == RiskAssessmentReviewStatus.ACCEPTED.value
            and investigation is not None
            and investigation.risk_level.lower() == assessment.overall_risk.lower()
        )

        return RiskAssessmentReviewViewResponse(
            assessment=RiskAssessmentResponse.model_validate(assessment),
            has_unreviewed_incident_data=has_unreviewed,
            active_in_investigation=is_active,
            matrix_metadata=RiskFramework.get_matrix_metadata(),
        )

    async def update_review(
        self,
        session: AsyncSession,
        user: Optional[User],
        assessment_id: str,
        request: RiskAssessmentReviewPatchRequest,
    ) -> RiskAssessment:
        """Updates QA reviewer notes, decisions, or field overrides."""
        assessment = await self.get_assessment(session, assessment_id)

        old_values = {
            "review_status": assessment.review_status,
            "overall_risk": assessment.overall_risk,
            "severity": assessment.severity,
            "likelihood": assessment.likelihood,
            "reviewer_notes": assessment.reviewer_notes,
        }

        new_status = request.review_decision.value if request.review_decision else assessment.review_status

        updated = await risk_assessment_repo.update_review_status(
            session=session,
            assessment_id=assessment_id,
            review_status=new_status,
            reviewer_notes=request.reviewer_notes,
            reviewed_by=user.id if user else None,
            overall_risk_override=request.overall_risk_override.value if request.overall_risk_override else None,
            severity_override=request.severity_override.value if request.severity_override else None,
            likelihood_override=request.likelihood_override.value if request.likelihood_override else None,
        )

        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=assessment.investigation_id,
            action=AuditAction.RISK_ASSESSMENT_REVIEWED,
            entity_type="RiskAssessment",
            entity_id=assessment_id,
            old_values=old_values,
            new_values={
                "review_status": updated.review_status,
                "overall_risk": updated.overall_risk,
                "reviewer_notes": updated.reviewer_notes,
            },
        )

        return updated

    async def accept_assessment(
        self,
        session: AsyncSession,
        user: Optional[User],
        assessment_id: str,
        request: RiskAssessmentAcceptRequest,
    ) -> RiskAssessment:
        """
        Human QA acceptance of risk assessment.
        Supersedes any previous active assessment for this investigation.
        Optionally synchronizes confirmed risk level and priority to the parent Investigation record.
        """
        assessment = await self.get_assessment(session, assessment_id)

        # Supersede previous accepted assessments for this investigation
        await risk_assessment_repo.supersede_previous_accepted(
            session=session,
            investigation_id=assessment.investigation_id,
            current_assessment_id=assessment.id,
        )

        # Update current to ACCEPTED
        updated = await risk_assessment_repo.update_review_status(
            session=session,
            assessment_id=assessment_id,
            review_status=RiskAssessmentReviewStatus.ACCEPTED.value,
            reviewer_notes=request.reviewer_notes or assessment.reviewer_notes,
            reviewed_by=user.id if user else None,
        )

        # Synchronize risk level and priority to Investigation if requested
        if request.apply_to_investigation:
            investigation = await investigation_repo.get(session, assessment.investigation_id)
            if investigation:
                old_risk = investigation.risk_level
                old_prio = investigation.priority

                # Map RiskClassification to Investigation RiskLevel
                overall_norm = updated.overall_risk.strip().lower()
                if overall_norm == "critical":
                    investigation.risk_level = RiskLevel.CRITICAL.value
                    investigation.priority = PriorityLevel.CRITICAL.value
                elif overall_norm == "high":
                    investigation.risk_level = RiskLevel.MAJOR.value
                    investigation.priority = PriorityLevel.HIGH.value
                elif overall_norm == "medium":
                    investigation.risk_level = RiskLevel.MAJOR.value
                    investigation.priority = PriorityLevel.MEDIUM.value
                elif overall_norm == "low":
                    investigation.risk_level = RiskLevel.MINOR.value
                    investigation.priority = PriorityLevel.LOW.value
                else:
                    investigation.risk_level = RiskLevel.MINOR.value

                investigation.updated_at = datetime.now(timezone.utc)
                session.add(investigation)
                await session.flush()

                # Audit log investigation update
                await audit_repo.record_action(
                    session=session,
                    user_id=user.id if user else None,
                    investigation_id=investigation.id,
                    action=AuditAction.UPDATE,
                    entity_type="Investigation",
                    entity_id=investigation.id,
                    old_values={"risk_level": old_risk, "priority": old_prio},
                    new_values={"risk_level": investigation.risk_level, "priority": investigation.priority},
                )

        # Audit log acceptance
        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=assessment.investigation_id,
            action=AuditAction.RISK_ASSESSMENT_ACCEPTED,
            entity_type="RiskAssessment",
            entity_id=assessment_id,
            new_values={
                "review_status": updated.review_status,
                "overall_risk": updated.overall_risk,
                "applied_to_investigation": request.apply_to_investigation,
            },
        )

        return updated

    async def reject_assessment(
        self,
        session: AsyncSession,
        user: Optional[User],
        assessment_id: str,
        request: RiskAssessmentRejectRequest,
    ) -> RiskAssessment:
        """Marks risk assessment REJECTED. Investigation remains unchanged."""
        assessment = await self.get_assessment(session, assessment_id)

        updated = await risk_assessment_repo.update_review_status(
            session=session,
            assessment_id=assessment_id,
            review_status=RiskAssessmentReviewStatus.REJECTED.value,
            reviewer_notes=request.reason,
            reviewed_by=user.id if user else None,
        )

        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=assessment.investigation_id,
            action=AuditAction.RISK_ASSESSMENT_REJECTED,
            entity_type="RiskAssessment",
            entity_id=assessment_id,
            new_values={
                "review_status": updated.review_status,
                "rejection_reason": request.reason,
            },
        )

        return updated

    async def request_additional_information(
        self,
        session: AsyncSession,
        user: Optional[User],
        assessment_id: str,
        request: RiskAssessmentInfoRequest,
    ) -> RiskAssessment:
        """Transitions assessment to NEEDS_MORE_INFORMATION."""
        assessment = await self.get_assessment(session, assessment_id)

        updated = await risk_assessment_repo.update_review_status(
            session=session,
            assessment_id=assessment_id,
            review_status=RiskAssessmentReviewStatus.NEEDS_MORE_INFORMATION.value,
            reviewer_notes=f"Information Requested: {request.information_requested}",
            reviewed_by=user.id if user else None,
        )

        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=assessment.investigation_id,
            action=AuditAction.RISK_ASSESSMENT_INFO_REQUESTED,
            entity_type="RiskAssessment",
            entity_id=assessment_id,
            new_values={
                "review_status": updated.review_status,
                "information_requested": request.information_requested,
            },
        )

        return updated


risk_assessment_service = RiskAssessmentService()
