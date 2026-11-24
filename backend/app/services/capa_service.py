import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.capa import CAPA, CAPATask, CAPARecommendation, EffectivenessCheck
from app.models.audit import AuditLog
from app.models.enums import (
    AuditAction,
    CAPAStatus,
    CAPATaskStatus,
    CAPARecommendationStatus,
    AIExecutionStatus,
    EffectivenessStatus,
    EffectivenessDecision,
    AIEffectivenessProposal,
    InvestigationStatus,
)
from app.ai.schemas.execution import AIExecutionCreate
from app.repositories.capa_repository import capa_repo
from app.repositories.ai_execution_repository import ai_execution_repo
from app.repositories.evidence_gap_repository import evidence_gap_repo
from app.repositories.investigation_repository import investigation_repo
from app.repositories.document_evidence_repository import evidence_repo
from app.services.capa_context_service import capa_context_service
from app.ai.graphs.capa_builder import build_capa_recommendation_graph
from app.ai.graphs.effectiveness_builder import build_effectiveness_assessment_graph

logger = logging.getLogger("pharmarca.capa_service")


def _is_overdue(due_date: Optional[datetime], now_utc: datetime) -> bool:
    if not due_date:
        return False
    if due_date.tzinfo is None:
        return due_date < now_utc.replace(tzinfo=None)
    return due_date < now_utc


