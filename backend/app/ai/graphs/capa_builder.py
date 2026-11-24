from langgraph.graph import StateGraph, START, END

from app.ai.graphs.capa_state import CAPAWorkflowState
from app.ai.graphs.capa_nodes import (
    validate_capa_request_node,
    prepare_investigation_context_node,
    identify_action_opportunities_node,
    generate_capa_recommendations_node,
    validate_capa_references_node,
    evaluate_action_quality_node,
    prioritize_recommendations_node,
)


def _route_after_validation(state: CAPAWorkflowState) -> str:
    if state.get("is_failed"):
        return END
    return "prepare_context"


def _route_after_context(state: CAPAWorkflowState) -> str:
    if state.get("is_failed"):
        return END
    return "identify_opportunities"


def build_capa_recommendation_graph():
    """
    Constructs and compiles the modular LangGraph workflow for AI-assisted CAPA recommendations:
    1. Request Validation
    2. Context Preparation
    3. Action Opportunity Identification
    4. AI Recommendation Generation (Groq / Mock)
    5. Causal Reference & Traceability Validation (anti-hallucination)
    6. SMART Action Quality Evaluation (anti-vague)
    7. Priority Calibration & Finalization
    """
    workflow = StateGraph(CAPAWorkflowState)

    # Register nodes
    workflow.add_node("validate_request", validate_capa_request_node)
    workflow.add_node("prepare_context", prepare_investigation_context_node)
    workflow.add_node("identify_opportunities", identify_action_opportunities_node)
    workflow.add_node("generate_recommendations", generate_capa_recommendations_node)
    workflow.add_node("validate_references", validate_capa_references_node)
    workflow.add_node("evaluate_quality", evaluate_action_quality_node)
    workflow.add_node("prioritize_and_finalize", prioritize_recommendations_node)

    # Connect edges
    workflow.add_edge(START, "validate_request")
    workflow.add_conditional_edges(
        "validate_request",
        _route_after_validation,
        {"prepare_context": "prepare_context", END: END},
    )
    workflow.add_conditional_edges(
        "prepare_context",
        _route_after_context,
        {"identify_opportunities": "identify_opportunities", END: END},
    )
    workflow.add_edge("identify_opportunities", "generate_recommendations")
    workflow.add_edge("generate_recommendations", "validate_references")
    workflow.add_edge("validate_references", "evaluate_quality")
    workflow.add_edge("evaluate_quality", "prioritize_and_finalize")
    workflow.add_edge("prioritize_and_finalize", END)

    return workflow.compile()

