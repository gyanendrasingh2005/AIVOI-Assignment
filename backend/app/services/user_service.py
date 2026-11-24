from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import (
    PharmaRCAException,
    EntityNotFoundException,
    ValidationException,
)
from app.models.enums import RoleName
from app.models.user import User, Role, UserRole
from app.schemas.user import (
    UserResponse,
    UserListResponse,
    UserProfileUpdate,
    UserStatusUpdate,
)
from app.repositories.user_repository import user_repo, role_repo
from app.repositories.token_repository import token_repo


class UserService:
    """Service handling user directory search, profile updates, and role assignments."""

    async def list_users(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
    ) -> UserListResponse:
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        skip = (page - 1) * page_size
        users, total = await user_repo.get_users_paged(
            session, skip=skip, limit=page_size, search=search, role=role
        )
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return UserListResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_user_by_id(
        self, session: AsyncSession, user_id: str
    ) -> UserResponse:
        user = await user_repo.get_with_roles(session, user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)
        return UserResponse.model_validate(user)

    async def update_profile(
        self,
        session: AsyncSession,
        *,
        current_user: User,
        profile_in: UserProfileUpdate,
    ) -> UserResponse:
        """
        Updates profile information.
        Security Rule: Role updates or privilege modifications are strictly prohibited here.
        """
        if profile_in.full_name is not None:
            current_user.full_name = profile_in.full_name.strip()
            session.add(current_user)
            await session.commit()
            user = await user_repo.get_with_roles(session, current_user.id)
            return UserResponse.model_validate(user or current_user)
        return UserResponse.model_validate(current_user)

    async def update_user_status(
        self,
        session: AsyncSession,
        *,
        current_admin: User,
        user_id: str,
        status_in: UserStatusUpdate,
    ) -> UserResponse:
        # Prevent self-deactivation by an administrator
        if current_admin.id == user_id and not status_in.is_active:
            raise PharmaRCAException(
                message="Administrators cannot suspend their own active account.",
                status_code=400,
                details={"code": "SELF_DEACTIVATION_PROHIBITED"},
            )

        user = await user_repo.get_with_roles(session, user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)

        # If deactivating, revoke all active sessions immediately
        if not status_in.is_active:
            await token_repo.revoke_all_user_tokens(session, user_id)

        updated_user = await user_repo.update_status(
            session, user_id=user_id, is_active=status_in.is_active
        )
        await session.commit()
        return UserResponse.model_validate(updated_user or user)

    async def assign_role(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        role_id: str,
    ) -> UserResponse:
        user = await user_repo.get_with_roles(session, user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)

        role = await role_repo.get(session, role_id)
        if not role:
            raise EntityNotFoundException("Role", role_id)

        await user_repo.assign_role(session, user_id=user_id, role_id=role_id)
        await session.commit()
        session.expire_all()

        reloaded = await user_repo.get_with_roles(session, user_id)
        return UserResponse.model_validate(reloaded)

    async def revoke_role(
        self,
        session: AsyncSession,
        *,
        current_admin: User,
        user_id: str,
        role_id: str,
    ) -> UserResponse:
        user = await user_repo.get_with_roles(session, user_id)
        if not user:
            raise EntityNotFoundException("User", user_id)

        role = await role_repo.get(session, role_id)
        if not role:
            raise EntityNotFoundException("Role", role_id)

        # Safeguard: prevent removing the last admin from an admin account
        if role.name == RoleName.ADMIN.value and current_admin.id == user_id:
            # Check if there are other active admins in the system
            admin_stmt = (
                select(User)
                .join(User.user_roles)
                .join(UserRole.role)
                .where(Role.name == RoleName.ADMIN.value, User.is_active.is_(True))
            )
            res = await session.execute(admin_stmt)
            active_admins = res.scalars().unique().all()
            if len(active_admins) <= 1:
                raise PharmaRCAException(
                    message="Cannot revoke the Admin role: at least one active administrator is required.",
                    status_code=400,
                    details={"code": "LAST_ADMIN_REVOCATION_PROHIBITED"},
                )

        await user_repo.revoke_role(session, user_id=user_id, role_id=role_id)
        await session.commit()
        session.expire_all()

        reloaded = await user_repo.get_with_roles(session, user_id)
        return UserResponse.model_validate(reloaded)


user_service = UserService()
