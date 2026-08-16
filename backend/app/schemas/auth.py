"""Request/response schemas for registration and login.

Uses a locally-validated email string rather than pydantic's `EmailStr`, which
requires the `email-validator` package that is not part of the `mainks`
environment. The pattern below is deliberately permissive — it rejects
obviously malformed input without attempting full RFC 5322 conformance, which
is not something a wellbeing app needs to adjudicate.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

EmailAddress = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, max_length=320, pattern=_EMAIL_PATTERN),
]


def is_valid_email(value: str) -> bool:
    """Check whether a string looks like an email address.

    Args:
        value: Candidate address.

    Returns:
        True if it matches the accepted pattern.
    """
    return bool(re.match(_EMAIL_PATTERN, value.strip()))


class UserRegisterRequest(BaseModel):
    """Registration payload."""

    email: EmailAddress
    password: str = Field(min_length=8, max_length=72)  # bcrypt input limit


class UserLoginRequest(BaseModel):
    """Login payload."""

    email: EmailAddress
    password: str


class UserResponse(BaseModel):
    """Public view of a user. Never exposes the password hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    """Issued access token."""

    access_token: str
    token_type: str = "bearer"
