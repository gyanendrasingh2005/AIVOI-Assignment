"""
Evidence Gap & Investigation Completeness Prompt Template
=========================================================
Adheres to 21 CFR Part 211, ICH Q9 (Quality Risk Management) and ICH Q10 (Pharmaceutical Quality Systems).
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class GapReferenceItem(BaseModel):
    document_id: Optional[str] = None
    evidence_id: Optional[str] = None
    filename: Optional[str] = None
    page_number: Optional[int] = None
    excerpt: Optional[str] = None
    relevance_reason: Optional[str] = None


class DetectedGapItem(BaseModel):
    gap_title: str
    category: str = Field(
        ...,
        description="One of: INCIDENT_INFORMATION, DOCUMENTATION, MANUFACTURING_PROCESS, EQUIPMENT, MATERIAL, BATCH_TRACEABILITY, ANALYTICAL, QUALITY_IMPACT, RCA_SUPPORT, FIVE_WHYS, FISHBONE, EVIDENCE_CONFLICT, SOURCE_VERIFICATION, INVESTIGATION_REVIEW, OTHER",
    )
    detection_type: str = Field(
        ...,
        description="One of: MISSING_INFORMATION, MISSING_EVIDENCE, INSUFFICIENT_EVIDENCE, CONFLICTING_EVIDENCE, STALE_EVIDENCE, UNVERIFIED_SOURCE, MISSING_TRACEABILITY, UNSUPPORTED_CAUSAL_CLAIM",
    )
    priority: str = Field(..., description="One of: CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL")
    description: str = Field(..., description="What specifically is missing or conflicting?")
    why_needed: str = Field(..., description="Why is this evidence essential to GMP/quality compliance?")
    affected_area: str = Field(..., description="Which part of the investigation does it affect?")
    recommended_evidence_type: str
    recommended_action: str = Field(..., description="Specific operational next step for the investigator.")
    confidence: float = Field(0.85, ge=0.0, le=1.0)
    supporting_references: List[GapReferenceItem] = Field(default_factory=list)


class DimensionEvaluationItem(BaseModel):
    dimension_name: str
    status: str = Field(..., description="One of: COMPLETE, PARTIALLY_COMPLETE, INCOMPLETE, NOT_APPLICABLE, UNDETERMINED")
    explanation: str
    missing_information: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)


class ConflictingEvidenceItem(BaseModel):
    item_a: str
    item_b: str
    conflict_description: str
    suggested_resolution: str


class GapAssessmentStructuredOutput(BaseModel):
    overall_status: str = Field(..., description="One of: COMPLETE, PARTIALLY_COMPLETE, INCOMPLETE, UNDETERMINED")
    completeness_score: float = Field(..., ge=0.0, le=100.0, description="Numerical readiness score 0.0 to 100.0")
    summary: str
    dimensions: List[DimensionEvaluationItem] = Field(
        ...,
        description="Mandatory 11 dimensions: Incident information, Document availability, Evidence traceability, Manufacturing process evidence, Equipment evidence, Material and batch evidence, Quality impact assessment, 5 Whys completeness, Fishbone completeness, Root cause verification, Investigation review completeness",
    )
    detected_gaps: List[DetectedGapItem] = Field(default_factory=list)
    conflicting_evidence: List[ConflictingEvidenceItem] = Field(default_factory=list)
    recommended_activities: List[str] = Field(default_factory=list)


GAP_ASSESSMENT_SYSTEM_PROMPT = """You are a Lead Pharmaceutical Quality Systems Auditor and GMP Regulatory Investigator specializing in active pharmaceutical ingredient (API) manufacturing (ICH Q7, Q9, Q10, 21 CFR Part 211).

Your mission is to perform an objective, evidence-grounded Evidence Gap Detection and Investigation Completeness Assessment.

CRITICAL REGULATORY PRINCIPLES:
1. EVIDENCE GROUNDING: Every gap must identify concrete missing data or records grounded in the investigation facts.
2. NEVER FABRICATE: Never invent document IDs, evidence IDs, batch numbers, equipment tags, or test results.
3. HUMAN DECISION AUTHORITY: All detected gaps are recommendations for human quality investigator review.
4. 11 MANDATORY DIMENSIONS TO ASSESS:
   - Incident information
   - Document availability
   - Evidence traceability
   - Manufacturing process evidence
   - Equipment evidence
   - Material and batch evidence
   - Quality impact assessment
   - 5 Whys completeness
   - Fishbone completeness
   - Root cause verification
   - Investigation review completeness
5. EVALUATE CONFLICTS & ASSUMPTIONS: Identify contradictions across documents or unsupported claims in root cause hypotheses.
6. RISK-BASED PRIORITIZATION: Prioritize gaps as CRITICAL or HIGH if they compromise product safety, batch release validity, or regulatory compliance.

Return output strictly conforming to the requested JSON schema.
"""


def build_gap_assessment_user_prompt(
    context_text: str,
    rules_text: str,
) -> str:
    return f"""Please perform an Evidence Gap Detection and Investigation Completeness Assessment for the following pharmaceutical investigation:

{context_text}

--- APPLICABLE EVIDENCE REQUIREMENT PROFILE RULES ---
{rules_text}

INSTRUCTIONS:
1. Systematically evaluate all 11 required completeness dimensions against the provided investigation records.
2. For any missing requirement, unverified root cause, or conflicting data, generate a specific DetectedGapItem.
3. Compute a realistic completeness score (0-100) reflecting the true completeness of the evidence package.
4. Formulate specific, actionable investigator activities to close each gap.
"""

