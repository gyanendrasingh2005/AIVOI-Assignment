import uuid
import pytest
import pytest_asyncio
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
    EvidenceGapStatus,
    EvidenceGapPriority,
    GapCategory,
    GapDetectionType,
    CompletenessDimensionStatus,
    CompletenessOverallStatus,
    AuditAction,
)
from app.models.user import User, Role
from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.evidence_gap import EvidenceGap
from app.models.completeness import CompletenessAssessment
from app.schemas.evidence_gap import (
    EvidenceGapAssignRequest,
    EvidenceGapRequestEvidenceRequest,
    EvidenceGapAssociateEvidenceRequest,
    EvidenceGapResolveRequest,
    EvidenceGapRejectRequest,
    EvidenceGapWaiveRequest,
    EvidenceGapReopenRequest,
    EvidenceGapPatchRequest,
)
from app.cli import seed_standard_roles
from app.repositories.user_repository import user_repo
from app.repositories.investigation_repository import investigation_repo
from app.repositories.evidence_gap_repository import evidence_gap_repo
from app.repositories.completeness_repository import completeness_repo
from app.services.evidence_gap_service import evidence_gap_service
from app.services.evidence_requirement_service import evidence_requirement_service
from app.ai.providers.mock_provider import MockAIProvider
import app.ai.services.ai_service as ai_service_mod
from app.ai.graphs.gap_nodes import (
    validate_gap_request_node,
    prepare_gap_context_node,
    load_requirement_profile_node,
    validate_evidence_references_node,
    prioritize_and_consolidate_gaps_node,
    calculate_completeness_node,
)


