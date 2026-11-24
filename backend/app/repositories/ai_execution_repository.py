from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_execution import AIExecution
from app.models.enums import AIExecutionStatus
from app.repositories.base import BaseRepository
from app.ai.schemas.execution import AIExecutionCreate


class AIExecutionRepository(BaseRepository[AIExecution, AIExecutionCreate, AIExecutionCreate]):
    """Repository managing persistence and retrieval of AI orchestration executions."""

    def __init__(self):
        super().__init__(AIExecution)

    async def get_by_workflow_id(
        self, session: AsyncSession, workflow_id: str
    ) -> Optional[AIExecution]:
        stmt = select(self.model).where(self.model.workflow_id == workflow_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_investigation(
        self, session: AsyncSession, investigation_id: str, skip: int = 0, limit: int = 50
    ) -> List[AIExecution]:
        stmt = (
            select(self.model)
            .where(self.model.investigation_id == investigation_id)
            .order_by(desc(self.model.started_at))
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def record_execution_start(
        self, session: AsyncSession, create_in: AIExecutionCreate
    ) -> AIExecution:
        db_obj = self.model(
            workflow_id=create_in.workflow_id,
            workflow_type=create_in.workflow_type,
            investigation_id=create_in.investigation_id,
            user_id=create_in.user_id,
            provider=create_in.provider,
            model=create_in.model,
            prompt_version=create_in.prompt_version,
            status=AIExecutionStatus.PENDING.value,
            input_context_summary=create_in.input_context_summary,
            started_at=datetime.now(timezone.utc),
        )
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def record_execution_completion(
        self,
        session: AsyncSession,
        execution_id: str,
        status: str,
        structured_output: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        token_usage: Optional[Dict[str, Any]] = None,
        latency_ms: Optional[int] = None,
    ) -> Optional[AIExecution]:
        db_obj = await self.get(session, execution_id)
        if not db_obj:
            return None

        db_obj.status = status
        db_obj.structured_output = structured_output
        db_obj.error_message = error_message
        db_obj.token_usage = token_usage
        db_obj.latency_ms = latency_ms
        db_obj.completed_at = datetime.now(timezone.utc)

        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj


ai_execution_repo = AIExecutionRepository()

