import uuid
import json
import pytest
from datetime import datetime, timezone
from typing import Dict, Any, List
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import get_password_hash
from app.models.enums import (
    RoleName,
    PriorityLevel,
    RiskLevel,
    InvestigationStatus,
    RCAStatus,
    CauseStatus,
    CauseClassification,
    Fishbone6MCategory,
    RCAMethod,
    AuditAction,
)
from app.models.user import User, Role
from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.document import Document
from app.models.audit import AuditLog
from app.models.rca import (
    RCAAnalysis,
    WhyAnalysisStep,
    FishboneCategory,
    FishboneCause,
    RootCause,
)
from app.schemas.user import UserCreate
from app.schemas.rca import (
    RCARequest,
    RCAResponse,
    RCAReviewPatchRequest,
    ManualCauseCreateRequest,
    CausePatchRequest,
    CauseVerifyRequest,
    CauseRejectRequest,
    RCAAcceptRequest,
    RCAEvidenceRequest,
    RCAStructuredOutput,
    WhyStepItem,
    FishboneCauseItem,
    RootCauseItem,
    ContributingFactorItem,
    RCAEvidenceGapItem,
    RCAEvidenceReference,
)
from app.cli import seed_standard_roles
from app.repositories.user_repository import user_repo
from app.repositories.investigation_repository import investigation_repo, incident_repo
from app.repositories.rca_repository import rca_repo
from app.services.rca_service import rca_service
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.graphs.rca_builder import create_rca_graph
from app.ai.graphs.rca_state import RCAWorkflowState
from app.ai.graphs.rca_nodes import (
    validate_rca_request_node,
    prepare_rca_context_node,
    validate_causal_chain_node,
    validate_rca_citations_node,
    categorize_fishbone_and_causes_node,
)


