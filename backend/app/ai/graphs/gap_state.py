"""
LangGraph Evidence Gap Assessment State Definition
===================================================
"""

from typing import TypedDict, Optional, List, Dict, Any


class GapAssessmentWorkflowState(TypedDict):
    investigation_id: str
    requirement_profile_version: str
    user_id: Optional[str]
    context_data: Dict[str, Any]
    applicable_rules: List[Dict[str, Any]]
    compiled_prompt_context: str
    compiled_rules_text: str

    # LLM Structured Output
    raw_ai_output: Optional[Dict[str, Any]]
    overall_status: str
    completeness_score: float
    summary: Optional[str]
    dimensions: List[Dict[str, Any]]
    detected_gaps: List[Dict[str, Any]]
    conflicting_evidence: List[Dict[str, Any]]
    recommended_activities: List[str]

    # Post-validation & Aggregates
    validated_gaps: List[Dict[str, Any]]
    critical_unresolved_gaps: int
    high_priority_unresolved_gaps: int
    total_unresolved_gaps: int
    conflicting_evidence_count: int
    unverified_causal_claims_count: int
    pending_reviews_count: int

    # Error handling & status
    error_message: Optional[str]
    is_failed: bool
