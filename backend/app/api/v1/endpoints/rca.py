from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_active_user, verify_investigation_access
from app.models.user import User
from app.repositories.investigation_repository import investigation_repo
from app.services.rca_service import rca_service
from app.schemas.rca import (
    RCARequest,
    RCAResponse,
    RCAReviewViewResponse,
    RCAReviewPatchRequest,
    ManualCauseCreateRequest,
    CausePatchRequest,
    CauseVerifyRequest,
    CauseRejectRequest,
    RCAAcceptRequest,
    RCAEvidenceRequest,
)

router = APIRouter(tags=["Root Cause Analysis (5 Whys + Fishbone)"])

AUTHORIZED_ROLES = {"Admin", "QA", "QA Approver", "Investigator"}


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


def _check_investigation_role(user: User, action_desc: str = "perform this action"):
    user_roles = {r.name for r in user.roles}
    if not user_roles.intersection(AUTHORIZED_ROLES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Requires QA, QA Approver, Investigator, or Admin to {action_desc}.",
        )


# ===========================================================================
# RCA Initiation & Listing
# ===========================================================================

@router.post(
    "/investigations/{investigation_id}/ai/rca",
    response_model=RCAResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate AI Root Cause Analysis",
    description="Gathers confirmed incident data and document evidence, runs LangGraph 5 Whys and Fishbone causal evaluation.",
)
@router.post(
    "/ai/investigations/{investigation_id}/rca",
    response_model=RCAResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def start_rca(
    investigation_id: str,
    rca_req: RCARequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RCAResponse:
    await _get_authorized_investigation(session, investigation_id, current_user)
    _check_investigation_role(current_user, "initiate Root Cause Analysis")

    rca = await rca_service.start_rca(
        session=session,
        user=current_user,
        investigation_id=investigation_id,
        request=rca_req,
    )
    return RCAResponse.model_validate(rca)


@router.get(
    "/investigations/{investigation_id}/rca",
    response_model=List[RCAResponse],
    status_code=status.HTTP_200_OK,
    summary="List RCA Analyses for Investigation",
    description="Returns all Root Cause Analysis runs for an authorized investigation, ordered newest first.",
)
@router.get(
    "/ai/investigations/{investigation_id}/rca",
    response_model=List[RCAResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def list_rcas(
    investigation_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> List[RCAResponse]:
    await _get_authorized_investigation(session, investigation_id, current_user)
    rcas = await rca_service.get_rcas_by_investigation(
        session=session,
        investigation_id=investigation_id,
        skip=skip,
        limit=limit,
    )
    return [RCAResponse.model_validate(r) for r in rcas]


# ===========================================================================
# Single RCA & Sub-Structure Endpoints
# ===========================================================================

@router.get(
    "/rca/{rca_id}",
    response_model=RCAResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Root Cause Analysis Details",
    description="Retrieves complete structured RCA record by UUID.",
)
@router.get(
    "/ai/rca/{rca_id}",
    response_model=RCAResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_rca(
    rca_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RCAResponse:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    return RCAResponse.model_validate(rca)


@router.get(
    "/rca/{rca_id}/five-whys",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get 5 Whys Analysis Chain",
    description="Retrieves the sequential 5 Whys question-answer chain with citations.",
)
@router.get(
    "/ai/rca/{rca_id}/five-whys",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_five_whys(
    rca_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> List[Dict[str, Any]]:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    return await rca_service.get_five_whys(session, rca_id)


@router.get(
    "/rca/{rca_id}/fishbone",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Ishikawa Fishbone Tree",
    description="Retrieves the 6M Fishbone tree categorized across Manpower, Machine, Method, Material, Measurement, Environment.",
)
@router.get(
    "/ai/rca/{rca_id}/fishbone",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_fishbone(
    rca_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> Dict[str, Any]:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    return await rca_service.get_fishbone(session, rca_id)


@router.get(
    "/rca/{rca_id}/review",
    response_model=RCAReviewViewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get RCA QA Review View",
    description="Provides assembled review view with incident snapshot, causes, and evidence gaps.",
)
@router.get(
    "/ai/rca/{rca_id}/review",
    response_model=RCAReviewViewResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_rca_review(
    rca_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RCAReviewViewResponse:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    return await rca_service.get_review_view(session, rca_id)


@router.patch(
    "/rca/{rca_id}/review",
    response_model=RCAResponse,
    status_code=status.HTTP_200_OK,
    summary="Update RCA Review Notes / Overrides",
    description="Allows authorized investigator to update notes, preliminary status, or structured overrides.",
)
@router.patch(
    "/ai/rca/{rca_id}/review",
    response_model=RCAResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def update_rca_review(
    rca_id: str,
    patch_req: RCAReviewPatchRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RCAResponse:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    _check_investigation_role(current_user, "update RCA review")

    updated = await rca_service.update_review(
        session=session,
        user=current_user,
        rca_id=rca_id,
        request=patch_req,
    )
    return RCAResponse.model_validate(updated)


# ===========================================================================
# Cause Lifecycle: Add, Edit, Verify, Reject
# ===========================================================================

@router.post(
    "/rca/{rca_id}/causes",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Manually Add Cause to RCA",
    description="Allows investigator to manually insert a new hypothesis or verified cause.",
)
@router.post(
    "/ai/rca/{rca_id}/causes",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def add_manual_cause(
    rca_id: str,
    cause_req: ManualCauseCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> Dict[str, Any]:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    _check_investigation_role(current_user, "add a cause")

    return await rca_service.add_manual_cause(
        session=session,
        user=current_user,
        rca_id=rca_id,
        request=cause_req,
    )


@router.patch(
    "/rca/{rca_id}/causes/{cause_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Edit Existing Cause",
    description="Updates description, category, or notes of an existing cause node.",
)
@router.patch(
    "/ai/rca/{rca_id}/causes/{cause_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def update_cause(
    rca_id: str,
    cause_id: str,
    cause_patch: CausePatchRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> Dict[str, Any]:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    _check_investigation_role(current_user, "edit a cause")

    return await rca_service.update_cause(
        session=session,
        user=current_user,
        rca_id=rca_id,
        cause_id=cause_id,
        request=cause_patch,
    )


@router.post(
    "/rca/{rca_id}/causes/{cause_id}/verify",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Verify Cause Hypothesis",
    description="Marks a cause hypothesis as verified by documented evidence.",
)
@router.post(
    "/ai/rca/{rca_id}/causes/{cause_id}/verify",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def verify_cause(
    rca_id: str,
    cause_id: str,
    verify_req: CauseVerifyRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> Dict[str, Any]:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    _check_investigation_role(current_user, "verify a cause")

    return await rca_service.verify_cause(
        session=session,
        user=current_user,
        rca_id=rca_id,
        cause_id=cause_id,
        request=verify_req,
    )


@router.post(
    "/rca/{rca_id}/causes/{cause_id}/reject",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Reject Cause Hypothesis",
    description="Rules out a cause hypothesis with mandatory documented rationale.",
)
@router.post(
    "/ai/rca/{rca_id}/causes/{cause_id}/reject",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def reject_cause(
    rca_id: str,
    cause_id: str,
    reject_req: CauseRejectRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> Dict[str, Any]:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    _check_investigation_role(current_user, "reject a cause")

    return await rca_service.reject_cause(
        session=session,
        user=current_user,
        rca_id=rca_id,
        cause_id=cause_id,
        request=reject_req,
    )


# ===========================================================================
# Acceptance, Evidence Requests & History
# ===========================================================================

@router.post(
    "/rca/{rca_id}/accept",
    response_model=RCAResponse,
    status_code=status.HTTP_200_OK,
    summary="Accept Root Cause Analysis",
    description="Formally accepts RCA, superseding previous runs and establishing the active causal determination.",
)
@router.post(
    "/ai/rca/{rca_id}/accept",
    response_model=RCAResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def accept_rca(
    rca_id: str,
    accept_req: RCAAcceptRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RCAResponse:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    _check_investigation_role(current_user, "accept Root Cause Analysis")

    updated = await rca_service.accept_rca(
        session=session,
        user=current_user,
        rca_id=rca_id,
        request=accept_req,
    )
    return RCAResponse.model_validate(updated)


@router.post(
    "/rca/{rca_id}/request-evidence",
    response_model=RCAResponse,
    status_code=status.HTTP_200_OK,
    summary="Request Evidence for Inconclusive RCA",
    description="Transitions RCA to NEEDS_MORE_EVIDENCE and creates an evidence gap item.",
)
@router.post(
    "/ai/rca/{rca_id}/request-evidence",
    response_model=RCAResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def request_evidence(
    rca_id: str,
    evidence_req: RCAEvidenceRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> RCAResponse:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    _check_investigation_role(current_user, "request evidence")

    updated = await rca_service.request_evidence(
        session=session,
        user=current_user,
        rca_id=rca_id,
        request=evidence_req,
    )
    return RCAResponse.model_validate(updated)


@router.get(
    "/rca/{rca_id}/history",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get RCA Version & Audit History",
    description="Returns version history and audit log trail for this investigation's RCA.",
)
@router.get(
    "/ai/rca/{rca_id}/history",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def get_rca_history(
    rca_id: str,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_active_user),
) -> Dict[str, Any]:
    rca = await rca_service.get_rca(session, rca_id)
    await _get_authorized_investigation(session, rca.investigation_id, current_user)
    return await rca_service.get_rca_history(session, rca_id)
