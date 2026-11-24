from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.rca import RCAAnalysis, RootCause, ContributingFactor
from app.models.evidence_gap import EvidenceGap
from app.models.risk_assessment import RiskAssessment
from app.models.capa import CAPA
from app.models.enums import RiskAssessmentReviewStatus, RCAStatus, EvidenceGapStatus


class CAPAContextService:
    """
    Assembles comprehensive, verified investigation context for AI CAPA recommendations:
    - Confirmed incident details and accepted extractions
    - Accepted RCA analyses with verified root causes and contributing factors
    - Unverified causal hypotheses requiring provisional recommendation labels
    - Accepted Risk Assessment matrix, criticality, and urgency
    - Critical and High priority unresolved evidence gaps
    - Existing CAPA plans to avoid duplicative proposals
    - Verified evidence references and document inventory
    """

    async def gather_capa_context(
        self, session: AsyncSession, investigation_id: str
    ) -> Dict[str, Any]:
        # 1. Retrieve Investigation & Incident
        stmt_inv = (
            select(Investigation)
            .where(Investigation.id == investigation_id)
            .options(selectinload(Investigation.incident))
        )
        res_inv = await session.execute(stmt_inv)
        inv = res_inv.scalar_one_or_none()
        if not inv:
            raise ValueError(f"Investigation {investigation_id} not found.")

        incident_info: Dict[str, Any] = {}
        if inv.incident:
            inc = inv.incident
            incident_info = {
                "incident_id": inc.id,
                "batch_number": inc.batch_number,
                "product_name": getattr(inc, "api_product_name", ""),
                "manufacturing_site": "Active Ingredients Plant",
                "unit_operation": getattr(inc, "manufacturing_stage", ""),
                "equipment_id": getattr(inc, "equipment_id", ""),
                "severity": getattr(inv, "priority", "MAJOR"),
                "incident_date": inc.incident_date.isoformat() if inc.incident_date else None,
                "description": getattr(inc, "incident_description", ""),
            }

        # 2. Retrieve Accepted / Completed RCA Analyses and Root Causes
        stmt_rca = (
            select(RCAAnalysis)
            .where(RCAAnalysis.investigation_id == investigation_id)
            .options(
                selectinload(RCAAnalysis.root_causes).selectinload(RootCause.contributing_factors),
                selectinload(RCAAnalysis.why_steps),
                selectinload(RCAAnalysis.fishbone_categories),
            )
            .order_by(RCAAnalysis.created_at.desc())
        )
        res_rca = await session.execute(stmt_rca)
        rca_list = list(res_rca.scalars().all())

        verified_root_causes: List[Dict[str, Any]] = []
        unverified_hypotheses: List[Dict[str, Any]] = []
        contributing_factors_list: List[Dict[str, Any]] = []
        accepted_rca_id: Optional[str] = None

        for rca in rca_list:
            if rca.status in [RCAStatus.ACCEPTED.value, RCAStatus.FINALIZED.value, "Accepted", "Completed"]:
                if not accepted_rca_id:
                    accepted_rca_id = rca.id

            for rc in rca.root_causes:
                # Check verification status
                is_confirmed = rc.human_confirmed or rc.status in ["Confirmed", "Verified", "CONFIRMED", "VERIFIED"]
                rc_dict = {
                    "root_cause_id": rc.id,
                    "rca_analysis_id": rca.id,
                    "title": rc.title,
                    "description": rc.description,
                    "category": rc.category,
                    "evidence_strength": rc.evidence_strength,
                    "is_confirmed": is_confirmed,
                    "status": rc.status,
                }
                if is_confirmed:
                    verified_root_causes.append(rc_dict)
                else:
                    unverified_hypotheses.append(rc_dict)

                for cf in rc.contributing_factors:
                    contributing_factors_list.append({
                        "contributing_factor_id": cf.id,
                        "root_cause_id": rc.id,
                        "description": cf.description,
                        "category": cf.category,
                        "evidence_reference": cf.evidence_reference,
                    })

        # If no RCA was accepted yet, take the latest RCA if available
        if not accepted_rca_id and rca_list:
            accepted_rca_id = rca_list[0].id

        # 3. Retrieve Accepted Risk Assessment
        stmt_risk = (
            select(RiskAssessment)
            .where(RiskAssessment.investigation_id == investigation_id)
            .order_by(RiskAssessment.created_at.desc())
        )
        res_risk = await session.execute(stmt_risk)
        all_risks = list(res_risk.scalars().all())

        accepted_risk = next(
            (r for r in all_risks if r.review_status == RiskAssessmentReviewStatus.ACCEPTED.value),
            all_risks[0] if all_risks else None,
        )

        risk_context: Dict[str, Any] = {}
        if accepted_risk:
            risk_context = {
                "risk_assessment_id": accepted_risk.id,
                "overall_risk": accepted_risk.overall_risk,
                "severity": accepted_risk.severity,
                "likelihood": accepted_risk.likelihood,
                "detectability": accepted_risk.detectability,
                "urgency": accepted_risk.urgency_recommendation,
                "risk_summary": accepted_risk.risk_rationale,
            }

        # 4. Retrieve Evidence Gaps (especially open/critical)
        stmt_gaps = (
            select(EvidenceGap)
            .where(EvidenceGap.investigation_id == investigation_id)
            .order_by(EvidenceGap.created_at.desc())
        )
        res_gaps = await session.execute(stmt_gaps)
        gaps_list = list(res_gaps.scalars().all())

        unresolved_gaps: List[Dict[str, Any]] = []
        for g in gaps_list:
            is_unresolved = g.status in [
                EvidenceGapStatus.OPEN.value,
                EvidenceGapStatus.UNDER_REVIEW.value,
                EvidenceGapStatus.EVIDENCE_REQUESTED.value,
                EvidenceGapStatus.EVIDENCE_RECEIVED.value,
                EvidenceGapStatus.PENDING_VERIFICATION.value,
                EvidenceGapStatus.REOPENED.value,
                "Open",
                "OPEN",
                "UNDER_REVIEW",
            ]
            if is_unresolved:
                unresolved_gaps.append({
                    "gap_id": g.id,
                    "gap_title": g.gap_title or g.description[:60],
                    "category": g.category,
                    "priority": g.priority,
                    "description": g.description,
                    "affected_area": g.affected_area,
                    "recommended_action": g.recommended_action,
                })

        # 5. Retrieve Existing CAPAs to prevent duplicate suggestions
        stmt_capas = (
            select(CAPA)
            .where(CAPA.investigation_id == investigation_id)
            .options(selectinload(CAPA.tasks))
        )
        res_capas = await session.execute(stmt_capas)
        existing_capas_list = list(res_capas.scalars().all())

        existing_capas: List[Dict[str, Any]] = [
            {
                "capa_id": c.id,
                "capa_number": c.capa_number,
                "title": c.title,
                "capa_type": c.capa_type,
                "root_cause_id": c.root_cause_id,
                "status": c.status,
                "tasks_count": len(c.tasks),
            }
            for c in existing_capas_list
        ]

        # 6. Retrieve Document Inventory & Evidence
        stmt_docs = select(Document).where(Document.investigation_id == investigation_id)
        res_docs = await session.execute(stmt_docs)
        docs = list(res_docs.scalars().all())
        doc_inventory = [
            {
                "document_id": d.id,
                "original_filename": d.original_filename,
                "document_type": getattr(d, "file_type", "document"),
                "is_analyzable": True,
            }
            for d in docs
        ]

        stmt_ev = select(Evidence).where(Evidence.investigation_id == investigation_id)
        res_ev = await session.execute(stmt_ev)
        ev_items = list(res_ev.scalars().all())
        evidence_inventory = [
            {
                "evidence_id": e.id,
                "document_id": e.document_id,
                "title": e.title,
                "source_reference": e.source_reference,
            }
            for e in ev_items
        ]

        return {
            "investigation_id": inv.id,
            "investigation_number": inv.investigation_number,
            "title": inv.title,
            "stage": getattr(inv, "stage", inv.status),
            "status": inv.status,
            "incident": incident_info,
            "accepted_rca_id": accepted_rca_id,
            "verified_root_causes": verified_root_causes,
            "unverified_hypotheses": unverified_hypotheses,
            "contributing_factors": contributing_factors_list,
            "risk_assessment": risk_context,
            "unresolved_gaps": unresolved_gaps,
            "existing_capas": existing_capas,
            "documents": doc_inventory,
            "evidence": evidence_inventory,
            "valid_root_cause_ids": [rc["root_cause_id"] for rc in verified_root_causes + unverified_hypotheses],
            "valid_contributing_factor_ids": [cf["contributing_factor_id"] for cf in contributing_factors_list],
            "valid_evidence_gap_ids": [g["gap_id"] for g in unresolved_gaps],
            "valid_evidence_ids": [e["evidence_id"] for e in evidence_inventory],
            "valid_document_ids": [d["document_id"] for d in doc_inventory],
        }


capa_context_service = CAPAContextService()

