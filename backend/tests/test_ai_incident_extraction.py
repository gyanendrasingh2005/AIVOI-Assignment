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
    DocumentProcessingStatus,
    ExtractionStatus,
    ExtractionReviewStatus,
    FieldExtractionStatus,
    FieldReviewDecision,
    AuditAction,
)
from app.models.user import User, Role
from app.models.investigation import Investigation
from app.models.incident import Incident
from app.models.document import Document
from app.models.audit import AuditLog
from app.models.incident_extraction import IncidentExtraction
from app.schemas.user import UserCreate
from app.schemas.extraction import (
    IncidentExtractionRequest,
    FieldReviewUpdateRequest,
    ExtractionReviewPatchRequest,
    FieldAcceptanceRequest,
    FieldRejectionRequest,
    ExtractedField,
    SourceReference,
    ExtractionStructuredOutput,
)
from app.cli import seed_standard_roles
from app.repositories.user_repository import user_repo
from app.repositories.investigation_repository import investigation_repo, incident_repo
from app.repositories.incident_extraction_repository import incident_extraction_repo
from app.services.document_context_service import document_context_service
from app.services.incident_extraction_service import incident_extraction_service
from app.ai.providers.mock_provider import MockAIProvider
from app.ai.graphs.extraction_builder import create_incident_extraction_graph
from app.ai.graphs.extraction_state import IncidentExtractionWorkflowState


# ---------------------------------------------------------------------------
# Test Fixtures & Sample Payloads
# ---------------------------------------------------------------------------

SAMPLE_BATCH_REPORT_TEXT = """
BATCH PRODUCTION RECORD EXCERPT
API Product: Pregabalin Crystalline
Batch Number: PGB-2026-0042
Manufacturing Stage: Final Crystallization
Equipment ID: RX-302 (Glass-Lined Reactor)
Incident Date: 2026-11-20
Observed Event: Crystallization temperature reached 48.5 °C during cooling step.
Expected Condition: Cooling ramp maintained strictly between 22.0 °C and 25.0 °C.
Immediate Actions: Automated chiller cooling bypass engaged immediately. Batch held in reactor under nitrogen purge.
Affected Batches: PGB-2026-0042, PGB-2026-0043
Potential Impact: Polymorphic purity compromised. Elevated Form II impurity detected.
Responsible Department: API Synthesis Operations
"""

SAMPLE_ANALYTICAL_CoA_TEXT = """
CERTIFICATE OF ANALYSIS (OUT OF SPECIFICATION)
Product: Pregabalin Crystalline
Batch: PGB-2026-0042
Test Parameter: Polymorphic Purity by Powder XRD
Expected Value: Form I >= 99.0%
Actual Value: 92.4% (Out of Specification)
Unit: % w/w
Status: OOS Confirmed. Secondary recrystallization proposed.
"""

SAMPLE_CONFLICTING_TEXT = """
OPERATOR SHIFT LOG
Batch: PGB-2026-0042
Note: Temperature observed was 39.0 °C at 14:15.
"""


