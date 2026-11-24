from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.user import User
from app.api.deps import get_active_user, require_permissions, verify_investigation_access
from app.repositories.investigation_repository import investigation_repo
from app.core.permissions import Permission
from app.services.evidence_gap_service import evidence_gap_service
from app.schemas.evidence_gap import (
    EvidenceGapResponse,
    EvidenceGapListResponse,
    EvidenceGapPatchRequest,
    EvidenceGapAssignRequest,
    EvidenceGapRequestEvidenceRequest,
    EvidenceGapAssociateEvidenceRequest,
    EvidenceGapResolveRequest,
    EvidenceGapRejectRequest,
    EvidenceGapWaiveRequest,
    EvidenceGapReopenRequest,
)
from app.schemas.completeness import (
    CompletenessAssessmentResponse,
    CompletenessAssessmentRequest,
    CompletenessHistoryResponse,
    CompletenessHistoryItem,
)

router = APIRouter(tags=["Evidence Gaps & Completeness"])


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


# ---------------------------------------------------------
# Assessment Endpoints
# ---------------------------------------------------------

@router.post(
    "/investigations/{investigation_id}/ai/evidence-gap-assessment",
    response_model=CompletenessAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger AI Evidence Gap Detection & Completeness Assessment",
)
async def trigger_gap_assessment(
    investigation_id: str,
    payload: Optional[CompletenessAssessmentRequest] = None,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_ASSESS)),
    session: AsyncSession = Depends(get_db),
):
    await _get_authorized_investigation(session, investigation_id, current_user)
    profile_version = payload.requirement_profile if payload and payload.requirement_profile else "1.0.0"

    try:
        assessment = await evidence_gap_service.start_evidence_gap_assessment(
            session=session,
            investigation_id=investigation_id,
            user_id=current_user.id,
            requirement_profile_version=profile_version,
        )
        return assessment
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/investigations/{investigation_id}/completeness",
    response_model=CompletenessAssessmentResponse,
    summary="Get Latest Investigation Completeness Assessment",
)
async def get_latest_completeness(
    investigation_id: str,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    await _get_authorized_investigation(session, investigation_id, current_user)
    assessment = await evidence_gap_service.get_latest_completeness_assessment(session, investigation_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completeness assessment found for investigation {investigation_id}.",
        )
    return assessment


@router.get(
    "/investigations/{investigation_id}/completeness/history",
    response_model=CompletenessHistoryResponse,
    summary="Get Investigation Completeness History Versions",
)
async def get_completeness_history(
    investigation_id: str,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    await _get_authorized_investigation(session, investigation_id, current_user)
    history = await evidence_gap_service.get_completeness_history(session, investigation_id, limit=limit)
    items = [
        CompletenessHistoryItem(
            id=a.id,
            assessment_version=a.assessment_version,
            overall_status=a.overall_status,
            completeness_score=a.completeness_score,
            total_unresolved_gaps=a.total_unresolved_gaps,
            critical_unresolved_gaps=a.critical_unresolved_gaps,
            created_at=a.created_at,
            created_by=a.created_by,
        )
        for a in history
    ]
    return CompletenessHistoryResponse(
        investigation_id=investigation_id,
        total_versions=len(items),
        assessments=items,
    )


# ---------------------------------------------------------
# Gap Listing & CRUD
# ---------------------------------------------------------

@router.get(
    "/investigations/{investigation_id}/evidence-gaps",
    response_model=EvidenceGapListResponse,
    summary="List Evidence Gaps with Filters and Pagination",
)
async def list_investigation_evidence_gaps(
    investigation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    priority: Optional[str] = None,
    gap_status: Optional[str] = Query(None, alias="status"),
    assigned_to: Optional[str] = None,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    await _get_authorized_investigation(session, investigation_id, current_user)
    gaps, total = await evidence_gap_service.list_evidence_gaps(
        session,
        investigation_id=investigation_id,
        skip=skip,
        limit=limit,
        category=category,
        priority=priority,
        status=gap_status,
        assigned_to=assigned_to,
    )
    return EvidenceGapListResponse(
        items=[EvidenceGapResponse.model_validate(g) for g in gaps],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/evidence-gaps/{gap_id}",
    response_model=EvidenceGapResponse,
    summary="Get Evidence Gap Details",
)
async def get_evidence_gap_details(
    gap_id: str,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    gap = await evidence_gap_service.get_evidence_gap(session, gap_id)
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence gap not found.")
    await _get_authorized_investigation(session, gap.investigation_id, current_user)
    return EvidenceGapResponse.model_validate(gap)


@router.patch(
    "/evidence-gaps/{gap_id}",
    response_model=EvidenceGapResponse,
    summary="Update Evidence Gap Metadata",
)
async def patch_evidence_gap(
    gap_id: str,
    payload: EvidenceGapPatchRequest,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_EDIT)),
    session: AsyncSession = Depends(get_db),
):
    gap = await evidence_gap_service.get_evidence_gap(session, gap_id)
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence gap not found.")
    await _get_authorized_investigation(session, gap.investigation_id, current_user)

    updated = await evidence_gap_service.patch_evidence_gap(
        session,
        gap_id=gap_id,
        user_id=current_user.id,
        patch_data=payload.model_dump(exclude_unset=True),
    )
    return EvidenceGapResponse.model_validate(updated)


@router.post(
    "/evidence-gaps/{gap_id}/assign",
    response_model=EvidenceGapResponse,
    summary="Assign Evidence Gap to Owner",
)
async def assign_evidence_gap(
    gap_id: str,
    payload: EvidenceGapAssignRequest,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_ASSIGN)),
    session: AsyncSession = Depends(get_db),
):
    gap = await evidence_gap_service.get_evidence_gap(session, gap_id)
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence gap not found.")
    await _get_authorized_investigation(session, gap.investigation_id, current_user)

    updated = await evidence_gap_service.assign_evidence_gap(
        session,
        gap_id=gap_id,
        user_id=current_user.id,
        assigned_to=payload.assigned_to,
        due_date=payload.due_date,
    )
    return EvidenceGapResponse.model_validate(updated)


