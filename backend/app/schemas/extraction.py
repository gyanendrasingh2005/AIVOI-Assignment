from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import (
    ExtractionStatus,
    ExtractionReviewStatus,
    FieldExtractionStatus,
    FieldReviewDecision,
)

# Approved field allowlist
ALLOWED_EXTRACTION_FIELDS = {
    # Product & Batch
    "api_product_name",
    "batch_number",
    "manufacturing_stage",
    "manufacturing_facility",
    "manufacturing_date",
    "incident_date",
    "incident_time",
    # Incident Description
    "incident_title",
    "incident_description",
    "observed_event",
    "expected_condition",
    "actual_condition",
    "condition_difference",
    "potential_quality_impact",
    # Process & Equipment
    "equipment_id",
    "equipment_name",
    "process_parameter",
    "expected_parameter_value",
    "actual_parameter_value",
    "unit_of_measurement",
    "parameter_deviation",
    "process_step",
    # Immediate Actions
    "immediate_actions",
    "equipment_isolation",
    "material_segregation",
    "notifications_made",
    "other_immediate_actions",
    # Impact Information
    "affected_batches",
    "potentially_affected_materials",
    "potential_patient_impact",
    "impact_assessment_status",
    # Additional
    "mentioned_personnel",
    "relevant_dates",
    "related_records",
    "observations",
}


class SourceReference(BaseModel):
    """Traceable empirical citation supporting an extracted field."""

    document_id: str = Field(..., description="UUID of the supporting source document")
    filename: str = Field(..., description="Original filename of the supporting document")
    page_number: Optional[int] = Field(None, description="Page number where the excerpt was observed")
    excerpt: str = Field(..., max_length=2000, description="Exact factual quotation from the source text")


class ExtractedField(BaseModel):
    """Single incident information item with confidence and source grounding."""

    field_name: str = Field(..., description="Standardized field key from approved allowlist")
    value: Optional[Any] = Field(None, description="Extracted factual value, or null if not found")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Model-estimated confidence 0.0 to 1.0")
    source_references: List[SourceReference] = Field(default_factory=list, description="Empirical document citations")
    status: FieldExtractionStatus = Field(default=FieldExtractionStatus.EXTRACTED, description="Extraction state")
    explanation: Optional[str] = Field(None, max_length=1000, description="Analytical commentary or conflict rationale")

    # Human review attributes
    reviewed_value: Optional[Any] = Field(None, description="Human-edited value override")
    review_decision: FieldReviewDecision = Field(default=FieldReviewDecision.PENDING, description="Human decision")
    reviewed_by: Optional[str] = Field(None, description="User ID of reviewing investigator")
    reviewed_at: Optional[datetime] = Field(None, description="Timestamp of human review")
    is_modified: bool = Field(default=False, description="True if human investigator edited the AI suggestion")

    @field_validator("field_name")
    def validate_field_name(cls, v: str) -> str:
        if v not in ALLOWED_EXTRACTION_FIELDS:
            # Allow fallback if model prefixed or snake_cased
            cleaned = v.strip().lower()
            if cleaned in ALLOWED_EXTRACTION_FIELDS:
                return cleaned
            raise ValueError(f"Field '{v}' is not in approved extraction allowlist.")
        return v


class MissingInformationItem(BaseModel):
    """Identified evidence gap or missing parameter in reviewed records."""

    field_name: str
    description: str
    impact: Optional[str] = None


class ConflictingInformationItem(BaseModel):
    """Documented discrepancy between two or more source documents."""

    field_name: str
    description: str
    conflicting_references: List[SourceReference] = Field(default_factory=list)


class DocumentProcessingSummary(BaseModel):
    """Processing status of a document selected for extraction."""

    document_id: str
    filename: str
    status: str  # "ANALYZED", "OCR_REQUIRED", "FAILED", "EMPTY"
    page_count: Optional[int] = None
    notes: Optional[str] = None


class ExtractionStructuredOutput(BaseModel):
    """Output contract for LLM structured JSON generation."""

    fields: List[ExtractedField] = Field(default_factory=list)
    missing_information: List[MissingInformationItem] = Field(default_factory=list)
    conflicting_information: List[ConflictingInformationItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# API Request & Response Schemas
# ---------------------------------------------------------------------------

class IncidentExtractionRequest(BaseModel):
    """Request payload to initiate AI incident extraction."""

    document_ids: List[str] = Field(..., min_length=1, description="List of source document UUIDs to analyze")
    extraction_instructions: Optional[str] = Field(
        None, max_length=1000, description="Optional focus instructions (e.g. 'Focus on crystallization temperature')"
    )


class FieldReviewUpdateRequest(BaseModel):
    """Review decision and optional edit for a single extracted field."""

    field_name: str
    reviewed_value: Optional[Any] = None
    review_decision: FieldReviewDecision


class ExtractionReviewPatchRequest(BaseModel):
    """Batch update payload for human review decisions."""

    fields: List[FieldReviewUpdateRequest] = Field(..., min_length=1)


class FieldAcceptanceRequest(BaseModel):
    """Request to apply accepted fields to the confirmed Incident record."""

    field_names: Optional[List[str]] = Field(
        None, description="Optional list of specific field names to accept; if omitted, accepts all APPROVED fields"
    )


class FieldRejectionRequest(BaseModel):
    """Request to reject specific fields or entire extraction."""

    field_names: Optional[List[str]] = Field(
        None, description="Optional list of specific field names to reject; if omitted, marks entire extraction rejected"
    )
    reason: Optional[str] = Field(None, max_length=500, description="Optional justification for rejection")


class IncidentExtractionResponse(BaseModel):
    """Complete representation of an AI incident extraction run."""

    id: str
    investigation_id: str
    ai_execution_id: Optional[str] = None
    created_by: Optional[str] = None
    source_document_ids: List[str] = Field(default_factory=list)
    provider: str
    model: str
    prompt_version: str
    status: str
    review_status: str
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    missing_information: List[Any] = Field(default_factory=list)
    conflicting_information: List[Any] = Field(default_factory=list)
    document_summaries: List[Any] = Field(default_factory=list)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExtractionReviewViewResponse(BaseModel):
    """Investigation review interface schema with original AI suggestions vs review decisions."""

    extraction_id: str
    investigation_id: str
    status: str
    review_status: str
    fields: List[ExtractedField] = Field(default_factory=list)
    missing_information: List[MissingInformationItem] = Field(default_factory=list)
    conflicting_information: List[ConflictingInformationItem] = Field(default_factory=list)
    document_summaries: List[DocumentProcessingSummary] = Field(default_factory=list)

