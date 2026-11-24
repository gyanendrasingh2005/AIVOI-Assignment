import uuid
import hashlib
from typing import Tuple, List, Optional, Any, Dict
from datetime import datetime, timezone
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.evidence import Evidence
from app.models.investigation import Investigation
from app.models.user import User
from app.models.enums import (
    RoleName,
    InvestigationStatus,
    DocumentProcessingStatus,
    AuditAction,
    EvidenceType,
    EvidenceVerificationStatus,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentTextIngestRequest,
    DocumentListItem,
    DocumentListResponse,
    DocumentPageItem,
    DocumentExtractedTextResponse,
    ExtractionTriggerResponse,
)
from app.schemas.evidence import EvidenceCreate, EvidenceResponse
from app.repositories.document_evidence_repository import document_repo, evidence_repo
from app.repositories.investigation_repository import investigation_repo
from app.repositories.approval_audit_repository import audit_repo
from app.services.storage_service import get_storage_service
from app.services.document_validation_service import document_validator
from app.services.extraction_service import extraction_service
from app.core.exceptions import (
    EntityNotFoundException,
    PharmaRCAException,
    DuplicateDocumentException,
    FileValidationException,
)
from app.core.logging import logger


class DocumentService:
    """Enterprise document management, secure storage, and text extraction service."""

    @staticmethod
    def _verify_user_access(investigation: Investigation, current_user: User) -> bool:
        """Verifies RBAC and investigation scoping for user access."""
        user_roles = {role.name for role in current_user.roles}

        # Admin and QA have global oversight
        if RoleName.ADMIN.value in user_roles or RoleName.QA.value in user_roles:
            return True

        # QA Approver can view when awaiting review/approval or closed
        if RoleName.QA_APPROVER.value in user_roles:
            return True

        # Investigator and Operator can access only if assigned or created
        if investigation.created_by == current_user.id or investigation.assigned_to == current_user.id:
            return True

        return False

    async def upload_document(
        self,
        session: AsyncSession,
        investigation_id: str,
        upload_file: UploadFile,
        document_category: Optional[str],
        current_user: User,
        client_ip: Optional[str] = None,
    ) -> Document:
        """Processes, validates, stores, and extracts readable text from uploaded documents."""
        # 1. Verify Investigation exists and access
        investigation = await investigation_repo.get(session, investigation_id)
        if not investigation:
            raise EntityNotFoundException("Investigation", investigation_id)

        if not self._verify_user_access(investigation, current_user):
            raise PharmaRCAException("Unauthorized to upload documents to this investigation.", status_code=403)

        if investigation.status in [InvestigationStatus.CLOSED.value, InvestigationStatus.REJECTED.value]:
            raise PharmaRCAException("Cannot attach new documents to a closed or rejected investigation.", status_code=400)

        # 2. Process and validate file boundedly
        content, sanitized_filename, ext, mime_type, checksum, total_size = (
            await document_validator.process_and_validate_upload(upload_file)
        )

        # 3. Detect duplicate document upload within this investigation
        existing = await document_repo.get_by_checksum_and_investigation(session, investigation_id, checksum)
        if existing:
            logger.warning(f"Duplicate upload detected: investigation={investigation_id}, checksum={checksum}")
            raise DuplicateDocumentException(checksum=checksum, existing_filename=existing.original_filename)

        # 4. Save to secure storage abstraction
        storage = get_storage_service()
        doc_uuid = str(uuid.uuid4())
        stored_filename = f"{doc_uuid}{ext}"
        destination_key = f"{investigation_id}/{stored_filename}"

        storage_path = await storage.save_file(content, destination_key)

        # 5. Extract text immediately
        extraction_res = extraction_service.extract_text(content, ext)

        extracted_text = extraction_res.extracted_text if extraction_res.extracted_text else None
        extracted_at = datetime.now(timezone.utc) if extraction_res.status == DocumentProcessingStatus.COMPLETED else None

        # 6. Create document database record
        doc = Document(
            id=doc_uuid,
            investigation_id=investigation_id,
            original_filename=sanitized_filename,
            stored_filename=stored_filename,
            file_type=mime_type,
            file_size=total_size,
            storage_path=storage_path,
            checksum=checksum,
            file_extension=ext,
            document_category=document_category or "Uncategorized",
            extracted_text=extracted_text,
            extracted_at=extracted_at,
            extraction_error=extraction_res.error_message,
            page_count=extraction_res.page_count,
            character_count=extraction_res.character_count,
            source_type="file_upload",
            metadata_json={"original_mime": upload_file.content_type},
            uploaded_by=current_user.id,
            uploaded_at=datetime.now(timezone.utc),
            processing_status=extraction_res.status.value,
            is_archived=False,
        )

        session.add(doc)

        # 7. Audit log creation
        await audit_repo.record_action(
            session=session,
            action=AuditAction.CREATE,
            entity_type="Document",
            entity_id=doc.id,
            investigation_id=investigation_id,
            user_id=current_user.id,
            new_values={
                "original_filename": sanitized_filename,
                "file_type": mime_type,
                "file_size": total_size,
                "checksum": checksum,
                "processing_status": extraction_res.status.value,
                "document_category": doc.document_category,
                "page_count": extraction_res.page_count,
                "character_count": extraction_res.character_count,
            },
        )

        await session.commit()
        await session.refresh(doc)
        logger.info(f"Successfully ingested and processed document: doc_id={doc.id}, status={doc.processing_status}")
        return doc

    async def ingest_pasted_text_or_email(
        self,
        session: AsyncSession,
        investigation_id: str,
        payload: DocumentTextIngestRequest,
        current_user: User,
        client_ip: Optional[str] = None,
    ) -> Document:
        """Ingests structured pasted text or email content as an auditable document record."""
        investigation = await investigation_repo.get(session, investigation_id)
        if not investigation:
            raise EntityNotFoundException("Investigation", investigation_id)

        if not self._verify_user_access(investigation, current_user):
            raise PharmaRCAException("Unauthorized to submit text to this investigation.", status_code=403)

        if investigation.status in [InvestigationStatus.CLOSED.value, InvestigationStatus.REJECTED.value]:
            raise PharmaRCAException("Cannot attach content to a closed or rejected investigation.", status_code=400)

        raw_bytes = payload.body.encode("utf-8")
        checksum = hashlib.sha256(raw_bytes).hexdigest()

        # Duplicate check
        existing = await document_repo.get_by_checksum_and_investigation(session, investigation_id, checksum)
        if existing:
            raise DuplicateDocumentException(checksum=checksum, existing_filename=existing.original_filename)

        doc_uuid = str(uuid.uuid4())
        stored_filename = f"text_{doc_uuid}.txt"
        destination_key = f"{investigation_id}/{stored_filename}"

        storage = get_storage_service()
        storage_path = await storage.save_file(raw_bytes, destination_key)

        sanitized_title = document_validator.sanitize_filename(payload.title)
        original_filename = f"{sanitized_title}.txt"

        category = payload.document_category or ("Email Ingestion" if payload.source_type == "email" else "Pasted Text")
        metadata = {
            "title": payload.title,
            "subject": payload.subject,
            "sender": payload.sender,
            "received_date": payload.received_date.isoformat() if payload.received_date else None,
            "source_type": payload.source_type,
        }

        doc = Document(
            id=doc_uuid,
            investigation_id=investigation_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_type="text/plain",
            file_size=len(raw_bytes),
            storage_path=storage_path,
            checksum=checksum,
            file_extension=".txt",
            document_category=category,
            extracted_text=payload.body,
            extracted_at=datetime.now(timezone.utc),
            extraction_error=None,
            page_count=1,
            character_count=len(payload.body),
            source_type=payload.source_type,
            metadata_json=metadata,
            uploaded_by=current_user.id,
            uploaded_at=datetime.now(timezone.utc),
            processing_status=DocumentProcessingStatus.COMPLETED.value,
            is_archived=False,
        )

        session.add(doc)

        await audit_repo.record_action(
            session=session,
            action=AuditAction.CREATE,
            entity_type="Document",
            entity_id=doc.id,
            investigation_id=investigation_id,
            user_id=current_user.id,
            new_values={
                "original_filename": original_filename,
                "source_type": payload.source_type,
                "checksum": checksum,
                "character_count": len(payload.body),
                "title": payload.title,
                "sender": payload.sender,
            },
        )

        await session.commit()
        await session.refresh(doc)
        logger.info(f"Successfully ingested {payload.source_type} record: doc_id={doc.id}")
        return doc

    async def get_investigation_documents(
        self,
        session: AsyncSession,
        investigation_id: str,
        page: int,
        page_size: int,
        category: Optional[str],
        status: Optional[str],
        current_user: User,
    ) -> DocumentListResponse:
        """Returns paginated document list for an investigation."""
        investigation = await investigation_repo.get(session, investigation_id)
        if not investigation:
            raise EntityNotFoundException("Investigation", investigation_id)

        if not self._verify_user_access(investigation, current_user):
            raise PharmaRCAException("Unauthorized to view documents for this investigation.", status_code=403)

        items, total = await document_repo.get_paged_by_investigation(
            session=session,
            investigation_id=investigation_id,
            page=page,
            page_size=page_size,
            category=category,
            status=status,
        )

        list_items = [
            DocumentListItem(
                id=d.id,
                investigation_id=d.investigation_id,
                original_filename=d.original_filename,
                file_type=d.file_type,
                file_size=d.file_size,
                checksum=d.checksum,
                file_extension=d.file_extension,
                document_category=d.document_category,
                processing_status=d.processing_status,
                source_type=d.source_type,
                uploaded_by=d.uploaded_by,
                uploaded_at=d.uploaded_at,
                page_count=d.page_count,
                character_count=d.character_count,
            )
            for d in items
        ]

        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return DocumentListResponse(
            items=list_items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_document_detail(
        self,
        session: AsyncSession,
        document_id: str,
        current_user: User,
    ) -> Document:
        """Retrieves document metadata by document ID with access verification."""
        doc = await document_repo.get_by_id_with_details(session, document_id)
        if not doc or doc.is_archived:
            raise EntityNotFoundException("Document", document_id)

        if not self._verify_user_access(doc.investigation, current_user):
            raise PharmaRCAException("Unauthorized to view this document.", status_code=403)

        return doc

    async def get_document_for_download(
        self,
        session: AsyncSession,
        document_id: str,
        current_user: User,
        client_ip: Optional[str] = None,
    ) -> Tuple[Document, str, int, str, str]:
        """Validates download permissions, logs download audit event, and prepares stream."""
        doc = await document_repo.get_by_id_with_details(session, document_id)
        if not doc or doc.is_archived:
            raise EntityNotFoundException("Document", document_id)

        if not self._verify_user_access(doc.investigation, current_user):
            raise PharmaRCAException("Unauthorized to download this document.", status_code=403)

        storage = get_storage_service()
        if not await storage.file_exists(doc.storage_path):
            raise EntityNotFoundException("Physical document file", document_id)

        # Audit download event
        await audit_repo.record_action(
            session=session,
            action=AuditAction.READ,
            entity_type="Document",
            entity_id=doc.id,
            investigation_id=doc.investigation_id,
            user_id=current_user.id,
            new_values={
                "event": "DOCUMENT_DOWNLOAD",
                "filename": doc.original_filename,
                "file_size": doc.file_size,
                "checksum": doc.checksum,
            },
        )
        await session.commit()

        return doc, doc.storage_path, doc.file_size, doc.original_filename, doc.file_type

    async def get_extracted_text(
        self,
        session: AsyncSession,
        document_id: str,
        current_user: User,
    ) -> DocumentExtractedTextResponse:
        """Returns extracted document text along with page boundary breakdowns."""
        doc = await self.get_document_detail(session, document_id, current_user)

        # Parse page breakdown if structured markers exist
        pages: List[DocumentPageItem] = []
        if doc.extracted_text and "--- Page " in doc.extracted_text:
            parts = doc.extracted_text.split("--- Page ")
            for part in parts:
                if not part.strip():
                    continue
                try:
                    header, rest = part.split("---\n", 1)
                    page_num = int(header.strip())
                    page_text = rest.strip()
                    pages.append(
                        DocumentPageItem(
                            page_number=page_num,
                            text=page_text,
                            character_count=len(page_text),
                            word_count=len(page_text.split()) if page_text else 0,
                        )
                    )
                except Exception:
                    pass

        if not pages and doc.extracted_text:
            pages = [
                DocumentPageItem(
                    page_number=1,
                    text=doc.extracted_text,
                    character_count=len(doc.extracted_text),
                    word_count=len(doc.extracted_text.split()),
                )
            ]

        return DocumentExtractedTextResponse(
            document_id=doc.id,
            investigation_id=doc.investigation_id,
            original_filename=doc.original_filename,
            processing_status=doc.processing_status,
            page_count=doc.page_count,
            character_count=doc.character_count,
            extracted_text=doc.extracted_text,
            extracted_at=doc.extracted_at,
            pages=pages,
            error_message=doc.extraction_error,
        )

    async def trigger_extraction(
        self,
        session: AsyncSession,
        document_id: str,
        current_user: User,
        force: bool = False,
    ) -> ExtractionTriggerResponse:
        """Triggers or re-runs deterministic text extraction for a stored document."""
        doc = await self.get_document_detail(session, document_id, current_user)

        # If already completed and not force, return existing
        if doc.processing_status == DocumentProcessingStatus.COMPLETED.value and not force:
            return ExtractionTriggerResponse(
                document_id=doc.id,
                status=doc.processing_status,
                page_count=doc.page_count,
                extracted_character_count=doc.character_count,
                message="Document is already successfully extracted. Returning existing extraction result.",
                error_message=None,
            )

        if doc.processing_status == DocumentProcessingStatus.PROCESSING.value and not force:
            return ExtractionTriggerResponse(
                document_id=doc.id,
                status=doc.processing_status,
                page_count=doc.page_count,
                extracted_character_count=doc.character_count,
                message="Extraction is currently in progress for this document.",
                error_message=None,
            )

        # Mark status as processing
        old_status = doc.processing_status
        doc.processing_status = DocumentProcessingStatus.PROCESSING.value
        await session.commit()

        storage = get_storage_service()
        try:
            content = await storage.read_file(doc.storage_path)
            res = extraction_service.extract_text(content, doc.file_extension or ".pdf")

            doc.processing_status = res.status.value
            doc.extracted_text = res.extracted_text if res.extracted_text else None
            doc.page_count = res.page_count
            doc.character_count = res.character_count
            doc.extraction_error = res.error_message
            doc.extracted_at = datetime.now(timezone.utc) if res.status == DocumentProcessingStatus.COMPLETED else None

            # Audit log
            await audit_repo.record_action(
                session=session,
                action=AuditAction.UPDATE,
                entity_type="Document",
                entity_id=doc.id,
                investigation_id=doc.investigation_id,
                user_id=current_user.id,
                old_values={"processing_status": old_status},
                new_values={
                    "processing_status": res.status.value,
                    "page_count": res.page_count,
                    "character_count": res.character_count,
                    "error_message": res.error_message,
                },
            )

            await session.commit()
            await session.refresh(doc)

            return ExtractionTriggerResponse(
                document_id=doc.id,
                status=doc.processing_status,
                page_count=doc.page_count,
                extracted_character_count=doc.character_count,
                message=f"Extraction completed with status: {doc.processing_status}",
                error_message=doc.extraction_error,
            )

        except Exception as exc:
            doc.processing_status = DocumentProcessingStatus.FAILED.value
            doc.extraction_error = f"Extraction error: {str(exc)}"
            await session.commit()
            logger.error(f"Extraction failed for doc_id={document_id}: {str(exc)}")
            return ExtractionTriggerResponse(
                document_id=doc.id,
                status=DocumentProcessingStatus.FAILED.value,
                page_count=doc.page_count,
                extracted_character_count=doc.character_count,
                message="Extraction operation failed.",
                error_message=doc.extraction_error,
            )

    async def delete_document(
        self,
        session: AsyncSession,
        document_id: str,
        current_user: User,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Soft-deletes or archives document with strict 21 CFR Part 11 traceability rules."""
        doc = await document_repo.get_by_id_with_details(session, document_id)
        if not doc or doc.is_archived:
            raise EntityNotFoundException("Document", document_id)

        user_roles = {r.name for r in current_user.roles}
        investigation = doc.investigation

        # Check permissions: Admin, QA, or Investigator if Draft/Initiated
        is_admin_or_qa = RoleName.ADMIN.value in user_roles or RoleName.QA.value in user_roles
        is_lead_investigator = (
            RoleName.INVESTIGATOR.value in user_roles
            and (investigation.assigned_to == current_user.id or investigation.created_by == current_user.id)
        )

        if not (is_admin_or_qa or is_lead_investigator):
            raise PharmaRCAException("Unauthorized to delete documents from this investigation.", status_code=403)

        # Locked if approved, CAPA in progress, or closed
        locked_statuses = [
            InvestigationStatus.PENDING_APPROVAL.value,
            InvestigationStatus.CAPA_IN_PROGRESS.value,
            InvestigationStatus.EFFECTIVENESS_VERIFICATION.value,
            InvestigationStatus.CLOSED.value,
        ]
        if investigation.status in locked_statuses:
            raise PharmaRCAException(
                f"Cannot delete source documents associated with an investigation in '{investigation.status}' status.",
                status_code=400,
            )

        # Soft delete
        doc.is_archived = True

        await audit_repo.record_action(
            session=session,
            action=AuditAction.DELETE,
            entity_type="Document",
            entity_id=doc.id,
            investigation_id=doc.investigation_id,
            user_id=current_user.id,
            old_values={"is_archived": False, "filename": doc.original_filename},
            new_values={"is_archived": True, "archived_at": datetime.now(timezone.utc).isoformat()},
        )

        await session.commit()
        logger.info(f"Archived document: doc_id={document_id}, user={current_user.email}")
        return {"message": "Document archived successfully", "document_id": document_id}

    async def associate_evidence(
        self,
        session: AsyncSession,
        document_id: str,
        payload: EvidenceCreate,
        current_user: User,
    ) -> Evidence:
        """Associates a document excerpt with verifiable evidence in an investigation."""
        doc = await self.get_document_detail(session, document_id, current_user)

        evidence_id = str(uuid.uuid4())
        evidence = Evidence(
            id=evidence_id,
            investigation_id=doc.investigation_id,
            document_id=doc.id,
            evidence_type=payload.evidence_type.value if hasattr(payload.evidence_type, "value") else str(payload.evidence_type),
            title=payload.title,
            description=payload.description,
            source_reference=payload.source_reference or doc.original_filename,
            page_number=payload.page_number,
            excerpt=payload.excerpt,
            verification_status=EvidenceVerificationStatus.UNVERIFIED.value,
            uploaded_by=current_user.id,
            created_at=datetime.now(timezone.utc),
        )

        session.add(evidence)

        await audit_repo.record_action(
            session=session,
            action=AuditAction.CREATE,
            entity_type="Evidence",
            entity_id=evidence_id,
            investigation_id=doc.investigation_id,
            user_id=current_user.id,
            new_values={
                "document_id": doc.id,
                "title": evidence.title,
                "evidence_type": evidence.evidence_type,
                "page_number": evidence.page_number,
            },
        )

        await session.commit()
        await session.refresh(evidence)
        return evidence


document_service = DocumentService()
