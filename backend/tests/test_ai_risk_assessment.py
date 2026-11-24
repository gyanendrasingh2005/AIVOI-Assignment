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
    RiskClassification,
    RiskLikelihood,
    RiskDetectability,
    InvestigationUrgency,
    RiskAssessmentStatus,
    RiskAssessmentReviewStatus,
    AuditAction,
)
from app.models.user import User, Role
from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.document import Document
from app.models.audit import AuditLog
from app.models.risk_assessment import RiskAssessment
from app.models.incident_extraction import IncidentExtraction
from app.schemas.user import UserCreate
from app.schemas.risk_assessment import (
    RiskAssessmentRequest,
    RiskAssessmentReviewPatchRequest,
    RiskAssessmentAcceptRequest,
    RiskAssessmentRejectRequest,
    RiskAssessmentInfoRequest,
    RiskAssessmentStructuredOutput,
)
from app.cli import seed_standard_roles
from app.repositories.user_repository import user_repo
from app.repositories.investigation_repository import investigation_repo, incident_repo
from app.repositories.risk_assessment_repository import risk_assessment_repo
from app.repositories.incident_extraction_repository import incident_extraction_repo
from app.services.risk_assessment_service import risk_assessment_service
from app.core.risk_framework import RiskFramework
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.graphs.risk_builder import create_risk_assessment_graph
from app.ai.graphs.risk_state import RiskAssessmentWorkflowState


def build_mock_structured_risk_assessment(doc_id: str) -> Dict[str, Any]:
    return {
        "quality_impact": {
            "status": "Potential impact identified",
            "findings": "High crystallization temperature (48.5 °C) risks polymorphic transformation and elevated impurity levels.",
            "supporting_references": [
                {
                    "document_id": doc_id,
                    "filename": "batch_record.txt",
                    "page_number": 1,
                    "excerpt": "Crystallization temperature reached 48.5 °C during cooling step.",
                    "related_field": "Product Quality Impact",
                    "relevance_reason": "Direct evidence of process temperature excursion exceeding 25 °C limit.",
                }
            ],
            "concerns": ["CQA out of specification risk: Polymorphic purity Form I."],
            "is_unverified": False,
        },
        "patient_impact": {
            "status": "Impact cannot currently be determined",
            "findings": "No clinical toxicity data available for Form II polymorphic variant in this dosage form.",
            "supporting_references": [],
            "concerns": ["Therapeutic bioavailability alteration possible if polymorph dissolves slower."],
            "is_unverified": False,
        },
        "batch_impact": {
            "status": "Confirmed impact documented in source evidence",
            "findings": "Batch PGB-2026-0042 directly affected; subsequent campaign batch PGB-2026-0043 potentially exposed to reactor residue.",
            "supporting_references": [
                {
                    "document_id": doc_id,
                    "filename": "batch_record.txt",
                    "page_number": 1,
                    "excerpt": "Affected Batches: PGB-2026-0042, PGB-2026-0043",
                    "related_field": "Batch & Material Impact",
                    "relevance_reason": "Source document explicitly lists two affected production lots.",
                }
            ],
            "concerns": ["Cross-batch seeding in reactor RX-302."],
            "is_unverified": False,
        },
        "process_impact": {
            "status": "Confirmed impact documented in source evidence",
            "findings": "Cooling ramp parameter deviation exceeded validated boundary by 23.5 °C.",
            "supporting_references": [],
            "concerns": ["Validated recipe step exceeded."],
            "is_unverified": False,
        },
        "equipment_impact": {
            "status": "No evidence identified",
            "findings": "Reactor RX-302 chiller valve reported responsive; mechanical inspection pending.",
            "supporting_references": [],
            "concerns": [],
            "is_unverified": False,
        },
        "data_integrity_impact": {
            "status": "No evidence identified",
            "findings": "SCADA audit trail confirms timely recording of excursion at 14:15 UTC without manual overwrites.",
            "supporting_references": [],
            "concerns": [],
            "is_unverified": False,
        },
        "severity": "Critical",
        "likelihood": "High",
        "detectability": "Low",
        "overall_risk": "Critical",
        "risk_rationale": "High temperature excursion in crystallization stage with confirmed OOS risk and multi-batch potential.",
        "urgency_recommendation": "Immediate Quality Review",
        "supporting_references": [
            {
                "document_id": doc_id,
                "filename": "batch_record.txt",
                "page_number": 1,
                "excerpt": "Crystallization temperature reached 48.5 °C during cooling step.",
                "related_field": "overall",
                "relevance_reason": "Core deviation evidence.",
            }
        ],
        "missing_information": [
            {
                "field_name": "chiller_maintenance_log",
                "description": "Preventative maintenance log for chiller bypass valve not provided.",
                "risk_implication": "Cannot verify if valve sticking was a recurring failure.",
            }
        ],
        "conflicting_evidence": [],
        "uncertainty_notes": "Patient impact cannot be fully evaluated until HPLC dissolution profile is complete.",
        "confidence_score": 0.95,
    }