class CAPAService:
    """
    Enterprise business logic service for CAPA Planning, Recommendations,
    Approval Governance, and Task Lifecycle Management.
    """

    # -------------------------------------------------------------
    # AI Recommendation Generation
    # -------------------------------------------------------------

    async def generate_capa_recommendations(
        self,
        session: AsyncSession,
        investigation_id: str,
        user_id: Optional[str] = None,
        focus_action_type: Optional[str] = None,
    ) -> List[CAPARecommendation]:
        """
        Gathers confirmed investigation context, invokes the LangGraph recommendation
        workflow, persists structured recommendations, and writes audit logs.
        """
        # 1. Record execution start
        exec_record = await ai_execution_repo.record_execution_start(
            session,
            create_in=AIExecutionCreate(
                workflow_id=str(uuid.uuid4()),
                workflow_type="capa_recommendation",
                investigation_id=investigation_id,
                user_id=user_id,
                provider="groq",
                model="llama-3.3-70b-versatile",
                prompt_version="1.0.0",
                input_context_summary={"focus_action_type": focus_action_type},
            ),
        )

        try:
            # 2. Gather context
            context = await capa_context_service.gather_capa_context(session, investigation_id)

            # 3. Execute LangGraph workflow
            graph = build_capa_recommendation_graph()
            initial_state = {
                "investigation_id": investigation_id,
                "focus_action_type": focus_action_type,
                "user_id": user_id,
                "context": context,
                "execution_id": exec_record.id,
            }
            final_state = await graph.ainvoke(initial_state)

            if final_state.get("is_failed"):
                err_msg = final_state.get("error_message", "CAPA recommendation workflow failed.")
                await ai_execution_repo.record_execution_completion(
                    session,
                    execution_id=exec_record.id,
                    status=AIExecutionStatus.FAILED.value,
                    error_message=err_msg,
                )
                raise ValueError(err_msg)

            # 4. Convert output to CAPARecommendation models
            raw_recs = final_state.get("recommendations", [])
            db_items: List[CAPARecommendation] = []

            for r in raw_recs:
                target_dt = None
                if r.get("target_date"):
                    try:
                        target_dt = datetime.fromisoformat(r["target_date"])
                    except Exception:
                        target_dt = None

                rec = CAPARecommendation(
                    investigation_id=investigation_id,
                    ai_execution_id=exec_record.id,
                    recommendation_title=r["recommendation_title"],
                    description=r["description"],
                    action_type=r["action_type"],
                    root_cause_id=r.get("root_cause_id"),
                    root_cause_title=r.get("root_cause_title"),
                    contributing_factor_ids=r.get("contributing_factor_ids", []),
                    evidence_gap_ids=r.get("evidence_gap_ids", []),
                    supporting_references=r.get("supporting_references", []),
                    rationale=r["rationale"],
                    expected_outcome=r["expected_outcome"],
                    recurrence_risk_addressed=r.get("recurrence_risk_addressed"),
                    priority=r.get("priority", "MEDIUM"),
                    suggested_department=r.get("suggested_department"),
                    suggested_role=r.get("suggested_role"),
                    suggested_target_days=r.get("suggested_target_days", 30),
                    target_date=target_dt,
                    implementation_steps=r.get("implementation_steps", []),
                    completion_criteria=r["completion_criteria"],
                    required_completion_evidence=r["required_completion_evidence"],
                    implementation_risks=r.get("implementation_risks"),
                    is_provisional=r.get("is_provisional", False),
                    uncertainty_rationale=r.get("uncertainty_rationale"),
                    status=CAPARecommendationStatus.PENDING_REVIEW.value,
                )
                db_items.append(rec)

            persisted_recs = await capa_repo.create_recommendations(session, db_items)

            # 5. Record execution success
            await ai_execution_repo.record_execution_completion(
                session,
                execution_id=exec_record.id,
                status=AIExecutionStatus.COMPLETED.value,
                structured_output={"recommendations_count": len(persisted_recs)},
            )

            # 6. Record Audit Log
            audit_entry = AuditLog(
                user_id=user_id,
                investigation_id=investigation_id,
                action=AuditAction.CAPA_RECOMMENDATION_GENERATED.value,
                entity_type="capa_recommendation",
                entity_id=exec_record.id,
                new_values={
                    "recommendations_count": len(persisted_recs),
                    "corrective_count": final_state.get("corrective_actions_count", 0),
                    "preventive_count": final_state.get("preventive_actions_count", 0),
                },
            )
            session.add(audit_entry)
            await session.commit()

            return persisted_recs

        except Exception as e:
            logger.error(f"Failed in generate_capa_recommendations: {e}")
            await session.rollback()
            raise

    # -------------------------------------------------------------
    # Recommendation Review & Listing
    # -------------------------------------------------------------

    async def list_recommendations(
        self,
        session: AsyncSession,
        investigation_id: str,
        status: Optional[str] = None,
        action_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[CAPARecommendation], int]:
        return await capa_repo.list_recommendations(
            session,
            investigation_id=investigation_id,
            status=status,
            action_type=action_type,
            skip=skip,
            limit=limit,
        )

    async def get_recommendation(
        self, session: AsyncSession, recommendation_id: str
    ) -> Optional[CAPARecommendation]:
        return await capa_repo.get_recommendation(session, recommendation_id)

    async def patch_recommendation(
        self,
        session: AsyncSession,
        recommendation_id: str,
        user_id: str,
        patch_data: Dict[str, Any],
    ) -> CAPARecommendation:
        rec = await capa_repo.get_recommendation(session, recommendation_id)
        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found.")

        old_vals = {
            "title": rec.recommendation_title,
            "action_type": rec.action_type,
            "priority": rec.priority,
        }
        updated = await capa_repo.update_recommendation(session, recommendation_id, patch_data)

        # Audit
        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=rec.investigation_id,
                action=AuditAction.CAPA_RECOMMENDATION_EDITED.value,
                entity_type="capa_recommendation",
                entity_id=rec.id,
                old_values=old_vals,
                new_values=patch_data,
            )
        )
        await session.commit()
        return updated

    async def accept_recommendation(
        self,
        session: AsyncSession,
        recommendation_id: str,
        user_id: str,
        notes: Optional[str] = None,
    ) -> CAPARecommendation:
        rec = await capa_repo.get_recommendation(session, recommendation_id)
        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found.")

        patch = {
            "status": CAPARecommendationStatus.ACCEPTED.value,
            "reviewed_by": user_id,
            "reviewed_at": datetime.now(timezone.utc),
        }
        updated = await capa_repo.update_recommendation(session, recommendation_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=rec.investigation_id,
                action=AuditAction.CAPA_RECOMMENDATION_ACCEPTED.value,
                entity_type="capa_recommendation",
                entity_id=rec.id,
                new_values={"notes": notes, "status": "ACCEPTED"},
            )
        )
        await session.commit()
        return updated

    async def reject_recommendation(
        self,
        session: AsyncSession,
        recommendation_id: str,
        user_id: str,
        justification: str,
    ) -> CAPARecommendation:
        if not justification or not justification.strip():
            raise ValueError("Mandatory justification is required to reject a CAPA recommendation.")

        rec = await capa_repo.get_recommendation(session, recommendation_id)
        if not rec:
            raise ValueError(f"Recommendation {recommendation_id} not found.")

        patch = {
            "status": CAPARecommendationStatus.REJECTED.value,
            "rejection_reason": justification.strip(),
            "reviewed_by": user_id,
            "reviewed_at": datetime.now(timezone.utc),
        }
        updated = await capa_repo.update_recommendation(session, recommendation_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=rec.investigation_id,
                action=AuditAction.CAPA_RECOMMENDATION_REJECTED.value,
                entity_type="capa_recommendation",
                entity_id=rec.id,
                new_values={"justification": justification, "status": "REJECTED"},
            )
        )
        await session.commit()
        return updated

    # -------------------------------------------------------------
    # CAPA Plan Creation & Lifecycle
    # -------------------------------------------------------------

    async def create_capa_plan(
        self,
        session: AsyncSession,
        investigation_id: str,
        user_id: str,
        plan_data: Dict[str, Any],
    ) -> CAPA:
        capa_number = await capa_repo.generate_next_capa_number(session, investigation_id)
        rec_ids = plan_data.pop("accepted_recommendation_ids", [])

        capa = CAPA(
            capa_number=capa_number,
            investigation_id=investigation_id,
            rca_analysis_id=plan_data.get("rca_analysis_id"),
            root_cause_id=plan_data.get("root_cause_id"),
            capa_type=plan_data.get("capa_type", "CORRECTIVE"),
            title=plan_data["title"],
            description=plan_data["description"],
            problem_statement=plan_data.get("problem_statement"),
            root_cause_summary=plan_data.get("root_cause_summary"),
            corrective_action_summary=plan_data.get("corrective_action_summary"),
            preventive_action_summary=plan_data.get("preventive_action_summary"),
            rationale=plan_data.get("rationale"),
            priority=plan_data.get("priority", "MEDIUM"),
            status=CAPAStatus.DRAFT.value,
            responsible_department=plan_data.get("responsible_department"),
            assigned_to=plan_data.get("assigned_to"),
            initiated_date=datetime.now(timezone.utc),
            due_date=plan_data.get("due_date"),
            approval_status="DRAFT",
            supporting_references=plan_data.get("supporting_references", []),
        )
        session.add(capa)
        await session.flush()
        await session.refresh(capa)

        # Mark associated recommendations as IMPLEMENTED
        for r_id in rec_ids:
            await capa_repo.update_recommendation(
                session,
                r_id,
                {
                    "status": CAPARecommendationStatus.IMPLEMENTED.value,
                    "created_capa_id": capa.id,
                },
            )

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=investigation_id,
                action=AuditAction.CAPA_CREATED.value,
                entity_type="capa",
                entity_id=capa.id,
                new_values={
                    "capa_number": capa_number,
                    "title": capa.title,
                    "capa_type": capa.capa_type,
                    "status": capa.status,
                },
            )
        )
        await session.commit()
        return await capa_repo.get_capa_detailed(session, capa.id)

    async def list_capas(
        self,
        session: AsyncSession,
        investigation_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[CAPA], int]:
        return await capa_repo.list_capas(
            session,
            investigation_id=investigation_id,
            status=status,
            priority=priority,
            skip=skip,
            limit=limit,
        )

    async def get_capa(
        self, session: AsyncSession, capa_id: str
    ) -> Optional[CAPA]:
        return await capa_repo.get_capa_detailed(session, capa_id)

    async def patch_capa(
        self,
        session: AsyncSession,
        capa_id: str,
        user_id: str,
        patch_data: Dict[str, Any],
    ) -> CAPA:
        capa = await capa_repo.get_capa_detailed(session, capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found.")

        if capa.status in [CAPAStatus.APPROVED.value, CAPAStatus.CLOSED.value, "Approved", "Closed"]:
            raise ValueError("Approved or Closed CAPA plans cannot be mutated without a formal revision.")

        old_vals = {"title": capa.title, "priority": capa.priority, "status": capa.status}
        updated = await capa_repo.update_capa(session, capa_id, patch_data)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=capa.investigation_id,
                action=AuditAction.CAPA_UPDATED.value,
                entity_type="capa",
                entity_id=capa.id,
                old_values=old_vals,
                new_values=patch_data,
            )
        )
        await session.commit()
        return updated

    # -------------------------------------------------------------
    # Controlled Approval Workflow
    # -------------------------------------------------------------

    async def submit_capa_for_review(
        self,
        session: AsyncSession,
        capa_id: str,
        user_id: str,
        comments: Optional[str] = None,
    ) -> CAPA:
        capa = await capa_repo.get_capa_detailed(session, capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found.")

        patch = {
            "status": CAPAStatus.PENDING_REVIEW.value,
            "approval_status": "PENDING_REVIEW",
            "approval_comments": comments,
        }
        updated = await capa_repo.update_capa(session, capa_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=capa.investigation_id,
                action=AuditAction.CAPA_SUBMITTED_FOR_REVIEW.value,
                entity_type="capa",
                entity_id=capa.id,
                new_values={"status": "PENDING_REVIEW", "comments": comments},
            )
        )
        await session.commit()
        return updated

    async def submit_capa_for_approval(
        self,
        session: AsyncSession,
        capa_id: str,
        user_id: str,
        comments: Optional[str] = None,
    ) -> CAPA:
        capa = await capa_repo.get_capa_detailed(session, capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found.")

        patch = {
            "status": CAPAStatus.PENDING_APPROVAL.value,
            "approval_status": "PENDING_APPROVAL",
            "approval_comments": comments,
        }
        updated = await capa_repo.update_capa(session, capa_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=capa.investigation_id,
                action=AuditAction.CAPA_SUBMITTED_FOR_APPROVAL.value,
                entity_type="capa",
                entity_id=capa.id,
                new_values={"status": "PENDING_APPROVAL", "comments": comments},
            )
        )
        await session.commit()
        return updated

    async def approve_capa(
        self,
        session: AsyncSession,
        capa_id: str,
        user_id: str,
        comments: Optional[str] = None,
    ) -> CAPA:
        capa = await capa_repo.get_capa_detailed(session, capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found.")

        patch = {
            "status": CAPAStatus.APPROVED.value,
            "approval_status": "APPROVED",
            "approved_by": user_id,
            "approved_at": datetime.now(timezone.utc),
            "approval_comments": comments,
        }
        updated = await capa_repo.update_capa(session, capa_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=capa.investigation_id,
                action=AuditAction.CAPA_APPROVED.value,
                entity_type="capa",
                entity_id=capa.id,
                new_values={"status": "APPROVED", "comments": comments},
            )
        )
        await session.commit()
        return updated

    async def reject_capa(
        self,
        session: AsyncSession,
        capa_id: str,
        user_id: str,
        justification: str,
    ) -> CAPA:
        if not justification or not justification.strip():
            raise ValueError("Mandatory rejection justification is required.")

        capa = await capa_repo.get_capa_detailed(session, capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found.")

        patch = {
            "status": CAPAStatus.REJECTED.value,
            "approval_status": "REJECTED",
            "approval_comments": justification.strip(),
        }
        updated = await capa_repo.update_capa(session, capa_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=capa.investigation_id,
                action=AuditAction.CAPA_REJECTED.value,
                entity_type="capa",
                entity_id=capa.id,
                new_values={"status": "REJECTED", "justification": justification},
            )
        )
        await session.commit()
        return updated

    # -------------------------------------------------------------
    # CAPA Task Lifecycle Management
    # -------------------------------------------------------------

    async def create_task(
        self,
        session: AsyncSession,
        capa_id: str,
        user_id: str,
        task_data: Dict[str, Any],
    ) -> CAPATask:
        capa = await capa_repo.get_capa_detailed(session, capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found.")

        task = CAPATask(
            capa_id=capa_id,
            title=task_data["title"],
            description=task_data.get("description"),
            action_type=task_data.get("action_type", "CORRECTIVE"),
            assigned_to=task_data.get("assigned_to"),
            department=task_data.get("department"),
            target_start_date=task_data.get("target_start_date"),
            due_date=task_data.get("due_date"),
            priority=task_data.get("priority", "MEDIUM"),
            status=task_data.get("status", CAPATaskStatus.NOT_STARTED.value),
            dependencies=task_data.get("dependencies", []),
            completion_criteria=task_data.get("completion_criteria"),
            required_evidence=task_data.get("required_evidence"),
        )
        session.add(task)
        await session.flush()
        await session.refresh(task)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=capa.investigation_id,
                action=AuditAction.CAPA_TASK_CREATED.value,
                entity_type="capa_task",
                entity_id=task.id,
                new_values={"capa_id": capa_id, "title": task.title},
            )
        )
        await session.commit()
        return await capa_repo.get_task(session, task.id)

    async def list_tasks(
        self,
        session: AsyncSession,
        capa_id: str,
        status: Optional[str] = None,
    ) -> List[CAPATask]:
        return await capa_repo.list_tasks(session, capa_id=capa_id, status=status)

    async def get_task(
        self, session: AsyncSession, task_id: str
    ) -> Optional[CAPATask]:
        return await capa_repo.get_task(session, task_id)

    async def patch_task(
        self,
        session: AsyncSession,
        task_id: str,
        user_id: str,
        patch_data: Dict[str, Any],
    ) -> CAPATask:
        task = await capa_repo.get_task(session, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        old_vals = {"title": task.title, "status": task.status}
        updated = await capa_repo.update_task(session, task_id, patch_data)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=task.capa.investigation_id if task.capa else None,
                action=AuditAction.CAPA_TASK_UPDATED.value,
                entity_type="capa_task",
                entity_id=task.id,
                old_values=old_vals,
                new_values=patch_data,
            )
        )
        await session.commit()
        return updated

    async def assign_task(
        self,
        session: AsyncSession,
        task_id: str,
        user_id: str,
        assigned_to: Optional[str] = None,
        due_date: Optional[datetime] = None,
        department: Optional[str] = None,
        assign_data: Optional[Dict[str, Any]] = None,
    ) -> CAPATask:
        if assign_data:
            assigned_to = assign_data.get("assigned_to", assigned_to)
            due_date = assign_data.get("due_date", due_date)
            department = assign_data.get("department", department)

        task = await capa_repo.get_task(session, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        patch: Dict[str, Any] = {
            "assigned_to": assigned_to,
            "status": CAPATaskStatus.PENDING.value,
        }
        if due_date:
            patch["due_date"] = due_date
        if department:
            patch["department"] = department

        updated = await capa_repo.update_task(session, task_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=task.capa.investigation_id if task.capa else None,
                action=AuditAction.CAPA_TASK_ASSIGNED.value,
                entity_type="capa_task",
                entity_id=task.id,
                new_values={"assigned_to": assigned_to, "due_date": str(due_date)},
            )
        )
        await session.commit()
        return updated

    async def submit_task_completion(
        self,
        session: AsyncSession,
        task_id: str,
        user_id: str,
        completion_notes: str,
        evidence_references: Optional[List[str]] = None,
    ) -> CAPATask:
        if not completion_notes or not completion_notes.strip():
            raise ValueError("Completion notes are mandatory when submitting a task for review.")

        task = await capa_repo.get_task(session, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        patch = {
            "status": CAPATaskStatus.PENDING_REVIEW.value,
            "completion_notes": completion_notes.strip(),
            "submitted_evidence_references": evidence_references or [],
        }
        updated = await capa_repo.update_task(session, task_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=task.capa.investigation_id if task.capa else None,
                action=AuditAction.CAPA_TASK_COMPLETION_SUBMITTED.value,
                entity_type="capa_task",
                entity_id=task.id,
                new_values={"notes": completion_notes, "evidence": evidence_references},
            )
        )
        await session.commit()
        return updated

    async def approve_task_completion(
        self,
        session: AsyncSession,
        task_id: str,
        user_id: str,
        comments: Optional[str] = None,
    ) -> CAPATask:
        task = await capa_repo.get_task(session, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        patch = {
            "status": CAPATaskStatus.COMPLETED.value,
            "completed_at": datetime.now(timezone.utc),
            "reviewed_by": user_id,
            "reviewed_at": datetime.now(timezone.utc),
            "review_comments": comments,
        }
        updated = await capa_repo.update_task(session, task_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=task.capa.investigation_id if task.capa else None,
                action=AuditAction.CAPA_TASK_COMPLETION_APPROVED.value,
                entity_type="capa_task",
                entity_id=task.id,
                new_values={"status": "COMPLETED", "comments": comments},
            )
        )
        await session.commit()
        return updated

    async def reject_task_completion(
        self,
        session: AsyncSession,
        task_id: str,
        user_id: str,
        justification: str,
    ) -> CAPATask:
        if not justification or not justification.strip():
            raise ValueError("Mandatory justification is required to reject task completion.")

        task = await capa_repo.get_task(session, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found.")

        patch = {
            "status": CAPATaskStatus.REJECTED.value,
            "reviewed_by": user_id,
            "reviewed_at": datetime.now(timezone.utc),
            "review_comments": justification.strip(),
        }
        updated = await capa_repo.update_task(session, task_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=task.capa.investigation_id if task.capa else None,
                action=AuditAction.CAPA_TASK_COMPLETION_REJECTED.value,
                entity_type="capa_task",
                entity_id=task.id,
                new_values={"status": "REJECTED", "justification": justification},
            )
        )
        await session.commit()
        return updated

    # -------------------------------------------------------------
    # History & Audit Queries
    # -------------------------------------------------------------

    async def get_capa_history(
        self, session: AsyncSession, capa_id: str
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_id == capa_id)
            .order_by(AuditLog.created_at.desc())
        )
        res = await session.execute(stmt)
        logs = res.scalars().all()
        return [
            {
                "id": l.id,
                "action": l.action,
                "user_id": l.user_id,
                "old_values": l.old_values,
                "new_values": l.new_values,
                "timestamp": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]

    async def get_task_history(
        self, session: AsyncSession, task_id: str
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_id == task_id)
            .order_by(AuditLog.created_at.desc())
        )
        res = await session.execute(stmt)
        logs = res.scalars().all()
        return [
            {
                "id": l.id,
                "action": l.action,
                "user_id": l.user_id,
                "old_values": l.old_values,
                "new_values": l.new_values,
                "timestamp": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]

    # -------------------------------------------------------------
    # CAPA Implementation Monitoring
    # -------------------------------------------------------------

    async def get_investigation_capa_monitoring(
        self, session: AsyncSession, investigation_id: str
    ) -> Dict[str, Any]:
        """Calculates comprehensive implementation monitoring statistics for all CAPAs in an investigation."""
        capas, total_capas = await capa_repo.list_capas(session, investigation_id=investigation_id, limit=200)

        total_tasks = 0
        completed_tasks = 0
        verified_tasks = 0
        in_progress_tasks = 0
        overdue_tasks = 0

        now_utc = datetime.now(timezone.utc)
        eff_summary = {
            "SCHEDULED": 0,
            "IN_PROGRESS": 0,
            "EFFECTIVE": 0,
            "INEFFECTIVE": 0,
            "PARTIALLY_EFFECTIVE": 0,
            "INSUFFICIENT_EVIDENCE": 0,
            "CANCELLED": 0,
        }

        capa_breakdown = []

        for c in capas:
            c_tasks = await capa_repo.list_tasks(session, capa_id=c.id)
            c_eff = await capa_repo.list_effectiveness_checks(session, capa_id=c.id)

            c_total = len(c_tasks)
            c_completed = sum(1 for t in c_tasks if t.status in [CAPATaskStatus.COMPLETED.value, "Completed", "COMPLETED"])
            c_verified = sum(1 for t in c_tasks if t.status in [CAPATaskStatus.COMPLETED.value, "Completed", "COMPLETED"] and t.reviewed_by is not None)
            c_overdue = sum(1 for t in c_tasks if _is_overdue(t.due_date, now_utc) and t.status not in [CAPATaskStatus.COMPLETED.value, "Completed", "COMPLETED"])
            c_in_progress = sum(1 for t in c_tasks if t.status in [CAPATaskStatus.IN_PROGRESS.value, CAPATaskStatus.PENDING.value, "InProgress", "In Progress", "Pending"])

            total_tasks += c_total
            completed_tasks += c_completed
            verified_tasks += c_verified
            in_progress_tasks += c_in_progress
            overdue_tasks += c_overdue

            for ec in c_eff:
                status_key = ec.status.replace(" ", "_").upper() if ec.status else "SCHEDULED"
                eff_summary[status_key] = eff_summary.get(status_key, 0) + 1

            c_progress = (c_verified / c_total * 100.0) if c_total > 0 else (100.0 if c.status in [CAPAStatus.COMPLETED.value, CAPAStatus.CLOSED.value] else 0.0)

            capa_breakdown.append({
                "id": c.id,
                "capa_number": c.capa_number,
                "title": c.title,
                "status": c.status,
                "priority": c.priority,
                "total_tasks": c_total,
                "completed_tasks": c_completed,
                "verified_tasks": c_verified,
                "overdue_tasks": c_overdue,
                "progress_percentage": round(c_progress, 1),
                "effectiveness_checks_count": len(c_eff),
            })

        overall_progress = (verified_tasks / total_tasks * 100.0) if total_tasks > 0 else (100.0 if total_capas > 0 else 0.0)

        return {
            "investigation_id": investigation_id,
            "total_capas": total_capas,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "verified_tasks": verified_tasks,
            "in_progress_tasks": in_progress_tasks,
            "overdue_tasks": overdue_tasks,
            "implementation_progress_percentage": round(overall_progress, 1),
            "effectiveness_checks_summary": eff_summary,
            "capa_breakdown": capa_breakdown,
        }

    async def get_capa_monitoring(
        self, session: AsyncSession, capa_id: str
    ) -> Dict[str, Any]:
        """Calculates implementation monitoring metrics for an individual CAPA."""
        capa = await capa_repo.get_capa_detailed(session, capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found.")

        tasks = await capa_repo.list_tasks(session, capa_id=capa_id)
        eff_checks = await capa_repo.list_effectiveness_checks(session, capa_id=capa_id)

        now_utc = datetime.now(timezone.utc)
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status in [CAPATaskStatus.COMPLETED.value, "Completed", "COMPLETED"])
        verified_tasks = sum(1 for t in tasks if t.status in [CAPATaskStatus.COMPLETED.value, "Completed", "COMPLETED"] and t.reviewed_by is not None)
        in_progress_tasks = sum(1 for t in tasks if t.status in [CAPATaskStatus.IN_PROGRESS.value, CAPATaskStatus.PENDING.value, "InProgress", "In Progress", "Pending"])
        overdue_tasks = sum(1 for t in tasks if _is_overdue(t.due_date, now_utc) and t.status not in [CAPATaskStatus.COMPLETED.value, "Completed", "COMPLETED"])

        eff_summary = {
            "SCHEDULED": 0,
            "IN_PROGRESS": 0,
            "EFFECTIVE": 0,
            "INEFFECTIVE": 0,
            "PARTIALLY_EFFECTIVE": 0,
            "INSUFFICIENT_EVIDENCE": 0,
            "CANCELLED": 0,
        }
        for ec in eff_checks:
            status_key = ec.status.replace(" ", "_").upper() if ec.status else "SCHEDULED"
            eff_summary[status_key] = eff_summary.get(status_key, 0) + 1

        progress = (verified_tasks / total_tasks * 100.0) if total_tasks > 0 else (100.0 if capa.status in [CAPAStatus.COMPLETED.value, CAPAStatus.CLOSED.value] else 0.0)

        return {
            "capa_id": capa_id,
            "investigation_id": capa.investigation_id,
            "capa_number": capa.capa_number,
            "title": capa.title,
            "status": capa.status,
            "priority": capa.priority,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "verified_tasks": verified_tasks,
            "in_progress_tasks": in_progress_tasks,
            "overdue_tasks": overdue_tasks,
            "implementation_progress_percentage": round(progress, 1),
            "effectiveness_checks_summary": eff_summary,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                    "is_overdue": bool(_is_overdue(t.due_date, now_utc) and t.status != CAPATaskStatus.COMPLETED.value),
                    "assigned_to": t.assigned_to,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                }
                for t in tasks
            ],
            "effectiveness_checks": [
                {
                    "id": ec.id,
                    "check_title": ec.check_title,
                    "verification_type": ec.verification_type,
                    "status": ec.status,
                    "effectiveness_decision": ec.effectiveness_decision,
                    "planned_completion_date": ec.planned_completion_date.isoformat() if ec.planned_completion_date else None,
                }
                for ec in eff_checks
            ],
        }

    # -------------------------------------------------------------
    # Effectiveness Checks Operations
    # -------------------------------------------------------------

    async def create_effectiveness_check(
        self,
        session: AsyncSession,
        capa_id: str,
        user_id: str,
        check_data: Dict[str, Any],
    ) -> EffectivenessCheck:
        capa = await capa_repo.get_capa_detailed(session, capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found.")

        check = EffectivenessCheck(
            capa_id=capa_id,
            check_title=check_data.get("check_title", "CAPA Effectiveness Verification"),
            verification_type=check_data.get("verification_type", "PROCESS_MONITORING"),
            objective=check_data.get("objective"),
            verification_method=check_data["verification_method"],
            acceptance_criteria=check_data["acceptance_criteria"],
            measurement_method=check_data.get("measurement_method"),
            baseline_data=check_data.get("baseline_data"),
            expected_outcome=check_data.get("expected_outcome"),
            observation_period_days=check_data.get("observation_period_days", 30),
            planned_start_date=check_data.get("planned_start_date"),
            planned_completion_date=check_data.get("planned_completion_date"),
            responsible_reviewer_id=check_data.get("responsible_reviewer_id"),
            required_evidence=check_data.get("required_evidence"),
            associated_evidence_ids=check_data.get("associated_evidence_ids", []),
            sampling_approach=check_data.get("sampling_approach"),
            check_frequency=check_data.get("check_frequency"),
            status=EffectivenessStatus.SCHEDULED.value,
        )
        session.add(check)
        await session.flush()
        await session.refresh(check)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=capa.investigation_id,
                action=AuditAction.EFFECTIVENESS_CHECK_CREATED.value,
                entity_type="effectiveness_check",
                entity_id=check.id,
                new_values={"capa_id": capa_id, "check_title": check.check_title, "verification_type": check.verification_type},
            )
        )
        await session.commit()
        return await capa_repo.get_effectiveness_check(session, check.id)

    async def get_effectiveness_check(
        self, session: AsyncSession, check_id: str
    ) -> Optional[EffectivenessCheck]:
        return await capa_repo.get_effectiveness_check(session, check_id)

    async def list_effectiveness_checks(
        self,
        session: AsyncSession,
        capa_id: str,
        status: Optional[str] = None,
    ) -> List[EffectivenessCheck]:
        return await capa_repo.list_effectiveness_checks(session, capa_id=capa_id, status=status)

    async def patch_effectiveness_check(
        self,
        session: AsyncSession,
        check_id: str,
        user_id: str,
        patch_data: Dict[str, Any],
    ) -> EffectivenessCheck:
        check = await capa_repo.get_effectiveness_check(session, check_id)
        if not check:
            raise ValueError(f"Effectiveness check {check_id} not found.")

        if check.status in [EffectivenessStatus.EFFECTIVE.value, EffectivenessStatus.INEFFECTIVE.value, "Effective", "Ineffective"]:
            raise ValueError("Finalized effectiveness checks cannot be edited.")

        old_vals = {"check_title": check.check_title, "status": check.status}
        updated = await capa_repo.update_effectiveness_check(session, check_id, patch_data)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=check.capa.investigation_id if check.capa else None,
                action=AuditAction.EFFECTIVENESS_CHECK_UPDATED.value,
                entity_type="effectiveness_check",
                entity_id=check.id,
                old_values=old_vals,
                new_values=patch_data,
            )
        )
        await session.commit()
        return updated

    async def delete_effectiveness_check(
        self,
        session: AsyncSession,
        check_id: str,
        user_id: str,
    ) -> bool:
        check = await capa_repo.get_effectiveness_check(session, check_id)
        if not check:
            raise ValueError(f"Effectiveness check {check_id} not found.")

        if check.effectiveness_decision:
            raise ValueError("Cannot delete an effectiveness check that has already been decided.")

        investigation_id = check.capa.investigation_id if check.capa else None
        await capa_repo.delete_effectiveness_check(session, check_id)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=investigation_id,
                action=AuditAction.EFFECTIVENESS_CHECK_DELETED.value,
                entity_type="effectiveness_check",
                entity_id=check_id,
                old_values={"title": check.check_title},
            )
        )
        await session.commit()
        return True

    async def attach_evidence_to_effectiveness_check(
        self,
        session: AsyncSession,
        check_id: str,
        user_id: str,
        evidence_ids: List[str],
    ) -> EffectivenessCheck:
        check = await capa_repo.get_effectiveness_check(session, check_id)
        if not check:
            raise ValueError(f"Effectiveness check {check_id} not found.")

        current_evidence = list(check.associated_evidence_ids or [])
        for e_id in evidence_ids:
            if e_id not in current_evidence:
                current_evidence.append(e_id)

        updated = await capa_repo.update_effectiveness_check(
            session,
            check_id,
            {"associated_evidence_ids": current_evidence, "status": EffectivenessStatus.IN_PROGRESS.value},
        )

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=check.capa.investigation_id if check.capa else None,
                action=AuditAction.EFFECTIVENESS_CHECK_EVIDENCE_ATTACHED.value,
                entity_type="effectiveness_check",
                entity_id=check.id,
                new_values={"evidence_ids": evidence_ids},
            )
        )
        await session.commit()
        return updated

    async def assess_effectiveness_ai(
        self,
        session: AsyncSession,
        check_id: str,
        user_id: str,
    ) -> EffectivenessCheck:
        check = await capa_repo.get_effectiveness_check(session, check_id)
        if not check:
            raise ValueError(f"Effectiveness check {check_id} not found.")

        capa = check.capa
        investigation_id = capa.investigation_id if capa else ""

        # Fetch associated evidence records
        evidence_records = []
        for e_id in (check.associated_evidence_ids or []):
            ev = await evidence_repo.get(session, e_id)
            if ev:
                evidence_records.append({
                    "id": ev.id,
                    "title": ev.title,
                    "description": ev.description,
                    "evidence_type": ev.evidence_type,
                })

        # Record AI execution start
        exec_record = await ai_execution_repo.record_execution_start(
            session,
            create_in=AIExecutionCreate(
                workflow_id=str(uuid.uuid4()),
                workflow_type="effectiveness_assessment",
                investigation_id=investigation_id,
                user_id=user_id,
                provider="groq",
                model="llama-3.3-70b-versatile",
                prompt_version="1.0.0",
                input_context_summary={"check_id": check_id, "evidence_count": len(evidence_records)},
            ),
        )

        try:
            graph = build_effectiveness_assessment_graph()
            state = {
                "investigation_id": investigation_id,
                "capa_id": capa.id if capa else "",
                "check_id": check_id,
                "user_id": user_id,
                "context": {
                    "capa": {
                        "id": capa.id if capa else "",
                        "title": capa.title if capa else "",
                        "capa_type": capa.capa_type if capa else "",
                        "root_cause_summary": capa.root_cause_summary if capa else "",
                    },
                    "check": {
                        "check_title": check.check_title,
                        "verification_type": check.verification_type,
                        "acceptance_criteria": check.acceptance_criteria,
                        "measurement_method": check.measurement_method,
                        "observation_period_days": check.observation_period_days,
                        "recurrence_observed": check.recurrence_observed,
                    },
                    "evidence": evidence_records,
                },
                "execution_id": exec_record.id,
            }
            final_state = await graph.ainvoke(state)

            if final_state.get("is_failed"):
                err_msg = final_state.get("error_message", "AI effectiveness assessment failed.")
                await ai_execution_repo.record_execution_completion(
                    session,
                    execution_id=exec_record.id,
                    status=AIExecutionStatus.FAILED.value,
                    error_message=err_msg,
                )
                raise ValueError(err_msg)

            summary_payload = {
                "ai_proposal": final_state.get("ai_proposal"),
                "confidence_score": final_state.get("confidence_score"),
                "rationale": final_state.get("rationale"),
                "citations": final_state.get("citations", []),
                "concerns_or_gaps": final_state.get("concerns_or_gaps", []),
                "recommended_human_actions": final_state.get("recommended_human_actions", []),
                "assessed_at": datetime.now(timezone.utc).isoformat(),
            }

            patch_data = {
                "ai_assessment_summary": summary_payload,
                "ai_execution_id": exec_record.id,
            }
            updated = await capa_repo.update_effectiveness_check(session, check_id, patch_data)

            await ai_execution_repo.record_execution_completion(
                session,
                execution_id=exec_record.id,
                status=AIExecutionStatus.COMPLETED.value,
            )

            session.add(
                AuditLog(
                    user_id=user_id,
                    investigation_id=investigation_id,
                    action=AuditAction.EFFECTIVENESS_CHECK_AI_ASSESSED.value,
                    entity_type="effectiveness_check",
                    entity_id=check.id,
                    new_values={"proposal": summary_payload.get("ai_proposal"), "confidence": summary_payload.get("confidence_score")},
                )
            )
            await session.commit()
            return updated

        except Exception as e:
            logger.error(f"Failed in assess_effectiveness_ai: {e}")
            await session.rollback()
            raise

    async def record_effectiveness_result(
        self,
        session: AsyncSession,
        check_id: str,
        user_id: str,
        result: str,
        conclusion: Optional[str] = None,
        recurrence_observed: bool = False,
        reviewer_comments: Optional[str] = None,
    ) -> EffectivenessCheck:
        check = await capa_repo.get_effectiveness_check(session, check_id)
        if not check:
            raise ValueError(f"Effectiveness check {check_id} not found.")

        patch = {
            "result": result,
            "conclusion": conclusion,
            "recurrence_observed": recurrence_observed,
            "reviewer_comments": reviewer_comments,
            "actual_completion_date": datetime.now(timezone.utc),
            "status": EffectivenessStatus.IN_PROGRESS.value,
        }
        updated = await capa_repo.update_effectiveness_check(session, check_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=check.capa.investigation_id if check.capa else None,
                action=AuditAction.EFFECTIVENESS_CHECK_RESULT_RECORDED.value,
                entity_type="effectiveness_check",
                entity_id=check.id,
                new_values={"result": result, "recurrence_observed": recurrence_observed},
            )
        )
        await session.commit()
        return updated

    async def finalize_effectiveness_decision(
        self,
        session: AsyncSession,
        check_id: str,
        user_id: str,
        decision: str,
        decision_reason: str,
    ) -> EffectivenessCheck:
        if not decision_reason or not decision_reason.strip():
            raise ValueError("Documented decision rationale is mandatory for quality verification.")

        check = await capa_repo.get_effectiveness_check(session, check_id)
        if not check:
            raise ValueError(f"Effectiveness check {check_id} not found.")

        # Business Quality Rules:
        # Rule 1: If recurrence was observed, action CANNOT be marked EFFECTIVE
        if decision.upper() == "EFFECTIVE" and check.recurrence_observed:
            raise ValueError(
                "Compliance Violation: An effectiveness check cannot be marked 'EFFECTIVE' when "
                "deviation recurrence was observed. Action must be evaluated as INEFFECTIVE or PARTIALLY_EFFECTIVE."
            )

        # Rule 2: If decision is EFFECTIVE, all CAPA action tasks must be COMPLETED
        if decision.upper() == "EFFECTIVE":
            capa = check.capa
            if capa:
                tasks = await capa_repo.list_tasks(session, capa_id=capa.id)
                non_completed = [t for t in tasks if t.status not in [CAPATaskStatus.COMPLETED.value, "Completed", "COMPLETED"]]
                if non_completed:
                    raise ValueError(
                        f"Cannot mark effectiveness check 'EFFECTIVE': CAPA has {len(non_completed)} "
                        "incomplete action task(s). All implementation tasks must be verified complete first."
                    )

        now = datetime.now(timezone.utc)
        patch = {
            "effectiveness_decision": decision.upper(),
            "decision_reason": decision_reason.strip(),
            "decision_by": user_id,
            "decision_at": now,
            "verified_by": user_id,
            "verified_at": now,
            "status": decision.upper(),
        }
        updated = await capa_repo.update_effectiveness_check(session, check_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=check.capa.investigation_id if check.capa else None,
                action=AuditAction.EFFECTIVENESS_CHECK_DECISION_FINALIZED.value,
                entity_type="effectiveness_check",
                entity_id=check.id,
                new_values={"decision": decision.upper(), "reason": decision_reason},
            )
        )
        await session.commit()
        return updated

    async def reopen_capa(
        self,
        session: AsyncSession,
        capa_id: str,
        user_id: str,
        reason: str,
        new_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> CAPA:
        if not reason or not reason.strip():
            raise ValueError("Documented reason is required to reopen a CAPA plan.")

        capa = await capa_repo.get_capa_detailed(session, capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found.")

        patch = {
            "status": CAPAStatus.IN_PROGRESS.value,
            "approval_comments": f"CAPA Reopened on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}: {reason.strip()}",
        }
        updated = await capa_repo.update_capa(session, capa_id, patch)

        # Create any new corrective tasks specified
        if new_tasks:
            for t_data in new_tasks:
                await self.create_task(session, capa_id, user_id, t_data)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=capa.investigation_id,
                action=AuditAction.CAPA_REOPENED.value,
                entity_type="capa",
                entity_id=capa.id,
                new_values={"status": "IN_PROGRESS", "reopen_reason": reason},
            )
        )
        await session.commit()
        return await capa_repo.get_capa_detailed(session, capa_id)

    async def create_followup_investigation_from_check(
        self,
        session: AsyncSession,
        check_id: str,
        user_id: str,
        justification: str,
        title: Optional[str] = None,
    ) -> str:
        check = await capa_repo.get_effectiveness_check(session, check_id)
        if not check:
            raise ValueError(f"Effectiveness check {check_id} not found.")

        capa = check.capa
        parent_inv = await investigation_repo.get(session, capa.investigation_id) if capa else None
        if not parent_inv:
            raise ValueError("Parent investigation not found.")

        inv_title = title or f"[Follow-up] {parent_inv.title}"
        current_year = datetime.now(timezone.utc).year
        inv_number = await investigation_repo.get_next_investigation_number(session, current_year)

        from app.models.investigation import Investigation
        from app.models.incident import Incident

        followup_inv = Investigation(
            investigation_number=inv_number,
            title=inv_title,
            description=f"Follow-up investigation initiated from failed CAPA {capa.capa_number} (Check: {check.check_title}). Justification: {justification}",
            priority=parent_inv.priority,
            risk_level=parent_inv.risk_level,
            status=InvestigationStatus.INITIATED.value,
            created_by=user_id,
            assigned_to=user_id,
        )
        session.add(followup_inv)
        await session.flush()

        # Replicate basic incident details linked to new investigation
        p_inc_res = await session.execute(select(Incident).where(Incident.investigation_id == parent_inv.id))
        p_inc = p_inc_res.scalar_one_or_none()
        if p_inc:
            f_inc = Incident(
                investigation_id=followup_inv.id,
                api_product_name=p_inc.api_product_name,
                batch_number=p_inc.batch_number,
                manufacturing_stage=p_inc.manufacturing_stage,
                equipment_id=p_inc.equipment_id,
                expected_parameter=p_inc.expected_parameter,
                actual_parameter=p_inc.actual_parameter,
                incident_date=datetime.now(timezone.utc),
                incident_description=f"Deviation recurrence under CAPA {capa.capa_number}. {justification}",
            )
            session.add(f_inc)

        check.followup_investigation_id = followup_inv.id
        session.add(check)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=parent_inv.id,
                action=AuditAction.CAPA_FOLLOWUP_INVESTIGATION_CREATED.value,
                entity_type="effectiveness_check",
                entity_id=check.id,
                new_values={
                    "followup_investigation_id": followup_inv.id,
                    "followup_investigation_number": inv_number,
                    "justification": justification,
                },
            )
        )
        await session.commit()
        return followup_inv.id

    async def validate_capa_closure(
        self, session: AsyncSession, capa_id: str
    ) -> Dict[str, Any]:
        """Validates all regulatory prerequisites required before a CAPA can be formally closed."""
        capa = await capa_repo.get_capa_detailed(session, capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found.")

        tasks = await capa_repo.list_tasks(session, capa_id=capa_id)
        checks = await capa_repo.list_effectiveness_checks(session, capa_id=capa_id)

        blockers = []

        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.status in [CAPATaskStatus.COMPLETED.value, "Completed", "COMPLETED"])
        uncompleted_tasks = [t for t in tasks if t.status not in [CAPATaskStatus.COMPLETED.value, "Completed", "COMPLETED"]]
        if uncompleted_tasks:
            blockers.append(f"{len(uncompleted_tasks)} action task(s) are not verified COMPLETED.")

        total_checks = len(checks)
        effective_checks = sum(1 for c in checks if c.status in [EffectivenessStatus.EFFECTIVE.value, "Effective", "EFFECTIVE"])
        if total_checks == 0:
            blockers.append("No effectiveness verification checks have been planned or scheduled for this CAPA.")
        else:
            non_effective = [c for c in checks if c.status not in [EffectivenessStatus.EFFECTIVE.value, "Effective", "EFFECTIVE"]]
            if non_effective:
                blockers.append(f"{len(non_effective)} effectiveness check(s) have not been confirmed EFFECTIVE.")

        open_gaps_count = 0
        if capa.investigation_id:
            gaps, total_gaps = await evidence_gap_repo.get_by_investigation(
                session, investigation_id=capa.investigation_id, status="OPEN", limit=100
            )
            open_gaps_count = total_gaps
            if open_gaps_count > 0:
                blockers.append(f"Investigation has {open_gaps_count} open evidence gap(s) that must be addressed.")

        is_closable = len(blockers) == 0

        return {
            "is_closable": is_closable,
            "can_close": is_closable,
            "blockers": blockers,
            "completed_tasks_count": completed_tasks,
            "total_tasks_count": total_tasks,
            "effective_checks_count": effective_checks,
            "total_checks_count": total_checks,
            "open_evidence_gaps_count": open_gaps_count,
        }

    async def close_capa(
        self,
        session: AsyncSession,
        capa_id: str,
        user_id: str,
        comments: str,
    ) -> CAPA:
        if not comments or not comments.strip():
            raise ValueError("Quality sign-off comments are mandatory to close a CAPA plan.")

        val_result = await self.validate_capa_closure(session, capa_id)
        if not val_result["is_closable"]:
            blocker_text = "; ".join(val_result["blockers"])
            raise ValueError(f"CAPA cannot be closed due to unmet prerequisites: {blocker_text}")

        capa = await capa_repo.get_capa_detailed(session, capa_id)
        patch = {
            "status": CAPAStatus.CLOSED.value,
            "approval_comments": f"Closed on {datetime.now(timezone.utc).strftime('%Y-%m-%d')}: {comments.strip()}",
        }
        updated = await capa_repo.update_capa(session, capa_id, patch)

        session.add(
            AuditLog(
                user_id=user_id,
                investigation_id=capa.investigation_id,
                action=AuditAction.CAPA_CLOSED.value,
                entity_type="capa",
                entity_id=capa.id,
                new_values={"status": "CLOSED", "comments": comments},
            )
        )
        await session.commit()
        return updated

    # Aliases for lifecycle convenience
    generate_recommendations = generate_capa_recommendations
    submit_review = submit_capa_for_review
    submit_approval = submit_capa_for_approval


capa_service = CAPAService()
