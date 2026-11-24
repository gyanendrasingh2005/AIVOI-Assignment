from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import ApprovalStatus
from app.schemas.user import UserResponse


class ApprovalBase(BaseModel):
    approval_status: ApprovalStatus = ApprovalStatus.APPROVED
    comments: Optional[str] = None


class ApprovalCreate(ApprovalBase):
    investigation_id: str
    reviewer_id: str


class ApprovalResponse(ApprovalBase):
    id: str
    investigation_id: str
    reviewer_id: str
    reviewed_at: datetime
    reviewer: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)
