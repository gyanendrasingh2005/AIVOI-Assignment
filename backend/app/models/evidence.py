from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import EvidenceType, EvidenceVerificationStatus


class Evidence(Base, UUIDPrimaryKeyMixin):
    """Specific verifiable evidence chunk linked to an investigation and supporting document."""

    __tablename__ = "evidence"

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50),
        default=EvidenceType.DOCUMENT_EXCERPT.value,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    verification_status: Mapped[str] = mapped_column(
        String(30),
        default=EvidenceVerificationStatus.UNVERIFIED.value,
        nullable=False,
    )
    uploaded_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="evidence",
    )
    document: Mapped[Optional["Document"]] = relationship(
        "Document",
        back_populates="evidence_items",
    )
    uploader: Mapped[Optional["User"]] = relationship("User")
