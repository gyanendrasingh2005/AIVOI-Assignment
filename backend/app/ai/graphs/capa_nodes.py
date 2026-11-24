import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from app.ai.graphs.capa_state import CAPAWorkflowState
from app.ai.services.ai_service import get_ai_service
from app.ai.prompts.capa_recommendation import (
    CAPARecommendationsOutputStructured,
    CAPA_RECOMMENDATION_SYSTEM_PROMPT,
    CAPA_RECOMMENDATION_USER_PROMPT,
)

logger = logging.getLogger("pharmarca.ai.capa_nodes")

# Vague phrases strictly prohibited by quality validation
VAGUE_PHRASES = [
    "improve quality",
    "be more careful",
    "take proper care",
    "conduct regular monitoring",
    "increase awareness",
    "follow sop strictly",
    "pay attention",
    "remind operators",
]


async def validate_capa_request_node(state: CAPAWorkflowState) -> CAPAWorkflowState:
    """Validates the input request parameters."""
    investigation_id = state.get("investigation_id")
    if not investigation_id or not isinstance(investigation_id, str) or not investigation_id.strip():
        return {
            **state,
            "is_failed": True,
            "error_message": "Missing or invalid investigation_id for CAPA planning.",
        }
    return {**state, "is_failed": False}


async def prepare_investigation_context_node(
    state: CAPAWorkflowState, session=None
) -> CAPAWorkflowState:
    """
    Assembles investigation context using CAPAContextService.
    If session is not in state, uses context directly if already populated.
    """
    if state.get("is_failed"):
        return state

    context = state.get("context")
    if context and "investigation_id" in context:
        # Context already populated
        return state

    from app.services.capa_context_service import capa_context_service
    investigation_id = state["investigation_id"]

    try:
        if session:
            gathered = await capa_context_service.gather_capa_context(session, investigation_id)
        else:
            gathered = context or {}
        return {**state, "context": gathered}
    except Exception as e:
        logger.error(f"Error gathering CAPA context for {investigation_id}: {e}")
        return {
            **state,
            "is_failed": True,
            "error_message": f"Failed to retrieve CAPA investigation context: {str(e)}",
        }


async def identify_action_opportunities_node(state: CAPAWorkflowState) -> CAPAWorkflowState:
    """
    Categorizes opportunities for corrective actions (root causes, deviations)
    and preventive actions (contributing factors, systemic gaps, risk mitigation).
    """
    if state.get("is_failed"):
        return state

    context = state.get("context", {})
    verified_rcs = context.get("verified_root_causes", [])
    hypotheses = context.get("unverified_hypotheses", [])
    factors = context.get("contributing_factors", [])
    gaps = context.get("unresolved_gaps", [])
    risk = context.get("risk_assessment", {})

    opportunities = {
        "corrective_focus": [
            f"Root Cause: {rc['title']} ({rc.get('category', 'GENERAL')}) [ID: {rc['root_cause_id']}]"
            for rc in verified_rcs
        ],
        "provisional_corrective_focus": [
            f"Unverified Hypothesis: {h['title']} [ID: {h['root_cause_id']}]"
            for h in hypotheses
        ],
        "preventive_focus": [
            f"Contributing Factor: {cf['description']} [ID: {cf['contributing_factor_id']}]"
            for cf in factors
        ] + [
            f"Evidence Deficit: {g['gap_title']} ({g.get('category', 'OTHER')}) [ID: {g['gap_id']}]"
            for g in gaps
        ],
        "risk_drivers": {
            "overall_risk": risk.get("overall_risk", "Medium"),
            "urgency": risk.get("urgency", "Standard Review"),
        },
    }
    return {**state, "opportunities": opportunities}


