import re
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.document import Document
from app.models.enums import DocumentProcessingStatus
from app.schemas.extraction import DocumentProcessingSummary
from app.repositories.document_evidence_repository import document_repo


class DocumentContextPreparationService:
    """
    Service responsible for assembling, sanitizing, and bounding document text context
    for AI incident extraction.
    Enforces security boundaries:
    - Never leaks internal storage paths to AI providers.
    - Strictly confines retrieval to the requested investigation.
    - Accurately reports OCR_REQUIRED and FAILED document states without sending bogus content.
    - Preserves document IDs, filenames, and page markers for citation traceability.
    """

    DEFAULT_MAX_CONTEXT_CHARS = 32000

    async def prepare_context(
        self,
        session: AsyncSession,
        investigation_id: str,
        document_ids: Optional[List[str]] = None,
        max_chars: Optional[int] = None,
    ) -> Tuple[str, List[DocumentProcessingSummary], List[Document]]:
        """
        Retrieves requested documents, validates investigation ownership,
        builds document processing summaries, and compiles bounded, structured text.
        """
        max_length = max_chars or self.DEFAULT_MAX_CONTEXT_CHARS
        summaries: List[DocumentProcessingSummary] = []
        analyzable_docs: List[Document] = []
        context_parts: List[str] = []
        current_length = 0

        if document_ids is None:
            docs_to_process = await document_repo.get_by_investigation(session, investigation_id)
        else:
            docs_to_process = []
            for doc_id in document_ids:
                doc = await document_repo.get(session, doc_id)
                if not doc:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Source document {doc_id} not found.",
                    )
                if doc.investigation_id != investigation_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Security violation: Document {doc_id} does not belong to investigation {investigation_id}.",
                    )
                docs_to_process.append(doc)

        for doc in docs_to_process:

            # Check for archived status
            if doc.is_archived:
                summaries.append(
                    DocumentProcessingSummary(
                        document_id=doc.id,
                        filename=doc.original_filename,
                        status="ARCHIVED",
                        page_count=doc.page_count,
                        notes="Document is archived and excluded from analysis.",
                    )
                )
                continue

            # Check processing status
            proc_status = (doc.processing_status or "").upper()
            if proc_status == DocumentProcessingStatus.OCR_REQUIRED.value.upper():
                summaries.append(
                    DocumentProcessingSummary(
                        document_id=doc.id,
                        filename=doc.original_filename,
                        status="OCR_REQUIRED",
                        page_count=doc.page_count,
                        notes="Scanned document requiring OCR before text can be analyzed.",
                    )
                )
                continue

            if proc_status == DocumentProcessingStatus.FAILED.value.upper():
                summaries.append(
                    DocumentProcessingSummary(
                        document_id=doc.id,
                        filename=doc.original_filename,
                        status="FAILED",
                        page_count=doc.page_count,
                        notes=f"Text extraction failed: {doc.extraction_error or 'Unknown error'}",
                    )
                )
                continue

            raw_text = (doc.extracted_text or "").strip()
            if not raw_text:
                summaries.append(
                    DocumentProcessingSummary(
                        document_id=doc.id,
                        filename=doc.original_filename,
                        status="EMPTY",
                        page_count=doc.page_count,
                        notes="Document has zero extractable characters.",
                    )
                )
                continue

            # Document is valid and has extracted text
            analyzable_docs.append(doc)
            summaries.append(
                DocumentProcessingSummary(
                    document_id=doc.id,
                    filename=doc.original_filename,
                    status="ANALYZED",
                    page_count=doc.page_count,
                    notes="Successfully staged for incident extraction.",
                )
            )

            # Format document block with metadata (no storage paths!)
            doc_header = (
                f"\n--- SOURCE DOCUMENT BEGIN ---\n"
                f"DOCUMENT_ID: {doc.id}\n"
                f"FILENAME: {doc.original_filename}\n"
                f"TOTAL_PAGES: {doc.page_count or 'Unknown'}\n"
                f"CATEGORY: {doc.document_category or 'General Record'}\n"
                f"CONTENT:\n"
            )
            doc_footer = "\n--- SOURCE DOCUMENT END ---\n"

            # Check length budget
            available_budget = max_length - current_length - len(doc_header) - len(doc_footer)
            if available_budget <= 200:
                # Context limit reached
                break

            if len(raw_text) > available_budget:
                truncated_text = raw_text[:available_budget] + "\n[... Document truncated due to context limit ...]"
                block = f"{doc_header}{truncated_text}{doc_footer}"
            else:
                block = f"{doc_header}{raw_text}{doc_footer}"

            context_parts.append(block)
            current_length += len(block)

        compiled_context = "".join(context_parts)
        return compiled_context, summaries, analyzable_docs


document_context_service = DocumentContextPreparationService()

