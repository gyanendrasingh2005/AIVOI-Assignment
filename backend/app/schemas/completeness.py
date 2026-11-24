from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import CompletenessDimensionStatus, CompletenessOverallStatus


class CompletenessDimensionResult(BaseModel):
    dimension_name: str
    status: str = CompletenessDimensionStatus.UNDETERMINED.value
    explanation: str
    related_gap_ids: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)


class CompletenessAssessmentRequest(BaseModel):
    requirement_profile: Optional[str] = "1.0.0"
    force_refresh: bool = False


class CompletenessAssessmentResponse(BaseModel):
    id: str
    investigation_id: str
    assessment_version: int
    overall_status: str
    completeness_score: float
    summary: Optional[str] = None
    dimension_results: List[CompletenessDimensionResult]
    critical_unresolved_gaps: int
    high_priority_unresolved_gaps: int
    total_unresolved_gaps: int
    conflicting_evidence_count: int
    unverified_causal_claims_count: int
    pending_reviews_count: int
    recommended_activities: List[str]
    requirement_profile_version: str
    ai_execution_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompletenessHistoryItem(BaseModel):
    id: str
    assessment_version: int
    overall_status: str
    completeness_score: float
    total_unresolved_gaps: int
    critical_unresolved_gaps: int
    created_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CompletenessHistoryResponse(BaseModel):
    investigation_id: str
    total_versions: int
    assessments: List[CompletenessHistoryItem]
