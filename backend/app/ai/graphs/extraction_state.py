from typing import TypedDict, Optional, Dict, Any, List


class IncidentExtractionWorkflowState(TypedDict, total=False):
    """
    Strongly typed LangGraph execution state for AI-powered incident extraction.
    Carries source documents, citation provenance, LLM prompts, token metrics,
    and unconfirmed draft extractions awaiting human review.
    """

    extraction_id: str
    workflow_id: str
    investigation_id: str
    user_id: Optional[str]
    document_ids: List[str]
    extraction_instructions: Optional[str]
    prompt_version: str

    # Document Staging & Context
    document_context: str
    document_summaries: List[Dict[str, Any]]
    valid_document_map: Dict[str, str]  # map of document_id -> filename

    # Prompts and LLM interaction
    system_prompt: str
    user_prompt: str
    raw_response: Optional[str]
    token_usage: Dict[str, int]
    latency_ms: int

    # Structured Extractions
    extracted_fields: Dict[str, Any]  # field_name -> ExtractedField dict
    missing_information: List[Dict[str, Any]]
    conflicting_information: List[Dict[str, Any]]

    # Execution control
    status: str  # "PENDING", "PROCESSING", "COMPLETED", "FAILED"
    errors: List[str]

