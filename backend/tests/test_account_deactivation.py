"""Account deactivation: password confirmation, soft-delete, and its effect on login."""

from __future__ import annotations

from fastapi.testclient import TestClient

CREDENTIALS = {"email": "deactivate.me@example.ac.uk", "password": "a-long-enough-password"}


def _register_and_login(client: TestClient) -> str:
    client.post("/auth/register", json=CREDENTIALS)
    response = client.post("/auth/login", json=CREDENTIALS)
    return response.json()["access_token"]


def test_deactivate_requires_correct_password(client: TestClient) -> None:
    """Wrong password confirmation is rejected; the account stays active."""
    token = _register_and_login(client)

    response = client.post(
        "/auth/deactivate",
        json={"password": "not-the-right-password"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401

    # Still active: login still works.
    still_works = client.post("/auth/login", json=CREDENTIALS)
    assert still_works.status_code == 200


def test_deactivate_requires_authentication(client: TestClient) -> None:
    """No bearer token at all is rejected before the password is even checked."""
    response = client.post("/auth/deactivate", json={"password": CREDENTIALS["password"]})
    assert response.status_code == 401


def test_deactivate_happy_path_returns_204(client: TestClient) -> None:
    """Correct password confirmation succeeds with no body."""
    token = _register_and_login(client)

    response = client.post(
        "/auth/deactivate",
        json={"password": CREDENTIALS["password"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


def test_deactivated_account_cannot_log_in_again(client: TestClient) -> None:
    """The exact scenario the feature exists for: login is blocked afterward."""
    token = _register_and_login(client)
    client.post(
        "/auth/deactivate",
        json={"password": CREDENTIALS["password"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post("/auth/login", json=CREDENTIALS)
    assert response.status_code == 401


def test_deactivated_account_login_failure_matches_wrong_password_message(
    client: TestClient,
) -> None:
    """A deactivated account fails login the same way as a wrong password.

    A distinct message would confirm the email belongs to a real (if
    deactivated) account -- the same account-enumeration concern
    test_login_with_unknown_email_gives_same_error_as_wrong_password already
    covers for registration status.
    """
    token = _register_and_login(client)
    client.post(
        "/auth/deactivate",
        json={"password": CREDENTIALS["password"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    deactivated = client.post("/auth/login", json=CREDENTIALS)
    wrong_password = client.post(
        "/auth/login", json={"email": "someone.else@example.ac.uk", "password": "whatever123"}
    )
    assert deactivated.json()["detail"] == wrong_password.json()["detail"]


def test_deactivated_accounts_existing_token_stops_working(client: TestClient) -> None:
    """A still-unexpired access token issued before deactivation is rejected
    on the next authenticated request, not just on a fresh login attempt."""
    token = _register_and_login(client)
    client.post(
        "/auth/deactivate",
        json={"password": CREDENTIALS["password"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.get(
        "/assessments/history", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_deactivate_does_not_delete_the_account_row(client: TestClient) -> None:
    """Soft-delete only: re-registering with the same email still conflicts,
    proving the row (and its uniqueness constraint) still exists."""
    token = _register_and_login(client)
    client.post(
        "/auth/deactivate",
        json={"password": CREDENTIALS["password"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = client.post("/auth/register", json=CREDENTIALS)
    assert response.status_code == 409
