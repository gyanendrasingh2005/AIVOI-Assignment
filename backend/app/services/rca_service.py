"""
Orchestration service for AI-assisted Root Cause Analysis (5 Whys + Fishbone/Ishikawa).
Complies with 21 CFR Part 11 ALCOA+ standards:
- AI-generated causes are strictly draft hypotheses until verified and accepted by an authorized human investigator.
- Historical RCA runs are preserved upon new acceptance (superseded), ensuring complete audit traceability.
- Provides discrete cause-level verification, rejection, editing, and manual cause insertion.
"""

import uuid
import copy
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified
from fastapi import HTTPException, status

from app.models.user import User
from app.models.investigation import Investigation
from app.models.rca import RCAAnalysis
from app.models.enums import (
    AuditAction,
    RCAStatus,
    CauseStatus,
    CauseClassification,
    Fishbone6MCategory,
)
from app.repositories.investigation_repository import investigation_repo
from app.repositories.rca_repository import rca_repo
from app.repositories.approval_audit_repository import audit_repo
from app.repositories.ai_execution_repository import ai_execution_repo
from app.services.rca_context_service import rca_context_service
from app.ai.providers.base import BaseAIProvider
import app.ai.services.ai_service as ai_service_mod
from app.ai.graphs.rca_state import RCAWorkflowState
from app.ai.graphs.rca_builder import create_rca_graph
from app.ai.schemas.execution import AIExecutionCreate
from app.schemas.rca import (
    RCARequest,
    RCAResponse,
    RCAReviewViewResponse,
    RCAReviewPatchRequest,
    ManualCauseCreateRequest,
    CausePatchRequest,
    CauseVerifyRequest,
    CauseRejectRequest,
    RCAAcceptRequest,
    RCAEvidenceRequest,
)

logger = logging.getLogger(__name__)


