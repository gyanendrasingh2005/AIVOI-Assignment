from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.evidence import Evidence
from app.schemas.document import DocumentCreate, DocumentBase
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document, DocumentCreate, DocumentBase]):
    def __init__(self):
        super().__init__(Document)

    async def get_by_investigation(
        self, session: AsyncSession, investigation_id: str
    ) -> List[Document]:
        """Returns non-archived documents for an investigation."""
        stmt = (
            select(Document)
            .where(
                and_(
                    Document.investigation_id == investigation_id,
                    Document.is_archived == False,
                )
            )
            .order_by(Document.uploaded_at.desc())
            .options(selectinload(Document.evidence_items))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_paged_by_investigation(
        self,
        session: AsyncSession,
        investigation_id: str,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Document], int]:
        """Returns paginated non-archived documents matching optional filters, plus total count."""
        base_conditions = [
            Document.investigation_id == investigation_id,
            Document.is_archived == False,
        ]

        if category:
            base_conditions.append(Document.document_category == category)
        if status:
            base_conditions.append(Document.processing_status.ilike(status))

        count_stmt = select(func.count(Document.id)).where(and_(*base_conditions))
        total_count = (await session.execute(count_stmt)).scalar() or 0

        offset = max(0, (page - 1) * page_size)
        query = (
            select(Document)
            .where(and_(*base_conditions))
            .order_by(Document.uploaded_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await session.execute(query)
        items = list(result.scalars().all())

        return items, total_count

    async def get_by_stored_filename(
        self, session: AsyncSession, stored_filename: str
    ) -> Optional[Document]:
        stmt = select(Document).where(Document.stored_filename == stored_filename)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_checksum_and_investigation(
        self, session: AsyncSession, investigation_id: str, checksum: str
    ) -> Optional[Document]:
        """Detects duplicate document uploads within an investigation."""
        stmt = select(Document).where(
            and_(
                Document.investigation_id == investigation_id,
                Document.checksum == checksum,
                Document.is_archived == False,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_details(
        self, session: AsyncSession, document_id: str
    ) -> Optional[Document]:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(
                selectinload(Document.investigation),
                selectinload(Document.evidence_items),
                selectinload(Document.uploader),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def archive_document(
        self, session: AsyncSession, document_id: str
    ) -> Optional[Document]:
        doc = await self.get(session, document_id)
        if doc:
            doc.is_archived = True
            await session.commit()
            await session.refresh(doc)
        return doc


class EvidenceRepository(BaseRepository[Evidence, EvidenceCreate, EvidenceUpdate]):
    def __init__(self):
        super().__init__(Evidence)

    async def get_by_investigation(
        self, session: AsyncSession, investigation_id: str
    ) -> List[Evidence]:
        stmt = (
            select(Evidence)
            .where(Evidence.investigation_id == investigation_id)
            .options(selectinload(Evidence.document))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_document(
        self, session: AsyncSession, document_id: str
    ) -> List[Evidence]:
        stmt = select(Evidence).where(Evidence.document_id == document_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())


document_repo = DocumentRepository()
evidence_repo = EvidenceRepository()
