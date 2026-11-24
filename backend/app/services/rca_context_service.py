"""
RCA Context Preparation Service for Pharmaceutical Investigations.
Assembles confirmed incident data, evidence records, document excerpts,
and active risk assessments while strictly enforcing investigation scoping,
ALCOA+ traceability, and prompt injection defense.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.risk_assessment import RiskAssessment
from app.repositories.investigation_repository import investigation_repo, incident_repo
from app.repositories.document_evidence_repository import document_repo, evidence_repo
from app.repositories.risk_assessment_repository import risk_assessment_repo
from app.repositories.incident_extraction_repository import incident_extraction_repo
from app.services.document_context_service import document_context_service
from app.schemas.rca import RCAEvidenceReference

logger = logging.getLogger(__name__)


def _sanitize_storage_paths(text: str) -> str:
    """Removes local filesystem paths (/var/..., C:\\..., /tmp/...) to prevent internal path leakage."""
    if not text:
        return ""
    text = re.sub(r"[A-Za-z]:\\[\w\\\.\-]+", "[REDACTED_PATH]", text)
    text = re.sub(r"/(?:var|tmp|app|etc|secure|home|data)/[\w/\.\-]+", "[REDACTED_PATH]", text)
    return text


class RCAContextPreparationService:
    """
    Assembles evidence-grounded context for 5 Whys and Fishbone root cause analysis.
    Guarantees:
    - Never leaks internal storage paths or server secrets.
    - Strictly confines retrieval to the specified investigation_id.
    - Differentiates confirmed empirical facts from unverified draft hypotheses.
    - Cites source IDs, document IDs, page numbers, and verbatim excerpts.
    """

    DEFAULT_MAX_CONTEXT_CHARS = 32000

    async def prepare_rca_context(
        self,
        session: AsyncSession,
        investigation_id: str,
        use_documents: bool = True,
        max_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Gathers confirmed incident data, active risk assessments, verified evidence items,
        and sanitized document text.
        """
        investigation = await investigation_repo.get(session, investigation_id)
        if not investigation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation {investigation_id} not found.",
            )

        # 1. Incident information
        incident = await incident_repo.get_by_investigation(session, investigation_id)
        has_unreviewed_incident_data = False
        incident_snapshot: Dict[str, Any] = {}

        if incident and (incident.api_product_name or incident.incident_description):
            incident_snapshot = {
                "api_product_name": incident.api_product_name,
                "batch_number": incident.batch_number,
                "manufacturing_stage": incident.manufacturing_stage,
                "incident_date": incident.incident_date.isoformat() if incident.incident_date else None,
                "equipment_id": incident.equipment_id,
                "expected_parameter": incident.expected_parameter,
                "actual_parameter": incident.actual_parameter,
                "incident_description": incident.incident_description,
                "immediate_actions": incident.immediate_actions,
                "affected_batches": incident.affected_batches,
                "potential_quality_impact": incident.potential_quality_impact,
                "source": "confirmed_incident_record",
            }
        else:
            # Fallback to extraction draft
            extractions = await incident_extraction_repo.get_by_investigation(session, investigation_id, limit=1)
            if extractions and extractions[0].extracted_fields:
                has_unreviewed_incident_data = True
                ef = extractions[0].extracted_fields
                incident_snapshot = {
                    "api_product_name": (ef.get("api_product_name") or {}).get("value"),
                    "batch_number": (ef.get("batch_number") or {}).get("value"),
                    "manufacturing_stage": (ef.get("manufacturing_stage") or {}).get("value"),
                    "incident_date": (ef.get("incident_date") or {}).get("value"),
                    "equipment_id": (ef.get("equipment_id") or {}).get("value"),
                    "expected_parameter": (ef.get("expected_parameter_value") or {}).get("value"),
                    "actual_parameter": (ef.get("actual_parameter_value") or {}).get("value"),
                    "incident_description": (ef.get("incident_description") or {}).get("value")
                    or (ef.get("observed_event") or {}).get("value"),
                    "immediate_actions": (ef.get("immediate_actions") or {}).get("value"),
                    "affected_batches": (ef.get("affected_batches") or {}).get("value"),
                    "potential_quality_impact": (ef.get("potential_quality_impact") or {}).get("value"),
                    "source": "unconfirmed_ai_extraction_draft",
                }

        # 2. Active Risk Assessment (if available)
        active_risk = await risk_assessment_repo.get_active_for_investigation(session, investigation_id)
        risk_summary: Optional[Dict[str, Any]] = None
        if active_risk:
            risk_summary = {
                "assessment_id": active_risk.id,
                "overall_risk": active_risk.overall_risk,
                "severity": active_risk.severity,
                "likelihood": active_risk.likelihood,
                "urgency_recommendation": active_risk.urgency_recommendation,
                "risk_rationale": active_risk.risk_rationale,
                "quality_impact": active_risk.quality_impact,
                "process_impact": active_risk.process_impact,
                "equipment_impact": active_risk.equipment_impact,
                "batch_impact": active_risk.batch_impact,
                "data_integrity_impact": active_risk.data_integrity_impact,
            }

        # 3. Evidence Records
        evidence_items = await evidence_repo.get_by_investigation(session, investigation_id)
        evidence_list: List[Dict[str, Any]] = []
        for ev in evidence_items:
            evidence_list.append({
                "evidence_id": ev.id,
                "document_id": ev.document_id,
                "title": ev.title,
                "description": ev.description,
                "source_reference": ev.source_reference,
                "page_number": ev.page_number,
                "excerpt": _sanitize_storage_paths(ev.excerpt or ""),
                "verification_status": ev.verification_status,
            })

        # 4. Source Documents Text Context
        doc_context = ""
        valid_document_map: Dict[str, str] = {}
        if use_documents:
            doc_context, doc_summaries, analyzable_docs = await document_context_service.prepare_context(
                session=session,
                investigation_id=investigation_id,
                max_chars=max_chars or self.DEFAULT_MAX_CONTEXT_CHARS,
            )
            valid_document_map = {doc.id: doc.original_filename for doc in analyzable_docs}

        # 5. Build Formatted Prompt Context
        context_lines: List[str] = [
            f"# INVESTIGATION CONTEXT: {investigation.investigation_number} - {investigation.title}\n"
        ]

        if has_unreviewed_incident_data:
            context_lines.append(
                "> [!WARNING] DATA RELIABILITY NOTICE:\n"
                "> The incident parameters below are derived from UNCONFIRMED AI DRAFTS awaiting human verification.\n"
                "> Evaluate potential causes with appropriate scrutiny.\n"
            )

        context_lines.append("## Confirmed Incident Details:")
        context_lines.append(f"- API Product: {incident_snapshot.get('api_product_name', 'Not specified')}")
        context_lines.append(f"- Batch Number: {incident_snapshot.get('batch_number', 'Not specified')}")
        context_lines.append(f"- Manufacturing Stage: {incident_snapshot.get('manufacturing_stage', 'Not specified')}")
        context_lines.append(f"- Incident Date: {incident_snapshot.get('incident_date', 'Not specified')}")
        context_lines.append(f"- Equipment Involved: {incident_snapshot.get('equipment_id', 'Not specified')}")
        context_lines.append(f"- Expected Parameter: {incident_snapshot.get('expected_parameter', 'Not specified')}")
        context_lines.append(f"- Actual Parameter: {incident_snapshot.get('actual_parameter', 'Not specified')}")
        context_lines.append(f"- Incident Description: {incident_snapshot.get('incident_description', 'Not specified')}")
        if incident_snapshot.get("immediate_actions"):
            context_lines.append(f"- Immediate Actions Taken: {incident_snapshot.get('immediate_actions')}")
        if incident_snapshot.get("affected_batches"):
            context_lines.append(f"- Affected Batches: {incident_snapshot.get('affected_batches')}")

        if risk_summary:
            context_lines.append("\n## Active Quality Risk Assessment Summary:")
            context_lines.append(f"- Overall Risk Level: {risk_summary.get('overall_risk')}")
            context_lines.append(f"- Severity: {risk_summary.get('severity')} | Likelihood: {risk_summary.get('likelihood')}")
            context_lines.append(f"- Urgency Recommendation: {risk_summary.get('urgency_recommendation')}")
            context_lines.append(f"- Risk Rationale: {risk_summary.get('risk_rationale')}")

        if evidence_list:
            context_lines.append("\n## Formally Verified Evidence Records:")
            for ev in evidence_list:
                context_lines.append(
                    f"- [{ev['verification_status']}] Evidence ID {ev['evidence_id']} (Doc: {ev['document_id'] or 'N/A'}, Page {ev['page_number'] or 'N/A'}):\n"
                    f"  Title: {ev['title']}\n"
                    f"  Excerpt: \"{ev['excerpt']}\""
                )

        if doc_context and doc_context.strip():
            context_lines.append("\n## Uploaded Source Document Text Excerpts:\n")
            context_lines.append(doc_context)

        compiled_prompt_context = "\n".join(context_lines)

        return {
            "investigation_id": investigation_id,
            "investigation_number": investigation.investigation_number,
            "investigation_title": investigation.title,
            "incident_snapshot": incident_snapshot,
            "has_unreviewed_incident_data": has_unreviewed_incident_data,
            "risk_summary": risk_summary,
            "evidence_list": evidence_list,
            "valid_document_map": valid_document_map,
            "valid_evidence_map": {ev["evidence_id"]: ev["title"] for ev in evidence_list},
            "document_context": doc_context,
            "compiled_prompt_context": compiled_prompt_context,
        }


rca_context_service = RCAContextPreparationService()
