"""
Investigation Gap Context Retrieval Service
============================================
Retrieves and compiles authorized investigation evidence context for gap detection
and investigation completeness assessment. Enforces strict investigation isolation.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.incident_extraction import IncidentExtraction
from app.models.risk_assessment import RiskAssessment
from app.models.rca import (
    RCAAnalysis,
    RootCause,
    WhyAnalysisStep,
    FishboneCategory,
    FishboneCause,
)
from app.models.evidence_gap import EvidenceGap
from app.models.audit import AuditLog
from app.models.enums import (
    RiskAssessmentReviewStatus,
    RCAStatus,
    ExtractionReviewStatus,
    EvidenceVerificationStatus,
)


class GapContextPreparationService:
    async def prepare_investigation_gap_context(
        self,
        session: AsyncSession,
        investigation_id: str,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Gathers complete, authoritative context for the active investigation.
        Rejects data belonging to any other investigation.
        """
        # 1. Retrieve Investigation with Incident
        stmt_inv = (
            select(Investigation)
            .options(selectinload(Investigation.incident))
            .where(Investigation.id == investigation_id)
        )
        res_inv = await session.execute(stmt_inv)
        investigation = res_inv.scalar_one_or_none()
        if not investigation:
            raise ValueError(f"Investigation {investigation_id} not found.")

        incident_data = {}
        if investigation.incident:
            inc: Incident = investigation.incident
            incident_data = {
                "id": inc.id,
                "api_product_name": inc.api_product_name,
                "batch_number": inc.batch_number,
                "manufacturing_stage": inc.manufacturing_stage,
                "incident_date": inc.incident_date.isoformat() if inc.incident_date else None,
                "equipment_id": inc.equipment_id,
                "expected_parameter": inc.expected_parameter,
                "actual_parameter": inc.actual_parameter,
                "incident_description": inc.incident_description,
                "immediate_actions": inc.immediate_actions,
                "affected_batches": inc.affected_batches or [],
                "potential_quality_impact": inc.potential_quality_impact,
                "is_confirmed": True,
            }

        # 2. Retrieve Human-Accepted Extractions
        stmt_extr = (
            select(IncidentExtraction)
            .where(
                IncidentExtraction.investigation_id == investigation_id,
                IncidentExtraction.review_status.in_([
                    ExtractionReviewStatus.ACCEPTED.value,
                    ExtractionReviewStatus.PARTIALLY_ACCEPTED.value,
                ]),
            )
            .order_by(desc(IncidentExtraction.created_at))
            .limit(1)
        )
        res_extr = await session.execute(stmt_extr)
        extraction = res_extr.scalar_one_or_none()
        extraction_data = extraction.extracted_fields if extraction else {}

        # 3. Retrieve Documents
        stmt_docs = (
            select(Document)
            .where(Document.investigation_id == investigation_id)
            .order_by(Document.uploaded_at)
        )
        res_docs = await session.execute(stmt_docs)
        documents = list(res_docs.scalars().all())
        doc_inventory = []
        for d in documents:
            doc_inventory.append({
                "document_id": d.id,
                "filename": d.original_filename,
                "file_type": d.file_type,
                "processing_status": d.processing_status,
                "excerpt": (d.extracted_text[:400] + "...") if d.extracted_text else "",
                "has_text": bool(d.extracted_text),
            })

        # 4. Retrieve Verified Evidence
        stmt_ev = (
            select(Evidence)
            .where(Evidence.investigation_id == investigation_id)
            .order_by(Evidence.created_at)
        )
        res_ev = await session.execute(stmt_ev)
        evidence_list = list(res_ev.scalars().all())
        verified_evidence = []
        for ev in evidence_list:
            verified_evidence.append({
                "evidence_id": ev.id,
                "document_id": ev.document_id,
                "title": ev.title,
                "evidence_type": ev.evidence_type,
                "verification_status": ev.verification_status,
                "description": ev.description,
                "is_verified": ev.verification_status == EvidenceVerificationStatus.VERIFIED.value,
            })

        # 5. Retrieve Accepted Risk Assessment
        stmt_risk = (
            select(RiskAssessment)
            .where(
                RiskAssessment.investigation_id == investigation_id,
                RiskAssessment.review_status == RiskAssessmentReviewStatus.ACCEPTED.value,
            )
            .order_by(desc(RiskAssessment.created_at))
            .limit(1)
        )
        res_risk = await session.execute(stmt_risk)
        risk_record = res_risk.scalar_one_or_none()
        risk_data = {}
        if risk_record:
            risk_data = {
                "id": risk_record.id,
                "overall_risk": risk_record.overall_risk,
                "severity": risk_record.severity,
                "likelihood": risk_record.likelihood,
                "urgency": risk_record.urgency_recommendation,
                "rationale": risk_record.risk_rationale,
            }

        # 6. Retrieve RCA Analysis (5 Whys, Fishbone, Root Causes)
        stmt_rca = (
            select(RCAAnalysis)
            .where(
                RCAAnalysis.investigation_id == investigation_id,
                RCAAnalysis.status.in_([RCAStatus.ACCEPTED.value, RCAStatus.PENDING_REVIEW.value, RCAStatus.AI_ANALYSIS_COMPLETED.value]),
            )
            .order_by(desc(RCAAnalysis.analysis_version))
            .limit(1)
        )
        res_rca = await session.execute(stmt_rca)
        rca_record = res_rca.scalar_one_or_none()
        rca_data = {}
        if rca_record:
            rca_data = {
                "id": rca_record.id,
                "status": rca_record.status,
                "problem_statement": rca_record.problem_statement,
                "five_whys": rca_record.five_whys_data or [],
                "fishbone": rca_record.fishbone_data or {},
                "root_causes": rca_record.root_causes_data or [],
                "contributing_factors": rca_record.contributing_factors_data or [],
            }

        # 7. Retrieve Existing Evidence Gaps
        stmt_gaps = (
            select(EvidenceGap)
            .where(EvidenceGap.investigation_id == investigation_id)
            .order_by(EvidenceGap.created_at)
        )
        res_gaps = await session.execute(stmt_gaps)
        gaps_list = list(res_gaps.scalars().all())
        existing_gaps = []
        for g in gaps_list:
            existing_gaps.append({
                "gap_id": g.id,
                "gap_title": g.gap_title or g.description[:40],
                "category": g.category,
                "priority": g.priority,
                "status": g.status,
                "description": g.description,
                "reason": g.reason,
            })

        # 8. Retrieve Investigation Review / Audit Summary
        stmt_audit = (
            select(AuditLog)
            .where(AuditLog.investigation_id == investigation_id)
            .order_by(desc(AuditLog.created_at))
            .limit(20)
        )
        res_audit = await session.execute(stmt_audit)
        audit_records = list(res_audit.scalars().all())
        audit_summary = [{"action": a.action, "timestamp": a.created_at.isoformat()} for a in audit_records]

        # Compile formatted prompt text
        compiled_text = self._compile_prompt_context(
            investigation=investigation,
            incident_data=incident_data,
            extraction_data=extraction_data,
            doc_inventory=doc_inventory,
            verified_evidence=verified_evidence,
            risk_data=risk_data,
            rca_data=rca_data,
            existing_gaps=existing_gaps,
        )

        return {
            "investigation_id": investigation.id,
            "investigation_number": investigation.investigation_number,
            "investigation_status": investigation.status,
            "incident": incident_data,
            "extraction": extraction_data,
            "documents": doc_inventory,
            "evidence": verified_evidence,
            "risk_assessment": risk_data,
            "rca": rca_data,
            "existing_gaps": existing_gaps,
            "audit_summary": audit_summary,
            "compiled_prompt_context": compiled_text,
        }

    def _compile_prompt_context(
        self,
        investigation: Investigation,
        incident_data: Dict[str, Any],
        extraction_data: Dict[str, Any],
        doc_inventory: List[Dict[str, Any]],
        verified_evidence: List[Dict[str, Any]],
        risk_data: Dict[str, Any],
        rca_data: Dict[str, Any],
        existing_gaps: List[Dict[str, Any]],
    ) -> str:
        lines = [
            f"=== INVESTIGATION CONTEXT: {investigation.investigation_number} ===",
            f"Investigation Title: {investigation.title}",
            f"Investigation Status: {investigation.status}",
            f"Risk Level: {investigation.risk_level} | Priority: {investigation.priority}",
            "",
            "--- CONFIRMED INCIDENT INFORMATION ---",
        ]
        if incident_data:
            lines.extend([
                f"API Product: {incident_data.get('api_product_name')}",
                f"Batch Number: {incident_data.get('batch_number')}",
                f"Manufacturing Stage: {incident_data.get('manufacturing_stage')}",
                f"Equipment ID: {incident_data.get('equipment_id')}",
                f"Expected Parameter: {incident_data.get('expected_parameter')}",
                f"Actual Parameter: {incident_data.get('actual_parameter')}",
                f"Incident Description: {incident_data.get('incident_description')}",
                f"Immediate Actions: {incident_data.get('immediate_actions')}",
            ])
        else:
            lines.append("No confirmed incident record registered yet.")

        lines.extend(["", "--- DOCUMENT INVENTORY ---"])
        if doc_inventory:
            for d in doc_inventory:
                lines.append(f"- Doc ID: {d['document_id']} | File: {d['filename']} | Status: {d['processing_status']}")
        else:
            lines.append("No documents uploaded.")

        lines.extend(["", "--- VERIFIED EVIDENCE RECORDS ---"])
        if verified_evidence:
            for ev in verified_evidence:
                lines.append(f"- Evidence ID: {ev['evidence_id']} | Type: {ev['evidence_type']} | Status: {ev['verification_status']} | Title: {ev['title']}")
        else:
            lines.append("No verified evidence records on file.")

        lines.extend(["", "--- QUALITY IMPACT & RISK ASSESSMENT ---"])
        if risk_data:
            lines.extend([
                f"Overall Risk: {risk_data.get('overall_risk')} | Severity: {risk_data.get('severity')}",
                f"Urgency: {risk_data.get('urgency')}",
                f"Rationale: {risk_data.get('rationale')}",
            ])
        else:
            lines.append("No accepted Quality Risk Assessment available.")

        lines.extend(["", "--- ROOT CAUSE ANALYSIS (RCA) STATUS ---"])
        if rca_data:
            lines.extend([
                f"RCA Status: {rca_data.get('status')}",
                f"Problem Statement: {rca_data.get('problem_statement')}",
                f"Five Whys Count: {len(rca_data.get('five_whys', []))}",
                f"Root Causes Identified: {len(rca_data.get('root_causes', []))}",
            ])
            for rc in rca_data.get("root_causes", []):
                lines.append(f"  * Root Cause: {rc.get('title')} (Status: {rc.get('verification_status', 'PROPOSED')})")
        else:
            lines.append("No RCA record completed yet.")

        lines.extend(["", "--- EXISTING UNRESOLVED GAPS ---"])
        if existing_gaps:
            for g in existing_gaps:
                lines.append(f"- [{g['priority']}] {g['category']}: {g['gap_title']} ({g['status']})")
        else:
            lines.append("No existing gaps recorded.")

        return "\n".join(lines)


gap_context_service = GapContextPreparationService()
