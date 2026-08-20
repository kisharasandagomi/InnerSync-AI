"""Email-based OTP login (round 7): opt-in default, code expiry, single-use enforcement."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import app.api.auth as auth_module
from app.models.otp_code import OtpCode

CREDENTIALS = {"email": "otp.me@example.ac.uk", "password": "the-original-password"}


class _FakeSettings:
    resend_api_key = "test-resend-key"
    frontend_base_url = "http://testserver"


def _configure_resend(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    """Capture (to_email, code) pairs instead of making a real network call."""
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(auth_module, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        auth_module,
        "send_otp_email",
        lambda to_email, code: sent.append((to_email, code)),
    )
    return sent


def _register_and_enable_otp(client: TestClient) -> dict[str, str]:
    client.post("/auth/register", json=CREDENTIALS)
    token = client.post("/auth/login", json=CREDENTIALS).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    response = client.patch("/auth/otp-setting", json={"enabled": True}, headers=headers)
    assert response.status_code == 200
    assert response.json()["otp_enabled"] is True
    return headers


# --- Opt-in default, and the unaffected path ---


def test_login_without_otp_enabled_returns_a_token_directly(client: TestClient) -> None:
    """Default off: an account that never opted in logs in exactly as before."""
    client.post("/auth/register", json=CREDENTIALS)

    response = client.post("/auth/login", json=CREDENTIALS)

    assert response.status_code == 200
    body = response.json()
    assert body["otp_required"] is False
    assert body["access_token"] is not None


def test_otp_setting_defaults_off_for_a_new_account(client: TestClient) -> None:
    client.post("/auth/register", json=CREDENTIALS)
    token = client.post("/auth/login", json=CREDENTIALS).json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert me.json()["otp_enabled"] is False


# --- OTP-enabled happy path ---


def test_login_with_otp_enabled_requires_a_code(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent = _configure_resend(monkeypatch)
    _register_and_enable_otp(client)

    response = client.post("/auth/login", json=CREDENTIALS)

    assert response.status_code == 200
    body = response.json()
    assert body["otp_required"] is True
    assert body["access_token"] is None
    assert body["login_token"] is not None
    assert len(sent) == 1
    assert sent[0][0] == CREDENTIALS["email"]
    assert len(sent[0][1]) == 6 and sent[0][1].isdigit()


def test_verify_otp_happy_path_returns_a_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent = _configure_resend(monkeypatch)
    _register_and_enable_otp(client)
    login_token = client.post("/auth/login", json=CREDENTIALS).json()["login_token"]
    code = sent[0][1]

    response = client.post(
        "/auth/login/verify-otp", json={"login_token": login_token, "code": code}
    )

    assert response.status_code == 200
    assert response.json()["access_token"] is not None


def test_verify_otp_rejects_wrong_code(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_resend(monkeypatch)
    _register_and_enable_otp(client)
    login_token = client.post("/auth/login", json=CREDENTIALS).json()["login_token"]

    response = client.post(
        "/auth/login/verify-otp", json={"login_token": login_token, "code": "000000"}
    )

    assert response.status_code == 400


# --- Expiry and single-use ---


def test_verify_otp_code_is_single_use(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent = _configure_resend(monkeypatch)
    _register_and_enable_otp(client)
    login_token = client.post("/auth/login", json=CREDENTIALS).json()["login_token"]
    code = sent[0][1]

    first = client.post(
        "/auth/login/verify-otp", json={"login_token": login_token, "code": code}
    )
    assert first.status_code == 200

    second = client.post(
        "/auth/login/verify-otp", json={"login_token": login_token, "code": code}
    )
    assert second.status_code == 400


def test_verify_otp_rejects_expired_code(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_session
) -> None:
    """A code past its 10-minute expiry is rejected even though it was never used."""
    sent = _configure_resend(monkeypatch)
    _register_and_enable_otp(client)
    login_token = client.post("/auth/login", json=CREDENTIALS).json()["login_token"]
    code = sent[0][1]

    from app.core.security import hash_reset_token

    row = (
        db_session.query(OtpCode)
        .filter(OtpCode.login_token_hash == hash_reset_token(login_token))
        .one()
    )
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    response = client.post(
        "/auth/login/verify-otp", json={"login_token": login_token, "code": code}
    )
    assert response.status_code == 400


def test_verify_otp_rejects_unknown_login_token(client: TestClient) -> None:
    response = client.post(
        "/auth/login/verify-otp",
        json={"login_token": "not-a-real-token", "code": "123456"},
    )
    assert response.status_code == 400


# --- Attempt cap (brute-force protection) ---


def test_verify_otp_invalidates_code_after_max_wrong_attempts(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """5 wrong guesses exhaust the code; a 6th attempt with the *correct*
    code is still rejected -- the row is invalidated outright, not merely
    still-counting."""
    sent = _configure_resend(monkeypatch)
    _register_and_enable_otp(client)
    login_token = client.post("/auth/login", json=CREDENTIALS).json()["login_token"]
    correct_code = sent[0][1]
    wrong_code = "000000" if correct_code != "000000" else "111111"

    for _ in range(5):
        response = client.post(
            "/auth/login/verify-otp",
            json={"login_token": login_token, "code": wrong_code},
        )
        assert response.status_code == 400

    final = client.post(
        "/auth/login/verify-otp",
        json={"login_token": login_token, "code": correct_code},
    )
    assert final.status_code == 400


def test_verify_otp_attempts_below_cap_still_allow_the_correct_code(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fewer than 5 wrong guesses do not lock out the correct code."""
    sent = _configure_resend(monkeypatch)
    _register_and_enable_otp(client)
    login_token = client.post("/auth/login", json=CREDENTIALS).json()["login_token"]
    correct_code = sent[0][1]
    wrong_code = "000000" if correct_code != "000000" else "111111"

    for _ in range(4):
        response = client.post(
            "/auth/login/verify-otp",
            json={"login_token": login_token, "code": wrong_code},
        )
        assert response.status_code == 400

    final = client.post(
        "/auth/login/verify-otp",
        json={"login_token": login_token, "code": correct_code},
    )
    assert final.status_code == 200


def test_locked_out_code_requires_signing_in_again_for_a_fresh_code(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After exhausting one code's attempts, a fresh login issues a fresh
    row with its own attempt counter, unaffected by the exhausted one."""
    sent = _configure_resend(monkeypatch)
    _register_and_enable_otp(client)
    first_login_token = client.post("/auth/login", json=CREDENTIALS).json()["login_token"]

    for _ in range(5):
        client.post(
            "/auth/login/verify-otp",
            json={"login_token": first_login_token, "code": "000000"},
        )

    second_response = client.post("/auth/login", json=CREDENTIALS)
    second_login_token = second_response.json()["login_token"]
    second_code = sent[-1][1]

    final = client.post(
        "/auth/login/verify-otp",
        json={"login_token": second_login_token, "code": second_code},
    )
    assert final.status_code == 200


def test_disabling_otp_returns_login_to_a_direct_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A student can turn OTP back off; login then behaves as before again."""
    _configure_resend(monkeypatch)
    headers = _register_and_enable_otp(client)
    client.patch("/auth/otp-setting", json={"enabled": False}, headers=headers)

    response = client.post("/auth/login", json=CREDENTIALS)

    assert response.status_code == 200
    assert response.json()["otp_required"] is False
    assert response.json()["access_token"] is not None