def build_mock_structured_gap_assessment(doc_id: str, ev_id: str) -> Dict[str, Any]:
    return {
        "overall_status": CompletenessOverallStatus.PARTIALLY_COMPLETE.value,
        "completeness_score": 75.0,
        "summary": "Investigation is partially complete with good incident description and batch records, but missing equipment calibration certificates and maintenance logs.",
        "dimensions": [
            {
                "dimension_name": "Incident information",
                "status": CompletenessDimensionStatus.COMPLETE.value,
                "explanation": "Incident facts, batch number, equipment tag, and actual parameters are confirmed.",
                "missing_information": [],
                "recommended_next_steps": [],
            },
            {
                "dimension_name": "Document availability",
                "status": CompletenessDimensionStatus.COMPLETE.value,
                "explanation": "Batch manufacturing record was uploaded and parsed.",
                "missing_information": [],
                "recommended_next_steps": [],
            },
            {
                "dimension_name": "Evidence traceability",
                "status": CompletenessDimensionStatus.PARTIALLY_COMPLETE.value,
                "explanation": "Chromatographic integration report verified; calibration certificate unverified.",
                "missing_information": ["Calibration report for temperature sensor TT-302"],
                "recommended_next_steps": ["Upload calibration log sheet."],
            },
            {
                "dimension_name": "Manufacturing process evidence",
                "status": CompletenessDimensionStatus.COMPLETE.value,
                "explanation": "Process parameter excursions corroborated by DCS trend data.",
                "missing_information": [],
                "recommended_next_steps": [],
            },
            {
                "dimension_name": "Equipment evidence",
                "status": CompletenessDimensionStatus.INCOMPLETE.value,
                "explanation": "Missing calibration certificate and maintenance history for reactor cooling loop.",
                "missing_information": ["Calibration log", "Preventive maintenance work order"],
                "recommended_next_steps": ["Retrieve calibration certificate from maintenance archives."],
            },
            {
                "dimension_name": "Material and batch evidence",
                "status": CompletenessDimensionStatus.COMPLETE.value,
                "explanation": "API lot genealogy and raw material lot numbers are documented.",
                "missing_information": [],
                "recommended_next_steps": [],
            },
            {
                "dimension_name": "Quality impact assessment",
                "status": CompletenessDimensionStatus.COMPLETE.value,
                "explanation": "Risk assessment completed and accepted by QA.",
                "missing_information": [],
                "recommended_next_steps": [],
            },
            {
                "dimension_name": "5 Whys completeness",
                "status": CompletenessDimensionStatus.COMPLETE.value,
                "explanation": "Sequential inquiry established failure down to pneumatic actuator.",
                "missing_information": [],
                "recommended_next_steps": [],
            },
            {
                "dimension_name": "Fishbone completeness",
                "status": CompletenessDimensionStatus.COMPLETE.value,
                "explanation": "6M decomposition performed across all categories.",
                "missing_information": [],
                "recommended_next_steps": [],
            },
            {
                "dimension_name": "Root cause verification",
                "status": CompletenessDimensionStatus.PARTIALLY_COMPLETE.value,
                "explanation": "Actuator failure is verified; pre-operation calibration check gap remains unverified.",
                "missing_information": ["Pre-operation verification log"],
                "recommended_next_steps": ["Review logbook sign-offs."],
            },
            {
                "dimension_name": "Investigation review completeness",
                "status": CompletenessDimensionStatus.PARTIALLY_COMPLETE.value,
                "explanation": "Investigation pending final human review of evidence gaps.",
                "missing_information": [],
                "recommended_next_steps": ["Complete gap closure and QA review."],
            },
        ],
        "detected_gaps": [
            {
                "gap_title": "Missing Calibration Certificate for TT-302",
                "category": GapCategory.EQUIPMENT.value,
                "detection_type": GapDetectionType.MISSING_EVIDENCE.value,
                "priority": EvidenceGapPriority.HIGH.value,
                "description": "Temperature transmitter TT-302 lacks contemporary calibration certification.",
                "why_needed": "21 CFR 211.68 requires verification of sensor accuracy for critical process parameters.",
                "affected_area": "Equipment Qualification & Process Temperature Monitoring",
                "recommended_evidence_type": "Calibration Certificate",
                "recommended_action": "Obtain certified calibration record from metrology department.",
                "confidence": 0.95,
                "supporting_references": [
                    {
                        "document_id": doc_id,
                        "filename": "batch_record.txt",
                        "page_number": 1,
                        "excerpt": "Temperature reached 48.5 °C measured by TT-302.",
                        "relevance_reason": "Direct batch record reference",
                    }
                ],
            },
            {
                "gap_title": "Missing Reactor Maintenance Log Sheet",
                "category": GapCategory.EQUIPMENT.value,
                "detection_type": GapDetectionType.MISSING_EVIDENCE.value,
                "priority": EvidenceGapPriority.MEDIUM.value,
                "description": "Reactor RX-302 preventive maintenance work orders for past 90 days not attached.",
                "why_needed": "Necessary to rule out pre-existing mechanical wear on cooling jacket control valve.",
                "affected_area": "Machine & Equipment Maintenance",
                "recommended_evidence_type": "Maintenance Work Order",
                "recommended_action": "Retrieve maintenance history for cooling valve CV-302.",
                "confidence": 0.88,
                "supporting_references": [
                    {
                        "document_id": doc_id,
                        "filename": "batch_record.txt",
                        "page_number": 1,
                        "excerpt": "Pneumatic valve CV-302 failed in closed position.",
                        "relevance_reason": "Failed component mention",
                    }
                ],
            },
        ],
        "conflicting_evidence": [],
        "recommended_activities": [
            "Request metrology calibration certificate for sensor TT-302.",
            "Retrieve maintenance work order history for valve CV-302.",
        ],
    }


