from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, ForeignKey, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import CompletenessOverallStatus


class CompletenessAssessment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Persisted record of an AI-powered investigation completeness assessment
    evaluating 11 critical GMP investigation dimensions.
    """

    __tablename__ = "completeness_assessments"

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    overall_status: Mapped[str] = mapped_column(
        String(30),
        default=CompletenessOverallStatus.UNDETERMINED.value,
        nullable=False,
        index=True,
    )
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 11-dimension breakdown
    dimension_results: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Aggregate metric counters
    critical_unresolved_gaps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    high_priority_unresolved_gaps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_unresolved_gaps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conflicting_evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unverified_causal_claims_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_reviews_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Actionable guidance
    recommended_activities: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    requirement_profile_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)

    # Lineage & Attributions
    ai_execution_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("ai_executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="completeness_assessments",
    )
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
    )
    ai_execution: Mapped[Optional["AIExecution"]] = relationship(
        "AIExecution",
        foreign_keys=[ai_execution_id],
    )
