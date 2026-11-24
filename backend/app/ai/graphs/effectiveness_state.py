from typing import TypedDict, List, Dict, Any, Optional


class EffectivenessWorkflowState(TypedDict, total=False):
    """State for the AI-assisted CAPA Effectiveness Verification LangGraph workflow."""

    investigation_id: str
    capa_id: str
    check_id: str
    user_id: Optional[str]
    context: Dict[str, Any]
    evidence_evaluation: Dict[str, Any]
    ai_proposal: str  # POTENTIALLY_EFFECTIVE, POTENTIALLY_INEFFECTIVE, INSUFFICIENT_EVIDENCE, CONFLICTING_EVIDENCE, REQUIRES_HUMAN_REVIEW
    confidence_score: float
    rationale: str
    citations: List[str]
    concerns_or_gaps: List[str]
    recommended_human_actions: List[str]
    is_failed: bool
    error_message: Optional[str]
    execution_id: Optional[str]

