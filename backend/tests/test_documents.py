import io
import zipfile
import pytest
import fitz
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.enums import RoleName, DocumentProcessingStatus, AuditAction, EvidenceType
from app.models.user import User, Role
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.audit import AuditLog
from app.schemas.user import UserCreate
from app.cli import seed_standard_roles
from app.repositories.user_repository import user_repo
from app.repositories.investigation_repository import investigation_repo
from app.core.security import get_password_hash


# ---------------------------------------------------------------------------
# Test Fixtures & In-Memory Document Generators
# ---------------------------------------------------------------------------

def create_valid_pdf_bytes(text: str = "Batch Manufacturing Report: Granulation humidity observed at 68% RH.") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def create_multipage_pdf_bytes() -> bytes:
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 72), "Page 1 Content: Critical Quality Attributes for Active Ingredient.")
    p2 = doc.new_page()
    p2.insert_text((50, 72), "Page 2 Content: High-Performance Liquid Chromatography Peak Purity.")
    data = doc.tobytes()
    doc.close()
    return data


def create_image_only_pdf_bytes() -> bytes:
    """Creates a PDF with graphical drawing but zero extractable text (simulating scanned document)."""
    doc = fitz.open()
    page = doc.new_page()
    page.draw_rect(fitz.Rect(50, 50, 300, 300), fill=(0.85, 0.85, 0.85))
    data = doc.tobytes()
    doc.close()
    return data


def create_encrypted_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Confidential Active Pharmaceutical Ingredient Formulation.")
    data = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="AdminSecret123!", user_pw="UserPass123!")
    doc.close()
    return data


def create_valid_docx_bytes(para_text: str = "Equipment Maintenance Log: Calibration certified for pressure sensor PT-102.") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml_content = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>'
            f'<w:p><w:r><w:t>{para_text}</w:t></w:r></w:p>'
            '<w:tbl>'
            '<w:tr>'
            '<w:tc><w:p><w:r><w:t>Sampling Point</w:t></w:r></w:p></w:tc>'
            '<w:tc><w:p><w:r><w:t>Test Result</w:t></w:r></w:p></w:tc>'
            '</w:tr>'
            '<w:tr>'
            '<w:tc><w:p><w:r><w:t>Top Port</w:t></w:r></w:p></w:tc>'
            '<w:tc><w:p><w:r><w:t>99.6%</w:t></w:r></w:p></w:tc>'
            '</w:tr>'
            '</w:tbl>'
            '</w:body></w:document>'
        )
        zf.writestr("word/document.xml", xml_content)
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
    return buf.getvalue()


@pytest.fixture
async def setup_document_environment(db_session: AsyncSession, client: AsyncClient):
    roles = await seed_standard_roles(db_session)
    admin_role = roles[RoleName.ADMIN.value]
    qa_role = roles[RoleName.QA.value]
    inv_role = roles[RoleName.INVESTIGATOR.value]
    operator_role = roles[RoleName.MANUFACTURING_OPERATOR.value]

    admin = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="Admin Quality Lead", email="admin.doc@pharma.com", is_active=True, password="Password123!", role_ids=[admin_role.id]),
        hashed_password=get_password_hash("Password123!"),
    )
    qa = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="QA Specialist", email="qa.doc@pharma.com", is_active=True, password="Password123!", role_ids=[qa_role.id]),
        hashed_password=get_password_hash("Password123!"),
    )
    inv1 = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="Lead Investigator 1", email="inv1.doc@pharma.com", is_active=True, password="Password123!", role_ids=[inv_role.id]),
        hashed_password=get_password_hash("Password123!"),
    )
    inv2 = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="Other Investigator 2", email="inv2.doc@pharma.com", is_active=True, password="Password123!", role_ids=[inv_role.id]),
        hashed_password=get_password_hash("Password123!"),
    )
    operator = await user_repo.create_user(
        db_session,
        obj_in=UserCreate(full_name="Plant Technician", email="operator.doc@pharma.com", is_active=True, password="Password123!", role_ids=[operator_role.id]),
        hashed_password=get_password_hash("Password123!"),
    )
    await db_session.commit()

    # Log in helper
    async def get_headers(email: str):
        res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
        return {"Authorization": f"Bearer {res.json()['access_token']}"}

    admin_headers = await get_headers("admin.doc@pharma.com")
    qa_headers = await get_headers("qa.doc@pharma.com")
    inv1_headers = await get_headers("inv1.doc@pharma.com")
    inv2_headers = await get_headers("inv2.doc@pharma.com")
    operator_headers = await get_headers("operator.doc@pharma.com")

    # Create investigation assigned to inv1
    create_inv_payload = {
        "title": "Yield Discrepancy in Reactor 01 API Synthesis",
        "description": "Chemical yield dropped 12% below validated qualification threshold.",
        "priority": "High",
        "risk_level": "Major",
        "status": "Initiated",
        "api_product_name": "Atorvastatin Calcium Trihydrate",
        "batch_number": "ATOR-2026-009",
        "manufacturing_stage": "Condensation Stage",
        "incident_date": datetime.now(timezone.utc).isoformat(),
        "incident_description": "Mother liquor assay revealed atypical unreacted intermediate fraction.",
    }
    inv_res = await client.post("/api/v1/investigations", headers=inv1_headers, json=create_inv_payload)
    assert inv_res.status_code == 201
    investigation_id = inv_res.json()["id"]

    return {
        "investigation_id": investigation_id,
        "admin": admin,
        "qa": qa,
        "inv1": inv1,
        "inv2": inv2,
        "operator": operator,
        "admin_headers": admin_headers,
        "qa_headers": qa_headers,
        "inv1_headers": inv1_headers,
        "inv2_headers": inv2_headers,
        "operator_headers": operator_headers,
    }


