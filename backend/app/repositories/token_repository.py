from typing import Optional, Any
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token import RefreshToken
from app.repositories.base import BaseRepository


class TokenRepository(BaseRepository[RefreshToken, Any, Any]):
    def __init__(self):
        super().__init__(RefreshToken)

    async def create_token_session(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        token_hash: str,
        jti: str,
        family_id: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
    ) -> RefreshToken:
        """Stores a hashed refresh token session with cryptographic replay tracking."""
        token_entry = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            jti=jti,
            family_id=family_id,
            expires_at=expires_at,
            device_info=device_info,
            is_revoked=False,
        )
        session.add(token_entry)
        await session.flush()
        return token_entry

    async def get_by_jti(
        self, session: AsyncSession, jti: str
    ) -> Optional[RefreshToken]:
        """Look up token session by unique JWT claim identifier."""
        stmt = select(RefreshToken).where(RefreshToken.jti == jti)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_hash(
        self, session: AsyncSession, token_hash: str
    ) -> Optional[RefreshToken]:
        """Look up token session by SHA-256 hash."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_token(
        self, session: AsyncSession, jti: str
    ) -> bool:
        """Invalidates a specific token upon rotation or standard logout."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.jti == jti)
            .values(is_revoked=True, revoked_at=now)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount > 0

    async def revoke_family(
        self, session: AsyncSession, family_id: str
    ) -> int:
        """
        Invalidates an entire token chain family upon detecting reuse of a previously rotated token.
        Critical security mitigation against replay attacks.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .values(is_revoked=True, revoked_at=now)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount

    async def revoke_all_user_tokens(
        self, session: AsyncSession, user_id: str
    ) -> int:
        """Invalidates all active authentication sessions for a given user (logout from all sessions)."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=now)
        )
        result = await session.execute(stmt)
        await session.flush()
        return result.rowcount


token_repo = TokenRepository()