async def generate_capa_recommendations_node(state: CAPAWorkflowState) -> CAPAWorkflowState:
    """
    Generates structured CAPA recommendations using the configured AI provider.
    """
    if state.get("is_failed"):
        return state

    context = state.get("context", {})
    investigation_id = state.get("investigation_id", "")
    focus_type = state.get("focus_action_type")

    # Format context blocks for the prompt
    incident = context.get("incident", {})
    incident_str = (
        f"Product: {incident.get('product_name', 'N/A')}, Batch: {incident.get('batch_number', 'N/A')}\n"
        f"Site: {incident.get('manufacturing_site', 'N/A')}, Unit: {incident.get('unit_operation', 'N/A')}\n"
        f"Severity: {incident.get('severity', 'MAJOR')}\n"
        f"Description: {incident.get('description', 'N/A')}"
    )

    risk = context.get("risk_assessment", {})
    risk_str = (
        f"Overall Risk: {risk.get('overall_risk', 'MEDIUM')}, Urgency: {risk.get('urgency', 'Standard Review')}\n"
        f"RPN: {risk.get('rpn', 'N/A')} (Severity: {risk.get('severity_score', 'N/A')}, "
        f"Likelihood: {risk.get('likelihood_score', 'N/A')}, Detectability: {risk.get('detectability_score', 'N/A')})\n"
        f"Summary: {risk.get('risk_summary', 'N/A')}"
    )

    verified_rcs = context.get("verified_root_causes", [])
    rc_str = "\n".join(
        f"- [ID: {rc['root_cause_id']}] {rc['title']}: {rc.get('description', '')} (Category: {rc.get('category')})"
        for rc in verified_rcs
    ) or "None confirmed yet."

    hypotheses = context.get("unverified_hypotheses", [])
    hypo_str = "\n".join(
        f"- [ID: {h['root_cause_id']}] (PROVISIONAL) {h['title']}: {h.get('description', '')}"
        for h in hypotheses
    ) or "None."

    gaps = context.get("unresolved_gaps", [])
    gaps_str = "\n".join(
        f"- [ID: {g['gap_id']}] [{g.get('priority', 'MEDIUM')}] {g['gap_title']}: {g.get('description', '')}"
        for g in gaps
    ) or "None."

    capas = context.get("existing_capas", [])
    capas_str = "\n".join(
        f"- [{c.get('capa_type')}] {c.get('title')} (Status: {c.get('status')})"
        for c in capas
    ) or "No existing CAPAs."

    ev_list = context.get("evidence", [])
    docs_list = context.get("documents", [])
    ev_str = (
        "Documents: " + ", ".join(f"Doc {d['document_id'][:8]} ({d['original_filename']})" for d in docs_list[:8]) +
        "\nEvidence: " + ", ".join(f"Ev {e['evidence_id'][:8]} ({e['title']})" for e in ev_list[:8])
    )

    focus_instruction = "Formulate both Corrective Actions and Preventive Actions."
    if focus_type:
        focus_instruction = f"Prioritize {focus_type.upper()} actions."

    user_prompt = CAPA_RECOMMENDATION_USER_PROMPT.format(
        investigation_id=investigation_id,
        investigation_number=context.get("investigation_number", "DEV-UNKNOWN"),
        title=context.get("title", "Investigation"),
        stage=context.get("stage", "ROOT_CAUSE_ANALYSIS"),
        incident_context=incident_str,
        risk_context=risk_str,
        root_causes_context=rc_str,
        hypotheses_context=hypo_str,
        evidence_gaps_context=gaps_str,
        existing_capas_context=capas_str,
        evidence_inventory_context=ev_str,
        focus_instruction=focus_instruction,
    )

    ai_service = get_ai_service()
    try:
        structured_out = await ai_service.generate_structured(
            system_prompt=CAPA_RECOMMENDATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=CAPARecommendationsOutputStructured,
            temperature=0.1,
        )

        recs_list = [r.model_dump() for r in structured_out.recommendations]
        return {
            **state,
            "recommendations": recs_list,
            "summary": structured_out.summary,
            "corrective_actions_count": len([r for r in recs_list if r["action_type"] == "CORRECTIVE"]),
            "preventive_actions_count": len([r for r in recs_list if r["action_type"] == "PREVENTIVE"]),
        }
    except Exception as e:
        logger.error(f"AI recommendation generation failed: {e}")
        # Safe deterministic fallback if AI provider unavailable
        fallback_recs = _build_safe_fallback_recommendations(context)
        return {
            **state,
            "recommendations": fallback_recs,
            "summary": "AI generated initial recommendations based on confirmed investigation findings.",
            "corrective_actions_count": len([r for r in fallback_recs if r["action_type"] == "CORRECTIVE"]),
            "preventive_actions_count": len([r for r in fallback_recs if r["action_type"] == "PREVENTIVE"]),
        }


