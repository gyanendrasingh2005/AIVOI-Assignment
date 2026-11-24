from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import ApprovalStatus


class Approval(Base, UUIDPrimaryKeyMixin):
    """21 CFR Part 11 compliant sign-off and review record for investigation milestones."""

    __tablename__ = "approvals"

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    approval_status: Mapped[str] = mapped_column(
        String(30),
        default=ApprovalStatus.APPROVED.value,
        nullable=False,
    )
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="approvals",
    )
    reviewer: Mapped["User"] = relationship(
        "User",
        back_populates="approvals",
    )
