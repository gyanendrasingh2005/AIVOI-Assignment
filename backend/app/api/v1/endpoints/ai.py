from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_active_user, verify_investigation_access
from app.models.user import User
from app.repositories.investigation_repository import investigation_repo
from app.repositories.ai_execution_repository import ai_execution_repo
from app.ai.services.ai_service import get_ai_service, AIService
from app.ai.schemas.common import WorkflowExecutionInput
from app.ai.schemas.execution import AIHealthResponse, AIExecutionResponse

router = APIRouter(prefix="/ai", tags=["AI Foundation"])


@router.get(
    "/health",
    response_model=AIHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="AI Diagnostic Health & Readiness",
    description="Reports AI configuration status, active provider, model name, and operational readiness without exposing secrets.",
)
async def get_ai_health(
    ai_service: AIService = Depends(get_ai_service),
) -> AIHealthResponse:
    """Safe diagnostic health check for AI services."""
    return await ai_service.get_health()


@router.get(
    "/executions/{execution_id}",
    response_model=AIExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI Workflow Execution Details",
    description="Retrieves audit-trailed execution record, structured outputs, and token metrics scoped to permitted investigation.",
)
async def get_ai_execution(
    execution_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> AIExecutionResponse:
    """Retrieves AI execution details with investigation-scoped access control."""
    execution = await ai_execution_repo.get(session, execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI execution {execution_id} not found.",
        )

    # Scoped investigation access verification
    investigation = await investigation_repo.get(session, execution.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view AI executions for this investigation.",
        )

    return AIExecutionResponse.model_validate(execution)


@router.get(
    "/investigations/{investigation_id}/executions",
    response_model=List[AIExecutionResponse],
    status_code=status.HTTP_200_OK,
    summary="List AI Executions for Investigation",
    description="Retrieves history of AI workflow executions for a specific investigation.",
)
async def list_investigation_ai_executions(
    investigation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> List[AIExecutionResponse]:
    """Lists all AI workflow executions for an authorized investigation."""
    investigation = await investigation_repo.get(session, investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {investigation_id} not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view AI executions for this investigation.",
        )

    executions = await ai_execution_repo.get_by_investigation(
        session, investigation_id=investigation_id, skip=skip, limit=limit
    )
    return [AIExecutionResponse.model_validate(e) for e in executions]


@router.post(
    "/execute",
    response_model=AIExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute AI Workflow",
    description="Triggers a foundational LangGraph AI workflow for an authorized investigation.",
)
async def execute_ai_workflow(
    input_data: WorkflowExecutionInput,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
    ai_service: AIService = Depends(get_ai_service),
) -> AIExecutionResponse:
    """Triggers an AI workflow run with 21 CFR Part 11 audit logging."""
    investigation = await investigation_repo.get(session, input_data.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {input_data.investigation_id} not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to execute AI workflows on this investigation.",
        )

    execution = await ai_service.execute_workflow(
        session=session,
        user=current_user,
        input_data=input_data,
    )
    return AIExecutionResponse.model_validate(execution)

