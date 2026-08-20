"""A single-use, short-lived login one-time code (round 7, email-based 2FA).

Two secrets per row, both stored only as SHA-256 hashes, the same reasoning
`PasswordResetToken` already follows: `login_token_hash` identifies *which*
pending login this code belongs to (returned to the client in
`LoginResponse.login_token`, presented back on `/auth/login/verify-otp`),
and `code_hash` is the 6-digit code itself, emailed to the account. A
database read alone must not yield a usable login -- an attacker would need
both the row's plaintext login_token (held only by the client that just
logged in with the right password) and the code (delivered only to the
account's own inbox).

`attempts` bounds how many wrong codes one row will tolerate before it is
invalidated (see `app.api.auth.MAX_OTP_ATTEMPTS`) -- without it, a 6-digit
code (1,000,000 possibilities) sitting valid for 10 minutes would be
brute-forceable by an attacker who obtained the login_token, since nothing
else would stop repeated guesses against `/auth/login/verify-otp`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class OtpCode(Base):
    """One issued login one-time-code's server-side record."""

    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    login_token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship()  # noqa: F821
