from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserRegister,
    UserLogin,
    PasswordChange,
    UserResponse,
)
from app.schemas.token import (
    TokenResponse,
    TokenRefreshRequest,
    TokenRevokeRequest,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
    description="Registers a new quality practitioner account with default Investigator role.",
)
async def register(
    register_in: UserRegister,
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await auth_service.register(session, register_in)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User authentication login",
    description="Authenticates credentials and returns a short-lived access token and rotated refresh token.",
)
async def login(
    login_in: UserLogin,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    device_info = f"{request.client.host if request.client else 'unknown'} | {request.headers.get('user-agent', 'unknown')[:100]}"
    return await auth_service.login(session, login_in, device_info=device_info)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate JWT refresh and access tokens",
    description="Rotates refresh token and returns a new access/refresh token pair. Detects token replay attacks.",
)
async def refresh(
    refresh_in: TokenRefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    device_info = f"{request.client.host if request.client else 'unknown'} | {request.headers.get('user-agent', 'unknown')[:100]}"
    return await auth_service.refresh_tokens(session, refresh_in, device_info=device_info)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout user session",
    description="Revokes the active refresh token session.",
)
async def logout(
    revoke_in: Optional[TokenRevokeRequest] = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    refresh_token = revoke_in.refresh_token if revoke_in else None
    await auth_service.logout(session, current_user, refresh_token)
    return {"message": "Successfully logged out from current session."}


@router.post(
    "/logout-all",
    status_code=status.HTTP_200_OK,
    summary="Logout from all sessions",
    description="Revokes all active refresh token sessions for the authenticated user.",
)
async def logout_all(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    count = await auth_service.logout_all(session, current_user)
    return {"message": f"Successfully revoked {count} active sessions."}


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user details",
    description="Retrieves the authenticated user's profile and assigned roles.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change user password",
    description="Verifies the current password and sets a new password, invalidating previous sessions.",
)
async def change_password(
    password_in: PasswordChange,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await auth_service.change_password(session, current_user, password_in)
    return {"message": "Password changed successfully. Please re-authenticate."}
