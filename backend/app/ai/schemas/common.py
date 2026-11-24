from typing import Optional, Dict, Any, Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar("T")


class TokenUsage(BaseModel):
    """Token consumption metrics for cost and audit tracking."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ProviderResponse(BaseModel):
    """Raw text completion response from an AI provider."""

    content: str
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    finish_reason: Optional[str] = None
    latency_ms: int = 0
    model: str
    provider: str


class StructuredOutputResult(BaseModel, Generic[T]):
    """Validated structured output parsed from model response."""

    data: Optional[T] = None
    raw_content: str = ""
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: int = 0
    model: str = ""
    provider: str = ""
    parsed_successfully: bool = True
    parsing_repair_applied: bool = False
    validation_error: Optional[str] = None


class WorkflowExecutionInput(BaseModel):
    """Standardized input payload for LangGraph workflows."""

    investigation_id: str
    workflow_type: str = "base_workflow"
    context_data: Dict[str, Any] = Field(default_factory=dict)
    document_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)

