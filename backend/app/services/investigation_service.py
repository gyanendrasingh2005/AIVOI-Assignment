from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    InvestigationStatus,
    PriorityLevel,
    RiskLevel,
    RoleName,
    AuditAction,
)
from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.user import User
from app.schemas.investigation import (
    InvestigationCreateRequest,
    InvestigationUpdateRequest,
    InvestigationAssignRequest,
    InvestigationTransitionRequest,
    InvestigationListItem,
    InvestigationListResponse,
    InvestigationDetailResponse,
    TimelineEvent,
    InvestigationTimelineResponse,
    DashboardSummaryResponse,
)
from app.core.exceptions import (
    PharmaRCAException,
    EntityNotFoundException,
    ComplianceViolationException,
)
from app.repositories.investigation_repository import investigation_repo, incident_repo
from app.repositories.approval_audit_repository import audit_repo
from app.repositories.user_repository import user_repo
from app.services.lifecycle_service import lifecycle_service
from app.api.deps import verify_investigation_access


class InvestigationService:
    """Enterprise domain service orchestrating pharmaceutical investigation lifecycle, intake, and audit trail."""

    async def create_investigation(
        self,
        session: AsyncSession,
        *,
        user: User,
        create_in: InvestigationCreateRequest,
        ip_address: Optional[str] = None,
    ) -> InvestigationDetailResponse:
        # Determine current discovery year for sequence numbering
        now_utc = datetime.now(timezone.utc)
        year = create_in.incident_date.year if create_in.incident_date else now_utc.year

        # Concurrency-safe atomic number generation
        investigation_number = await investigation_repo.get_next_investigation_number(session, year)

        # Validate assigned investigator if specified
        assigned_user = None
        if create_in.assigned_to:
            assigned_user = await user_repo.get_with_roles(session, create_in.assigned_to)
            if not assigned_user:
                raise EntityNotFoundException("User (Assigned Investigator)", create_in.assigned_to)
            if not assigned_user.is_active:
                raise PharmaRCAException(
                    message="Cannot assign investigation to a suspended or deactivated account.",
                    status_code=400,
                )
            eligible_roles = {
                RoleName.INVESTIGATOR.value,
                RoleName.QA.value,
                RoleName.QA_APPROVER.value,
                RoleName.ADMIN.value,
            }
            user_roles = {r.name for r in assigned_user.roles}
            if not user_roles.intersection(eligible_roles):
                raise PharmaRCAException(
                    message=f"Assigned user must hold an investigation role ({', '.join(eligible_roles)}).",
                    status_code=400,
                )

        # Create master Investigation entity
        investigation = Investigation(
            investigation_number=investigation_number,
            title=create_in.title.strip(),
            description=create_in.description.strip() if create_in.description else None,
            priority=create_in.priority.value,
            risk_level=create_in.risk_level.value,
            status=create_in.status.value,
            created_by=user.id,
            assigned_to=create_in.assigned_to,
        )
        session.add(investigation)
        await session.flush()

        # Create linked Incident intake entity
        incident = Incident(
            investigation_id=investigation.id,
            api_product_name=create_in.api_product_name.strip(),
            batch_number=create_in.batch_number.strip(),
            manufacturing_stage=create_in.manufacturing_stage.strip(),
            incident_date=create_in.incident_date,
            incident_description=create_in.incident_description.strip(),
            equipment_id=create_in.equipment_id.strip() if create_in.equipment_id else None,
            expected_parameter=create_in.expected_parameter.strip() if create_in.expected_parameter else None,
            actual_parameter=create_in.actual_parameter.strip() if create_in.actual_parameter else None,
            immediate_actions=create_in.immediate_actions.strip() if create_in.immediate_actions else None,
            affected_batches=create_in.affected_batches,
            potential_quality_impact=create_in.potential_quality_impact.strip() if create_in.potential_quality_impact else None,
        )
        session.add(incident)
        await session.flush()

        # If created directly in Initiated state, run prerequisites validation
        if create_in.status == InvestigationStatus.INITIATED:
            investigation.incident = incident
            lifecycle_service.validate_prerequisites(InvestigationStatus.INITIATED.value, investigation)

        # Link in-memory relationships for eager serialization
        investigation.creator = user
        investigation.incident = incident
        if assigned_user:
            investigation.assignee = assigned_user

        # Record ALCOA+ contemporaneous creation log
        await audit_repo.log_event(
            session,
            action=AuditAction.CREATE.value,
            entity_type="Investigation",
            entity_id=investigation.id,
            user_id=user.id,
            investigation_id=investigation.id,
            new_values={
                "investigation_number": investigation_number,
                "title": investigation.title,
                "status": investigation.status,
                "priority": investigation.priority,
                "risk_level": investigation.risk_level,
                "api_product_name": incident.api_product_name,
                "batch_number": incident.batch_number,
                "assigned_to": investigation.assigned_to,
            },
        )

        await session.commit()
        return InvestigationDetailResponse.model_validate(investigation)

    async def get_investigation_detail(
        self,
        session: AsyncSession,
        *,
        user: User,
        investigation_id: str,
    ) -> InvestigationDetailResponse:
        investigation = await investigation_repo.get_detailed(session, investigation_id)
        if not investigation:
            raise EntityNotFoundException("Investigation", investigation_id)

        has_access = await verify_investigation_access(investigation, user)
        if not has_access:
            raise PharmaRCAException(
                message="Access denied: You do not have permission to view this investigation record.",
                status_code=403,
            )

        return InvestigationDetailResponse.model_validate(investigation)

    async def list_investigations(
        self,
        session: AsyncSession,
        *,
        user: User,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        risk_level: Optional[str] = None,
        api_product_name: Optional[str] = None,
        manufacturing_stage: Optional[str] = None,
        assigned_to: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> InvestigationListResponse:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        skip = (page - 1) * page_size
        user_roles = {r.name for r in user.roles}
        can_view_all = bool(
            user_roles.intersection({RoleName.ADMIN.value, RoleName.QA.value, RoleName.QA_APPROVER.value})
        )

        items_raw, total = await investigation_repo.get_investigations_paged(
            session,
            skip=skip,
            limit=page_size,
            search=search,
            status=status,
            priority=priority,
            risk_level=risk_level,
            api_product_name=api_product_name,
            manufacturing_stage=manufacturing_stage,
            assigned_to=assigned_to,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order,
            user_filter_id=user.id,
            can_view_all=can_view_all,
        )

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        items = [InvestigationListItem(**row) for row in items_raw]

        return InvestigationListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_investigation(
        self,
        session: AsyncSession,
        *,
        user: User,
        investigation_id: str,
        update_in: InvestigationUpdateRequest,
    ) -> InvestigationDetailResponse:
        investigation = await investigation_repo.get_detailed(session, investigation_id)
        if not investigation:
            raise EntityNotFoundException("Investigation", investigation_id)

        # Verify access & editing authorization
        has_access = await verify_investigation_access(investigation, user)
        if not has_access:
            raise PharmaRCAException(
                message="Access denied: You do not have authorization to edit this investigation.",
                status_code=403,
            )

        # Invariance rule: Closed or Rejected investigations cannot be modified
        if investigation.status in [InvestigationStatus.CLOSED.value, InvestigationStatus.REJECTED.value]:
            raise PharmaRCAException(
                message=f"Cannot modify investigation: Record is in terminal state '{investigation.status}'.",
                status_code=400,
            )

        old_values = {}
        new_values = {}

        # Update Investigation fields
        if update_in.title is not None and update_in.title != investigation.title:
            old_values["title"] = investigation.title
            investigation.title = update_in.title.strip()
            new_values["title"] = investigation.title

        if update_in.description is not None and update_in.description != investigation.description:
            old_values["description"] = investigation.description
            investigation.description = update_in.description.strip()
            new_values["description"] = investigation.description

        if update_in.priority is not None and update_in.priority.value != investigation.priority:
            old_values["priority"] = investigation.priority
            investigation.priority = update_in.priority.value
            new_values["priority"] = investigation.priority

        if update_in.risk_level is not None and update_in.risk_level.value != investigation.risk_level:
            old_values["risk_level"] = investigation.risk_level
            investigation.risk_level = update_in.risk_level.value
            new_values["risk_level"] = investigation.risk_level

        # Update Incident fields
        incident = investigation.incident
        if incident:
            incident_fields = [
                ("api_product_name", update_in.api_product_name),
                ("batch_number", update_in.batch_number),
                ("manufacturing_stage", update_in.manufacturing_stage),
                ("incident_date", update_in.incident_date),
                ("incident_description", update_in.incident_description),
                ("equipment_id", update_in.equipment_id),
                ("expected_parameter", update_in.expected_parameter),
                ("actual_parameter", update_in.actual_parameter),
                ("immediate_actions", update_in.immediate_actions),
                ("affected_batches", update_in.affected_batches),
                ("potential_quality_impact", update_in.potential_quality_impact),
            ]
            for field_name, new_val in incident_fields:
                if new_val is not None:
                    curr_val = getattr(incident, field_name)
                    if curr_val != new_val:
                        old_values[field_name] = curr_val
                        setattr(incident, field_name, new_val)
                        new_values[field_name] = new_val
            session.add(incident)

        session.add(investigation)
        await session.flush()

        if new_values:
            await audit_repo.log_event(
                session,
                action=AuditAction.UPDATE.value,
                entity_type="Investigation",
                entity_id=investigation.id,
                user_id=user.id,
                investigation_id=investigation.id,
                old_values=old_values,
                new_values=new_values,
            )

        await session.commit()
        return InvestigationDetailResponse.model_validate(investigation)

    async def delete_investigation(
        self,
        session: AsyncSession,
        *,
        user: User,
        investigation_id: str,
    ) -> bool:
        investigation = await investigation_repo.get_detailed(session, investigation_id)
        if not investigation:
            raise EntityNotFoundException("Investigation", investigation_id)

        user_roles = {r.name for r in user.roles}
        is_admin = RoleName.ADMIN.value in user_roles
        is_creator = investigation.created_by == user.id

        if not (is_admin or is_creator):
            raise PharmaRCAException(
                message="Only administrators or the authoring creator can delete this record.",
                status_code=403,
            )

        # Regulated deletion constraint
        locked_states = [
            InvestigationStatus.PENDING_APPROVAL.value,
            InvestigationStatus.CAPA_IN_PROGRESS.value,
            InvestigationStatus.EFFECTIVENESS_VERIFICATION.value,
            InvestigationStatus.CLOSED.value,
        ]
        if investigation.status in locked_states:
            raise ComplianceViolationException(
                rule_name="GAMP_LOCKED_INVESTIGATION_DELETION",
                message=f"Cannot delete investigation in state '{investigation.status}'. Regulated quality records must be retained.",
            )

        await audit_repo.log_event(
            session,
            action=AuditAction.DELETE.value,
            entity_type="Investigation",
            entity_id=investigation.id,
            user_id=user.id,
            investigation_id=investigation.id,
            old_values={
                "investigation_number": investigation.investigation_number,
                "title": investigation.title,
                "status": investigation.status,
            },
        )

        await session.delete(investigation)
        await session.commit()
        return True

    async def assign_investigator(
        self,
        session: AsyncSession,
        *,
        user: User,
        investigation_id: str,
        assign_in: InvestigationAssignRequest,
    ) -> InvestigationDetailResponse:
        user_roles = {r.name for r in user.roles}
        can_assign = bool(user_roles.intersection({RoleName.ADMIN.value, RoleName.QA.value}))
        if not can_assign:
            raise PharmaRCAException(
                message="Only QA Personnel or Administrators have authority to assign investigations.",
                status_code=403,
            )

        investigation = await investigation_repo.get_detailed(session, investigation_id)
        if not investigation:
            raise EntityNotFoundException("Investigation", investigation_id)

        if investigation.status in [InvestigationStatus.CLOSED.value, InvestigationStatus.REJECTED.value]:
            raise PharmaRCAException(
                message="Cannot reassign an investigation that has been closed or rejected.",
                status_code=400,
            )

        target_user = await user_repo.get_with_roles(session, assign_in.assigned_to)
        if not target_user:
            raise EntityNotFoundException("User", assign_in.assigned_to)
        if not target_user.is_active:
            raise PharmaRCAException(
                message="Cannot assign an inactive user.",
                status_code=400,
            )

        target_roles = {r.name for r in target_user.roles}
        eligible_roles = {
            RoleName.INVESTIGATOR.value,
            RoleName.QA.value,
            RoleName.QA_APPROVER.value,
            RoleName.ADMIN.value,
        }
        if not target_roles.intersection(eligible_roles):
            raise PharmaRCAException(
                message=f"Assigned user must hold an investigative role ({', '.join(eligible_roles)}).",
                status_code=400,
            )

        old_assignee = investigation.assigned_to
        investigation.assigned_to = target_user.id
        investigation.assignee = target_user
        session.add(investigation)
        await session.flush()

        await audit_repo.log_event(
            session,
            action="ASSIGNMENT_CHANGE",
            entity_type="Investigation",
            entity_id=investigation.id,
            user_id=user.id,
            investigation_id=investigation.id,
            old_values={"assigned_to": old_assignee},
            new_values={
                "assigned_to": target_user.id,
                "assigned_to_name": target_user.full_name,
                "comments": assign_in.comments,
            },
        )

        await session.commit()
        return InvestigationDetailResponse.model_validate(investigation)

    async def submit_investigation(
        self,
        session: AsyncSession,
        *,
        user: User,
        investigation_id: str,
    ) -> InvestigationDetailResponse:
        """Submits a draft investigation to formal Initiated status."""
        investigation = await lifecycle_service.execute_transition(
            session,
            investigation_id=investigation_id,
            target_status=InvestigationStatus.INITIATED.value,
            user=user,
            comments="Investigation submitted for formal QMS intake",
        )
        return InvestigationDetailResponse.model_validate(investigation)

    async def transition_status(
        self,
        session: AsyncSession,
        *,
        user: User,
        investigation_id: str,
        transition_in: InvestigationTransitionRequest,
    ) -> InvestigationDetailResponse:
        """Executes a controlled state transition."""
        investigation = await lifecycle_service.execute_transition(
            session,
            investigation_id=investigation_id,
            target_status=transition_in.target_status.value,
            user=user,
            comments=transition_in.comments,
            reason=transition_in.reason,
        )
        return InvestigationDetailResponse.model_validate(investigation)

    async def get_timeline(
        self,
        session: AsyncSession,
        *,
        user: User,
        investigation_id: str,
    ) -> InvestigationTimelineResponse:
        investigation = await investigation_repo.get_detailed(session, investigation_id)
        if not investigation:
            raise EntityNotFoundException("Investigation", investigation_id)

        has_access = await verify_investigation_access(investigation, user)
        if not has_access:
            raise PharmaRCAException(message="Access denied.", status_code=403)

        logs = await audit_repo.get_by_investigation(session, investigation_id)
        events: List[TimelineEvent] = []

        for log in logs:
            title = log.action.replace("_", " ").title()
            desc = None
            if log.new_values and isinstance(log.new_values, dict):
                if "status" in log.new_values:
                    title = f"Status Changed to '{log.new_values['status']}'"
                    if "comments" in log.new_values and log.new_values["comments"]:
                        desc = log.new_values["comments"]
                    elif "reason" in log.new_values and log.new_values["reason"]:
                        desc = f"Reason: {log.new_values['reason']}"
                elif "assigned_to_name" in log.new_values:
                    title = f"Assigned to {log.new_values['assigned_to_name']}"
                    desc = log.new_values.get("comments")
                elif "title" in log.new_values:
                    title = f"Investigation Created: {log.new_values['title']}"

            user_name = log.user.full_name if log.user else "System / Automated"
            user_email = log.user.email if log.user else None

            events.append(
                TimelineEvent(
                    id=log.id,
                    event_type=log.action,
                    title=title,
                    description=desc,
                    timestamp=log.created_at,
                    user_id=log.user_id,
                    user_name=user_name,
                    user_email=user_email,
                    metadata=log.new_values if isinstance(log.new_values, dict) else None,
                )
            )

        return InvestigationTimelineResponse(
            investigation_id=investigation.id,
            investigation_number=investigation.investigation_number,
            events=events,
        )

    async def get_audit_history(
        self,
        session: AsyncSession,
        *,
        user: User,
        investigation_id: str,
    ) -> List[Dict[str, Any]]:
        investigation = await investigation_repo.get_detailed(session, investigation_id)
        if not investigation:
            raise EntityNotFoundException("Investigation", investigation_id)

        has_access = await verify_investigation_access(investigation, user)
        if not has_access:
            raise PharmaRCAException(message="Access denied.", status_code=403)

        logs = await audit_repo.get_by_investigation(session, investigation_id)
        results = []
        for log in logs:
            results.append({
                "id": log.id,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "user_id": log.user_id,
                "user_name": log.user.full_name if log.user else None,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "created_at": log.created_at,
            })
        return results

    async def get_dashboard_summary(
        self,
        session: AsyncSession,
        *,
        user: User,
    ) -> DashboardSummaryResponse:
        user_roles = {r.name for r in user.roles}
        can_view_all = bool(
            user_roles.intersection({RoleName.ADMIN.value, RoleName.QA.value, RoleName.QA_APPROVER.value})
        )
        summary = await investigation_repo.get_dashboard_summary(
            session, user_filter_id=user.id, can_view_all=can_view_all
        )
        return DashboardSummaryResponse(**summary)

    async def get_dashboard_recent(
        self,
        session: AsyncSession,
        *,
        user: User,
        limit: int = 10,
    ) -> List[InvestigationListItem]:
        user_roles = {r.name for r in user.roles}
        can_view_all = bool(
            user_roles.intersection({RoleName.ADMIN.value, RoleName.QA.value, RoleName.QA_APPROVER.value})
        )
        raw_items = await investigation_repo.get_recent_investigations(
            session, limit=limit, user_filter_id=user.id, can_view_all=can_view_all
        )
        return [InvestigationListItem(**row) for row in raw_items]


investigation_service = InvestigationService()
