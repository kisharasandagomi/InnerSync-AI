"""Transactional email via Resend's HTTP API (round 4: password reset).

Uses `urllib.request` from the standard library rather than adding a new
runtime HTTP dependency -- `httpx` is already in requirements.txt but
reserved there for the test suite (see that file's comments); this is the
only production code path in the app that sends outbound HTTP itself
(Gemini calls go through the `google-genai` SDK).

Fails loudly if `RESEND_API_KEY` is unset, the same "config problem, not a
runtime one" treatment `app.chatbot.gemini_client.get_gemini_client()` gives
a missing `GEMINI_API_KEY` -- this module is checked once, before any
account lookup, so a missing key fails identically for every request and
reveals nothing about whether a given email is registered.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.core.config import get_settings


class EmailConfigError(RuntimeError):
    """Raised when Resend cannot be configured (missing API key)."""


class EmailSendError(RuntimeError):
    """Raised when Resend rejects or fails to deliver a genuinely-attempted send."""


def _require_resend_config() -> tuple[str, str]:
    """Resolve and validate Resend settings.

    Returns:
        `(api_key, from_email)`.

    Raises:
        EmailConfigError: If `RESEND_API_KEY` is unset or blank.
    """
    settings = get_settings()
    key = settings.resend_api_key.strip()
    if not key:
        raise EmailConfigError(
            "RESEND_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and add a real Resend API key from https://resend.com/api-keys -- "
            "password reset emails cannot be sent without one."
        )
    return key, settings.resend_from_email


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    """Send a password reset email via Resend.

    Args:
        to_email: The recipient's address.
        reset_link: The full, ready-to-click reset URL (already contains the
            single-use token).

    Raises:
        EmailConfigError: If Resend is not configured.
        EmailSendError: If Resend's API rejects the request or is unreachable.
    """
    api_key, from_email = _require_resend_config()

    body = json.dumps(
        {
            "from": from_email,
            "to": [to_email],
            "subject": "Reset your InnerSync AI password",
            "html": (
                "<p>A password reset was requested for your InnerSync AI account.</p>"
                f'<p><a href="{reset_link}">Click here to choose a new password</a>. '
                "This link expires in 45 minutes and can only be used once.</p>"
                "<p>If you did not request this, you can safely ignore this email.</p>"
            ),
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise EmailSendError(f"Resend returned HTTP {response.status}")
    except urllib.error.URLError as exc:
        raise EmailSendError(f"Could not reach Resend: {exc}") from exc
