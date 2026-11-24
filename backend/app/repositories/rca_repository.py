import copy
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, desc, func, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
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
from app.models.enums import RCAStatus, CauseStatus, CauseClassification
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

    async def get_by_investigation(
        self, session: AsyncSession, investigation_id: str, skip: int = 0, limit: int = 50
    ) -> List[RCAAnalysis]:
        """Returns all RCA records for an investigation ordered newest first."""
        stmt = (
            select(self.model)
            .where(self.model.investigation_id == investigation_id)
            .order_by(desc(self.model.analysis_version), desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

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
            .order_by(desc(RCAAnalysis.analysis_version), desc(RCAAnalysis.created_at))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_accepted_for_investigation(
        self, session: AsyncSession, investigation_id: str
    ) -> Optional[RCAAnalysis]:
        """Returns the active accepted RCA for an investigation, if one exists."""
        stmt = (
            select(self.model)
            .where(
                self.model.investigation_id == investigation_id,
                self.model.status == RCAStatus.ACCEPTED.value,
            )
            .order_by(desc(self.model.analysis_version), desc(self.model.reviewed_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_latest_version_number(
        self, session: AsyncSession, investigation_id: str
    ) -> int:
        """Returns highest analysis_version number for an investigation."""
        stmt = (
            select(func.max(self.model.analysis_version))
            .where(self.model.investigation_id == investigation_id)
        )
        result = await session.execute(stmt)
        max_ver = result.scalar()
        return int(max_ver or 0)

    async def create_rca_record(
        self,
        session: AsyncSession,
        *,
        investigation_id: str,
        ai_execution_id: Optional[str],
        created_by: Optional[str],
        analysis_method: str,
        analysis_version: int,
        prompt_version: str = "1.0.0",
        problem_statement: Optional[str] = None,
    ) -> RCAAnalysis:
        """Initializes a new RCA record in DRAFT status."""
        db_obj = self.model(
            investigation_id=investigation_id,
            ai_execution_id=ai_execution_id,
            created_by=created_by,
            analysis_method=analysis_method,
            analysis_version=analysis_version,
            prompt_version=prompt_version,
            problem_statement=problem_statement,
            incident_summary=None,
            status=RCAStatus.DRAFT.value,
            five_whys_data=[],
            fishbone_data={},
            root_causes_data=[],
            contributing_factors_data=[],
            rejected_hypotheses_data=[],
            evidence_gaps_data=[],
            summary=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def update_rca_completion(
        self,
        session: AsyncSession,
        *,
        rca_id: str,
        problem_statement: str,
        incident_summary: str,
        five_whys_data: List[Dict[str, Any]],
        fishbone_data: Dict[str, Any],
        root_causes_data: List[Dict[str, Any]],
        contributing_factors_data: List[Dict[str, Any]],
        rejected_hypotheses_data: List[Dict[str, Any]],
        evidence_gaps_data: List[Dict[str, Any]],
        summary: Optional[str],
        status: str,
    ) -> Optional[RCAAnalysis]:
        """Updates RCA with completed LangGraph output using copy.deepcopy and flag_modified."""
        db_obj = await self.get(session, rca_id)
        if not db_obj:
            return None

        db_obj.problem_statement = problem_statement
        db_obj.incident_summary = incident_summary
        db_obj.five_whys_data = copy.deepcopy(five_whys_data)
        db_obj.fishbone_data = copy.deepcopy(fishbone_data)
        db_obj.root_causes_data = copy.deepcopy(root_causes_data)
        db_obj.contributing_factors_data = copy.deepcopy(contributing_factors_data)
        db_obj.rejected_hypotheses_data = copy.deepcopy(rejected_hypotheses_data)
        db_obj.evidence_gaps_data = copy.deepcopy(evidence_gaps_data)
        db_obj.summary = summary
        db_obj.status = status
        db_obj.updated_at = datetime.now(timezone.utc)

        flag_modified(db_obj, "five_whys_data")
        flag_modified(db_obj, "fishbone_data")
        flag_modified(db_obj, "root_causes_data")
        flag_modified(db_obj, "contributing_factors_data")
        flag_modified(db_obj, "rejected_hypotheses_data")
        flag_modified(db_obj, "evidence_gaps_data")

        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def supersede_previous_accepted(
        self, session: AsyncSession, investigation_id: str, current_rca_id: str
    ) -> int:
        """Transitions previously accepted RCA records to SUPERSEDED."""
        stmt = (
            update(self.model)
            .where(
                self.model.investigation_id == investigation_id,
                self.model.id != current_rca_id,
                self.model.status == RCAStatus.ACCEPTED.value,
            )
            .values(
                status=RCAStatus.SUPERSEDED.value,
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount

    async def update_review_status(
        self,
        session: AsyncSession,
        *,
        rca_id: str,
        status: str,
        reviewer_notes: Optional[str] = None,
        reviewed_by: Optional[str] = None,
    ) -> Optional[RCAAnalysis]:
        """Updates RCA review status, notes, and reviewer attribution."""
        db_obj = await self.get(session, rca_id)
        if not db_obj:
            return None

        db_obj.status = status
        if reviewer_notes is not None:
            db_obj.reviewer_notes = reviewer_notes
        if reviewed_by:
            db_obj.reviewed_by = reviewed_by
            db_obj.reviewed_at = datetime.now(timezone.utc)

        db_obj.updated_at = datetime.now(timezone.utc)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

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

    async def sync_relational_child_records(
        self, session: AsyncSession, rca: RCAAnalysis
    ) -> None:
        """
        Synchronizes JSON 5 Whys, Fishbone categories, Root causes, and Evidence gaps
        into relational database entities for relational consistency.
        """
        # 1. Sync 5 Whys
        if rca.five_whys_data:
            await session.execute(
                delete(WhyAnalysisStep).where(WhyAnalysisStep.rca_analysis_id == rca.id)
            )
            for item in rca.five_whys_data:
                db_step = WhyAnalysisStep(
                    rca_analysis_id=rca.id,
                    step_number=item.get("step_number", 1),
                    question=item.get("question", "Why?"),
                    answer=item.get("answer", "Answer"),
                    explanation=item.get("explanation"),
                    confidence_score=float(item.get("confidence", 0.8)),
                    verification_status=item.get("verification_status", "PROPOSED"),
                    assumptions=item.get("assumptions", []),
                    supporting_references=item.get("supporting_references", []),
                    is_root_cause=bool(item.get("is_root_cause", False)),
                )
                session.add(db_step)

        # 2. Sync Fishbone Categories and Causes
        if rca.fishbone_data:
            cat_ids_stmt = select(FishboneCategory.id).where(FishboneCategory.rca_analysis_id == rca.id)
            cat_ids_res = await session.execute(cat_ids_stmt)
            cat_ids = cat_ids_res.scalars().all()
            if cat_ids:
                await session.execute(
                    delete(FishboneCause).where(FishboneCause.category_id.in_(cat_ids))
                )
                await session.execute(
                    delete(FishboneCategory).where(FishboneCategory.rca_analysis_id == rca.id)
                )
            for cat_name, causes_list in rca.fishbone_data.items():
                db_cat = FishboneCategory(rca_analysis_id=rca.id, name=cat_name)
                session.add(db_cat)
                await session.flush()
                for c_item in causes_list:
                    db_cause = FishboneCause(
                        category_id=db_cat.id,
                        cause_title=c_item.get("title"),
                        cause_description=c_item.get("description", ""),
                        confidence_score=float(c_item.get("confidence", 0.8)),
                        verification_status=c_item.get("verification_status", "PROPOSED"),
                        potential_impact=c_item.get("potential_impact"),
                        supporting_references=c_item.get("supporting_references", []),
                        is_significant=bool(c_item.get("classification") == CauseClassification.ROOT_CAUSE.value),
                    )
                    session.add(db_cause)

        # 3. Sync Root Causes
        if rca.root_causes_data:
            await session.execute(
                delete(RootCause).where(RootCause.rca_analysis_id == rca.id)
            )
            for rc_item in rca.root_causes_data:
                db_rc = RootCause(
                    rca_analysis_id=rca.id,
                    title=rc_item.get("title", "Root Cause"),
                    description=rc_item.get("description", ""),
                    category=rc_item.get("category", "Method"),
                    confidence_score=float(rc_item.get("confidence", 0.85)),
                    status="Confirmed" if rc_item.get("human_confirmed") else "Identified",
                    ai_generated=True,
                    human_confirmed=bool(rc_item.get("human_confirmed", False)),
                    supporting_references=rc_item.get("supporting_references", []),
                )
                session.add(db_rc)

        await session.flush()


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