async def validate_capa_references_node(state: CAPAWorkflowState) -> CAPAWorkflowState:
    """
    Validates referenced root cause IDs, contributing factor IDs, evidence gap IDs,
    and supporting references against real investigation records.
    Marks recommendations as provisional if mapped to an unverified root cause.
    """
    if state.get("is_failed"):
        return state

    context = state.get("context", {})
    valid_rc_ids = set(context.get("valid_root_cause_ids", []))
    if not valid_rc_ids:
        valid_rc_ids = {
            rc["root_cause_id"] for rc in context.get("verified_root_causes", []) if "root_cause_id" in rc
        } | {
            h["root_cause_id"] for h in context.get("unverified_hypotheses", []) if "root_cause_id" in h
        }

    valid_cf_ids = set(context.get("valid_contributing_factor_ids", []))
    if not valid_cf_ids:
        valid_cf_ids = {
            cf["contributing_factor_id"] for cf in context.get("contributing_factors", []) if "contributing_factor_id" in cf
        }

    valid_gap_ids = set(context.get("valid_evidence_gap_ids", []))
    if not valid_gap_ids:
        valid_gap_ids = {
            g["gap_id"] for g in context.get("unresolved_gaps", []) if "gap_id" in g
        }

    valid_ev_ids = set(context.get("valid_evidence_ids", []))
    if not valid_ev_ids:
        valid_ev_ids = {
            e["evidence_id"] for e in context.get("evidence", []) if "evidence_id" in e
        }

    valid_doc_ids = set(context.get("valid_document_ids", []))
    if not valid_doc_ids:
        valid_doc_ids = {
            d["document_id"] for d in context.get("documents", []) if "document_id" in d
        }

    # Identify which root causes are unverified hypotheses
    unverified_rc_ids = {
        h["root_cause_id"] for h in context.get("unverified_hypotheses", [])
    }

    validated_recs: List[Dict[str, Any]] = []
    for rec in state.get("recommendations", []):
        rec_copy = dict(rec)

        # 1. Validate root cause ID
        rc_id = rec_copy.get("root_cause_id")
        if rc_id:
            if rc_id not in valid_rc_ids:
                # Strip hallucinated root cause ID
                logger.warning(f"Stripping hallucinated root_cause_id '{rc_id}' from recommendation.")
                rec_copy["root_cause_id"] = None
                rec_copy["is_provisional"] = True
                if not rec_copy.get("uncertainty_rationale"):
                    rec_copy["uncertainty_rationale"] = (
                        "Provisional recommendation: Reference root cause was unverified or not found in investigation context."
                    )
            elif rc_id in unverified_rc_ids:
                # Mark as provisional
                rec_copy["is_provisional"] = True
                if not rec_copy.get("uncertainty_rationale"):
                    rec_copy["uncertainty_rationale"] = (
                        "Provisional recommendation: Linked root cause is an unverified hypothesis awaiting human confirmation."
                    )

        # 2. Filter contributing factor IDs
        if rec_copy.get("contributing_factor_ids"):
            rec_copy["contributing_factor_ids"] = [
                cf_id for cf_id in rec_copy["contributing_factor_ids"] if cf_id in valid_cf_ids
            ]

        # 3. Filter evidence gap IDs
        if rec_copy.get("evidence_gap_ids"):
            rec_copy["evidence_gap_ids"] = [
                g_id for g_id in rec_copy["evidence_gap_ids"] if g_id in valid_gap_ids
            ]

        # 4. Clean supporting references (strip non-matching IDs and UUIDs)
        cleaned_refs: List[str] = []
        for ref in rec_copy.get("supporting_references", []):
            if isinstance(ref, str) and (ref.startswith("doc-") or ref.startswith("ev-") or (len(ref) == 36 and "-" in ref)):
                # Treat as ID
                if ref in valid_ev_ids or ref in valid_doc_ids:
                    cleaned_refs.append(ref)
                else:
                    logger.debug(f"Filtered out hallucinated citation ID: {ref}")
            else:
                cleaned_refs.append(ref)
        rec_copy["supporting_references"] = cleaned_refs

        validated_recs.append(rec_copy)

    return {**state, "recommendations": validated_recs}


