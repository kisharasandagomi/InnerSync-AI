"""Contract tests for `GET /assessments/history` (Progress Monitoring Dashboard).

Read-only endpoint: these tests cover the two properties that matter for a
history view over sensitive wellbeing data — it never leaks another user's
rows, and it returns rows in the order a trend view needs them in.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.test_assessments import NOTEBOOK_CASE_HIGH_STRESS


def _register_and_login(client: TestClient, email: str) -> dict[str, str]:
    credentials = {"email": email, "password": "a-long-enough-password"}
    client.post("/auth/register", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_history_requires_authentication(client: TestClient) -> None:
    """Auth failure: an unauthenticated request is rejected."""
    response = client.get("/assessments/history")

    assert response.status_code == 401


def test_history_empty_for_a_user_with_no_check_ins(client: TestClient) -> None:
    """A brand-new user has no history yet — an empty list, not an error."""
    headers = _register_and_login(client, "no.history@example.ac.uk")

    response = client.get("/assessments/history", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_history_returns_only_the_authenticated_users_own_rows(client: TestClient) -> None:
    """User B's history must never include a row created by user A."""
    headers_a = _register_and_login(client, "student.a@example.ac.uk")
    headers_b = _register_and_login(client, "student.b@example.ac.uk")

    # user A submits two check-ins; user B submits one.
    client.post("/assessments", json=NOTEBOOK_CASE_HIGH_STRESS, headers=headers_a)
    second = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="yes")
    client.post("/assessments", json=second, headers=headers_a)
    client.post("/assessments", json=NOTEBOOK_CASE_HIGH_STRESS, headers=headers_b)

    body_a = client.get("/assessments/history", headers=headers_a).json()
    body_b = client.get("/assessments/history", headers=headers_b).json()

    assert len(body_a) == 2
    assert len(body_b) == 1
    # No overlap: user B's single assessment_id must not appear in A's list.
    assert body_b[0]["assessment_id"] not in {row["assessment_id"] for row in body_a}


def test_history_is_returned_in_chronological_order(client: TestClient) -> None:
    """Three submissions for one user come back oldest-first, matching submission order."""
    headers = _register_and_login(client, "sequence@example.ac.uk")

    first = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no_previous_checkin")
    second = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no")
    third = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no")

    ids = []
    for payload in (first, second, third):
        response = client.post("/assessments", json=payload, headers=headers)
        ids.append(response.json()["assessment_id"])

    body = client.get("/assessments/history", headers=headers).json()

    assert [row["assessment_id"] for row in body] == ids
    # created_at must be non-decreasing across the returned sequence.
    timestamps = [row["created_at"] for row in body]
    assert timestamps == sorted(timestamps)


def test_history_item_shape_and_vocabulary(client: TestClient) -> None:
    """Each item carries the dashboard's fields and none of the forbidden vocabulary."""
    headers = _register_and_login(client, "shape.check@example.ac.uk")
    client.post("/assessments", json=NOTEBOOK_CASE_HIGH_STRESS, headers=headers)

    response = client.get("/assessments/history", headers=headers)
    body = response.json()

    assert len(body) == 1
    item = body[0]
    for field in (
        "assessment_id",
        "created_at",
        "stress_level",
        "stress_level_label",
        "previous_engagement",
        "adaptive_recovery_applied",
        "is_escalation",
        "top_factor_phrase",
        "explanation",
    ):
        assert field in item, f"missing field: {field}"

    assert item["stress_level"] == 2
    assert item["stress_level_label"] == "high"
    assert item["adaptive_recovery_applied"] is False
    assert item["is_escalation"] is False
    assert item["top_factor_phrase"] is not None
    assert len(item["explanation"]) > len(item["top_factor_phrase"])

    payload = response.text.lower()
    for term in ("shap", "feature", "importance", "severity", "diagnosis", "treatment"):
        assert term not in payload, f"response leaked forbidden vocabulary: {term}"


def test_history_explanation_matches_what_was_returned_at_submission_time(
    client: TestClient,
) -> None:
    """The stored, replayed explanation is byte-identical to the original response."""
    headers = _register_and_login(client, "explanation.replay@example.ac.uk")

    submit_response = client.post(
        "/assessments", json=NOTEBOOK_CASE_HIGH_STRESS, headers=headers
    )
    original_explanation = submit_response.json()["explanation"]

    history = client.get("/assessments/history", headers=headers).json()

    assert len(history) == 1
    assert history[0]["explanation"] == original_explanation