class RCAService:
    """
    Service coordinating the generation, retrieval, review, and lifecycle
    of Root Cause Analysis (5 Whys and Fishbone) records.
    """

    async def start_rca(
        self,
        session: AsyncSession,
        user: Optional[User],
        investigation_id: str,
        request: RCARequest,
        provider_override: Optional[BaseAIProvider] = None,
    ) -> RCAAnalysis:
        """
        Gathers confirmed incident data and document evidence, runs LangGraph RCA evaluation,
        persists unconfirmed structured results, and logs audit events.
        """
        investigation = await investigation_repo.get(session, investigation_id)
        if not investigation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation {investigation_id} not found.",
            )

        # Step 1: Prepare context
        context = await rca_context_service.prepare_rca_context(
            session=session,
            investigation_id=investigation_id,
            use_documents=request.use_documents,
        )

        incident_snapshot = context.get("incident_snapshot", {})
        if not incident_snapshot or not (
            incident_snapshot.get("api_product_name")
            or incident_snapshot.get("incident_description")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot run Root Cause Analysis: no incident details or intake data found for this investigation.",
            )

        latest_version = await rca_repo.get_latest_version_number(
            session, investigation_id
        )
        new_version = latest_version + 1

        # Step 2: Initialize AI Execution record
        execution = await ai_execution_repo.create_execution(
            session=session,
            obj_in=AIExecutionCreate(
                investigation_id=investigation_id,
                workflow_type="rca",
                model_name="llama-3.3-70b-versatile",
                prompt_version="1.0.0",
                user_id=user.id if user else None,
                system_prompt="",
                user_prompt="",
            ),
        )

        # Step 3: Initialize RCAAnalysis record in DRAFT
        method_str = (
            request.analysis_method.value
            if hasattr(request.analysis_method, "value")
            else str(request.analysis_method)
        )
        rca = await rca_repo.create_rca_record(
            session=session,
            investigation_id=investigation_id,
            ai_execution_id=execution.id,
            created_by=user.id if user else None,
            analysis_method=method_str,
            analysis_version=new_version,
            prompt_version="1.0.0",
            problem_statement=incident_snapshot.get("incident_description"),
        )

        # Audit log: RCA_REQUESTED
        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=investigation_id,
            action=AuditAction.RCA_REQUESTED.value,
            details={
                "rca_id": rca.id,
                "analysis_version": new_version,
                "method": rca.analysis_method,
                "use_documents": request.use_documents,
                "ai_execution_id": execution.id,
            },
        )

        # Step 4: Provider Selection
        if provider_override:
            provider = provider_override
        else:
            ai_svc = ai_service_mod.get_ai_service()
            provider = ai_svc.provider

        # Step 5: Execute LangGraph Workflow
        graph = create_rca_graph(provider)
        initial_state: RCAWorkflowState = {
            "rca_id": rca.id,
            "workflow_id": execution.id,
            "investigation_id": investigation_id,
            "user_id": user.id if user else None,
            "analysis_method": rca.analysis_method,
            "prompt_version": "1.0.0",
            "incident_snapshot": context["incident_snapshot"],
            "has_unreviewed_incident_data": context["has_unreviewed_incident_data"],
            "risk_summary": context["risk_summary"],
            "evidence_list": context["evidence_list"],
            "valid_document_map": context["valid_document_map"],
            "valid_evidence_map": context["valid_evidence_map"],
            "compiled_prompt_context": context["context_text"],
            "additional_focus": request.additional_focus,
            "token_usage": {},
            "latency_ms": 0,
            "five_whys": [],
            "fishbone_causes": [],
            "potential_root_causes": [],
            "contributing_factors": [],
            "rejected_hypotheses": [],
            "evidence_gaps": [],
            "unsupported_assumptions": [],
            "status": "PROCESSING",
            "errors": [],
        }

        result_state = await graph.ainvoke(initial_state)

        # Step 6: Group fishbone causes by 6M category
        fishbone_dict: Dict[str, List[Dict[str, Any]]] = {
            Fishbone6MCategory.MANPOWER.value: [],
            Fishbone6MCategory.MACHINE.value: [],
            Fishbone6MCategory.METHOD.value: [],
            Fishbone6MCategory.MATERIAL.value: [],
            Fishbone6MCategory.MEASUREMENT.value: [],
            Fishbone6MCategory.ENVIRONMENT.value: [],
        }
        for c in result_state.get("fishbone_causes", []):
            cat = c.get("category", Fishbone6MCategory.METHOD.value)
            if cat not in fishbone_dict:
                fishbone_dict[cat] = []
            fishbone_dict[cat].append(c)

        # Step 7: Update RCAAnalysis record
        final_status = (
            RCAStatus.AI_ANALYSIS_COMPLETED.value
            if result_state.get("status") != "FAILED"
            else RCAStatus.DRAFT.value
        )
        updated_rca = await rca_repo.update_rca_completion(
            session=session,
            rca_id=rca.id,
            problem_statement=result_state.get("problem_statement")
            or rca.problem_statement
            or "Investigated deviation event.",
            incident_summary=result_state.get("incident_summary") or "",
            five_whys_data=result_state.get("five_whys", []),
            fishbone_data=fishbone_dict,
            root_causes_data=result_state.get("potential_root_causes", []),
            contributing_factors_data=result_state.get("contributing_factors", []),
            rejected_hypotheses_data=result_state.get("rejected_hypotheses", []),
            evidence_gaps_data=result_state.get("evidence_gaps", []),
            summary=result_state.get("causal_chain_critique"),
            status=final_status,
        )

        # Step 8: Sync child relational entities
        await rca_repo.sync_relational_child_records(session, updated_rca)

        # Step 9: Complete AI Execution Record
        token_usage = result_state.get("token_usage", {})
        await ai_execution_repo.complete_execution(
            session=session,
            execution_id=execution.id,
            structured_output={
                "problem_statement": updated_rca.problem_statement,
                "incident_summary": updated_rca.incident_summary,
                "five_whys": updated_rca.five_whys_data,
                "fishbone_causes": result_state.get("fishbone_causes", []),
                "potential_root_causes": updated_rca.root_causes_data,
                "contributing_factors": updated_rca.contributing_factors_data,
                "rejected_hypotheses": updated_rca.rejected_hypotheses_data,
                "evidence_gaps": updated_rca.evidence_gaps_data,
                "unsupported_assumptions": result_state.get(
                    "unsupported_assumptions", []
                ),
            },
            prompt_tokens=token_usage.get("prompt_tokens", 0),
            completion_tokens=token_usage.get("completion_tokens", 0),
            total_tokens=token_usage.get("total_tokens", 0),
            latency_ms=result_state.get("latency_ms", 0),
        )

        # Step 10: Audit log: RCA_GENERATED
        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=investigation_id,
            action=AuditAction.RCA_GENERATED.value,
            details={
                "rca_id": rca.id,
                "version": new_version,
                "status": updated_rca.status,
                "five_whys_steps": len(updated_rca.five_whys_data),
                "root_causes_count": len(updated_rca.root_causes_data),
                "contributing_factors_count": len(
                    updated_rca.contributing_factors_data
                ),
                "evidence_gaps_count": len(updated_rca.evidence_gaps_data),
                "ai_execution_id": execution.id,
            },
        )

        return updated_rca

    async def get_rca(self, session: AsyncSession, rca_id: str) -> RCAAnalysis:
        """Retrieves RCA record or raises 404."""
        rca = await rca_repo.get(session, rca_id)
        if not rca:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Root Cause Analysis {rca_id} not found.",
            )
        return rca

    async def get_rcas_by_investigation(
        self,
        session: AsyncSession,
        investigation_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[RCAAnalysis]:
        """Lists all RCA records for an investigation ordered by newest version first."""
        return await rca_repo.get_by_investigation(
            session, investigation_id, skip=skip, limit=limit
        )

    async def get_five_whys(
        self, session: AsyncSession, rca_id: str
    ) -> List[Dict[str, Any]]:
        """Retrieves structured 5 Whys steps for an RCA analysis."""
        rca = await self.get_rca(session, rca_id)
        return rca.five_whys_data or []

    async def get_fishbone(
        self, session: AsyncSession, rca_id: str
    ) -> Dict[str, Any]:
        """Retrieves 6M Fishbone tree for an RCA analysis."""
        rca = await self.get_rca(session, rca_id)
        return rca.fishbone_data or {}

    async def get_review_view(
        self, session: AsyncSession, rca_id: str
    ) -> RCAReviewViewResponse:
        """Assembles comprehensive review payload for human QA."""
        rca = await self.get_rca(session, rca_id)
        context = await rca_context_service.prepare_rca_context(
            session=session,
            investigation_id=rca.investigation_id,
            use_documents=False,
        )
        return RCAReviewViewResponse(
            rca=RCAResponse.model_validate(rca),
            incident_snapshot=context.get("incident_snapshot", {}),
            five_whys=rca.five_whys_data or [],
            fishbone_categories=rca.fishbone_data or {},
            root_causes=rca.root_causes_data or [],
            contributing_factors=rca.contributing_factors_data or [],
            evidence_gaps=rca.evidence_gaps_data or [],
            unsupported_assumptions=[],
        )

    async def update_review(
        self,
        session: AsyncSession,
        user: Optional[User],
        rca_id: str,
        request: RCAReviewPatchRequest,
    ) -> RCAAnalysis:
        """Applies reviewer edits or status update to RCA."""
        rca = await self.get_rca(session, rca_id)

        if request.summary is not None:
            rca.summary = request.summary
        if request.problem_statement is not None:
            rca.problem_statement = request.problem_statement
        if request.reviewer_notes is not None:
            rca.reviewer_notes = request.reviewer_notes
        if request.review_status is not None:
            rca.status = (
                request.review_status.value
                if hasattr(request.review_status, "value")
                else str(request.review_status)
            )
        if request.five_whys_override is not None:
            rca.five_whys_data = copy.deepcopy(request.five_whys_override)
            flag_modified(rca, "five_whys_data")
        if request.fishbone_override is not None:
            rca.fishbone_data = copy.deepcopy(request.fishbone_override)
            flag_modified(rca, "fishbone_data")

        rca.updated_at = datetime.now(timezone.utc)
        if user:
            rca.reviewed_by = user.id
            rca.reviewed_at = datetime.now(timezone.utc)

        session.add(rca)
        await session.flush()
        await session.refresh(rca)
        await rca_repo.sync_relational_child_records(session, rca)

        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=rca.investigation_id,
            action=AuditAction.RCA_REVIEWED.value,
            details={
                "rca_id": rca.id,
                "status": rca.status,
                "notes_updated": request.reviewer_notes is not None,
            },
        )
        return rca

    async def add_manual_cause(
        self,
        session: AsyncSession,
        user: Optional[User],
        rca_id: str,
        request: ManualCauseCreateRequest,
    ) -> Dict[str, Any]:
        """Manually adds an investigator-proposed cause to fishbone and cause lists."""
        rca = await self.get_rca(session, rca_id)

        cause_id = f"mc-{uuid.uuid4().hex[:8]}"
        category_name = request.category
        classification_val = (
            request.classification.value
            if hasattr(request.classification, "value")
            else str(request.classification)
        )

        new_cause: Dict[str, Any] = {
            "cause_id": cause_id,
            "category": category_name,
            "title": request.title,
            "description": request.description,
            "classification": classification_val,
            "status": CauseStatus.PROPOSED.value,
            "confidence": 1.0,
            "is_manual": True,
            "created_by": user.id if user else None,
            "supporting_references": [
                r.model_dump() for r in request.supporting_references
            ],
            "verification_status": CauseStatus.PROPOSED.value,
            "human_confirmed": False,
        }

        # Add to fishbone category
        fishbone = copy.deepcopy(rca.fishbone_data or {})
        if category_name not in fishbone:
            fishbone[category_name] = []
        fishbone[category_name].append(new_cause)
        rca.fishbone_data = fishbone
        flag_modified(rca, "fishbone_data")

        # Add to root_causes_data or contributing_factors_data if classified as such
        if classification_val == CauseClassification.ROOT_CAUSE.value:
            root_causes = copy.deepcopy(rca.root_causes_data or [])
            root_causes.append(new_cause)
            rca.root_causes_data = root_causes
            flag_modified(rca, "root_causes_data")
        elif classification_val == CauseClassification.CONTRIBUTING_FACTOR.value:
            contrib = copy.deepcopy(rca.contributing_factors_data or [])
            contrib.append(new_cause)
            rca.contributing_factors_data = contrib
            flag_modified(rca, "contributing_factors_data")

        rca.updated_at = datetime.now(timezone.utc)
        session.add(rca)
        await session.flush()
        await session.refresh(rca)
        await rca_repo.sync_relational_child_records(session, rca)

        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=rca.investigation_id,
            action=AuditAction.RCA_CAUSE_ADDED.value,
            details={
                "rca_id": rca.id,
                "cause_id": cause_id,
                "category": category_name,
                "classification": classification_val,
                "title": request.title,
            },
        )
        return new_cause

    async def update_cause(
        self,
        session: AsyncSession,
        user: Optional[User],
        rca_id: str,
        cause_id: str,
        request: CausePatchRequest,
    ) -> Dict[str, Any]:
        """Modifies title, description, category, or notes of an existing cause."""
        rca = await self.get_rca(session, rca_id)

        target_cause: Optional[Dict[str, Any]] = None

        # Search and update in fishbone_data
        fishbone = copy.deepcopy(rca.fishbone_data or {})
        for cat_name, causes in fishbone.items():
            for c in causes:
                if c.get("cause_id") == cause_id:
                    target_cause = c
                    break
            if target_cause:
                break

        # Search root_causes_data
        root_causes = copy.deepcopy(rca.root_causes_data or [])
        rc_target = next(
            (c for c in root_causes if c.get("cause_id") == cause_id), None
        )
        if rc_target:
            target_cause = target_cause or rc_target

        # Search contributing_factors_data
        contrib = copy.deepcopy(rca.contributing_factors_data or [])
        cf_target = next(
            (c for c in contrib if c.get("cause_id") == cause_id), None
        )
        if cf_target:
            target_cause = target_cause or cf_target

        if not target_cause:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cause {cause_id} not found in Root Cause Analysis {rca_id}.",
            )

        # Apply updates
        if request.title is not None:
            target_cause["title"] = request.title
            if rc_target:
                rc_target["title"] = request.title
        if request.description is not None:
            target_cause["description"] = request.description
            if rc_target:
                rc_target["description"] = request.description
            if cf_target:
                cf_target["description"] = request.description
        if request.category is not None:
            target_cause["category"] = request.category
        if request.classification is not None:
            target_cause["classification"] = (
                request.classification.value
                if hasattr(request.classification, "value")
                else str(request.classification)
            )
        if request.verification_status is not None:
            status_val = (
                request.verification_status.value
                if hasattr(request.verification_status, "value")
                else str(request.verification_status)
            )
            target_cause["verification_status"] = status_val
            target_cause["status"] = status_val
        if request.potential_impact is not None:
            target_cause["potential_impact"] = request.potential_impact
        if request.rejection_reason is not None:
            target_cause["rejection_reason"] = request.rejection_reason

        rca.fishbone_data = fishbone
        rca.root_causes_data = root_causes
        rca.contributing_factors_data = contrib
        flag_modified(rca, "fishbone_data")
        flag_modified(rca, "root_causes_data")
        flag_modified(rca, "contributing_factors_data")

        rca.updated_at = datetime.now(timezone.utc)
        session.add(rca)
        await session.flush()
        await session.refresh(rca)
        await rca_repo.sync_relational_child_records(session, rca)

        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=rca.investigation_id,
            action=AuditAction.RCA_CAUSE_EDITED.value,
            details={
                "rca_id": rca.id,
                "cause_id": cause_id,
                "updated_fields": [k for k, v in request.model_dump(exclude_unset=True).items()],
            },
        )
        return target_cause

    async def verify_cause(
        self,
        session: AsyncSession,
        user: Optional[User],
        rca_id: str,
        cause_id: str,
        request: CauseVerifyRequest,
    ) -> Dict[str, Any]:
        """Verifies a cause node as validated by investigator evidence."""
        rca = await self.get_rca(session, rca_id)

        target_cause: Optional[Dict[str, Any]] = None

        fishbone = copy.deepcopy(rca.fishbone_data or {})
        for cat_name, causes in fishbone.items():
            for c in causes:
                if c.get("cause_id") == cause_id:
                    target_cause = c
                    break
            if target_cause:
                break

        root_causes = copy.deepcopy(rca.root_causes_data or [])
        rc_target = next(
            (c for c in root_causes if c.get("cause_id") == cause_id), None
        )
        target_cause = target_cause or rc_target

        contrib = copy.deepcopy(rca.contributing_factors_data or [])
        cf_target = next(
            (c for c in contrib if c.get("cause_id") == cause_id), None
        )
        target_cause = target_cause or cf_target

        if not target_cause:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cause {cause_id} not found in Root Cause Analysis {rca_id}.",
            )

        now_str = datetime.now(timezone.utc).isoformat()
        target_cause["status"] = CauseStatus.VERIFIED.value
        target_cause["verification_status"] = CauseStatus.VERIFIED.value
        target_cause["human_confirmed"] = True
        target_cause["verified_by"] = user.id if user else None
        target_cause["verified_at"] = now_str
        target_cause["verification_notes"] = request.verification_notes

        if rc_target:
            rc_target["human_confirmed"] = True
            rc_target["verification_status"] = CauseStatus.VERIFIED.value
            rc_target["status"] = CauseStatus.VERIFIED.value
            rc_target["verification_notes"] = request.verification_notes

        if request.is_root_cause and not rc_target:
            target_cause["classification"] = CauseClassification.ROOT_CAUSE.value
            root_causes.append(target_cause)

        rca.fishbone_data = fishbone
        rca.root_causes_data = root_causes
        rca.contributing_factors_data = contrib
        flag_modified(rca, "fishbone_data")
        flag_modified(rca, "root_causes_data")
        flag_modified(rca, "contributing_factors_data")

        rca.updated_at = datetime.now(timezone.utc)
        session.add(rca)
        await session.flush()
        await session.refresh(rca)
        await rca_repo.sync_relational_child_records(session, rca)

        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=rca.investigation_id,
            action=AuditAction.RCA_CAUSE_VERIFIED.value,
            details={
                "rca_id": rca.id,
                "cause_id": cause_id,
                "is_root_cause": request.is_root_cause,
                "verification_notes": request.verification_notes,
            },
        )
        return target_cause

    async def reject_cause(
        self,
        session: AsyncSession,
        user: Optional[User],
        rca_id: str,
        cause_id: str,
        request: CauseRejectRequest,
    ) -> Dict[str, Any]:
        """Formally rules out a hypothesis with documented evidence reason."""
        rca = await self.get_rca(session, rca_id)

        target_cause: Optional[Dict[str, Any]] = None

        fishbone = copy.deepcopy(rca.fishbone_data or {})
        for cat_name, causes in fishbone.items():
            for c in causes:
                if c.get("cause_id") == cause_id:
                    target_cause = c
                    break
            if target_cause:
                break

        root_causes = copy.deepcopy(rca.root_causes_data or [])
        rc_target = next(
            (c for c in root_causes if c.get("cause_id") == cause_id), None
        )
        target_cause = target_cause or rc_target

        contrib = copy.deepcopy(rca.contributing_factors_data or [])
        cf_target = next(
            (c for c in contrib if c.get("cause_id") == cause_id), None
        )
        target_cause = target_cause or cf_target

        if not target_cause:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cause {cause_id} not found in Root Cause Analysis {rca_id}.",
            )

        now_str = datetime.now(timezone.utc).isoformat()
        target_cause["status"] = CauseStatus.REJECTED.value
        target_cause["verification_status"] = CauseStatus.REJECTED.value
        target_cause["rejection_reason"] = request.rejection_reason
        target_cause["rejected_by"] = user.id if user else None
        target_cause["rejected_at"] = now_str

        # Add to rejected_hypotheses_data if not already there
        rejected = copy.deepcopy(rca.rejected_hypotheses_data or [])
        if not any(r.get("cause_id") == cause_id for r in rejected):
            rejected.append(target_cause)
        rca.rejected_hypotheses_data = rejected
        flag_modified(rca, "rejected_hypotheses_data")

        # Remove from active root causes if present
        if rc_target:
            root_causes = [c for c in root_causes if c.get("cause_id") != cause_id]
            rca.root_causes_data = root_causes
            flag_modified(rca, "root_causes_data")

        rca.fishbone_data = fishbone
        rca.contributing_factors_data = contrib
        flag_modified(rca, "fishbone_data")
        flag_modified(rca, "contributing_factors_data")

        rca.updated_at = datetime.now(timezone.utc)
        session.add(rca)
        await session.flush()
        await session.refresh(rca)
        await rca_repo.sync_relational_child_records(session, rca)

        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=rca.investigation_id,
            action=AuditAction.RCA_CAUSE_REJECTED.value,
            details={
                "rca_id": rca.id,
                "cause_id": cause_id,
                "rejection_reason": request.rejection_reason,
            },
        )
        return target_cause

    async def accept_rca(
        self,
        session: AsyncSession,
        user: Optional[User],
        rca_id: str,
        request: RCAAcceptRequest,
    ) -> RCAAnalysis:
        """
        Formally accepts Root Cause Analysis:
        - Supersedes any previously accepted RCA for the investigation.
        - Marks current RCA as ACCEPTED and human_confirmed.
        - Preserves historical records for ALCOA+ compliance.
        """
        rca = await self.get_rca(session, rca_id)

        # Supersede previous accepted runs
        superseded_count = await rca_repo.supersede_previous_accepted(
            session=session,
            investigation_id=rca.investigation_id,
            current_rca_id=rca.id,
        )

        rca.status = RCAStatus.ACCEPTED.value
        rca.reviewed_by = user.id if user else None
        rca.reviewed_at = datetime.now(timezone.utc)
        rca.reviewer_notes = request.reviewer_notes
        rca.updated_at = datetime.now(timezone.utc)

        # Mark specified or existing root causes as confirmed
        root_causes = copy.deepcopy(rca.root_causes_data or [])
        for rc in root_causes:
            if not request.confirmed_root_cause_ids or rc.get("cause_id") in request.confirmed_root_cause_ids:
                rc["human_confirmed"] = True
                rc["verification_status"] = CauseStatus.VERIFIED.value
        rca.root_causes_data = root_causes
        flag_modified(rca, "root_causes_data")

        session.add(rca)
        await session.flush()
        await session.refresh(rca)
        await rca_repo.sync_relational_child_records(session, rca)

        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=rca.investigation_id,
            action=AuditAction.RCA_ACCEPTED.value,
            details={
                "rca_id": rca.id,
                "version": rca.analysis_version,
                "superseded_previous_runs": superseded_count,
                "confirmed_root_causes": len(request.confirmed_root_cause_ids or root_causes),
            },
        )
        return rca

    async def request_evidence(
        self,
        session: AsyncSession,
        user: Optional[User],
        rca_id: str,
        request: RCAEvidenceRequest,
    ) -> RCAAnalysis:
        """Transitions RCA to NEEDS_MORE_EVIDENCE and appends an evidence gap record."""
        rca = await self.get_rca(session, rca_id)

        rca.status = RCAStatus.NEEDS_MORE_EVIDENCE.value
        rca.updated_at = datetime.now(timezone.utc)

        new_gap = {
            "gap_id": f"gap-req-{uuid.uuid4().hex[:6]}",
            "description": request.evidence_requested,
            "reason": "Requested during causal review before RCA finalization",
            "priority": request.priority,
            "suggested_source": "Quality Investigation Evidence Intake",
            "requested_by": user.id if user else None,
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }

        evidence_gaps = copy.deepcopy(rca.evidence_gaps_data or [])
        evidence_gaps.append(new_gap)
        rca.evidence_gaps_data = evidence_gaps
        flag_modified(rca, "evidence_gaps_data")

        session.add(rca)
        await session.flush()
        await session.refresh(rca)
        await rca_repo.sync_relational_child_records(session, rca)

        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=rca.investigation_id,
            action=AuditAction.RCA_EVIDENCE_REQUESTED.value,
            details={
                "rca_id": rca.id,
                "evidence_requested": request.evidence_requested,
                "priority": request.priority,
            },
        )
        return rca

    async def get_rca_history(
        self, session: AsyncSession, rca_id: str
    ) -> Dict[str, Any]:
        """Provides complete version history and audit log trail for an RCA."""
        rca = await self.get_rca(session, rca_id)
        all_runs = await rca_repo.get_by_investigation(
            session, rca.investigation_id, limit=50
        )
        audits = await audit_repo.get_by_investigation(session, rca.investigation_id)

        rca_audits = [
            {
                "id": str(a.id),
                "action": a.action,
                "performed_by": a.performed_by,
                "timestamp": a.created_at.isoformat() if a.created_at else None,
                "details": a.details,
            }
            for a in audits
            if a.action.startswith("RCA_")
        ]

        return {
            "current_rca_id": rca.id,
            "investigation_id": rca.investigation_id,
            "versions": [
                {
                    "rca_id": r.id,
                    "version": r.analysis_version,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                    "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                    "root_causes_count": len(r.root_causes_data or []),
                }
                for r in all_runs
            ],
            "audit_trail": rca_audits,
        }


rca_service = RCAService()