def build_mock_structured_extraction(doc1_id: str, doc2_id: str) -> Dict[str, Any]:
    return {
        "fields": [
            {
                "field_name": "api_product_name",
                "value": "Pregabalin Crystalline",
                "confidence": 0.98,
                "status": "EXTRACTED",
                "source_references": [
                    {
                        "document_id": doc1_id,
                        "filename": "batch_report.txt",
                        "page_number": 1,
                        "excerpt": "API Product: Pregabalin Crystalline",
                    }
                ],
            },
            {
                "field_name": "batch_number",
                "value": "PGB-2026-0042",
                "confidence": 0.99,
                "status": "EXTRACTED",
                "source_references": [
                    {
                        "document_id": doc1_id,
                        "filename": "batch_report.txt",
                        "page_number": 1,
                        "excerpt": "Batch Number: PGB-2026-0042",
                    }
                ],
            },
            {
                "field_name": "manufacturing_stage",
                "value": "Final Crystallization",
                "confidence": 0.95,
                "status": "EXTRACTED",
                "source_references": [
                    {
                        "document_id": doc1_id,
                        "filename": "batch_report.txt",
                        "page_number": 1,
                        "excerpt": "Manufacturing Stage: Final Crystallization",
                    }
                ],
            },
            {
                "field_name": "incident_date",
                "value": "2026-11-20",
                "confidence": 0.96,
                "status": "EXTRACTED",
                "source_references": [
                    {
                        "document_id": doc1_id,
                        "filename": "batch_report.txt",
                        "page_number": 1,
                        "excerpt": "Incident Date: 2026-11-20",
                    }
                ],
            },
            {
                "field_name": "equipment_id",
                "value": "RX-302",
                "confidence": 0.94,
                "status": "EXTRACTED",
                "source_references": [
                    {
                        "document_id": doc1_id,
                        "filename": "batch_report.txt",
                        "page_number": 1,
                        "excerpt": "Equipment ID: RX-302 (Glass-Lined Reactor)",
                    }
                ],
            },
            {
                "field_name": "actual_parameter_value",
                "value": "48.5 °C",
                "confidence": 0.97,
                "status": "EXTRACTED",
                "source_references": [
                    {
                        "document_id": doc1_id,
                        "filename": "batch_report.txt",
                        "page_number": 1,
                        "excerpt": "Crystallization temperature reached 48.5 °C during cooling step.",
                    }
                ],
            },
            {
                "field_name": "expected_parameter_value",
                "value": "22.0 °C to 25.0 °C",
                "confidence": 0.95,
                "status": "EXTRACTED",
                "source_references": [
                    {
                        "document_id": doc1_id,
                        "filename": "batch_report.txt",
                        "page_number": 1,
                        "excerpt": "Cooling ramp maintained strictly between 22.0 °C and 25.0 °C.",
                    }
                ],
            },
            {
                "field_name": "immediate_actions",
                "value": "Automated chiller cooling bypass engaged. Batch held under nitrogen purge.",
                "confidence": 0.93,
                "status": "EXTRACTED",
                "source_references": [
                    {
                        "document_id": doc1_id,
                        "filename": "batch_report.txt",
                        "page_number": 1,
                        "excerpt": "Automated chiller cooling bypass engaged immediately. Batch held in reactor under nitrogen purge.",
                    }
                ],
            },
            {
                "field_name": "affected_batches",
                "value": ["PGB-2026-0042", "PGB-2026-0043"],
                "confidence": 0.91,
                "status": "EXTRACTED",
                "source_references": [
                    {
                        "document_id": doc1_id,
                        "filename": "batch_report.txt",
                        "page_number": 1,
                        "excerpt": "Affected Batches: PGB-2026-0042, PGB-2026-0043",
                    }
                ],
            },
            {
                "field_name": "potential_quality_impact",
                "value": "Polymorphic purity compromised with Form II impurity.",
                "confidence": 0.92,
                "status": "EXTRACTED",
                "source_references": [
                    {
                        "document_id": doc2_id,
                        "filename": "analytical_coa.txt",
                        "page_number": 1,
                        "excerpt": "Actual Value: 92.4% (Out of Specification)",
                    }
                ],
            },
        ],
        "missing_information": [
            {
                "field_name": "manufacturing_facility",
                "description": "Specific manufacturing suite or building was not documented.",
                "impact": "Low impact on root cause analysis.",
            }
        ],
        "conflicting_information": [],
    }


