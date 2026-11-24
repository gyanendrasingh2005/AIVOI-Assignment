import json
import logging
from typing import Dict, Any, Optional, Type, Callable, Awaitable
from pydantic import BaseModel, ValidationError

from app.ai.graphs.state import WorkflowState
from app.ai.providers.base import BaseAIProvider
from app.ai.prompts.base import get_system_prompt, PROMPT_VERSIONS
from app.ai.exceptions import sanitize_ai_error

logger = logging.getLogger(__name__)


def validate_input_node(state: WorkflowState) -> WorkflowState:
    """
    Validates input state requirements before LLM invocation.
    Ensures required IDs and context are present.
    """
    errors = list(state.get("errors", []))
    if not state.get("investigation_id"):
        errors.append("Validation failed: investigation_id is required.")
    if not state.get("workflow_id"):
        errors.append("Validation failed: workflow_id is required.")
    if not state.get("input_context"):
        errors.append("Validation failed: input_context cannot be empty.")

    if errors:
        state["errors"] = errors
        state["status"] = "FAILED"
    else:
        state["status"] = "PROCESSING"
        state["errors"] = []

    return state


def prepare_context_node(state: WorkflowState) -> WorkflowState:
    """
    Prepares system instructions and structured user prompt from context data.
    """
    if state.get("status") == "FAILED":
        return state

    workflow_type = state.get("workflow_type", "base_workflow")
    prompt_ver = state.get("prompt_version") or PROMPT_VERSIONS.get(workflow_type, "1.0.0")
    state["prompt_version"] = prompt_ver

    # Ensure system prompt is loaded
    if not state.get("system_prompt"):
        state["system_prompt"] = get_system_prompt("analytical_assistant", prompt_ver)

    # Format user prompt from input context
    context = state.get("input_context", {})
    context_str = json.dumps(context, indent=2, default=str)
    user_prompt = (
        f"Workflow Type: {workflow_type}\n"
        f"Investigation ID: {state.get('investigation_id')}\n\n"
        f"Input Investigation & Incident Context:\n{context_str}\n\n"
        f"Please analyze the provided context strictly adhering to pharmaceutical analytical standards."
    )
    state["user_prompt"] = user_prompt
    return state


def make_llm_execution_node(
    provider: BaseAIProvider,
    output_schema: Optional[Type[BaseModel]] = None,
) -> Callable[[WorkflowState], Awaitable[WorkflowState]]:
    """
    Creates an async node function that invokes the AI provider.
    """

    async def llm_execution_node(state: WorkflowState) -> WorkflowState:
        if state.get("status") == "FAILED":
            return state

        try:
            if output_schema:
                result = await provider.generate_structured(
                    prompt=state.get("user_prompt", ""),
                    response_model=output_schema,
                    system_prompt=state.get("system_prompt", ""),
                )
                state["raw_response"] = result.raw_content
                state["token_usage"] = {
                    "prompt_tokens": result.token_usage.prompt_tokens,
                    "completion_tokens": result.token_usage.completion_tokens,
                    "total_tokens": result.token_usage.total_tokens,
                }
                state["latency_ms"] = result.latency_ms

                if result.parsed_successfully and result.data:
                    state["structured_output"] = result.data.model_dump()
                else:
                    errors = list(state.get("errors", []))
                    err_msg = result.validation_error or "Structured parsing failed."
                    errors.append(sanitize_ai_error(err_msg))
                    state["errors"] = errors
                    state["status"] = "FAILED"
            else:
                result = await provider.generate_text(
                    prompt=state.get("user_prompt", ""),
                    system_prompt=state.get("system_prompt", ""),
                )
                state["raw_response"] = result.content
                state["token_usage"] = {
                    "prompt_tokens": result.token_usage.prompt_tokens,
                    "completion_tokens": result.token_usage.completion_tokens,
                    "total_tokens": result.token_usage.total_tokens,
                }
                state["latency_ms"] = result.latency_ms
                # Set a basic dictionary structure for raw text outputs
                state["structured_output"] = {"text_output": result.content}

        except Exception as e:
            errors = list(state.get("errors", []))
            errors.append(sanitize_ai_error(f"LLM execution error: {str(e)}"))
            state["errors"] = errors
            state["status"] = "FAILED"

        return state

    return llm_execution_node


def make_validate_output_node(
    output_schema: Optional[Type[BaseModel]] = None,
) -> Callable[[WorkflowState], WorkflowState]:
    """
    Creates a node function to validate final output against schema.
    """

    def validate_output_node(state: WorkflowState) -> WorkflowState:
        if state.get("status") == "FAILED":
            return state

        if output_schema:
            data = state.get("structured_output")
            if not data:
                errors = list(state.get("errors", []))
                errors.append("Output validation error: structured_output is missing.")
                state["errors"] = errors
                state["status"] = "FAILED"
                return state

            try:
                output_schema.model_validate(data)
            except ValidationError as e:
                errors = list(state.get("errors", []))
                errors.append(sanitize_ai_error(f"Schema validation error: {str(e)}"))
                state["errors"] = errors
                state["status"] = "FAILED"
                return state

        return state

    return validate_output_node


def complete_workflow_node(state: WorkflowState) -> WorkflowState:
    """Marks successful completion of the workflow."""
    if not state.get("errors") and state.get("status") != "FAILED":
        state["status"] = "COMPLETED"
    return state


def handle_failure_node(state: WorkflowState) -> WorkflowState:
    """Handles workflow failure and records state."""
    state["status"] = "FAILED"
    if not state.get("errors"):
        state["errors"] = ["Unknown workflow execution failure."]
    return state