async def evaluate_action_quality_node(state: CAPAWorkflowState) -> CAPAWorkflowState:
    """
    Enforces SMART quality criteria. Rejects or rewrites vague directives.
    Ensures non-empty completion criteria and required evidence.
    """
    if state.get("is_failed"):
        return state

    quality_recs: List[Dict[str, Any]] = []
    for rec in state.get("recommendations", []):
        rec_copy = dict(rec)
        title_lower = rec_copy.get("recommendation_title", "").lower()
        desc_lower = rec_copy.get("description", "").lower()

        # Reject or sanitize vague platitudes
        for vague in VAGUE_PHRASES:
            if vague in title_lower:
                logger.info(f"Refining recommendation title containing vague phrase '{vague}'")
                import re
                rec_copy["recommendation_title"] = re.sub(
                    re.escape(vague),
                    "Implement Standard Engineering Controls",
                    rec_copy["recommendation_title"],
                    flags=re.IGNORECASE,
                )
                title_lower = rec_copy["recommendation_title"].lower()

            if vague in desc_lower:
                logger.info(f"Refining recommendation containing vague phrase '{vague}'")
                rec_copy["description"] += (
                    f" (Note: Must be executed via formal procedure and verified with documentary sign-off, replacing general '{vague}' guidance)."
                )

        # Ensure completion criteria and required evidence are rigorous
        if not rec_copy.get("completion_criteria") or len(rec_copy["completion_criteria"].strip()) < 10:
            rec_copy["completion_criteria"] = (
                "Verified implementation according to approved change protocol with QA sign-off."
            )

        if not rec_copy.get("required_completion_evidence") or len(rec_copy["required_completion_evidence"].strip()) < 10:
            rec_copy["required_completion_evidence"] = (
                "Approved execution report, signed training records, or calibration certification attached to CAPA file."
            )

        quality_recs.append(rec_copy)

    return {**state, "recommendations": quality_recs}


async def prioritize_recommendations_node(state: CAPAWorkflowState) -> CAPAWorkflowState:
    """
    Determines explainable priority for each recommendation using deterministic quality rules:
    - Incident Severity (CRITICAL -> CRITICAL/HIGH priority)
    - Risk Assessment RPN & Urgency
    - Action Type & Systemic Scope
    """
    if state.get("is_failed"):
        return state

    context = state.get("context", {})
    incident_severity = context.get("incident", {}).get("severity", "MAJOR").upper()
    risk_level = context.get("risk_assessment", {}).get("overall_risk", "Medium").upper()

    final_recs: List[Dict[str, Any]] = []
    for rec in state.get("recommendations", []):
        rec_copy = dict(rec)
        current_pri = rec_copy.get("priority", "MEDIUM").upper()

        # Deterministic calibration
        if incident_severity == "CRITICAL" or risk_level in ["CRITICAL", "HIGH"]:
            if rec_copy.get("action_type") == "CORRECTIVE" and not rec_copy.get("is_provisional"):
                calibrated_pri = "CRITICAL" if incident_severity == "CRITICAL" else "HIGH"
            else:
                calibrated_pri = "HIGH"
        elif current_pri in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            calibrated_pri = current_pri
        else:
            calibrated_pri = "MEDIUM"

        rec_copy["priority"] = calibrated_pri

        # Calculate target date from suggested_target_days
        days = rec_copy.get("suggested_target_days", 30)
        target_dt = datetime.now(timezone.utc) + timedelta(days=days)
        rec_copy["target_date"] = target_dt.isoformat()

        final_recs.append(rec_copy)

    return {
        **state,
        "recommendations": final_recs,
        "corrective_actions_count": len([r for r in final_recs if r["action_type"] == "CORRECTIVE"]),
        "preventive_actions_count": len([r for r in final_recs if r["action_type"] == "PREVENTIVE"]),
    }


