"""Round 3 personalization features: greeting, comparative trend, hobby recommendations.

Three independent pieces, tested at the level each is actually decided:
- Greeting fallback is a pure function (`resolve_greeting_name`) plus a thin
  registration/login wiring check.
- The comparative trend message is tested as a pure function
  (`determine_comparative_trend`) for every branch including the
  escalation-coordination case, then once more end-to-end through a real
  five-submission sequence that reaches every branch for real, mirroring
  `test_adaptive_recovery.py`'s real-sequence pattern.
- Hobby personalisation is tested directly against
  `build_recommendation_plan` with a hand-constructed factor list — the
  same technique that module's own docstring describes it as designed for —
  rather than hunting for a real feature vector that happens to select
  `mental_health_history` as a top factor.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.schemas.auth import resolve_greeting_name
from app.services.adaptive_recovery import CheckInSummary
from app.services.comparative_trend import (
    COMPARATIVE_ESCALATION_COORDINATED_MESSAGE,
    COMPARATIVE_IMPROVED_MESSAGE,
    COMPARATIVE_SAME_MESSAGE,
    COMPARATIVE_WORSE_MESSAGE,
    determine_comparative_trend,
)
from ml_pipeline.src.explainability.generator import ExplanationFactor, validate_user_facing_text
from ml_pipeline.src.recommendation.engine import _resolve_action_text, build_recommendation_plan
from ml_pipeline.src.recommendation.catalogue import RECOMMENDATION_CATALOGUE
from tests.test_assessments import NOTEBOOK_CASE_HIGH_STRESS

# A deterministic low-severity feature vector — distinct in class from
# NOTEBOOK_CASE_HIGH_STRESS, needed to construct a real improve/worsen
# sequence. Not pinned to an exact expected explanation string (unlike
# NOTEBOOK_CASE_HIGH_STRESS); only its resulting class matters here.
LOW_STRESS_CASE = {
    "self_esteem": 25,
    "mental_health_history": 0,
    "headache": 0,
    "breathing_problem": 0,
    "noise_level": 1,
    "living_conditions": 4,
    "safety": 4,
    "basic_needs": 4,
    "academic_performance": 4,
    "study_load": 1,
    "teacher_student_relationship": 4,
    "social_support": 3,
    "peer_pressure": 0,
    "extracurricular_activities": 1,
    "previous_engagement": "no_previous_checkin",
}


def _register_and_login(
    client: TestClient, email: str, display_name: str | None = None, hobby: str | None = None
) -> dict[str, str]:
    payload = {"email": email, "password": "a-long-enough-password"}
    if display_name is not None:
        payload["display_name"] = display_name
    if hobby is not None:
        payload["hobby"] = hobby
    client.post("/auth/register", json=payload)
    token = client.post(
        "/auth/login", json={"email": email, "password": "a-long-enough-password"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Personalized greeting
# ---------------------------------------------------------------------------


def test_resolve_greeting_name_uses_display_name_when_set() -> None:
    assert resolve_greeting_name("Sam", "sam.k@example.ac.uk") == "Sam"


def test_resolve_greeting_name_falls_back_to_email_local_part_when_unset() -> None:
    assert resolve_greeting_name(None, "sam.k@example.ac.uk") == "sam.k"


def test_resolve_greeting_name_falls_back_when_display_name_is_blank() -> None:
    """Whitespace-only counts as unset, not a broken greeting like 'Hi , ...'."""
    assert resolve_greeting_name("   ", "sam.k@example.ac.uk") == "sam.k"


def test_resolve_greeting_name_strips_whitespace_from_a_real_name() -> None:
    assert resolve_greeting_name("  Sam  ", "sam.k@example.ac.uk") == "Sam"


def test_register_persists_display_name_and_hobby(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "named.student@example.ac.uk",
            "password": "a-long-enough-password",
            "display_name": "Alex",
            "hobby": "painting",
        },
    )

    assert response.status_code == 201
    assert response.json()["display_name"] == "Alex"


def test_register_without_display_name_leaves_it_unset(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "anon.student@example.ac.uk", "password": "a-long-enough-password"},
    )

    assert response.status_code == 201
    assert response.json()["display_name"] is None


def test_login_returns_display_name(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={
            "email": "login.name@example.ac.uk",
            "password": "a-long-enough-password",
            "display_name": "Riley",
        },
    )
    response = client.post(
        "/auth/login",
        json={"email": "login.name@example.ac.uk", "password": "a-long-enough-password"},
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Riley"


def test_login_returns_null_display_name_when_never_set(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "no.name.login@example.ac.uk", "password": "a-long-enough-password"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "no.name.login@example.ac.uk", "password": "a-long-enough-password"},
    )

    assert response.json()["display_name"] is None


# ---------------------------------------------------------------------------
# 2. Comparative trend message
# ---------------------------------------------------------------------------


def test_comparative_fallback_texts_pass_the_safety_gate() -> None:
    for text in (
        COMPARATIVE_IMPROVED_MESSAGE,
        COMPARATIVE_SAME_MESSAGE,
        COMPARATIVE_WORSE_MESSAGE,
        COMPARATIVE_ESCALATION_COORDINATED_MESSAGE,
    ):
        validate_user_facing_text(text)  # must not raise


def test_first_ever_checkin_has_no_comparative_message() -> None:
    result = determine_comparative_trend(current_predicted_class=2, history=[], is_escalation=False)

    assert result.outcome is None
    assert result.message is None


def test_comparative_message_when_improved() -> None:
    history = [CheckInSummary(predicted_class=2, top_driver_feature="study_load")]
    result = determine_comparative_trend(
        current_predicted_class=0, history=history, is_escalation=False
    )

    assert result.outcome == "improved"
    assert result.message == COMPARATIVE_IMPROVED_MESSAGE


def test_comparative_message_when_same() -> None:
    history = [CheckInSummary(predicted_class=1, top_driver_feature="study_load")]
    result = determine_comparative_trend(
        current_predicted_class=1, history=history, is_escalation=False
    )

    assert result.outcome == "same"
    assert result.message == COMPARATIVE_SAME_MESSAGE


def test_comparative_message_when_worse() -> None:
    history = [CheckInSummary(predicted_class=0, top_driver_feature="study_load")]
    result = determine_comparative_trend(
        current_predicted_class=2, history=history, is_escalation=False
    )

    assert result.outcome == "worse"
    assert result.message == COMPARATIVE_WORSE_MESSAGE
    # Self-compassion framing, not clinical or alarming language.
    assert "be gentle" in result.message.lower()


def test_escalation_takes_priority_over_the_worse_message() -> None:
    """The real-world case: escalation only fires when the prior check-in was
    also the highest class, so the ordinal outcome is structurally "same" —
    but the coordinated message must be used regardless, not the "same" one."""
    history = [CheckInSummary(predicted_class=2, top_driver_feature="study_load")]
    result = determine_comparative_trend(
        current_predicted_class=2, history=history, is_escalation=True
    )

    assert result.outcome == "same"  # the true ordinal comparison, logged for audit
    assert result.message == COMPARATIVE_ESCALATION_COORDINATED_MESSAGE
    assert result.message != COMPARATIVE_SAME_MESSAGE
    assert result.message != COMPARATIVE_WORSE_MESSAGE


def test_escalation_coordination_overrides_even_a_hypothetical_worse_outcome() -> None:
    """Defensive case: is_escalation is an explicit input, not inferred from
    the ordinal outcome — this must not depend on that structural coincidence."""
    history = [CheckInSummary(predicted_class=0, top_driver_feature="study_load")]
    result = determine_comparative_trend(
        current_predicted_class=2, history=history, is_escalation=True
    )

    assert result.outcome == "worse"
    assert result.message == COMPARATIVE_ESCALATION_COORDINATED_MESSAGE


def test_real_sequence_covers_every_comparative_branch(
    client: TestClient, db_session
) -> None:
    """One real five-submission sequence: first-ever -> worse -> same
    (no escalation yet) -> escalation-coordinated -> improved."""
    headers = _register_and_login(client, "comparative.sequence@example.ac.uk")

    # 1. First-ever check-in: no comparative message.
    r1 = client.post("/assessments", json=LOW_STRESS_CASE, headers=headers)
    assert r1.status_code == 201
    body1 = r1.json()
    assert body1["stress_level"] == 0
    assert body1["comparative_trend_message"] is None

    # 2. High stress after low: worse.
    second = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no")
    r2 = client.post("/assessments", json=second, headers=headers)
    body2 = r2.json()
    assert body2["stress_level"] == 2
    assert body2["comparative_trend_message"] == COMPARATIVE_WORSE_MESSAGE
    assert body2["is_escalation"] is False

    # 3. High stress again: same class as last time, streak only 2 -> not
    # escalation yet, so the plain "same" message is used.
    third = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no")
    r3 = client.post("/assessments", json=third, headers=headers)
    body3 = r3.json()
    assert body3["stress_level"] == 2
    assert body3["is_escalation"] is False
    assert body3["comparative_trend_message"] == COMPARATIVE_SAME_MESSAGE

    # 4. High stress a third consecutive time: escalation fires. The
    # coordinated message must replace the "same" message, not stack with
    # the escalation signpost.
    fourth = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no")
    r4 = client.post("/assessments", json=fourth, headers=headers)
    body4 = r4.json()
    assert body4["stress_level"] == 2
    assert body4["is_escalation"] is True
    assert body4["comparative_trend_message"] == COMPARATIVE_ESCALATION_COORDINATED_MESSAGE
    assert body4["comparative_trend_message"] != COMPARATIVE_SAME_MESSAGE

    # 5. Back to low stress: improved from the immediately previous (high).
    fifth = dict(LOW_STRESS_CASE, previous_engagement="no")
    r5 = client.post("/assessments", json=fifth, headers=headers)
    body5 = r5.json()
    assert body5["stress_level"] == 0
    assert body5["is_escalation"] is False
    assert body5["comparative_trend_message"] == COMPARATIVE_IMPROVED_MESSAGE

    # Audit trail: the true ordinal outcome is persisted even under
    # escalation coordination (row 4 logs "same", not a fabricated "worse").
    from app.models.recommendation import Recommendation

    rec4 = (
        db_session.query(Recommendation)
        .filter(Recommendation.assessment_id == body4["assessment_id"])
        .one()
    )
    assert rec4.comparative_trend_outcome == "same"
    assert rec4.comparative_trend_message == COMPARATIVE_ESCALATION_COORDINATED_MESSAGE


# ---------------------------------------------------------------------------
# 3. Hobby-personalized recommendations
# ---------------------------------------------------------------------------


def _mental_health_history_factor(shap_value: float = 0.05) -> ExplanationFactor:
    return ExplanationFactor(
        feature="mental_health_history",
        feature_value=1,
        shap_value=shap_value,
        direction="raising",
        rank=1,
        # Not asserted on directly by these tests — only `action` is.
        phrase="some of what you have carried before around your wellbeing may still be with you",
    )


def test_recommendation_uses_generic_action_when_no_hobby_set() -> None:
    plan = build_recommendation_plan(
        factors=[_mental_health_history_factor()], predicted_class=1, hobby=None
    )

    assert len(plan.recommendations) == 1
    generic_template = RECOMMENDATION_CATALOGUE["mental_health_history"][0]
    assert plan.recommendations[0].action == generic_template.action
    assert "{hobby}" not in plan.recommendations[0].action


def test_recommendation_uses_hobby_when_set() -> None:
    plan = build_recommendation_plan(
        factors=[_mental_health_history_factor()], predicted_class=1, hobby="painting"
    )

    assert len(plan.recommendations) == 1
    action = plan.recommendations[0].action
    assert "painting" in action
    assert action != RECOMMENDATION_CATALOGUE["mental_health_history"][0].action


def test_hobby_personalization_does_not_affect_unrelated_factors() -> None:
    """A hobby is only wired into one template; every other factor is untouched."""
    study_load_factor = ExplanationFactor(
        feature="study_load",
        feature_value=5,
        shap_value=0.08,
        direction="raising",
        rank=1,
        phrase="the amount of academic work you are carrying appears to be a real pressure",
    )
    plan = build_recommendation_plan(factors=[study_load_factor], predicted_class=2, hobby="painting")

    assert "painting" not in plan.recommendations[0].action
    assert plan.recommendations[0].action == RECOMMENDATION_CATALOGUE["study_load"][0].action


def test_resolve_action_text_falls_back_when_hobby_text_fails_the_safety_gate() -> None:
    """An unlucky hobby value (contains forbidden vocabulary) must not break the plan."""
    template = RECOMMENDATION_CATALOGUE["mental_health_history"][0]

    resolved = _resolve_action_text(template, hobby="my anxiety disorder support group")

    assert resolved == template.action  # generic fallback, not the rejected personalised text
    assert "disorder" not in resolved


def test_resolve_action_text_returns_generic_for_a_template_without_hobby_support() -> None:
    template = RECOMMENDATION_CATALOGUE["study_load"][0]

    assert _resolve_action_text(template, hobby="painting") == template.action
