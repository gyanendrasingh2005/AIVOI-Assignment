from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class IncidentBase(BaseModel):
    api_product_name: str = Field(..., max_length=150)
    batch_number: str = Field(..., max_length=50)
    manufacturing_stage: str = Field(..., max_length=100)
    incident_date: datetime
    incident_description: str
    equipment_id: Optional[str] = Field(None, max_length=50)
    expected_parameter: Optional[str] = Field(None, max_length=255)
    actual_parameter: Optional[str] = Field(None, max_length=255)
    immediate_actions: Optional[str] = None
    affected_batches: Optional[Any] = None
    potential_quality_impact: Optional[str] = None


class IncidentCreate(IncidentBase):
    investigation_id: str


class IncidentUpdate(BaseModel):
    api_product_name: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_stage: Optional[str] = None
    incident_date: Optional[datetime] = None
    incident_description: Optional[str] = None
    equipment_id: Optional[str] = None
    expected_parameter: Optional[str] = None
    actual_parameter: Optional[str] = None
    immediate_actions: Optional[str] = None
    affected_batches: Optional[Any] = None
    potential_quality_impact: Optional[str] = None


class IncidentResponse(IncidentBase):
    id: str
    investigation_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
