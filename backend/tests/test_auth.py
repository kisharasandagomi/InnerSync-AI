"""Registration and login: happy paths plus auth-failure cases.

`IMPLEMENTATION_RULES.md` requires every API route to have at least one
happy-path test and one auth-failure test.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

CREDENTIALS = {"email": "new.student@example.ac.uk", "password": "a-long-enough-password"}


def test_register_returns_user_without_password_hash(client: TestClient) -> None:
    """Happy path: registration succeeds and never echoes the password."""
    response = client.post("/auth/register", json=CREDENTIALS)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == CREDENTIALS["email"]
    assert "id" in body and "created_at" in body
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    """A second registration with the same email is refused."""
    client.post("/auth/register", json=CREDENTIALS)
    response = client.post("/auth/register", json=CREDENTIALS)

    assert response.status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    """Passwords below the minimum length are rejected by validation."""
    response = client.post(
        "/auth/register", json={"email": "short@example.ac.uk", "password": "abc"}
    )

    assert response.status_code == 422


def test_login_happy_path_returns_bearer_token(client: TestClient) -> None:
    """Happy path: valid credentials yield a bearer token."""
    client.post("/auth/register", json=CREDENTIALS)
    response = client.post("/auth/login", json=CREDENTIALS)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]


def test_login_with_wrong_password_is_unauthorized(client: TestClient) -> None:
    """Auth failure: wrong password is rejected."""
    client.post("/auth/register", json=CREDENTIALS)
    response = client.post(
        "/auth/login", json={"email": CREDENTIALS["email"], "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_login_with_unknown_email_gives_same_error_as_wrong_password(
    client: TestClient,
) -> None:
    """Unknown email and wrong password are indistinguishable to the caller.

    Differing responses would let an attacker enumerate registered addresses.
    """
    client.post("/auth/register", json=CREDENTIALS)

    wrong_password = client.post(
        "/auth/login", json={"email": CREDENTIALS["email"], "password": "wrong-password"}
    )
    unknown_email = client.post(
        "/auth/login", json={"email": "nobody@example.ac.uk", "password": "any-password"}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]
