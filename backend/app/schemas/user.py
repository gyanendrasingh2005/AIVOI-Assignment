from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field, model_validator

from app.core.security import validate_password_complexity


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


class UserRegister(BaseModel):
    """Public registration schema with mandatory password verification."""

    full_name: str = Field(..., min_length=2, max_length=255, description="Full legal name of the quality practitioner")
    email: EmailStr = Field(..., description="Enterprise email address")
    password: str = Field(..., min_length=8, description="Secure password complying with complexity rules")
    confirm_password: str = Field(..., min_length=8, description="Confirmation matching the password")

    @model_validator(mode="after")
    def validate_registration(self) -> "UserRegister":
        # Normalize email
        self.email = self.email.strip().lower()

        # Enforce password match
        if self.password != self.confirm_password:
            raise ValueError("Password and confirmation password do not match.")

        # Enforce complexity standards
        is_valid, error_msg = validate_password_complexity(self.password)
        if not is_valid:
            raise ValueError(error_msg)

        return self


class UserLogin(BaseModel):
    """Authentication login credential payload."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Account password")

    @model_validator(mode="after")
    def normalize_credentials(self) -> "UserLogin":
        self.email = self.email.strip().lower()
        return self


class PasswordChange(BaseModel):
    """Change password payload requiring current password verification."""

    current_password: str = Field(..., min_length=1, description="Current valid password")
    new_password: str = Field(..., min_length=8, description="New secure password")
    confirm_new_password: str = Field(..., min_length=8, description="Confirmation of new password")

    @model_validator(mode="after")
    def validate_password_change(self) -> "PasswordChange":
        if self.new_password != self.confirm_new_password:
            raise ValueError("New password and confirmation do not match.")
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password.")

        is_valid, error_msg = validate_password_complexity(self.new_password)
        if not is_valid:
            raise ValueError(error_msg)
        return self


class UserProfileUpdate(BaseModel):
    """Profile self-service update schema (strictly prohibits role changes)."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)


class UserStatusUpdate(BaseModel):
    """Administrative schema to activate or suspend a user account."""

    is_active: bool = Field(..., description="Active status for authentication")


class UserRoleAssign(BaseModel):
    """Administrative schema for role assignment."""

    role_id: str = Field(..., min_length=36, max_length=36, description="UUID of the role to assign")


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


class UserListResponse(BaseModel):
    """Paginated list of user entities."""

    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
