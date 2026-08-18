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
    """Registration payload.

    `display_name` and `hobby` are both optional and collected here — one
    extra step's worth of friction, once, rather than a separate profile
    flow — per round 3's personalization features. Neither is required;
    skipping both leaves the same graceful fallbacks this project already
    uses elsewhere (see `resolve_greeting_name` below and
    `ml_pipeline/src/recommendation/catalogue.py`'s hobby-aware template).
    """

    email: EmailAddress
    password: str = Field(min_length=8, max_length=72)  # bcrypt input limit
    display_name: str | None = Field(default=None, max_length=80)
    hobby: str | None = Field(default=None, max_length=80)


class DeactivateAccountRequest(BaseModel):
    """Deactivation payload. Requires the current password, same as any
    other destructive account action, so a stolen still-valid access token
    alone cannot deactivate an account without also knowing the password."""

    password: str


class ForgotPasswordRequest(BaseModel):
    """Forgot-password payload. Just the email -- the response is identical
    whether or not it belongs to a registered account, so no other input is
    needed here."""

    email: EmailAddress


class ForgotPasswordResponse(BaseModel):
    """Always the same message, sent whether or not the email is registered.

    Mirrors `login`'s existing account-enumeration discipline: a distinct
    "no account with that email" response would let a caller enumerate
    registered addresses one guess at a time.
    """

    message: str = "If that email is registered, a reset link has been sent."


class ResetPasswordRequest(BaseModel):
    """Reset-password payload: the emailed single-use token and a new password."""

    token: str
    new_password: str = Field(min_length=8, max_length=72)


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
    display_name: str | None = None


class TokenResponse(BaseModel):
    """Issued access token.

    `display_name` rides along here (rather than requiring a separate
    "who am I" call) so the frontend can render the check-in greeting
    template immediately after sign-in without an extra round trip. `None`
    when the student never set one — the frontend falls back to the email's
    local part, via the same reasoning as `resolve_greeting_name` below.
    """

    access_token: str
    token_type: str = "bearer"
    display_name: str | None = None


def resolve_greeting_name(display_name: str | None, email: str) -> str:
    """The name to greet a student by: their own choice, or a graceful fallback.

    A template, not an LLM generation — see `frontend/src/pages/ChatPage.tsx`'s
    `questionPrompt`, which uses the frontend equivalent of this same
    fallback (`resolveGreetingName` in `services/greeting.ts`) to build the
    literal "Hi {name}, ready for your check-in?" string. Kept here too, and
    exercised by a backend test, so the *reasoning* — never a blank or
    broken greeting — is verified on both sides rather than trusted to only
    one.

    Args:
        display_name: The student's own chosen name, or `None`/blank if
            never set.
        email: Always present — the fallback source.

    Returns:
        `display_name` if it is set and non-blank; otherwise the part of
        `email` before the `@`.
    """
    if display_name and display_name.strip():
        return display_name.strip()
    return email.split("@", 1)[0]
