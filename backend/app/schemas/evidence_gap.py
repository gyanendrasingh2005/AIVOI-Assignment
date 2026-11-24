from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import EvidenceGapPriority, EvidenceGapStatus


class EvidenceGapBase(BaseModel):
    description: str
    reason: str
    priority: EvidenceGapPriority = EvidenceGapPriority.MEDIUM
    suggested_source: Optional[str] = Field(None, max_length=255)
    status: EvidenceGapStatus = EvidenceGapStatus.OPEN


class EvidenceGapCreate(EvidenceGapBase):
    investigation_id: str
    root_cause_id: Optional[str] = None


class EvidenceGapUpdate(BaseModel):
    description: Optional[str] = None
    reason: Optional[str] = None
    priority: Optional[EvidenceGapPriority] = None
    suggested_source: Optional[str] = None
    status: Optional[EvidenceGapStatus] = None


class EvidenceGapResponse(EvidenceGapBase):
    id: str
    investigation_id: str
    root_cause_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
