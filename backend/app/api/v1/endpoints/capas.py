from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user import User
from app.api.deps import get_active_user, require_permissions, verify_investigation_access
from app.repositories.investigation_repository import investigation_repo
from app.core.permissions import Permission
from app.services.capa_service import capa_service
from app.schemas.capa import (
    CAPAAIRecommendationRequest,
    CAPARecommendationResponse,
    CAPARecommendationListResponse,
    CAPARecommendationPatchRequest,
    CAPARecommendationAcceptRequest,
    CAPARecommendationRejectRequest,
    CAPAPlanCreateRequest,
    CAPAPatchRequest,
    CAPASubmitReviewRequest,
    CAPASubmitApprovalRequest,
    CAPAApproveRequest,
    CAPARejectRequest,
    CAPAResponse,
    CAPAListResponse,
    CAPATaskCreateRequest,
    CAPATaskPatchRequest,
    CAPATaskAssignRequest,
    CAPATaskSubmitCompletionRequest,
    CAPATaskApproveCompletionRequest,
    CAPATaskRejectCompletionRequest,
    CAPATaskResponse,
    CAPATaskListResponse,
    EffectivenessCheckCreateRequest,
    EffectivenessCheckPatchRequest,
    EffectivenessCheckEvidenceAttachRequest,
    EffectivenessCheckRecordResultRequest,
    EffectivenessCheckFinalizeDecisionRequest,
    EffectivenessCheckReopenCAPARequest,
    EffectivenessCheckFollowupInvestigationRequest,
    EffectivenessCheckResponse,
    EffectivenessCheckListResponse,
    CAPAClosureValidationResponse,
    CAPACloseRequest,
    CAPAReopenRequest,
    CAPAMonitoringSummaryResponse,
)

router = APIRouter(tags=["Corrective & Preventive Actions (CAPA)"])


async def _get_authorized_investigation(
    session: AsyncSession,
    investigation_id: str,
    user: User,
):
    investigation = await investigation_repo.get(session, investigation_id)
    if not investigation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Investigation {investigation_id} not found.",
        )
    has_access = await verify_investigation_access(investigation, user)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to view or modify this investigation.",
        )
    return investigation


# ===========================================================================
# 1. CAPA Recommendations Endpoints
# ===========================================================================

