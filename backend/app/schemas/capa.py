from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import (
    CAPAType,
    CAPAStatus,
    PriorityLevel,
    CAPATaskStatus,
    EffectivenessStatus,
)


class CAPATaskBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    status: CAPATaskStatus = CAPATaskStatus.PENDING
    completion_notes: Optional[str] = None


class CAPATaskCreate(CAPATaskBase):
    pass


class CAPATaskResponse(CAPATaskBase):
    id: str
    capa_id: str
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EffectivenessCheckBase(BaseModel):
    verification_method: str = Field(..., max_length=255)
    acceptance_criteria: str
    result: Optional[str] = None
    status: EffectivenessStatus = EffectivenessStatus.SCHEDULED


class EffectivenessCheckCreate(EffectivenessCheckBase):
    pass


class EffectivenessCheckResponse(EffectivenessCheckBase):
    id: str
    capa_id: str
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CAPABase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    capa_type: CAPAType = CAPAType.CORRECTIVE
    rationale: Optional[str] = None
    priority: PriorityLevel = PriorityLevel.MEDIUM
    status: CAPAStatus = CAPAStatus.DRAFT
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class CAPACreate(CAPABase):
    investigation_id: str
    root_cause_id: Optional[str] = None


class CAPAUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    capa_type: Optional[CAPAType] = None
    rationale: Optional[str] = None
    priority: Optional[PriorityLevel] = None
    status: Optional[CAPAStatus] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class CAPAResponse(CAPABase):
    id: str
    investigation_id: str
    root_cause_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    tasks: List[CAPATaskResponse] = []
    effectiveness_checks: List[EffectivenessCheckResponse] = []

    model_config = ConfigDict(from_attributes=True)