@pytest.fixture
async def setup_extraction_environment(db_session: AsyncSession, client: AsyncClient):
    roles = await seed_standard_roles(db_session)
    qa_role = roles[RoleName.QA.value]
    inv_role = roles[RoleName.INVESTIGATOR.value]
    op_role = roles[RoleName.MANUFACTURING_OPERATOR.value]

    qa_user = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="Quality Assurance Lead",
            email="qa.extract@pharma.com",
            is_active=True,
            password="Password123!",
            role_ids=[qa_role.id],
        ),
        hashed_password=get_password_hash("Password123!"),
    )

    inv_user = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="Assigned Investigator",
            email="inv.extract@pharma.com",
            is_active=True,
            password="Password123!",
            role_ids=[inv_role.id],
        ),
        hashed_password=get_password_hash("Password123!"),
    )

    unassigned_user = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(
            full_name="Unassigned Operator",
            email="operator.extract@pharma.com",
            is_active=True,
            password="Password123!",
            role_ids=[op_role.id],
        ),
        hashed_password=get_password_hash("Password123!"),
    )

    async def get_token(email: str) -> str:
        res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        assert res.status_code == 200
        return res.json()["access_token"]

    qa_token = await get_token("qa.extract@pharma.com")
    inv_token = await get_token("inv.extract@pharma.com")
    unassigned_token = await get_token("operator.extract@pharma.com")

    # Create investigation
    investigation = Investigation(
        investigation_number="INV-2026-00444",
        title="Thermal Excursion During Pregabalin Crystallization",
        description="Temperature spike observed during crystallization phase in reactor RX-302.",
        status=InvestigationStatus.UNDER_INVESTIGATION.value,
        priority=PriorityLevel.HIGH.value,
        risk_level=RiskLevel.CRITICAL.value,
        created_by=qa_user.id,
        assigned_to=inv_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(investigation)
    await db_session.flush()

    # Create initial Incident record linked to investigation
    incident = Incident(
        investigation_id=investigation.id,
        api_product_name="Pregabalin Initial",
        batch_number="INIT-BATCH",
        manufacturing_stage="Initial Stage",
        incident_date=datetime(2026, 11, 1, tzinfo=timezone.utc),
        incident_description="Initial intake narrative awaiting document verification",
    )
    db_session.add(incident)
    await db_session.flush()

    # Create source documents
    doc1 = Document(
        investigation_id=investigation.id,
        original_filename="batch_report.txt",
        stored_filename=f"batch_report_{uuid.uuid4().hex[:8]}.txt",
        file_type="text/plain",
        file_size=len(SAMPLE_BATCH_REPORT_TEXT),
        storage_path="storage/evidence/batch_report.txt",
        checksum="checksum_batch_001",
        extracted_text=SAMPLE_BATCH_REPORT_TEXT,
        processing_status=DocumentProcessingStatus.COMPLETED.value,
        page_count=1,
        character_count=len(SAMPLE_BATCH_REPORT_TEXT),
        source_type="file_upload",
    )
    doc2 = Document(
        investigation_id=investigation.id,
        original_filename="analytical_coa.txt",
        stored_filename=f"coa_{uuid.uuid4().hex[:8]}.txt",
        file_type="text/plain",
        file_size=len(SAMPLE_ANALYTICAL_CoA_TEXT),
        storage_path="storage/evidence/coa.txt",
        checksum="checksum_coa_002",
        extracted_text=SAMPLE_ANALYTICAL_CoA_TEXT,
        processing_status=DocumentProcessingStatus.COMPLETED.value,
        page_count=1,
        character_count=len(SAMPLE_ANALYTICAL_CoA_TEXT),
        source_type="file_upload",
    )
    doc_ocr = Document(
        investigation_id=investigation.id,
        original_filename="scanned_batch_sheet.pdf",
        stored_filename=f"scanned_{uuid.uuid4().hex[:8]}.pdf",
        file_type="application/pdf",
        file_size=1024,
        storage_path="storage/evidence/scanned.pdf",
        checksum="checksum_ocr_003",
        extracted_text=None,
        processing_status=DocumentProcessingStatus.OCR_REQUIRED.value,
        page_count=3,
        source_type="file_upload",
    )
    doc_failed = Document(
        investigation_id=investigation.id,
        original_filename="corrupted_historian.docx",
        stored_filename=f"corrupted_{uuid.uuid4().hex[:8]}.docx",
        file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        file_size=2048,
        storage_path="storage/evidence/corrupted.docx",
        checksum="checksum_failed_004",
        extracted_text=None,
        extraction_error="ZIP package archive corrupted",
        processing_status=DocumentProcessingStatus.FAILED.value,
        source_type="file_upload",
    )

    db_session.add_all([doc1, doc2, doc_ocr, doc_failed])
    await db_session.flush()
    await db_session.refresh(investigation)
    await db_session.refresh(incident)
    await db_session.refresh(doc1)
    await db_session.refresh(doc2)

    return {
        "qa_user": qa_user,
        "inv_user": inv_user,
        "unassigned_user": unassigned_user,
        "qa_token": qa_token,
        "inv_token": inv_token,
        "unassigned_token": unassigned_token,
        "investigation": investigation,
        "incident": incident,
        "doc1": doc1,
        "doc2": doc2,
        "doc_ocr": doc_ocr,
        "doc_failed": doc_failed,
    }


# ---------------------------------------------------------------------------
# 1. Document Context Preparation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_context_preparation_analyzable_and_ocr(db_session: AsyncSession, setup_extraction_environment):
    """Verifies document context staging correctly handles analyzed, OCR_REQUIRED, and FAILED states."""
    env = setup_extraction_environment
    inv = env["investigation"]
    doc1 = env["doc1"]
    doc_ocr = env["doc_ocr"]
    doc_failed = env["doc_failed"]

    context, summaries, analyzable = await document_context_service.prepare_context(
        session=db_session,
        investigation_id=inv.id,
        document_ids=[doc1.id, doc_ocr.id, doc_failed.id],
    )

    assert doc1.original_filename in context
    assert "storage/evidence" not in context  # Security: No internal storage paths leaked!
    assert len(analyzable) == 1
    assert analyzable[0].id == doc1.id

    status_map = {s.document_id: s.status for s in summaries}
    assert status_map[doc1.id] == "ANALYZED"
    assert status_map[doc_ocr.id] == "OCR_REQUIRED"
    assert status_map[doc_failed.id] == "FAILED"


@pytest.mark.asyncio
async def test_document_context_preparation_cross_investigation_rejection(db_session: AsyncSession, setup_extraction_environment):
    """Rejects documents that do not belong to the requested investigation (multi-tenant boundary)."""
    env = setup_extraction_environment
    doc1 = env["doc1"]
    fake_inv_id = str(uuid.uuid4())

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await document_context_service.prepare_context(
            session=db_session,
            investigation_id=fake_inv_id,
            document_ids=[doc1.id],
        )
    assert exc_info.value.status_code == 400
    assert "Security violation" in exc_info.value.detail


# ---------------------------------------------------------------------------
# 2. LangGraph Extraction Graph Node & Workflow Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_langgraph_incident_extraction_workflow_success(setup_extraction_environment):
    """Executes full StateGraph extraction workflow with mock AI provider."""
    env = setup_extraction_environment
    doc1 = env["doc1"]
    doc2 = env["doc2"]

    mock_data = build_mock_structured_extraction(doc1.id, doc2.id)
    provider = MockAIProvider(structured_data=mock_data)
    graph = create_incident_extraction_graph(provider)

    initial_state: IncidentExtractionWorkflowState = {
        "extraction_id": str(uuid.uuid4()),
        "workflow_id": str(uuid.uuid4()),
        "investigation_id": env["investigation"].id,
        "user_id": env["inv_user"].id,
        "document_ids": [doc1.id, doc2.id],
        "extraction_instructions": "Focus on thermal excursion",
        "prompt_version": "1.0.0",
        "document_context": SAMPLE_BATCH_REPORT_TEXT,
        "document_summaries": [
            {"document_id": doc1.id, "filename": doc1.original_filename, "status": "ANALYZED"}
        ],
        "valid_document_map": {doc1.id: doc1.original_filename, doc2.id: doc2.original_filename},
        "errors": [],
        "status": ExtractionStatus.PENDING.value,
    }

    final_state = await graph.ainvoke(initial_state)

    assert final_state["status"] == ExtractionStatus.COMPLETED.value
    fields = final_state["extracted_fields"]
    assert "api_product_name" in fields
    assert fields["api_product_name"]["value"] == "Pregabalin Crystalline"
    assert fields["batch_number"]["value"] == "PGB-2026-0042"
    assert fields["equipment_id"]["value"] == "RX-302"
    assert fields["actual_parameter_value"]["value"] == "48.5 °C"

    # Verify source references
    refs = fields["api_product_name"]["source_references"]
    assert len(refs) == 1
    assert refs[0]["document_id"] == doc1.id
    assert refs[0]["filename"] == doc1.original_filename


@pytest.mark.asyncio
async def test_langgraph_hallucinated_source_reference_detection(setup_extraction_environment):
    """Detects and flags when an AI model cites a hallucinated document ID."""
    env = setup_extraction_environment
    doc1 = env["doc1"]

    hallucinated_data = {
        "fields": [
            {
                "field_name": "batch_number",
                "value": "FABRICATED-123",
                "confidence": 0.8,
                "status": "EXTRACTED",
                "source_references": [
                    {
                        "document_id": str(uuid.uuid4()),  # NOT IN valid_document_map!
                        "filename": "invented_doc.pdf",
                        "page_number": 99,
                        "excerpt": "Fabricated text",
                    }
                ],
            }
        ],
        "missing_information": [],
        "conflicting_information": [],
    }

    provider = MockAIProvider(structured_data=hallucinated_data)
    graph = create_incident_extraction_graph(provider)

    initial_state: IncidentExtractionWorkflowState = {
        "extraction_id": str(uuid.uuid4()),
        "workflow_id": str(uuid.uuid4()),
        "investigation_id": env["investigation"].id,
        "document_ids": [doc1.id],
        "document_context": SAMPLE_BATCH_REPORT_TEXT,
        "valid_document_map": {doc1.id: doc1.original_filename},
        "errors": [],
        "status": ExtractionStatus.PENDING.value,
    }

    final_state = await graph.ainvoke(initial_state)

    batch_field = final_state["extracted_fields"]["batch_number"]
    # validate_source_references_node flags invalid citation as NEEDS_REVIEW
    assert batch_field["status"] == FieldExtractionStatus.NEEDS_REVIEW.value
    assert "FLAG: Model cited unverified document reference" in batch_field["explanation"]


# ---------------------------------------------------------------------------
# 3. IncidentExtractionService & Human Review Workflow Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_incident_extraction_service_full_lifecycle(db_session: AsyncSession, setup_extraction_environment):
    """Tests end-to-end extraction, review patch, field acceptance, and confirmed incident update."""
    env = setup_extraction_environment
    inv = env["investigation"]
    doc1 = env["doc1"]
    doc2 = env["doc2"]
    qa_user = env["qa_user"]

    mock_data = build_mock_structured_extraction(doc1.id, doc2.id)
    mock_provider = MockAIProvider(structured_data=mock_data)

    # 1. Trigger Extraction
    req = IncidentExtractionRequest(document_ids=[doc1.id, doc2.id])
    extraction = await incident_extraction_service.start_incident_extraction(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=req,
        provider_override=mock_provider,
    )

    assert extraction.id is not None
    assert extraction.status == ExtractionStatus.COMPLETED.value
    assert extraction.review_status == ExtractionReviewStatus.PENDING_REVIEW.value
    assert "api_product_name" in extraction.extracted_fields

    # Verify Incident record was NOT modified during extraction (human control guardrail)
    incident_before = await incident_repo.get_by_investigation(db_session, inv.id)
    assert incident_before.api_product_name == "Pregabalin Initial"

    # 2. Human Review: Investigator edits a suggested parameter before acceptance
    patch_req = ExtractionReviewPatchRequest(
        fields=[
            FieldReviewUpdateRequest(
                field_name="api_product_name",
                reviewed_value="Pregabalin Crystalline (EP Grade)",
                review_decision=FieldReviewDecision.ACCEPTED,
            ),
            FieldReviewUpdateRequest(
                field_name="batch_number",
                reviewed_value=None,  # Keep AI suggestion
                review_decision=FieldReviewDecision.ACCEPTED,
            ),
        ]
    )

    reviewed_extraction = await incident_extraction_service.update_review_decisions(
        session=db_session,
        user=qa_user,
        extraction_id=extraction.id,
        patch_req=patch_req,
    )
    assert reviewed_extraction.review_status == ExtractionReviewStatus.PARTIALLY_ACCEPTED.value
    prod_field = reviewed_extraction.extracted_fields["api_product_name"]
    assert prod_field["is_modified"] is True
    assert prod_field["reviewed_value"] == "Pregabalin Crystalline (EP Grade)"

    # 3. Controlled Field Acceptance: Apply confirmed attributes to Incident entity
    accept_req = FieldAcceptanceRequest(field_names=["api_product_name", "batch_number", "actual_parameter_value"])
    accepted_extraction, updated_incident = await incident_extraction_service.accept_incident_fields(
        session=db_session,
        user=qa_user,
        extraction_id=extraction.id,
        accept_req=accept_req,
    )

    # Verify database Incident entity now reflects the accepted values!
    assert updated_incident.api_product_name == "Pregabalin Crystalline (EP Grade)"
    assert updated_incident.batch_number == "PGB-2026-0042"
    assert updated_incident.actual_parameter == "48.5 °C"

    # Verify 21 CFR Part 11 ALCOA+ audit log was written for the accepted fields
    stmt = select(AuditLog).where(
        AuditLog.entity_id == updated_incident.id,
        AuditLog.action == AuditAction.AI_FIELD_ACCEPTED.value,
    )
    audit_res = await db_session.execute(stmt)
    audit_entries = list(audit_res.scalars().all())
    assert len(audit_entries) >= 2  # api_product_name and batch_number entries recorded


@pytest.mark.asyncio
async def test_incident_extraction_rejection_does_not_mutate_incident(db_session: AsyncSession, setup_extraction_environment):
    """Ensures rejecting an extraction marks it rejected without altering confirmed incident data."""
    env = setup_extraction_environment
    inv = env["investigation"]
    doc1 = env["doc1"]
    doc2 = env["doc2"]
    qa_user = env["qa_user"]

    mock_data = build_mock_structured_extraction(doc1.id, doc2.id)
    mock_provider = MockAIProvider(structured_data=mock_data)

    req = IncidentExtractionRequest(document_ids=[doc1.id, doc2.id])
    extraction = await incident_extraction_service.start_incident_extraction(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=req,
        provider_override=mock_provider,
    )

    reject_req = FieldRejectionRequest(reason="Source documents determined to be draft notes.")
    rejected_extraction = await incident_extraction_service.reject_incident_extraction(
        session=db_session,
        user=qa_user,
        extraction_id=extraction.id,
        reject_req=reject_req,
    )

    assert rejected_extraction.review_status == ExtractionReviewStatus.REJECTED.value

    # Confirmed incident record must remain completely untouched
    incident = await incident_repo.get_by_investigation(db_session, inv.id)
    assert incident.api_product_name == "Pregabalin Initial"


# ---------------------------------------------------------------------------
# 4. REST API Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_trigger_extraction_authorized_and_forbidden(client: AsyncClient, setup_extraction_environment):
    """POST /api/v1/investigations/{id}/ai/extract-incident enforces RBAC and access scoping."""
    env = setup_extraction_environment
    inv = env["investigation"]
    doc1 = env["doc1"]

    # 1. Unauthenticated -> 401
    res_anon = await client.post(
        f"/api/v1/investigations/{inv.id}/ai/extract-incident",
        json={"document_ids": [doc1.id]},
    )
    assert res_anon.status_code == 401

    # 2. Unassigned operator without access to investigation -> 403 Forbidden
    res_forbidden = await client.post(
        f"/api/v1/investigations/{inv.id}/ai/extract-incident",
        json={"document_ids": [doc1.id]},
        headers={"Authorization": f"Bearer {env['unassigned_token']}"},
    )
    assert res_forbidden.status_code == 403

    # 3. Privileged QA user -> 202 Accepted
    res_qa = await client.post(
        f"/api/v1/investigations/{inv.id}/ai/extract-incident",
        json={"document_ids": [doc1.id], "extraction_instructions": "Check reactor logs"},
        headers={"Authorization": f"Bearer {env['qa_token']}"},
    )
    assert res_qa.status_code == 202
    data = res_qa.json()
    assert data["investigation_id"] == inv.id
    assert "source_document_ids" in data


@pytest.mark.asyncio
async def test_api_review_and_accept_workflow(client: AsyncClient, db_session: AsyncSession, setup_extraction_environment):
    """Full API test: list extractions, get review view, patch decision, accept field."""
    env = setup_extraction_environment
    inv = env["investigation"]
    doc1 = env["doc1"]
    qa_user = env["qa_user"]
    qa_token = env["qa_token"]

    mock_data = build_mock_structured_extraction(doc1.id, doc1.id)
    mock_provider = MockAIProvider(structured_data=mock_data)

    extraction = await incident_extraction_service.start_incident_extraction(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=IncidentExtractionRequest(document_ids=[doc1.id]),
        provider_override=mock_provider,
    )

    # 1. GET /api/v1/investigations/{id}/ai/extractions
    res_list = await client.get(
        f"/api/v1/investigations/{inv.id}/ai/extractions",
        headers={"Authorization": f"Bearer {qa_token}"},
    )
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 2. GET /api/v1/ai/extractions/{id}/review
    res_review = await client.get(
        f"/api/v1/ai/extractions/{extraction.id}/review",
        headers={"Authorization": f"Bearer {qa_token}"},
    )
    assert res_review.status_code == 200
    review_data = res_review.json()
    assert "fields" in review_data
    assert "missing_information" in review_data
    assert "document_summaries" in review_data

    # 3. PATCH /api/v1/ai/extractions/{id}/review
    res_patch = await client.patch(
        f"/api/v1/ai/extractions/{extraction.id}/review",
        json={
            "fields": [
                {
                    "field_name": "batch_number",
                    "reviewed_value": "PGB-2026-0042",
                    "review_decision": "ACCEPTED",
                }
            ]
        },
        headers={"Authorization": f"Bearer {qa_token}"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["review_status"] == "PARTIALLY_ACCEPTED"

    # 4. POST /api/v1/ai/extractions/{id}/accept
    res_accept = await client.post(
        f"/api/v1/ai/extractions/{extraction.id}/accept",
        json={"field_names": ["batch_number"]},
        headers={"Authorization": f"Bearer {qa_token}"},
    )
    assert res_accept.status_code == 200

    # Verify DB Incident record was updated
    incident = await incident_repo.get_by_investigation(db_session, inv.id)
    assert incident.batch_number == "PGB-2026-0042"


@pytest.mark.asyncio
async def test_api_reject_extraction(client: AsyncClient, db_session: AsyncSession, setup_extraction_environment):
    """POST /api/v1/ai/extractions/{id}/reject marks extraction rejected."""
    env = setup_extraction_environment
    inv = env["investigation"]
    doc1 = env["doc1"]
    qa_user = env["qa_user"]
    qa_token = env["qa_token"]

    mock_data = build_mock_structured_extraction(doc1.id, doc1.id)
    mock_provider = MockAIProvider(structured_data=mock_data)

    extraction = await incident_extraction_service.start_incident_extraction(
        session=db_session,
        user=qa_user,
        investigation_id=inv.id,
        request=IncidentExtractionRequest(document_ids=[doc1.id]),
        provider_override=mock_provider,
    )

    res_reject = await client.post(
        f"/api/v1/ai/extractions/{extraction.id}/reject",
        json={"reason": "Incorrect lot documentation uploaded."},
        headers={"Authorization": f"Bearer {qa_token}"},
    )
    assert res_reject.status_code == 200
    assert res_reject.json()["review_status"] == "REJECTED"

