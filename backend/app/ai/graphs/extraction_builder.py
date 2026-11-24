from typing import Literal
from langgraph.graph import StateGraph, START, END

from app.models.enums import ExtractionStatus
from app.ai.providers.base import BaseAIProvider
from app.ai.graphs.extraction_state import IncidentExtractionWorkflowState
from app.ai.graphs.extraction_nodes import (
    validate_request_node,
    prepare_extraction_context_node,
    make_extract_incident_fields_node,
    validate_source_references_node,
    detect_missing_and_conflicting_node,
    complete_extraction_node,
    handle_extraction_failure_node,
)


def _route_after_validation(state: IncidentExtractionWorkflowState) -> Literal["prepare_context", "handle_failure"]:
    if state.get("status") == ExtractionStatus.FAILED.value or state.get("errors"):
        return "handle_failure"
    return "prepare_context"


def _route_after_extraction(state: IncidentExtractionWorkflowState) -> Literal["validate_sources", "handle_failure"]:
    if state.get("status") == ExtractionStatus.FAILED.value or state.get("errors"):
        return "handle_failure"
    return "validate_sources"


def create_incident_extraction_graph(provider: BaseAIProvider):
    """
    Assembles and compiles the LangGraph StateGraph workflow for AI-powered incident extraction.
    Flow:
      START
      -> validate_request
      -> (check error ? handle_failure : prepare_context)
      -> extract_fields (async Groq call)
      -> (check error ? handle_failure : validate_sources)
      -> detect_missing_and_conflicts
      -> complete_extraction
      -> END
    """
    workflow = StateGraph(IncidentExtractionWorkflowState)

    # Register nodes
    workflow.add_node("validate_request", validate_request_node)
    workflow.add_node("prepare_context", prepare_extraction_context_node)
    workflow.add_node("extract_fields", make_extract_incident_fields_node(provider))
    workflow.add_node("validate_sources", validate_source_references_node)
    workflow.add_node("detect_missing_and_conflicts", detect_missing_and_conflicting_node)
    workflow.add_node("complete_extraction", complete_extraction_node)
    workflow.add_node("handle_failure", handle_extraction_failure_node)

    # Register edges
    workflow.add_edge(START, "validate_request")
    workflow.add_conditional_edges(
        "validate_request",
        _route_after_validation,
        {
            "prepare_context": "prepare_context",
            "handle_failure": "handle_failure",
        },
    )
    workflow.add_edge("prepare_context", "extract_fields")
    workflow.add_conditional_edges(
        "extract_fields",
        _route_after_extraction,
        {
            "validate_sources": "validate_sources",
            "handle_failure": "handle_failure",
        },
    )
    workflow.add_edge("validate_sources", "detect_missing_and_conflicts")
    workflow.add_edge("detect_missing_and_conflicts", "complete_extraction")
    workflow.add_edge("complete_extraction", END)
    workflow.add_edge("handle_failure", END)

    return workflow.compile()

