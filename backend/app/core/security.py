"""Password hashing and JWT issuing/verification.

No secret is defined here — the signing key comes from `core.config`, which
reads it from `.env`.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

# bcrypt is used directly rather than through passlib. passlib 1.7.4 reads
# `bcrypt.__about__.__version__`, which was removed in bcrypt 4.1+, so the two
# installed versions are incompatible (passlib's last release was 2020). Calling
# bcrypt directly avoids the broken shim and adds no dependency.

# bcrypt silently truncates input beyond 72 bytes, which would make two
# different long passwords interchangeable. Reject rather than truncate.
MAX_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    """Raised when a password exceeds bcrypt's 72-byte input limit."""


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password for storage.

    Args:
        plain_password: The user's password.

    Returns:
        A bcrypt hash safe to persist.

    Raises:
        PasswordTooLongError: If the password exceeds 72 bytes when encoded.
    """
    encoded = plain_password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise PasswordTooLongError(
            f"Password exceeds {MAX_PASSWORD_BYTES} bytes and would be truncated by bcrypt"
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored hash.

    Args:
        plain_password: Candidate password.
        hashed_password: Stored bcrypt hash.

    Returns:
        True if the password matches. False if it does not, or if the stored
        hash is malformed.
    """
    encoded = plain_password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed or non-bcrypt stored hash.
        return False


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """Issue a signed JWT access token.

    Args:
        subject: Value for the `sub` claim — the user's pseudonymous id, not
            their email, so the token carries no direct identifier.
        expires_minutes: Optional override for token lifetime.

    Returns:
        Encoded JWT.
    """
    settings = get_settings()
    minutes = expires_minutes or settings.access_token_expire_minutes
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def generate_reset_token() -> str:
    """Generate a single-use password reset token.

    Returns:
        A cryptographically random, URL-safe string. Only its hash (see
        `hash_reset_token`) is ever persisted -- this raw value exists only
        for the length of one request/response cycle and inside the emailed
        link itself.
    """
    return secrets.token_urlsafe(32)


def generate_otp_code() -> str:
    """Generate a 6-digit numeric login one-time code (round 7).

    Uses `secrets.randbelow`, not `random`, for the same reason
    `generate_reset_token` uses `secrets.token_urlsafe` -- this value gates a
    real login and must not be predictable. Zero-padded so every code is
    exactly 6 digits, including e.g. `"004821"`.

    Returns:
        A 6-character numeric string. Only its hash (see `hash_reset_token`,
        reused here -- both are single-use, short-lived, high-entropy-enough
        values hashed the same way) is ever persisted.
    """
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_reset_token(token: str) -> str:
    """Hash a reset token for storage/lookup.

    Args:
        token: The raw token, as emailed to the student.

    Returns:
        Its SHA-256 hex digest. Reset tokens are single-use, short-lived,
        high-entropy random values (not passwords, which are low-entropy and
        reused across sites), so a fast hash is the right tool here, unlike
        `hash_password`'s deliberately slow bcrypt.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_access_token(token: str) -> str | None:
    """Validate a JWT and extract its subject.

    Args:
        token: Encoded JWT.

    Returns:
        The `sub` claim, or None if the token is invalid, expired, or malformed.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None
    subject = payload.get("sub")
    return str(subject) if subject is not None else None
