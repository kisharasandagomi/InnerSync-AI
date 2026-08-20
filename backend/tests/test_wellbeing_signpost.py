"""Wellbeing signpost status (round 7): GET /assessments/escalation-status.

Mirrors `test_adaptive_recovery.py`'s real-sequence pattern: one real,
multi-submission sequence through the actual `POST /assessments` endpoint
with the model, database, and Adaptive Recovery Framework all genuinely
exercised, rather than a constructed/mocked `is_escalation` value. This
proves the profile page's signpost tracks the real
`Recommendation.is_escalation` flag -- appearing once sustained high stress
is detected, and clearing again once a later check-in no longer escalates --
not a separate calculation of its own.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.test_assessments import NOTEBOOK_CASE_HIGH_STRESS
from tests.test_personalization import LOW_STRESS_CASE


def test_escalation_status_is_false_with_no_checkins_yet(client: TestClient) -> None:
    credentials = {"email": "signpost.none@example.ac.uk", "password": "a-long-enough-password"}
    client.post("/auth/register", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]

    response = client.get(
        "/assessments/escalation-status", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["is_escalation"] is False


def test_escalation_status_requires_authentication(client: TestClient) -> None:
    response = client.get("/assessments/escalation-status")
    assert response.status_code == 401


def test_escalation_status_appears_then_clears_across_a_real_sequence(
    client: TestClient,
) -> None:
    """1st-3rd check-ins: same real escalating pattern
    `test_adaptive_recovery.py`'s own live sequence produces (3 consecutive
    class-2 results escalate). 4th check-in: a genuinely low-stress result,
    which must clear the signpost again -- proving it reflects the *most
    recent* check-in, not "has ever escalated"."""
    credentials = {"email": "signpost.sequence@example.ac.uk", "password": "a-long-enough-password"}
    client.post("/auth/register", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    def _status() -> bool:
        return client.get("/assessments/escalation-status", headers=headers).json()[
            "is_escalation"
        ]

    first = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no_previous_checkin")
    r1 = client.post("/assessments", json=first, headers=headers)
    assert r1.json()["is_escalation"] is False
    assert _status() is False, "no signpost after just the 1st high-stress check-in"

    second = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no")
    r2 = client.post("/assessments", json=second, headers=headers)
    assert r2.json()["is_escalation"] is False
    assert _status() is False, "no signpost after 2 consecutive high-stress check-ins (needs 3)"

    third = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no")
    r3 = client.post("/assessments", json=third, headers=headers)
    assert r3.json()["is_escalation"] is True
    assert _status() is True, "signpost must appear once the 3rd check-in escalates"

    fourth = dict(LOW_STRESS_CASE, previous_engagement="no")
    r4 = client.post("/assessments", json=fourth, headers=headers)
    assert r4.json()["is_escalation"] is False
    assert _status() is False, "signpost must clear once a later check-in no longer escalates"


def test_escalation_status_does_not_leak_across_users(client: TestClient) -> None:
    """A second user's own history must never affect what the first user's
    signpost shows, even after the first user genuinely escalates."""
    first = {"email": "signpost.first@example.ac.uk", "password": "a-long-enough-password"}
    second = {"email": "signpost.second@example.ac.uk", "password": "a-long-enough-password"}
    client.post("/auth/register", json=first)
    token1 = client.post("/auth/login", json=first).json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    for engagement in ("no_previous_checkin", "no", "no"):
        client.post(
            "/assessments",
            json=dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement=engagement),
            headers=headers1,
        )
    assert (
        client.get("/assessments/escalation-status", headers=headers1).json()["is_escalation"]
        is True
    )

    client.post("/auth/register", json=second)
    token2 = client.post("/auth/login", json=second).json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    response = client.get("/assessments/escalation-status", headers=headers2)
    assert response.json()["is_escalation"] is False
