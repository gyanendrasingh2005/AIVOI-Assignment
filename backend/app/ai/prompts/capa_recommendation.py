from typing import List, Optional
from pydantic import BaseModel, Field


class CAPARecommendationItemStructured(BaseModel):
    recommendation_title: str = Field(
        ...,
        description="Action-oriented title specifying the exact engineering, procedural, or operational modification.",
    )
    description: str = Field(
        ...,
        description="Comprehensive description of what must change, where it must change, and technical mechanism.",
    )
    action_type: str = Field(
        ...,
        description="'CORRECTIVE' to eliminate cause of existing deviation, or 'PREVENTIVE' to prevent recurrence across related systems.",
    )
    root_cause_id: Optional[str] = Field(
        None,
        description="ID of the verified root cause addressed from the investigation context. Leave None if addressing a general systemic gap.",
    )
    root_cause_title: Optional[str] = Field(
        None,
        description="Title of the addressed root cause.",
    )
    contributing_factor_ids: List[str] = Field(
        default_factory=list,
        description="List of contributing factor IDs directly resolved by this action.",
    )
    evidence_gap_ids: List[str] = Field(
        default_factory=list,
        description="List of unresolved evidence gap IDs mitigated or closed by this action.",
    )
    supporting_references: List[str] = Field(
        default_factory=list,
        description="Supporting document citations, BPR page numbers, or evidence IDs backing this action.",
    )
    rationale: str = Field(
        ...,
        description="Technical justification explaining why this specific action is appropriate and consequence of inaction.",
    )
    expected_outcome: str = Field(
        ...,
        description="Measurable end state and expected reduction in recurrence risk.",
    )
    recurrence_risk_addressed: Optional[str] = Field(
        None,
        description="Specific failure mode and residual recurrence risk addressed.",
    )
    priority: str = Field(
        "MEDIUM",
        description="'CRITICAL', 'HIGH', 'MEDIUM', or 'LOW' based on patient safety, quality impact, and recurrence likelihood.",
    )
    suggested_department: Optional[str] = Field(
        None,
        description="Responsible department (e.g., Engineering, Manufacturing, Quality Control, QA, Metrology).",
    )
    suggested_role: Optional[str] = Field(
        None,
        description="Designated role (e.g., Maintenance Lead, Process Engineer, Validation Specialist, Training Manager).",
    )
    suggested_target_days: int = Field(
        30,
        description="Realistic completion timeframe in days (e.g., 14 for critical equipment repairs, 30-45 for procedure updates, 60 for re-qualification).",
    )
    implementation_steps: List[str] = Field(
        default_factory=list,
        description="Numbered or sequential steps required to implement the action.",
    )
    completion_criteria: str = Field(
        ...,
        description="Measurable criteria demonstrating that the action has been fully and correctly executed.",
    )
    required_completion_evidence: str = Field(
        ...,
        description="Specific documentation required to close the action (e.g., IQ/OQ execution report, approved SOP redline, signed training logs).",
    )
    implementation_risks: Optional[str] = Field(
        None,
        description="Potential operational or compliance risks introduced during implementation and mitigation.",
    )
    is_provisional: bool = Field(
        False,
        description="Set to true if this recommendation is based on an unverified hypothesis rather than a confirmed root cause.",
    )
    uncertainty_rationale: Optional[str] = Field(
        None,
        description="Explanation of uncertainties or remaining evidentiary gaps if provisional.",
    )


class CAPARecommendationsOutputStructured(BaseModel):
    recommendations: List[CAPARecommendationItemStructured] = Field(
        default_factory=list,
        description="List of structured corrective and preventive action recommendations.",
    )
    summary: str = Field(
        ...,
        description="Executive summary of the overall CAPA strategy and risk reduction rationale.",
    )
    corrective_actions_count: int = Field(0, description="Total count of corrective actions.")
    preventive_actions_count: int = Field(0, description="Total count of preventive actions.")


