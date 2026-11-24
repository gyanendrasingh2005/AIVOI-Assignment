from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_active_user, verify_investigation_access
from app.models.user import User
from app.repositories.investigation_repository import investigation_repo
from app.repositories.ai_execution_repository import ai_execution_repo
from app.repositories.incident_extraction_repository import incident_extraction_repo
from app.ai.services.ai_service import get_ai_service, AIService
from app.services.incident_extraction_service import incident_extraction_service
from app.ai.schemas.common import WorkflowExecutionInput
from app.ai.schemas.execution import AIHealthResponse, AIExecutionResponse
from app.schemas.extraction import (
    IncidentExtractionRequest,
    IncidentExtractionResponse,
    ExtractionReviewViewResponse,
    ExtractionReviewPatchRequest,
    FieldAcceptanceRequest,
    FieldRejectionRequest,
)

router = APIRouter(tags=["AI Foundation & Incident Extraction"])


# ---------------------------------------------------------------------------
# Foundation Diagnostic & Execution Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/ai/health",
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
    "/ai/executions/{execution_id}",
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
    "/ai/investigations/{investigation_id}/executions",
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
    "/ai/execute",
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


# ---------------------------------------------------------------------------
# AI-Powered Incident Information Extraction & Human Review Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/investigations/{investigation_id}/ai/extract-incident",
    response_model=IncidentExtractionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate AI Incident Information Extraction",
    description="Starts LangGraph extraction workflow across selected investigation documents.",
)
async def trigger_incident_extraction(
    investigation_id: str,
    request: IncidentExtractionRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> IncidentExtractionResponse:
    """Starts AI-powered incident extraction workflow."""
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
            detail="Access denied: You do not have permission to run AI extractions on this investigation.",
        )

    extraction = await incident_extraction_service.start_incident_extraction(
        session=session,
        user=current_user,
        investigation_id=investigation_id,
        request=request,
    )
    return IncidentExtractionResponse.model_validate(extraction)


@router.get(
    "/investigations/{investigation_id}/ai/extractions",
    response_model=List[IncidentExtractionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Incident Extraction Runs",
    description="Retrieves historical AI incident extraction runs for the investigation.",
)
async def list_investigation_extractions(
    investigation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> List[IncidentExtractionResponse]:
    """Lists historical AI extraction runs for an investigation."""
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
            detail="Access denied: You do not have permission to view extractions for this investigation.",
        )

    extractions = await incident_extraction_repo.get_by_investigation(
        session, investigation_id=investigation_id, skip=skip, limit=limit
    )
    return [IncidentExtractionResponse.model_validate(e) for e in extractions]


@router.get(
    "/ai/extractions/{extraction_id}",
    response_model=IncidentExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Incident Extraction Details",
    description="Retrieves complete extraction result with structured suggestions, missing info, and conflicts.",
)
async def get_incident_extraction_details(
    extraction_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> IncidentExtractionResponse:
    """Retrieves full extraction details scoped to permitted investigation."""
    extraction = await incident_extraction_repo.get(session, extraction_id)
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident extraction {extraction_id} not found.",
        )

    investigation = await investigation_repo.get(session, extraction.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view this extraction.",
        )

    return IncidentExtractionResponse.model_validate(extraction)


@router.get(
    "/ai/extractions/{extraction_id}/review",
    response_model=ExtractionReviewViewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Extraction Human Review View",
    description="Retrieves review-ready payload with individual field suggestions, confidence, and source citations.",
)
async def get_extraction_review_view(
    extraction_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> ExtractionReviewViewResponse:
    """Retrieves human review view with source excerpts."""
    extraction = await incident_extraction_repo.get(session, extraction_id)
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident extraction {extraction_id} not found.",
        )

    investigation = await investigation_repo.get(session, extraction.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view this extraction.",
        )

    return await incident_extraction_service.get_extraction_review_view(
        session=session,
        user=current_user,
        extraction_id=extraction_id,
    )


@router.patch(
    "/ai/extractions/{extraction_id}/review",
    response_model=IncidentExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Human Review Decisions and Overrides",
    description="Allows an investigator to update review decisions (accept/reject/edit) without altering confirmed Incident records.",
)
async def patch_extraction_review_decisions(
    extraction_id: str,
    patch_req: ExtractionReviewPatchRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> IncidentExtractionResponse:
    """Updates human review decisions for extracted fields."""
    extraction = await incident_extraction_repo.get(session, extraction_id)
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident extraction {extraction_id} not found.",
        )

    investigation = await investigation_repo.get(session, extraction.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to review extractions for this investigation.",
        )

    updated = await incident_extraction_service.update_review_decisions(
        session=session,
        user=current_user,
        extraction_id=extraction_id,
        patch_req=patch_req,
    )
    return IncidentExtractionResponse.model_validate(updated)


@router.post(
    "/ai/extractions/{extraction_id}/accept",
    response_model=IncidentExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept Reviewed Incident Fields",
    description="Explicit authenticated human action: applies accepted fields to the confirmed Incident record with full ALCOA+ audit history.",
)
async def accept_incident_fields(
    extraction_id: str,
    accept_req: FieldAcceptanceRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> IncidentExtractionResponse:
    """Applies accepted fields to the confirmed database Incident record."""
    extraction = await incident_extraction_repo.get(session, extraction_id)
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident extraction {extraction_id} not found.",
        )

    investigation = await investigation_repo.get(session, extraction.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to accept extraction fields for this investigation.",
        )

    updated_extraction, _ = await incident_extraction_service.accept_incident_fields(
        session=session,
        user=current_user,
        extraction_id=extraction_id,
        accept_req=accept_req,
    )
    return IncidentExtractionResponse.model_validate(updated_extraction)


@router.post(
    "/ai/extractions/{extraction_id}/reject",
    response_model=IncidentExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Incident Extraction Fields",
    description="Rejects extraction suggestions without modifying the confirmed Incident record.",
)
async def reject_incident_extraction(
    extraction_id: str,
    reject_req: FieldRejectionRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> IncidentExtractionResponse:
    """Rejects extraction suggestions without mutating confirmed incident data."""
    extraction = await incident_extraction_repo.get(session, extraction_id)
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident extraction {extraction_id} not found.",
        )

    investigation = await investigation_repo.get(session, extraction.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to reject extractions for this investigation.",
        )

    updated_extraction = await incident_extraction_service.reject_incident_extraction(
        session=session,
        user=current_user,
        extraction_id=extraction_id,
        reject_req=reject_req,
    )
    return IncidentExtractionResponse.model_validate(updated_extraction)
