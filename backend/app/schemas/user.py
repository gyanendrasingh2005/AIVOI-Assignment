from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field


class RoleBase(BaseModel):
    name: str = Field(..., max_length=50, description="Role name (e.g. Admin, QA, QC, Investigator)")
    description: Optional[str] = Field(None, max_length=255)


class RoleResponse(RoleBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Plaintext password to be hashed")
    role_ids: List[str] = Field(default_factory=list, description="List of role IDs to assign")


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime
    roles: List[RoleResponse] = []

    model_config = ConfigDict(from_attributes=True)
