"""The core endpoint, including a drift check against the notebook output.

`NOTEBOOK_CASE_HIGH_STRESS` is the exact feature vector of test row 2 — the
"correct_class_2_high" local case examined in `06_ExplanationGenerator.ipynb`
and `07_RecommendationEngine.ipynb`. The expected explanation and recommendation
titles below are copied verbatim from those notebooks' executed output.

The point of pinning them here is drift detection: if the backend port and the
research-world logic ever diverge — a changed template, a different SHAP axis, a
reordered feature vector — this test fails rather than the two quietly
disagreeing about what a student should be told.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

# Test row 2 of the stratified split (random_state=42, test_size=0.2).
NOTEBOOK_CASE_HIGH_STRESS = {
    "self_esteem": 14,
    "mental_health_history": 1,
    "headache": 5,
    "breathing_problem": 5,
    "noise_level": 3,
    "living_conditions": 2,
    "safety": 1,
    "basic_needs": 2,
    "academic_performance": 2,
    "study_load": 5,
    "teacher_student_relationship": 2,
    "social_support": 1,
    "peer_pressure": 5,
    "extracurricular_activities": 5,
    # First submission in each of these tests (a fresh user, one call) — the
    # honest value for a genuine first-ever check-in.
    "previous_engagement": "no_previous_checkin",
}

EXPECTED_CLASS = 2

EXPECTED_EXPLANATION = (
    "Your current wellbeing check-in suggests you are under a fair amount of "
    "pressure at the moment. In particular, how much you are taking on outside "
    "your studies appears to be stretching you. Alongside that, pressure from "
    "the people around you appears to be adding to what you are already "
    "managing, and how you have been feeling about yourself lately appears to "
    "be weighing on you. This is a snapshot of how things look right now rather "
    "than a fixed picture. If this feels familiar or has been going on for a "
    "while, talking it through with your university wellbeing service is a "
    "reasonable next step."
)

EXPECTED_RECOMMENDATION_TITLES = [
    "Pause one commitment for a fortnight",
    "Decline one thing this week",
    "A short weekly note on what went well",
]

# Vocabulary that must never appear in a response body.
FORBIDDEN_IN_RESPONSE = [
    "shap",
    "feature",
    "importance",
    "severity",
    "diagnosis",
    "treatment",
    "disorder",
]


def test_assessment_requires_authentication(client: TestClient) -> None:
    """Auth failure: an unauthenticated submission is rejected."""
    response = client.post("/assessments", json=NOTEBOOK_CASE_HIGH_STRESS)

    assert response.status_code == 401


def test_assessment_rejects_invalid_token(client: TestClient) -> None:
    """Auth failure: a malformed bearer token is rejected."""
    response = client.post(
        "/assessments",
        json=NOTEBOOK_CASE_HIGH_STRESS,
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


def test_assessment_response_shape(client: TestClient, auth_headers: dict[str, str]) -> None:
    """Happy path: the response carries level, explanation and recommendations."""
    response = client.post(
        "/assessments", json=NOTEBOOK_CASE_HIGH_STRESS, headers=auth_headers
    )

    assert response.status_code == 201
    body = response.json()
    for field in (
        "assessment_id",
        "created_at",
        "stress_level",
        "stress_level_label",
        "explanation",
        "recommendations",
        "is_affirmation",
        "is_escalation",
    ):
        assert field in body, f"missing field: {field}"

    assert body["stress_level"] in (0, 1, 2)
    assert isinstance(body["recommendations"], list)
    for item in body["recommendations"]:
        assert {"priority", "title", "action", "rationale", "category"} <= set(item)


def test_assessment_matches_notebook_output(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Drift check: the API reproduces the notebook result for the same input."""
    response = client.post(
        "/assessments", json=NOTEBOOK_CASE_HIGH_STRESS, headers=auth_headers
    )
    body = response.json()

    assert body["stress_level"] == EXPECTED_CLASS
    assert body["stress_level_label"] == "high"
    assert body["explanation"] == EXPECTED_EXPLANATION
    assert body["is_affirmation"] is False
    # A single first-ever submission: neither adaptive rule has history to act
    # on, so this must reproduce the unmodified point-in-time plan exactly.
    assert body["is_escalation"] is False
    assert [r["title"] for r in body["recommendations"]] == EXPECTED_RECOMMENDATION_TITLES
    assert [r["priority"] for r in body["recommendations"]] == [1, 2, 3]


def test_response_leaks_no_technical_vocabulary(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """No SHAP value, feature name or clinical term may reach the caller."""
    response = client.post(
        "/assessments", json=NOTEBOOK_CASE_HIGH_STRESS, headers=auth_headers
    )
    payload = response.text.lower()

    leaked = [term for term in FORBIDDEN_IN_RESPONSE if term in payload]
    assert not leaked, f"response leaked technical vocabulary: {leaked}"


def test_assessment_persists_all_three_rows(
    client: TestClient, auth_headers: dict[str, str], db_session
) -> None:
    """The assessment, its explanation, and its recommendation are all stored."""
    from app.models.assessment import Assessment
    from app.models.explanation_record import ExplanationRecord
    from app.models.recommendation import Recommendation

    response = client.post(
        "/assessments", json=NOTEBOOK_CASE_HIGH_STRESS, headers=auth_headers
    )
    assessment_id = response.json()["assessment_id"]

    assessment = db_session.get(Assessment, assessment_id)
    assert assessment is not None
    assert assessment.model_version == "v2"
    assert assessment.peer_pressure == NOTEBOOK_CASE_HIGH_STRESS["peer_pressure"]
    assert assessment.previous_engagement == "no_previous_checkin"

    record = (
        db_session.query(ExplanationRecord)
        .filter(ExplanationRecord.assessment_id == assessment_id)
        .one()
    )
    # The audit trail is persisted but never returned to the caller.
    assert record.paragraph == EXPECTED_EXPLANATION
    assert len(record.faithfulness_factors) == 4
    assert {"feature", "shap_value", "direction"} <= set(record.faithfulness_factors[0])

    recommendation = (
        db_session.query(Recommendation)
        .filter(Recommendation.assessment_id == assessment_id)
        .one()
    )
    assert len(recommendation.actions) == 3
    assert recommendation.adaptive_recovery_applied is False
    assert recommendation.is_escalation is False


def test_assessment_rejects_out_of_range_value(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """Values outside the schema's observed range are rejected."""
    payload = dict(NOTEBOOK_CASE_HIGH_STRESS, social_support=99)
    response = client.post("/assessments", json=payload, headers=auth_headers)

    assert response.status_code == 422
