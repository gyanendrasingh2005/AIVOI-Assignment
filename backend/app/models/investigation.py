from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import InvestigationStatus, PriorityLevel, RiskLevel


class Investigation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Investigation record tracking root cause determination and CAPA formulation for API deviations."""

    __tablename__ = "investigations"

    investigation_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(50),
        default=InvestigationStatus.DRAFT.value,
        index=True,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        default=PriorityLevel.MEDIUM.value,
        nullable=False,
    )
    risk_level: Mapped[str] = mapped_column(
        String(20),
        default=RiskLevel.MAJOR.value,
        nullable=False,
    )

    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="created_investigations",
    )
    assignee: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_to],
        back_populates="assigned_investigations",
    )
    incident: Mapped[Optional["Incident"]] = relationship(
        "Incident",
        back_populates="investigation",
        uselist=False,
        cascade="all, delete-orphan",
    )
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    rca_analyses: Mapped[List["RCAAnalysis"]] = relationship(
        "RCAAnalysis",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    evidence_gaps: Mapped[List["EvidenceGap"]] = relationship(
        "EvidenceGap",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    completeness_assessments: Mapped[List["CompletenessAssessment"]] = relationship(
        "CompletenessAssessment",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    capas: Mapped[List["CAPA"]] = relationship(
        "CAPA",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    approvals: Mapped[List["Approval"]] = relationship(
        "Approval",
        back_populates="investigation",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="investigation",
    )


class InvestigationCounter(Base):
    """
    Concurrency-safe sequence counter maintaining yearly counters
    for pharmaceutical investigation numbers (INV-YYYY-XXXXX).
    """

    __tablename__ = "investigation_counters"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

