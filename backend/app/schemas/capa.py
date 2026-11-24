from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.enums import (
    CAPAType,
    CAPAStatus,
    PriorityLevel,
    CAPATaskStatus,
    EffectivenessStatus,
    CAPARecommendationStatus,
)


# -------------------------------------------------------------
# CAPA Tasks Schemas
# -------------------------------------------------------------

class CAPATaskBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    action_type: str = "CORRECTIVE"
    assigned_to: Optional[str] = None
    department: Optional[str] = None
    target_start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    priority: str = "MEDIUM"
    status: str = CAPATaskStatus.PENDING.value
    dependencies: List[str] = Field(default_factory=list)
    completion_criteria: Optional[str] = None
    required_evidence: Optional[str] = None
    submitted_evidence_references: List[str] = Field(default_factory=list)
    completion_notes: Optional[str] = None

    @field_validator("action_type", mode="before")
    @classmethod
    def normalize_action_type(cls, v: Any) -> str:
        if isinstance(v, str):
            v_upper = v.upper()
            if "PREVENT" in v_upper:
                return "PREVENTIVE"
            return "CORRECTIVE"
        return "CORRECTIVE"

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.upper()
        return "MEDIUM"

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> str:
        if isinstance(v, CAPATaskStatus):
            return v.value
        if isinstance(v, str):
            v_clean = v.replace(" ", "_").upper()
            if v_clean in [s.name for s in CAPATaskStatus]:
                return v_clean
            return v
        return "Pending"


class CAPATaskCreate(CAPATaskBase):
    pass


class CAPATaskCreateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    action_type: str = "CORRECTIVE"
    assigned_to: Optional[str] = None
    department: Optional[str] = None
    target_start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    priority: str = "MEDIUM"
    dependencies: List[str] = Field(default_factory=list)
    completion_criteria: Optional[str] = None
    required_evidence: Optional[str] = None


class CAPATaskPatchRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    action_type: Optional[str] = None
    department: Optional[str] = None
    target_start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    dependencies: Optional[List[str]] = None
    completion_criteria: Optional[str] = None
    required_evidence: Optional[str] = None


class CAPATaskAssignRequest(BaseModel):
    assigned_to: str
    due_date: Optional[datetime] = None
    department: Optional[str] = None


class CAPATaskSubmitCompletionRequest(BaseModel):
    completion_notes: str
    evidence_references: List[str] = Field(default_factory=list)


class CAPATaskApproveCompletionRequest(BaseModel):
    comments: Optional[str] = None


class CAPATaskRejectCompletionRequest(BaseModel):
    justification: str


class CAPATaskResponse(CAPATaskBase):
    id: str
    capa_id: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_comments: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CAPATaskListResponse(BaseModel):
    items: List[CAPATaskResponse]
    total: int
    capa_id: str


# -------------------------------------------------------------
# Effectiveness Checks Schemas
# -------------------------------------------------------------

class EffectivenessCheckBase(BaseModel):
    check_title: str = "CAPA Effectiveness Verification"
    verification_type: str = "PROCESS_MONITORING"
    objective: Optional[str] = None
    verification_method: str = Field(..., max_length=255)
    acceptance_criteria: str
    measurement_method: Optional[str] = None
    baseline_data: Optional[str] = None
    expected_outcome: Optional[str] = None
    observation_period_days: int = 30
    planned_start_date: Optional[datetime] = None
    planned_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None
    responsible_reviewer_id: Optional[str] = None
    required_evidence: Optional[str] = None
    associated_evidence_ids: List[str] = Field(default_factory=list)
    sampling_approach: Optional[str] = None
    check_frequency: Optional[str] = None
    result: Optional[str] = None
    conclusion: Optional[str] = None
    reviewer_comments: Optional[str] = None
    status: str = EffectivenessStatus.SCHEDULED.value
    effectiveness_decision: Optional[str] = None
    decision_reason: Optional[str] = None
    decision_by: Optional[str] = None
    decision_at: Optional[datetime] = None
    ai_assessment_summary: Optional[Dict[str, Any]] = None
    ai_execution_id: Optional[str] = None
    recurrence_observed: bool = False
    followup_investigation_id: Optional[str] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> str:
        if isinstance(v, EffectivenessStatus):
            return v.value
        if isinstance(v, str):
            v_clean = v.replace(" ", "_").upper()
            for s in EffectivenessStatus:
                if s.name == v_clean or s.value.replace(" ", "_").upper() == v_clean:
                    return s.value
            return v
        return EffectivenessStatus.SCHEDULED.value


class EffectivenessCheckCreate(EffectivenessCheckBase):
    pass


