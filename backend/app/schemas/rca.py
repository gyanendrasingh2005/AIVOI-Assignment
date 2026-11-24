from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    RCAMethod,
    RCAStatus,
    RootCauseCategory,
    EvidenceStrength,
    RootCauseStatus,
    ContributingFactorStatus,
    CauseStatus,
    CauseClassification,
    Fishbone6MCategory,
)


class RCAEvidenceReference(BaseModel):
    """Grounding citation linking an RCA deduction or cause to source document evidence."""

    document_id: Optional[str] = Field(None, description="UUID of source document")
    evidence_id: Optional[str] = Field(None, description="UUID of evidence record if linked")
    filename: Optional[str] = Field(None, description="Original filename of source document")
    page_number: Optional[int] = Field(None, description="Page number where excerpt appears")
    excerpt: str = Field(..., max_length=2500, description="Verbatim factual excerpt from record")
    related_field: Optional[str] = Field(None, description="Related incident parameter or cause node")
    relevance_reason: Optional[str] = Field(None, max_length=1000, description="Explanation linking evidence to causal deduction")


class WhyStepItem(BaseModel):
    """A step in an iterative 5 Whys causal inquiry."""

    step_number: int = Field(..., ge=1, le=10, description="Sequential Why step number (1 to 5+)")
    question: str = Field(..., description="Causal query e.g. 'Why did crystallization temperature exceed setpoint?'")
    answer: str = Field(..., description="Factual causal deduction explaining the question")
    explanation: Optional[str] = Field(None, description="Contextual technical rationale or mechanism")
    supporting_references: List[RCAEvidenceReference] = Field(
        default_factory=list, description="Empirical document citations"
    )
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Estimated confidence score")
    verification_status: CauseStatus = Field(default=CauseStatus.PROPOSED, description="Human QA verification status")
    assumptions: List[str] = Field(default_factory=list, description="Unverified operational assumptions identified")
    missing_information: List[str] = Field(default_factory=list, description="Missing records or parameters required")
    is_root_cause: bool = Field(default=False, description="True if step represents the terminal root cause mechanism")
    causal_leap_detected: bool = Field(default=False, description="True if jump between previous answer and question is ungrounded")
    reasoning_critique: Optional[str] = Field(None, description="Critique of causal logic e.g. circular or repeated reasoning")

    @field_validator("verification_status", mode="before")
    @classmethod
    def normalize_verification_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_norm = v.upper().replace(" ", "_").replace("-", "_")
            if v_norm in CauseStatus.__members__:
                return CauseStatus[v_norm]
        return v


