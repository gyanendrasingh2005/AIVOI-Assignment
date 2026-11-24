from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.api.deps import (
    get_current_user,
    require_permissions,
)
from app.core.permissions import Permission
from app.models.user import User
from app.schemas.user import (
    UserResponse,
    UserListResponse,
    UserProfileUpdate,
    UserStatusUpdate,
    UserRoleAssign,
)
from app.services.user_service import user_service

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Retrieves the authenticated user's current identity and roles.",
)
async def get_user_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    description="Updates non-sensitive profile information such as full name. Privilege or role modification is rejected.",
)
async def update_user_me(
    profile_in: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await user_service.update_profile(
        session, current_user=current_user, profile_in=profile_in
    )


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List quality personnel",
    description="Searches and filters registered users with pagination. Requires USERS_VIEW permission.",
)
async def list_users(
    page: int = Query(1, ge=1, description="Page index"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Substring search by full name or email"),
    role: Optional[str] = Query(None, description="Filter by assigned role name"),
    current_user: User = Depends(require_permissions(Permission.USERS_VIEW)),
    session: AsyncSession = Depends(get_db),
) -> UserListResponse:
    return await user_service.list_users(
        session, page=page, page_size=page_size, search=search, role=role
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user details by ID",
    description="Retrieves user profile and role assignments by user identifier.",
)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    # Allow user to view their own ID, or require USERS_VIEW permission for others
    if current_user.id != user_id:
        has_perm_dep = require_permissions(Permission.USERS_VIEW)
        await has_perm_dep(current_user)

    return await user_service.get_user_by_id(session, user_id=user_id)


@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user active status",
    description="Activates or deactivates a user account. Requires USERS_MANAGE permission.",
)
async def update_user_status(
    user_id: str,
    status_in: UserStatusUpdate,
    current_admin: User = Depends(require_permissions(Permission.USERS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await user_service.update_user_status(
        session, current_admin=current_admin, user_id=user_id, status_in=status_in
    )


@router.post(
    "/{user_id}/roles",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign role to user",
    description="Grants an enterprise role to a user. Requires ROLES_MANAGE permission.",
)
async def assign_role(
    user_id: str,
    role_in: UserRoleAssign,
    current_admin: User = Depends(require_permissions(Permission.ROLES_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await user_service.assign_role(
        session, user_id=user_id, role_id=role_in.role_id
    )


@router.delete(
    "/{user_id}/roles/{role_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke role from user",
    description="Revokes an enterprise role from a user. Requires ROLES_MANAGE permission.",
)
async def revoke_role(
    user_id: str,
    role_id: str,
    current_admin: User = Depends(require_permissions(Permission.ROLES_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    return await user_service.revoke_role(
        session, current_admin=current_admin, user_id=user_id, role_id=role_id
    )
