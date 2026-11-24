from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AIExecutionCreate(BaseModel):
    """Payload to record initialization of an AI workflow execution."""

    workflow_id: str
    workflow_type: str
    investigation_id: str
    user_id: Optional[str] = None
    provider: str
    model: str
    prompt_version: str
    input_context_summary: Optional[Dict[str, Any]] = None


class AIExecutionResponse(BaseModel):
    """Audit-trailed representation of an AI workflow execution."""

    id: str
    workflow_id: str
    workflow_type: str
    investigation_id: str
    user_id: Optional[str] = None
    provider: str
    model: str
    prompt_version: str
    status: str
    input_context_summary: Optional[Dict[str, Any]] = None
    structured_output: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    token_usage: Optional[Dict[str, Any]] = None
    latency_ms: Optional[int] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AIHealthResponse(BaseModel):
    """Sanitized diagnostic report on AI provider readiness."""

    status: str
    provider: str
    model: str
    api_key_configured: bool
    timeout_seconds: int
    max_retries: int
    features_ready: List[str] = Field(default_factory=list)