CAPA_RECOMMENDATION_SYSTEM_PROMPT = """You are a Senior Pharmaceutical Quality Systems Architect, CAPA Specialist, and API Manufacturing Subject Matter Expert.

Your role is to formulate professional, evidence-grounded Corrective and Preventive Action (CAPA) recommendations conforming to:
- ICH Q10 Pharmaceutical Quality System guidelines
- FDA 21 CFR Part 211 (Current Good Manufacturing Practice for Finished Pharmaceuticals)
- WHO Good Manufacturing Practices for Active Pharmaceutical Ingredients (APIs)
- ISO 9001 / ISO 13485 Corrective and Preventive Action requirements

### REGULATORY PRINCIPLES & GOVERNANCE:
1. CLEAR ACTION CLASSIFICATION:
   - CORRECTIVE ACTION: Intended to eliminate an identified cause of an existing nonconformity or deviation (e.g., replace defective seal gasket, recalibrate drift transmitter, revise conflicting SOP instructions, correct raw material handling).
   - PREVENTIVE ACTION: Intended to eliminate the cause of a potential nonconformity or prevent recurrence across related systems, suites, or products (e.g., introduce automated pressure trend alarms, enhance preventive maintenance frequency on all vacuum dryers, implement pre-batch verification checklists).
   - IMMEDIATE CORRECTION vs SYSTEMIC ACTION: Do not mistake an immediate batch disposition (e.g., "quarantine and re-dry lot") for a systemic Corrective Action. Recommend systemic actions that resolve the root cause.

2. EVIDENCE-GROUNDED TRACEABILITY:
   - Every recommended action MUST be mapped to an identified root cause ID or contributing factor ID from the investigation context.
   - If a root cause is an UNVERIFIED hypothesis, you MUST set `is_provisional = true` and articulate the evidentiary uncertainty in `uncertainty_rationale`.
   - Cite verified document inventory or evidence IDs provided in the context. NEVER invent non-existent batch numbers, equipment IDs, or citation references.

3. SMART ACTION QUALITY REQUIREMENTS:
   - Specific: Clearly describe what must change, where it must change, and who should perform it.
   - Measurable: Define concrete completion criteria and required documentation (e.g., approved IQ/OQ protocol, revised SOP-MFG-042 rev 05 with QA sign-off, calibration certificate).
   - Achievable: Propose realistic target timelines (e.g., 14-30 days for engineering repairs, 30-45 days for SOP revisions and training, 60 days for equipment qualification).
   - Relevant: Directly address the confirmed failure mechanism and avoid unrelated changes.
   - Time-bound: Specify realistic implementation days and milestones.

4. STRICT PROHIBITION AGAINST VAGUE ACTIONS:
   - Recommendations containing vague platitudes such as "Improve quality", "Be more careful", "Follow SOP strictly", "Conduct regular monitoring", or "Increase awareness" are strictly forbidden.
   - State the exact procedural clause, parameter tolerance, mechanical assembly, or training evaluation method.
"""

CAPA_RECOMMENDATION_USER_PROMPT = """Analyze the following verified investigation context and formulate structured CAPA recommendations:

INVESTIGATION IDENTIFICATION:
- Investigation ID: {investigation_id}
- Reference Number: {investigation_number}
- Title: {title}
- Current Stage: {stage}

CONFIRMED INCIDENT:
{incident_context}

ACCEPTED RISK ASSESSMENT:
{risk_context}

VERIFIED ROOT CAUSES & CONTRIBUTING FACTORS:
{root_causes_context}

UNVERIFIED CAUSAL HYPOTHESES:
{hypotheses_context}

UNRESOLVED EVIDENCE GAPS:
{evidence_gaps_context}

EXISTING CAPAS (AVOID DUPLICATION):
{existing_capas_context}

VERIFIED EVIDENCE INVENTORY:
{evidence_inventory_context}

USER FOCUS:
{focus_instruction}

Generate a comprehensive set of targeted Corrective Actions and Preventive Actions that eliminate root causes, address contributing factors, resolve critical evidence gaps, and mitigate recurrence risk.
"""

