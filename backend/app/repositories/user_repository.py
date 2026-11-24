from typing import Optional, List, Any
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Role, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .where(User.email == email)
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

    async def create_user(
        self, session: AsyncSession, *, obj_in: UserCreate, hashed_password: str
    ) -> User:
        user_data = obj_in.model_dump(exclude={"password", "role_ids"})
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
        user_role = UserRole(user_id=user_id, role_id=role_id)
        session.add(user_role)
        await session.flush()
        return user_role


class RoleRepository(BaseRepository[Role, Any, Any]):
    def __init__(self):
        super().__init__(Role)

    async def get_by_name(self, session: AsyncSession, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


user_repo = UserRepository()
role_repo = RoleRepository()
