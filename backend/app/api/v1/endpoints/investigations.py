from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.investigation import (
    InvestigationCreateRequest,
    InvestigationUpdateRequest,
    InvestigationAssignRequest,
    InvestigationTransitionRequest,
    InvestigationListItem,
    InvestigationListResponse,
    InvestigationDetailResponse,
    InvestigationTimelineResponse,
    DashboardSummaryResponse,
)
from app.services.investigation_service import investigation_service

router = APIRouter(prefix="/investigations", tags=["Investigation Management"])


# ==========================================
# Dashboard & Analytics Endpoints (Ordered Before /{id})
# ==========================================

@router.get(
    "/dashboard/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Investigation quality KPI metrics",
    description="Aggregates open, closed, risk level, and overdue statistics scoped to the user's role.",
)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardSummaryResponse:
    return await investigation_service.get_dashboard_summary(session, user=current_user)


@router.get(
    "/dashboard/recent",
    response_model=List[InvestigationListItem],
    status_code=status.HTTP_200_OK,
    summary="Recently updated investigations",
    description="Lists recently active investigations accessible to the user.",
)
async def get_dashboard_recent(
    limit: int = Query(10, ge=1, le=50, description="Max entries to retrieve"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[InvestigationListItem]:
    return await investigation_service.get_dashboard_recent(session, user=current_user, limit=limit)


# ==========================================
# Primary CRUD & Search Endpoints
# ==========================================

@router.post(
    "",
    response_model=InvestigationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create pharmaceutical investigation",
    description="Creates an investigation and contemporaneous incident intake record with concurrency-safe numbering.",
)
async def create_investigation(
    create_in: InvestigationCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvestigationDetailResponse:
    ip_addr = request.client.host if request.client else None
    return await investigation_service.create_investigation(
        session, user=current_user, create_in=create_in, ip_address=ip_addr
    )


@router.get(
    "",
    response_model=InvestigationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search and filter investigations",
    description="Searches investigations by number, title, or batch with multi-attribute filtering, sorting, and pagination.",
)
async def list_investigations(
    page: int = Query(1, ge=1, description="Page index"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search keyword for number, title, or batch"),
    status: Optional[str] = Query(None, description="Filter by status (Draft, Initiated, Under Investigation, etc.)"),
    priority: Optional[str] = Query(None, description="Filter by priority (Low, Medium, High, Critical)"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (Minor, Major, Critical)"),
    api_product_name: Optional[str] = Query(None, description="Filter by API product name"),
    manufacturing_stage: Optional[str] = Query(None, description="Filter by manufacturing stage"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned investigator UUID"),
    date_from: Optional[datetime] = Query(None, description="Created on or after"),
    date_to: Optional[datetime] = Query(None, description="Created on or before"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, priority, title, updated_at)"),
    sort_order: str = Query("desc", description="Sort direction (asc, desc)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvestigationListResponse:
    return await investigation_service.list_investigations(
        session,
        user=current_user,
        page=page,
        page_size=page_size,
        search=search,
        status=status,
        priority=priority,
        risk_level=risk_level,
        api_product_name=api_product_name,
        manufacturing_stage=manufacturing_stage,
        assigned_to=assigned_to,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{investigation_id}",
    response_model=InvestigationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get investigation details",
    description="Retrieves comprehensive investigation details including incident intake, author, and assignee.",
)
async def get_investigation_by_id(
    investigation_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvestigationDetailResponse:
    return await investigation_service.get_investigation_detail(
        session, user=current_user, investigation_id=investigation_id
    )


@router.patch(
    "/{investigation_id}",
    response_model=InvestigationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update investigation and incident details",
    description="Updates investigation and incident parameters with full ALCOA+ change tracking. Closed records cannot be edited.",
)
async def update_investigation(
    investigation_id: str,
    update_in: InvestigationUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvestigationDetailResponse:
    return await investigation_service.update_investigation(
        session, user=current_user, investigation_id=investigation_id, update_in=update_in
    )


@router.delete(
    "/{investigation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete investigation",
    description="Restricted deletion for unapproved Draft or Initiated investigations. Active approved investigations cannot be deleted.",
)
async def delete_investigation(
    investigation_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await investigation_service.delete_investigation(
        session, user=current_user, investigation_id=investigation_id
    )
    return {"message": "Investigation deleted successfully."}


# ==========================================
# Lifecycle, Workflow & Assignment Endpoints
# ==========================================

@router.post(
    "/{investigation_id}/submit",
    response_model=InvestigationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit draft investigation",
    description="Validates incident prerequisites and transitions draft investigation into active Initiated status.",
)
async def submit_investigation(
    investigation_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvestigationDetailResponse:
    return await investigation_service.submit_investigation(
        session, user=current_user, investigation_id=investigation_id
    )


@router.post(
    "/{investigation_id}/assign",
    response_model=InvestigationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign lead investigator",
    description="Designates or reassigns an eligible active investigator with mandatory audit logging.",
)
async def assign_investigator(
    investigation_id: str,
    assign_in: InvestigationAssignRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvestigationDetailResponse:
    return await investigation_service.assign_investigator(
        session, user=current_user, investigation_id=investigation_id, assign_in=assign_in
    )


@router.post(
    "/{investigation_id}/transition",
    response_model=InvestigationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute lifecycle status transition",
    description="Enforces pharmaceutical state machine rules, prerequisite validations, and role permissions.",
)
async def transition_investigation(
    investigation_id: str,
    transition_in: InvestigationTransitionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvestigationDetailResponse:
    return await investigation_service.transition_status(
        session, user=current_user, investigation_id=investigation_id, transition_in=transition_in
    )


@router.get(
    "/{investigation_id}/timeline",
    response_model=InvestigationTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Investigation chronological timeline",
    description="Retrieves contemporaneous milestone events and status changes from the audit history.",
)
async def get_investigation_timeline(
    investigation_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvestigationTimelineResponse:
    return await investigation_service.get_timeline(
        session, user=current_user, investigation_id=investigation_id
    )


@router.get(
    "/{investigation_id}/audit-history",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Investigation ALCOA+ audit history",
    description="Retrieves raw immutable audit trail records capturing old and new values for every change.",
)
async def get_investigation_audit_history(
    investigation_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    return await investigation_service.get_audit_history(
        session, user=current_user, investigation_id=investigation_id
    )