class EffectivenessCheckCreateRequest(BaseModel):
    check_title: str = "CAPA Effectiveness Verification"
    verification_type: str = "PROCESS_MONITORING"
    objective: Optional[str] = None
    verification_method: str
    acceptance_criteria: str
    measurement_method: Optional[str] = None
    baseline_data: Optional[str] = None
    expected_outcome: Optional[str] = None
    observation_period_days: int = 30
    planned_start_date: Optional[datetime] = None
    planned_completion_date: Optional[datetime] = None
    responsible_reviewer_id: Optional[str] = None
    required_evidence: Optional[str] = None
    associated_evidence_ids: List[str] = Field(default_factory=list)
    sampling_approach: Optional[str] = None
    check_frequency: Optional[str] = None


class EffectivenessCheckPatchRequest(BaseModel):
    check_title: Optional[str] = None
    verification_type: Optional[str] = None
    objective: Optional[str] = None
    verification_method: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    measurement_method: Optional[str] = None
    baseline_data: Optional[str] = None
    expected_outcome: Optional[str] = None
    observation_period_days: Optional[int] = None
    planned_start_date: Optional[datetime] = None
    planned_completion_date: Optional[datetime] = None
    responsible_reviewer_id: Optional[str] = None
    required_evidence: Optional[str] = None
    sampling_approach: Optional[str] = None
    check_frequency: Optional[str] = None


class EffectivenessCheckEvidenceAttachRequest(BaseModel):
    evidence_ids: List[str] = Field(..., min_length=1)


class EffectivenessCheckRecordResultRequest(BaseModel):
    result: str
    conclusion: Optional[str] = None
    recurrence_observed: bool = False
    reviewer_comments: Optional[str] = None


class EffectivenessCheckFinalizeDecisionRequest(BaseModel):
    decision: str  # EFFECTIVE, INEFFECTIVE, PARTIALLY_EFFECTIVE, INSUFFICIENT_EVIDENCE
    decision_reason: str


class EffectivenessCheckReopenCAPARequest(BaseModel):
    reason: str
    new_tasks: Optional[List[Dict[str, Any]]] = None


class EffectivenessCheckFollowupInvestigationRequest(BaseModel):
    justification: str
    title: Optional[str] = None


class EffectivenessCheckResponse(EffectivenessCheckBase):
    id: str
    capa_id: str
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EffectivenessCheckListResponse(BaseModel):
    items: List[EffectivenessCheckResponse]
    total: int
    capa_id: str


# -------------------------------------------------------------
# CAPA Monitoring & Closure Schemas
# -------------------------------------------------------------

class CAPAClosureValidationResponse(BaseModel):
    is_closable: bool
    can_close: bool
    blockers: List[str] = Field(default_factory=list)
    completed_tasks_count: int
    total_tasks_count: int
    effective_checks_count: int
    total_checks_count: int
    open_evidence_gaps_count: int


class CAPACloseRequest(BaseModel):
    comments: str


class CAPAReopenRequest(BaseModel):
    justification: str


class CAPAMonitoringSummaryResponse(BaseModel):
    investigation_id: Optional[str] = None
    total_capas: int
    total_tasks: int
    completed_tasks: int
    verified_tasks: int
    in_progress_tasks: int
    overdue_tasks: int
    implementation_progress_percentage: float
    effectiveness_checks_summary: Dict[str, int] = Field(default_factory=dict)
    capa_breakdown: List[Dict[str, Any]] = Field(default_factory=list)


# -------------------------------------------------------------
# CAPA Recommendation Schemas
# -------------------------------------------------------------

class CAPAAIRecommendationRequest(BaseModel):
    focus_action_type: Optional[str] = None  # None for both CORRECTIVE and PREVENTIVE


class CAPARecommendationBase(BaseModel):
    recommendation_title: str = Field(..., max_length=255)
    description: str
    action_type: str = "CORRECTIVE"
    root_cause_id: Optional[str] = None
    root_cause_title: Optional[str] = None
    contributing_factor_ids: List[str] = Field(default_factory=list)
    evidence_gap_ids: List[str] = Field(default_factory=list)
    supporting_references: List[str] = Field(default_factory=list)
    rationale: str
    expected_outcome: str
    recurrence_risk_addressed: Optional[str] = None
    priority: str = "MEDIUM"
    suggested_department: Optional[str] = None
    suggested_role: Optional[str] = None
    suggested_target_days: int = 30
    target_date: Optional[datetime] = None
    implementation_steps: List[str] = Field(default_factory=list)
    completion_criteria: str
    required_completion_evidence: str
    implementation_risks: Optional[str] = None
    is_provisional: bool = False
    uncertainty_rationale: Optional[str] = None


class CAPARecommendationPatchRequest(BaseModel):
    recommendation_title: Optional[str] = None
    description: Optional[str] = None
    action_type: Optional[str] = None
    priority: Optional[str] = None
    suggested_department: Optional[str] = None
    suggested_role: Optional[str] = None
    suggested_target_days: Optional[int] = None
    target_date: Optional[datetime] = None
    implementation_steps: Optional[List[str]] = None
    completion_criteria: Optional[str] = None
    required_completion_evidence: Optional[str] = None
    rationale: Optional[str] = None
    expected_outcome: Optional[str] = None


