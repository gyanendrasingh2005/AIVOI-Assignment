from typing import Optional, List, Any, Tuple
from sqlalchemy import select, func, or_, delete, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Role, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        normalized_email = email.strip().lower()
        stmt = (
            select(User)
            .where(func.lower(User.email) == normalized_email)
            .options(selectinload(User.roles))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_roles(self, session: AsyncSession, id: str) -> Optional[User]:
        stmt = (
            select(User)
            .where(User.id == id)
            .options(selectinload(User.roles))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_users_paged(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
    ) -> Tuple[List[User], int]:
        """
        Retrieves paginated users supporting substring search and role filtering.
        """
        stmt = select(User).options(selectinload(User.roles))
        count_stmt = select(func.count(func.distinct(User.id)))

        conditions = []
        if search:
            search_pattern = f"%{search.strip()}%"
            conditions.append(
                or_(
                    User.full_name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                )
            )

        if role:
            # Filter users that have the specified role
            stmt = stmt.join(User.user_roles).join(UserRole.role).where(Role.name == role)
            count_stmt = count_stmt.join(User.user_roles).join(UserRole.role).where(Role.name == role)

        if conditions:
            stmt = stmt.where(*conditions)
            count_stmt = count_stmt.where(*conditions)

        # Count total
        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one() or 0

        # Fetch records
        stmt = stmt.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await session.execute(stmt)
        users = list(result.scalars().unique().all())

        return users, total

    async def create_user(
        self, session: AsyncSession, *, obj_in: UserCreate, hashed_password: str
    ) -> User:
        user_data = obj_in.model_dump(exclude={"password", "role_ids"})
        user_data["email"] = user_data["email"].strip().lower()
        user = User(**user_data, hashed_password=hashed_password)
        session.add(user)
        await session.flush()

        # Associate roles
        for role_id in obj_in.role_ids:
            user_role = UserRole(user_id=user.id, role_id=role_id)
            session.add(user_role)

        await session.flush()
        return await self.get_with_roles(session, user.id) or user

    async def assign_role(
        self, session: AsyncSession, *, user_id: str, role_id: str
    ) -> UserRole:
        """Assigns a role to a user if not already assigned."""
        existing_stmt = select(UserRole).where(
            UserRole.user_id == user_id, UserRole.role_id == role_id
        )
        existing = await session.execute(existing_stmt)
        user_role = existing.scalar_one_or_none()
        if user_role:
            return user_role

        user_role = UserRole(user_id=user_id, role_id=role_id)
        session.add(user_role)
        await session.flush()
        return user_role

    async def revoke_role(
        self, session: AsyncSession, *, user_id: str, role_id: str
    ) -> bool:
        """Revokes a role assignment from a user."""
        stmt = delete(UserRole).where(
            UserRole.user_id == user_id, UserRole.role_id == role_id
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount > 0

    async def update_status(
        self, session: AsyncSession, *, user_id: str, is_active: bool
    ) -> Optional[User]:
        """Toggles account active status."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(is_active=is_active)
            .returning(User)
        )
        await session.execute(stmt)
        await session.flush()
        return await self.get_with_roles(session, user_id)

    async def update_password(
        self, session: AsyncSession, *, user_id: str, hashed_password: str
    ) -> bool:
        """Updates user hashed password."""
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=hashed_password)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount > 0


class RoleRepository(BaseRepository[Role, Any, Any]):
    def __init__(self):
        super().__init__(Role)

    async def get_by_name(self, session: AsyncSession, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_roles(self, session: AsyncSession) -> List[Role]:
        stmt = select(Role).order_by(Role.name.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())


user_repo = UserRepository()
role_repo = RoleRepository()
