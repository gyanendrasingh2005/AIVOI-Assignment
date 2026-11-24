from typing import Optional, List, Any, Tuple, Dict
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, or_, and_, desc, asc
from sqlalchemy.orm import selectinload, aliased
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation import Investigation, InvestigationCounter
from app.models.incident import Incident
from app.models.user import User
from app.schemas.investigation import InvestigationCreate, InvestigationUpdate
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.repositories.base import BaseRepository


class InvestigationRepository(BaseRepository[Investigation, InvestigationCreate, InvestigationUpdate]):
    def __init__(self):
        super().__init__(Investigation)

    async def get_next_investigation_number(self, session: AsyncSession, year: int) -> str:
        """
        Concurrency-safe generation of unique investigation numbers (INV-YYYY-XXXXX)
        using row-level database locking (with_for_update).
        """
        stmt = (
            select(InvestigationCounter)
            .where(InvestigationCounter.year == year)
            .with_for_update()
        )
        result = await session.execute(stmt)
        counter = result.scalar_one_or_none()

        if not counter:
            counter = InvestigationCounter(year=year, last_value=1)
            session.add(counter)
            await session.flush()
        else:
            counter.last_value += 1
            session.add(counter)
            await session.flush()

        return f"INV-{year}-{counter.last_value:05d}"

    async def get_by_number(self, session: AsyncSession, investigation_number: str) -> Optional[Investigation]:
        stmt = (
            select(Investigation)
            .where(Investigation.investigation_number == investigation_number)
            .options(
                selectinload(Investigation.creator),
                selectinload(Investigation.assignee),
                selectinload(Investigation.incident),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_detailed(self, session: AsyncSession, id: str) -> Optional[Investigation]:
        stmt = (
            select(Investigation)
            .where(Investigation.id == id)
            .options(
                selectinload(Investigation.creator),
                selectinload(Investigation.assignee),
                selectinload(Investigation.incident),
                selectinload(Investigation.documents),
                selectinload(Investigation.evidence),
                selectinload(Investigation.rca_analyses),
                selectinload(Investigation.evidence_gaps),
                selectinload(Investigation.capas),
                selectinload(Investigation.approvals),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_investigations_paged(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
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
        user_filter_id: Optional[str] = None,
        can_view_all: bool = True,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves paginated investigations with full filtering, sorting, and user-role access scoping.
        """
        CreatorUser = aliased(User, name="creator_user")
        AssigneeUser = aliased(User, name="assignee_user")

        stmt = (
            select(
                Investigation,
                Incident.api_product_name,
                Incident.batch_number,
                CreatorUser.full_name.label("creator_name"),
                AssigneeUser.full_name.label("assignee_name"),
            )
            .outerjoin(Incident, Investigation.id == Incident.investigation_id)
            .outerjoin(CreatorUser, Investigation.created_by == CreatorUser.id)
            .outerjoin(AssigneeUser, Investigation.assigned_to == AssigneeUser.id)
        )

        count_stmt = (
            select(func.count(func.distinct(Investigation.id)))
            .outerjoin(Incident, Investigation.id == Incident.investigation_id)
        )

        conditions = []

        # Scoping: if user cannot view all, restrict to creator or assignee
        if not can_view_all and user_filter_id:
            conditions.append(
                or_(
                    Investigation.created_by == user_filter_id,
                    Investigation.assigned_to == user_filter_id,
                )
            )

        # Full-text / substring search across number, title, and batch number
        if search:
            pat = f"%{search.strip()}%"
            conditions.append(
                or_(
                    Investigation.investigation_number.ilike(pat),
                    Investigation.title.ilike(pat),
                    Incident.batch_number.ilike(pat),
                )
            )

        # Granular filters
        if status:
            conditions.append(Investigation.status == status)
        if priority:
            conditions.append(Investigation.priority == priority)
        if risk_level:
            conditions.append(Investigation.risk_level == risk_level)
        if api_product_name:
            conditions.append(Incident.api_product_name.ilike(f"%{api_product_name.strip()}%"))
        if manufacturing_stage:
            conditions.append(Incident.manufacturing_stage.ilike(f"%{manufacturing_stage.strip()}%"))
        if assigned_to:
            conditions.append(Investigation.assigned_to == assigned_to)
        if date_from:
            conditions.append(Investigation.created_at >= date_from)
        if date_to:
            conditions.append(Investigation.created_at <= date_to)

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        # Count total matching rows
        total_res = await session.execute(count_stmt)
        total = total_res.scalar_one() or 0

        # Sorting
        order_col = Investigation.created_at
        if sort_by == "priority":
            order_col = Investigation.priority
        elif sort_by == "title":
            order_col = Investigation.title
        elif sort_by == "updated_at":
            order_col = Investigation.updated_at

        if sort_order.lower() == "asc":
            stmt = stmt.order_by(asc(order_col))
        else:
            stmt = stmt.order_by(desc(order_col))

        stmt = stmt.offset(skip).limit(limit)
        result = await session.execute(stmt)
        rows = result.all()

        items = []
        for inv, prod, batch, creator_name, assignee_name in rows:
            items.append({
                "id": inv.id,
                "investigation_number": inv.investigation_number,
                "title": inv.title,
                "description": inv.description,
                "priority": inv.priority,
                "risk_level": inv.risk_level,
                "status": inv.status,
                "created_by": inv.created_by,
                "assigned_to": inv.assigned_to,
                "created_at": inv.created_at,
                "updated_at": inv.updated_at,
                "closed_at": inv.closed_at,
                "api_product_name": prod,
                "batch_number": batch,
                "creator_name": creator_name,
                "assignee_name": assignee_name,
            })

        return items, total

    async def get_dashboard_summary(
        self,
        session: AsyncSession,
        *,
        user_filter_id: Optional[str] = None,
        can_view_all: bool = True,
    ) -> Dict[str, Any]:
        """
        Computes accurate QMS dashboard KPI metrics using database aggregations.
        """
        conditions = []
        if not can_view_all and user_filter_id:
            conditions.append(
                or_(
                    Investigation.created_by == user_filter_id,
                    Investigation.assigned_to == user_filter_id,
                )
            )

        # Status aggregation
        status_stmt = select(Investigation.status, func.count(Investigation.id))
        if conditions:
            status_stmt = status_stmt.where(*conditions)
        status_stmt = status_stmt.group_by(Investigation.status)
        status_res = await session.execute(status_stmt)
        by_status = dict(status_res.all())

        # Risk level aggregation
        risk_stmt = select(Investigation.risk_level, func.count(Investigation.id))
        if conditions:
            risk_stmt = risk_stmt.where(*conditions)
        risk_stmt = risk_stmt.group_by(Investigation.risk_level)
        risk_res = await session.execute(risk_stmt)
        by_risk_level = dict(risk_res.all())

        # Total count
        total = sum(by_status.values())

        # Terminal statuses
        closed = by_status.get("Closed", 0)
        rejected = by_status.get("Rejected", 0)
        open_count = total - closed - rejected

        # Overdue: active open investigations opened > 30 days ago
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        overdue_stmt = (
            select(func.count(Investigation.id))
            .where(
                Investigation.status.notin_(["Closed", "Rejected"]),
                Investigation.created_at <= thirty_days_ago,
            )
        )
        if conditions:
            overdue_stmt = overdue_stmt.where(*conditions)
        overdue_res = await session.execute(overdue_stmt)
        overdue_count = overdue_res.scalar_one() or 0

        return {
            "total_investigations": total,
            "open_investigations": open_count,
            "draft_investigations": by_status.get("Draft", 0),
            "under_investigation": by_status.get("Under Investigation", 0),
            "under_review": by_status.get("Pending Review", 0),
            "pending_approval": by_status.get("Pending Approval", 0),
            "capa_in_progress": by_status.get("CAPA In Progress", 0),
            "closed_investigations": closed,
            "rejected_investigations": rejected,
            "overdue_investigations": overdue_count,
            "by_risk_level": by_risk_level,
            "by_status": by_status,
        }

    async def get_recent_investigations(
        self,
        session: AsyncSession,
        *,
        limit: int = 10,
        user_filter_id: Optional[str] = None,
        can_view_all: bool = True,
    ) -> List[Dict[str, Any]]:
        items, _ = await self.get_investigations_paged(
            session,
            skip=0,
            limit=limit,
            sort_by="updated_at",
            sort_order="desc",
            user_filter_id=user_filter_id,
            can_view_all=can_view_all,
        )
        return items

    async def update_status(
        self, session: AsyncSession, *, id: str, status: str, closed_at: Optional[datetime] = None
    ) -> Optional[Investigation]:
        investigation = await self.get(session, id)
        if investigation:
            investigation.status = status
            if closed_at:
                investigation.closed_at = closed_at
            elif status == "Closed" and not investigation.closed_at:
                investigation.closed_at = datetime.now(timezone.utc)
            session.add(investigation)
            await session.flush()
            await session.refresh(investigation)
        return investigation


class IncidentRepository(BaseRepository[Incident, IncidentCreate, IncidentUpdate]):
    def __init__(self):
        super().__init__(Incident)

    async def get_by_investigation(self, session: AsyncSession, investigation_id: str) -> Optional[Incident]:
        stmt = select(Incident).where(Incident.investigation_id == investigation_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_batch(self, session: AsyncSession, batch_number: str) -> List[Incident]:
        stmt = select(Incident).where(Incident.batch_number == batch_number)
        result = await session.execute(stmt)
        return list(result.scalars().all())


investigation_repo = InvestigationRepository()
incident_repo = IncidentRepository()
