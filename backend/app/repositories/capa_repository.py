from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capa import CAPA, CAPATask, EffectivenessCheck, CAPARecommendation
from app.schemas.capa import (
    CAPACreate,
    CAPAUpdate,
    CAPATaskCreate,
    EffectivenessCheckCreate,
)
from app.repositories.base import BaseRepository


class CAPARepository(BaseRepository[CAPA, CAPACreate, CAPAUpdate]):
    def __init__(self):
        super().__init__(CAPA)

    # ---------------------------------------------------------
    # Recommendation Operations
    # ---------------------------------------------------------

    async def create_recommendations(
        self, session: AsyncSession, items: List[CAPARecommendation]
    ) -> List[CAPARecommendation]:
        session.add_all(items)
        await session.flush()
        for item in items:
            await session.refresh(item)
        return items

    async def get_recommendation(
        self, session: AsyncSession, recommendation_id: str
    ) -> Optional[CAPARecommendation]:
        stmt = (
            select(CAPARecommendation)
            .where(CAPARecommendation.id == recommendation_id)
            .options(
                selectinload(CAPARecommendation.reviewer),
                selectinload(CAPARecommendation.root_cause),
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_recommendations(
        self,
        session: AsyncSession,
        investigation_id: str,
        status: Optional[str] = None,
        action_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[CAPARecommendation], int]:
        filters = [CAPARecommendation.investigation_id == investigation_id]
        if status:
            filters.append(CAPARecommendation.status == status)
        if action_type:
            filters.append(func.upper(CAPARecommendation.action_type) == action_type.upper())

        # Count
        count_stmt = select(func.count(CAPARecommendation.id)).where(and_(*filters))
        count_res = await session.execute(count_stmt)
        total = count_res.scalar() or 0

        # Query items
        stmt = (
            select(CAPARecommendation)
            .where(and_(*filters))
            .options(
                selectinload(CAPARecommendation.reviewer),
                selectinload(CAPARecommendation.root_cause),
            )
            .order_by(CAPARecommendation.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all()), total

    async def update_recommendation(
        self,
        session: AsyncSession,
        recommendation_id: str,
        patch_data: Dict[str, Any],
    ) -> Optional[CAPARecommendation]:
        rec = await self.get_recommendation(session, recommendation_id)
        if not rec:
            return None
        for key, value in patch_data.items():
            if hasattr(rec, key):
                setattr(rec, key, value)
        rec.updated_at = datetime.now(timezone.utc)
        session.add(rec)
        await session.flush()
        await session.refresh(rec)
        return rec

    # ---------------------------------------------------------
    # CAPA Plan Operations
    # ---------------------------------------------------------

    async def get_detailed_by_investigation(
        self, session: AsyncSession, investigation_id: str
    ) -> List[CAPA]:
        stmt = (
            select(CAPA)
            .where(CAPA.investigation_id == investigation_id)
            .options(
                selectinload(CAPA.tasks).selectinload(CAPATask.assignee),
                selectinload(CAPA.tasks).selectinload(CAPATask.reviewer),
                selectinload(CAPA.effectiveness_checks),
                selectinload(CAPA.assignee),
                selectinload(CAPA.approver),
                selectinload(CAPA.root_cause),
            )
            .order_by(CAPA.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_capa_detailed(
        self, session: AsyncSession, capa_id: str
    ) -> Optional[CAPA]:
        stmt = (
            select(CAPA)
            .where(CAPA.id == capa_id)
            .options(
                selectinload(CAPA.tasks).selectinload(CAPATask.assignee),
                selectinload(CAPA.tasks).selectinload(CAPATask.reviewer),
                selectinload(CAPA.effectiveness_checks),
                selectinload(CAPA.assignee),
                selectinload(CAPA.approver),
                selectinload(CAPA.root_cause),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_number(
        self, session: AsyncSession, capa_number: str
    ) -> Optional[CAPA]:
        stmt = (
            select(CAPA)
            .where(CAPA.capa_number == capa_number)
            .options(
                selectinload(CAPA.tasks),
                selectinload(CAPA.effectiveness_checks),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_capas(
        self,
        session: AsyncSession,
        investigation_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[CAPA], int]:
        filters = [CAPA.investigation_id == investigation_id]
        if status:
            filters.append(func.upper(CAPA.status) == status.upper())
        if priority:
            filters.append(func.upper(CAPA.priority) == priority.upper())

        count_stmt = select(func.count(CAPA.id)).where(and_(*filters))
        count_res = await session.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            select(CAPA)
            .where(and_(*filters))
            .options(
                selectinload(CAPA.tasks).selectinload(CAPATask.assignee),
                selectinload(CAPA.tasks).selectinload(CAPATask.reviewer),
                selectinload(CAPA.effectiveness_checks),
                selectinload(CAPA.assignee),
                selectinload(CAPA.approver),
                selectinload(CAPA.root_cause),
            )
            .order_by(CAPA.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all()), total

    async def update_capa(
        self, session: AsyncSession, capa_id: str, patch_data: Dict[str, Any]
    ) -> Optional[CAPA]:
        capa = await self.get_capa_detailed(session, capa_id)
        if not capa:
            return None
        for key, value in patch_data.items():
            if hasattr(capa, key):
                setattr(capa, key, value)
        capa.updated_at = datetime.now(timezone.utc)
        session.add(capa)
        await session.flush()
        await session.refresh(capa)
        return capa

    async def generate_next_capa_number(
        self, session: AsyncSession, investigation_id: str
    ) -> str:
        current_year = datetime.now(timezone.utc).year
        prefix = f"CAPA-{current_year}-"
        stmt = (
            select(func.count(CAPA.id))
            .where(CAPA.capa_number.like(f"{prefix}%"))
        )
        res = await session.execute(stmt)
        count = (res.scalar() or 0) + 1
        return f"{prefix}{count:04d}"

    # ---------------------------------------------------------
    # CAPA Task Operations
    # ---------------------------------------------------------

    async def add_task(
        self, session: AsyncSession, *, capa_id: str, obj_in: CAPATaskCreate
    ) -> CAPATask:
        db_obj = CAPATask(**obj_in.model_dump(), capa_id=capa_id)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def get_task(
        self, session: AsyncSession, task_id: str
    ) -> Optional[CAPATask]:
        stmt = (
            select(CAPATask)
            .where(CAPATask.id == task_id)
            .options(
                selectinload(CAPATask.assignee),
                selectinload(CAPATask.reviewer),
                selectinload(CAPATask.capa),
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_tasks(
        self,
        session: AsyncSession,
        capa_id: str,
        status: Optional[str] = None,
    ) -> List[CAPATask]:
        filters = [CAPATask.capa_id == capa_id]
        if status:
            filters.append(func.upper(CAPATask.status) == status.upper())

        stmt = (
            select(CAPATask)
            .where(and_(*filters))
            .options(
                selectinload(CAPATask.assignee),
                selectinload(CAPATask.reviewer),
            )
            .order_by(CAPATask.created_at.asc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def update_task(
        self, session: AsyncSession, task_id: str, patch_data: Dict[str, Any]
    ) -> Optional[CAPATask]:
        task = await self.get_task(session, task_id)
        if not task:
            return None
        for key, value in patch_data.items():
            if hasattr(task, key):
                setattr(task, key, value)
        task.updated_at = datetime.now(timezone.utc)
        session.add(task)
        await session.flush()
        await session.refresh(task)
        return task

    async def complete_task(
        self, session: AsyncSession, *, task_id: str, notes: Optional[str] = None
    ) -> Optional[CAPATask]:
        stmt = select(CAPATask).where(CAPATask.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()
        if task:
            task.status = "Completed"
            task.completion_notes = notes
            task.completed_at = datetime.now(timezone.utc)
            session.add(task)
            await session.flush()
            await session.refresh(task)
        return task

    async def add_effectiveness_check(
        self, session: AsyncSession, *, capa_id: str, obj_in: EffectivenessCheckCreate
    ) -> EffectivenessCheck:
        db_obj = EffectivenessCheck(**obj_in.model_dump(), capa_id=capa_id)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def get_effectiveness_check(
        self, session: AsyncSession, check_id: str
    ) -> Optional[EffectivenessCheck]:
        stmt = (
            select(EffectivenessCheck)
            .where(EffectivenessCheck.id == check_id)
            .options(
                selectinload(EffectivenessCheck.capa),
                selectinload(EffectivenessCheck.verifier),
                selectinload(EffectivenessCheck.responsible_reviewer),
                selectinload(EffectivenessCheck.decision_maker),
                selectinload(EffectivenessCheck.followup_investigation),
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_effectiveness_checks(
        self,
        session: AsyncSession,
        capa_id: str,
        status: Optional[str] = None,
    ) -> List[EffectivenessCheck]:
        filters = [EffectivenessCheck.capa_id == capa_id]
        if status:
            filters.append(func.upper(EffectivenessCheck.status) == status.upper())

        stmt = (
            select(EffectivenessCheck)
            .where(and_(*filters))
            .options(
                selectinload(EffectivenessCheck.verifier),
                selectinload(EffectivenessCheck.responsible_reviewer),
                selectinload(EffectivenessCheck.decision_maker),
            )
            .order_by(EffectivenessCheck.created_at.asc())
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def update_effectiveness_check(
        self, session: AsyncSession, check_id: str, patch_data: Dict[str, Any]
    ) -> Optional[EffectivenessCheck]:
        check = await self.get_effectiveness_check(session, check_id)
        if not check:
            return None
        for key, value in patch_data.items():
            if hasattr(check, key):
                setattr(check, key, value)
        check.updated_at = datetime.now(timezone.utc)
        session.add(check)
        await session.flush()
        await session.refresh(check)
        return check

    async def delete_effectiveness_check(
        self, session: AsyncSession, check_id: str
    ) -> bool:
        check = await self.get_effectiveness_check(session, check_id)
        if not check:
            return False
        await session.delete(check)
        await session.flush()
        return True


capa_repo = CAPARepository()
