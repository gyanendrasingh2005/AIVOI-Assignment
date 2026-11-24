"""
LangGraph Evidence Gap Assessment Workflow Nodes
=================================================
Independent, testable nodes orchestrating evidence gap detection and completeness scoring.
"""

from typing import Dict, Any, List
from app.ai.graphs.gap_state import GapAssessmentWorkflowState
from app.ai.prompts.gap_assessment import (
    GAP_ASSESSMENT_SYSTEM_PROMPT,
    build_gap_assessment_user_prompt,
    GapAssessmentStructuredOutput,
)
from app.ai.services.ai_service import get_ai_service
from app.services.gap_context_service import gap_context_service
from app.services.evidence_requirement_service import evidence_requirement_service
from app.models.enums import CompletenessDimensionStatus, CompletenessOverallStatus, EvidenceGapPriority, GapCategory


MANDATORY_11_DIMENSIONS = [
    "Incident information",
    "Document availability",
    "Evidence traceability",
    "Manufacturing process evidence",
    "Equipment evidence",
    "Material and batch evidence",
    "Quality impact assessment",
    "5 Whys completeness",
    "Fishbone completeness",
    "Root cause verification",
    "Investigation review completeness",
]


async def validate_gap_request_node(state: GapAssessmentWorkflowState) -> Dict[str, Any]:
    """Validates that a valid investigation ID is supplied."""
    inv_id = state.get("investigation_id")
    if not inv_id or not str(inv_id).strip():
        return {
            "is_failed": True,
            "error_message": "investigation_id is required for evidence gap assessment.",
        }
    return {
        "is_failed": False,
        "requirement_profile_version": state.get("requirement_profile_version") or "1.0.0",
    }


async def prepare_gap_context_node(
    state: GapAssessmentWorkflowState, session=None
) -> Dict[str, Any]:
    """Retrieves authoritative context for the active investigation."""
    if state.get("is_failed"):
        return {}

    inv_id = state["investigation_id"]
    try:
        # Context preparation service expects active session
        if session is not None:
            ctx = await gap_context_service.prepare_investigation_gap_context(
                session, inv_id, state.get("user_id")
            )
        else:
            ctx = state.get("context_data") or {}

        compiled_context = ctx.get("compiled_prompt_context", "")
        return {
            "context_data": ctx,
            "compiled_prompt_context": compiled_context,
        }
    except Exception as e:
        return {
            "is_failed": True,
            "error_message": f"Failed to retrieve investigation context: {str(e)}",
        }


async def load_requirement_profile_node(state: GapAssessmentWorkflowState) -> Dict[str, Any]:
    """Loads and filters applicable evidence requirement profile rules."""
    if state.get("is_failed"):
        return {}

    profile_ver = state.get("requirement_profile_version", "1.0.0")
    ctx = state.get("context_data", {})

    applicable_rules = evidence_requirement_service.evaluate_applicable_rules(ctx, profile_ver)
    rules_dicts = []
    lines = []
    for r in applicable_rules:
        rules_dicts.append({
            "code": r.code,
            "name": r.name,
            "category": r.category,
            "dimension": r.dimension,
            "description": r.description,
            "default_priority": r.default_priority,
            "recommended_evidence_type": r.recommended_evidence_type,
            "recommended_action": r.recommended_action,
        })
        lines.append(f"- [{r.code}] {r.name} ({r.category}): {r.description} -> Expected Action: {r.recommended_action}")

    return {
        "applicable_rules": rules_dicts,
        "compiled_rules_text": "\n".join(lines),
    }


async def execute_gap_and_completeness_ai_node(state: GapAssessmentWorkflowState) -> Dict[str, Any]:
    """Invokes LLM provider with structured output schema for evidence gap detection."""
    if state.get("is_failed"):
        return {}

    ai_svc = get_ai_service()
    provider = ai_svc.get_provider()

    user_prompt = build_gap_assessment_user_prompt(
        context_text=state.get("compiled_prompt_context", ""),
        rules_text=state.get("compiled_rules_text", ""),
    )

    try:
        result = await provider.generate_structured(
            prompt=user_prompt,
            response_model=GapAssessmentStructuredOutput,
            system_prompt=GAP_ASSESSMENT_SYSTEM_PROMPT,
            temperature=0.1,
        )

        if not result.parsed_successfully or not result.data:
            err = result.validation_error or "Structured gap assessment output parsing failed."
            return {"is_failed": True, "error_message": err}

        response_model: GapAssessmentStructuredOutput = result.data
        output_dict = response_model.model_dump()

        # Validate that all 11 mandatory dimensions are present
        existing_dims = {d["dimension_name"]: d for d in output_dict.get("dimensions", [])}
        complete_dimensions = []
        for dim_name in MANDATORY_11_DIMENSIONS:
            if dim_name in existing_dims:
                complete_dimensions.append(existing_dims[dim_name])
            else:
                complete_dimensions.append({
                    "dimension_name": dim_name,
                    "status": CompletenessDimensionStatus.UNDETERMINED.value,
                    "explanation": f"Automated evaluation for {dim_name} was not returned by model.",
                    "missing_information": [],
                    "recommended_next_steps": ["Review dimension manually."],
                })

        return {
            "raw_ai_output": output_dict,
            "overall_status": output_dict.get("overall_status", CompletenessOverallStatus.UNDETERMINED.value),
            "completeness_score": float(output_dict.get("completeness_score", 50.0)),
            "summary": output_dict.get("summary", ""),
            "dimensions": complete_dimensions,
            "detected_gaps": output_dict.get("detected_gaps", []),
            "conflicting_evidence": output_dict.get("conflicting_evidence", []),
            "recommended_activities": output_dict.get("recommended_activities", []),
        }
    except Exception as e:
        return {
            "is_failed": True,
            "error_message": f"LLM execution error during gap assessment: {str(e)}",
        }