@pytest.fixture
async def setup_risk_environment(db_session: AsyncSession, client: AsyncClient):
    roles = await seed_standard_roles(db_session)
    qa_role = roles[RoleName.QA.value]
    inv_role = roles[RoleName.INVESTIGATOR.value]
    operator_role = roles[RoleName.MANUFACTURING_OPERATOR.value]

    qa_user = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="Quality Assurance Lead",
            email="qa.lead@pharma.com",
            is_active=True,
            password="Password123!",
            role_ids=[qa_role.id],
        ),
        hashed_password=get_password_hash("Password123!"),
    )

    inv_user = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="Principal Investigator",
            email="investigator@pharma.com",
            is_active=True,
            password="Password123!",
            role_ids=[inv_role.id],
        ),
        hashed_password=get_password_hash("Password123!"),
    )

    other_user = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="Other Facility Operator",
            email="other.operator@pharma.com",
            is_active=True,
            password="Password123!",
            role_ids=[operator_role.id],
        ),
        hashed_password=get_password_hash("Password123!"),
    )

    # Login QA user
    qa_login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "qa.lead@pharma.com", "password": "Password123!"},
    )
    qa_token = qa_login_resp.json()["access_token"]
    qa_headers = {"Authorization": f"Bearer {qa_token}"}

    # Login Investigator user
    inv_login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "investigator@pharma.com", "password": "Password123!"},
    )
    inv_token = inv_login_resp.json()["access_token"]
    inv_headers = {"Authorization": f"Bearer {inv_token}"}

    # Login Other user
    other_login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "other.operator@pharma.com", "password": "Password123!"},
    )
    other_token = other_login_resp.json()["access_token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Create Investigation & confirmed Incident
    investigation = Investigation(
        investigation_number="INV-2026-0099",
        title="Pregabalin Crystallization Excursion Investigation",
        description="Temperature excursion observed during cooling ramp in reactor RX-302.",
        status=InvestigationStatus.UNDER_INVESTIGATION.value,
        priority=PriorityLevel.MEDIUM.value,
        risk_level=RiskLevel.MAJOR.value,
        created_by=inv_user.id,
        assigned_to=inv_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(investigation)
    await db_session.flush()

    incident = Incident(
        investigation_id=investigation.id,
        api_product_name="Pregabalin Crystalline",
        batch_number="PGB-2026-0042",
        manufacturing_stage="Final Crystallization",
        incident_date=datetime.now(timezone.utc),
        incident_description="Crystallization temperature reached 48.5 °C during cooling step.",
        equipment_id="RX-302",
        expected_parameter="22.0 °C to 25.0 °C",
        actual_parameter="48.5 °C",
        immediate_actions="Automated chiller cooling bypass engaged immediately.",
        affected_batches=["PGB-2026-0042", "PGB-2026-0043"],
        potential_quality_impact="Polymorphic purity compromised.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(incident)

    # Document
    doc = Document(
        investigation_id=investigation.id,
        original_filename="batch_record.txt",
        stored_filename="stored_batch_record.txt",
        file_type="text/plain",
        file_size=1024,
        storage_path="/tmp/stored_batch_record.txt",
        extracted_text="Crystallization temperature reached 48.5 °C during cooling step. Affected Batches: PGB-2026-0042, PGB-2026-0043",
        processing_status="Completed",
        uploaded_by=inv_user.id,
        uploaded_at=datetime.now(timezone.utc),
    )
    db_session.add(doc)
    await db_session.flush()

    return {
        "qa_user": qa_user,
        "inv_user": inv_user,
        "other_user": other_user,
        "qa_headers": qa_headers,
        "inv_headers": inv_headers,
        "other_headers": other_headers,
        "investigation": investigation,
        "incident": incident,
        "document": doc,
    }


# ===========================================================================
# 1. Unit Tests for RiskFramework
# ===========================================================================

def test_risk_framework_matrix_calculations():
    # Critical Severity mappings
    assert (
        RiskFramework.calculate_overall_risk(
            RiskClassification.CRITICAL, RiskLikelihood.HIGH
        )
        == RiskClassification.CRITICAL
    )
    assert (
        RiskFramework.calculate_overall_risk(
            RiskClassification.CRITICAL, RiskLikelihood.MEDIUM
        )
        == RiskClassification.CRITICAL
    )
    assert (
        RiskFramework.calculate_overall_risk(
            RiskClassification.CRITICAL, RiskLikelihood.LOW
        )
        == RiskClassification.HIGH
    )

    # High Severity mappings
    assert (
        RiskFramework.calculate_overall_risk(
            RiskClassification.HIGH, RiskLikelihood.HIGH
        )
        == RiskClassification.HIGH
    )
    assert (
        RiskFramework.calculate_overall_risk(
            RiskClassification.HIGH, RiskLikelihood.MEDIUM, RiskDetectability.LOW
        )
        == RiskClassification.HIGH
    )
    assert (
        RiskFramework.calculate_overall_risk(
            RiskClassification.HIGH, RiskLikelihood.LOW
        )
        == RiskClassification.MEDIUM
    )

    # Medium & Minor Severity mappings
    assert (
        RiskFramework.calculate_overall_risk(
            RiskClassification.MEDIUM, RiskLikelihood.HIGH
        )
        == RiskClassification.MEDIUM
    )
    assert (
        RiskFramework.calculate_overall_risk(
            RiskClassification.LOW, RiskLikelihood.LOW
        )
        == RiskClassification.LOW
    )

    # Undetermined handling
    assert (
        RiskFramework.calculate_overall_risk(
            RiskClassification.UNDETERMINED, RiskLikelihood.HIGH
        )
        == RiskClassification.UNDETERMINED
    )


def test_risk_framework_urgency_determinations():
    assert (
        RiskFramework.determine_urgency(RiskClassification.CRITICAL)
        == InvestigationUrgency.IMMEDIATE
    )
    assert (
        RiskFramework.determine_urgency(RiskClassification.HIGH)
        == InvestigationUrgency.URGENT
    )
    assert (
        RiskFramework.determine_urgency(RiskClassification.MEDIUM)
        == InvestigationUrgency.STANDARD
    )
    # Patient impact undetermined elevates urgency
    assert (
        RiskFramework.determine_urgency(
            RiskClassification.MEDIUM, patient_impact_undetermined=True
        )
        == InvestigationUrgency.INFO_REQUIRED
    )
    assert (
        RiskFramework.determine_urgency(
            RiskClassification.CRITICAL, patient_impact_undetermined=True
        )
        == InvestigationUrgency.IMMEDIATE
    )


# ===========================================================================
# 2. LangGraph Workflow Execution Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_risk_graph_execution_with_mock_provider():
    doc_id = str(uuid.uuid4())
    mock_payload = build_mock_structured_risk_assessment(doc_id)
    provider = MockAIProvider(structured_data=mock_payload)
    graph = create_risk_assessment_graph(provider)

    initial_state: RiskAssessmentWorkflowState = {
        "assessment_id": str(uuid.uuid4()),
        "investigation_id": "inv-test-1",
        "incident_snapshot": {
            "api_product_name": "Pregabalin Crystalline",
            "batch_number": "PGB-2026-0042",
            "incident_description": "Excursion observed.",
        },
        "valid_document_map": {doc_id: "batch_record.txt"},
        "document_context": "Sample source evidence excerpt.",
    }

    final_state = await graph.ainvoke(initial_state)

    assert final_state.get("status") == RiskAssessmentStatus.COMPLETED.value
    assert final_state.get("overall_risk") == RiskClassification.CRITICAL.value
    assert final_state.get("urgency_recommendation") == InvestigationUrgency.IMMEDIATE.value

    # Check that all 6 dimensions are populated
    for dim in [
        "quality_impact",
        "patient_impact",
        "batch_impact",
        "process_impact",
        "equipment_impact",
        "data_integrity_impact",
    ]:
        assert dim in final_state
        assert "status" in final_state[dim]
        assert "findings" in final_state[dim]

    # Verify citation preservation
    refs = final_state.get("supporting_references", [])
    assert len(refs) > 0
    assert refs[0]["document_id"] == doc_id
    assert refs[0]["filename"] == "batch_record.txt"


@pytest.mark.asyncio
async def test_risk_graph_citation_validation_strips_hallucinated_ids():
    fake_doc_id = "non-existent-doc-uuid"
    mock_payload = build_mock_structured_risk_assessment(fake_doc_id)
    provider = MockAIProvider(structured_data=mock_payload)
    graph = create_risk_assessment_graph(provider)

    initial_state: RiskAssessmentWorkflowState = {
        "assessment_id": str(uuid.uuid4()),
        "investigation_id": "inv-test-2",
        "incident_snapshot": {"api_product_name": "Pregabalin", "incident_description": "Excursion"},
        "valid_document_map": {},  # empty valid documents
    }

    final_state = await graph.ainvoke(initial_state)

    refs = final_state.get("supporting_references", [])
    assert len(refs) > 0
    # The hallucinated ID was stripped to None and flagged as Unverified Citation
    assert refs[0]["document_id"] is None
    assert "(Unverified Citation)" in refs[0]["relevance_reason"]


@pytest.mark.asyncio
async def test_risk_graph_failure_safe_fallback():
    provider = MockAIProvider(should_timeout=True)
    graph = create_risk_assessment_graph(provider)

    initial_state: RiskAssessmentWorkflowState = {
        "assessment_id": str(uuid.uuid4()),
        "investigation_id": "inv-test-3",
        "incident_snapshot": {"api_product_name": "Pregabalin", "incident_description": "Excursion"},
    }

    final_state = await graph.ainvoke(initial_state)

    assert final_state.get("status") == RiskAssessmentStatus.FAILED.value
    assert final_state.get("overall_risk") == RiskClassification.UNDETERMINED.value
    assert final_state.get("urgency_recommendation") == InvestigationUrgency.INFO_REQUIRED.value
    assert "quality_impact" in final_state
    assert final_state["quality_impact"]["status"] == "Impact cannot currently be determined"


# ===========================================================================
# 3. Service Layer Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_service_start_risk_assessment_from_confirmed_incident(
    db_session: AsyncSession, setup_risk_environment: Dict[str, Any]
):
    env = setup_risk_environment
    inv = env["investigation"]
    doc = env["document"]
    user = env["inv_user"]

    mock_payload = build_mock_structured_risk_assessment(doc.id)
    provider = MockAIProvider(structured_data=mock_payload)

    assessment = await risk_assessment_service.start_risk_assessment(
        session=db_session,
        user=user,
        investigation_id=inv.id,
        request=RiskAssessmentRequest(use_documents=True),
        provider_override=provider,
    )

    assert assessment.id is not None
    assert assessment.investigation_id == inv.id
    assert assessment.status == RiskAssessmentStatus.COMPLETED.value
    assert assessment.overall_risk == RiskClassification.CRITICAL.value
    assert assessment.incident_snapshot["source"] == "confirmed_incident_record"
    assert assessment.incident_snapshot["api_product_name"] == "Pregabalin Crystalline"

    # Verify ALCOA+ Audit Logs
    audit_stmt = (
        select(AuditLog)
        .where(AuditLog.investigation_id == inv.id)
        .order_by(AuditLog.created_at)
    )
    audits = (await db_session.execute(audit_stmt)).scalars().all()
    actions = [a.action for a in audits]
    assert AuditAction.RISK_ASSESSMENT_REQUESTED.value in actions
    assert AuditAction.RISK_ASSESSMENT_COMPLETED.value in actions


@pytest.mark.asyncio
async def test_service_start_risk_assessment_from_draft_extraction(
    db_session: AsyncSession, setup_risk_environment: Dict[str, Any]
):
    env = setup_risk_environment
    inv_user = env["inv_user"]

    # Create investigation without confirmed incident, but with extraction draft
    new_inv = Investigation(
        investigation_number="INV-2026-0100",
        title="Draft Only Investigation",
        status=InvestigationStatus.DRAFT.value,
        priority=PriorityLevel.LOW.value,
        risk_level=RiskLevel.MINOR.value,
        created_by=inv_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(new_inv)
    await db_session.flush()

    extraction = IncidentExtraction(
        investigation_id=new_inv.id,
        source_document_ids=[],
        provider="mock",
        model="mock-model",
        prompt_version="1.0.0",
        status="COMPLETED",
        review_status="PENDING_REVIEW",
        extracted_fields={
            "api_product_name": {"value": "Draft API", "confidence": 0.8},
            "incident_description": {"value": "Draft observed excursion", "confidence": 0.85},
        },
        missing_information=[],
        conflicting_information=[],
        document_summaries=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(extraction)
    await db_session.flush()

    mock_payload = build_mock_structured_risk_assessment("doc-dummy")
    provider = MockAIProvider(structured_data=mock_payload)

    assessment = await risk_assessment_service.start_risk_assessment(
        session=db_session,
        user=inv_user,
        investigation_id=new_inv.id,
        request=RiskAssessmentRequest(use_documents=False),
        provider_override=provider,
    )

    assert assessment.status == RiskAssessmentStatus.COMPLETED.value
    assert assessment.incident_snapshot["source"] == "unconfirmed_ai_extraction_draft"
    assert assessment.incident_snapshot["api_product_name"] == "Draft API"


@pytest.mark.asyncio
async def test_service_start_risk_assessment_missing_incident_raises_400(
    db_session: AsyncSession, setup_risk_environment: Dict[str, Any]
):
    env = setup_risk_environment
    inv_user = env["inv_user"]

    empty_inv = Investigation(
        investigation_number="INV-EMPTY-001",
        title="Empty Investigation",
        created_by=inv_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(empty_inv)
    await db_session.flush()

    with pytest.raises(Exception) as exc_info:
        await risk_assessment_service.start_risk_assessment(
            session=db_session,
            user=inv_user,
            investigation_id=empty_inv.id,
            request=RiskAssessmentRequest(),
        )
    assert "no incident information or intake data found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_service_human_qa_review_view_and_patch(
    db_session: AsyncSession, setup_risk_environment: Dict[str, Any]
):
    env = setup_risk_environment
    inv = env["investigation"]
    qa_user = env["qa_user"]

    mock_payload = build_mock_structured_risk_assessment("doc-1")
    provider = MockAIProvider(structured_data=mock_payload)

    assessment = await risk_assessment_service.start_risk_assessment(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=RiskAssessmentRequest(use_documents=False),
        provider_override=provider,
    )

    # Review View
    review_view = await risk_assessment_service.get_review_view(db_session, assessment.id)
    assert review_view.assessment.id == assessment.id
    assert "dimensions" in review_view.matrix_metadata
    assert not review_view.has_unreviewed_incident_data

    # Patch Review (Human override & notes)
    patched = await risk_assessment_service.update_review(
        session=db_session,
        user=qa_user,
        assessment_id=assessment.id,
        request=RiskAssessmentReviewPatchRequest(
            reviewer_notes="Investigator confirmed preliminary review.",
            overall_risk_override=RiskClassification.HIGH,
        ),
    )

    assert patched.overall_risk == RiskClassification.HIGH.value
    assert patched.reviewer_notes == "Investigator confirmed preliminary review."


@pytest.mark.asyncio
async def test_service_qa_acceptance_and_investigation_sync(
    db_session: AsyncSession, setup_risk_environment: Dict[str, Any]
):
    env = setup_risk_environment
    inv = env["investigation"]
    qa_user = env["qa_user"]

    mock_payload = build_mock_structured_risk_assessment("doc-1")
    provider = MockAIProvider(structured_data=mock_payload)

    # First assessment
    assessment1 = await risk_assessment_service.start_risk_assessment(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=RiskAssessmentRequest(use_documents=False),
        provider_override=provider,
    )

    # QA Accepts assessment1 and synchronizes investigation
    accepted1 = await risk_assessment_service.accept_assessment(
        session=db_session,
        user=qa_user,
        assessment_id=assessment1.id,
        request=RiskAssessmentAcceptRequest(apply_to_investigation=True, reviewer_notes="Formal QA Acceptance"),
    )

    assert accepted1.review_status == RiskAssessmentReviewStatus.ACCEPTED.value

    # Verify investigation record synchronized
    updated_inv = await investigation_repo.get(db_session, inv.id)
    assert updated_inv.risk_level == RiskLevel.CRITICAL.value
    assert updated_inv.priority == PriorityLevel.CRITICAL.value

    # Create a second assessment and accept it -> supersedes first
    assessment2 = await risk_assessment_service.start_risk_assessment(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=RiskAssessmentRequest(use_documents=False),
        provider_override=provider,
    )
    await risk_assessment_service.accept_assessment(
        session=db_session,
        user=qa_user,
        assessment_id=assessment2.id,
        request=RiskAssessmentAcceptRequest(apply_to_investigation=True),
    )

    # Reload assessment1
    reloaded1 = await risk_assessment_repo.get(db_session, assessment1.id)
    assert reloaded1.review_status == RiskAssessmentReviewStatus.SUPERSEDED.value


@pytest.mark.asyncio
async def test_service_qa_rejection_leaves_investigation_unchanged(
    db_session: AsyncSession, setup_risk_environment: Dict[str, Any]
):
    env = setup_risk_environment
    inv = env["investigation"]
    qa_user = env["qa_user"]

    orig_risk = inv.risk_level
    orig_priority = inv.priority

    mock_payload = build_mock_structured_risk_assessment("doc-1")
    provider = MockAIProvider(structured_data=mock_payload)

    assessment = await risk_assessment_service.start_risk_assessment(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=RiskAssessmentRequest(use_documents=False),
        provider_override=provider,
    )

    rejected = await risk_assessment_service.reject_assessment(
        session=db_session,
        user=qa_user,
        assessment_id=assessment.id,
        request=RiskAssessmentRejectRequest(reason="Methodology inconclusive; repeated testing required."),
    )

    assert rejected.review_status == RiskAssessmentReviewStatus.REJECTED.value

    # Investigation remains completely untouched
    refreshed_inv = await investigation_repo.get(db_session, inv.id)
    assert refreshed_inv.risk_level == orig_risk
    assert refreshed_inv.priority == orig_priority


@pytest.mark.asyncio
async def test_service_request_additional_information(
    db_session: AsyncSession, setup_risk_environment: Dict[str, Any]
):
    env = setup_risk_environment
    inv = env["investigation"]
    qa_user = env["qa_user"]

    mock_payload = build_mock_structured_risk_assessment("doc-1")
    provider = MockAIProvider(structured_data=mock_payload)

    assessment = await risk_assessment_service.start_risk_assessment(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=RiskAssessmentRequest(use_documents=False),
        provider_override=provider,
    )

    info_req_assessment = await risk_assessment_service.request_additional_information(
        session=db_session,
        user=qa_user,
        assessment_id=assessment.id,
        request=RiskAssessmentInfoRequest(information_requested="Need HPLC purity assay confirmation from QA lab."),
    )

    assert info_req_assessment.review_status == RiskAssessmentReviewStatus.NEEDS_MORE_INFORMATION.value
    assert "HPLC purity assay" in info_req_assessment.reviewer_notes


# ===========================================================================
# 4. REST API Endpoint Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_api_risk_assessments_flow(
    client: AsyncClient, setup_risk_environment: Dict[str, Any], monkeypatch
):
    env = setup_risk_environment
    inv = env["investigation"]
    qa_headers = env["qa_headers"]

    # Mock get_ai_service so endpoint uses deterministic MockAIProvider
    doc_id = env["document"].id
    mock_payload = build_mock_structured_risk_assessment(doc_id)
    mock_provider = MockAIProvider(structured_data=mock_payload)

    class DummyAIService:
        provider = mock_provider

    import app.ai.services.ai_service as ai_service_mod
    monkeypatch.setattr(ai_service_mod, "get_ai_service", lambda: DummyAIService())

    # 1. Trigger Risk Assessment
    post_resp = await client.post(
        f"/api/v1/investigations/{inv.id}/ai/risk-assessments",
        headers=qa_headers,
        json={"use_documents": True, "additional_instructions": "Check crystal size impact."},
    )
    assert post_resp.status_code == 201
    assessment_data = post_resp.json()
    assessment_id = assessment_data["id"]
    assert assessment_data["overall_risk"] == "Critical"
    assert assessment_data["status"] == "COMPLETED"

    # 2. List Risk Assessments
    list_resp = await client.get(
        f"/api/v1/investigations/{inv.id}/ai/risk-assessments",
        headers=qa_headers,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 3. Get Risk Assessment by ID
    get_resp = await client.get(
        f"/api/v1/ai/risk-assessments/{assessment_id}",
        headers=qa_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == assessment_id

    # 4. Get Review View
    review_resp = await client.get(
        f"/api/v1/ai/risk-assessments/{assessment_id}/review",
        headers=qa_headers,
    )
    assert review_resp.status_code == 200
    assert "matrix_metadata" in review_resp.json()

    # 5. Patch Review
    patch_resp = await client.patch(
        f"/api/v1/ai/risk-assessments/{assessment_id}/review",
        headers=qa_headers,
        json={"reviewer_notes": "Reviewed by QA Lead. Agree with critical rating."},
    )
    assert patch_resp.status_code == 200
    assert "Reviewed by QA Lead" in patch_resp.json()["reviewer_notes"]

    # 6. Request Information
    info_resp = await client.post(
        f"/api/v1/ai/risk-assessments/{assessment_id}/request-information",
        headers=qa_headers,
        json={"information_requested": "Provide secondary crystal seed certificate."},
    )
    assert info_resp.status_code == 200
    assert info_resp.json()["review_status"] == "NEEDS_MORE_INFORMATION"

    # 7. Accept Assessment
    accept_resp = await client.post(
        f"/api/v1/ai/risk-assessments/{assessment_id}/accept",
        headers=qa_headers,
        json={"apply_to_investigation": True, "reviewer_notes": "Final acceptance confirmed."},
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["review_status"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_api_rbac_unauthorized_user_forbidden(
    client: AsyncClient, setup_risk_environment: Dict[str, Any]
):
    env = setup_risk_environment
    inv = env["investigation"]
    other_headers = env["other_headers"]

    # User without access to investigation gets 403 Forbidden
    resp = await client.get(
        f"/api/v1/investigations/{inv.id}/ai/risk-assessments",
        headers=other_headers,
    )
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]