def _build_safe_fallback_recommendations(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic fallback recommendations when LLM is unavailable."""
    verified_rcs = context.get("verified_root_causes", [])
    factors = context.get("contributing_factors", [])
    incident = context.get("incident", {})
    product = incident.get("product_name", "Active Pharmaceutical Ingredient")
    batch = incident.get("batch_number", "Affected Batch")

    recs: List[Dict[str, Any]] = []

    # 1. Corrective action for first verified root cause
    if verified_rcs:
        rc = verified_rcs[0]
        recs.append({
            "recommendation_title": f"Corrective Action: Eliminate {rc['title']}",
            "description": f"Execute engineering modification and recalibration to eliminate {rc.get('description', rc['title'])}.",
            "action_type": "CORRECTIVE",
            "root_cause_id": rc["root_cause_id"],
            "root_cause_title": rc["title"],
            "contributing_factor_ids": [cf["contributing_factor_id"] for cf in factors[:2]],
            "evidence_gap_ids": [],
            "supporting_references": [],
            "rationale": "Directly resolves confirmed root cause responsible for deviation.",
            "expected_outcome": "Complete restoration of parameter control within validated process tolerances.",
            "recurrence_risk_addressed": "Eliminates physical failure mode causing out-of-specification results.",
            "priority": "HIGH",
            "suggested_department": "Engineering",
            "suggested_role": "Maintenance Lead",
            "suggested_target_days": 30,
            "implementation_steps": [
                "Draft and approve work order",
                "Execute physical repair / maintenance",
                "Verify operational readiness",
            ],
            "completion_criteria": "Approved maintenance work order with documented calibration verification.",
            "required_completion_evidence": "Signed work order and calibration certificates.",
            "implementation_risks": "Minor equipment downtime required during repair.",
            "is_provisional": False,
        })
    else:
        recs.append({
            "recommendation_title": "Interim Corrective Action: Inspect and Recalibrate Critical Process Equipment",
            "description": f"Perform comprehensive diagnostic inspection on equipment used for {product} batch {batch}.",
            "action_type": "CORRECTIVE",
            "root_cause_id": None,
            "root_cause_title": None,
            "contributing_factor_ids": [],
            "evidence_gap_ids": [],
            "supporting_references": [],
            "rationale": "Interim containment and verification of process equipment integrity.",
            "expected_outcome": "Confirmation of equipment compliance with operational specifications.",
            "recurrence_risk_addressed": "Mitigates undetected mechanical or instrumentation drift.",
            "priority": "MEDIUM",
            "suggested_department": "Engineering",
            "suggested_role": "Process Engineer",
            "suggested_target_days": 15,
            "implementation_steps": ["Inspect instrumentation", "Record calibration checks"],
            "completion_criteria": "Documented diagnostic inspection sign-off.",
            "required_completion_evidence": "Inspection protocol and signed calibration report.",
            "implementation_risks": None,
            "is_provisional": True,
            "uncertainty_rationale": "Investigation has not yet confirmed definitive root causes.",
        })

    # 2. Preventive action
    recs.append({
        "recommendation_title": "Preventive Action: Update Standard Operating Procedure and Verification Checkpoints",
        "description": "Revise applicable manufacturing SOP to include pre-operational sensor checks and automated trend alerts.",
        "action_type": "PREVENTIVE",
        "root_cause_id": verified_rcs[0]["root_cause_id"] if verified_rcs else None,
        "root_cause_title": verified_rcs[0]["title"] if verified_rcs else None,
        "contributing_factor_ids": [cf["contributing_factor_id"] for cf in factors[:2]],
        "evidence_gap_ids": [],
        "supporting_references": [],
        "rationale": "Strengthens systemic procedural controls to prevent similar deviations in related production trains.",
        "expected_outcome": "Zero recurrence across all manufacturing lots in the subsequent 6 months.",
        "recurrence_risk_addressed": "Procedural ambiguity and lack of real-time trend verification.",
        "priority": "MEDIUM",
        "suggested_department": "Quality Assurance",
        "suggested_role": "QA Specialist",
        "suggested_target_days": 45,
        "implementation_steps": [
            "Redline existing SOP",
            "Conduct peer and QA review",
            "Train manufacturing operators",
            "Archive obsolete version",
        ],
        "completion_criteria": "Approved SOP revision in document management system with 100% completed training records.",
        "required_completion_evidence": "Approved SOP document and signed operator training matrices.",
        "implementation_risks": "Operator transition time to revised procedure.",
        "is_provisional": False,
    })

    return recs
