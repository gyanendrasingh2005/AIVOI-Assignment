import uuid
import logging
from typing import Optional, Type, Dict, Any
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.user import User
from app.models.ai_execution import AIExecution
from app.models.enums import AuditAction, AIExecutionStatus
from app.repositories.investigation_repository import investigation_repo
from app.repositories.ai_execution_repository import ai_execution_repo
from app.repositories.approval_audit_repository import audit_repo
from app.ai.providers.base import BaseAIProvider
from app.ai.providers.groq_provider import GroqProvider
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.graphs.state import WorkflowState
from app.ai.graphs.builder import create_base_workflow_graph
from app.ai.prompts.base import PROMPT_VERSIONS
from app.ai.schemas.common import WorkflowExecutionInput
from app.ai.schemas.execution import AIExecutionCreate, AIHealthResponse

logger = logging.getLogger(__name__)


class AIService:
    """
    Central orchestration service for AI analytical workflows.
    Integrates LangGraph StateGraphs, Groq AI provider, DB execution logging,
    and 21 CFR Part 11 audit trails.
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self._provider = provider

    def get_provider(self) -> BaseAIProvider:
        """Resolves or initializes the AI provider."""
        if self._provider is not None:
            return self._provider
        # Default to GroqProvider; if in mock environment without key, fall back gracefully
        if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "placeholder_key":
            return GroqProvider()
        return GroqProvider()

    def set_provider(self, provider: BaseAIProvider) -> None:
        """Sets or replaces the active provider (useful for testing)."""
        self._provider = provider

    async def get_health(self) -> AIHealthResponse:
        """Performs diagnostic health check on active provider."""
        provider = self.get_provider()
        return await provider.health_check()

    async def execute_workflow(
        self,
        session: AsyncSession,
        user: Optional[User],
        input_data: WorkflowExecutionInput,
        output_schema: Optional[Type[BaseModel]] = None,
        provider_override: Optional[BaseAIProvider] = None,
    ) -> AIExecution:
        """
        Executes an AI workflow with complete database audit tracking.
        1. Validates existence of the target investigation.
        2. Records execution start in database with PENDING status.
        3. Orchestrates LangGraph graph execution.
        4. Updates execution record in database with completion/failure status.
        5. Logs 21 CFR Part 11 compliant audit trail.
        """
        # Step 1: Validate investigation existence
        investigation = await investigation_repo.get(session, input_data.investigation_id)
        if not investigation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation {input_data.investigation_id} not found",
            )

        provider = provider_override or self.get_provider()
        workflow_id = str(uuid.uuid4())
        prompt_version = PROMPT_VERSIONS.get(input_data.workflow_type, "1.0.0")

        # Step 2: Record start in DB
        execution_create = AIExecutionCreate(
            workflow_id=workflow_id,
            workflow_type=input_data.workflow_type,
            investigation_id=input_data.investigation_id,
            user_id=user.id if user else None,
            provider=getattr(provider, "provider", "groq") if hasattr(provider, "provider") else "groq",
            model=provider.model,
            prompt_version=prompt_version,
            input_context_summary=input_data.context_data,
        )
        execution = await ai_execution_repo.record_execution_start(session, execution_create)

        # Step 3: Compile and invoke LangGraph graph
        graph = create_base_workflow_graph(provider=provider, output_schema=output_schema)
        initial_state: WorkflowState = {
            "workflow_id": workflow_id,
            "investigation_id": input_data.investigation_id,
            "workflow_type": input_data.workflow_type,
            "user_id": user.id if user else None,
            "prompt_version": prompt_version,
            "input_context": input_data.context_data,
            "system_prompt": "",
            "user_prompt": "",
            "errors": [],
            "retry_count": 0,
            "status": AIExecutionStatus.PENDING.value,
        }

        try:
            final_state = await graph.ainvoke(initial_state)
            exec_status = final_state.get("status", AIExecutionStatus.COMPLETED.value)
            structured_output = final_state.get("structured_output")
            errors = final_state.get("errors", [])
            error_message = "; ".join(errors) if errors else None
            token_usage = final_state.get("token_usage")
            latency_ms = final_state.get("latency_ms")
        except Exception as e:
            logger.error(f"LangGraph execution exception for workflow {workflow_id}: {str(e)}")
            exec_status = AIExecutionStatus.FAILED.value
            structured_output = None
            error_message = f"Orchestration failure: {str(e)}"
            token_usage = None
            latency_ms = None

        # Step 4: Record completion in DB
        updated_execution = await ai_execution_repo.record_execution_completion(
            session=session,
            execution_id=execution.id,
            status=exec_status,
            structured_output=structured_output,
            error_message=error_message,
            token_usage=token_usage,
            latency_ms=latency_ms,
        )

        # Step 5: ALCOA+ Audit Log
        await audit_repo.record_action(
            session=session,
            user_id=user.id if user else None,
            investigation_id=input_data.investigation_id,
            action=AuditAction.AI_EXECUTE,
            entity_type="AIExecution",
            entity_id=execution.id,
            new_values={
                "workflow_id": workflow_id,
                "workflow_type": input_data.workflow_type,
                "investigation_id": input_data.investigation_id,
                "status": exec_status,
                "latency_ms": latency_ms,
            },
        )

        return updated_execution or execution


_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Returns singleton AIService instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
