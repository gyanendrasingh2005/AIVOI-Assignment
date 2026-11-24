"""
Pydantic Schemas for AI-Assisted Pharmaceutical Quality and Risk Assessment.
Compliant with 21 CFR Part 11 ALCOA+ standards.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    RiskClassification,
    RiskLikelihood,
    RiskDetectability,
    InvestigationUrgency,
    RiskAssessmentStatus,
    RiskAssessmentReviewStatus,
)

# Approved Dimension Evaluation Statuses
DIMENSION_STATUS_ALLOWLIST = {
    "No evidence identified",
    "Potential impact identified",
    "Impact cannot currently be determined",
    "Confirmed impact documented in source evidence",
}


class RiskEvidenceReference(BaseModel):
    """Traceable empirical citation supporting risk dimension evaluations."""

    document_id: Optional[str] = Field(None, description="UUID of the supporting source document")
    evidence_id: Optional[str] = Field(None, description="UUID of associated evidence item if existing")
    filename: Optional[str] = Field(None, description="Filename of supporting document")
    page_number: Optional[int] = Field(None, description="Page number where excerpt was observed")
    excerpt: str = Field(..., max_length=2500, description="Exact factual quotation from source document")
    related_field: Optional[str] = Field(None, description="Associated field or dimension name")
    relevance_reason: Optional[str] = Field(None, max_length=1000, description="Reasoning linking citation to risk conclusion")


class DimensionEvaluation(BaseModel):
    """Detailed evaluation of an individual risk dimension."""

    status: str = Field(
        ...,
        description="Evaluation status: 'No evidence identified', 'Potential impact identified', "
                    "'Impact cannot currently be determined', or 'Confirmed impact documented in source evidence'",
    )
    findings: str = Field(..., description="Factual analysis and narrative summary of findings")
    supporting_references: List[RiskEvidenceReference] = Field(
        default_factory=list,
        description="Empirical document or evidence citations grounding this dimension",
    )
    concerns: List[str] = Field(
        default_factory=list,
        description="Specific quality, patient safety, regulatory or GMP concerns",
    )
    is_unverified: bool = Field(
        default=False,
        description="True if finding is derived from unconfirmed AI drafts or missing records",
    )

    @field_validator("status")
    def validate_dimension_status(cls, v: str) -> str:
        if v not in DIMENSION_STATUS_ALLOWLIST:
            # Fallback check case-insensitive match
            for allowed in DIMENSION_STATUS_ALLOWLIST:
                if v.strip().lower() == allowed.lower():
                    return allowed
            raise ValueError(
                f"Dimension status '{v}' is not recognized. Must be one of: {list(DIMENSION_STATUS_ALLOWLIST)}"
            )
        return v


class MissingEvidenceItem(BaseModel):
    """Identified data gap critical to quality or risk assessment."""

    field_name: str = Field(..., description="Parameter or document type missing")
    description: str = Field(..., description="Description of the missing information")
    risk_implication: Optional[str] = Field(
        None, description="Why this missing information affects risk estimation or uncertainty"
    )


class ConflictingEvidenceItem(BaseModel):
    """Conflict observed across records or parameters."""

    field_name: str = Field(..., description="Subject of the discrepancy")
    description: str = Field(..., description="Detailed description of the conflict")
    conflicting_references: List[RiskEvidenceReference] = Field(
        default_factory=list, description="Citations demonstrating the discrepancy"
    )


class RiskAssessmentStructuredOutput(BaseModel):
    """Structured LLM response for pharmaceutical quality and risk assessment."""

    # 6 Core Dimensions
    quality_impact: DimensionEvaluation = Field(..., description="Product quality and critical quality attributes impact")
    patient_impact: DimensionEvaluation = Field(..., description="Patient safety and clinical risk evaluation")
    batch_impact: DimensionEvaluation = Field(..., description="Affected batch, prior/subsequent batches, inventory impact")
    process_impact: DimensionEvaluation = Field(..., description="Process parameters, recipe steps, validated state impact")
    equipment_impact: DimensionEvaluation = Field(..., description="Equipment integrity, calibration, cleaning, maintenance impact")
    data_integrity_impact: DimensionEvaluation = Field(..., description="ALCOA+ principles, records, audit trails, tampering concerns")

    # Risk Classifications
    severity: RiskClassification = Field(..., description="Severity classification (Critical, Major, Minor, Undetermined)")
    likelihood: RiskLikelihood = Field(..., description="Likelihood of recurrence or harm (High, Medium, Low, Unlikely, Uncertain)")
    detectability: Optional[RiskDetectability] = Field(None, description="Detectability prior to release (Low, Medium, High)")
    overall_risk: RiskClassification = Field(..., description="Overall risk level derived from matrix")

    risk_rationale: str = Field(..., description="Comprehensive explanation of risk evaluation and justification")
    urgency_recommendation: InvestigationUrgency = Field(..., description="Urgency recommendation for QA oversight")

    # Traceability
    supporting_references: List[RiskEvidenceReference] = Field(
        default_factory=list, description="All citations grounding the assessment"
    )
    missing_information: List[MissingEvidenceItem] = Field(
        default_factory=list, description="Missing evidence or parameter gaps"
    )
    conflicting_evidence: List[ConflictingEvidenceItem] = Field(
        default_factory=list, description="Discrepancies found across source evidence"
    )
    uncertainty_notes: Optional[str] = Field(None, description="Analytical commentary on uncertainty bounds")
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Overall confidence score 0.0 to 1.0")


# API Request / Response schemas

class RiskAssessmentRequest(BaseModel):
    """Request payload to initiate AI risk assessment."""

    use_documents: bool = Field(default=True, description="Whether to include extracted text from uploaded documents")
    additional_instructions: Optional[str] = Field(
        None, max_length=2000, description="Optional focused investigator instructions"
    )


class RiskAssessmentReviewPatchRequest(BaseModel):
    """Human QA investigator review modifications and overrides."""

    overall_risk_override: Optional[RiskClassification] = Field(None, description="Human override for overall risk")
    severity_override: Optional[RiskClassification] = Field(None, description="Human override for severity")
    likelihood_override: Optional[RiskLikelihood] = Field(None, description="Human override for likelihood")
    reviewer_notes: Optional[str] = Field(None, max_length=5000, description="Investigator or QA notes")
    review_decision: Optional[RiskAssessmentReviewStatus] = Field(
        None, description="Review decision state (PENDING_REVIEW, NEEDS_MORE_INFORMATION, ACCEPTED, REJECTED, SUPERSEDED)"
    )


class RiskAssessmentAcceptRequest(BaseModel):
    """Request for QA acceptance of a risk assessment."""

    apply_to_investigation: bool = Field(
        default=True,
        description="Whether to synchronize accepted risk level and priority to the parent Investigation record",
    )
    reviewer_notes: Optional[str] = Field(None, max_length=5000, description="QA acceptance justification notes")


class RiskAssessmentRejectRequest(BaseModel):
    """Request to reject a risk assessment."""

    reason: str = Field(..., min_length=5, max_length=5000, description="Documented reason for rejection")


class RiskAssessmentInfoRequest(BaseModel):
    """Request additional information for an inconclusive risk assessment."""

    information_requested: str = Field(..., min_length=5, max_length=5000, description="Required information description")


class RiskAssessmentResponse(BaseModel):
    """Public representation of RiskAssessment entity."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    investigation_id: str
    ai_execution_id: Optional[str] = None
    created_by: Optional[str] = None
    framework_version: str

    incident_snapshot: Dict[str, Any]
    quality_impact: Dict[str, Any]
    patient_impact: Dict[str, Any]
    batch_impact: Dict[str, Any]
    process_impact: Dict[str, Any]
    equipment_impact: Dict[str, Any]
    data_integrity_impact: Dict[str, Any]

    severity: str
    likelihood: str
    detectability: Optional[str] = None
    overall_risk: str

    risk_rationale: str
    urgency_recommendation: str

    supporting_references: List[Dict[str, Any]]
    missing_information: List[Dict[str, Any]]
    conflicting_evidence: List[Dict[str, Any]]
    uncertainty_notes: Optional[str] = None
    confidence_score: float

    status: str
    review_status: str
    reviewer_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class RiskAssessmentListResponse(BaseModel):
    """Paginated list of risk assessments for an investigation."""

    items: List[RiskAssessmentResponse]
    total: int


class RiskAssessmentReviewViewResponse(BaseModel):
    """Comprehensive view tailored for QA review screen."""

    assessment: RiskAssessmentResponse
    has_unreviewed_incident_data: bool = Field(
        default=False,
        description="True if incident information relied upon is derived from unconfirmed AI drafts",
    )
    active_in_investigation: bool = Field(
        default=False,
        description="True if this assessment's risk level is currently reflected in the active investigation",
    )
    matrix_metadata: Dict[str, Any]
