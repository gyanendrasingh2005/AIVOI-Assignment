from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_active_user, verify_investigation_access
from app.models.user import User
from app.repositories.investigation_repository import investigation_repo
from app.repositories.ai_execution_repository import ai_execution_repo
from app.repositories.incident_extraction_repository import incident_extraction_repo
from app.repositories.risk_assessment_repository import risk_assessment_repo
from app.ai.services.ai_service import get_ai_service, AIService
from app.services.incident_extraction_service import incident_extraction_service
from app.services.risk_assessment_service import risk_assessment_service
from app.ai.schemas.common import WorkflowExecutionInput
from app.ai.schemas.execution import AIHealthResponse, AIExecutionResponse
from app.models.enums import RoleName
from app.schemas.extraction import (
    IncidentExtractionRequest,
    IncidentExtractionResponse,
    ExtractionReviewViewResponse,
    ExtractionReviewPatchRequest,
    FieldAcceptanceRequest,
    FieldRejectionRequest,
)
from app.schemas.risk_assessment import (
    RiskAssessmentRequest,
    RiskAssessmentResponse,
    RiskAssessmentReviewPatchRequest,
    RiskAssessmentAcceptRequest,
    RiskAssessmentRejectRequest,
    RiskAssessmentInfoRequest,
    RiskAssessmentReviewViewResponse,
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


# ---------------------------------------------------------------------------
# AI Quality Impact and Risk Assessment Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/investigations/{investigation_id}/ai/risk-assessments",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger AI Quality Impact & Risk Assessment",
    description="Evaluates 6 quality risk dimensions from confirmed incident information and document evidence. Generates unconfirmed draft risk evaluation.",
)
async def start_risk_assessment(
    investigation_id: str,
    request: RiskAssessmentRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RiskAssessmentResponse:
    """Initiates LangGraph Quality and Risk Assessment for an authorized investigation."""
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
            detail="Access denied: You do not have permission to trigger risk assessment for this investigation.",
        )

    assessment = await risk_assessment_service.start_risk_assessment(
        session=session,
        user=current_user,
        investigation_id=investigation_id,
        request=request,
    )
    return RiskAssessmentResponse.model_validate(assessment)


@router.get(
    "/investigations/{investigation_id}/ai/risk-assessments",
    response_model=List[RiskAssessmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List Quality Risk Assessments for Investigation",
    description="Retrieves historical quality risk assessments ordered newest first.",
)
async def list_risk_assessments(
    investigation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> List[RiskAssessmentResponse]:
    """Lists all risk assessment runs for an authorized investigation."""
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
            detail="Access denied: You do not have permission to view risk assessments for this investigation.",
        )

    assessments = await risk_assessment_service.get_assessments_by_investigation(
        session=session,
        investigation_id=investigation_id,
        skip=skip,
        limit=limit,
    )
    return [RiskAssessmentResponse.model_validate(a) for a in assessments]


@router.get(
    "/ai/risk-assessments/{assessment_id}",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Risk Assessment Details",
    description="Retrieves complete structured quality and risk assessment record.",
)
async def get_risk_assessment(
    assessment_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RiskAssessmentResponse:
    """Retrieves risk assessment record by UUID with authorization check."""
    assessment = await risk_assessment_service.get_assessment(session, assessment_id)
    investigation = await investigation_repo.get(session, assessment.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view this risk assessment.",
        )

    return RiskAssessmentResponse.model_validate(assessment)


@router.get(
    "/ai/risk-assessments/{assessment_id}/review",
    response_model=RiskAssessmentReviewViewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Risk Assessment QA Review View",
    description="Returns detailed view tailored for human QA review, including unreviewed data flags and matrix rules.",
)
async def get_risk_assessment_review(
    assessment_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RiskAssessmentReviewViewResponse:
    """Constructs dedicated QA review payload for risk assessment."""
    assessment = await risk_assessment_service.get_assessment(session, assessment_id)
    investigation = await investigation_repo.get(session, assessment.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to review this risk assessment.",
        )

    return await risk_assessment_service.get_review_view(session, assessment_id)


@router.patch(
    "/ai/risk-assessments/{assessment_id}/review",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Risk Assessment Review Decision / Overrides",
    description="Allows authorized investigator or QA to record notes, overrides, or preliminary review status.",
)
async def update_risk_assessment_review(
    assessment_id: str,
    patch_req: RiskAssessmentReviewPatchRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RiskAssessmentResponse:
    """Updates review decisions and field overrides for risk assessment."""
    assessment = await risk_assessment_service.get_assessment(session, assessment_id)
    investigation = await investigation_repo.get(session, assessment.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to update this risk assessment review.",
        )

    updated = await risk_assessment_service.update_review(
        session=session,
        user=current_user,
        assessment_id=assessment_id,
        request=patch_req,
    )
    return RiskAssessmentResponse.model_validate(updated)


@router.post(
    "/ai/risk-assessments/{assessment_id}/accept",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept Quality Risk Assessment",
    description="Explicit human QA acceptance action: supersedes previous assessments and synchronizes risk level to parent Investigation.",
)
async def accept_risk_assessment(
    assessment_id: str,
    accept_req: RiskAssessmentAcceptRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RiskAssessmentResponse:
    """Formally accepts quality risk assessment with investigation synchronization."""
    assessment = await risk_assessment_service.get_assessment(session, assessment_id)
    investigation = await investigation_repo.get(session, assessment.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to accept risk assessments for this investigation.",
        )

    user_role_names = {r.name for r in current_user.roles}
    qa_roles = {"Admin", "QA", "QA Approver", "Investigator"}
    if not user_role_names.intersection(qa_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only QA, QA Approver, Admin, or Investigator can accept risk assessments.",
        )

    updated = await risk_assessment_service.accept_assessment(
        session=session,
        user=current_user,
        assessment_id=assessment_id,
        request=accept_req,
    )
    return RiskAssessmentResponse.model_validate(updated)


@router.post(
    "/ai/risk-assessments/{assessment_id}/reject",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Quality Risk Assessment",
    description="Marks risk assessment as REJECTED. Leaves investigation risk level and priority unchanged.",
)
async def reject_risk_assessment(
    assessment_id: str,
    reject_req: RiskAssessmentRejectRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RiskAssessmentResponse:
    """Rejects risk assessment with documented reason."""
    assessment = await risk_assessment_service.get_assessment(session, assessment_id)
    investigation = await investigation_repo.get(session, assessment.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to reject this risk assessment.",
        )

    updated = await risk_assessment_service.reject_assessment(
        session=session,
        user=current_user,
        assessment_id=assessment_id,
        request=reject_req,
    )
    return RiskAssessmentResponse.model_validate(updated)


@router.post(
    "/ai/risk-assessments/{assessment_id}/request-information",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Request Information for Inconclusive Risk Assessment",
    description="Transitions assessment to NEEDS_MORE_INFORMATION and logs requested data points.",
)
async def request_risk_assessment_info(
    assessment_id: str,
    info_req: RiskAssessmentInfoRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RiskAssessmentResponse:
    """Requests additional evidence or clarification for risk assessment."""
    assessment = await risk_assessment_service.get_assessment(session, assessment_id)
    investigation = await investigation_repo.get(session, assessment.investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated investigation not found.",
        )

    has_access = await verify_investigation_access(investigation, current_user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to request information for this risk assessment.",
        )

    updated = await risk_assessment_service.request_additional_information(
        session=session,
        user=current_user,
        assessment_id=assessment_id,
        request=info_req,
    )
    return RiskAssessmentResponse.model_validate(updated)

