from typing import Optional
from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.models.enums import EvidenceGapStatus, EvidenceGapPriority


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
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(20),
        default=EvidenceGapPriority.MEDIUM.value,
        nullable=False,
    )
    suggested_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default=EvidenceGapStatus.OPEN.value,
        nullable=False,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="evidence_gaps",
    )
    root_cause: Mapped[Optional["RootCause"]] = relationship(
        "RootCause",
        back_populates="evidence_gaps",
    )
