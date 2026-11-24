from typing import List, Optional
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import (
    CAPAType,
    CAPAStatus,
    PriorityLevel,
    CAPATaskStatus,
    EffectivenessStatus,
)


class CAPA(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Corrective and Preventive Action plan conforming to ICH Q10 guidelines."""

    __tablename__ = "capas"

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
    capa_type: Mapped[str] = mapped_column(
        String(20),
        default=CAPAType.CORRECTIVE.value,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
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
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="capas",
    )
    root_cause: Mapped[Optional["RootCause"]] = relationship(
        "RootCause",
        back_populates="capas",
    )
    assignee: Mapped[Optional["User"]] = relationship("User")
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
    assigned_to: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default=CAPATaskStatus.PENDING.value,
        nullable=False,
    )
    completion_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    capa: Mapped["CAPA"] = relationship(
        "CAPA",
        back_populates="tasks",
    )
    assignee: Mapped[Optional["User"]] = relationship("User")


class EffectivenessCheck(Base, UUIDPrimaryKeyMixin):
    """Periodic verification check ensuring the root cause was eliminated and recurrence prevented."""

    __tablename__ = "effectiveness_checks"

    capa_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("capas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verification_method: Mapped[str] = mapped_column(String(255), nullable=False)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default=EffectivenessStatus.SCHEDULED.value,
        nullable=False,
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

    # Relationships
    capa: Mapped["CAPA"] = relationship(
        "CAPA",
        back_populates="effectiveness_checks",
    )
    verifier: Mapped[Optional["User"]] = relationship("User")
