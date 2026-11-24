from typing import List, Callable, Optional, Set
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import PharmaRCAException
from app.core.security import decode_jwt_token
from app.core.permissions import (
    Permission,
    ROLE_PERMISSIONS,
    get_permissions_for_roles,
    has_permission,
)
from app.models.enums import RoleName
from app.models.user import User
from app.models.investigation import Investigation
from app.database.session import get_db
from app.repositories.user_repository import user_repo


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    scheme_name="PharmaRCA_Bearer",
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Validates JWT access token, checks expiration, signature, and active status.
    """
    payload = decode_jwt_token(token)

    token_type = payload.get("type")
    if token_type != "access":
        raise PharmaRCAException(
            message="Invalid token type: access token required.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"code": "INVALID_TOKEN_TYPE"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise PharmaRCAException(
            message="Token claim missing user identifier.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"code": "MALFORMED_TOKEN"},
        )

    user = await user_repo.get_with_roles(session, user_id)
    if not user:
        raise PharmaRCAException(
            message="User account associated with this token was not found.",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details={"code": "USER_NOT_FOUND"},
        )

    if not user.is_active:
        raise PharmaRCAException(
            message="Account has been suspended or deactivated. Contact your Quality Administrator.",
            status_code=status.HTTP_403_FORBIDDEN,
            details={"code": "ACCOUNT_DEACTIVATED"},
        )

    return user


async def get_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Convenience dependency returning an active user."""
    if not current_user.is_active:
        raise PharmaRCAException(
            message="Account is inactive.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return current_user


def require_roles(*allowed_roles: RoleName) -> Callable:
    """
    Factory creating a dependency that verifies the user possesses at least one of the specified roles.
    """
    allowed_role_names = {r.value if isinstance(r, RoleName) else str(r) for r in allowed_roles}

    async def role_checker(current_user: User = Depends(get_active_user)) -> User:
        user_role_names = {r.name for r in current_user.roles}
        if not user_role_names.intersection(allowed_role_names):
            raise PharmaRCAException(
                message=f"Access denied: Requires one of the following roles: {', '.join(allowed_role_names)}.",
                status_code=status.HTTP_403_FORBIDDEN,
                details={
                    "required_roles": list(allowed_role_names),
                    "user_roles": list(user_role_names),
                },
            )
        return current_user

    return role_checker


def require_permissions(*required_permissions: Permission) -> Callable:
    """
    Factory creating a dependency that verifies the user possesses ALL specified permissions.
    """
    required_perm_values = {
        p.value if isinstance(p, Permission) else str(p) for p in required_permissions
    }

    async def permission_checker(
        current_user: User = Depends(get_active_user),
    ) -> User:
        user_roles = [r.name for r in current_user.roles]
        user_perms = get_permissions_for_roles(user_roles)

        missing_perms = required_perm_values - user_perms
        if missing_perms:
            raise PharmaRCAException(
                message=f"Access denied: Missing required permission(s): {', '.join(missing_perms)}.",
                status_code=status.HTTP_403_FORBIDDEN,
                details={
                    "missing_permissions": list(missing_perms),
                    "granted_permissions": list(user_perms),
                },
            )
        return current_user

    return permission_checker


async def verify_investigation_access(
    investigation: Investigation,
    user: User,
) -> bool:
    """
    Verifies if a user has authorization to access or mutate an investigation:
    - Admin, QA, QA Approver have full oversight.
    - Investigators and Operators can only access if they created or are assigned to the investigation.
    """
    user_roles = {r.name for r in user.roles}
    privileged_roles = {RoleName.ADMIN.value, RoleName.QA.value, RoleName.QA_APPROVER.value}

    if user_roles.intersection(privileged_roles):
        return True

    # Check assignment/creation
    if investigation.created_by == user.id or investigation.assigned_to == user.id:
        return True

    return False
