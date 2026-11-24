"""
Evidence Gap & Investigation Completeness Orchestration Service
===============================================================
Orchestrates AI-driven gap detection, completeness evaluations, and human-in-the-loop review actions.
"""

import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.investigation import Investigation
from app.models.evidence_gap import EvidenceGap
from app.models.completeness import CompletenessAssessment
from app.models.evidence import Evidence
from app.models.enums import (
    AuditAction,
    AIExecutionStatus,
    EvidenceGapStatus,
    CompletenessOverallStatus,
)
from app.ai.schemas.execution import AIExecutionCreate
from app.ai.services.ai_service import get_ai_service
from app.repositories.evidence_gap_repository import evidence_gap_repo
from app.repositories.completeness_repository import completeness_repo
from app.repositories.ai_execution_repository import ai_execution_repo
from app.repositories.approval_audit_repository import audit_repo
from app.services.gap_context_service import gap_context_service
from app.ai.graphs.gap_builder import create_gap_assessment_graph
from app.ai.graphs.gap_state import GapAssessmentWorkflowState


class EvidenceGapService:
    async def start_evidence_gap_assessment(
        self,
        session: AsyncSession,
        investigation_id: str,
        user_id: Optional[str] = None,
        requirement_profile_version: str = "1.0.0",
    ) -> CompletenessAssessment:
        """
        Orchestrates full Evidence Gap Detection and Completeness Assessment workflow via LangGraph.
        """
        stmt = select(Investigation).where(Investigation.id == investigation_id)
        res = await session.execute(stmt)
        inv = res.scalar_one_or_none()
        if not inv:
            raise ValueError(f"Investigation {investigation_id} not found.")

        # Record AI execution start
        ai_svc = get_ai_service()
        provider = ai_svc.get_provider()
        workflow_id = str(uuid.uuid4())

        exec_in = AIExecutionCreate(
            investigation_id=investigation_id,
            workflow_id=workflow_id,
            workflow_type="evidence_gap_assessment",
            user_id=user_id,
            provider="groq" if provider.__class__.__name__ == "GroqProvider" else "mock",
            model=getattr(provider, "model", "llama-3.3-70b-versatile"),
            prompt_version=requirement_profile_version,
            input_context_summary={"profile_version": requirement_profile_version},
        )
        execution = await ai_execution_repo.record_execution_start(session, exec_in)

        await audit_repo.record_action(
            session,
            action=AuditAction.GAP_ASSESSMENT_STARTED.value,
            entity_type="Investigation",
            entity_id=investigation_id,
            user_id=user_id,
            investigation_id=investigation_id,
            details={"execution_id": execution.id, "profile_version": requirement_profile_version},
        )

        # Prepare context
        context = await gap_context_service.prepare_investigation_gap_context(
            session, investigation_id, user_id
        )

        # Build & execute LangGraph
        graph = create_gap_assessment_graph()
        initial_state: GapAssessmentWorkflowState = {
            "investigation_id": investigation_id,
            "requirement_profile_version": requirement_profile_version,
            "user_id": user_id,
            "context_data": context,
            "applicable_rules": [],
            "compiled_prompt_context": context.get("compiled_prompt_context", ""),
            "compiled_rules_text": "",
            "raw_ai_output": None,
            "overall_status": CompletenessOverallStatus.UNDETERMINED.value,
            "completeness_score": 0.0,
            "summary": None,
            "dimensions": [],
            "detected_gaps": [],
            "conflicting_evidence": [],
            "recommended_activities": [],
            "validated_gaps": [],
            "critical_unresolved_gaps": 0,
            "high_priority_unresolved_gaps": 0,
            "total_unresolved_gaps": 0,
            "conflicting_evidence_count": 0,
            "unverified_causal_claims_count": 0,
            "pending_reviews_count": 0,
            "error_message": None,
            "is_failed": False,
        }

        final_state = await graph.ainvoke(initial_state)

        if final_state.get("is_failed"):
            await ai_execution_repo.record_execution_completion(
                session,
                execution_id=execution.id,
                status=AIExecutionStatus.FAILED.value,
                error_message=final_state.get("error_message"),
            )
            await session.commit()
            raise RuntimeError(f"Gap assessment workflow failed: {final_state.get('error_message')}")

        # Compute next assessment version
        latest_ver = await completeness_repo.get_latest_version_number(session, investigation_id)
        current_version = latest_ver + 1

        # Persist detected gaps
        validated_gaps = final_state.get("validated_gaps", [])
        for gap_item in validated_gaps:
            new_gap = EvidenceGap(
                investigation_id=investigation_id,
                root_cause_id=gap_item.get("root_cause_id"),
                gap_title=gap_item.get("gap_title"),
                description=gap_item.get("description", ""),
                reason=gap_item.get("why_needed", "Required for quality compliance"),
                category=gap_item.get("category", "OTHER"),
                detection_type=gap_item.get("detection_type", "MISSING_EVIDENCE"),
                priority=gap_item.get("priority", "MEDIUM"),
                affected_area=gap_item.get("affected_area"),
                recommended_evidence_type=gap_item.get("recommended_evidence_type"),
                recommended_action=gap_item.get("recommended_action"),
                detection_source="AI_ASSESSMENT",
                ai_confidence=gap_item.get("confidence", 0.85),
                status=EvidenceGapStatus.OPEN.value,
                assessment_version=current_version,
                requirement_profile_version=requirement_profile_version,
                associated_evidence_ids=[],
                supporting_references=gap_item.get("supporting_references", []),
            )
            session.add(new_gap)
            await session.flush()

            await audit_repo.record_action(
                session,
                action=AuditAction.EVIDENCE_GAP_CREATED.value,
                entity_type="EvidenceGap",
                entity_id=new_gap.id,
                user_id=user_id,
                investigation_id=investigation_id,
                details={"gap_title": new_gap.gap_title, "category": new_gap.category, "priority": new_gap.priority},
            )

        # Persist completeness assessment
        assessment = await completeness_repo.create_assessment(
            session,
            investigation_id=investigation_id,
            assessment_version=current_version,
            overall_status=final_state.get("overall_status", CompletenessOverallStatus.UNDETERMINED.value),
            completeness_score=final_state.get("completeness_score", 0.0),
            dimension_results=final_state.get("dimensions", []),
            critical_unresolved_gaps=final_state.get("critical_unresolved_gaps", 0),
            high_priority_unresolved_gaps=final_state.get("high_priority_unresolved_gaps", 0),
            total_unresolved_gaps=final_state.get("total_unresolved_gaps", 0),
            conflicting_evidence_count=final_state.get("conflicting_evidence_count", 0),
            unverified_causal_claims_count=final_state.get("unverified_causal_claims_count", 0),
            pending_reviews_count=final_state.get("pending_reviews_count", 0),
            recommended_activities=final_state.get("recommended_activities", []),
            requirement_profile_version=requirement_profile_version,
            summary=final_state.get("summary"),
            ai_execution_id=execution.id,
            created_by=user_id,
        )

        await ai_execution_repo.record_execution_completion(
            session,
            execution_id=execution.id,
            status=AIExecutionStatus.COMPLETED.value,
            structured_output={
                "assessment_version": current_version,
                "overall_status": assessment.overall_status,
                "score": assessment.completeness_score,
                "total_gaps": len(validated_gaps),
            },
        )

        await audit_repo.record_action(
            session,
            action=AuditAction.COMPLETENESS_ASSESSMENT_CREATED.value,
            entity_type="CompletenessAssessment",
            entity_id=assessment.id,
            user_id=user_id,
            investigation_id=investigation_id,
            details={"version": current_version, "score": assessment.completeness_score, "status": assessment.overall_status},
        )

        await session.commit()
        return assessment

    async def get_latest_completeness_assessment(
        self, session: AsyncSession, investigation_id: str
    ) -> Optional[CompletenessAssessment]:
        return await completeness_repo.get_latest_for_investigation(session, investigation_id)

    async def get_completeness_history(
        self, session: AsyncSession, investigation_id: str, limit: int = 50
    ) -> List[CompletenessAssessment]:
        return await completeness_repo.get_history_for_investigation(session, investigation_id, limit)

    async def list_evidence_gaps(
        self,
        session: AsyncSession,
        investigation_id: str,
        skip: int = 0,
        limit: int = 50,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> Tuple[List[EvidenceGap], int]:
        return await evidence_gap_repo.get_by_investigation(
            session,
            investigation_id,
            skip=skip,
            limit=limit,
            category=category,
            priority=priority,
            status=status,
            assigned_to=assigned_to,
        )

    async def get_evidence_gap(
        self, session: AsyncSession, gap_id: str
    ) -> Optional[EvidenceGap]:
        return await evidence_gap_repo.get_detailed(session, gap_id)

    async def patch_evidence_gap(
        self,
        session: AsyncSession,
        gap_id: str,
        user_id: Optional[str],
        patch_data: Dict[str, Any],
    ) -> Optional[EvidenceGap]:
        gap = await evidence_gap_repo.get(session, gap_id)
        if not gap:
            return None
        old_val = {"gap_title": gap.gap_title, "priority": gap.priority, "category": gap.category}

        for k, v in patch_data.items():
            if v is not None and hasattr(gap, k):
                setattr(gap, k, v)
        gap.updated_at = datetime.now(timezone.utc)
        session.add(gap)
        await session.flush()
        await session.refresh(gap)

        await audit_repo.record_action(
            session,
            action=AuditAction.EVIDENCE_GAP_UPDATED.value,
            entity_type="EvidenceGap",
            entity_id=gap.id,
            user_id=user_id,
            investigation_id=gap.investigation_id,
            old_values=old_val,
            new_values=patch_data,
        )
        await session.commit()
        return gap

    async def assign_evidence_gap(
        self,
        session: AsyncSession,
        gap_id: str,
        user_id: Optional[str],
        assigned_to: str,
        due_date: Optional[datetime] = None,
    ) -> Optional[EvidenceGap]:
        gap = await evidence_gap_repo.get(session, gap_id)
        if not gap:
            return None
        old_assigned = gap.assigned_to

        updated = await evidence_gap_repo.assign_gap(
            session, gap_id=gap_id, assigned_to=assigned_to, due_date=due_date
        )

        await audit_repo.record_action(
            session,
            action=AuditAction.EVIDENCE_GAP_ASSIGNED.value,
            entity_type="EvidenceGap",
            entity_id=gap.id,
            user_id=user_id,
            investigation_id=gap.investigation_id,
            old_values={"assigned_to": old_assigned},
            new_values={"assigned_to": assigned_to, "due_date": due_date.isoformat() if due_date else None},
        )
        await session.commit()
        return updated

    async def request_evidence(
        self,
        session: AsyncSession,
        gap_id: str,
        user_id: Optional[str],
        notes: str,
        suggested_source: Optional[str] = None,
    ) -> Optional[EvidenceGap]:
        gap = await evidence_gap_repo.get(session, gap_id)
        if not gap:
            return None

        updated = await evidence_gap_repo.request_evidence(
            session, gap_id=gap_id, notes=notes, suggested_source=suggested_source
        )

        await audit_repo.record_action(
            session,
            action=AuditAction.EVIDENCE_REQUESTED.value,
            entity_type="EvidenceGap",
            entity_id=gap.id,
            user_id=user_id,
            investigation_id=gap.investigation_id,
            details={"notes": notes, "suggested_source": suggested_source},
        )
        await session.commit()
        return updated

    async def associate_evidence(
        self,
        session: AsyncSession,
        gap_id: str,
        user_id: Optional[str],
        evidence_ids: List[str],
    ) -> Optional[EvidenceGap]:
        gap = await evidence_gap_repo.get(session, gap_id)
        if not gap:
            return None

        # Verify evidence belongs to this investigation
        stmt = select(Evidence.id).where(
            Evidence.investigation_id == gap.investigation_id,
            Evidence.id.in_(evidence_ids),
        )
        res = await session.execute(stmt)
        valid_ids = set(res.scalars().all())
        if len(valid_ids) != len(evidence_ids):
            invalid = set(evidence_ids) - valid_ids
            raise ValueError(f"Evidence IDs {invalid} do not belong to this investigation.")

        updated = await evidence_gap_repo.associate_evidence(
            session, gap_id=gap_id, evidence_ids=evidence_ids
        )

        await audit_repo.record_action(
            session,
            action=AuditAction.EVIDENCE_ASSOCIATED.value,
            entity_type="EvidenceGap",
            entity_id=gap.id,
            user_id=user_id,
            investigation_id=gap.investigation_id,
            details={"evidence_ids": evidence_ids},
        )
        await session.commit()
        return updated

    async def resolve_evidence_gap(
        self,
        session: AsyncSession,
        gap_id: str,
        user_id: Optional[str],
        justification: str,
        evidence_ids: Optional[List[str]] = None,
    ) -> Optional[EvidenceGap]:
        gap = await evidence_gap_repo.get(session, gap_id)
        if not gap:
            return None
        if not justification or not justification.strip():
            raise ValueError("Justification is mandatory when resolving an evidence gap.")

        if evidence_ids:
            # Verify evidence IDs belong to this investigation
            stmt = select(Evidence.id).where(
                Evidence.investigation_id == gap.investigation_id,
                Evidence.id.in_(evidence_ids),
            )
            res = await session.execute(stmt)
            valid_ids = set(res.scalars().all())
            if len(valid_ids) != len(evidence_ids):
                raise ValueError("Associated evidence IDs do not belong to this investigation.")

        updated = await evidence_gap_repo.resolve_gap(
            session,
            gap_id=gap_id,
            justification=justification,
            resolved_by=user_id or "UNKNOWN",
            evidence_ids=evidence_ids,
        )

        await audit_repo.record_action(
            session,
            action=AuditAction.EVIDENCE_GAP_RESOLVED.value,
            entity_type="EvidenceGap",
            entity_id=gap.id,
            user_id=user_id,
            investigation_id=gap.investigation_id,
            details={"justification": justification, "evidence_ids": evidence_ids or []},
        )
        await session.commit()
        return updated

    async def reject_evidence_gap(
        self,
        session: AsyncSession,
        gap_id: str,
        user_id: Optional[str],
        justification: str,
    ) -> Optional[EvidenceGap]:
        gap = await evidence_gap_repo.get(session, gap_id)
        if not gap:
            return None
        if not justification or not justification.strip():
            raise ValueError("Justification is mandatory when rejecting an evidence gap.")

        updated = await evidence_gap_repo.reject_gap(
            session,
            gap_id=gap_id,
            justification=justification,
            resolved_by=user_id or "UNKNOWN",
        )

        await audit_repo.record_action(
            session,
            action=AuditAction.EVIDENCE_GAP_REJECTED.value,
            entity_type="EvidenceGap",
            entity_id=gap.id,
            user_id=user_id,
            investigation_id=gap.investigation_id,
            details={"justification": justification},
        )
        await session.commit()
        return updated

    async def waive_evidence_gap(
        self,
        session: AsyncSession,
        gap_id: str,
        user_id: Optional[str],
        justification: str,
        policy_reference: Optional[str] = None,
    ) -> Optional[EvidenceGap]:
        gap = await evidence_gap_repo.get(session, gap_id)
        if not gap:
            return None
        if not justification or not justification.strip():
            raise ValueError("Justification is mandatory when waiving an evidence gap.")

        updated = await evidence_gap_repo.waive_gap(
            session,
            gap_id=gap_id,
            justification=justification,
            resolved_by=user_id or "UNKNOWN",
            policy_reference=policy_reference,
        )

        await audit_repo.record_action(
            session,
            action=AuditAction.EVIDENCE_GAP_WAIVED.value,
            entity_type="EvidenceGap",
            entity_id=gap.id,
            user_id=user_id,
            investigation_id=gap.investigation_id,
            details={"justification": justification, "policy_reference": policy_reference},
        )
        await session.commit()
        return updated

    async def reopen_evidence_gap(
        self,
        session: AsyncSession,
        gap_id: str,
        user_id: Optional[str],
        justification: str,
    ) -> Optional[EvidenceGap]:
        gap = await evidence_gap_repo.get(session, gap_id)
        if not gap:
            return None
        if not justification or not justification.strip():
            raise ValueError("Justification is mandatory when reopening an evidence gap.")

        updated = await evidence_gap_repo.reopen_gap(
            session, gap_id=gap_id, justification=justification
        )

        await audit_repo.record_action(
            session,
            action=AuditAction.EVIDENCE_GAP_REOPENED.value,
            entity_type="EvidenceGap",
            entity_id=gap.id,
            user_id=user_id,
            investigation_id=gap.investigation_id,
            details={"justification": justification},
        )
        await session.commit()
        return updated

    async def get_gap_history(
        self, session: AsyncSession, gap_id: str
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(audit_repo.model)
            .where(
                audit_repo.model.entity_type == "EvidenceGap",
                audit_repo.model.entity_id == gap_id,
            )
            .order_by(audit_repo.model.created_at)
        )
        res = await session.execute(stmt)
        audits = list(res.scalars().all())
        history = []
        for a in audits:
            history.append({
                "action": a.action,
                "timestamp": a.created_at.isoformat(),
                "performed_by": a.user_id,
                "old_values": a.old_values,
                "new_values": a.new_values,
            })
        return history


evidence_gap_service = EvidenceGapService()
