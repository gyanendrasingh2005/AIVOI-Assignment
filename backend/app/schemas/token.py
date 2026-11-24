from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.user import UserResponse


class TokenResponse(BaseModel):
    """Payload returned upon successful authentication or token refresh."""

    access_token: str = Field(..., description="Signed short-lived JWT access token")
    refresh_token: str = Field(..., description="Signed long-lived JWT refresh token")
    token_type: str = Field("bearer", description="Token scheme (bearer)")
    expires_in: int = Field(..., description="Access token lifespan in seconds")
    user: UserResponse = Field(..., description="Authenticated user profile and role details")

    model_config = ConfigDict(from_attributes=True)


class TokenRefreshRequest(BaseModel):
    """Payload to request access token rotation."""

    refresh_token: str = Field(..., description="Active JWT refresh token")


class TokenRevokeRequest(BaseModel):
    """Optional payload when revoking a specific session refresh token."""

    refresh_token: Optional[str] = Field(None, description="Target refresh token to revoke upon logout")


class TokenPayload(BaseModel):
    """Decoded internal representation of JWT claims."""

    sub: str
    iat: int
    exp: int
    jti: str
    type: str
    family_id: Optional[str] = None
    roles: List[str] = []
    permissions: List[str] = []