@router.post(
    "/evidence-gaps/{gap_id}/request-evidence",
    response_model=EvidenceGapResponse,
    summary="Request Supporting Evidence for Gap",
)
async def request_evidence_for_gap(
    gap_id: str,
    payload: EvidenceGapRequestEvidenceRequest,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_REQUEST)),
    session: AsyncSession = Depends(get_db),
):
    gap = await evidence_gap_service.get_evidence_gap(session, gap_id)
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence gap not found.")
    await _get_authorized_investigation(session, gap.investigation_id, current_user)

    updated = await evidence_gap_service.request_evidence(
        session,
        gap_id=gap_id,
        user_id=current_user.id,
        notes=payload.notes,
        suggested_source=payload.suggested_source,
    )
    return EvidenceGapResponse.model_validate(updated)


@router.post(
    "/evidence-gaps/{gap_id}/associate-evidence",
    response_model=EvidenceGapResponse,
    summary="Associate Existing Investigation Evidence to Gap",
)
async def associate_evidence_to_gap(
    gap_id: str,
    payload: EvidenceGapAssociateEvidenceRequest,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_EDIT)),
    session: AsyncSession = Depends(get_db),
):
    gap = await evidence_gap_service.get_evidence_gap(session, gap_id)
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence gap not found.")
    await _get_authorized_investigation(session, gap.investigation_id, current_user)

    try:
        updated = await evidence_gap_service.associate_evidence(
            session,
            gap_id=gap_id,
            user_id=current_user.id,
            evidence_ids=payload.evidence_ids,
        )
        return EvidenceGapResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/evidence-gaps/{gap_id}/resolve",
    response_model=EvidenceGapResponse,
    summary="Resolve Evidence Gap with Justification",
)
async def resolve_evidence_gap(
    gap_id: str,
    payload: EvidenceGapResolveRequest,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_RESOLVE)),
    session: AsyncSession = Depends(get_db),
):
    gap = await evidence_gap_service.get_evidence_gap(session, gap_id)
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence gap not found.")
    await _get_authorized_investigation(session, gap.investigation_id, current_user)

    try:
        updated = await evidence_gap_service.resolve_evidence_gap(
            session,
            gap_id=gap_id,
            user_id=current_user.id,
            justification=payload.justification,
            evidence_ids=payload.evidence_ids,
        )
        return EvidenceGapResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/evidence-gaps/{gap_id}/reject",
    response_model=EvidenceGapResponse,
    summary="Reject Evidence Gap with Mandatory Justification",
)
async def reject_evidence_gap(
    gap_id: str,
    payload: EvidenceGapRejectRequest,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_REJECT)),
    session: AsyncSession = Depends(get_db),
):
    gap = await evidence_gap_service.get_evidence_gap(session, gap_id)
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence gap not found.")
    await _get_authorized_investigation(session, gap.investigation_id, current_user)

    try:
        updated = await evidence_gap_service.reject_evidence_gap(
            session,
            gap_id=gap_id,
            user_id=current_user.id,
            justification=payload.justification,
        )
        return EvidenceGapResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/evidence-gaps/{gap_id}/waive",
    response_model=EvidenceGapResponse,
    summary="Waive Evidence Gap with Regulatory Justification",
)
async def waive_evidence_gap(
    gap_id: str,
    payload: EvidenceGapWaiveRequest,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_WAIVE)),
    session: AsyncSession = Depends(get_db),
):
    gap = await evidence_gap_service.get_evidence_gap(session, gap_id)
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence gap not found.")
    await _get_authorized_investigation(session, gap.investigation_id, current_user)

    try:
        updated = await evidence_gap_service.waive_evidence_gap(
            session,
            gap_id=gap_id,
            user_id=current_user.id,
            justification=payload.justification,
            policy_reference=payload.policy_reference,
        )
        return EvidenceGapResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.post(
    "/evidence-gaps/{gap_id}/reopen",
    response_model=EvidenceGapResponse,
    summary="Reopen Previously Resolved Evidence Gap",
)
async def reopen_evidence_gap(
    gap_id: str,
    payload: EvidenceGapReopenRequest,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_REOPEN)),
    session: AsyncSession = Depends(get_db),
):
    gap = await evidence_gap_service.get_evidence_gap(session, gap_id)
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence gap not found.")
    await _get_authorized_investigation(session, gap.investigation_id, current_user)

    try:
        updated = await evidence_gap_service.reopen_evidence_gap(
            session,
            gap_id=gap_id,
            user_id=current_user.id,
            justification=payload.justification,
        )
        return EvidenceGapResponse.model_validate(updated)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))


@router.get(
    "/evidence-gaps/{gap_id}/history",
    response_model=List[Dict[str, Any]],
    summary="Get Complete Evidence Gap Lifecycle History",
)
async def get_evidence_gap_history(
    gap_id: str,
    current_user: User = Depends(require_permissions(Permission.EVIDENCE_GAP_VIEW)),
    session: AsyncSession = Depends(get_db),
):
    gap = await evidence_gap_service.get_evidence_gap(session, gap_id)
    if not gap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence gap not found.")
    await _get_authorized_investigation(session, gap.investigation_id, current_user)

    return await evidence_gap_service.get_gap_history(session, gap_id)