# ---------------------------------------------------------------------------
# Tests: Secure Upload Validation & Format Checks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_valid_pdf_and_extraction(client: AsyncClient, setup_document_environment: dict, db_session: AsyncSession):
    """Verifies valid PDF upload, deterministic text extraction, checksum calculation, and metadata storage."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    pdf_content = create_valid_pdf_bytes("Batch Record #8819: pH shifted to 4.2 at 14:00.")

    files = {"file": ("batch_record_8819.pdf", pdf_content, "application/pdf")}
    data = {"document_category": "Batch Record"}

    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files, data=data)
    assert res.status_code == 201
    doc_data = res.json()

    assert doc_data["original_filename"] == "batch_record_8819.pdf"
    assert doc_data["file_type"] == "application/pdf"
    assert doc_data["file_extension"] == ".pdf"
    assert doc_data["document_category"] == "Batch Record"
    assert doc_data["processing_status"] == DocumentProcessingStatus.COMPLETED.value
    assert len(doc_data["checksum"]) == 64
    assert doc_data["page_count"] == 1
    assert doc_data["character_count"] > 0
    assert doc_data["is_archived"] is False

    doc_id = doc_data["id"]

    # Verify extracted text endpoint
    text_res = await client.get(f"/api/v1/documents/{doc_id}/extracted-text", headers=headers)
    assert text_res.status_code == 200
    text_data = text_res.json()
    assert "Batch Record #8819" in text_data["extracted_text"]
    assert len(text_data["pages"]) == 1
    assert text_data["pages"][0]["page_number"] == 1


@pytest.mark.asyncio
async def test_upload_multipage_pdf_page_boundaries(client: AsyncClient, setup_document_environment: dict):
    """Verifies that multi-page PDFs preserve page boundaries and record page-specific structures."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    multi_pdf = create_multipage_pdf_bytes()
    files = {"file": ("analytical_dossier.pdf", multi_pdf, "application/pdf")}

    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    assert res.status_code == 201
    doc_id = res.json()["id"]
    assert res.json()["page_count"] == 2

    # Verify extracted text breakdown
    text_res = await client.get(f"/api/v1/documents/{doc_id}/extracted-text", headers=headers)
    assert text_res.status_code == 200
    data = text_res.json()
    assert len(data["pages"]) == 2
    assert "Page 1 Content" in data["pages"][0]["text"]
    assert "Page 2 Content" in data["pages"][1]["text"]
    assert "--- Page 1 ---" in data["extracted_text"]
    assert "--- Page 2 ---" in data["extracted_text"]


