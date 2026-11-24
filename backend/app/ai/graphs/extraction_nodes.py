import json
import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable
from pydantic import ValidationError

from app.models.enums import ExtractionStatus, FieldExtractionStatus, FieldReviewDecision
from app.schemas.extraction import (
    ExtractionStructuredOutput,
    ExtractedField,
    SourceReference,
    MissingInformationItem,
    ConflictingInformationItem,
    ALLOWED_EXTRACTION_FIELDS,
)
from app.ai.graphs.extraction_state import IncidentExtractionWorkflowState
from app.ai.providers.base import BaseAIProvider
from app.ai.prompts.base import get_system_prompt
from app.ai.exceptions import sanitize_ai_error

logger = logging.getLogger(__name__)

CRITICAL_INVESTIGATION_FIELDS = [
    ("api_product_name", "Active Pharmaceutical Ingredient product identifier"),
    ("batch_number", "API batch or lot number"),
    ("manufacturing_stage", "Process stage where anomaly was observed"),
    ("incident_date", "Date of anomaly detection or occurrence"),
    ("incident_description", "Factual narrative of observed deviation"),
    ("actual_parameter_value", "Measured out-of-specification or atypical value"),
    ("potential_quality_impact", "Assessment of impact on critical quality attributes"),
]


def validate_request_node(state: IncidentExtractionWorkflowState) -> IncidentExtractionWorkflowState:
    """Validates required input parameters for the extraction run."""
    errors = list(state.get("errors", []))
    if not state.get("investigation_id"):
        errors.append("Validation failed: investigation_id is required.")
    if not state.get("document_ids"):
        errors.append("Validation failed: At least one document_id is required.")

    if errors:
        state["errors"] = errors
        state["status"] = ExtractionStatus.FAILED.value
    else:
        state["status"] = ExtractionStatus.PROCESSING.value
        state["errors"] = []

    return state


def prepare_extraction_context_node(state: IncidentExtractionWorkflowState) -> IncidentExtractionWorkflowState:
    """Prepares system instructions and structured prompt payload."""
    if state.get("status") == ExtractionStatus.FAILED.value:
        return state

    prompt_version = state.get("prompt_version", "1.0.0")
    system_prompt = get_system_prompt("incident_extraction", prompt_version)
    state["system_prompt"] = system_prompt

    doc_context = state.get("document_context", "")
    instructions = state.get("extraction_instructions") or "Perform comprehensive GMP incident extraction."

    user_prompt = (
        f"INVESTIGATION ID: {state.get('investigation_id')}\n"
        f"SPECIAL INSTRUCTIONS: {instructions}\n\n"
        f"SOURCE DOCUMENT EVIDENCE EXCERPTS:\n"
        f"{doc_context}\n\n"
        f"TASK:\n"
        f"1. Extract all factual incident information supported by the document excerpts.\n"
        f"2. Ground every extracted field with source_references (document_id, filename, page_number, excerpt).\n"
        f"3. For fields not mentioned in the source records, set value=null and status='NOT_FOUND'.\n"
        f"4. If documents report conflicting values, set status='CONFLICTING' and cite both sources.\n"
        f"5. Explicitly catalog missing critical GMP information and document conflicts.\n"
        f"6. Return ONLY valid JSON conforming to ExtractionStructuredOutput schema."
    )
    state["user_prompt"] = user_prompt
    return state


def make_extract_incident_fields_node(
    provider: BaseAIProvider,
) -> Callable[[IncidentExtractionWorkflowState], Awaitable[IncidentExtractionWorkflowState]]:
    """Invokes provider structured generation to extract incident information."""

    async def extract_incident_fields_node(state: IncidentExtractionWorkflowState) -> IncidentExtractionWorkflowState:
        if state.get("status") == ExtractionStatus.FAILED.value:
            return state

        # If no analyzable documents had text, avoid calling LLM with empty context
        if not state.get("document_context", "").strip():
            logger.warning("No analyzable document text available; generating empty structured output.")
            state["extracted_fields"] = {}
            state["missing_information"] = [
                {
                    "field_name": "all_fields",
                    "description": "No text could be analyzed from provided documents (scanned, empty, or failed).",
                    "impact": "Manual investigation intake required.",
                }
            ]
            state["conflicting_information"] = []
            state["raw_response"] = "{}"
            state["token_usage"] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            state["latency_ms"] = 0
            return state

        try:
            result = await provider.generate_structured(
                prompt=state.get("user_prompt", ""),
                response_model=ExtractionStructuredOutput,
                system_prompt=state.get("system_prompt", ""),
            )
            state["raw_response"] = result.raw_content
            state["token_usage"] = {
                "prompt_tokens": result.token_usage.prompt_tokens,
                "completion_tokens": result.token_usage.completion_tokens,
                "total_tokens": result.token_usage.total_tokens,
            }
            state["latency_ms"] = result.latency_ms

            if result.parsed_successfully and result.data:
                data: ExtractionStructuredOutput = result.data
                fields_dict = {}
                for f in data.fields:
                    f_name = f.field_name.strip().lower()
                    if f_name in ALLOWED_EXTRACTION_FIELDS:
                        f.field_name = f_name
                        fields_dict[f_name] = f.model_dump()

                state["extracted_fields"] = fields_dict
                state["missing_information"] = [m.model_dump() for m in data.missing_information]
                state["conflicting_information"] = [c.model_dump() for c in data.conflicting_information]
            else:
                errors = list(state.get("errors", []))
                err_msg = result.validation_error or "Structured incident extraction parsing failed."
                errors.append(sanitize_ai_error(err_msg))
                state["errors"] = errors
                state["status"] = ExtractionStatus.FAILED.value

        except Exception as e:
            errors = list(state.get("errors", []))
            errors.append(sanitize_ai_error(f"Incident extraction LLM failure: {str(e)}"))
            state["errors"] = errors
            state["status"] = ExtractionStatus.FAILED.value

        return state

    return extract_incident_fields_node


