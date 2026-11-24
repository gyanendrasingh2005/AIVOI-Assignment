import copy
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident_extraction import IncidentExtraction
from app.models.enums import ExtractionStatus, ExtractionReviewStatus
from app.repositories.base import BaseRepository
from app.schemas.extraction import IncidentExtractionResponse


class IncidentExtractionRepository(BaseRepository[IncidentExtraction, IncidentExtractionResponse, IncidentExtractionResponse]):
    """Repository managing persistence, retrieval, and human review states for AI incident extractions."""

    def __init__(self):
        super().__init__(IncidentExtraction)

    async def get_by_investigation(
        self, session: AsyncSession, investigation_id: str, skip: int = 0, limit: int = 50
    ) -> List[IncidentExtraction]:
        """Returns all extraction records for an investigation ordered newest first."""
        stmt = (
            select(self.model)
            .where(self.model.investigation_id == investigation_id)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_extraction_record(
        self,
        session: AsyncSession,
        *,
        investigation_id: str,
        ai_execution_id: Optional[str],
        created_by: Optional[str],
        source_document_ids: List[str],
        provider: str,
        model: str,
        prompt_version: str,
        document_summaries: List[Dict[str, Any]],
    ) -> IncidentExtraction:
        db_obj = self.model(
            investigation_id=investigation_id,
            ai_execution_id=ai_execution_id,
            created_by=created_by,
            source_document_ids=source_document_ids,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            status=ExtractionStatus.PENDING.value,
            review_status=ExtractionReviewStatus.PENDING_REVIEW.value,
            extracted_fields={},
            missing_information=[],
            conflicting_information=[],
            document_summaries=document_summaries,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def update_extraction_completion(
        self,
        session: AsyncSession,
        *,
        extraction_id: str,
        status: str,
        extracted_fields: Dict[str, Any],
        missing_information: List[Dict[str, Any]],
        conflicting_information: List[Dict[str, Any]],
        document_summaries: List[Dict[str, Any]],
    ) -> Optional[IncidentExtraction]:
        db_obj = await self.get(session, extraction_id)
        if not db_obj:
            return None

        db_obj.status = status
        db_obj.extracted_fields = copy.deepcopy(extracted_fields)
        db_obj.missing_information = copy.deepcopy(missing_information)
        db_obj.conflicting_information = copy.deepcopy(conflicting_information)
        db_obj.document_summaries = copy.deepcopy(document_summaries)
        db_obj.updated_at = datetime.now(timezone.utc)

        flag_modified(db_obj, "extracted_fields")
        flag_modified(db_obj, "missing_information")
        flag_modified(db_obj, "conflicting_information")
        flag_modified(db_obj, "document_summaries")

        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def save_review_state(
        self,
        session: AsyncSession,
        *,
        extraction_id: str,
        review_status: str,
        extracted_fields: Dict[str, Any],
        reviewed_by: str,
    ) -> Optional[IncidentExtraction]:
        db_obj = await self.get(session, extraction_id)
        if not db_obj:
            return None

        db_obj.review_status = review_status
        db_obj.extracted_fields = copy.deepcopy(extracted_fields)
        db_obj.reviewed_by = reviewed_by
        db_obj.reviewed_at = datetime.now(timezone.utc)
        db_obj.updated_at = datetime.now(timezone.utc)

        flag_modified(db_obj, "extracted_fields")

        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj


incident_extraction_repo = IncidentExtractionRepository()