@pytest.mark.asyncio
async def test_upload_valid_docx_and_table_extraction(client: AsyncClient, setup_document_environment: dict):
    """Verifies OpenXML DOCX upload with paragraph and table extraction in reading order."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    docx_content = create_valid_docx_bytes("Cleaning Validation protocol report.")
    files = {"file": ("cleaning_report.docx", docx_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}

    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    assert res.status_code == 201
    doc_id = res.json()["id"]
    assert res.json()["processing_status"] == DocumentProcessingStatus.COMPLETED.value

    # Check extracted content contains paragraph and pipe-delimited table rows
    text_res = await client.get(f"/api/v1/documents/{doc_id}/extracted-text", headers=headers)
    assert text_res.status_code == 200
    extracted = text_res.json()["extracted_text"]
    assert "Cleaning Validation protocol report." in extracted
    assert "| Sampling Point | Test Result |" in extracted
    assert "| Top Port | 99.6% |" in extracted


@pytest.mark.asyncio
async def test_upload_valid_plain_text(client: AsyncClient, setup_document_environment: dict):
    """Verifies plain text file upload and character decoding."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    txt_content = "SCADA Historian Export\nTimestamp: 2026-11-24 10:15:00\nAgitator RPM: 110\nMotor Load: 4.8 kW\n".encode("utf-8")
    files = {"file": ("historian_log.txt", txt_content, "text/plain")}

    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    assert res.status_code == 201
    assert res.json()["processing_status"] == DocumentProcessingStatus.COMPLETED.value

    doc_id = res.json()["id"]
    text_res = await client.get(f"/api/v1/documents/{doc_id}/extracted-text", headers=headers)
    assert "SCADA Historian Export" in text_res.json()["extracted_text"]


@pytest.mark.asyncio
async def test_empty_file_rejection(client: AsyncClient, setup_document_environment: dict):
    """Verifies that 0-byte files are strictly rejected."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    files = {"file": ("empty.pdf", b"", "application/pdf")}
    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    assert res.status_code == 400
    msg = (res.json().get("message") or res.json().get("detail", "")).lower()
    assert "empty" in msg


@pytest.mark.asyncio
async def test_unsupported_extension_rejection(client: AsyncClient, setup_document_environment: dict):
    """Verifies that files with unwhitelisted extensions are rejected."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    files = {"file": ("malicious_script.sh", b"#!/bin/bash\necho test\n", "application/x-sh")}
    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    assert res.status_code == 400
    msg = (res.json().get("message") or res.json().get("detail", "")).lower()
    assert "not supported" in msg


@pytest.mark.asyncio
async def test_file_signature_and_mime_mismatch_rejection(client: AsyncClient, setup_document_environment: dict):
    """Verifies that an executable disguised as a PDF (extension spoofing) is detected and blocked."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    # Windows PE executable magic 'MZ' disguised as PDF
    fake_pdf = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    files = {"file": ("spoofed_document.pdf", fake_pdf, "application/pdf")}

    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    assert res.status_code == 400
    msg = (res.json().get("message") or res.json().get("detail", "")).lower()
    assert "executable" in msg or "header" in msg


@pytest.mark.asyncio
async def test_duplicate_checksum_detection(client: AsyncClient, setup_document_environment: dict):
    """Verifies that uploading the exact same document twice in an investigation triggers a 409 Conflict."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    pdf_content = create_valid_pdf_bytes("SOP-QC-401: Calibration verification standard.")
    files1 = {"file": ("calibration_sop.pdf", pdf_content, "application/pdf")}

    # First upload succeeds
    res1 = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files1)
    assert res1.status_code == 201

    # Second upload with identical bytes fails with 409 Conflict
    files2 = {"file": ("calibration_sop_copy.pdf", pdf_content, "application/pdf")}
    res2 = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files2)
    assert res2.status_code == 409
    msg2 = (res2.json().get("message") or res2.json().get("detail", "")).lower()
    assert "identical content" in msg2


