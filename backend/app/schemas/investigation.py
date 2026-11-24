from typing import Optional, List, Any, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import InvestigationStatus, PriorityLevel, RiskLevel
from app.schemas.user import UserResponse
from app.schemas.incident import IncidentResponse, IncidentBase


class InvestigationBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=255, description="Brief descriptive title of the API deviation")
    description: Optional[str] = Field(None, description="Detailed problem statement and background")
    priority: PriorityLevel = Field(default=PriorityLevel.MEDIUM, description="Processing urgency level")
    risk_level: RiskLevel = Field(default=RiskLevel.MAJOR, description="GMP quality risk classification")


class InvestigationCreate(InvestigationBase):
    investigation_number: str = Field(..., min_length=3, max_length=50)
    status: InvestigationStatus = InvestigationStatus.DRAFT
    assigned_to: Optional[str] = None


class InvestigationCreateRequest(InvestigationBase):
    """Client request schema creating an investigation and embedded incident intake."""

    status: InvestigationStatus = Field(
        default=InvestigationStatus.DRAFT,
        description="Initial status: Draft or Initiated",
    )
    assigned_to: Optional[str] = Field(None, description="UUID of the assigned lead investigator")

    # Embedded Incident Intake Attributes
    api_product_name: str = Field(..., min_length=2, max_length=150, description="Active Pharmaceutical Ingredient trade/generic name")
    batch_number: str = Field(..., min_length=1, max_length=50, description="Unique API manufacturing lot/batch number")
    manufacturing_stage: str = Field(..., min_length=2, max_length=100, description="Processing stage (e.g. Synthesis, Crystallization, Drying)")
    incident_date: datetime = Field(..., description="Contemporaneous timestamp of deviation discovery")
    incident_description: str = Field(..., min_length=10, description="Thorough factual narrative of observed anomaly")
    equipment_id: Optional[str] = Field(None, max_length=50, description="Tag/identifier of reactor, centrifuge, or analytical asset")
    expected_parameter: Optional[str] = Field(None, max_length=255, description="Validated process parameter range")
    actual_parameter: Optional[str] = Field(None, max_length=255, description="Observed/measured out-of-spec or atypical value")
    immediate_actions: Optional[str] = Field(None, description="Immediate containment, quarantine or batch hold actions taken")
    affected_batches: Optional[Any] = Field(None, description="JSON array of related or concurrent batches evaluated")
    potential_quality_impact: Optional[str] = Field(None, description="Initial assessment of impact on critical quality attributes")


class InvestigationUpdateRequest(BaseModel):
    """Partial update payload for ongoing investigation and incident records."""

    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = None
    priority: Optional[PriorityLevel] = None
    risk_level: Optional[RiskLevel] = None

    # Incident attributes
    api_product_name: Optional[str] = Field(None, min_length=2, max_length=150)
    batch_number: Optional[str] = Field(None, min_length=1, max_length=50)
    manufacturing_stage: Optional[str] = Field(None, min_length=2, max_length=100)
    incident_date: Optional[datetime] = None
    incident_description: Optional[str] = Field(None, min_length=10)
    equipment_id: Optional[str] = None
    expected_parameter: Optional[str] = None
    actual_parameter: Optional[str] = None
    immediate_actions: Optional[str] = None
    affected_batches: Optional[Any] = None
    potential_quality_impact: Optional[str] = None


class InvestigationTransitionRequest(BaseModel):
    """Payload to trigger a validated status transition across the quality lifecycle."""

    target_status: InvestigationStatus = Field(..., description="Target lifecycle state")
    comments: Optional[str] = Field(None, max_length=1000, description="Review notes or justification for the status change")
    reason: Optional[str] = Field(None, max_length=500, description="Mandatory reason when rejecting or re-opening")


class InvestigationAssignRequest(BaseModel):
    """Payload to designate or reassign the lead investigator."""

    assigned_to: str = Field(..., min_length=36, max_length=36, description="UUID of active investigator user")
    comments: Optional[str] = Field(None, description="Assignment rationale or instructions")


class InvestigationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[InvestigationStatus] = None
    priority: Optional[PriorityLevel] = None
    risk_level: Optional[RiskLevel] = None
    assigned_to: Optional[str] = None
    closed_at: Optional[datetime] = None


class InvestigationResponse(InvestigationBase):
    id: str
    investigation_number: str
    status: str
    created_by: Optional[str] = None
    assigned_to: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InvestigationListItem(InvestigationResponse):
    """Slim view optimized for paginated registry display."""

    api_product_name: Optional[str] = None
    batch_number: Optional[str] = None
    creator_name: Optional[str] = None
    assignee_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InvestigationListResponse(BaseModel):
    """Paginated list of investigation entries."""

    items: List[InvestigationListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class InvestigationDetailResponse(InvestigationResponse):
    """Rich comprehensive representation including incident and actor associations."""

    creator: Optional[UserResponse] = None
    assignee: Optional[UserResponse] = None
    incident: Optional[IncidentResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TimelineEvent(BaseModel):
    """Chronological milestone in the investigation audit trail."""

    id: str
    event_type: str
    title: str
    description: Optional[str] = None
    timestamp: datetime
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class InvestigationTimelineResponse(BaseModel):
    investigation_id: str
    investigation_number: str
    events: List[TimelineEvent]


class DashboardSummaryResponse(BaseModel):
    """Statistical overview of QMS investigations."""

    total_investigations: int
    open_investigations: int
    draft_investigations: int
    under_investigation: int
    under_review: int
    pending_approval: int
    capa_in_progress: int
    closed_investigations: int
    rejected_investigations: int
    overdue_investigations: int
    by_risk_level: Dict[str, int]
    by_status: Dict[str, int]
