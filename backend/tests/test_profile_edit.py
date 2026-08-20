"""Edit-profile (round 7): display name update and in-session password change."""

from __future__ import annotations

from fastapi.testclient import TestClient

CREDENTIALS = {"email": "edit.me@example.ac.uk", "password": "the-original-password"}


def _headers(client: TestClient) -> dict[str, str]:
    client.post("/auth/register", json=CREDENTIALS)
    token = client.post("/auth/login", json=CREDENTIALS).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- Display name ---


def test_update_display_name_happy_path(client: TestClient) -> None:
    headers = _headers(client)

    response = client.patch(
        "/auth/profile", json={"display_name": "Kavi"}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Kavi"

    me = client.get("/auth/me", headers=headers)
    assert me.json()["display_name"] == "Kavi"


def test_update_display_name_strips_whitespace(client: TestClient) -> None:
    headers = _headers(client)

    response = client.patch(
        "/auth/profile", json={"display_name": "  Kavi  "}, headers=headers
    )

    assert response.json()["display_name"] == "Kavi"


def test_update_display_name_blank_clears_it(client: TestClient) -> None:
    """Setting a blank/whitespace-only name clears it -- the frontend then
    falls back to the email's local part, same as never having set one."""
    headers = _headers(client)
    client.patch("/auth/profile", json={"display_name": "Kavi"}, headers=headers)

    response = client.patch("/auth/profile", json={"display_name": "   "}, headers=headers)

    assert response.status_code == 200
    assert response.json()["display_name"] is None


def test_update_display_name_rejects_over_max_length(client: TestClient) -> None:
    headers = _headers(client)

    response = client.patch(
        "/auth/profile", json={"display_name": "x" * 81}, headers=headers
    )

    assert response.status_code == 422


def test_update_display_name_requires_authentication(client: TestClient) -> None:
    response = client.patch("/auth/profile", json={"display_name": "Kavi"})
    assert response.status_code == 401


# --- Change password ---


def test_change_password_happy_path(client: TestClient) -> None:
    headers = _headers(client)

    response = client.post(
        "/auth/change-password",
        json={"current_password": CREDENTIALS["password"], "new_password": "a-brand-new-password"},
        headers=headers,
    )
    assert response.status_code == 204

    old_login = client.post("/auth/login", json=CREDENTIALS)
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login",
        json={"email": CREDENTIALS["email"], "password": "a-brand-new-password"},
    )
    assert new_login.status_code == 200


def test_change_password_rejects_wrong_current_password(client: TestClient) -> None:
    headers = _headers(client)

    response = client.post(
        "/auth/change-password",
        json={"current_password": "not-the-real-password", "new_password": "a-brand-new-password"},
        headers=headers,
    )

    assert response.status_code == 401
    # The original password must still work -- a rejected change is a no-op.
    still_works = client.post("/auth/login", json=CREDENTIALS)
    assert still_works.status_code == 200


def test_change_password_rejects_too_short_new_password(client: TestClient) -> None:
    headers = _headers(client)

    response = client.post(
        "/auth/change-password",
        json={"current_password": CREDENTIALS["password"], "new_password": "short1"},
        headers=headers,
    )

    assert response.status_code == 422


def test_change_password_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/auth/change-password",
        json={"current_password": "x", "new_password": "a-brand-new-password"},
    )
    assert response.status_code == 401
