"""
LangGraph execution nodes for AI-assisted Root Cause Analysis (5 Whys + Fishbone).
Handles prompt context preparation, model execution, causal chain validation,
source citation verification, and 6M categorization.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable

from app.models.enums import (
    RCAStatus,
    CauseStatus,
    CauseClassification,
    Fishbone6MCategory,
)
from app.ai.providers.base import BaseAIProvider
from app.ai.prompts.base import get_system_prompt
from app.ai.graphs.rca_state import RCAWorkflowState
from app.schemas.rca import (
    RCAStructuredOutput,
    WhyStepItem,
    FishboneCauseItem,
    RootCauseItem,
    ContributingFactorItem,
    RCAEvidenceGapItem,
    RCAEvidenceReference,
)

logger = logging.getLogger(__name__)

STANDARD_6M_CATEGORIES = [
    Fishbone6MCategory.MANPOWER.value,
    Fishbone6MCategory.MACHINE.value,
    Fishbone6MCategory.METHOD.value,
    Fishbone6MCategory.MATERIAL.value,
    Fishbone6MCategory.MEASUREMENT.value,
    Fishbone6MCategory.ENVIRONMENT.value,
]


def validate_rca_request_node(state: RCAWorkflowState) -> RCAWorkflowState:
    """Validates required investigation inputs for RCA."""
    errors = list(state.get("errors", []))

    if not state.get("investigation_id"):
        errors.append("Missing required investigation_id in RCA workflow state.")

    snapshot = state.get("incident_snapshot", {})
    if not snapshot or not (snapshot.get("api_product_name") or snapshot.get("incident_description")):
        errors.append("Missing incident details or intake data required for causal analysis.")

    if errors:
        state["errors"] = errors
        state["status"] = "FAILED"
        return state

    state["errors"] = []
    state["status"] = "PROCESSING"
    return state


def prepare_rca_context_node(state: RCAWorkflowState) -> RCAWorkflowState:
    """Assembles the versioned system prompt and structured human prompt."""
    if state.get("status") == "FAILED":
        return state

    prompt_version = state.get("prompt_version", "1.0.0")
    system_prompt = get_system_prompt("rca", prompt_version)
    state["system_prompt"] = system_prompt

    context_text = state.get("compiled_prompt_context", "")
    instructions = state.get("additional_focus")

    lines = [context_text]

    if instructions:
        lines.append(f"\n## Investigator Focus Instructions:\n{instructions}")

    lines.append("\n\n## RCA EXECUTION TASK:")
    lines.append("1. Formulate a precise, objective Initial Problem Statement.")
    lines.append("2. Perform an evidence-grounded 5 Whys analysis moving sequentially from the observed symptom to underlying root causes.")
    lines.append("   - Do NOT force 5 steps if root cause is reached earlier.")
    lines.append("   - Ensure every Why logically explains the preceding answer.")
    lines.append("   - Strictly avoid circular reasoning, repeated statements, or unsupported leaps.")
    lines.append("3. Perform a Fishbone (Ishikawa) analysis across the 6 standard categories: Manpower / People, Machine / Equipment, Method / Process, Material, Measurement, Environment.")
    lines.append("4. Clearly distinguish Root Causes from Contributing Factors and Possible Causes.")
    lines.append("5. Ground every finding with empirical citations (document_id, evidence_id, filename, page_number, excerpt).")
    lines.append("6. Explicitly identify unsupported assumptions and evidence gaps.")
    lines.append("7. Return strictly valid JSON conforming to RCAStructuredOutput schema.")

    state["user_prompt"] = "\n".join(lines)
    return state


def make_generate_rca_node(
    provider: BaseAIProvider,
) -> Callable[[RCAWorkflowState], Awaitable[RCAWorkflowState]]:
    """Factory creating the async LLM execution node for structured RCA generation."""

    async def generate_rca_node(state: RCAWorkflowState) -> RCAWorkflowState:
        if state.get("status") == "FAILED":
            return state

        system_prompt = state.get("system_prompt", "")
        user_prompt = state.get("user_prompt", "")
        start_time = time.time()

        try:
            result = await provider.generate_structured(
                prompt=user_prompt,
                response_model=RCAStructuredOutput,
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
                data: RCAStructuredOutput = result.data
                state["problem_statement"] = data.problem_statement
                state["incident_summary"] = data.incident_summary
                state["five_whys"] = [w.model_dump() for w in data.five_whys]
                state["fishbone_causes"] = [c.model_dump() for c in data.fishbone_causes]
                state["potential_root_causes"] = [r.model_dump() for r in data.potential_root_causes]
                state["contributing_factors"] = [f.model_dump() for f in data.contributing_factors]
                state["rejected_hypotheses"] = [rh.model_dump() for rh in data.rejected_hypotheses]
                state["evidence_gaps"] = [g.model_dump() for g in data.evidence_gaps]
                state["causal_chain_critique"] = data.causal_chain_critique
                state["unsupported_assumptions"] = data.unsupported_assumptions
            else:
                errors = list(state.get("errors", []))
                err_msg = result.validation_error or "Structured RCA output parsing failed."
                errors.append(err_msg)
                state["errors"] = errors
                state["status"] = "FAILED"

        except Exception as exc:
            logger.error("Error during AI RCA generation: %s", exc, exc_info=True)
            latency_ms = int((time.time() - start_time) * 1000)
            errors = list(state.get("errors", []))
            errors.append(f"AI RCA execution failed: {str(exc)}")
            state["errors"] = errors
            state["status"] = "FAILED"
            state["latency_ms"] = latency_ms

        return state

    return generate_rca_node


def validate_causal_chain_node(state: RCAWorkflowState) -> RCAWorkflowState:
    """
    Validates logical consistency of 5 Whys steps.
    Identifies:
    - Circular reasoning
    - Repeated statements / paraphrasing
    - Unsupported causal leaps
    - Restating the question
    """
    if state.get("status") == "FAILED":
        return state

    five_whys = list(state.get("five_whys", []))
    unsupported_assumptions = list(state.get("unsupported_assumptions", []))
    critiques = []

    seen_answers = set()

    for idx, step in enumerate(five_whys):
        q = (step.get("question") or "").strip().lower()
        ans = (step.get("answer") or "").strip().lower()
        step_num = step.get("step_number", idx + 1)

        # 1. Check for circular reasoning or restatement
        if ans and (ans in seen_answers or ans == q or (idx > 0 and ans in (five_whys[idx - 1].get("question") or "").lower())):
            step["reasoning_critique"] = "Potential circular reasoning or duplicate statement detected."
            step["verification_status"] = CauseStatus.NEEDS_EVIDENCE.value
            critiques.append(f"Step {step_num}: Circular reasoning or repeated statement observed.")
        seen_answers.add(ans)

        # 2. Check for unsupported leaps (0 references and non-trivial claim)
        refs = step.get("supporting_references", [])
        if not refs:
            step["causal_leap_detected"] = True
            assumption_msg = f"Step {step_num} assertion ('{step.get('answer')[:80]}...') lacks empirical document citations."
            if assumption_msg not in unsupported_assumptions:
                unsupported_assumptions.append(assumption_msg)

    if critiques:
        existing_critique = state.get("causal_chain_critique") or ""
        state["causal_chain_critique"] = (existing_critique + " " + "; ".join(critiques)).strip()

    state["five_whys"] = five_whys
    state["unsupported_assumptions"] = unsupported_assumptions
    return state


def validate_rca_citations_node(state: RCAWorkflowState) -> RCAWorkflowState:
    """
    Validates empirical citations against database document IDs and evidence IDs.
    Strips hallucinated IDs and flags unverified citations.
    """
    if state.get("status") == "FAILED":
        return state

    valid_doc_map = state.get("valid_document_map", {})
    valid_ev_map = state.get("valid_evidence_map", {})

    def _clean_references(refs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cleaned = []
        for r in refs:
            rd = dict(r)
            doc_id = rd.get("document_id")
            ev_id = rd.get("evidence_id")

            # Check document ID
            if doc_id:
                if doc_id not in valid_doc_map:
                    rd["document_id"] = None
                    rd["relevance_reason"] = f"(Unverified Citation) {rd.get('relevance_reason', '')}".strip()
                else:
                    rd["filename"] = valid_doc_map[doc_id]

            # Check evidence ID
            if ev_id and ev_id not in valid_ev_map:
                rd["evidence_id"] = None
                rd["relevance_reason"] = f"(Unverified Evidence ID) {rd.get('relevance_reason', '')}".strip()

            cleaned.append(rd)
        return cleaned

    # Clean references across all RCA sections
    for step in state.get("five_whys", []):
        step["supporting_references"] = _clean_references(step.get("supporting_references", []))

    for cause in state.get("fishbone_causes", []):
        cause["supporting_references"] = _clean_references(cause.get("supporting_references", []))

    for rc in state.get("potential_root_causes", []):
        rc["supporting_references"] = _clean_references(rc.get("supporting_references", []))

    for cf in state.get("contributing_factors", []):
        cf["supporting_references"] = _clean_references(cf.get("supporting_references", []))

    return state


def categorize_fishbone_and_causes_node(state: RCAWorkflowState) -> RCAWorkflowState:
    """
    Normalizes Fishbone causes into 6M categories and ensures root causes
    are strictly marked as unconfirmed drafts (PROPOSED).
    """
    if state.get("status") == "FAILED":
        return state

    causes = state.get("fishbone_causes", [])
    normalized_causes = []

    for cause in causes:
        c = dict(cause)
        cat = c.get("category", "").strip().lower()

        # Map to standard 6M name
        matched_cat = Fishbone6MCategory.METHOD.value
        for standard in STANDARD_6M_CATEGORIES:
            first_word = standard.split()[0].lower()
            if first_word in cat:
                matched_cat = standard
                break
        c["category"] = matched_cat

        # Ensure draft status
        if not c.get("verification_status"):
            c["verification_status"] = CauseStatus.PROPOSED.value

        normalized_causes.append(c)

    state["fishbone_causes"] = normalized_causes

    # Ensure root causes are marked unconfirmed
    root_causes = state.get("potential_root_causes", [])
    for rc in root_causes:
        rc["human_confirmed"] = False
        rc["verification_status"] = CauseStatus.PROPOSED.value

    state["potential_root_causes"] = root_causes
    return state


def complete_rca_node(state: RCAWorkflowState) -> RCAWorkflowState:
    """Finalizes completed RCA analysis."""
    state["status"] = RCAStatus.AI_ANALYSIS_COMPLETED.value
    return state


def handle_rca_failure_node(state: RCAWorkflowState) -> RCAWorkflowState:
    """Fallback error handler ensuring conservative defaults upon failure."""
    state["status"] = "FAILED"
    state["problem_statement"] = state.get("problem_statement") or "Root Cause Analysis could not be completed."
    state["incident_summary"] = state.get("incident_summary") or "Automated causal evaluation failed."
    state["five_whys"] = state.get("five_whys") or []
    state["fishbone_causes"] = state.get("fishbone_causes") or []
    state["potential_root_causes"] = []
    state["contributing_factors"] = []
    state["rejected_hypotheses"] = []
    state["evidence_gaps"] = state.get("evidence_gaps") or [
        {
            "gap_id": "gap-err-1",
            "description": "Automated workflow failure; manual root cause investigation required.",
            "reason": "AI orchestration encountered an unrecoverable error.",
            "priority": "High",
            "suggested_source": "Quality Investigation Team",
        }
    ]
    state["unsupported_assumptions"] = state.get("unsupported_assumptions") or []
    return state