@pytest.mark.asyncio
async def test_unsafe_filename_sanitization(client: AsyncClient, setup_document_environment: dict):
    """Verifies path traversal in filenames is stripped and sanitized."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    pdf_content = create_valid_pdf_bytes("Valid content under hostile filename.")
    files = {"file": ("../../../../etc/passwd.pdf", pdf_content, "application/pdf")}

    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    assert res.status_code == 201
    sanitized_name = res.json()["original_filename"]
    assert "/" not in sanitized_name
    assert ".." not in sanitized_name
    assert sanitized_name.endswith(".pdf")


# ---------------------------------------------------------------------------
# Tests: OCR Detection, Encrypted & Malformed Document Handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scanned_image_only_pdf_triggers_ocr_required(client: AsyncClient, setup_document_environment: dict):
    """Verifies that an image-only / scanned PDF with 0 extractable text flags OCR_REQUIRED without fabrication."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    scanned_pdf = create_image_only_pdf_bytes()
    files = {"file": ("scanned_paper_batch_sheet.pdf", scanned_pdf, "application/pdf")}

    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    assert res.status_code == 201
    doc_data = res.json()

    assert doc_data["processing_status"] == DocumentProcessingStatus.OCR_REQUIRED.value
    assert doc_data["character_count"] == 0
    assert "ocr is required" in doc_data["extraction_error"].lower()


@pytest.mark.asyncio
async def test_encrypted_pdf_handling(client: AsyncClient, setup_document_environment: dict):
    """Verifies that encrypted/password-protected PDFs are flagged FAILED with clear error message."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    enc_pdf = create_encrypted_pdf_bytes()
    files = {"file": ("encrypted_patent.pdf", enc_pdf, "application/pdf")}

    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    assert res.status_code == 201
    doc_data = res.json()

    assert doc_data["processing_status"] == DocumentProcessingStatus.FAILED.value
    assert "password-protected or encrypted" in doc_data["extraction_error"].lower()


@pytest.mark.asyncio
async def test_malformed_document_handling(client: AsyncClient, setup_document_environment: dict):
    """Verifies corrupted PDF files that start with %PDF- but contain garbage bytes fail gracefully."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    corrupt_pdf = b"%PDF-1.4\nCorrupt garbage payload that terminates abruptly."
    files = {"file": ("corrupt_report.pdf", corrupt_pdf, "application/pdf")}

    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    assert res.status_code == 201
    doc_data = res.json()
    assert doc_data["processing_status"] == DocumentProcessingStatus.FAILED.value
    assert "malformed" in doc_data["extraction_error"].lower() or "corrupt" in doc_data["extraction_error"].lower()


# ---------------------------------------------------------------------------
# Tests: Pasted Text and Email Ingestion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pasted_text_and_email_ingestion(client: AsyncClient, setup_document_environment: dict):
    """Verifies structured ingestion of pasted incident notes and email communication."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    # 1. Pasted Text Ingestion
    pasted_payload = {
        "source_type": "pasted_text",
        "title": "Shift Handover Log Excerpt",
        "body": "Night shift operator reported erratic reading on condenser recirculation pump P-04 at 03:15 AM.",
        "document_category": "Operator Notes",
    }
    pasted_res = await client.post(f"/api/v1/investigations/{inv_id}/documents/text", headers=headers, json=pasted_payload)
    assert pasted_res.status_code == 201
    pasted_data = pasted_res.json()
    assert pasted_data["source_type"] == "pasted_text"
    assert pasted_data["processing_status"] == DocumentProcessingStatus.COMPLETED.value
    assert pasted_data["character_count"] == len(pasted_payload["body"])

    # 2. Email Ingestion
    email_payload = {
        "source_type": "email",
        "title": "Vendor Deviation Notification",
        "subject": "Investigation on Raw Material Lot #RM-8891 Solvent Purity",
        "sender": "qa.external@solvents-supplier.com",
        "received_date": datetime.now(timezone.utc).isoformat(),
        "body": "Dear QA Team, please be advised that analytical re-testing of Lot #RM-8891 showed trace moisture content at 0.35%.",
        "document_category": "Supplier Quality Notification",
    }
    email_res = await client.post(f"/api/v1/investigations/{inv_id}/documents/text", headers=headers, json=email_payload)
    assert email_res.status_code == 201
    email_data = email_res.json()
    assert email_data["source_type"] == "email"
    assert email_data["metadata_json"]["sender"] == "qa.external@solvents-supplier.com"
    assert email_data["metadata_json"]["subject"] == "Investigation on Raw Material Lot #RM-8891 Solvent Purity"

    # 3. Validation: Empty body rejected
    empty_payload = {
        "source_type": "pasted_text",
        "title": "Empty Note",
        "body": "   ",
    }
    empty_res = await client.post(f"/api/v1/investigations/{inv_id}/documents/text", headers=headers, json=empty_payload)
    assert empty_res.status_code == 422


# ---------------------------------------------------------------------------
# Tests: Document Listing, Detail, Download & Extraction Trigger
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_listing_and_download(client: AsyncClient, setup_document_environment: dict):
    """Verifies paginated listing and secure streaming download without path leakage."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    # Upload test document
    pdf_content = create_valid_pdf_bytes("Official Master Batch Production Record.")
    files = {"file": ("download_test.pdf", pdf_content, "application/pdf")}
    upload_res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    doc_id = upload_res.json()["id"]

    # List documents
    list_res = await client.get(f"/api/v1/investigations/{inv_id}/documents?page=1&page_size=10", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == doc_id for item in list_data["items"])

    # Download document
    dl_res = await client.get(f"/api/v1/documents/{doc_id}/download", headers=headers)
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="download_test.pdf"' in dl_res.headers["content-disposition"]
    assert dl_res.content == pdf_content


