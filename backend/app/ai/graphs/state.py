from typing import TypedDict, Optional, Dict, Any, List


class WorkflowState(TypedDict, total=False):
    """
    Strongly typed LangGraph state dictionary shared across workflow nodes.
    Maintains complete execution context, trace IDs, prompt payloads,
    token metrics, and structured results.
    """

    workflow_id: str
    investigation_id: str
    workflow_type: str
    user_id: Optional[str]
    prompt_version: str

    input_context: Dict[str, Any]
    system_prompt: str
    user_prompt: str

    raw_response: Optional[str]
    structured_output: Optional[Dict[str, Any]]
    token_usage: Dict[str, int]
    latency_ms: int

    errors: List[str]
    retry_count: int
    status: str  # "PENDING", "PROCESSING", "COMPLETED", "FAILED"

