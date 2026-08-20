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


class UpdateProfileRequest(BaseModel):
    """Edit-profile payload (round 7): display name only.

    `display_name` may be explicitly set to `None` (or an empty/whitespace
    string) to clear it — the frontend then falls back to the email's local
    part everywhere it's shown, via the same `resolve_greeting_name`
    reasoning used at registration. No password is required here: changing a
    display name is not a destructive or security-relevant action, unlike
    deactivation or a password change, both of which do require it.
    """

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, max_length=80)


class ChangePasswordRequest(BaseModel):
    """Change-password payload for an already-authenticated session (round 7).

    Distinct from `ResetPasswordRequest`: this is "I know my current
    password and want to set a new one," reached from Settings while signed
    in, not the forgot/reset-password flow for a locked-out student. Requires
    the current password, the same confirmation pattern
    `DeactivateAccountRequest` already uses, so a stolen still-valid access
    token alone cannot take over the account's credentials.
    """

    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


class UpdateOtpSettingRequest(BaseModel):
    """Toggle email one-time-code sign-in (round 7). Opt-in, default off —
    see `app.models.user.User.otp_enabled`'s docstring."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool


class MeResponse(BaseModel):
    """The caller's own current profile (round 7).

    Lets Settings load current `display_name` and `otp_enabled` fresh on
    mount, rather than only trusting the snapshot carried on `TokenResponse`
    at the moment of login — a value changed in another tab, or toggled and
    reloaded, must not appear stale here.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str | None = None
    otp_enabled: bool


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


class LoginResponse(BaseModel):
    """`POST /auth/login`'s response (round 7): either a token, or a request
    for a one-time code.

    A single shape covering both outcomes, rather than two different status
    codes or response models, so the frontend has one place to branch
    (`otp_required`) instead of needing to distinguish response shapes by
    HTTP status. `otp_required=False` (the default, and the only case for
    every account that hasn't opted in) carries exactly `TokenResponse`'s
    fields; `otp_required=True` carries only `login_token` — the opaque,
    single-use value the client must present back to `/auth/login/verify-otp`
    alongside the emailed code. No `access_token` is ever present when
    `otp_required` is True: the password alone is explicitly not sufficient
    to authenticate an OTP-enabled account.
    """

    otp_required: bool = False
    login_token: str | None = None

    access_token: str | None = None
    token_type: str = "bearer"
    display_name: str | None = None


class VerifyOtpRequest(BaseModel):
    """Second step of an OTP-gated login: the `login_token` from
    `LoginResponse` plus the code emailed to the account."""

    model_config = ConfigDict(extra="forbid")

    login_token: str
    code: str = Field(min_length=6, max_length=6)


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
