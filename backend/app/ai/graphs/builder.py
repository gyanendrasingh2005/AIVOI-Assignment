from typing import Optional, Type, Literal
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END

from app.ai.graphs.state import WorkflowState
from app.ai.graphs.nodes import (
    validate_input_node,
    prepare_context_node,
    make_llm_execution_node,
    make_validate_output_node,
    complete_workflow_node,
    handle_failure_node,
)
from app.ai.providers.base import BaseAIProvider


def _route_after_validation(state: WorkflowState) -> Literal["prepare_context", "handle_failure"]:
    if state.get("status") == "FAILED" or state.get("errors"):
        return "handle_failure"
    return "prepare_context"


def _route_after_execution(state: WorkflowState) -> Literal["validate_output", "handle_failure"]:
    if state.get("status") == "FAILED" or state.get("errors"):
        return "handle_failure"
    return "validate_output"


def _route_after_output_validation(state: WorkflowState) -> Literal["complete_workflow", "handle_failure"]:
    if state.get("status") == "FAILED" or state.get("errors"):
        return "handle_failure"
    return "complete_workflow"


def create_base_workflow_graph(
    provider: BaseAIProvider,
    output_schema: Optional[Type[BaseModel]] = None,
):
    """
    Assembles and compiles a LangGraph StateGraph workflow for AI analytical execution.
    Nodes:
      - validate_input
      - prepare_context
      - execute_llm (async)
      - validate_output
      - complete_workflow
      - handle_failure
    Includes conditional routing for robust failure handling.
    """
    workflow = StateGraph(WorkflowState)

    # Register nodes
    workflow.add_node("validate_input", validate_input_node)
    workflow.add_node("prepare_context", prepare_context_node)
    workflow.add_node("execute_llm", make_llm_execution_node(provider, output_schema))
    workflow.add_node("validate_output", make_validate_output_node(output_schema))
    workflow.add_node("complete_workflow", complete_workflow_node)
    workflow.add_node("handle_failure", handle_failure_node)

    # Register edges
    workflow.add_edge(START, "validate_input")
    workflow.add_conditional_edges(
        "validate_input",
        _route_after_validation,
        {
            "prepare_context": "prepare_context",
            "handle_failure": "handle_failure",
        },
    )
    workflow.add_edge("prepare_context", "execute_llm")
    workflow.add_conditional_edges(
        "execute_llm",
        _route_after_execution,
        {
            "validate_output": "validate_output",
            "handle_failure": "handle_failure",
        },
    )
    workflow.add_conditional_edges(
        "validate_output",
        _route_after_output_validation,
        {
            "complete_workflow": "complete_workflow",
            "handle_failure": "handle_failure",
        },
    )
    workflow.add_edge("complete_workflow", END)
    workflow.add_edge("handle_failure", END)

    return workflow.compile()

