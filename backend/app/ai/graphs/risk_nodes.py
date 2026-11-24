"""
LangGraph execution nodes for AI-assisted Quality Impact and Risk Assessment.
Handles context preparation, model execution, citation verification, and risk matrix derivation.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable

from app.models.enums import (
    RiskClassification,
    RiskLikelihood,
    RiskDetectability,
    InvestigationUrgency,
    RiskAssessmentStatus,
)
from app.core.risk_framework import RiskFramework
from app.ai.providers.base import BaseAIProvider
from app.ai.prompts.base import get_system_prompt
from app.ai.graphs.risk_state import RiskAssessmentWorkflowState
from app.schemas.risk_assessment import (
    RiskAssessmentStructuredOutput,
    DimensionEvaluation,
    RiskEvidenceReference,
)

logger = logging.getLogger(__name__)


def validate_risk_request_node(state: RiskAssessmentWorkflowState) -> RiskAssessmentWorkflowState:
    """Validates required input context for risk assessment."""
    errors = list(state.get("errors", []))

    if not state.get("investigation_id"):
        errors.append("Missing required investigation_id in risk assessment state.")

    incident_snapshot = state.get("incident_snapshot", {})
    if not incident_snapshot:
        errors.append("Missing incident data or snapshot for risk evaluation.")

    if errors:
        state["errors"] = errors
        state["status"] = RiskAssessmentStatus.FAILED.value
        return state

    state["errors"] = []
    state["status"] = RiskAssessmentStatus.PROCESSING.value
    state["framework_version"] = state.get("framework_version") or RiskFramework.VERSION
    return state


def prepare_risk_context_node(state: RiskAssessmentWorkflowState) -> RiskAssessmentWorkflowState:
    """
    Assembles structured prompt context combining confirmed/draft incident details
    and associated document evidence.
    """
    if state.get("status") == RiskAssessmentStatus.FAILED.value:
        return state

    framework_version = state.get("framework_version", RiskFramework.VERSION)
    system_prompt = get_system_prompt("risk_assessment", framework_version)
    state["system_prompt"] = system_prompt

    snapshot = state.get("incident_snapshot", {})
    has_unreviewed = state.get("has_unreviewed_incident_data", False)
    doc_context = state.get("document_context", "")
    instructions = state.get("additional_instructions")

    lines = ["# INCIDENT INFORMATION FOR QUALITY & RISK EVALUATION\n"]

    if has_unreviewed:
        lines.append(
            "> [!WARNING] DATA RELIABILITY NOTICE:\n"
            "> Some or all incident data below originates from UNCONFIRMED AI EXTRACTIONS awaiting human review.\n"
            "> Treat any unverified parameter conservatively and note information gaps in the assessment.\n"
        )

    # Format incident fields
    lines.append(f"Product Name: {snapshot.get('api_product_name', 'Not specified')}")
    lines.append(f"Batch Number: {snapshot.get('batch_number', 'Not specified')}")
    lines.append(f"Manufacturing Stage: {snapshot.get('manufacturing_stage', 'Not specified')}")
    lines.append(f"Incident Date: {snapshot.get('incident_date', 'Not specified')}")
    lines.append(f"Equipment Involved: {snapshot.get('equipment_id', 'Not specified')}")
    lines.append(f"Expected Parameter: {snapshot.get('expected_parameter', 'Not specified')}")
    lines.append(f"Actual Parameter: {snapshot.get('actual_parameter', 'Not specified')}")
    lines.append(f"Incident Description:\n{snapshot.get('incident_description', 'No description provided')}")

    if snapshot.get("immediate_actions"):
        lines.append(f"\nImmediate Actions Taken:\n{snapshot.get('immediate_actions')}")

    if snapshot.get("affected_batches"):
        lines.append(f"\nAffected Batches Identified: {snapshot.get('affected_batches')}")

    if snapshot.get("potential_quality_impact"):
        lines.append(f"\nPreliminary Quality Impact Notes:\n{snapshot.get('potential_quality_impact')}")

    # Append document evidence if available
    if doc_context and doc_context.strip():
        lines.append("\n\n# SOURCE DOCUMENT EVIDENCE\n")
        lines.append(doc_context)
    else:
        lines.append("\n\n# SOURCE DOCUMENT EVIDENCE\nNo uploaded document text available for this investigation.")

    if instructions:
        lines.append(f"\n\n# INVESTIGATOR FOCUS INSTRUCTIONS\n{instructions}")

    lines.append("\n\nTASK:")
    lines.append("1. Evaluate Product Quality, Patient Impact, Batch/Material, Process, Equipment, and Data Integrity.")
    lines.append("2. Ground findings with supporting_references citing document_id, filename, page_number, and verbatim excerpt.")
    lines.append("3. Classify Severity, Likelihood, Detectability, Overall Risk, and Urgency Recommendation.")
    lines.append("4. List any missing GMP evidence or contradictory records.")
    lines.append("5. Return strictly valid JSON conforming to RiskAssessmentStructuredOutput schema.")

    state["user_prompt"] = "\n".join(lines)
    return state


def make_evaluate_risk_node(
    provider: BaseAIProvider,
) -> Callable[[RiskAssessmentWorkflowState], Awaitable[RiskAssessmentWorkflowState]]:
    """Factory creating the async LLM execution node for structured risk evaluation."""

    async def evaluate_risk_node(state: RiskAssessmentWorkflowState) -> RiskAssessmentWorkflowState:
        if state.get("status") == RiskAssessmentStatus.FAILED.value:
            return state

        system_prompt = state.get("system_prompt", "")
        user_prompt = state.get("user_prompt", "")
        start_time = time.time()

        try:
            result = await provider.generate_structured(
                prompt=user_prompt,
                response_model=RiskAssessmentStructuredOutput,
                system_prompt=system_prompt,
            )
            latency_ms = result.latency_ms or int((time.time() - start_time) * 1000)
            state["latency_ms"] = latency_ms
            state["raw_response"] = result.raw_content
            state["token_usage"] = {
                "prompt_tokens": result.token_usage.prompt_tokens,
                "completion_tokens": result.token_usage.completion_tokens,
                "total_tokens": result.token_usage.total_tokens,
            }

            if result.parsed_successfully and result.data:
                data: RiskAssessmentStructuredOutput = result.data
                res_dict = data.model_dump()

                state["quality_impact"] = res_dict.get("quality_impact", {})
                state["patient_impact"] = res_dict.get("patient_impact", {})
                state["batch_impact"] = res_dict.get("batch_impact", {})
                state["process_impact"] = res_dict.get("process_impact", {})
                state["equipment_impact"] = res_dict.get("equipment_impact", {})
                state["data_integrity_impact"] = res_dict.get("data_integrity_impact", {})

                # Severity & Likelihood
                sev = res_dict.get("severity")
                state["severity"] = sev.value if hasattr(sev, "value") else str(sev or RiskClassification.UNDETERMINED.value)

                lik = res_dict.get("likelihood")
                state["likelihood"] = lik.value if hasattr(lik, "value") else str(lik or RiskLikelihood.UNDETERMINED.value)

                det = res_dict.get("detectability")
                state["detectability"] = det.value if hasattr(det, "value") else (str(det) if det else None)

                ovr = res_dict.get("overall_risk")
                state["overall_risk"] = ovr.value if hasattr(ovr, "value") else str(ovr or RiskClassification.UNDETERMINED.value)

                state["risk_rationale"] = res_dict.get("risk_rationale", "No rationale generated.")

                urg = res_dict.get("urgency_recommendation")
                state["urgency_recommendation"] = urg.value if hasattr(urg, "value") else str(urg or InvestigationUrgency.STANDARD.value)

                state["supporting_references"] = res_dict.get("supporting_references", [])
                state["missing_information"] = res_dict.get("missing_information", [])
                state["conflicting_evidence"] = res_dict.get("conflicting_evidence", [])
                state["uncertainty_notes"] = res_dict.get("uncertainty_notes")
                state["confidence_score"] = float(res_dict.get("confidence_score", 0.8))
            else:
                errors = list(state.get("errors", []))
                err_msg = result.validation_error or "Structured risk assessment parsing failed."
                errors.append(err_msg)
                state["errors"] = errors
                state["status"] = RiskAssessmentStatus.FAILED.value

        except Exception as exc:
            logger.error("Error during AI risk evaluation: %s", exc, exc_info=True)
            latency_ms = int((time.time() - start_time) * 1000)
            errors = list(state.get("errors", []))
            errors.append(f"AI risk evaluation failed: {str(exc)}")
            state["errors"] = errors
            state["status"] = RiskAssessmentStatus.FAILED.value
            state["latency_ms"] = latency_ms

        return state

    return evaluate_risk_node


def validate_risk_citations_node(state: RiskAssessmentWorkflowState) -> RiskAssessmentWorkflowState:
    """
    Validates empirical citations against known valid document UUIDs.
    If a reference cites an unknown document ID, it is stripped or marked unverified.
    """
    if state.get("status") == RiskAssessmentStatus.FAILED.value:
        return state

    valid_map = state.get("valid_document_map", {})
    raw_refs = list(state.get("supporting_references", []))
    validated_refs: List[Dict[str, Any]] = []

    for ref in raw_refs:
        ref_dict = dict(ref)
        doc_id = ref_dict.get("document_id")
        if doc_id:
            if doc_id not in valid_map:
                logger.warning("Referenced document_id '%s' not found in valid documents list.", doc_id)
                ref_dict["document_id"] = None
                ref_dict["relevance_reason"] = (
                    f"(Unverified Citation) {ref_dict.get('relevance_reason', '')}"
                ).strip()
            else:
                ref_dict["filename"] = valid_map[doc_id]
        validated_refs.append(ref_dict)

    state["supporting_references"] = validated_refs

    # Validate citations inside each dimension
    dim_keys = [
        "quality_impact",
        "patient_impact",
        "batch_impact",
        "process_impact",
        "equipment_impact",
        "data_integrity_impact",
    ]
    for key in dim_keys:
        dim = dict(state.get(key, {}))
        refs = dim.get("supporting_references", [])
        clean_refs = []
        for r in refs:
            rd = dict(r)
            d_id = rd.get("document_id")
            if d_id and d_id not in valid_map:
                rd["document_id"] = None
                rd["relevance_reason"] = f"(Unverified Citation) {rd.get('relevance_reason', '')}".strip()
            elif d_id and d_id in valid_map:
                rd["filename"] = valid_map[d_id]
            clean_refs.append(rd)
        dim["supporting_references"] = clean_refs
        state[key] = dim

    return state


def calculate_framework_matrix_node(state: RiskAssessmentWorkflowState) -> RiskAssessmentWorkflowState:
    """
    Calculates and reconciles the overall risk and urgency recommendation using
    the versioned RiskFramework matrix logic. Ensures consistency and deterministic rules.
    """
    if state.get("status") == RiskAssessmentStatus.FAILED.value:
        return state

    raw_severity = str(state.get("severity", RiskClassification.UNDETERMINED.value))
    raw_likelihood = str(state.get("likelihood", RiskLikelihood.UNDETERMINED.value))
    raw_detectability = state.get("detectability")

    # Map string to enums safely
    severity_enum = RiskClassification.UNDETERMINED
    for e in RiskClassification:
        if raw_severity.strip().lower() == e.value.lower():
            severity_enum = e
            break

    likelihood_enum = RiskLikelihood.UNDETERMINED
    for e in RiskLikelihood:
        if raw_likelihood.strip().lower() == e.value.lower():
            likelihood_enum = e
            break

    detectability_enum = None
    if raw_detectability:
        for e in RiskDetectability:
            if str(raw_detectability).strip().lower() == e.value.lower():
                detectability_enum = e
                break

    # Calculate overall risk via framework
    overall_risk = RiskFramework.calculate_overall_risk(
        severity=severity_enum,
        likelihood=likelihood_enum,
        detectability=detectability_enum,
    )

    # Check patient impact and missing info gaps
    patient_impact = state.get("patient_impact", {})
    patient_status = patient_impact.get("status", "")
    patient_undetermined = (
        patient_status == "Impact cannot currently be determined"
        or severity_enum == RiskClassification.UNDETERMINED
    )
    has_critical_gaps = bool(state.get("missing_information"))

    urgency = RiskFramework.determine_urgency(
        overall_risk=overall_risk,
        has_critical_gaps=has_critical_gaps,
        patient_impact_undetermined=patient_undetermined,
    )

    state["severity"] = severity_enum.value
    state["likelihood"] = likelihood_enum.value
    state["detectability"] = detectability_enum.value if detectability_enum else None
    state["overall_risk"] = overall_risk.value
    state["urgency_recommendation"] = urgency.value

    return state


def complete_risk_assessment_node(state: RiskAssessmentWorkflowState) -> RiskAssessmentWorkflowState:
    """Finalizes completed risk assessment."""
    state["status"] = RiskAssessmentStatus.COMPLETED.value
    return state


def handle_risk_failure_node(state: RiskAssessmentWorkflowState) -> RiskAssessmentWorkflowState:
    """Fallback handler on fatal node failure. Sets safe, conservative defaults."""
    default_dim = {
        "status": "Impact cannot currently be determined",
        "findings": "Assessment could not be completed due to workflow processing failure.",
        "supporting_references": [],
        "concerns": ["AI evaluation failed or encountered unrecoverable error"],
        "is_unverified": True,
    }

    state["status"] = RiskAssessmentStatus.FAILED.value
    if not state.get("quality_impact"):
        state["quality_impact"] = default_dim
    if not state.get("patient_impact"):
        state["patient_impact"] = default_dim
    if not state.get("batch_impact"):
        state["batch_impact"] = default_dim
    if not state.get("process_impact"):
        state["process_impact"] = default_dim
    if not state.get("equipment_impact"):
        state["equipment_impact"] = default_dim
    if not state.get("data_integrity_impact"):
        state["data_integrity_impact"] = default_dim

    state["severity"] = RiskClassification.UNDETERMINED.value
    state["likelihood"] = RiskLikelihood.UNDETERMINED.value
    state["overall_risk"] = RiskClassification.UNDETERMINED.value
    state["urgency_recommendation"] = InvestigationUrgency.INFO_REQUIRED.value
    state["risk_rationale"] = "Automated quality risk evaluation failed. Manual investigation required."
    state["confidence_score"] = 0.0

    return state
