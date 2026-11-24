from langgraph.graph import StateGraph, START, END

from app.ai.graphs.effectiveness_state import EffectivenessWorkflowState
from app.ai.graphs.effectiveness_nodes import (
    validate_effectiveness_request_node,
    evaluate_effectiveness_evidence_node,
    synthesize_effectiveness_assessment_node,
)


def _route_after_validation(state: EffectivenessWorkflowState) -> str:
    if state.get("is_failed"):
        return END
    return "evaluate_evidence"


def build_effectiveness_assessment_graph():
    """
    Constructs and compiles the LangGraph workflow for advisory CAPA Effectiveness Verification:
    1. Validate input request
    2. Evaluate evidence against criteria, observation period, and recurrence data
    3. Synthesize structured findings and advisory recommendation
    """
    workflow = StateGraph(EffectivenessWorkflowState)

    workflow.add_node("validate_request", validate_effectiveness_request_node)
    workflow.add_node("evaluate_evidence", evaluate_effectiveness_evidence_node)
    workflow.add_node("synthesize_assessment", synthesize_effectiveness_assessment_node)

    workflow.add_edge(START, "validate_request")
    workflow.add_conditional_edges(
        "validate_request",
        _route_after_validation,
        {"evaluate_evidence": "evaluate_evidence", END: END},
    )
    workflow.add_edge("evaluate_evidence", "synthesize_assessment")
    workflow.add_edge("synthesize_assessment", END)

    return workflow.compile()

