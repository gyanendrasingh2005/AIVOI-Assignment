import re
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any, List
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import PharmaRCAException


# Configure Passlib bcrypt context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Password complexity regex:
# >= 8 chars, >= 1 uppercase, >= 1 lowercase, >= 1 digit, >= 1 special character
PASSWORD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$"
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against an existing bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Computes a secure bcrypt hash for the provided password."""
    return pwd_context.hash(password)


def validate_password_complexity(password: str) -> Tuple[bool, Optional[str]]:
    """
    Validates password against enterprise pharmaceutical security standards:
    - Minimum 8 characters.
    - At least one uppercase letter (A-Z).
    - At least one lowercase letter (a-z).
    - At least one digit (0-9).
    - At least one special symbol.
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A-Z)."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one numeric digit (0-9)."
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        return False, "Password must contain at least one special character."
    return True, None


def hash_token(raw_token: str) -> str:
    """Returns a non-reversible SHA-256 hex digest for persistent token storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(
    subject: str,
    roles: List[str],
    permissions: List[str],
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, str]:
    """
    Generates a cryptographically signed short-lived JWT access token.
    Returns: (encoded_token_string, jti)
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    jti = str(uuid.uuid4())
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
        "type": "access",
        "roles": roles,
        "permissions": permissions,
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti


def create_refresh_token(
    subject: str,
    family_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, str, str, datetime]:
    """
    Generates a longer-lived JWT refresh token with unique jti and rotation family.
    Returns: (encoded_token_string, jti, family_id, expire_datetime)
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    jti = str(uuid.uuid4())
    token_family = family_id or str(uuid.uuid4())

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
        "family_id": token_family,
        "type": "refresh",
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti, token_family, expire


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decodes and verifies a JWT token's signature and expiration.
    Raises PharmaRCAException with appropriate HTTP status if invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise PharmaRCAException(
            message="Token has expired. Please authenticate again.",
            status_code=401,
            details={"code": "TOKEN_EXPIRED"},
        )
    except JWTError as e:
        raise PharmaRCAException(
            message="Invalid authentication credentials or signature.",
            status_code=401,
            details={"code": "INVALID_TOKEN", "error": str(e)},
        )