@pytest_asyncio.fixture
async def setup_gap_env(db_session: AsyncSession):
    await seed_standard_roles(db_session)

    res_qa = await db_session.execute(select(Role).where(Role.name == RoleName.QA.value))
    qa_role = res_qa.scalar_one()

    res_inv = await db_session.execute(select(Role).where(Role.name == RoleName.INVESTIGATOR.value))
    inv_role = res_inv.scalar_one()

    res_op = await db_session.execute(select(Role).where(Role.name == RoleName.MANUFACTURING_OPERATOR.value))
    op_role = res_op.scalar_one()

    qa_user = User(
        id=str(uuid.uuid4()),
        email="qa.gap@example.com",
        full_name="Quality Auditor",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    qa_user.roles.append(qa_role)

    inv_user = User(
        id=str(uuid.uuid4()),
        email="inv.gap@example.com",
        full_name="Lead Investigator",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    inv_user.roles.append(inv_role)

    op_user = User(
        id=str(uuid.uuid4()),
        email="operator.gap@example.com",
        full_name="Shift Operator",
        hashed_password=get_password_hash("Secret123!"),
        is_active=True,
    )
    op_user.roles.append(op_role)

    db_session.add_all([qa_user, inv_user, op_user])
    await db_session.flush()

    investigation = Investigation(
        id=str(uuid.uuid4()),
        investigation_number=f"INV-GAP-{uuid.uuid4().hex[:6].upper()}",
        title="Pregabalin Temperature Excursion Gap Assessment",
        description="Temperature deviation during purification step.",
        status=InvestigationStatus.UNDER_INVESTIGATION.value,
        risk_level=RiskLevel.MAJOR.value,
        priority=PriorityLevel.HIGH.value,
        created_by=inv_user.id,
        assigned_to=inv_user.id,
    )
    db_session.add(investigation)
    await db_session.flush()

    incident = Incident(
        id=str(uuid.uuid4()),
        investigation_id=investigation.id,
        api_product_name="Pregabalin API",
        batch_number="PGB-2026-0099",
        manufacturing_stage="Purification & Final Crystallization",
        incident_date=datetime.now(timezone.utc),
        equipment_id="RX-302",
        expected_parameter="Temperature 20.0 - 25.0 °C",
        actual_parameter="Temperature reached 48.5 °C",
        incident_description="Crystallization cooling interrupted; jacket temperature spiked to 48.5 °C.",
        immediate_actions="Paused process; notified QA.",
        affected_batches=["PGB-2026-0099"],
        potential_quality_impact="Polymorphic purity degradation.",
    )
    db_session.add(incident)

    doc = Document(
        id=str(uuid.uuid4()),
        investigation_id=investigation.id,
        original_filename="batch_record.txt",
        stored_filename="stored_batch_record.txt",
        file_type="text/plain",
        file_size=2048,
        storage_path="documents/batch_record.txt",
        extracted_text="Temperature reached 48.5 °C measured by TT-302. Pneumatic valve CV-302 failed in closed position.",
        processing_status="Completed",
        uploaded_by=inv_user.id,
        uploaded_at=datetime.now(timezone.utc),
    )
    db_session.add(doc)

    evidence = Evidence(
        id=str(uuid.uuid4()),
        investigation_id=investigation.id,
        document_id=doc.id,
        title="DCS Historical Trend",
        evidence_type="Process Trend",
        verification_status="Verified",
        description="Recorded 45-minute temperature excursion.",
        uploaded_by=inv_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(evidence)
    await db_session.commit()

    return {
        "qa_user": qa_user,
        "inv_user": inv_user,
        "op_user": op_user,
        "investigation": investigation,
        "incident": incident,
        "document": doc,
        "evidence": evidence,
    }


# =========================================================================
# Node-Level Unit Tests
# =========================================================================

@pytest.mark.asyncio
async def test_validate_gap_request_node():
    res_fail = await validate_gap_request_node({"investigation_id": ""})
    assert res_fail["is_failed"] is True
    assert "investigation_id is required" in res_fail["error_message"]

    res_ok = await validate_gap_request_node({"investigation_id": "inv-123", "requirement_profile_version": "1.0.0"})
    assert res_ok["is_failed"] is False
    assert res_ok["requirement_profile_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_prepare_gap_context_node(db_session: AsyncSession, setup_gap_env):
    env = setup_gap_env
    inv = env["investigation"]

    state = {
        "investigation_id": inv.id,
        "user_id": env["inv_user"].id,
        "requirement_profile_version": "1.0.0",
        "is_failed": False,
    }
    updated = await prepare_gap_context_node(state, session=db_session)
    assert not updated.get("is_failed")
    ctx = updated["context_data"]
    assert ctx["investigation_id"] == inv.id
    assert ctx["incident"]["batch_number"] == "PGB-2026-0099"
    assert len(ctx["documents"]) == 1
    assert len(ctx["evidence"]) == 1
    assert "PGB-2026-0099" in updated["compiled_prompt_context"]


@pytest.mark.asyncio
async def test_load_requirement_profile_node():
    ctx = {
        "incident": {
            "batch_number": "BATCH-01",
            "equipment_id": "RX-101",
        }
    }
    state = {
        "is_failed": False,
        "requirement_profile_version": "1.0.0",
        "context_data": ctx,
    }
    updated = await load_requirement_profile_node(state)
    assert len(updated["applicable_rules"]) >= 5
    codes = [r["code"] for r in updated["applicable_rules"]]
    assert "DOC_BATCH_RECORD" in codes
    assert "EQP_CALIBRATION_STATUS" in codes
    assert "EQP_CALIBRATION_STATUS" in updated["compiled_rules_text"]


@pytest.mark.asyncio
async def test_validate_evidence_references_strips_hallucinated_ids():
    valid_doc_id = str(uuid.uuid4())
    fake_doc_id = str(uuid.uuid4())
    fake_ev_id = str(uuid.uuid4())

    state = {
        "is_failed": False,
        "context_data": {
            "documents": [{"document_id": valid_doc_id}],
            "evidence": [],
        },
        "detected_gaps": [
            {
                "gap_title": "Missing Record",
                "supporting_references": [
                    {"document_id": valid_doc_id, "evidence_id": None, "relevance_reason": "Real Doc"},
                    {"document_id": fake_doc_id, "evidence_id": fake_ev_id, "relevance_reason": "Hallucinated Doc"},
                ],
            }
        ],
    }

    updated = await validate_evidence_references_node(state)
    gaps = updated["validated_gaps"]
    refs = gaps[0]["supporting_references"]
    assert refs[0]["document_id"] == valid_doc_id
    assert refs[1]["document_id"] is None
    assert "(Unverified Citation)" in refs[1]["relevance_reason"]


@pytest.mark.asyncio
async def test_prioritize_and_consolidate_gaps_node():
    state = {
        "is_failed": False,
        "context_data": {
            "rca": {
                "root_causes": [{"id": "rc-1", "title": "Cooling Valve Seizure"}]
            }
        },
        "validated_gaps": [
            {
                "gap_title": "Valve Maintenance",
                "description": "Lack of maintenance records for Cooling Valve Seizure.",
                "priority": "high",
                "category": "equipment",
            }
        ],
    }

    updated = await prioritize_and_consolidate_gaps_node(state)
    gap = updated["validated_gaps"][0]
    assert gap["root_cause_id"] == "rc-1"
    assert gap["priority"] == EvidenceGapPriority.HIGH.value
    assert gap["category"] == GapCategory.EQUIPMENT.value


@pytest.mark.asyncio
async def test_calculate_completeness_node():
    state = {
        "is_failed": False,
        "completeness_score": 90.0,
        "context_data": {
            "rca": {"root_causes": [{"title": "RC", "verification_status": "PROPOSED"}]}
        },
        "validated_gaps": [
            {"priority": EvidenceGapPriority.CRITICAL.value},
            {"priority": EvidenceGapPriority.HIGH.value},
        ],
        "conflicting_evidence": [],
    }

    updated = await calculate_completeness_node(state)
    assert updated["critical_unresolved_gaps"] == 1
    assert updated["high_priority_unresolved_gaps"] == 1
    assert updated["total_unresolved_gaps"] == 2
    assert updated["unverified_causal_claims_count"] == 1
    # 90.0 - 20 (critical) - 10 (high) - 10 (unverified RC) = 50.0
    assert updated["completeness_score"] == 50.0
    assert updated["overall_status"] == CompletenessOverallStatus.INCOMPLETE.value


# =========================================================================
# Service-Level Integration Tests
# =========================================================================

@pytest.mark.asyncio
async def test_service_start_evidence_gap_assessment(db_session: AsyncSession, setup_gap_env):
    env = setup_gap_env
    inv = env["investigation"]
    doc = env["document"]
    ev = env["evidence"]

    mock_data = build_mock_structured_gap_assessment(doc.id, ev.id)
    provider = MockAIProvider(model="mock-groq-gap")
    provider.structured_data = mock_data
    ai_service_mod.get_ai_service().set_provider(provider)

    assessment = await evidence_gap_service.start_evidence_gap_assessment(
        db_session,
        investigation_id=inv.id,
        user_id=env["inv_user"].id,
        requirement_profile_version="1.0.0",
    )

    assert assessment.id is not None
    assert assessment.investigation_id == inv.id
    assert assessment.assessment_version == 1
    assert len(assessment.dimension_results) == 11
    assert assessment.total_unresolved_gaps == 2

    # Verify gaps were persisted in evidence_gaps table
    gaps, count = await evidence_gap_repo.get_by_investigation(db_session, investigation_id=inv.id)
    assert count == 2
    assert gaps[0].gap_title is not None
    assert gaps[0].status == EvidenceGapStatus.OPEN.value


@pytest.mark.asyncio
async def test_service_gap_human_review_lifecycle(db_session: AsyncSession, setup_gap_env):
    env = setup_gap_env
    inv = env["investigation"]
    qa_user = env["qa_user"]
    inv_user = env["inv_user"]
    evidence = env["evidence"]

    # Create initial gap
    gap = EvidenceGap(
        investigation_id=inv.id,
        gap_title="Calibration Verification Missing",
        description="Sensor TT-302 calibration is missing.",
        reason="Required for process monitoring.",
        category=GapCategory.EQUIPMENT.value,
        priority=EvidenceGapPriority.HIGH.value,
        status=EvidenceGapStatus.OPEN.value,
        associated_evidence_ids=[],
        supporting_references=[],
    )
    db_session.add(gap)
    await db_session.commit()

    # 1. Assign gap
    due = datetime.now(timezone.utc)
    assigned = await evidence_gap_service.assign_evidence_gap(
        db_session, gap_id=gap.id, user_id=qa_user.id, assigned_to=inv_user.id, due_date=due
    )
    assert assigned.assigned_to == inv_user.id

    # 2. Request evidence
    requested = await evidence_gap_service.request_evidence(
        db_session, gap_id=gap.id, user_id=qa_user.id, notes="Please check calibration binder.", suggested_source="Binder 4"
    )
    assert requested.status == EvidenceGapStatus.EVIDENCE_REQUESTED.value
    assert requested.suggested_source == "Binder 4"

    # 3. Associate evidence
    associated = await evidence_gap_service.associate_evidence(
        db_session, gap_id=gap.id, user_id=inv_user.id, evidence_ids=[evidence.id]
    )
    assert evidence.id in associated.associated_evidence_ids
    assert associated.status == EvidenceGapStatus.EVIDENCE_RECEIVED.value

    # 4. Resolve gap
    resolved = await evidence_gap_service.resolve_evidence_gap(
        db_session, gap_id=gap.id, user_id=qa_user.id, justification="Calibration verified in acceptable range.", evidence_ids=[evidence.id]
    )
    assert resolved.status == EvidenceGapStatus.RESOLVED.value
    assert resolved.resolved_by == qa_user.id

    # 5. Reopen gap
    reopened = await evidence_gap_service.reopen_evidence_gap(
        db_session, gap_id=gap.id, user_id=qa_user.id, justification="Subsequent audit revealed sticker expired."
    )
    assert reopened.status == EvidenceGapStatus.REOPENED.value

    # 6. Reject gap
    rejected = await evidence_gap_service.reject_evidence_gap(
        db_session, gap_id=gap.id, user_id=qa_user.id, justification="Not applicable for this equipment type."
    )
    assert rejected.status == EvidenceGapStatus.REJECTED.value

    # 7. Waive gap
    waived = await evidence_gap_service.waive_evidence_gap(
        db_session, gap_id=gap.id, user_id=qa_user.id, justification="Equipment redundant loop used.", policy_reference="SOP-QA-012"
    )
    assert waived.status == EvidenceGapStatus.WAIVED_WITH_JUSTIFICATION.value
    assert "[SOP-QA-012]" in waived.resolution_justification

    # 8. Check audit history
    history = await evidence_gap_service.get_gap_history(db_session, gap_id=gap.id)
    assert len(history) >= 7


# =========================================================================
# API Endpoints & RBAC Integration Tests
# =========================================================================

@pytest.mark.asyncio
async def test_api_gap_assessment_and_listing_flow(client: AsyncClient, db_session: AsyncSession, setup_gap_env):
    env = setup_gap_env
    inv = env["investigation"]
    doc = env["document"]
    ev = env["evidence"]
    inv_user = env["inv_user"]
    qa_user = env["qa_user"]

    mock_data = build_mock_structured_gap_assessment(doc.id, ev.id)
    provider = MockAIProvider(model="mock-groq-gap")
    provider.structured_data = mock_data
    ai_service_mod.get_ai_service().set_provider(provider)

    # Login as investigator
    res_login = await client.post(
        "/api/v1/auth/login",
        json={"email": inv_user.email, "password": "Secret123!"},
    )
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Trigger assessment
    res_assess = await client.post(
        f"/api/v1/investigations/{inv.id}/ai/evidence-gap-assessment",
        json={"requirement_profile": "1.0.0"},
        headers=headers,
    )
    assert res_assess.status_code == 201
    assess_data = res_assess.json()
    assert assess_data["investigation_id"] == inv.id
    assert assess_data["assessment_version"] == 1
    assert len(assess_data["dimension_results"]) == 11

    # 2. Get latest completeness
    res_comp = await client.get(
        f"/api/v1/investigations/{inv.id}/completeness",
        headers=headers,
    )
    assert res_comp.status_code == 200
    assert res_comp.json()["assessment_version"] == 1

    # 3. List gaps with filter
    res_gaps = await client.get(
        f"/api/v1/investigations/{inv.id}/evidence-gaps?category=EQUIPMENT",
        headers=headers,
    )
    assert res_gaps.status_code == 200
    gaps_list = res_gaps.json()
    assert gaps_list["total"] == 2
    gap_id = gaps_list["items"][0]["id"]

    # 4. Patch gap metadata
    res_patch = await client.patch(
        f"/api/v1/evidence-gaps/{gap_id}",
        json={"gap_title": "Updated Calibration Title"},
        headers=headers,
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["gap_title"] == "Updated Calibration Title"

    # Login as QA for resolution
    res_login_qa = await client.post(
        "/api/v1/auth/login",
        json={"email": qa_user.email, "password": "Secret123!"},
    )
    assert res_login_qa.status_code == 200
    qa_token = res_login_qa.json()["access_token"]
    qa_headers = {"Authorization": f"Bearer {qa_token}"}

    # 5. Resolve gap
    res_res = await client.post(
        f"/api/v1/evidence-gaps/{gap_id}/resolve",
        json={"justification": "Calibration certificate verified in metrology archive."},
        headers=qa_headers,
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == EvidenceGapStatus.RESOLVED.value

    # 6. Check history
    res_hist = await client.get(
        f"/api/v1/evidence-gaps/{gap_id}/history",
        headers=headers,
    )
    assert res_hist.status_code == 200
    assert len(res_hist.json()) >= 1


@pytest.mark.asyncio
async def test_api_rbac_operator_forbidden(client: AsyncClient, db_session: AsyncSession, setup_gap_env):
    env = setup_gap_env
    inv = env["investigation"]
    op_user = env["op_user"]

    # Login as operator
    res_login = await client.post(
        "/api/v1/auth/login",
        json={"email": op_user.email, "password": "Secret123!"},
    )
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Operator cannot trigger gap assessment
    res_assess = await client.post(
        f"/api/v1/investigations/{inv.id}/ai/evidence-gap-assessment",
        json={"requirement_profile": "1.0.0"},
        headers=headers,
    )
    assert res_assess.status_code == 403
