from typing import Optional, List
from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    Query,
    Request,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentTextIngestRequest,
    DocumentExtractedTextResponse,
    ExtractionTriggerResponse,
)
from app.schemas.evidence import EvidenceCreate, EvidenceResponse
from app.services.document_service import document_service
from app.services.storage_service import get_storage_service
from app.repositories.document_evidence_repository import evidence_repo

router = APIRouter()


# ---------------------------------------------------------------------------
# Investigation Document Upload & Ingestion Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/investigations/{investigation_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process source document",
    description="Uploads a PDF, DOCX, or TXT document, securely stores it, and triggers text extraction.",
    tags=["Documents"],
)
async def upload_document(
    investigation_id: str,
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT)"),
    document_category: Optional[str] = Form(None, description="Category (Batch Record, CoA, Historian, etc.)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    client_ip = request.client.host if request and request.client else None
    return await document_service.upload_document(
        session=db,
        investigation_id=investigation_id,
        upload_file=file,
        document_category=document_category,
        current_user=current_user,
        client_ip=client_ip,
    )


@router.post(
    "/investigations/{investigation_id}/documents/text",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest pasted text or email content",
    description="Securely ingests structured pasted text or email records with audit trail.",
    tags=["Documents"],
)
async def ingest_pasted_text_or_email(
    investigation_id: str,
    payload: DocumentTextIngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    client_ip = request.client.host if request and request.client else None
    return await document_service.ingest_pasted_text_or_email(
        session=db,
        investigation_id=investigation_id,
        payload=payload,
        current_user=current_user,
        client_ip=client_ip,
    )


@router.get(
    "/investigations/{investigation_id}/documents",
    response_model=DocumentListResponse,
    summary="List investigation documents",
    description="Returns paginated source documents associated with an investigation.",
    tags=["Documents"],
)
async def list_investigation_documents(
    investigation_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await document_service.get_investigation_documents(
        session=db,
        investigation_id=investigation_id,
        page=page,
        page_size=page_size,
        category=category,
        status=status,
        current_user=current_user,
    )


# ---------------------------------------------------------------------------
# Individual Document Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document metadata",
    description="Retrieves metadata for a specific document without full extracted text.",
    tags=["Documents"],
)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await document_service.get_document_detail(
        session=db,
        document_id=document_id,
        current_user=current_user,
    )


@router.get(
    "/documents/{document_id}/download",
    summary="Download original document",
    description="Streams the original document file with sanitized filename and content headers.",
    tags=["Documents"],
)
async def download_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    client_ip = request.client.host if request and request.client else None
    doc, storage_path, file_size, original_filename, media_type = (
        await document_service.get_document_for_download(
            session=db,
            document_id=document_id,
            current_user=current_user,
            client_ip=client_ip,
        )
    )

    storage = get_storage_service()
    return StreamingResponse(
        storage.stream_file(storage_path),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{original_filename}"',
            "Content-Length": str(file_size),
        },
    )


@router.get(
    "/documents/{document_id}/extracted-text",
    response_model=DocumentExtractedTextResponse,
    summary="Get extracted text and page breakdown",
    description="Retrieves the full extracted text with page-by-page structure and character counts.",
    tags=["Documents"],
)
async def get_extracted_text(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await document_service.get_extracted_text(
        session=db,
        document_id=document_id,
        current_user=current_user,
    )


@router.post(
    "/documents/{document_id}/extract",
    response_model=ExtractionTriggerResponse,
    summary="Trigger text extraction",
    description="Triggers or forces re-extraction of text for an uploaded document.",
    tags=["Documents"],
)
async def trigger_extraction(
    document_id: str,
    force: bool = Query(False, description="Force re-extraction if already completed"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await document_service.trigger_extraction(
        session=db,
        document_id=document_id,
        current_user=current_user,
        force=force,
    )


@router.delete(
    "/documents/{document_id}",
    summary="Delete or archive document",
    description="Soft-deletes/archives a document with audit tracking. Restricted on closed investigations.",
    tags=["Documents"],
)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    client_ip = request.client.host if request and request.client else None
    return await document_service.delete_document(
        session=db,
        document_id=document_id,
        current_user=current_user,
        client_ip=client_ip,
    )


# ---------------------------------------------------------------------------
# Evidence Association Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/documents/{document_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Associate document with evidence record",
    description="Creates a verifiable evidence item linked to this document and its parent investigation.",
    tags=["Documents"],
)
async def associate_evidence_with_document(
    document_id: str,
    payload: EvidenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await document_service.associate_evidence(
        session=db,
        document_id=document_id,
        payload=payload,
        current_user=current_user,
    )


@router.get(
    "/documents/{document_id}/evidence",
    response_model=List[EvidenceResponse],
    summary="Get evidence items for document",
    description="Returns all evidence records associated with this document.",
    tags=["Documents"],
)
async def get_document_evidence(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await document_service.get_document_detail(db, document_id, current_user)
    return await evidence_repo.get_by_document(db, document_id)