@pytest.mark.asyncio
async def test_trigger_re_extraction_idempotency(client: AsyncClient, setup_document_environment: dict):
    """Verifies that trigger-extraction returns existing results when completed, and force re-runs extraction."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    pdf_content = create_valid_pdf_bytes("Analytical Certificate: Purity 99.85%.")
    files = {"file": ("coa_test.pdf", pdf_content, "application/pdf")}
    upload_res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    doc_id = upload_res.json()["id"]

    # 1. Trigger extraction without force -> returns existing result
    res1 = await client.post(f"/api/v1/documents/{doc_id}/extract", headers=headers)
    assert res1.status_code == 200
    assert "already successfully extracted" in res1.json()["message"].lower()

    # 2. Trigger with force=true -> executes re-extraction
    res2 = await client.post(f"/api/v1/documents/{doc_id}/extract?force=true", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["status"] == DocumentProcessingStatus.COMPLETED.value


# ---------------------------------------------------------------------------
# Tests: Evidence Association Traceability
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evidence_association_traceability(client: AsyncClient, setup_document_environment: dict):
    """Verifies linking an uploaded document to an Evidence item for RCA traceability."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    pdf_content = create_valid_pdf_bytes("Chromatography calibration chromatogram: Peak symmetry at 1.18.")
    files = {"file": ("chromatogram_peak.pdf", pdf_content, "application/pdf")}
    upload_res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    doc_id = upload_res.json()["id"]

    evidence_payload = {
        "title": "Atypical Chromatogram Peak Asymmetry",
        "evidence_type": "AnalyticalResult",
        "description": "Peak asymmetry factor exceeded standard 0.95-1.05 range.",
        "page_number": 1,
        "excerpt": "Peak symmetry at 1.18",
        "source_reference": "HPLC Column 03 Calibration Log",
    }

    ev_res = await client.post(f"/api/v1/documents/{doc_id}/evidence", headers=headers, json=evidence_payload)
    assert ev_res.status_code == 201
    ev_data = ev_res.json()
    assert ev_data["document_id"] == doc_id
    assert ev_data["investigation_id"] == inv_id
    assert ev_data["page_number"] == 1
    assert ev_data["excerpt"] == "Peak symmetry at 1.18"

    # Query evidence by document
    ev_list_res = await client.get(f"/api/v1/documents/{doc_id}/evidence", headers=headers)
    assert ev_list_res.status_code == 200
    assert len(ev_list_res.json()) >= 1


