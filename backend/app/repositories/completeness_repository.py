from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.completeness import CompletenessAssessment
from app.repositories.base import BaseRepository
from pydantic import BaseModel


class CompletenessAssessmentDummySchema(BaseModel):
    pass


class CompletenessAssessmentRepository(
    BaseRepository[CompletenessAssessment, CompletenessAssessmentDummySchema, CompletenessAssessmentDummySchema]
):
    def __init__(self):
        super().__init__(CompletenessAssessment)

    async def get_latest_for_investigation(
        self, session: AsyncSession, investigation_id: str
    ) -> Optional[CompletenessAssessment]:
        """Returns the most recent completeness assessment for an investigation."""
        stmt = (
            select(self.model)
            .options(selectinload(self.model.creator))
            .where(self.model.investigation_id == investigation_id)
            .order_by(desc(self.model.assessment_version), desc(self.model.created_at))
            .limit(1)
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_history_for_investigation(
        self, session: AsyncSession, investigation_id: str, limit: int = 50
    ) -> List[CompletenessAssessment]:
        """Returns historical completeness assessment versions newest first."""
        stmt = (
            select(self.model)
            .where(self.model.investigation_id == investigation_id)
            .order_by(desc(self.model.assessment_version), desc(self.model.created_at))
            .limit(limit)
        )
        res = await session.execute(stmt)
        return list(res.scalars().all())

    async def get_latest_version_number(
        self, session: AsyncSession, investigation_id: str
    ) -> int:
        stmt = (
            select(func.max(self.model.assessment_version))
            .where(self.model.investigation_id == investigation_id)
        )
        res = await session.execute(stmt)
        val = res.scalar()
        return int(val or 0)

    async def create_assessment(
        self,
        session: AsyncSession,
        *,
        investigation_id: str,
        assessment_version: int,
        overall_status: str,
        completeness_score: float,
        dimension_results: List[Dict[str, Any]],
        critical_unresolved_gaps: int,
        high_priority_unresolved_gaps: int,
        total_unresolved_gaps: int,
        conflicting_evidence_count: int,
        unverified_causal_claims_count: int,
        pending_reviews_count: int,
        recommended_activities: List[str],
        requirement_profile_version: str = "1.0.0",
        summary: Optional[str] = None,
        ai_execution_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> CompletenessAssessment:
        db_obj = self.model(
            investigation_id=investigation_id,
            assessment_version=assessment_version,
            overall_status=overall_status,
            completeness_score=completeness_score,
            summary=summary,
            dimension_results=dimension_results,
            critical_unresolved_gaps=critical_unresolved_gaps,
            high_priority_unresolved_gaps=high_priority_unresolved_gaps,
            total_unresolved_gaps=total_unresolved_gaps,
            conflicting_evidence_count=conflicting_evidence_count,
            unverified_causal_claims_count=unverified_causal_claims_count,
            pending_reviews_count=pending_reviews_count,
            recommended_activities=recommended_activities,
            requirement_profile_version=requirement_profile_version,
            ai_execution_id=ai_execution_id,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj


completeness_repo = CompletenessAssessmentRepository()
