"""
LangGraph Builder for AI-assisted Root Cause Analysis (5 Whys + Fishbone) workflow.
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END

from app.ai.providers.base import BaseAIProvider
from app.ai.graphs.rca_state import RCAWorkflowState
from app.ai.graphs.rca_nodes import (
    validate_rca_request_node,
    prepare_rca_context_node,
    make_generate_rca_node,
    validate_causal_chain_node,
    validate_rca_citations_node,
    categorize_fishbone_and_causes_node,
    complete_rca_node,
    handle_rca_failure_node,
)


def _route_after_validation(state: RCAWorkflowState) -> Literal["prepare_context", "handle_failure"]:
    if state.get("status") == "FAILED" or state.get("errors"):
        return "handle_failure"
    return "prepare_context"


def _route_after_generation(state: RCAWorkflowState) -> Literal["validate_causal_chain", "handle_failure"]:
    if state.get("status") == "FAILED" or state.get("errors"):
        return "handle_failure"
    return "validate_causal_chain"


def create_rca_graph(provider: BaseAIProvider):
    """
    Assembles and compiles the LangGraph StateGraph workflow for Root Cause Analysis.
    Flow:
      START
      -> validate_rca_request
      -> (check error ? handle_failure : prepare_context)
      -> generate_rca (async Groq call with RCAStructuredOutput)
      -> (check error ? handle_failure : validate_causal_chain)
      -> validate_citations
      -> categorize_fishbone_and_causes
      -> complete_rca
      -> END
    """
    workflow = StateGraph(RCAWorkflowState)

    # Register nodes
    workflow.add_node("validate_rca_request", validate_rca_request_node)
    workflow.add_node("prepare_context", prepare_rca_context_node)
    workflow.add_node("generate_rca", make_generate_rca_node(provider))
    workflow.add_node("validate_causal_chain", validate_causal_chain_node)
    workflow.add_node("validate_citations", validate_rca_citations_node)
    workflow.add_node("categorize_fishbone_and_causes", categorize_fishbone_and_causes_node)
    workflow.add_node("complete_rca", complete_rca_node)
    workflow.add_node("handle_failure", handle_rca_failure_node)

    # Register edges
    workflow.add_edge(START, "validate_rca_request")
    workflow.add_conditional_edges(
        "validate_rca_request",
        _route_after_validation,
        {
            "prepare_context": "prepare_context",
            "handle_failure": "handle_failure",
        },
    )
    workflow.add_edge("prepare_context", "generate_rca")
    workflow.add_conditional_edges(
        "generate_rca",
        _route_after_generation,
        {
            "validate_causal_chain": "validate_causal_chain",
            "handle_failure": "handle_failure",
        },
    )
    workflow.add_edge("validate_causal_chain", "validate_citations")
    workflow.add_edge("validate_citations", "categorize_fishbone_and_causes")
    workflow.add_edge("categorize_fishbone_and_causes", "complete_rca")
    workflow.add_edge("complete_rca", END)
    workflow.add_edge("handle_failure", END)

    return workflow.compile()

