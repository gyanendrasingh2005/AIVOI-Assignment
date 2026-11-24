from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rca import (
    RCAAnalysis,
    RootCause,
    ContributingFactor,
    WhyAnalysisStep,
    FishboneCategory,
    FishboneCause,
)
from app.models.evidence_gap import EvidenceGap
from app.schemas.rca import (
    RCAAnalysisCreate,
    RCAAnalysisBase,
    RootCauseCreate,
    RootCauseBase,
    ContributingFactorCreate,
    WhyAnalysisStepCreate,
    FishboneCauseCreate,
)
from app.schemas.evidence_gap import EvidenceGapCreate, EvidenceGapUpdate
from app.repositories.base import BaseRepository


class RCARepository(BaseRepository[RCAAnalysis, RCAAnalysisCreate, RCAAnalysisBase]):
    def __init__(self):
        super().__init__(RCAAnalysis)

    async def get_detailed_by_investigation(
        self, session: AsyncSession, investigation_id: str
    ) -> List[RCAAnalysis]:
        stmt = (
            select(RCAAnalysis)
            .where(RCAAnalysis.investigation_id == investigation_id)
            .options(
                selectinload(RCAAnalysis.root_causes).selectinload(RootCause.contributing_factors),
                selectinload(RCAAnalysis.why_steps),
                selectinload(RCAAnalysis.fishbone_categories).selectinload(FishboneCategory.causes),
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def add_root_cause(
        self, session: AsyncSession, *, rca_id: str, obj_in: RootCauseCreate
    ) -> RootCause:
        db_obj = RootCause(**obj_in.model_dump(), rca_analysis_id=rca_id)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def add_why_step(
        self, session: AsyncSession, *, rca_id: str, obj_in: WhyAnalysisStepCreate
    ) -> WhyAnalysisStep:
        db_obj = WhyAnalysisStep(**obj_in.model_dump(), rca_analysis_id=rca_id)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def add_fishbone_category(
        self, session: AsyncSession, *, rca_id: str, name: str
    ) -> FishboneCategory:
        db_obj = FishboneCategory(rca_analysis_id=rca_id, name=name)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def add_fishbone_cause(
        self, session: AsyncSession, *, category_id: str, obj_in: FishboneCauseCreate
    ) -> FishboneCause:
        db_obj = FishboneCause(**obj_in.model_dump(), category_id=category_id)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj


class EvidenceGapRepository(BaseRepository[EvidenceGap, EvidenceGapCreate, EvidenceGapUpdate]):
    def __init__(self):
        super().__init__(EvidenceGap)

    async def get_by_investigation(
        self, session: AsyncSession, investigation_id: str
    ) -> List[EvidenceGap]:
        stmt = select(EvidenceGap).where(EvidenceGap.investigation_id == investigation_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())


rca_repo = RCARepository()
evidence_gap_repo = EvidenceGapRepository()