def build_mock_structured_rca(doc_id: str) -> Dict[str, Any]:
    return {
        "problem_statement": "Elevated crystallization temperature (48.5 °C) during Pregabalin crystallization exceeded validated process limit of 25.0 °C.",
        "incident_summary": "During batch PGB-2026-0042 production, cooling water flow failed, causing temperature excursion in reactor RX-302.",
        "five_whys": [
            {
                "step_number": 1,
                "question": "Why did the crystallization temperature reach 48.5 °C?",
                "answer": "Cooling jacket flow stopped abruptly during the final crystallizer ramp.",
                "explanation": "Chilled glycol coolant stopped circulating through reactor RX-302 jacket.",
                "supporting_references": [
                    {
                        "document_id": doc_id,
                        "filename": "batch_record.txt",
                        "page_number": 1,
                        "excerpt": "Crystallization temperature reached 48.5 °C during cooling step.",
                        "related_field": "Actual Parameter",
                        "relevance_reason": "Direct batch record entry",
                    }
                ],
                "confidence": 0.95,
                "verification_status": "PROPOSED",
                "assumptions": [],
                "missing_information": [],
                "is_root_cause": False,
                "causal_leap_detected": False,
                "reasoning_critique": None,
            },
            {
                "step_number": 2,
                "question": "Why did cooling jacket flow stop abruptly?",
                "answer": "Pneumatic control valve CV-302 failed in the closed position.",
                "explanation": "The actuator lost pneumatic supply pressure.",
                "supporting_references": [
                    {
                        "document_id": doc_id,
                        "filename": "batch_record.txt",
                        "page_number": 1,
                        "excerpt": "Pneumatic valve CV-302 failed in closed position.",
                        "related_field": "Equipment ID",
                        "relevance_reason": "Operator log",
                    }
                ],
                "confidence": 0.9,
                "verification_status": "PROPOSED",
                "assumptions": [],
                "missing_information": [],
                "is_root_cause": False,
                "causal_leap_detected": False,
                "reasoning_critique": None,
            },
            {
                "step_number": 3,
                "question": "Why did pneumatic valve CV-302 lose supply pressure?",
                "answer": "Instrument air regulator diaphragm ruptured due to age fatigue.",
                "explanation": "The rubber diaphragm developed a 5mm tear under operating pressure.",
                "supporting_references": [],
                "confidence": 0.85,
                "verification_status": "PROPOSED",
                "assumptions": ["Regulator maintenance overdue"],
                "missing_information": ["Maintenance work order logs"],
                "is_root_cause": True,
                "causal_leap_detected": False,
                "reasoning_critique": None,
            },
        ],
        "fishbone_causes": [
            {
                "cause_id": "cause-1",
                "category": "Machine / Equipment",
                "title": "Air Regulator Diaphragm Rupture",
                "description": "Diaphragm fatigue on pneumatic valve CV-302 cut off cooling supply.",
                "supporting_references": [
                    {
                        "document_id": doc_id,
                        "filename": "batch_record.txt",
                        "page_number": 1,
                        "excerpt": "Pneumatic valve CV-302 failed in closed position.",
                        "related_field": "Equipment ID",
                        "relevance_reason": "Operator log",
                    }
                ],
                "confidence": 0.9,
                "verification_status": "PROPOSED",
                "potential_impact": "Loss of cooling during critical crystallization step.",
                "classification": "Root Cause",
                "related_why_step": 3,
                "rejection_reason": None,
            },
            {
                "cause_id": "cause-2",
                "category": "Method / Process",
                "title": "Preventative Maintenance Frequency Inadequate",
                "description": "Elastomer diaphragms scheduled for inspection every 24 months rather than manufacturer recommended 12 months.",
                "supporting_references": [],
                "confidence": 0.8,
                "verification_status": "PROPOSED",
                "potential_impact": "Increased failure rate of critical instrument components.",
                "classification": "Contributing Factor",
                "related_why_step": None,
                "rejection_reason": None,
            },
            {
                "cause_id": "cause-3",
                "category": "Measurement",
                "title": "Secondary Alarm Delay",
                "description": "SCADA high-temperature alarm threshold delay was set to 15 minutes instead of instantaneous.",
                "supporting_references": [],
                "confidence": 0.75,
                "verification_status": "PROPOSED",
                "potential_impact": "Delayed operator notification of temperature excursion.",
                "classification": "Contributing Factor",
                "related_why_step": None,
                "rejection_reason": None,
            },
        ],
        "potential_root_causes": [
            {
                "cause_id": "rc-1",
                "title": "Instrument Air Regulator Diaphragm Fatigue",
                "description": "Pneumatic actuator air supply failed due to unprevented diaphragm rupture on CV-302.",
                "category": "Machine / Equipment",
                "supporting_references": [
                    {
                        "document_id": doc_id,
                        "filename": "batch_record.txt",
                        "page_number": 1,
                        "excerpt": "Pneumatic valve CV-302 failed in closed position.",
                        "related_field": "Equipment ID",
                        "relevance_reason": "Operator log",
                    }
                ],
                "confidence": 0.9,
                "verification_status": "PROPOSED",
                "human_confirmed": False,
            }
        ],
        "contributing_factors": [
            {
                "factor_id": "cf-1",
                "description": "Alarm delay in SCADA system hindered early detection.",
                "category": "Measurement",
                "supporting_references": [],
                "impact_on_incident": "Delayed human intervention by 15 minutes.",
            }
        ],
        "rejected_hypotheses": [],
        "evidence_gaps": [
            {
                "gap_id": "gap-1",
                "description": "Calibration and PM history for valve CV-302 over the preceding 24 months.",
                "reason": "Verify whether preventive maintenance was deferred.",
                "priority": "High",
                "suggested_source": "Computerized Maintenance Management System (CMMS)",
            }
        ],
        "causal_chain_critique": "Causal logic from high temperature to valve actuator diaphragm rupture is physically sound and supported by equipment logs.",
        "unsupported_assumptions": ["Assumed ambient temperatures did not accelerate diaphragm thermal degradation."],
    }


