from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import InvestigationStatus, PriorityLevel, RiskLevel
from app.schemas.user import UserResponse
from app.schemas.incident import IncidentResponse


class InvestigationBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    description: Optional[str] = None
    priority: PriorityLevel = PriorityLevel.MEDIUM
    risk_level: RiskLevel = RiskLevel.MAJOR


class InvestigationCreate(InvestigationBase):
    investigation_number: str = Field(..., min_length=3, max_length=50)
    status: InvestigationStatus = InvestigationStatus.DRAFT
    assigned_to: Optional[str] = None


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


class InvestigationDetailResponse(InvestigationResponse):
    creator: Optional[UserResponse] = None
    assignee: Optional[UserResponse] = None
    incident: Optional[IncidentResponse] = None

    model_config = ConfigDict(from_attributes=True)
