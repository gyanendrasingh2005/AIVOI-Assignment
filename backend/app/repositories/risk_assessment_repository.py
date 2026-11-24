import copy
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, desc, update
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.risk_assessment import RiskAssessment
from app.models.enums import RiskAssessmentStatus, RiskAssessmentReviewStatus
from app.repositories.base import BaseRepository
from app.schemas.risk_assessment import RiskAssessmentResponse


class RiskAssessmentRepository(BaseRepository[RiskAssessment, RiskAssessmentResponse, RiskAssessmentResponse]):
    """Repository managing persistence, retrieval, and human QA review for Quality Risk Assessments."""

    def __init__(self):
        super().__init__(RiskAssessment)

    async def get_by_investigation(
        self, session: AsyncSession, investigation_id: str, skip: int = 0, limit: int = 50
    ) -> List[RiskAssessment]:
        """Returns all risk assessments for an investigation ordered newest first."""
        stmt = (
            select(self.model)
            .where(self.model.investigation_id == investigation_id)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_for_investigation(
        self, session: AsyncSession, investigation_id: str
    ) -> Optional[RiskAssessment]:
        """Returns the currently active (accepted) risk assessment for an investigation, if any."""
        stmt = (
            select(self.model)
            .where(
                self.model.investigation_id == investigation_id,
                self.model.review_status == RiskAssessmentReviewStatus.ACCEPTED.value,
            )
            .order_by(desc(self.model.reviewed_at), desc(self.model.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def create_assessment_record(
        self,
        session: AsyncSession,
        *,
        investigation_id: str,
        ai_execution_id: Optional[str],
        created_by: Optional[str],
        framework_version: str,
        incident_snapshot: Dict[str, Any],
    ) -> RiskAssessment:
        """Initializes a new RiskAssessment record in PENDING state."""
        db_obj = self.model(
            investigation_id=investigation_id,
            ai_execution_id=ai_execution_id,
            created_by=created_by,
            framework_version=framework_version,
            incident_snapshot=copy.deepcopy(incident_snapshot),
            quality_impact={},
            patient_impact={},
            batch_impact={},
            process_impact={},
            equipment_impact={},
            data_integrity_impact={},
            severity="Undetermined",
            likelihood="Undetermined",
            detectability=None,
            overall_risk="Undetermined",
            risk_rationale="Assessment initialized, pending execution.",
            urgency_recommendation="Additional Information Required",
            supporting_references=[],
            missing_information=[],
            conflicting_evidence=[],
            uncertainty_notes=None,
            confidence_score=0.0,
            status=RiskAssessmentStatus.PENDING.value,
            review_status=RiskAssessmentReviewStatus.PENDING_REVIEW.value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def update_assessment_completion(
        self,
        session: AsyncSession,
        *,
        assessment_id: str,
        quality_impact: Dict[str, Any],
        patient_impact: Dict[str, Any],
        batch_impact: Dict[str, Any],
        process_impact: Dict[str, Any],
        equipment_impact: Dict[str, Any],
        data_integrity_impact: Dict[str, Any],
        severity: str,
        likelihood: str,
        detectability: Optional[str],
        overall_risk: str,
        risk_rationale: str,
        urgency_recommendation: str,
        supporting_references: List[Dict[str, Any]],
        missing_information: List[Dict[str, Any]],
        conflicting_evidence: List[Dict[str, Any]],
        uncertainty_notes: Optional[str],
        confidence_score: float,
        status: str,
    ) -> Optional[RiskAssessment]:
        """Updates assessment with completed LangGraph evaluation output."""
        db_obj = await self.get(session, assessment_id)
        if not db_obj:
            return None

        db_obj.quality_impact = copy.deepcopy(quality_impact)
        db_obj.patient_impact = copy.deepcopy(patient_impact)
        db_obj.batch_impact = copy.deepcopy(batch_impact)
        db_obj.process_impact = copy.deepcopy(process_impact)
        db_obj.equipment_impact = copy.deepcopy(equipment_impact)
        db_obj.data_integrity_impact = copy.deepcopy(data_integrity_impact)

        db_obj.severity = severity
        db_obj.likelihood = likelihood
        db_obj.detectability = detectability
        db_obj.overall_risk = overall_risk
        db_obj.risk_rationale = risk_rationale
        db_obj.urgency_recommendation = urgency_recommendation

        db_obj.supporting_references = copy.deepcopy(supporting_references)
        db_obj.missing_information = copy.deepcopy(missing_information)
        db_obj.conflicting_evidence = copy.deepcopy(conflicting_evidence)
        db_obj.uncertainty_notes = uncertainty_notes
        db_obj.confidence_score = confidence_score
        db_obj.status = status
        db_obj.updated_at = datetime.now(timezone.utc)

        flag_modified(db_obj, "quality_impact")
        flag_modified(db_obj, "patient_impact")
        flag_modified(db_obj, "batch_impact")
        flag_modified(db_obj, "process_impact")
        flag_modified(db_obj, "equipment_impact")
        flag_modified(db_obj, "data_integrity_impact")
        flag_modified(db_obj, "supporting_references")
        flag_modified(db_obj, "missing_information")
        flag_modified(db_obj, "conflicting_evidence")

        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def supersede_previous_accepted(
        self, session: AsyncSession, investigation_id: str, current_assessment_id: str
    ) -> int:
        """
        Transitions previously accepted risk assessments for this investigation to SUPERSEDED.
        Preserves complete historical audit trail while ensuring single active risk source of truth.
        """
        stmt = (
            update(self.model)
            .where(
                self.model.investigation_id == investigation_id,
                self.model.id != current_assessment_id,
                self.model.review_status == RiskAssessmentReviewStatus.ACCEPTED.value,
            )
            .values(
                review_status=RiskAssessmentReviewStatus.SUPERSEDED.value,
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
        assessment_id: str,
        review_status: str,
        reviewer_notes: Optional[str] = None,
        reviewed_by: Optional[str] = None,
        overall_risk_override: Optional[str] = None,
        severity_override: Optional[str] = None,
        likelihood_override: Optional[str] = None,
    ) -> Optional[RiskAssessment]:
        """Records QA reviewer decision, notes, and optional field overrides."""
        db_obj = await self.get(session, assessment_id)
        if not db_obj:
            return None

        db_obj.review_status = review_status
        if reviewer_notes is not None:
            db_obj.reviewer_notes = reviewer_notes
        if reviewed_by:
            db_obj.reviewed_by = reviewed_by
            db_obj.reviewed_at = datetime.now(timezone.utc)

        if overall_risk_override:
            db_obj.overall_risk = overall_risk_override
        if severity_override:
            db_obj.severity = severity_override
        if likelihood_override:
            db_obj.likelihood = likelihood_override

        db_obj.updated_at = datetime.now(timezone.utc)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj


risk_assessment_repo = RiskAssessmentRepository()