# ---------------------------------------------------------------------------
# Tests: Access Scoping, Authorization & Restricted Deletion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_access_scoping_and_unauthorized_rejection(client: AsyncClient, setup_document_environment: dict):
    """Verifies that investigators cannot upload or access documents of unassigned investigations."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    unassigned_inv_headers = env["inv2_headers"]
    assigned_headers = env["inv1_headers"]

    # 1. Unassigned investigator upload rejected
    pdf_content = create_valid_pdf_bytes("Unauthorized investigation file.")
    files = {"file": ("unauthorized.pdf", pdf_content, "application/pdf")}
    res_upload = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=unassigned_inv_headers, files=files)
    assert res_upload.status_code == 403

    # Upload document using assigned investigator
    assigned_upload = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=assigned_headers, files=files)
    assert assigned_upload.status_code == 201
    doc_id = assigned_upload.json()["id"]

    # 2. Unassigned investigator cannot get detail or download
    res_detail = await client.get(f"/api/v1/documents/{doc_id}", headers=unassigned_inv_headers)
    assert res_detail.status_code == 403

    res_dl = await client.get(f"/api/v1/documents/{doc_id}/download", headers=unassigned_inv_headers)
    assert res_dl.status_code == 403

    # 3. QA Specialist has global access
    qa_headers = env["qa_headers"]
    qa_detail = await client.get(f"/api/v1/documents/{doc_id}", headers=qa_headers)
    assert qa_detail.status_code == 200


@pytest.mark.asyncio
async def test_soft_deletion_and_terminal_state_lock(client: AsyncClient, setup_document_environment: dict, db_session: AsyncSession):
    """Verifies soft-deletion of documents and rejection on locked/closed investigations."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    assigned_headers = env["inv1_headers"]
    admin_headers = env["admin_headers"]

    pdf_content = create_valid_pdf_bytes("Document to be deleted.")
    files = {"file": ("doc_to_delete.pdf", pdf_content, "application/pdf")}
    up_res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=assigned_headers, files=files)
    doc_id = up_res.json()["id"]

    # 1. Soft-delete by lead investigator succeeds when investigation is Initiated
    del_res = await client.delete(f"/api/v1/documents/{doc_id}", headers=assigned_headers)
    assert del_res.status_code == 200
    assert "archived successfully" in del_res.json()["message"].lower()

    # Deleted document no longer returned in active list
    list_res = await client.get(f"/api/v1/investigations/{inv_id}/documents", headers=assigned_headers)
    assert not any(item["id"] == doc_id for item in list_res.json()["items"])

    # 2. Verify deletion blocked on Closed investigation
    # Upload new doc
    files2 = {"file": ("locked_doc.pdf", pdf_content, "application/pdf")}
    up2 = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=admin_headers, files=files2)
    locked_doc_id = up2.json()["id"]

    # Move investigation to Closed status directly in DB for test
    inv = await investigation_repo.get(db_session, inv_id)
    inv.status = "Closed"
    await db_session.commit()

    # Attempt delete on closed investigation -> 400 Bad Request
    del_blocked = await client.delete(f"/api/v1/documents/{locked_doc_id}", headers=admin_headers)
    assert del_blocked.status_code == 400
    msg_blocked = (del_blocked.json().get("message") or del_blocked.json().get("detail", "")).lower()
    assert "cannot delete" in msg_blocked


# ---------------------------------------------------------------------------
# Tests: ALCOA+ Audit Logging of Document Events
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_document_audit_logging(client: AsyncClient, setup_document_environment: dict, db_session: AsyncSession):
    """Verifies that all document operations (upload, text ingestion, download, deletion) write audit entries."""
    env = setup_document_environment
    inv_id = env["investigation_id"]
    headers = env["inv1_headers"]

    # Upload document
    pdf_content = create_valid_pdf_bytes("Audit Verification Document Content.")
    files = {"file": ("audit_doc.pdf", pdf_content, "application/pdf")}
    res = await client.post(f"/api/v1/investigations/{inv_id}/documents", headers=headers, files=files)
    doc_id = res.json()["id"]

    # Download document
    await client.get(f"/api/v1/documents/{doc_id}/download", headers=headers)

    # Delete document
    await client.delete(f"/api/v1/documents/{doc_id}", headers=headers)

    # Inspect audit log entries in DB
    stmt = (
        select(AuditLog)
        .where(AuditLog.entity_id == doc_id)
        .order_by(AuditLog.created_at.asc())
    )
    result = await db_session.execute(stmt)
    logs = list(result.scalars().all())

    actions = [log.action for log in logs]
    assert AuditAction.CREATE.value in actions or AuditAction.CREATE in actions
    assert AuditAction.READ.value in actions or AuditAction.READ in actions
    assert AuditAction.DELETE.value in actions or AuditAction.DELETE in actions