@pytest.fixture
async def setup_rca_environment(db_session: AsyncSession) -> Dict[str, Any]:
    await seed_standard_roles(db_session)

    qa_role = (await db_session.execute(select(Role).where(Role.name == RoleName.QA.value))).scalars().first()
    inv_role = (await db_session.execute(select(Role).where(Role.name == RoleName.INVESTIGATOR.value))).scalars().first()
    operator_role = (await db_session.execute(select(Role).where(Role.name == RoleName.MANUFACTURING_OPERATOR.value))).scalars().first()

    qa_user = User(
        id=str(uuid.uuid4()),
        email="qa.rca@example.com",
        full_name="Quality Assurance Lead",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    qa_user.roles.append(qa_role)

    inv_user = User(
        id=str(uuid.uuid4()),
        email="investigator.rca@example.com",
        full_name="Lead Causal Investigator",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    inv_user.roles.append(inv_role)

    operator_user = User(
        id=str(uuid.uuid4()),
        email="operator.rca@example.com",
        full_name="Shift Operator",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    operator_user.roles.append(operator_role)

    db_session.add_all([qa_user, inv_user, operator_user])
    await db_session.flush()

    # Create investigation
    investigation = Investigation(
        id=str(uuid.uuid4()),
        investigation_number=f"INV-RCA-{uuid.uuid4().hex[:6].upper()}",
        title="Pregabalin Crystallization Temperature Excursion",
        description="Reactor RX-302 temperature spiked during batch crystallization step.",
        status=InvestigationStatus.UNDER_INVESTIGATION.value,
        risk_level=RiskLevel.MAJOR.value,
        priority=PriorityLevel.HIGH.value,
        created_by=inv_user.id,
        assigned_to=inv_user.id,
    )
    db_session.add(investigation)
    await db_session.flush()

    # Add confirmed incident
    incident = Incident(
        id=str(uuid.uuid4()),
        investigation_id=investigation.id,
        api_product_name="Pregabalin Active Substance",
        batch_number="PGB-2026-0042",
        manufacturing_stage="Purification & Final Crystallization",
        incident_date=datetime.now(timezone.utc),
        equipment_id="RX-302",
        expected_parameter="Temperature 20.0 - 25.0 °C",
        actual_parameter="Temperature reached 48.5 °C",
        incident_description="Crystallization cooling interrupted; jacket temperature spiked to 48.5 °C for 45 minutes.",
        immediate_actions="Switched to emergency cooling loop; paused batch crystallization; notified QA.",
        affected_batches=["PGB-2026-0042"],
        potential_quality_impact="Potential Form II polymorph precipitation and impurity profile degradation.",
    )
    db_session.add(incident)

    # Add source document
    doc = Document(
        id=str(uuid.uuid4()),
        investigation_id=investigation.id,
        original_filename="batch_record.txt",
        stored_filename="stored_batch_record.txt",
        file_type="text/plain",
        file_size=2048,
        storage_path="documents/batch_record.txt",
        extracted_text="Crystallization temperature reached 48.5 °C during cooling step. Affected Batches: PGB-2026-0042. Pneumatic valve CV-302 failed in closed position.",
        processing_status="Completed",
        uploaded_by=inv_user.id,
        uploaded_at=datetime.now(timezone.utc),
    )
    db_session.add(doc)
    await db_session.commit()

    return {
        "qa_user": qa_user,
        "inv_user": inv_user,
        "operator_user": operator_user,
        "investigation": investigation,
        "incident": incident,
        "document": doc,
    }


# ===========================================================================
# 1. LangGraph Node Unit Tests
# ===========================================================================

def test_validate_rca_request_node():
    # Failure case: missing incident data
    invalid_state: RCAWorkflowState = {
        "investigation_id": "inv-1",
        "incident_snapshot": {},
        "errors": [],
    }
    res_fail = validate_rca_request_node(invalid_state)
    assert res_fail["status"] == "FAILED"
    assert len(res_fail["errors"]) > 0

    # Success case
    valid_state: RCAWorkflowState = {
        "investigation_id": "inv-1",
        "incident_snapshot": {"api_product_name": "Pregabalin", "incident_description": "Excursion observed"},
        "errors": [],
    }
    res_ok = validate_rca_request_node(valid_state)
    assert res_ok["status"] == "PROCESSING"
    assert len(res_ok["errors"]) == 0


def test_prepare_rca_context_node():
    state: RCAWorkflowState = {
        "status": "PROCESSING",
        "prompt_version": "1.0.0",
        "compiled_prompt_context": "=== INVESTIGATION EVIDENCE ===\nBatch: PGB-2026-0042",
        "additional_focus": "Focus specifically on instrument air pressure and pneumatic valve CV-302.",
    }
    updated = prepare_rca_context_node(state)
    assert "ICH Q9/Q10" in updated["system_prompt"]
    assert "PGB-2026-0042" in updated["user_prompt"]
    assert "valve CV-302" in updated["user_prompt"]


def test_validate_causal_chain_node_detects_circular_and_repeats():
    # Repeated answer simulating circular reasoning
    state: RCAWorkflowState = {
        "status": "PROCESSING",
        "five_whys": [
            {
                "step_number": 1,
                "question": "Why did crystallization temperature exceed limit?",
                "answer": "Because the cooling failed.",
            },
            {
                "step_number": 2,
                "question": "Why did cooling fail?",
                "answer": "Because the cooling failed.",  # Exact repetition
            },
        ],
    }
    res = validate_causal_chain_node(state)
    assert res["five_whys"][1]["causal_leap_detected"] is True
    assert "circular reasoning" in res["five_whys"][1]["reasoning_critique"].lower()


def test_validate_rca_citations_node_strips_unverified_ids():
    state: RCAWorkflowState = {
        "status": "PROCESSING",
        "valid_document_map": {"doc-real-1": "batch_record.txt"},
        "valid_evidence_map": {},
        "potential_root_causes": [
            {
                "cause_id": "rc-1",
                "title": "Air regulator rupture",
                "supporting_references": [
                    {
                        "document_id": "doc-hallucinated-99",  # Invalid ID
                        "filename": "fake_file.pdf",
                        "excerpt": "hallucinated quote",
                    },
                    {
                        "document_id": "doc-real-1",  # Valid ID
                        "filename": "batch_record.txt",
                        "excerpt": "real quote",
                    },
                ],
            }
        ],
    }
    res = validate_rca_citations_node(state)
    rc_refs = res["potential_root_causes"][0]["supporting_references"]
    assert len(rc_refs) == 2
    # Invalid doc id must be stripped to None and flagged
    assert rc_refs[0]["document_id"] is None
    assert "(Unverified Citation)" in rc_refs[0]["relevance_reason"]
    # Valid doc id retained
    assert rc_refs[1]["document_id"] == "doc-real-1"


def test_categorize_fishbone_and_causes_node():
    state: RCAWorkflowState = {
        "status": "PROCESSING",
        "fishbone_causes": [
            {
                "cause_id": "c-1",
                "category": "machine",  # lowercase -> must normalize to Machine / Equipment
                "title": "Valve stuck",
                "classification": "Root Cause",
            },
            {
                "cause_id": "c-2",
                "category": "Random Category",  # non-standard -> must default to Method / Process
                "title": "SOP unclear",
                "classification": "Contributing Factor",
            },
        ],
        "potential_root_causes": [{"cause_id": "rc-1", "title": "Valve defect", "human_confirmed": True}],
    }
    res = categorize_fishbone_and_causes_node(state)
    assert res["fishbone_causes"][0]["category"] == Fishbone6MCategory.MACHINE.value
    assert res["fishbone_causes"][1]["category"] == Fishbone6MCategory.METHOD.value
    # AI causes must be strictly PROPOSED and human_confirmed=False
    assert res["fishbone_causes"][0]["verification_status"] == CauseStatus.PROPOSED.value
    assert res["potential_root_causes"][0]["human_confirmed"] is False


# ===========================================================================
# 2. Service Orchestration & Lifecycle Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_service_start_rca_and_relational_sync(
    db_session: AsyncSession, setup_rca_environment: Dict[str, Any]
):
    env = setup_rca_environment
    inv = env["investigation"]
    inv_user = env["inv_user"]
    doc = env["document"]

    mock_payload = build_mock_structured_rca(doc.id)
    provider = MockAIProvider(structured_data=mock_payload)

    rca = await rca_service.start_rca(
        session=db_session,
        user=inv_user,
        investigation_id=inv.id,
        request=RCARequest(analysis_method=RCAMethod.HYBRID, use_documents=True),
        provider_override=provider,
    )

    assert rca.id is not None
    assert rca.investigation_id == inv.id
    assert rca.analysis_version == 1
    assert rca.status == RCAStatus.AI_ANALYSIS_COMPLETED.value
    assert len(rca.five_whys_data) == 3
    assert len(rca.root_causes_data) == 1
    assert len(rca.contributing_factors_data) == 1

    # Verify relational child records synced
    why_steps = (await db_session.execute(select(WhyAnalysisStep).where(WhyAnalysisStep.rca_analysis_id == rca.id))).scalars().all()
    assert len(why_steps) == 3

    fishbone_cats = (await db_session.execute(select(FishboneCategory).where(FishboneCategory.rca_analysis_id == rca.id))).scalars().all()
    assert len(fishbone_cats) >= 1

    rel_root_causes = (await db_session.execute(select(RootCause).where(RootCause.rca_analysis_id == rca.id))).scalars().all()
    assert len(rel_root_causes) == 1

    # Verify AuditLog recorded
    audits = (await db_session.execute(select(AuditLog).where(AuditLog.investigation_id == inv.id).order_by(AuditLog.created_at))).scalars().all()
    actions = [a.action for a in audits]
    assert AuditAction.RCA_REQUESTED.value in actions
    assert AuditAction.RCA_GENERATED.value in actions


@pytest.mark.asyncio
async def test_service_manual_cause_lifecycle(
    db_session: AsyncSession, setup_rca_environment: Dict[str, Any]
):
    env = setup_rca_environment
    inv = env["investigation"]
    inv_user = env["inv_user"]
    doc = env["document"]

    mock_payload = build_mock_structured_rca(doc.id)
    provider = MockAIProvider(structured_data=mock_payload)

    rca = await rca_service.start_rca(
        session=db_session,
        user=inv_user,
        investigation_id=inv.id,
        request=RCARequest(use_documents=False),
        provider_override=provider,
    )

    # 1. Add manual cause
    new_cause = await rca_service.add_manual_cause(
        session=db_session,
        user=inv_user,
        rca_id=rca.id,
        request=ManualCauseCreateRequest(
            category=Fishbone6MCategory.MANPOWER.value,
            title="Operator Training Gap",
            description="Operator on shift was not certified on emergency cooling changeover SOP.",
            classification=CauseClassification.CONTRIBUTING_FACTOR,
        ),
    )
    cause_id = new_cause["cause_id"]
    assert new_cause["is_manual"] is True
    assert new_cause["category"] == Fishbone6MCategory.MANPOWER.value

    # 2. Edit cause
    updated_cause = await rca_service.update_cause(
        session=db_session,
        user=inv_user,
        rca_id=rca.id,
        cause_id=cause_id,
        request=CausePatchRequest(description="Updated description: Operator certification expired 2 weeks prior."),
    )
    assert "expired 2 weeks prior" in updated_cause["description"]

    # 3. Verify cause
    verified_cause = await rca_service.verify_cause(
        session=db_session,
        user=inv_user,
        rca_id=rca.id,
        cause_id=cause_id,
        request=CauseVerifyRequest(verification_notes="Confirmed via LMS training matrix records."),
    )
    assert verified_cause["verification_status"] == CauseStatus.VERIFIED.value
    assert verified_cause["human_confirmed"] is True

    # 4. Reject cause
    rejected_cause = await rca_service.reject_cause(
        session=db_session,
        user=inv_user,
        rca_id=rca.id,
        cause_id=cause_id,
        request=CauseRejectRequest(rejection_reason="Further investigation proved primary operator handled changeover properly."),
    )
    assert rejected_cause["verification_status"] == CauseStatus.REJECTED.value

    # Check AuditLog
    audits = (await db_session.execute(select(AuditLog).where(AuditLog.investigation_id == inv.id))).scalars().all()
    actions = [a.action for a in audits]
    assert AuditAction.RCA_CAUSE_ADDED.value in actions
    assert AuditAction.RCA_CAUSE_EDITED.value in actions
    assert AuditAction.RCA_CAUSE_VERIFIED.value in actions
    assert AuditAction.RCA_CAUSE_REJECTED.value in actions


@pytest.mark.asyncio
async def test_service_qa_acceptance_and_version_supersession(
    db_session: AsyncSession, setup_rca_environment: Dict[str, Any]
):
    env = setup_rca_environment
    inv = env["investigation"]
    qa_user = env["qa_user"]
    doc = env["document"]

    mock_payload = build_mock_structured_rca(doc.id)
    provider = MockAIProvider(structured_data=mock_payload)

    # First RCA run
    rca1 = await rca_service.start_rca(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=RCARequest(use_documents=False),
        provider_override=provider,
    )

    # QA Accepts first RCA
    accepted1 = await rca_service.accept_rca(
        session=db_session,
        user=qa_user,
        rca_id=rca1.id,
        request=RCAAcceptRequest(reviewer_notes="QA Review Complete. Root cause confirmed."),
    )
    assert accepted1.status == RCAStatus.ACCEPTED.value

    # Second RCA run
    rca2 = await rca_service.start_rca(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=RCARequest(use_documents=False),
        provider_override=provider,
    )
    assert rca2.analysis_version == 2

    # QA Accepts second RCA -> supersedes first RCA
    accepted2 = await rca_service.accept_rca(
        session=db_session,
        user=qa_user,
        rca_id=rca2.id,
        request=RCAAcceptRequest(reviewer_notes="Re-analysis with valve maintenance records."),
    )
    assert accepted2.status == RCAStatus.ACCEPTED.value

    # Verify rca1 is now SUPERSEDED
    reloaded1 = await rca_repo.get(db_session, rca1.id)
    assert reloaded1.status == RCAStatus.SUPERSEDED.value

    # Verify history endpoint provides complete audit and version trail
    history = await rca_service.get_rca_history(db_session, rca2.id)
    assert len(history["versions"]) == 2
    assert any(v["status"] == RCAStatus.SUPERSEDED.value for v in history["versions"])
    assert any(v["status"] == RCAStatus.ACCEPTED.value for v in history["versions"])


@pytest.mark.asyncio
async def test_service_request_more_evidence(
    db_session: AsyncSession, setup_rca_environment: Dict[str, Any]
):
    env = setup_rca_environment
    inv = env["investigation"]
    qa_user = env["qa_user"]
    doc = env["document"]

    mock_payload = build_mock_structured_rca(doc.id)
    provider = MockAIProvider(structured_data=mock_payload)

    rca = await rca_service.start_rca(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=RCARequest(use_documents=False),
        provider_override=provider,
    )

    updated = await rca_service.request_evidence(
        session=db_session,
        user=qa_user,
        rca_id=rca.id,
        request=RCAEvidenceRequest(
            evidence_requested="Need calibration certs for CV-302 actuator and PLC temperature transmitter TT-302.",
            priority="High",
        ),
    )
    assert updated.status == RCAStatus.NEEDS_MORE_EVIDENCE.value
    assert len(updated.evidence_gaps_data) >= 1
    assert "calibration certs for CV-302" in updated.evidence_gaps_data[-1]["description"]


# ===========================================================================
# 3. HTTP API Endpoints & RBAC Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_api_rca_flow_and_sub_structures(
    client: AsyncClient,
    db_session: AsyncSession,
    setup_rca_environment: Dict[str, Any],
    monkeypatch,
):
    env = setup_rca_environment
    inv = env["investigation"]
    inv_user = env["inv_user"]
    doc = env["document"]

    # Authenticate as Investigator
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": inv_user.email, "password": "Secret123!"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Configure AI service provider with deterministic MockAIProvider
    mock_payload = build_mock_structured_rca(doc.id)
    mock_provider = MockAIProvider(structured_data=mock_payload)
    import app.ai.services.ai_service as ai_service_mod
    ai_service_mod.get_ai_service().set_provider(mock_provider)

    # 1. POST /api/v1/investigations/{investigation_id}/ai/rca
    start_res = await client.post(
        f"/api/v1/investigations/{inv.id}/ai/rca",
        json={"analysis_method": "Hybrid", "use_documents": True},
        headers=headers,
    )
    assert start_res.status_code == 201
    rca_data = start_res.json()
    rca_id = rca_data["id"]
    assert rca_data["analysis_version"] == 1
    assert rca_data["status"] == RCAStatus.AI_ANALYSIS_COMPLETED.value

    # 2. GET /api/v1/investigations/{investigation_id}/rca
    list_res = await client.get(f"/api/v1/investigations/{inv.id}/rca", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. GET /api/v1/rca/{rca_id}
    detail_res = await client.get(f"/api/v1/rca/{rca_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == rca_id

    # 4. GET /api/v1/rca/{rca_id}/five-whys
    whys_res = await client.get(f"/api/v1/rca/{rca_id}/five-whys", headers=headers)
    assert whys_res.status_code == 200
    assert len(whys_res.json()) == 3

    # 5. GET /api/v1/rca/{rca_id}/fishbone
    fishbone_res = await client.get(f"/api/v1/rca/{rca_id}/fishbone", headers=headers)
    assert fishbone_res.status_code == 200
    assert Fishbone6MCategory.MACHINE.value in fishbone_res.json()

    # 6. GET /api/v1/rca/{rca_id}/review
    review_res = await client.get(f"/api/v1/rca/{rca_id}/review", headers=headers)
    assert review_res.status_code == 200
    assert review_res.json()["incident_snapshot"]["api_product_name"] == "Pregabalin Active Substance"

    # 7. POST /api/v1/rca/{rca_id}/causes (Manual cause addition)
    add_cause_res = await client.post(
        f"/api/v1/rca/{rca_id}/causes",
        json={
            "category": "Material",
            "title": "Chilled Glycol Impurity",
            "description": "Contamination in glycol coolant line caused partial heat exchange obstruction.",
            "classification": "Contributing Factor",
        },
        headers=headers,
    )
    assert add_cause_res.status_code == 201
    added_cause_id = add_cause_res.json()["cause_id"]

    # 8. POST /api/v1/rca/{rca_id}/causes/{cause_id}/verify
    verify_res = await client.post(
        f"/api/v1/rca/{rca_id}/causes/{added_cause_id}/verify",
        json={"verification_notes": "Coolant samples confirmed visual particulates.", "is_root_cause": False},
        headers=headers,
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["verification_status"] == CauseStatus.VERIFIED.value

    # 9. POST /api/v1/rca/{rca_id}/accept
    accept_res = await client.post(
        f"/api/v1/rca/{rca_id}/accept",
        json={"reviewer_notes": "Accepted by Investigation Team."},
        headers=headers,
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == RCAStatus.ACCEPTED.value

    # 10. GET /api/v1/rca/{rca_id}/history
    history_res = await client.get(f"/api/v1/rca/{rca_id}/history", headers=headers)
    assert history_res.status_code == 200
    assert len(history_res.json()["versions"]) >= 1


@pytest.mark.asyncio
async def test_api_rca_rbac_forbidden_for_operator(
    client: AsyncClient,
    db_session: AsyncSession,
    setup_rca_environment: Dict[str, Any],
):
    env = setup_rca_environment
    inv = env["investigation"]
    operator_user = env["operator_user"]

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": operator_user.email, "password": "Secret123!"},
    )
    assert login_res.status_code == 200
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # Operator cannot initiate RCA
    start_res = await client.post(
        f"/api/v1/investigations/{inv.id}/ai/rca",
        json={"analysis_method": "Hybrid"},
        headers=headers,
    )
    assert start_res.status_code == 403
    assert "Access denied" in start_res.json()["detail"]
