from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import (
    CAPAType,
    CAPAStatus,
    PriorityLevel,
    CAPATaskStatus,
    EffectivenessStatus,
    CAPARecommendationStatus,
)


class CAPARecommendation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    AI-generated or human-added CAPA recommendation requiring review and acceptance.
    """

    __tablename__ = "capa_recommendations"

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ai_execution_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("ai_executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    recommendation_title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str] = mapped_column(
        String(30),
        default="CORRECTIVE",
        nullable=False,
    )  # CORRECTIVE / PREVENTIVE
    root_cause_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("root_causes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    root_cause_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contributing_factor_ids: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_gap_ids: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    supporting_references: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    expected_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    recurrence_risk_addressed: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20),
        default="MEDIUM",
        nullable=False,
    )
    suggested_department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    suggested_role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    suggested_target_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    implementation_steps: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    completion_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    required_completion_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    implementation_risks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_provisional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uncertainty_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default=CAPARecommendationStatus.PENDING_REVIEW.value,
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_capa_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("capas.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="capa_recommendations",
    )
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by])
    root_cause: Mapped[Optional["RootCause"]] = relationship("RootCause")
    capa: Mapped[Optional["CAPA"]] = relationship("CAPA", back_populates="recommendations")


class CAPA(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Corrective and Preventive Action plan conforming to ICH Q10 guidelines."""

    __tablename__ = "capas"

    capa_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )
    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rca_analysis_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("rca_analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    root_cause_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("root_causes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    capa_type: Mapped[str] = mapped_column(
        String(20),
        default=CAPAType.CORRECTIVE.value,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    problem_statement: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    root_cause_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    corrective_action_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preventive_action_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20),
        default=PriorityLevel.MEDIUM.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default=CAPAStatus.DRAFT.value,
        nullable=False,
    )
    responsible_department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    initiated_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    approval_status: Mapped[Optional[str]] = mapped_column(
        String(30),
        default="DRAFT",
        nullable=True,
    )
    approval_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    supporting_references: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="capas",
    )
    root_cause: Mapped[Optional["RootCause"]] = relationship(
        "RootCause",
        back_populates="capas",
    )
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])
    tasks: Mapped[List["CAPATask"]] = relationship(
        "CAPATask",
        back_populates="capa",
        cascade="all, delete-orphan",
    )
    effectiveness_checks: Mapped[List["EffectivenessCheck"]] = relationship(
        "EffectivenessCheck",
        back_populates="capa",
        cascade="all, delete-orphan",
    )
    recommendations: Mapped[List["CAPARecommendation"]] = relationship(
        "CAPARecommendation",
        back_populates="capa",
    )


class CAPATask(Base, UUIDPrimaryKeyMixin):
    """Action item assigned to complete a designated CAPA."""

    __tablename__ = "capa_tasks"

    capa_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("capas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_type: Mapped[str] = mapped_column(String(30), default="CORRECTIVE", nullable=False)
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default=CAPATaskStatus.PENDING.value,
        nullable=False,
    )
    dependencies: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    completion_criteria: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_evidence_references: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    review_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completion_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    capa: Mapped["CAPA"] = relationship(
        "CAPA",
        back_populates="tasks",
    )
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to])
    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by])


class EffectivenessCheck(Base, UUIDPrimaryKeyMixin):
    """Periodic verification check ensuring the root cause was eliminated and recurrence prevented."""

    __tablename__ = "effectiveness_checks"

    capa_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("capas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    check_title: Mapped[str] = mapped_column(
        String(255),
        default="CAPA Effectiveness Verification",
        nullable=False,
    )
    verification_type: Mapped[str] = mapped_column(
        String(50),
        default="PROCESS_MONITORING",
        nullable=False,
    )
    objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_method: Mapped[str] = mapped_column(String(255), nullable=False)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    measurement_method: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    baseline_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_outcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observation_period_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    planned_start_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    planned_completion_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_completion_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    responsible_reviewer_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    required_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    associated_evidence_ids: Mapped[List[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )
    sampling_approach: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    check_frequency: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conclusion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default=EffectivenessStatus.SCHEDULED.value,
        nullable=False,
    )
    effectiveness_decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ai_assessment_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ai_execution_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("ai_executions.id", ondelete="SET NULL"),
        nullable=True,
    )
    recurrence_observed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    followup_investigation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    capa: Mapped["CAPA"] = relationship(
        "CAPA",
        back_populates="effectiveness_checks",
    )
    verifier: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by])
    responsible_reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[responsible_reviewer_id],
    )
    decision_maker: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[decision_by],
    )
    followup_investigation: Mapped[Optional["Investigation"]] = relationship(
        "Investigation",
        foreign_keys=[followup_investigation_id],
    )
