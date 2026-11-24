from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import DocumentProcessingStatus


class Document(Base, UUIDPrimaryKeyMixin):
    """File record representing batch production records, analytical CoAs, or equipment historian exports."""

    __tablename__ = "documents"

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    uploaded_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    processing_status: Mapped[str] = mapped_column(
        String(30),
        default=DocumentProcessingStatus.PENDING.value,
        nullable=False,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="documents",
    )
    uploader: Mapped[Optional["User"]] = relationship("User")
    evidence_items: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="document",
    )
