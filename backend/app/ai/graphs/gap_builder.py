"""
Evidence Gap & Investigation Completeness LangGraph Builder
===========================================================
"""

from langgraph.graph import StateGraph, END
from app.ai.graphs.gap_state import GapAssessmentWorkflowState
from app.ai.graphs.gap_nodes import (
    validate_gap_request_node,
    prepare_gap_context_node,
    load_requirement_profile_node,
    execute_gap_and_completeness_ai_node,
    validate_evidence_references_node,
    prioritize_and_consolidate_gaps_node,
    calculate_completeness_node,
)


def create_gap_assessment_graph():
    """Builds and compiles the Evidence Gap & Completeness LangGraph StateGraph."""
    graph = StateGraph(GapAssessmentWorkflowState)

    # 1. Add nodes
    graph.add_node("validate_request", validate_gap_request_node)
    graph.add_node("prepare_context", prepare_gap_context_node)
    graph.add_node("load_profile", load_requirement_profile_node)
    graph.add_node("execute_ai", execute_gap_and_completeness_ai_node)
    graph.add_node("validate_references", validate_evidence_references_node)
    graph.add_node("prioritize_gaps", prioritize_and_consolidate_gaps_node)
    graph.add_node("calculate_completeness", calculate_completeness_node)

    # 2. Add routing edges
    def route_after_validation(state: GapAssessmentWorkflowState) -> str:
        if state.get("is_failed"):
            return END
        return "prepare_context"

    def route_after_context(state: GapAssessmentWorkflowState) -> str:
        if state.get("is_failed"):
            return END
        return "load_profile"

    def route_after_profile(state: GapAssessmentWorkflowState) -> str:
        if state.get("is_failed"):
            return END
        return "execute_ai"

    def route_after_ai(state: GapAssessmentWorkflowState) -> str:
        if state.get("is_failed"):
            return END
        return "validate_references"

    graph.set_entry_point("validate_request")
    graph.add_conditional_edges("validate_request", route_after_validation, {"prepare_context": "prepare_context", END: END})
    graph.add_conditional_edges("prepare_context", route_after_context, {"load_profile": "load_profile", END: END})
    graph.add_conditional_edges("load_profile", route_after_profile, {"execute_ai": "execute_ai", END: END})
    graph.add_conditional_edges("execute_ai", route_after_ai, {"validate_references": "validate_references", END: END})
    graph.add_edge("validate_references", "prioritize_gaps")
    graph.add_edge("prioritize_gaps", "calculate_completeness")
    graph.add_edge("calculate_completeness", END)

    return graph.compile()

