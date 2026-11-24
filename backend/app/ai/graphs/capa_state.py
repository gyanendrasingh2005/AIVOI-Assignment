from typing import TypedDict, List, Dict, Any, Optional


class CAPAWorkflowState(TypedDict, total=False):
    investigation_id: str
    focus_action_type: Optional[str]
    user_id: Optional[str]
    context: Dict[str, Any]
    opportunities: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    summary: str
    corrective_actions_count: int
    preventive_actions_count: int
    is_failed: bool
    error_message: Optional[str]
    execution_id: Optional[str]