@router.post(
    "/investigations/{investigation_id}/ai/capa-recommendations",
    response_model=List[CAPARecommendationResponse],
    status_code=status.HTTP_200_OK,
    summary="Generate AI-Assisted CAPA Recommendations",
)
async def generate_capa_recommendations(
    investigation_id: str,
    payload: Optional[CAPAAIRecommendationRequest] = None,
    current_user: User = Depends(require_permissions(Permission.CAPA_RECOMMEND)),
    session: AsyncSession = Depends(get_db),
):
    await _get_authorized_investigation(session, investigation_id, current_user)
    focus = payload.focus_action_type if payload else None

    try:
        recs = await capa_service.generate_recommendations(
            session=session,
            investigation_id=investigation_id,
            user_id=current_user.id,
            focus_action_type=focus,
        )
        return [CAPARecommendationResponse.model_validate(r) for r in recs]
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/investigations/{investigation_id}/capa-recommendations",
    response_model=CAPARecommendationListResponse,
    summary="List CAPA Recommendations with Filters",
)
async def list_capa_recommendations(
    investigation_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    action_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(require_permissions(Permission.CAPA_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    await _get_authorized_investigation(session, investigation_id, current_user)
    items, total = await capa_service.list_recommendations(
        session,
        investigation_id=investigation_id,
        status=status_filter,
        action_type=action_type,
        skip=skip,
        limit=limit,
    )
    return CAPARecommendationListResponse(
        items=[CAPARecommendationResponse.model_validate(i) for i in items],
        total=total,
        investigation_id=investigation_id,
    )


@router.get(
    "/capa-recommendations/{recommendation_id}",
    response_model=CAPARecommendationResponse,
    summary="Get Single CAPA Recommendation Details",
)
async def get_capa_recommendation(
    recommendation_id: str,
    current_user: User = Depends(require_permissions(Permission.CAPA_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    rec = await capa_service.get_recommendation(session, recommendation_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")
    await _get_authorized_investigation(session, rec.investigation_id, current_user)
    return CAPARecommendationResponse.model_validate(rec)


@router.patch(
    "/capa-recommendations/{recommendation_id}",
    response_model=CAPARecommendationResponse,
    summary="Edit CAPA Recommendation Details",
)
async def patch_capa_recommendation(
    recommendation_id: str,
    payload: CAPARecommendationPatchRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_EDIT)),
    session: AsyncSession = Depends(get_db),
):
    rec = await capa_service.get_recommendation(session, recommendation_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")
    await _get_authorized_investigation(session, rec.investigation_id, current_user)

    updated = await capa_service.patch_recommendation(
        session=session,
        recommendation_id=recommendation_id,
        user_id=current_user.id,
        patch_data=payload.model_dump(exclude_unset=True),
    )
    return CAPARecommendationResponse.model_validate(updated)


@router.post(
    "/capa-recommendations/{recommendation_id}/accept",
    response_model=CAPARecommendationResponse,
    summary="Accept CAPA Recommendation via Human Review",
)
async def accept_capa_recommendation(
    recommendation_id: str,
    payload: Optional[CAPARecommendationAcceptRequest] = None,
    current_user: User = Depends(require_permissions(Permission.CAPA_REVIEW)),
    session: AsyncSession = Depends(get_db),
):
    rec = await capa_service.get_recommendation(session, recommendation_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")
    await _get_authorized_investigation(session, rec.investigation_id, current_user)

    notes = payload.notes if payload else None
    updated = await capa_service.accept_recommendation(
        session=session,
        recommendation_id=recommendation_id,
        user_id=current_user.id,
        notes=notes,
    )
    return CAPARecommendationResponse.model_validate(updated)


@router.post(
    "/capa-recommendations/{recommendation_id}/reject",
    response_model=CAPARecommendationResponse,
    summary="Reject CAPA Recommendation with Mandatory Justification",
)
async def reject_capa_recommendation(
    recommendation_id: str,
    payload: CAPARecommendationRejectRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_REJECT)),
    session: AsyncSession = Depends(get_db),
):
    rec = await capa_service.get_recommendation(session, recommendation_id)
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendation not found.")
    await _get_authorized_investigation(session, rec.investigation_id, current_user)

    try:
        updated = await capa_service.reject_recommendation(
            session=session,
            recommendation_id=recommendation_id,
            user_id=current_user.id,
            justification=payload.justification,
        )
        return CAPARecommendationResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


# ===========================================================================
# 2. CAPA Plans Endpoints
# ===========================================================================

@router.post(
    "/investigations/{investigation_id}/capas",
    response_model=CAPAResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a CAPA Plan",
)
async def create_capa_plan(
    investigation_id: str,
    payload: CAPAPlanCreateRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_CREATE)),
    session: AsyncSession = Depends(get_db),
):
    await _get_authorized_investigation(session, investigation_id, current_user)

    capa = await capa_service.create_capa_plan(
        session=session,
        investigation_id=investigation_id,
        user_id=current_user.id,
        plan_data=payload.model_dump(),
    )
    return CAPAResponse.model_validate(capa)


@router.get(
    "/investigations/{investigation_id}/capas",
    response_model=CAPAListResponse,
    summary="List CAPA Plans for an Investigation",
)
async def list_investigation_capas(
    investigation_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permissions(Permission.CAPA_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    await _get_authorized_investigation(session, investigation_id, current_user)
    items, total = await capa_service.list_capas(
        session=session,
        investigation_id=investigation_id,
        status=status_filter,
        priority=priority,
        skip=skip,
        limit=limit,
    )
    return CAPAListResponse(
        items=[CAPAResponse.model_validate(c) for c in items],
        total=total,
        investigation_id=investigation_id,
    )


@router.get(
    "/capas/{capa_id}",
    response_model=CAPAResponse,
    summary="Get Detailed CAPA Plan",
)
async def get_capa_plan(
    capa_id: str,
    current_user: User = Depends(require_permissions(Permission.CAPA_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)
    return CAPAResponse.model_validate(capa)


@router.patch(
    "/capas/{capa_id}",
    response_model=CAPAResponse,
    summary="Update Editable CAPA Plan Metadata",
)
async def patch_capa_plan(
    capa_id: str,
    payload: CAPAPatchRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_EDIT)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    try:
        updated = await capa_service.patch_capa(
            session=session,
            capa_id=capa_id,
            user_id=current_user.id,
            patch_data=payload.model_dump(exclude_unset=True),
        )
        return CAPAResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/capas/{capa_id}/submit-review",
    response_model=CAPAResponse,
    summary="Submit CAPA Plan for Review",
)
async def submit_capa_for_review(
    capa_id: str,
    payload: Optional[CAPASubmitReviewRequest] = None,
    current_user: User = Depends(require_permissions(Permission.CAPA_SUBMIT)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    comments = payload.comments if payload else None
    updated = await capa_service.submit_capa_for_review(session, capa_id, current_user.id, comments)
    return CAPAResponse.model_validate(updated)


@router.post(
    "/capas/{capa_id}/submit-approval",
    response_model=CAPAResponse,
    summary="Submit CAPA Plan for Authorized Approval",
)
async def submit_capa_for_approval(
    capa_id: str,
    payload: Optional[CAPASubmitApprovalRequest] = None,
    current_user: User = Depends(require_permissions(Permission.CAPA_SUBMIT)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    comments = payload.comments if payload else None
    updated = await capa_service.submit_capa_for_approval(session, capa_id, current_user.id, comments)
    return CAPAResponse.model_validate(updated)


@router.post(
    "/capas/{capa_id}/approve",
    response_model=CAPAResponse,
    summary="Approve CAPA Plan by Authorized QA Approver",
)
async def approve_capa_plan(
    capa_id: str,
    payload: Optional[CAPAApproveRequest] = None,
    current_user: User = Depends(require_permissions(Permission.CAPA_APPROVE)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    comments = payload.comments if payload else None
    updated = await capa_service.approve_capa(session, capa_id, current_user.id, comments)
    return CAPAResponse.model_validate(updated)


@router.post(
    "/capas/{capa_id}/reject",
    response_model=CAPAResponse,
    summary="Reject CAPA Plan with Justification",
)
async def reject_capa_plan(
    capa_id: str,
    payload: CAPARejectRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_REJECT)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    try:
        updated = await capa_service.reject_capa(session, capa_id, current_user.id, payload.justification)
        return CAPAResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


# ===========================================================================
# 3. CAPA Tasks Endpoints
# ===========================================================================

@router.post(
    "/capas/{capa_id}/tasks",
    response_model=CAPATaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a CAPA Action Task",
)
async def create_capa_task(
    capa_id: str,
    payload: CAPATaskCreateRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_TASK_EDIT)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    task = await capa_service.create_task(session, capa_id, current_user.id, payload.model_dump())
    return CAPATaskResponse.model_validate(task)


@router.get(
    "/capas/{capa_id}/tasks",
    response_model=CAPATaskListResponse,
    summary="List Action Tasks for a CAPA",
)
async def list_capa_tasks(
    capa_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_permissions(Permission.CAPA_TASK_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    tasks = await capa_service.list_tasks(session, capa_id, status=status_filter)
    return CAPATaskListResponse(
        items=[CAPATaskResponse.model_validate(t) for t in tasks],
        total=len(tasks),
        capa_id=capa_id,
    )


@router.get(
    "/capa-tasks/{task_id}",
    response_model=CAPATaskResponse,
    summary="Get Detailed CAPA Task",
)
async def get_capa_task(
    task_id: str,
    current_user: User = Depends(require_permissions(Permission.CAPA_TASK_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    task = await capa_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.capa:
        await _get_authorized_investigation(session, task.capa.investigation_id, current_user)
    return CAPATaskResponse.model_validate(task)


@router.patch(
    "/capa-tasks/{task_id}",
    response_model=CAPATaskResponse,
    summary="Update CAPA Task Metadata",
)
async def patch_capa_task(
    task_id: str,
    payload: CAPATaskPatchRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_TASK_EDIT)),
    session: AsyncSession = Depends(get_db),
):
    task = await capa_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.capa:
        await _get_authorized_investigation(session, task.capa.investigation_id, current_user)

    updated = await capa_service.patch_task(
        session=session,
        task_id=task_id,
        user_id=current_user.id,
        patch_data=payload.model_dump(exclude_unset=True),
    )
    return CAPATaskResponse.model_validate(updated)


@router.post(
    "/capa-tasks/{task_id}/assign",
    response_model=CAPATaskResponse,
    summary="Assign Task to Owner & Due Date",
)
async def assign_capa_task(
    task_id: str,
    payload: CAPATaskAssignRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_TASK_ASSIGN)),
    session: AsyncSession = Depends(get_db),
):
    task = await capa_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.capa:
        await _get_authorized_investigation(session, task.capa.investigation_id, current_user)

    updated = await capa_service.assign_task(
        session=session,
        task_id=task_id,
        user_id=current_user.id,
        assigned_to=payload.assigned_to,
        due_date=payload.due_date,
        department=payload.department,
    )
    return CAPATaskResponse.model_validate(updated)


@router.post(
    "/capa-tasks/{task_id}/submit-completion",
    response_model=CAPATaskResponse,
    summary="Submit Task Completion Evidence for Review",
)
async def submit_task_completion(
    task_id: str,
    payload: CAPATaskSubmitCompletionRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_TASK_SUBMIT)),
    session: AsyncSession = Depends(get_db),
):
    task = await capa_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.capa:
        await _get_authorized_investigation(session, task.capa.investigation_id, current_user)

    try:
        updated = await capa_service.submit_task_completion(
            session=session,
            task_id=task_id,
            user_id=current_user.id,
            completion_notes=payload.completion_notes,
            evidence_references=payload.evidence_references,
        )
        return CAPATaskResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/capa-tasks/{task_id}/approve-completion",
    response_model=CAPATaskResponse,
    summary="Approve Task Completion by Authorized Reviewer",
)
async def approve_task_completion(
    task_id: str,
    payload: Optional[CAPATaskApproveCompletionRequest] = None,
    current_user: User = Depends(require_permissions(Permission.CAPA_TASK_REVIEW)),
    session: AsyncSession = Depends(get_db),
):
    task = await capa_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.capa:
        await _get_authorized_investigation(session, task.capa.investigation_id, current_user)

    comments = payload.comments if payload else None
    updated = await capa_service.approve_task_completion(
        session=session,
        task_id=task_id,
        user_id=current_user.id,
        comments=comments,
    )
    return CAPATaskResponse.model_validate(updated)


@router.post(
    "/capa-tasks/{task_id}/reject-completion",
    response_model=CAPATaskResponse,
    summary="Reject Task Completion Submission with Justification",
)
async def reject_task_completion(
    task_id: str,
    payload: CAPATaskRejectCompletionRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_TASK_REVIEW)),
    session: AsyncSession = Depends(get_db),
):
    task = await capa_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.capa:
        await _get_authorized_investigation(session, task.capa.investigation_id, current_user)

    try:
        updated = await capa_service.reject_task_completion(
            session=session,
            task_id=task_id,
            user_id=current_user.id,
            justification=payload.justification,
        )
        return CAPATaskResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


# ===========================================================================
# 4. History Endpoints
# ===========================================================================

@router.get(
    "/capas/{capa_id}/history",
    response_model=List[Dict[str, Any]],
    summary="Get Complete CAPA Plan Audit History",
)
async def get_capa_history(
    capa_id: str,
    current_user: User = Depends(require_permissions(Permission.CAPA_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    return await capa_service.get_capa_history(session, capa_id)


@router.get(
    "/capa-tasks/{task_id}/history",
    response_model=List[Dict[str, Any]],
    summary="Get Complete CAPA Task Audit History",
)
async def get_task_history(
    task_id: str,
    current_user: User = Depends(require_permissions(Permission.CAPA_TASK_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    task = await capa_service.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    if task.capa:
        await _get_authorized_investigation(session, task.capa.investigation_id, current_user)

    return await capa_service.get_task_history(session, task_id)


# ===========================================================================
# 4. CAPA Implementation Monitoring Endpoints
# ===========================================================================

@router.get(
    "/investigations/{investigation_id}/capa-monitoring",
    response_model=CAPAMonitoringSummaryResponse,
    summary="Get Implementation Monitoring Overview for Investigation CAPAs",
)
async def get_investigation_capa_monitoring(
    investigation_id: str,
    current_user: User = Depends(require_permissions(Permission.CAPA_MONITORING_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    await _get_authorized_investigation(session, investigation_id, current_user)
    data = await capa_service.get_investigation_capa_monitoring(session, investigation_id)
    return CAPAMonitoringSummaryResponse(**data)


@router.get(
    "/capas/{capa_id}/monitoring",
    response_model=Dict[str, Any],
    summary="Get Detailed Implementation Monitoring for Single CAPA",
)
async def get_capa_monitoring(
    capa_id: str,
    current_user: User = Depends(require_permissions(Permission.CAPA_MONITORING_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)
    return await capa_service.get_capa_monitoring(session, capa_id)


# ===========================================================================
# 5. Effectiveness Checks Endpoints
# ===========================================================================

@router.post(
    "/capas/{capa_id}/effectiveness-checks",
    response_model=EffectivenessCheckResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule an Effectiveness Verification Check",
)
async def create_effectiveness_check(
    capa_id: str,
    payload: EffectivenessCheckCreateRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_EFFECTIVENESS_CREATE)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    check = await capa_service.create_effectiveness_check(
        session=session,
        capa_id=capa_id,
        user_id=current_user.id,
        check_data=payload.model_dump(),
    )
    return EffectivenessCheckResponse.model_validate(check)


@router.get(
    "/capas/{capa_id}/effectiveness-checks",
    response_model=EffectivenessCheckListResponse,
    summary="List Effectiveness Verification Checks for a CAPA",
)
async def list_effectiveness_checks(
    capa_id: str,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_permissions(Permission.CAPA_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    checks = await capa_service.list_effectiveness_checks(session, capa_id=capa_id, status=status_filter)
    return EffectivenessCheckListResponse(
        items=[EffectivenessCheckResponse.model_validate(c) for c in checks],
        total=len(checks),
        capa_id=capa_id,
    )


@router.get(
    "/effectiveness-checks/{check_id}",
    response_model=EffectivenessCheckResponse,
    summary="Get Single Effectiveness Check Details",
)
async def get_effectiveness_check(
    check_id: str,
    current_user: User = Depends(require_permissions(Permission.CAPA_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    check = await capa_service.get_effectiveness_check(session, check_id)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Effectiveness check not found.")
    if check.capa:
        await _get_authorized_investigation(session, check.capa.investigation_id, current_user)
    return EffectivenessCheckResponse.model_validate(check)


@router.patch(
    "/effectiveness-checks/{check_id}",
    response_model=EffectivenessCheckResponse,
    summary="Update Effectiveness Check Parameters",
)
async def patch_effectiveness_check(
    check_id: str,
    payload: EffectivenessCheckPatchRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_EFFECTIVENESS_REVIEW)),
    session: AsyncSession = Depends(get_db),
):
    check = await capa_service.get_effectiveness_check(session, check_id)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Effectiveness check not found.")
    if check.capa:
        await _get_authorized_investigation(session, check.capa.investigation_id, current_user)

    try:
        updated = await capa_service.patch_effectiveness_check(
            session=session,
            check_id=check_id,
            user_id=current_user.id,
            patch_data=payload.model_dump(exclude_unset=True),
        )
        return EffectivenessCheckResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.delete(
    "/effectiveness-checks/{check_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Unfinalized Effectiveness Check",
)
async def delete_effectiveness_check(
    check_id: str,
    current_user: User = Depends(require_permissions(Permission.CAPA_EFFECTIVENESS_CREATE)),
    session: AsyncSession = Depends(get_db),
):
    check = await capa_service.get_effectiveness_check(session, check_id)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Effectiveness check not found.")
    if check.capa:
        await _get_authorized_investigation(session, check.capa.investigation_id, current_user)

    try:
        await capa_service.delete_effectiveness_check(session, check_id, current_user.id)
        return None
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/effectiveness-checks/{check_id}/evidence",
    response_model=EffectivenessCheckResponse,
    summary="Attach Verification Evidence to Check",
)
async def attach_evidence_to_check(
    check_id: str,
    payload: EffectivenessCheckEvidenceAttachRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_EFFECTIVENESS_REVIEW)),
    session: AsyncSession = Depends(get_db),
):
    check = await capa_service.get_effectiveness_check(session, check_id)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Effectiveness check not found.")
    if check.capa:
        await _get_authorized_investigation(session, check.capa.investigation_id, current_user)

    updated = await capa_service.attach_evidence_to_effectiveness_check(
        session=session,
        check_id=check_id,
        user_id=current_user.id,
        evidence_ids=payload.evidence_ids,
    )
    return EffectivenessCheckResponse.model_validate(updated)


@router.post(
    "/effectiveness-checks/{check_id}/ai-assess",
    response_model=EffectivenessCheckResponse,
    summary="Run AI Advisory Effectiveness Assessment",
)
async def run_ai_effectiveness_assessment(
    check_id: str,
    current_user: User = Depends(require_permissions(Permission.CAPA_EFFECTIVENESS_REVIEW)),
    session: AsyncSession = Depends(get_db),
):
    check = await capa_service.get_effectiveness_check(session, check_id)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Effectiveness check not found.")
    if check.capa:
        await _get_authorized_investigation(session, check.capa.investigation_id, current_user)

    try:
        updated = await capa_service.assess_effectiveness_ai(
            session=session,
            check_id=check_id,
            user_id=current_user.id,
        )
        return EffectivenessCheckResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/effectiveness-checks/{check_id}/record-result",
    response_model=EffectivenessCheckResponse,
    summary="Record Empirical Verification Results & Recurrence Data",
)
async def record_effectiveness_result(
    check_id: str,
    payload: EffectivenessCheckRecordResultRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_EFFECTIVENESS_REVIEW)),
    session: AsyncSession = Depends(get_db),
):
    check = await capa_service.get_effectiveness_check(session, check_id)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Effectiveness check not found.")
    if check.capa:
        await _get_authorized_investigation(session, check.capa.investigation_id, current_user)

    updated = await capa_service.record_effectiveness_result(
        session=session,
        check_id=check_id,
        user_id=current_user.id,
        result=payload.result,
        conclusion=payload.conclusion,
        recurrence_observed=payload.recurrence_observed,
        reviewer_comments=payload.reviewer_comments,
    )
    return EffectivenessCheckResponse.model_validate(updated)


@router.post(
    "/effectiveness-checks/{check_id}/finalize-decision",
    response_model=EffectivenessCheckResponse,
    summary="Finalize Authorized Quality Decision on Effectiveness",
)
async def finalize_effectiveness_decision(
    check_id: str,
    payload: EffectivenessCheckFinalizeDecisionRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_EFFECTIVENESS_APPROVE)),
    session: AsyncSession = Depends(get_db),
):
    check = await capa_service.get_effectiveness_check(session, check_id)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Effectiveness check not found.")
    if check.capa:
        await _get_authorized_investigation(session, check.capa.investigation_id, current_user)

    try:
        updated = await capa_service.finalize_effectiveness_decision(
            session=session,
            check_id=check_id,
            user_id=current_user.id,
            decision=payload.decision,
            decision_reason=payload.decision_reason,
        )
        return EffectivenessCheckResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/effectiveness-checks/{check_id}/reopen-capa",
    response_model=CAPAResponse,
    summary="Reopen CAPA Plan Due to Failed Effectiveness",
)
async def reopen_capa_from_check(
    check_id: str,
    payload: EffectivenessCheckReopenCAPARequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_REOPEN)),
    session: AsyncSession = Depends(get_db),
):
    check = await capa_service.get_effectiveness_check(session, check_id)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Effectiveness check not found.")
    if check.capa:
        await _get_authorized_investigation(session, check.capa.investigation_id, current_user)

    updated_capa = await capa_service.reopen_capa(
        session=session,
        capa_id=check.capa_id,
        user_id=current_user.id,
        reason=payload.reason,
        new_tasks=payload.new_tasks,
    )
    return CAPAResponse.model_validate(updated_capa)


@router.post(
    "/effectiveness-checks/{check_id}/create-followup-investigation",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Linked Follow-up Investigation for Recurrence",
)
async def create_followup_investigation_from_check(
    check_id: str,
    payload: EffectivenessCheckFollowupInvestigationRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_EFFECTIVENESS_APPROVE)),
    session: AsyncSession = Depends(get_db),
):
    check = await capa_service.get_effectiveness_check(session, check_id)
    if not check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Effectiveness check not found.")
    if check.capa:
        await _get_authorized_investigation(session, check.capa.investigation_id, current_user)

    try:
        followup_id = await capa_service.create_followup_investigation_from_check(
            session=session,
            check_id=check_id,
            user_id=current_user.id,
            justification=payload.justification,
            title=payload.title,
        )
        return {"followup_investigation_id": followup_id}
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


# ===========================================================================
# 6. CAPA Closure Endpoints
# ===========================================================================

@router.get(
    "/capas/{capa_id}/closure-validation",
    response_model=CAPAClosureValidationResponse,
    summary="Validate Prerequisites for CAPA Closure",
)
async def validate_capa_closure(
    capa_id: str,
    current_user: User = Depends(require_permissions(Permission.CAPA_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    data = await capa_service.validate_capa_closure(session, capa_id)
    return CAPAClosureValidationResponse(**data)


@router.post(
    "/capas/{capa_id}/close",
    response_model=CAPAResponse,
    summary="Authorize Formal Closure of CAPA Plan",
)
async def close_capa_plan(
    capa_id: str,
    payload: CAPACloseRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_CLOSE)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    try:
        closed = await capa_service.close_capa(
            session=session,
            capa_id=capa_id,
            user_id=current_user.id,
            comments=payload.comments,
        )
        return CAPAResponse.model_validate(closed)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/capas/{capa_id}/reopen",
    response_model=CAPAResponse,
    summary="Reopen an Existing CAPA Plan",
)
async def reopen_capa_plan(
    capa_id: str,
    payload: CAPAReopenRequest,
    current_user: User = Depends(require_permissions(Permission.CAPA_REOPEN)),
    session: AsyncSession = Depends(get_db),
):
    capa = await capa_service.get_capa(session, capa_id)
    if not capa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="CAPA plan not found.")
    await _get_authorized_investigation(session, capa.investigation_id, current_user)

    try:
        reopened = await capa_service.reopen_capa(
            session=session,
            capa_id=capa_id,
            user_id=current_user.id,
            reason=payload.justification,
        )
        return CAPAResponse.model_validate(reopened)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

