from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import RiskAssessmentStatus, RiskAssessmentReviewStatus


class RiskAssessment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Structured AI-assisted Quality Impact and Risk Assessment record.
    Evaluates product quality, patient impact, batch/material, process, equipment, and data integrity.
    Maintains 21 CFR Part 11 ALCOA+ audit trailing, versioned risk framework calculations,
    and unconfirmed draft status until explicit human QA review.
    """

    __tablename__ = "risk_assessments"

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
        index=True,
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    framework_version: Mapped[str] = mapped_column(
        String(20),
        default="1.0.0",
        nullable=False,
    )

    # Input Incident Snapshot at assessment time
    incident_snapshot: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Dimension Assessments
    quality_impact: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    patient_impact: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    batch_impact: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    process_impact: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    equipment_impact: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    data_integrity_impact: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # Classifications
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    likelihood: Mapped[str] = mapped_column(String(30), nullable=False)
    detectability: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    overall_risk: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    risk_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    urgency_recommendation: Mapped[str] = mapped_column(String(100), nullable=False)

    # Traceability & Evidence Provance
    supporting_references: Mapped[List[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    missing_information: Mapped[List[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    conflicting_evidence: Mapped[List[Any]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    uncertainty_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Execution & Human Review States
    status: Mapped[str] = mapped_column(
        String(30),
        default=RiskAssessmentStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    review_status: Mapped[str] = mapped_column(
        String(30),
        default=RiskAssessmentReviewStatus.PENDING_REVIEW.value,
        nullable=False,
        index=True,
    )

    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    investigation = relationship("Investigation", backref="risk_assessments")
    ai_execution = relationship("AIExecution", backref="risk_assessments")
    creator = relationship("User", foreign_keys=[created_by], backref="created_risk_assessments")
    reviewer = relationship("User", foreign_keys=[reviewed_by], backref="reviewed_risk_assessments")