def validate_source_references_node(state: IncidentExtractionWorkflowState) -> IncidentExtractionWorkflowState:
    """
    Validates that cited document_ids and filenames correspond to genuine source documents.
    Protects against model hallucinating source references.
    """
    if state.get("status") == ExtractionStatus.FAILED.value:
        return state

    valid_doc_map = state.get("valid_document_map", {})
    extracted_fields = state.get("extracted_fields", {})

    for field_name, field_dict in extracted_fields.items():
        refs = field_dict.get("source_references", [])
        validated_refs = []
        has_invalid_ref = False

        for ref in refs:
            doc_id = ref.get("document_id")
            fname = ref.get("filename")

            # Check if cited document belongs to genuine source docs
            if doc_id in valid_doc_map:
                # Synchronize filename if model mistyped it
                ref["filename"] = valid_doc_map[doc_id]
                validated_refs.append(ref)
            else:
                has_invalid_ref = True
                logger.warning(
                    f"Hallucinated document_id '{doc_id}' detected for field '{field_name}'. Flagging for review."
                )

        if has_invalid_ref:
            field_dict["status"] = FieldExtractionStatus.NEEDS_REVIEW.value
            field_dict["explanation"] = (
                (field_dict.get("explanation") or "") + " [FLAG: Model cited unverified document reference]"
            ).strip()

        field_dict["source_references"] = validated_refs

    state["extracted_fields"] = extracted_fields
    return state


def detect_missing_and_conflicting_node(state: IncidentExtractionWorkflowState) -> IncidentExtractionWorkflowState:
    """
    Audits extracted fields against critical GMP parameters and appends unpopulated
    fields to missing_information.
    """
    if state.get("status") == ExtractionStatus.FAILED.value:
        return state

    extracted = state.get("extracted_fields", {})
    missing_items = list(state.get("missing_information", []))
    existing_missing_keys = {m.get("field_name") for m in missing_items}

    for key, desc in CRITICAL_INVESTIGATION_FIELDS:
        field_val = extracted.get(key)
        is_missing = False
        if not field_val or field_val.get("value") is None or str(field_val.get("value")).strip() == "":
            is_missing = True
        elif field_val.get("status") == FieldExtractionStatus.NOT_FOUND.value:
            is_missing = True

        if is_missing and key not in existing_missing_keys:
            missing_items.append(
                {
                    "field_name": key,
                    "description": f"Critical GMP parameter '{key}' ({desc}) was not documented in source records.",
                    "impact": "Investigation completeness requires manual entry or supplementary documents.",
                }
            )

    state["missing_information"] = missing_items

    # Format conflicting entries
    conflicting_items = list(state.get("conflicting_information", []))
    for f_name, f_data in extracted.items():
        if f_data.get("status") == FieldExtractionStatus.CONFLICTING.value:
            if not any(c.get("field_name") == f_name for c in conflicting_items):
                conflicting_items.append(
                    {
                        "field_name": f_name,
                        "description": f_data.get("explanation") or f"Conflicting values reported for {f_name}.",
                        "conflicting_references": f_data.get("source_references", []),
                    }
                )

    state["conflicting_information"] = conflicting_items
    return state


def complete_extraction_node(state: IncidentExtractionWorkflowState) -> IncidentExtractionWorkflowState:
    """Finalizes successful extraction state."""
    if not state.get("errors") and state.get("status") != ExtractionStatus.FAILED.value:
        state["status"] = ExtractionStatus.COMPLETED.value
    return state


def handle_extraction_failure_node(state: IncidentExtractionWorkflowState) -> IncidentExtractionWorkflowState:
    """Handles extraction workflow failures gracefully."""
    state["status"] = ExtractionStatus.FAILED.value
    if not state.get("errors"):
        state["errors"] = ["Unknown incident extraction failure."]
    return state

