"""
State definition for AI-assisted Root Cause Analysis (5 Whys + Fishbone) LangGraph workflow.
"""

from typing import TypedDict, Optional, Dict, Any, List


class RCAWorkflowState(TypedDict, total=False):
    """
    Strongly typed LangGraph execution state for Root Cause Analysis.
    Maintains investigation context, document evidence, prompt payloads, token usage,
    5 Whys sequential chain, Fishbone 6M categories, and root cause classifications.
    """

    rca_id: str
    workflow_id: str
    investigation_id: str
    user_id: Optional[str]
    analysis_method: str
    prompt_version: str

    # Investigation & Evidence Context
    incident_snapshot: Dict[str, Any]
    has_unreviewed_incident_data: bool
    risk_summary: Optional[Dict[str, Any]]
    evidence_list: List[Dict[str, Any]]
    valid_document_map: Dict[str, str]
    valid_evidence_map: Dict[str, str]
    compiled_prompt_context: str
    additional_focus: Optional[str]

    # Prompts & Model execution
    system_prompt: str
    user_prompt: str
    raw_response: Optional[str]
    token_usage: Dict[str, int]
    latency_ms: int

    # Structured RCA Output
    problem_statement: str
    incident_summary: str
    five_whys: List[Dict[str, Any]]
    fishbone_causes: List[Dict[str, Any]]
    potential_root_causes: List[Dict[str, Any]]
    contributing_factors: List[Dict[str, Any]]
    rejected_hypotheses: List[Dict[str, Any]]
    evidence_gaps: List[Dict[str, Any]]
    causal_chain_critique: Optional[str]
    unsupported_assumptions: List[str]

    # Execution control
    status: str  # "PENDING", "PROCESSING", "COMPLETED", "FAILED"
    errors: List[str]