async def validate_evidence_references_node(state: GapAssessmentWorkflowState) -> Dict[str, Any]:
    """Validates document and evidence citations against verified database IDs."""
    if state.get("is_failed"):
        return {}

    ctx = state.get("context_data", {})
    valid_doc_ids = {d["document_id"] for d in ctx.get("documents", [])}
    valid_ev_ids = {ev["evidence_id"] for ev in ctx.get("evidence", [])}

    validated_gaps = []
    for gap in state.get("detected_gaps", []):
        cleaned_refs = []
        for ref in gap.get("supporting_references", []):
            doc_id = ref.get("document_id")
            ev_id = ref.get("evidence_id")

            # Check validity
            doc_valid = doc_id is None or doc_id in valid_doc_ids
            ev_valid = ev_id is None or ev_id in valid_ev_ids

            if not doc_valid or not ev_valid:
                # Flag unverified citation rather than dropping
                ref["relevance_reason"] = f"(Unverified Citation) {ref.get('relevance_reason', '')}".strip()
                ref["document_id"] = None
                ref["evidence_id"] = None

            cleaned_refs.append(ref)

        gap["supporting_references"] = cleaned_refs
        validated_gaps.append(gap)

    return {"validated_gaps": validated_gaps}


async def prioritize_and_consolidate_gaps_node(state: GapAssessmentWorkflowState) -> Dict[str, Any]:
    """
    Consolidates gaps, attaches related RCA causes if matched, and validates priority.
    """
    if state.get("is_failed"):
        return {}

    ctx = state.get("context_data", {})
    rca = ctx.get("rca", {})
    root_causes = rca.get("root_causes", [])

    consolidated = []
    for gap in state.get("validated_gaps", []):
        # Match root cause ID if title matches
        matched_rc_id = None
        for rc in root_causes:
            if rc.get("title", "").lower() in gap.get("description", "").lower():
                matched_rc_id = rc.get("id")
                break

        gap["root_cause_id"] = matched_rc_id

        # Normalize priority & category
        p = gap.get("priority", "MEDIUM").upper()
        if p not in EvidenceGapPriority.__members__:
            p = EvidenceGapPriority.MEDIUM.value
        gap["priority"] = p

        cat = gap.get("category", "OTHER").upper().replace(" ", "_")
        if cat not in GapCategory.__members__:
            cat = GapCategory.OTHER.value
        gap["category"] = cat

        consolidated.append(gap)

    return {"validated_gaps": consolidated}


async def calculate_completeness_node(state: GapAssessmentWorkflowState) -> Dict[str, Any]:
    """
    Tallies unresolved gaps, conflict counts, unverified causal claims,
    and calculates calibrated completeness metrics.
    """
    if state.get("is_failed"):
        return {}

    gaps = state.get("validated_gaps", [])
    conflicts = state.get("conflicting_evidence", [])
    ctx = state.get("context_data", {})
    rca = ctx.get("rca", {})
    root_causes = rca.get("root_causes", [])

    critical_count = sum(1 for g in gaps if g.get("priority") == EvidenceGapPriority.CRITICAL.value)
    high_count = sum(1 for g in gaps if g.get("priority") == EvidenceGapPriority.HIGH.value)
    total_gaps = len(gaps)
    conflicts_count = len(conflicts)

    # Unverified root causes count
    unverified_claims = sum(
        1 for rc in root_causes if rc.get("verification_status") in ["PROPOSED", "UNDER_INVESTIGATION", None]
    )

    # Calibrated score logic:
    # Starts from baseline score, penalizes critical (-20) and high (-10) gaps, conflicts (-15), unverified claims (-10)
    base_score = float(state.get("completeness_score", 85.0))
    deductions = (critical_count * 20.0) + (high_count * 10.0) + (conflicts_count * 15.0) + (unverified_claims * 10.0)
    calculated_score = max(0.0, min(100.0, base_score - deductions))

    # Determine overall status
    if critical_count > 0 or calculated_score < 50.0:
        overall_status = CompletenessOverallStatus.INCOMPLETE.value
    elif high_count > 0 or calculated_score < 85.0 or unverified_claims > 0:
        overall_status = CompletenessOverallStatus.PARTIALLY_COMPLETE.value
    else:
        overall_status = CompletenessOverallStatus.COMPLETE.value

    return {
        "completeness_score": round(calculated_score, 1),
        "overall_status": overall_status,
        "critical_unresolved_gaps": critical_count,
        "high_priority_unresolved_gaps": high_count,
        "total_unresolved_gaps": total_gaps,
        "conflicting_evidence_count": conflicts_count,
        "unverified_causal_claims_count": unverified_claims,
        "pending_reviews_count": 1 if unverified_claims > 0 else 0,
    }
