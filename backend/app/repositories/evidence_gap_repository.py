from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, desc, func, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence_gap import EvidenceGap
from app.models.enums import EvidenceGapStatus, EvidenceGapPriority, GapCategory, GapDetectionType
from app.schemas.evidence_gap import EvidenceGapCreate, EvidenceGapUpdate
from app.repositories.base import BaseRepository


class EvidenceGapRepository(BaseRepository[EvidenceGap, EvidenceGapCreate, EvidenceGapUpdate]):
    def __init__(self):
        super().__init__(EvidenceGap)

    async def get_by_investigation(
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
        """Returns filtered evidence gaps for an investigation with total count."""
        stmt = (
            select(self.model)
            .options(
                selectinload(self.model.assigned_user),
                selectinload(self.model.resolver_user),
            )
            .where(self.model.investigation_id == investigation_id)
        )
        count_stmt = select(func.count(self.model.id)).where(self.model.investigation_id == investigation_id)

        if category:
            stmt = stmt.where(self.model.category == category)
            count_stmt = count_stmt.where(self.model.category == category)
        if priority:
            stmt = stmt.where(self.model.priority == priority)
            count_stmt = count_stmt.where(self.model.priority == priority)
        if status:
            stmt = stmt.where(self.model.status == status)
            count_stmt = count_stmt.where(self.model.status == status)
        if assigned_to:
            stmt = stmt.where(self.model.assigned_to == assigned_to)
            count_stmt = count_stmt.where(self.model.assigned_to == assigned_to)

        count_res = await session.execute(count_stmt)
        total = count_res.scalar_one()

        stmt = stmt.order_by(desc(self.model.created_at)).offset(skip).limit(limit)
        res = await session.execute(stmt)
        return list(res.scalars().all()), int(total)

    async def get_detailed(self, session: AsyncSession, gap_id: str) -> Optional[EvidenceGap]:
        stmt = (
            select(self.model)
            .options(
                selectinload(self.model.assigned_user),
                selectinload(self.model.resolver_user),
                selectinload(self.model.root_cause),
            )
            .where(self.model.id == gap_id)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def assign_gap(
        self,
        session: AsyncSession,
        *,
        gap_id: str,
        assigned_to: str,
        due_date: Optional[datetime] = None,
    ) -> Optional[EvidenceGap]:
        gap = await self.get(session, gap_id)
        if not gap:
            return None
        gap.assigned_to = assigned_to
        if due_date:
            gap.due_date = due_date
        gap.updated_at = datetime.now(timezone.utc)
        session.add(gap)
        await session.flush()
        await session.refresh(gap)
        return gap

    async def request_evidence(
        self,
        session: AsyncSession,
        *,
        gap_id: str,
        notes: str,
        suggested_source: Optional[str] = None,
    ) -> Optional[EvidenceGap]:
        gap = await self.get(session, gap_id)
        if not gap:
            return None
        gap.status = EvidenceGapStatus.EVIDENCE_REQUESTED.value
        if suggested_source:
            gap.suggested_source = suggested_source
        gap.updated_at = datetime.now(timezone.utc)
        session.add(gap)
        await session.flush()
        await session.refresh(gap)
        return gap

    async def associate_evidence(
        self,
        session: AsyncSession,
        *,
        gap_id: str,
        evidence_ids: List[str],
    ) -> Optional[EvidenceGap]:
        gap = await self.get(session, gap_id)
        if not gap:
            return None
        current = list(gap.associated_evidence_ids or [])
        for eid in evidence_ids:
            if eid not in current:
                current.append(eid)
        gap.associated_evidence_ids = current
        if gap.status == EvidenceGapStatus.EVIDENCE_REQUESTED.value:
            gap.status = EvidenceGapStatus.EVIDENCE_RECEIVED.value
        gap.updated_at = datetime.now(timezone.utc)
        session.add(gap)
        await session.flush()
        await session.refresh(gap)
        return gap

    async def resolve_gap(
        self,
        session: AsyncSession,
        *,
        gap_id: str,
        justification: str,
        resolved_by: str,
        evidence_ids: Optional[List[str]] = None,
    ) -> Optional[EvidenceGap]:
        gap = await self.get(session, gap_id)
        if not gap:
            return None
        gap.status = EvidenceGapStatus.RESOLVED.value
        gap.resolution_justification = justification
        gap.resolved_by = resolved_by
        gap.resolved_at = datetime.now(timezone.utc)
        if evidence_ids:
            current = list(gap.associated_evidence_ids or [])
            for eid in evidence_ids:
                if eid not in current:
                    current.append(eid)
            gap.associated_evidence_ids = current
        gap.updated_at = datetime.now(timezone.utc)
        session.add(gap)
        await session.flush()
        await session.refresh(gap)
        return gap

    async def reject_gap(
        self,
        session: AsyncSession,
        *,
        gap_id: str,
        justification: str,
        resolved_by: str,
    ) -> Optional[EvidenceGap]:
        gap = await self.get(session, gap_id)
        if not gap:
            return None
        gap.status = EvidenceGapStatus.REJECTED.value
        gap.resolution_justification = justification
        gap.resolved_by = resolved_by
        gap.resolved_at = datetime.now(timezone.utc)
        gap.updated_at = datetime.now(timezone.utc)
        session.add(gap)
        await session.flush()
        await session.refresh(gap)
        return gap

    async def waive_gap(
        self,
        session: AsyncSession,
        *,
        gap_id: str,
        justification: str,
        resolved_by: str,
        policy_reference: Optional[str] = None,
    ) -> Optional[EvidenceGap]:
        gap = await self.get(session, gap_id)
        if not gap:
            return None
        gap.status = EvidenceGapStatus.WAIVED_WITH_JUSTIFICATION.value
        reason_text = justification
        if policy_reference:
            reason_text = f"[{policy_reference}] {justification}"
        gap.resolution_justification = reason_text
        gap.resolved_by = resolved_by
        gap.resolved_at = datetime.now(timezone.utc)
        gap.updated_at = datetime.now(timezone.utc)
        session.add(gap)
        await session.flush()
        await session.refresh(gap)
        return gap

    async def reopen_gap(
        self,
        session: AsyncSession,
        *,
        gap_id: str,
        justification: str,
    ) -> Optional[EvidenceGap]:
        gap = await self.get(session, gap_id)
        if not gap:
            return None
        gap.status = EvidenceGapStatus.REOPENED.value
        gap.resolution_justification = f"Reopened: {justification}"
        gap.resolved_by = None
        gap.resolved_at = None
        gap.updated_at = datetime.now(timezone.utc)
        session.add(gap)
        await session.flush()
        await session.refresh(gap)
        return gap


evidence_gap_repo = EvidenceGapRepository()
