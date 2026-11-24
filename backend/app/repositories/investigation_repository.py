from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation import Investigation
from app.models.incident import Incident
from app.schemas.investigation import InvestigationCreate, InvestigationUpdate
from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.repositories.base import BaseRepository


class InvestigationRepository(BaseRepository[Investigation, InvestigationCreate, InvestigationUpdate]):
    def __init__(self):
        super().__init__(Investigation)

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