class FishboneCauseItem(BaseModel):
    """Specific cause node attached to an Ishikawa 6M category branch."""

    cause_id: str = Field(..., description="Unique stable ID for this cause (e.g. cause-1)")
    category: str = Field(..., description="6M Category e.g. 'Machine / Equipment'")
    title: str = Field(..., max_length=255, description="Concise cause title")
    description: str = Field(..., description="Detailed description of the causal mechanism")
    supporting_references: List[RCAEvidenceReference] = Field(
        default_factory=list, description="Empirical document citations"
    )
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Estimated confidence")
    verification_status: CauseStatus = Field(default=CauseStatus.PROPOSED, description="Verification status")
    potential_impact: Optional[str] = Field(None, description="Potential impact on process or API quality")
    classification: CauseClassification = Field(
        default=CauseClassification.POSSIBLE_CAUSE, description="Root Cause, Contributing Factor, or Possible Cause"
    )
    related_why_step: Optional[int] = Field(None, description="Associated 5 Whys step number if correlated")
    rejection_reason: Optional[str] = Field(None, description="Documented reason if cause was rejected")

    @field_validator("classification", mode="before")
    @classmethod
    def normalize_classification(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_norm = v.upper().replace(" ", "_").replace("-", "_")
            if v_norm in CauseClassification.__members__:
                return CauseClassification[v_norm]
        return v

    @field_validator("verification_status", mode="before")
    @classmethod
    def normalize_verification_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_norm = v.upper().replace(" ", "_").replace("-", "_")
            if v_norm in CauseStatus.__members__:
                return CauseStatus[v_norm]
        return v


class RootCauseItem(BaseModel):
    """A verified or proposed primary underlying root cause."""

    cause_id: str = Field(..., description="Unique identifier for root cause")
    title: str = Field(..., max_length=255, description="Root cause summary")
    description: str = Field(..., description="Comprehensive explanation of underlying root mechanism")
    category: str = Field(default="Method / Process", description="Primary 6M category")
    supporting_references: List[RCAEvidenceReference] = Field(
        default_factory=list, description="Empirical document citations"
    )
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    verification_status: CauseStatus = Field(default=CauseStatus.PROPOSED)
    human_confirmed: bool = Field(default=False, description="True only after authorized QA human sign-off")

    @field_validator("verification_status", mode="before")
    @classmethod
    def normalize_verification_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_norm = v.upper().replace(" ", "_").replace("-", "_")
            if v_norm in CauseStatus.__members__:
                return CauseStatus[v_norm]
        return v


class ContributingFactorItem(BaseModel):
    """Secondary condition or factor that exacerbated the incident."""

    factor_id: str = Field(..., description="Unique identifier for contributing factor")
    description: str = Field(..., description="Explanation of contributing factor")
    category: str = Field(..., description="6M Category")
    supporting_references: List[RCAEvidenceReference] = Field(
        default_factory=list, description="Empirical document citations"
    )
    impact_on_incident: Optional[str] = Field(None, description="How this factor increased severity or likelihood")


class RCAEvidenceGapItem(BaseModel):
    """Missing document, parameter, or unverified assumption in the causal inquiry."""

    gap_id: str = Field(..., description="Unique identifier for evidence gap")
    description: str = Field(..., description="Description of missing information")
    reason: str = Field(..., description="Why this evidence is necessary to complete RCA")
    priority: str = Field(default="Medium", description="High, Medium, or Low")
    suggested_source: Optional[str] = Field(None, description="Suggested record e.g. calibration log, SOP")


class RCAStructuredOutput(BaseModel):
    """Structured LLM response for pharmaceutical Root Cause Analysis."""

    problem_statement: str = Field(..., description="Clear, objective statement of observed deviation or defect")
    incident_summary: str = Field(..., description="Summary of confirmed manufacturing incident context")
    five_whys: List[WhyStepItem] = Field(default_factory=list, description="Structured sequential 5 Whys chain")
    fishbone_causes: List[FishboneCauseItem] = Field(
        default_factory=list, description="Causes categorized under 6M Ishikawa branches"
    )
    potential_root_causes: List[RootCauseItem] = Field(
        default_factory=list, description="Underlying root causes requiring human verification"
    )
    contributing_factors: List[ContributingFactorItem] = Field(
        default_factory=list, description="Contributing secondary factors"
    )
    rejected_hypotheses: List[FishboneCauseItem] = Field(
        default_factory=list, description="Hypotheses evaluated and ruled out by documented evidence"
    )
    evidence_gaps: List[RCAEvidenceGapItem] = Field(
        default_factory=list, description="Evidence gaps or unverified assumptions identified"
    )
    causal_chain_critique: Optional[str] = Field(
        None, description="Critique of logic, circularity, or unsupported leaps in the chain"
    )
    unsupported_assumptions: List[str] = Field(
        default_factory=list, description="Assumptions lacking empirical grounding in records"
    )


# ---------------------------------------------------------------------------
# API Request & Response Schemas
# ---------------------------------------------------------------------------

class RCARequest(BaseModel):
    """Request payload to initiate AI Root Cause Analysis."""

    analysis_method: RCAMethod = Field(
        default=RCAMethod.HYBRID,
        description="Methodology: '5 Whys', 'Fishbone', or 'Hybrid'",
    )
    use_documents: bool = Field(default=True, description="Whether to include text from uploaded documents")
    additional_focus: Optional[str] = Field(
        None, max_length=2000, description="Optional focused investigator instructions"
    )


class RCAResponse(BaseModel):
    """Full representation of RCAAnalysis database entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    investigation_id: str
    ai_execution_id: Optional[str] = None
    created_by: Optional[str] = None
    analysis_method: str
    analysis_version: int
    summary: Optional[str] = None
    status: str
    prompt_version: str

    problem_statement: Optional[str] = None
    incident_summary: Optional[str] = None

    five_whys_data: List[Dict[str, Any]]
    fishbone_data: Dict[str, Any]
    root_causes_data: List[Dict[str, Any]]
    contributing_factors_data: List[Dict[str, Any]]
    rejected_hypotheses_data: List[Dict[str, Any]]
    evidence_gaps_data: List[Dict[str, Any]]

    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class RCAListResponse(BaseModel):
    items: List[RCAResponse]
    total: int


class RCAReviewViewResponse(BaseModel):
    """Comprehensive review payload tailored for human QA review."""

    rca: RCAResponse
    incident_snapshot: Dict[str, Any]
    five_whys: List[Dict[str, Any]]
    fishbone_categories: Dict[str, List[Dict[str, Any]]]
    root_causes: List[Dict[str, Any]]
    contributing_factors: List[Dict[str, Any]]
    evidence_gaps: List[Dict[str, Any]]
    unsupported_assumptions: List[str]


class RCAReviewPatchRequest(BaseModel):
    """Human investigator review updates."""

    summary: Optional[str] = Field(None, max_length=5000)
    problem_statement: Optional[str] = Field(None, max_length=5000)
    reviewer_notes: Optional[str] = Field(None, max_length=5000)
    review_status: Optional[RCAStatus] = None
    five_whys_override: Optional[List[Dict[str, Any]]] = None
    fishbone_override: Optional[Dict[str, Any]] = None


class ManualCauseCreateRequest(BaseModel):
    """Add a manual cause to RCA."""

    category: str = Field(..., description="6M category name")
    title: str = Field(..., max_length=255)
    description: str = Field(...)
    classification: CauseClassification = Field(default=CauseClassification.POSSIBLE_CAUSE)
    supporting_references: List[RCAEvidenceReference] = Field(default_factory=list)

    @field_validator("classification", mode="before")
    @classmethod
    def normalize_classification(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_norm = v.upper().replace(" ", "_").replace("-", "_")
            if v_norm in CauseClassification.__members__:
                return CauseClassification[v_norm]
        return v


class CausePatchRequest(BaseModel):
    """Edit an existing cause in RCA."""

    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    classification: Optional[CauseClassification] = None
    verification_status: Optional[CauseStatus] = None
    rejection_reason: Optional[str] = None
    potential_impact: Optional[str] = None

    @field_validator("classification", mode="before")
    @classmethod
    def normalize_classification(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_norm = v.upper().replace(" ", "_").replace("-", "_")
            if v_norm in CauseClassification.__members__:
                return CauseClassification[v_norm]
        return v

    @field_validator("verification_status", mode="before")
    @classmethod
    def normalize_verification_status(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_norm = v.upper().replace(" ", "_").replace("-", "_")
            if v_norm in CauseStatus.__members__:
                return CauseStatus[v_norm]
        return v


class CauseVerifyRequest(BaseModel):
    """Mark a cause as verified by human investigator."""

    verification_notes: Optional[str] = None
    is_root_cause: bool = False


class CauseRejectRequest(BaseModel):
    """Reject a cause with documented rationale."""

    rejection_reason: str = Field(..., min_length=5, description="Documented reason for rejection")


class RCAAcceptRequest(BaseModel):
    """Explicit human QA acceptance of RCA analysis."""

    reviewer_notes: Optional[str] = Field(None, max_length=5000)
    confirmed_root_cause_ids: List[str] = Field(
        default_factory=list, description="IDs of confirmed root causes to finalize"
    )


class RCAEvidenceRequest(BaseModel):
    """Request additional evidence for inconclusive RCA."""

    evidence_requested: str = Field(..., min_length=5, max_length=5000)
    priority: str = Field(default="High")


# ---------------------------------------------------------------------------
# Legacy Relational Support Models
# ---------------------------------------------------------------------------

class WhyAnalysisStepBase(BaseModel):
    step_number: int = Field(..., ge=1)
    question: str = Field(..., max_length=500)
    answer: str
    evidence_reference: Optional[str] = Field(None, max_length=255)
    is_root_cause: bool = False


class WhyAnalysisStepCreate(WhyAnalysisStepBase):
    pass


class WhyAnalysisStepResponse(WhyAnalysisStepBase):
    id: str
    rca_analysis_id: str
    model_config = ConfigDict(from_attributes=True)


class FishboneCauseBase(BaseModel):
    cause_description: str
    parent_cause_id: Optional[str] = None
    evidence_reference: Optional[str] = Field(None, max_length=255)
    is_significant: bool = False


class FishboneCauseCreate(FishboneCauseBase):
    pass


class FishboneCauseResponse(FishboneCauseBase):
    id: str
    category_id: str
    model_config = ConfigDict(from_attributes=True)


class FishboneCategoryResponse(BaseModel):
    id: str
    rca_analysis_id: str
    name: str
    causes: List[FishboneCauseResponse] = []
    model_config = ConfigDict(from_attributes=True)


class ContributingFactorBase(BaseModel):
    description: str
    category: str = Field(..., max_length=50)
    evidence_reference: Optional[str] = Field(None, max_length=255)
    status: ContributingFactorStatus = ContributingFactorStatus.ACTIVE


class ContributingFactorCreate(ContributingFactorBase):
    pass


class ContributingFactorResponse(ContributingFactorBase):
    id: str
    root_cause_id: str
    model_config = ConfigDict(from_attributes=True)


class RootCauseBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    category: RootCauseCategory = RootCauseCategory.METHOD
    evidence_strength: EvidenceStrength = EvidenceStrength.MODERATE
    status: RootCauseStatus = RootCauseStatus.IDENTIFIED
    ai_generated: bool = False
    human_confirmed: bool = False


class RootCauseCreate(RootCauseBase):
    pass


class RootCauseResponse(RootCauseBase):
    id: str
    rca_analysis_id: str
    created_at: datetime
    updated_at: datetime
    contributing_factors: List[ContributingFactorResponse] = []
    model_config = ConfigDict(from_attributes=True)


class RCAAnalysisBase(BaseModel):
    analysis_method: RCAMethod = RCAMethod.FIVE_WHYS
    analysis_version: int = 1
    summary: Optional[str] = None
    status: RCAStatus = RCAStatus.DRAFT


class RCAAnalysisCreate(RCAAnalysisBase):
    investigation_id: str


RCAAnalysisResponse = RCAResponse

