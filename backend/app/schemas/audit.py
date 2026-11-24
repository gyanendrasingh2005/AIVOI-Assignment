from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.enums import AuditAction


class AuditLogBase(BaseModel):
    action: AuditAction
    entity_type: str
    entity_id: str
    old_values: Optional[Any] = None
    new_values: Optional[Any] = None


class AuditLogCreate(AuditLogBase):
    user_id: Optional[str] = None
    investigation_id: Optional[str] = None


class AuditLogResponse(AuditLogBase):
    id: str
    user_id: Optional[str] = None
    investigation_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
