from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    hash_token,
)
from app.core.permissions import get_permissions_for_roles
from app.core.exceptions import (
    PharmaRCAException,
    EntityNotFoundException,
    ValidationException,
)
from app.models.enums import RoleName
from app.models.user import User, Role
from app.schemas.user import (
    UserRegister,
    UserLogin,
    PasswordChange,
    UserResponse,
    UserCreate,
)
from app.schemas.token import TokenResponse, TokenRefreshRequest
from app.repositories.user_repository import user_repo, role_repo
from app.repositories.token_repository import token_repo


class AuthService:
    """Enterprise authentication service handling registrations, logins, rotations, and revocations."""

    async def register(
        self, session: AsyncSession, register_in: UserRegister
    ) -> UserResponse:
        normalized_email = register_in.email.strip().lower()

        # Check for existing account
        existing_user = await user_repo.get_by_email(session, normalized_email)
        if existing_user:
            raise PharmaRCAException(
                message="An account with this email address already exists.",
                status_code=409,
                details={"email": normalized_email},
            )

        # Ensure default non-privileged role (Investigator) exists
        default_role = await role_repo.get_by_name(session, RoleName.INVESTIGATOR.value)
        if not default_role:
            default_role = Role(
                name=RoleName.INVESTIGATOR.value,
                description="Default role for pharmaceutical incident and RCA investigators",
            )
            session.add(default_role)
            await session.flush()

        # Create user with hashed credentials and default role
        hashed_pw = get_password_hash(register_in.password)
        create_schema = UserCreate(
            full_name=register_in.full_name,
            email=normalized_email,
            is_active=True,
            password=register_in.password,
            role_ids=[default_role.id],
        )

        user = await user_repo.create_user(
            session, obj_in=create_schema, hashed_password=hashed_pw
        )
        await session.commit()
        return UserResponse.model_validate(user)

    async def login(
        self,
        session: AsyncSession,
        login_in: UserLogin,
        device_info: Optional[str] = None,
    ) -> TokenResponse:
        normalized_email = login_in.email.strip().lower()
        user = await user_repo.get_by_email(session, normalized_email)

        if not user or not verify_password(login_in.password, user.hashed_password):
            raise PharmaRCAException(
                message="Invalid email credentials or password.",
                status_code=401,
                details={"code": "INVALID_CREDENTIALS"},
            )

        if not user.is_active:
            raise PharmaRCAException(
                message="Account has been suspended or deactivated. Contact your Quality Administrator.",
                status_code=403,
                details={"code": "ACCOUNT_DEACTIVATED"},
            )

        # Extract roles and calculate effective permissions
        roles = [r.name for r in user.roles]
        permissions = list(get_permissions_for_roles(roles))

        # Generate tokens
        access_token, access_jti = create_access_token(
            subject=user.id,
            roles=roles,
            permissions=permissions,
        )
        refresh_token, refresh_jti, family_id, expire = create_refresh_token(
            subject=user.id
        )

        # Persist hashed refresh token session
        token_hash = hash_token(refresh_token)
        await token_repo.create_token_session(
            session,
            user_id=user.id,
            token_hash=token_hash,
            jti=refresh_jti,
            family_id=family_id,
            expires_at=expire,
            device_info=device_info,
        )
        await session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )

    async def refresh_tokens(
        self,
        session: AsyncSession,
        refresh_in: TokenRefreshRequest,
        device_info: Optional[str] = None,
    ) -> TokenResponse:
        # Decode token
        payload = decode_jwt_token(refresh_in.refresh_token)

        if payload.get("type") != "refresh":
            raise PharmaRCAException(
                message="Invalid token type provided for refresh endpoint.",
                status_code=401,
                details={"code": "INVALID_TOKEN_TYPE"},
            )

        user_id = payload.get("sub")
        jti = payload.get("jti")
        family_id = payload.get("family_id")

        if not user_id or not jti or not family_id:
            raise PharmaRCAException(
                message="Token payload is missing required claims.",
                status_code=401,
                details={"code": "MALFORMED_TOKEN"},
            )

        # Look up token session by JTI
        stored_token = await token_repo.get_by_jti(session, jti)

        # Detect reuse or invalid token
        if not stored_token or stored_token.is_revoked:
            # Token reuse detected: Invalidate entire family chain
            await token_repo.revoke_family(session, family_id)
            await session.commit()
            raise PharmaRCAException(
                message="Security violation: Refresh token reuse detected. All sessions in this chain have been revoked.",
                status_code=401,
                details={"code": "TOKEN_REUSE_DETECTED"},
            )

        # Check expiration against UTC
        now = datetime.now(timezone.utc)
        token_expires = stored_token.expires_at
        if token_expires.tzinfo is None:
            token_expires = token_expires.replace(tzinfo=timezone.utc)

        if token_expires < now:
            await token_repo.revoke_token(session, jti)
            await session.commit()
            raise PharmaRCAException(
                message="Refresh token has expired. Please authenticate again.",
                status_code=401,
                details={"code": "REFRESH_TOKEN_EXPIRED"},
            )

        # Verify user status
        user = await user_repo.get_with_roles(session, user_id)
        if not user or not user.is_active:
            await token_repo.revoke_family(session, family_id)
            await session.commit()
            raise PharmaRCAException(
                message="Account inactive or not found.",
                status_code=403,
                details={"code": "USER_NOT_ACTIVE"},
            )

        # Rotate token: revoke current token
        await token_repo.revoke_token(session, jti)

        # Issue new token pair within same family
        roles = [r.name for r in user.roles]
        permissions = list(get_permissions_for_roles(roles))

        new_access_token, _ = create_access_token(
            subject=user.id,
            roles=roles,
            permissions=permissions,
        )
        new_refresh_token, new_jti, _, new_expire = create_refresh_token(
            subject=user.id, family_id=family_id
        )

        # Store rotated refresh token
        new_token_hash = hash_token(new_refresh_token)
        await token_repo.create_token_session(
            session,
            user_id=user.id,
            token_hash=new_token_hash,
            jti=new_jti,
            family_id=family_id,
            expires_at=new_expire,
            device_info=device_info,
        )
        await session.commit()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )

    async def logout(
        self,
        session: AsyncSession,
        current_user: User,
        refresh_token: Optional[str] = None,
    ) -> bool:
        if refresh_token:
            try:
                payload = decode_jwt_token(refresh_token)
                jti = payload.get("jti")
                if jti:
                    await token_repo.revoke_token(session, jti)
                    await session.commit()
                    return True
            except Exception:
                # If token is invalid or expired, proceed silently
                pass
        return True

    async def logout_all(self, session: AsyncSession, current_user: User) -> int:
        count = await token_repo.revoke_all_user_tokens(session, current_user.id)
        await session.commit()
        return count

    async def change_password(
        self,
        session: AsyncSession,
        current_user: User,
        password_in: PasswordChange,
    ) -> bool:
        if not verify_password(password_in.current_password, current_user.hashed_password):
            raise PharmaRCAException(
                message="Current password verification failed.",
                status_code=400,
                details={"code": "INVALID_CURRENT_PASSWORD"},
            )

        new_hashed = get_password_hash(password_in.new_password)
        await user_repo.update_password(
            session, user_id=current_user.id, hashed_password=new_hashed
        )

        # Revoke existing sessions to require re-authentication with new password
        await token_repo.revoke_all_user_tokens(session, current_user.id)
        await session.commit()
        return True


auth_service = AuthService()
