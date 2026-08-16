"""Adaptive Recovery Framework: decision-logic unit tests plus a real multi-check-in sequence.

Two layers of coverage:

1. `decide_adaptive_strategy` tested directly against constructed
   `CheckInSummary` history — fast, deterministic, isolated from the model and
   the database. This is where the three required cases are shown precisely.
2. One real, multi-submission sequence through the actual `POST /assessments`
   endpoint, real model, real (SQLite-backed) database — proving the wiring,
   not just the logic. `NOTEBOOK_CASE_HIGH_STRESS` is deterministic, so
   submitting it three times in a row for the same user produces the exact
   escalating pattern needed to observe a factor switch and then an
   escalation for real, not simulated.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.adaptive_recovery import (
    ESCALATION_STREAK_THRESHOLD,
    FACTOR_SWITCH_STREAK_THRESHOLD,
    HIGHEST_SEVERITY_CLASS,
    CheckInSummary,
    decide_adaptive_strategy,
)
from tests.test_assessments import NOTEBOOK_CASE_HIGH_STRESS

# ---------------------------------------------------------------------------
# Layer 1 — decide_adaptive_strategy, in isolation
# ---------------------------------------------------------------------------


def test_first_checkin_falls_back_to_point_in_time() -> None:
    """(c) No history at all — the point-in-time plan must pass through unchanged."""
    decision = decide_adaptive_strategy(
        current_predicted_class=1,
        current_top_driver="study_load",
        previous_engagement="no_previous_checkin",
        history=[],
    )

    assert decision.strategy == "point_in_time"
    assert decision.applied is False


def test_insufficient_history_falls_back_to_point_in_time() -> None:
    """One prior check-in with a different top driver — no pattern to detect."""
    decision = decide_adaptive_strategy(
        current_predicted_class=1,
        current_top_driver="study_load",
        previous_engagement="no",
        history=[CheckInSummary(predicted_class=1, top_driver_feature="social_support")],
    )

    assert decision.strategy == "point_in_time"
    assert decision.applied is False


def test_repeated_ignored_factor_switches_strategy() -> None:
    """(a) Same top driver twice running, reported not-engaged -> factor switch."""
    decision = decide_adaptive_strategy(
        current_predicted_class=1,
        current_top_driver="study_load",
        previous_engagement="no",
        history=[CheckInSummary(predicted_class=1, top_driver_feature="study_load")],
    )

    assert decision.strategy == "factor_switch"
    assert decision.applied is True
    assert decision.switched_feature == "study_load"
    assert decision.reason == "repeated_factor_switch:study_load:streak=2"


def test_repeated_factor_with_partial_engagement_also_switches() -> None:
    """"Partially" engaged counts as not-engaged-enough, same as "no"."""
    decision = decide_adaptive_strategy(
        current_predicted_class=1,
        current_top_driver="study_load",
        previous_engagement="partially",
        history=[CheckInSummary(predicted_class=1, top_driver_feature="study_load")],
    )

    assert decision.strategy == "factor_switch"


def test_repeated_factor_with_full_engagement_does_not_switch() -> None:
    """Reported "yes" (engaged) must NOT trigger a switch even with a repeated factor."""
    decision = decide_adaptive_strategy(
        current_predicted_class=1,
        current_top_driver="study_load",
        previous_engagement="yes",
        history=[CheckInSummary(predicted_class=1, top_driver_feature="study_load")],
    )

    assert decision.strategy == "point_in_time"
    assert decision.applied is False


def test_factor_streak_breaks_on_non_consecutive_match() -> None:
    """A matching factor two check-ins back, with a different one in between, does not count.

    "Consecutive" must mean an unbroken run ending at the current check-in,
    not "appeared somewhere in recent history".
    """
    decision = decide_adaptive_strategy(
        current_predicted_class=1,
        current_top_driver="study_load",
        previous_engagement="no",
        history=[
            CheckInSummary(predicted_class=1, top_driver_feature="social_support"),
            CheckInSummary(predicted_class=1, top_driver_feature="study_load"),
        ],
    )

    assert decision.strategy == "point_in_time"


def test_sustained_high_severity_escalates_regardless_of_engagement() -> None:
    """(b) Three consecutive class-2 check-ins escalate, even fully engaged."""
    decision = decide_adaptive_strategy(
        current_predicted_class=HIGHEST_SEVERITY_CLASS,
        current_top_driver="study_load",
        previous_engagement="yes",  # engagement must not matter here
        history=[
            CheckInSummary(predicted_class=HIGHEST_SEVERITY_CLASS, top_driver_feature="study_load"),
            CheckInSummary(predicted_class=HIGHEST_SEVERITY_CLASS, top_driver_feature="study_load"),
        ],
    )

    assert decision.strategy == "escalation"
    assert decision.applied is True
    assert decision.escalation_message is not None
    assert decision.reason == f"sustained_high_severity:streak={ESCALATION_STREAK_THRESHOLD}"


def test_escalation_streak_breaks_on_a_lower_class_in_between() -> None:
    """Two class-2 check-ins with a moderate one between them is not a streak of 3."""
    decision = decide_adaptive_strategy(
        current_predicted_class=HIGHEST_SEVERITY_CLASS,
        current_top_driver="study_load",
        previous_engagement="no",
        history=[
            CheckInSummary(predicted_class=1, top_driver_feature="study_load"),
            CheckInSummary(predicted_class=HIGHEST_SEVERITY_CLASS, top_driver_feature="study_load"),
        ],
    )

    assert decision.strategy != "escalation"


def test_escalation_overrides_a_simultaneously_valid_factor_switch() -> None:
    """When both rules would fire, escalation must win — not run alongside a switch."""
    decision = decide_adaptive_strategy(
        current_predicted_class=HIGHEST_SEVERITY_CLASS,
        current_top_driver="study_load",
        previous_engagement="no",  # would also satisfy the factor-switch rule
        history=[
            CheckInSummary(predicted_class=HIGHEST_SEVERITY_CLASS, top_driver_feature="study_load"),
            CheckInSummary(predicted_class=HIGHEST_SEVERITY_CLASS, top_driver_feature="study_load"),
        ],
    )

    assert decision.strategy == "escalation"


def test_no_current_top_driver_cannot_trigger_factor_switch() -> None:
    """An affirmation check-in (no recommendations) has nothing to switch."""
    decision = decide_adaptive_strategy(
        current_predicted_class=0,
        current_top_driver=None,
        previous_engagement="no",
        history=[CheckInSummary(predicted_class=0, top_driver_feature=None)],
    )

    assert decision.strategy == "point_in_time"


assert FACTOR_SWITCH_STREAK_THRESHOLD == 2, "tests above assume the documented threshold"
assert ESCALATION_STREAK_THRESHOLD == 3, "tests above assume the documented threshold"


# ---------------------------------------------------------------------------
# Layer 2 — a real three-submission sequence through the live endpoint
# ---------------------------------------------------------------------------


def test_real_sequence_first_checkin_then_factor_switch_then_escalation(
    client: TestClient, db_session
) -> None:
    """Submit the same real, deterministic fixture three times for one user.

    Because the model and the fixture are both deterministic, this reproduces
    all three required cases for real, not simulated:
      1st submission (no prior history)              -> point-in-time, unchanged
      2nd submission (engagement "no" on the 1st)     -> factor switch
      3rd submission (engagement "no" on the 2nd)     -> escalation, overriding
                                                          the factor switch
    """
    credentials = {"email": "adaptive.sequence@example.ac.uk", "password": "a-long-enough-password"}
    client.post("/auth/register", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # --- (c) first-ever check-in: falls back to point-in-time, unchanged ---
    first = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no_previous_checkin")
    r1 = client.post("/assessments", json=first, headers=headers)
    assert r1.status_code == 201
    body1 = r1.json()
    assert body1["stress_level"] == 2
    assert body1["is_escalation"] is False
    original_titles = [r["title"] for r in body1["recommendations"]]
    assert original_titles == [
        "Pause one commitment for a fortnight",
        "Decline one thing this week",
        "A short weekly note on what went well",
    ]

    # --- (a) second check-in, reporting non-engagement with the first ---
    second = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no")
    r2 = client.post("/assessments", json=second, headers=headers)
    assert r2.status_code == 201
    body2 = r2.json()
    assert body2["stress_level"] == 2  # same deterministic input -> same class
    assert body2["is_escalation"] is False, "streak of 2 must not escalate yet (needs 3)"

    switched_titles = [r["title"] for r in body2["recommendations"]]
    # Priority 1 (extracurricular_activities) swapped to its catalogue alternate...
    assert switched_titles[0] == "Hand off one part of it"
    assert switched_titles[0] != original_titles[0]
    # ...priorities 2 and 3 (different factors) are untouched.
    assert switched_titles[1:] == original_titles[1:]

    # --- (b) third check-in, reporting non-engagement with the second ---
    third = dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no")
    r3 = client.post("/assessments", json=third, headers=headers)
    assert r3.status_code == 201
    body3 = r3.json()
    assert body3["stress_level"] == 2
    assert body3["is_escalation"] is True, "3 consecutive class-2 check-ins must escalate"
    assert body3["recommendations"] == [], "escalation replaces the recommendation list, not supplements it"
    assert body3["escalation_message"]
    assert "wellbeing service" in body3["escalation_message"]

    # --- persisted audit trail matches what was actually decided ---
    # `db_session` is the exact session the app used (conftest's `client`
    # fixture overrides get_db with it), so this reads the same rows back
    # rather than opening a second, disconnected connection.
    from app.models.recommendation import Recommendation

    def _recommendation_for(assessment_id: int) -> Recommendation:
        return (
            db_session.query(Recommendation)
            .filter(Recommendation.assessment_id == assessment_id)
            .one()
        )

    rec1 = _recommendation_for(body1["assessment_id"])
    rec2 = _recommendation_for(body2["assessment_id"])
    rec3 = _recommendation_for(body3["assessment_id"])

    assert rec1.adaptive_recovery_applied is False
    assert rec1.adaptive_recovery_reason == "no_pattern_detected"

    assert rec2.adaptive_recovery_applied is True
    assert rec2.adaptive_recovery_reason == "repeated_factor_switch:extracurricular_activities:streak=2"
    assert rec2.is_escalation is False

    assert rec3.adaptive_recovery_applied is True
    assert rec3.adaptive_recovery_reason == "sustained_high_severity:streak=3"
    assert rec3.is_escalation is True
    assert rec3.actions == []
