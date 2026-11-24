from typing import Optional, Any
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin, TimestampMixin


class Incident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The underlying manufacturing or testing event that initiated an API quality investigation."""

    __tablename__ = "incidents"

    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    api_product_name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    batch_number: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    manufacturing_stage: Mapped[str] = mapped_column(String(100), nullable=False)
    incident_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    incident_description: Mapped[str] = mapped_column(Text, nullable=False)

    equipment_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    expected_parameter: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    actual_parameter: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    immediate_actions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Store affected batches using JSON/JSONB for cross-dialect compatibility
    affected_batches: Mapped[Optional[Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        nullable=True,
    )
    potential_quality_impact: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    investigation: Mapped["Investigation"] = relationship(
        "Investigation",
        back_populates="incident",
    )
