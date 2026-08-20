"""Transactional email via Resend's HTTP API (round 4: password reset;
round 7: login one-time codes -- reuses this same infrastructure rather than
adding a second email integration).

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


def _post_to_resend(api_key: str, payload: dict[str, object]) -> None:
    """Send one request to Resend's `/emails` endpoint.

    Args:
        api_key: Resend API key.
        payload: The request body (`from`, `to`, `subject`, `html`).

    Raises:
        EmailSendError: If Resend rejects the request or is unreachable.
    """
    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Cloudflare (fronting api.resend.com) blocks urllib's default
            # "Python-urllib/x.y" User-Agent outright with a bot-protection
            # 403 (Cloudflare error 1010) before the request ever reaches
            # Resend -- discovered during live verification, where every
            # send failed with an opaque "HTTP Error 403: Forbidden" that
            # turned out to have nothing to do with Resend's own API key or
            # recipient validation. Any ordinary browser-like value avoids
            # the block; the request is still a plain server-to-server call.
            "User-Agent": "Mozilla/5.0 (compatible; InnerSyncAI-Backend/1.0)",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status >= 400:
                raise EmailSendError(f"Resend returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        # Surface Resend's own JSON error body (e.g. its `message` field)
        # rather than just the generic status line -- the previous
        # str(exc) ("HTTP Error 403: Forbidden") gave no way to tell a
        # sandbox-recipient restriction apart from a bad API key or the
        # Cloudflare block above.
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover - defensive, body already gone
            detail = str(exc)
        raise EmailSendError(f"Resend rejected the request: {detail}") from exc
    except urllib.error.URLError as exc:
        raise EmailSendError(f"Could not reach Resend: {exc}") from exc


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

    _post_to_resend(
        api_key,
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
        },
    )


def send_otp_email(to_email: str, code: str) -> None:
    """Send a login one-time code via Resend (round 7).

    Args:
        to_email: The recipient's address -- always the account's own,
            already-verified-by-registration email; this function is only
            ever called after a correct password on an OTP-enabled account.
        code: The 6-digit code, plaintext, exactly as generated -- the only
            place it exists in plaintext outside the request that created it.

    Raises:
        EmailConfigError: If Resend is not configured.
        EmailSendError: If Resend's API rejects the request or is unreachable.
    """
    api_key, from_email = _require_resend_config()

    _post_to_resend(
        api_key,
        {
            "from": from_email,
            "to": [to_email],
            "subject": "Your InnerSync AI sign-in code",
            "html": (
                "<p>Use this code to finish signing in to InnerSync AI:</p>"
                f'<p style="font-size: 28px; font-weight: 600; letter-spacing: 4px;">{code}</p>'
                "<p>This code expires in 10 minutes and can only be used once.</p>"
                "<p>If you did not just try to sign in, you can safely ignore this "
                "email -- your account is still protected by your password.</p>"
            ),
        },
    )
