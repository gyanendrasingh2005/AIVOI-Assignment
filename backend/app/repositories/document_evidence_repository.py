from typing import Optional, List
from sqlalchemy import select
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
        stmt = (
            select(Document)
            .where(Document.investigation_id == investigation_id)
            .options(selectinload(Document.evidence_items))
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_stored_filename(
        self, session: AsyncSession, stored_filename: str
    ) -> Optional[Document]:
        stmt = select(Document).where(Document.stored_filename == stored_filename)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


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
