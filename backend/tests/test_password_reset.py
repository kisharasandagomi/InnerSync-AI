"""Forgot/reset password: account enumeration, token expiry, and single-use enforcement."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app.api.auth as auth_module
from app.models.password_reset_token import PasswordResetToken

CREDENTIALS = {"email": "reset.me@example.ac.uk", "password": "the-original-password"}


class _FakeSettings:
    """Stand-in for app.core.config.Settings with Resend "configured"."""

    resend_api_key = "test-resend-key"
    frontend_base_url = "http://testserver"


def _configure_resend(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Monkeypatch Resend to "configured" and capture (to_email, reset_link)
    pairs instead of making a real network call."""
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(auth_module, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        auth_module,
        "send_password_reset_email",
        lambda to_email, reset_link: sent.append((to_email, reset_link)),
    )
    return sent


def _extract_token(reset_link: str) -> str:
    return reset_link.split("token=", 1)[1]


# --- Account enumeration ---


def test_forgot_password_same_response_for_known_and_unknown_email_when_unconfigured(
    client: TestClient,
) -> None:
    """With RESEND_API_KEY unset (the test default), both cases fail the
    same way -- a config problem does not become an enumeration signal."""
    client.post("/auth/register", json=CREDENTIALS)

    known = client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
    unknown = client.post("/auth/forgot-password", json={"email": "nobody@example.ac.uk"})

    assert known.status_code == unknown.status_code == 503


def test_forgot_password_same_response_for_known_and_unknown_email_when_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The actual point of this endpoint: identical response either way."""
    sent = _configure_resend(monkeypatch)
    client.post("/auth/register", json=CREDENTIALS)

    known = client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
    unknown = client.post("/auth/forgot-password", json={"email": "nobody@example.ac.uk"})

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    # Only the real account actually gets an email queued.
    assert len(sent) == 1
    assert sent[0][0] == CREDENTIALS["email"]


def test_forgot_password_does_not_email_a_deactivated_account(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deactivated account can't log in anyway, so it should not receive
    (or need) a reset link, but the response must still look the same."""
    sent = _configure_resend(monkeypatch)
    client.post("/auth/register", json=CREDENTIALS)
    token = client.post("/auth/login", json=CREDENTIALS).json()["access_token"]
    client.post(
        "/auth/deactivate",
        json={"password": CREDENTIALS["password"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})

    assert response.status_code == 200
    assert sent == []


# --- Reset flow, expiry, single-use ---


def test_reset_password_happy_path_changes_the_password(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent = _configure_resend(monkeypatch)
    client.post("/auth/register", json=CREDENTIALS)
    client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
    raw_token = _extract_token(sent[0][1])

    response = client.post(
        "/auth/reset-password", json={"token": raw_token, "new_password": "a-brand-new-password"}
    )
    assert response.status_code == 204

    old_password_login = client.post("/auth/login", json=CREDENTIALS)
    assert old_password_login.status_code == 401

    new_password_login = client.post(
        "/auth/login",
        json={"email": CREDENTIALS["email"], "password": "a-brand-new-password"},
    )
    assert new_password_login.status_code == 200


def test_reset_password_rejects_unknown_token(client: TestClient) -> None:
    response = client.post(
        "/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "whatever12345"},
    )
    assert response.status_code == 400


def test_reset_password_token_is_single_use(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same token cannot be used a second time."""
    sent = _configure_resend(monkeypatch)
    client.post("/auth/register", json=CREDENTIALS)
    client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
    raw_token = _extract_token(sent[0][1])

    first = client.post(
        "/auth/reset-password", json={"token": raw_token, "new_password": "first-new-password1"}
    )
    assert first.status_code == 204

    second = client.post(
        "/auth/reset-password", json={"token": raw_token, "new_password": "second-new-password"}
    )
    assert second.status_code == 400


def test_reset_password_rejects_expired_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_session
) -> None:
    """A token past its expiry is rejected even though it was never used."""
    sent = _configure_resend(monkeypatch)
    client.post("/auth/register", json=CREDENTIALS)
    client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
    raw_token = _extract_token(sent[0][1])

    from app.core.security import hash_reset_token

    row = (
        db_session.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == hash_reset_token(raw_token))
        .one()
    )
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    response = client.post(
        "/auth/reset-password", json={"token": raw_token, "new_password": "too-late-password1"}
    )
    assert response.status_code == 400


def test_reset_password_invalidates_other_outstanding_tokens_for_the_same_user(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Requesting two reset links, then using the second: the first must no
    longer work, since a successful reset retires every other in-flight link."""
    sent = _configure_resend(monkeypatch)
    client.post("/auth/register", json=CREDENTIALS)
    client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
    client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
    first_token = _extract_token(sent[0][1])
    second_token = _extract_token(sent[1][1])

    used_second = client.post(
        "/auth/reset-password",
        json={"token": second_token, "new_password": "second-link-password"},
    )
    assert used_second.status_code == 204

    stale_first = client.post(
        "/auth/reset-password", json={"token": first_token, "new_password": "first-link-password"}
    )
    assert stale_first.status_code == 400
