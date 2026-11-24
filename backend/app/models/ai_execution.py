from typing import Optional, Any, Dict
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import AIExecutionStatus


class AIExecution(Base, UUIDPrimaryKeyMixin):
    """
    Audit-trailed AI orchestration execution record.
    Tracks all LangGraph workflows, token usages, prompt versions, and structured outputs.
    Ensures 21 CFR Part 11 traceability for AI analytical assistance without quality authority.
    """

    __tablename__ = "ai_executions"

    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workflow_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    investigation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default=AIExecutionStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    input_context_summary: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    structured_output: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_usage: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    investigation = relationship("Investigation", backref="ai_executions")
    user = relationship("User", backref="ai_executions")

