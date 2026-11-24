from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.capa import CAPA, CAPATask, EffectivenessCheck
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

    async def get_detailed_by_investigation(
        self, session: AsyncSession, investigation_id: str
    ) -> List[CAPA]:
        stmt = (
            select(CAPA)
            .where(CAPA.investigation_id == investigation_id)
            .options(
                selectinload(CAPA.tasks),
                selectinload(CAPA.effectiveness_checks),
                selectinload(CAPA.assignee),
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def add_task(
        self, session: AsyncSession, *, capa_id: str, obj_in: CAPATaskCreate
    ) -> CAPATask:
        db_obj = CAPATask(**obj_in.model_dump(), capa_id=capa_id)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

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


capa_repo = CAPARepository()
