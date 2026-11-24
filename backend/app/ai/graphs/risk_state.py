"""
State definition for AI-assisted Quality Impact and Risk Assessment LangGraph workflow.
"""

from typing import TypedDict, Optional, Dict, Any, List


class RiskAssessmentWorkflowState(TypedDict, total=False):
    """
    Strongly typed LangGraph execution state for quality and risk assessment.
    Carries incident information, document evidence, prompt payloads, token usage,
    6 evaluated risk dimensions, and risk classification matrix metrics.
    """

    assessment_id: str
    workflow_id: str
    investigation_id: str
    user_id: Optional[str]
    framework_version: str

    # Source Incident Context
    incident_snapshot: Dict[str, Any]
    has_unreviewed_incident_data: bool
    unreviewed_fields_warning: Optional[str]

    # Staged Evidence Context
    document_context: str
    valid_document_map: Dict[str, str]  # map of document_id -> filename
    additional_instructions: Optional[str]

    # Prompts & Model execution
    system_prompt: str
    user_prompt: str
    raw_response: Optional[str]
    token_usage: Dict[str, int]
    latency_ms: int

    # Evaluated Risk Dimensions
    quality_impact: Dict[str, Any]
    patient_impact: Dict[str, Any]
    batch_impact: Dict[str, Any]
    process_impact: Dict[str, Any]
    equipment_impact: Dict[str, Any]
    data_integrity_impact: Dict[str, Any]

    # Classifications
    severity: str
    likelihood: str
    detectability: Optional[str]
    overall_risk: str
    risk_rationale: str
    urgency_recommendation: str

    # Traceability & Evidence Provance
    supporting_references: List[Dict[str, Any]]
    missing_information: List[Dict[str, Any]]
    conflicting_evidence: List[Dict[str, Any]]
    uncertainty_notes: Optional[str]
    confidence_score: float

    # Execution control
    status: str  # "PENDING", "PROCESSING", "COMPLETED", "FAILED"
    errors: List[str]