class CAPARecommendationAcceptRequest(BaseModel):
    notes: Optional[str] = None


class CAPARecommendationRejectRequest(BaseModel):
    justification: str


class CAPARecommendationResponse(CAPARecommendationBase):
    id: str
    investigation_id: str
    ai_execution_id: Optional[str] = None
    status: str = CAPARecommendationStatus.PENDING_REVIEW.value
    rejection_reason: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_capa_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CAPARecommendationListResponse(BaseModel):
    items: List[CAPARecommendationResponse]
    total: int
    investigation_id: str


# -------------------------------------------------------------
# CAPA Plan Schemas
# -------------------------------------------------------------

class CAPABase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    capa_type: CAPAType = CAPAType.CORRECTIVE
    rationale: Optional[str] = None
    priority: PriorityLevel = PriorityLevel.MEDIUM
    status: CAPAStatus = CAPAStatus.DRAFT
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v: Any) -> PriorityLevel:
        if isinstance(v, PriorityLevel):
            return v
        if isinstance(v, str):
            v_upper = v.upper()
            mapping = {
                "LOW": PriorityLevel.LOW,
                "MEDIUM": PriorityLevel.MEDIUM,
                "HIGH": PriorityLevel.HIGH,
                "CRITICAL": PriorityLevel.CRITICAL,
            }
            if v_upper in mapping:
                return mapping[v_upper]
            for p in PriorityLevel:
                if p.value.lower() == v.lower():
                    return p
        return PriorityLevel.MEDIUM

    @field_validator("capa_type", mode="before")
    @classmethod
    def normalize_capa_type(cls, v: Any) -> CAPAType:
        if isinstance(v, CAPAType):
            return v
        if isinstance(v, str):
            if "PREVENT" in v.upper():
                return CAPAType.PREVENTIVE
            return CAPAType.CORRECTIVE
        return CAPAType.CORRECTIVE

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> CAPAStatus:
        if isinstance(v, CAPAStatus):
            return v
        if isinstance(v, str):
            v_clean = v.replace(" ", "_").upper()
            for s in CAPAStatus:
                if s.name == v_clean or s.value.replace(" ", "_").upper() == v_clean:
                    return s
        return CAPAStatus.DRAFT


class CAPACreate(CAPABase):
    investigation_id: str
    root_cause_id: Optional[str] = None


class CAPAPlanCreateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    capa_type: str = "CORRECTIVE"
    rca_analysis_id: Optional[str] = None
    root_cause_id: Optional[str] = None
    problem_statement: Optional[str] = None
    root_cause_summary: Optional[str] = None
    corrective_action_summary: Optional[str] = None
    preventive_action_summary: Optional[str] = None
    rationale: Optional[str] = None
    priority: str = "MEDIUM"
    responsible_department: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    supporting_references: List[str] = Field(default_factory=list)
    accepted_recommendation_ids: List[str] = Field(default_factory=list)


class CAPAPatchRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    capa_type: Optional[str] = None
    problem_statement: Optional[str] = None
    root_cause_summary: Optional[str] = None
    corrective_action_summary: Optional[str] = None
    preventive_action_summary: Optional[str] = None
    rationale: Optional[str] = None
    priority: Optional[str] = None
    responsible_department: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    supporting_references: Optional[List[str]] = None


class CAPAUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    capa_type: Optional[CAPAType] = None
    rationale: Optional[str] = None
    priority: Optional[PriorityLevel] = None
    status: Optional[CAPAStatus] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None


class CAPASubmitReviewRequest(BaseModel):
    comments: Optional[str] = None


class CAPASubmitApprovalRequest(BaseModel):
    comments: Optional[str] = None


class CAPAApproveRequest(BaseModel):
    comments: Optional[str] = None


class CAPARejectRequest(BaseModel):
    justification: str


class CAPAResponse(CAPABase):
    id: str
    investigation_id: str
    capa_number: Optional[str] = None
    rca_analysis_id: Optional[str] = None
    root_cause_id: Optional[str] = None
    problem_statement: Optional[str] = None
    root_cause_summary: Optional[str] = None
    corrective_action_summary: Optional[str] = None
    preventive_action_summary: Optional[str] = None
    responsible_department: Optional[str] = None
    initiated_date: Optional[datetime] = None
    approval_status: Optional[str] = None
    approval_comments: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    supporting_references: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    tasks: List[CAPATaskResponse] = []
    effectiveness_checks: List[EffectivenessCheckResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CAPAListResponse(BaseModel):
    items: List[CAPAResponse]
    total: int
    investigation_id: str
