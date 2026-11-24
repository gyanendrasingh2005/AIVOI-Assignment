from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.enums import EvidenceGapPriority, EvidenceGapStatus, GapCategory, GapDetectionType


def normalize_priority(v: Any) -> str:
    if isinstance(v, EvidenceGapPriority):
        return v.value
    if isinstance(v, str):
        cleaned = v.strip().upper().replace(" ", "_")
        for member in EvidenceGapPriority:
            if member.name == cleaned or member.value.upper() == cleaned:
                return member.value
    return EvidenceGapPriority.MEDIUM.value


def normalize_status(v: Any) -> str:
    if isinstance(v, EvidenceGapStatus):
        return v.value
    if isinstance(v, str):
        cleaned = v.strip().upper().replace(" ", "_")
        for member in EvidenceGapStatus:
            if member.name == cleaned or member.value.upper() == cleaned:
                return member.value
    return EvidenceGapStatus.OPEN.value


def normalize_category(v: Any) -> str:
    if isinstance(v, GapCategory):
        return v.value
    if isinstance(v, str):
        cleaned = v.strip().upper().replace(" ", "_").replace("/", "_")
        for member in GapCategory:
            if member.name == cleaned or member.value == cleaned:
                return member.value
    return GapCategory.OTHER.value


def normalize_detection_type(v: Any) -> str:
    if isinstance(v, GapDetectionType):
        return v.value
    if isinstance(v, str):
        cleaned = v.strip().upper().replace(" ", "_")
        for member in GapDetectionType:
            if member.name == cleaned or member.value == cleaned:
                return member.value
    return GapDetectionType.MISSING_EVIDENCE.value


class EvidenceGapBase(BaseModel):
    description: str
    reason: str
    gap_title: Optional[str] = None
    category: str = GapCategory.OTHER.value
    detection_type: str = GapDetectionType.MISSING_EVIDENCE.value
    priority: str = EvidenceGapPriority.MEDIUM.value
    affected_area: Optional[str] = None
    suggested_source: Optional[str] = Field(None, max_length=255)
    recommended_evidence_type: Optional[str] = None
    recommended_action: Optional[str] = None
    detection_source: str = "AI_ASSESSMENT"
    ai_confidence: Optional[float] = None
    status: str = EvidenceGapStatus.OPEN.value
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    associated_evidence_ids: List[str] = Field(default_factory=list)
    supporting_references: List[Dict[str, Any]] = Field(default_factory=list)

    @field_validator("priority", mode="before")
    def validate_priority(cls, v: Any) -> str:
        return normalize_priority(v)

    @field_validator("status", mode="before")
    def validate_status(cls, v: Any) -> str:
        return normalize_status(v)

    @field_validator("category", mode="before")
    def validate_category(cls, v: Any) -> str:
        return normalize_category(v)

    @field_validator("detection_type", mode="before")
    def validate_detection_type(cls, v: Any) -> str:
        return normalize_detection_type(v)


class EvidenceGapCreate(EvidenceGapBase):
    investigation_id: str
    root_cause_id: Optional[str] = None
    assessment_version: int = 1
    requirement_profile_version: Optional[str] = "1.0.0"


class EvidenceGapUpdate(BaseModel):
    gap_title: Optional[str] = None
    description: Optional[str] = None
    reason: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    detection_type: Optional[str] = None
    affected_area: Optional[str] = None
    suggested_source: Optional[str] = None
    recommended_evidence_type: Optional[str] = None
    recommended_action: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None


class EvidenceGapAssignRequest(BaseModel):
    assigned_to: str
    due_date: Optional[datetime] = None


class EvidenceGapRequestEvidenceRequest(BaseModel):
    notes: str
    suggested_source: Optional[str] = None


class EvidenceGapAssociateEvidenceRequest(BaseModel):
    evidence_ids: List[str]


class EvidenceGapResolveRequest(BaseModel):
    justification: str
    evidence_ids: Optional[List[str]] = None


class EvidenceGapRejectRequest(BaseModel):
    justification: str


class EvidenceGapWaiveRequest(BaseModel):
    justification: str
    policy_reference: Optional[str] = None


class EvidenceGapReopenRequest(BaseModel):
    justification: str


class EvidenceGapPatchRequest(BaseModel):
    gap_title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    affected_area: Optional[str] = None
    recommended_action: Optional[str] = None
    due_date: Optional[datetime] = None


class EvidenceGapResponse(EvidenceGapBase):
    id: str
    investigation_id: str
    root_cause_id: Optional[str] = None
    assessment_version: int = 1
    requirement_profile_version: Optional[str] = None
    resolution_justification: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    assigned_user_name: Optional[str] = None
    resolver_user_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceGapListResponse(BaseModel):
    items: List[EvidenceGapResponse]
    total: int
    skip: int
    limit: int
