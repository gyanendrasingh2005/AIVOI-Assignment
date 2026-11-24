from typing import Optional, Set, Dict, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import InvestigationStatus, RoleName, AuditAction
from app.models.investigation import Investigation
from app.models.user import User
from app.core.exceptions import PharmaRCAException, ComplianceViolationException
from app.repositories.investigation_repository import investigation_repo
from app.repositories.approval_audit_repository import audit_repo


# Centralized QMS Lifecycle State Machine Transition Graph
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    InvestigationStatus.DRAFT.value: {
        InvestigationStatus.INITIATED.value,
    },
    InvestigationStatus.INITIATED.value: {
        InvestigationStatus.UNDER_INVESTIGATION.value,
        InvestigationStatus.REJECTED.value,
    },
    InvestigationStatus.UNDER_INVESTIGATION.value: {
        InvestigationStatus.RCA_IN_PROGRESS.value,
        InvestigationStatus.REJECTED.value,
    },
    InvestigationStatus.RCA_IN_PROGRESS.value: {
        InvestigationStatus.PENDING_REVIEW.value,
    },
    InvestigationStatus.PENDING_REVIEW.value: {
        InvestigationStatus.UNDER_INVESTIGATION.value,  # Rework / additional investigation requested
        InvestigationStatus.PENDING_APPROVAL.value,     # Quality review verified
        InvestigationStatus.REJECTED.value,
    },
    InvestigationStatus.PENDING_APPROVAL.value: {
        InvestigationStatus.PENDING_REVIEW.value,      # Approver sends back for QA clarification
        InvestigationStatus.CAPA_IN_PROGRESS.value,    # 21 CFR Part 11 Approval granted
        InvestigationStatus.REJECTED.value,
    },
    InvestigationStatus.CAPA_IN_PROGRESS.value: {
        InvestigationStatus.EFFECTIVENESS_VERIFICATION.value,
    },
    InvestigationStatus.EFFECTIVENESS_VERIFICATION.value: {
        InvestigationStatus.CLOSED.value,              # Final QMS closure
        InvestigationStatus.CAPA_IN_PROGRESS.value,    # Effectiveness criteria failed, more CAPA needed
    },
    InvestigationStatus.CLOSED.value: set(),           # Terminal state
    InvestigationStatus.REJECTED.value: set(),         # Terminal state
}


class InvestigationLifecycleService:
    """
    Centralized regulatory quality state machine enforcing GAMP 5 and 21 CFR Part 11
    transition criteria across the investigation lifecycle.
    """

    def validate_transition_path(
        self, current_status: str, target_status: str
    ) -> None:
        """Verifies if the target status is a valid successor in the state machine."""
        allowed = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise PharmaRCAException(
                message=(
                    f"Invalid status transition from '{current_status}' to '{target_status}'. "
                    f"Allowed target states: {list(allowed) if allowed else 'None (Terminal state)'}."
                ),
                status_code=400,
                details={
                    "current_status": current_status,
                    "target_status": target_status,
                    "allowed_transitions": list(allowed),
                },
            )

    def validate_role_authorization(
        self,
        current_status: str,
        target_status: str,
        user: User,
        investigation: Investigation,
    ) -> None:
        """
        Enforces pharmaceutical role authorization rules for status transitions.
        """
        user_roles = {r.name for r in user.roles}
        is_admin = RoleName.ADMIN.value in user_roles
        is_qa = RoleName.QA.value in user_roles
        is_approver = RoleName.QA_APPROVER.value in user_roles
        is_owner = investigation.created_by == user.id or investigation.assigned_to == user.id

        # 1. Approval stage transitions (Pending Approval -> CAPA In Progress or Closed)
        if target_status in [InvestigationStatus.CAPA_IN_PROGRESS.value, InvestigationStatus.CLOSED.value]:
            if not (is_admin or is_approver):
                raise ComplianceViolationException(
                    rule_name="21_CFR_PART_11_APPROVAL_AUTHORITY",
                    message="Only authorized QA Approvers or Quality Administrators can grant formal investigation approval or closure.",
                )

        # 2. Submission to QA Review
        if target_status == InvestigationStatus.PENDING_REVIEW.value:
            if not (is_admin or is_qa or is_owner):
                raise PharmaRCAException(
                    message="Only the designated investigator, QA, or Admin can submit for quality review.",
                    status_code=403,
                )

        # 3. Submission to QA Approver
        if target_status == InvestigationStatus.PENDING_APPROVAL.value:
            if not (is_admin or is_qa):
                raise PharmaRCAException(
                    message="Only Quality Assurance personnel or Administrators can advance investigations to final Approval.",
                    status_code=403,
                )

        # 4. Rejection authority
        if target_status == InvestigationStatus.REJECTED.value:
            if not (is_admin or is_qa or is_approver):
                raise PharmaRCAException(
                    message="Only QA, QA Approvers, or Administrators have authority to reject investigations.",
                    status_code=403,
                )

    def validate_prerequisites(
        self,
        target_status: str,
        investigation: Investigation,
        reason: Optional[str] = None,
    ) -> None:
        """
        Ensures all documentary and quality prerequisites are satisfied before state entry.
        """
        # Rejection requires documentation
        if target_status == InvestigationStatus.REJECTED.value and not reason:
            raise PharmaRCAException(
                message="A documented justification/reason is mandatory when rejecting an investigation.",
                status_code=422,
                details={"field": "reason"},
            )

        # Initiation requires incident data
        if target_status == InvestigationStatus.INITIATED.value:
            if not investigation.title or len(investigation.title.strip()) < 5:
                raise PharmaRCAException(
                    message="Investigation title must be at least 5 characters long.",
                    status_code=422,
                )
            incident = investigation.incident
            if not incident:
                raise PharmaRCAException(
                    message="Cannot initiate investigation: Incident intake data is missing.",
                    status_code=422,
                )
            if not incident.api_product_name or not incident.batch_number:
                raise PharmaRCAException(
                    message="API product name and batch number are mandatory before initiation.",
                    status_code=422,
                )

    async def execute_transition(
        self,
        session: AsyncSession,
        *,
        investigation_id: str,
        target_status: str,
        user: User,
        comments: Optional[str] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Investigation:
        """
        Executes an audited state transition within an atomic transaction.
        """
        investigation = await investigation_repo.get_detailed(session, investigation_id)
        if not investigation:
            raise PharmaRCAException(
                message=f"Investigation '{investigation_id}' not found.",
                status_code=404,
            )

        current_status = investigation.status

        # 1. Validate state path
        self.validate_transition_path(current_status, target_status)

        # 2. Validate role authorization
        self.validate_role_authorization(current_status, target_status, user, investigation)

        # 3. Validate prerequisites
        self.validate_prerequisites(target_status, investigation, reason)

        # 4. Apply transition
        old_status = investigation.status
        investigation.status = target_status
        now = datetime.now(timezone.utc)
        if target_status in [InvestigationStatus.CLOSED.value, InvestigationStatus.REJECTED.value]:
            investigation.closed_at = now

        session.add(investigation)
        await session.flush()

        # 5. Record ALCOA+ Audit Log
        await audit_repo.log_event(
            session,
            action=AuditAction.STATUS_CHANGE.value,
            entity_type="Investigation",
            entity_id=investigation.id,
            user_id=user.id,
            investigation_id=investigation.id,
            old_values={"status": old_status},
            new_values={
                "status": target_status,
                "comments": comments,
                "reason": reason,
                "transition_timestamp": now.isoformat(),
            },
        )

        await session.commit()
        return await investigation_repo.get_detailed(session, investigation.id) or investigation


lifecycle_service = InvestigationLifecycleService()
