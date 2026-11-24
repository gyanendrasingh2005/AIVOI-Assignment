"""
LangGraph Builder for AI-assisted Quality Impact and Risk Assessment workflow.
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END

from app.models.enums import RiskAssessmentStatus
from app.ai.providers.base import BaseAIProvider
from app.ai.graphs.risk_state import RiskAssessmentWorkflowState
from app.ai.graphs.risk_nodes import (
    validate_risk_request_node,
    prepare_risk_context_node,
    make_evaluate_risk_node,
    validate_risk_citations_node,
    calculate_framework_matrix_node,
    complete_risk_assessment_node,
    handle_risk_failure_node,
)


def _route_after_validation(state: RiskAssessmentWorkflowState) -> Literal["prepare_context", "handle_failure"]:
    if state.get("status") == RiskAssessmentStatus.FAILED.value or state.get("errors"):
        return "handle_failure"
    return "prepare_context"


def _route_after_evaluation(state: RiskAssessmentWorkflowState) -> Literal["validate_citations", "handle_failure"]:
    if state.get("status") == RiskAssessmentStatus.FAILED.value or state.get("errors"):
        return "handle_failure"
    return "validate_citations"


def create_risk_assessment_graph(provider: BaseAIProvider):
    """
    Assembles and compiles the LangGraph StateGraph workflow for Quality Risk Assessment.
    Flow:
      START
      -> validate_risk_request
      -> (check error ? handle_failure : prepare_context)
      -> evaluate_risk (async Groq call with structured output)
      -> (check error ? handle_failure : validate_citations)
      -> calculate_matrix (ICH Q9 risk matrix reconciliation)
      -> complete_assessment
      -> END
    """
    workflow = StateGraph(RiskAssessmentWorkflowState)

    # Register nodes
    workflow.add_node("validate_risk_request", validate_risk_request_node)
    workflow.add_node("prepare_context", prepare_risk_context_node)
    workflow.add_node("evaluate_risk", make_evaluate_risk_node(provider))
    workflow.add_node("validate_citations", validate_risk_citations_node)
    workflow.add_node("calculate_matrix", calculate_framework_matrix_node)
    workflow.add_node("complete_assessment", complete_risk_assessment_node)
    workflow.add_node("handle_failure", handle_risk_failure_node)

    # Register edges
    workflow.add_edge(START, "validate_risk_request")
    workflow.add_conditional_edges(
        "validate_risk_request",
        _route_after_validation,
        {
            "prepare_context": "prepare_context",
            "handle_failure": "handle_failure",
        },
    )
    workflow.add_edge("prepare_context", "evaluate_risk")
    workflow.add_conditional_edges(
        "evaluate_risk",
        _route_after_evaluation,
        {
            "validate_citations": "validate_citations",
            "handle_failure": "handle_failure",
        },
    )
    workflow.add_edge("validate_citations", "calculate_matrix")
    workflow.add_edge("calculate_matrix", "complete_assessment")
    workflow.add_edge("complete_assessment", END)
    workflow.add_edge("handle_failure", END)

    return workflow.compile()
