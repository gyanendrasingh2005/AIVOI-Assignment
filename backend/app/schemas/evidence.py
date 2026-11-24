from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import EvidenceType, EvidenceVerificationStatus


class EvidenceBase(BaseModel):
    title: str = Field(..., max_length=255)
    evidence_type: EvidenceType = EvidenceType.DOCUMENT_EXCERPT
    description: Optional[str] = None
    source_reference: Optional[str] = Field(None, max_length=255)
    page_number: Optional[int] = None
    excerpt: Optional[str] = None


class EvidenceCreate(EvidenceBase):
    investigation_id: str
    document_id: Optional[str] = None
    verification_status: EvidenceVerificationStatus = EvidenceVerificationStatus.UNVERIFIED


class EvidenceUpdate(BaseModel):
    title: Optional[str] = None
    evidence_type: Optional[EvidenceType] = None
    description: Optional[str] = None
    source_reference: Optional[str] = None
    page_number: Optional[int] = None
    excerpt: Optional[str] = None
    verification_status: Optional[EvidenceVerificationStatus] = None


class EvidenceResponse(EvidenceBase):
    id: str
    investigation_id: str
    document_id: Optional[str] = None
    verification_status: str
    uploaded_by: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
