from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Float, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import EvidenceGapStatus, EvidenceGapPriority, GapCategory, GapDetectionType


class EvidenceGap(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """An identified gap, missing log, or unverified assumption in the investigation evidence trail."""

    __tablename__ = "evidence_gaps"

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    root_cause_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("root_causes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    gap_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50),
        default=GapCategory.OTHER.value,
        nullable=False,
        index=True,
    )
    detection_type: Mapped[str] = mapped_column(
        String(50),
        default=GapDetectionType.MISSING_EVIDENCE.value,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(30),
        default=EvidenceGapPriority.MEDIUM.value,
        nullable=False,
        index=True,
    )
    affected_area: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    suggested_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recommended_evidence_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    recommended_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detection_source: Mapped[str] = mapped_column(String(50), default="AI_ASSESSMENT", nullable=False)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default=EvidenceGapStatus.OPEN.value,
        nullable=False,
        index=True,
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    requirement_profile_version: Mapped[Optional[str]] = mapped_column(String(20), default="1.0.0", nullable=True)
    assessment_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    associated_evidence_ids: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    supporting_references: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="evidence_gaps",
    )
    root_cause: Mapped[Optional["RootCause"]] = relationship(
        "RootCause",
        back_populates="evidence_gaps",
    )
    assigned_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_to],
    )
    resolver_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[resolved_by],
    )
