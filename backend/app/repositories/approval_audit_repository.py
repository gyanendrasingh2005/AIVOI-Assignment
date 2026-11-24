from typing import Optional, List, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import Approval
from app.models.audit import AuditLog
from app.schemas.approval import ApprovalCreate, ApprovalBase
from app.schemas.audit import AuditLogCreate, AuditLogBase
from app.repositories.base import BaseRepository


class ApprovalRepository(BaseRepository[Approval, ApprovalCreate, ApprovalBase]):
    def __init__(self):
        super().__init__(Approval)

    async def get_by_investigation(
        self, session: AsyncSession, investigation_id: str
    ) -> List[Approval]:
        stmt = (
            select(Approval)
            .where(Approval.investigation_id == investigation_id)
            .options(selectinload(Approval.reviewer))
            .order_by(Approval.reviewed_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


class AuditLogRepository(BaseRepository[AuditLog, AuditLogCreate, AuditLogBase]):
    def __init__(self):
        super().__init__(AuditLog)

    async def log_event(
        self,
        session: AsyncSession,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: Optional[str] = None,
        investigation_id: Optional[str] = None,
        old_values: Optional[Any] = None,
        new_values: Optional[Any] = None,
    ) -> AuditLog:
        audit_entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            investigation_id=investigation_id,
            old_values=old_values,
            new_values=new_values,
        )
        session.add(audit_entry)
        await session.flush()
        await session.refresh(audit_entry)
        return audit_entry

    async def get_history_for_entity(
        self, session: AsyncSession, entity_type: str, entity_id: str
    ) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


approval_repo = ApprovalRepository()
audit_repo = AuditLogRepository()
