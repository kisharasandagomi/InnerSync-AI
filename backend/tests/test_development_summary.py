"""Aggregated development summary (round 7): unit tests plus a real multi-check-in sequence.

Two layers, the same split `test_adaptive_recovery.py` uses:

1. `build_development_summary` tested directly against constructed
   `CheckInForSummary` lists -- fast, deterministic, isolated from the model
   and the database.
2. One real, multi-submission sequence through `POST /assessments`, reusing
   `NOTEBOOK_CASE_HIGH_STRESS` (the same deterministic fixture
   `test_adaptive_recovery.py` uses for its own live sequence), then reading
   `GET /assessments/summary` -- proving the wiring, not just the logic.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.development_summary import (
    CLOSING_MESSAGES,
    CheckInForSummary,
    build_development_summary,
)
from ml_pipeline.src.explainability.generator import validate_user_facing_text
from tests.test_assessments import NOTEBOOK_CASE_HIGH_STRESS

# ---------------------------------------------------------------------------
# Layer 0 — every closing message passes the actual safety gate
# ---------------------------------------------------------------------------


def test_every_closing_message_passes_the_safety_gate() -> None:
    assert len(CLOSING_MESSAGES) >= 3, "the pool should be more than a token 1-2 entries"
    for message in CLOSING_MESSAGES:
        validate_user_facing_text(message)  # raises on any forbidden vocabulary


def test_closing_message_pool_has_no_duplicate_entries() -> None:
    assert len(set(CLOSING_MESSAGES)) == len(CLOSING_MESSAGES)


# ---------------------------------------------------------------------------
# Layer 1 — build_development_summary, in isolation
# ---------------------------------------------------------------------------


def test_no_checkins_yet_gives_a_graceful_placeholder() -> None:
    summary = build_development_summary([], total_checkin_count=0)

    assert summary.checkins_considered == 0
    assert summary.most_frequent_factor_label is None
    assert "keep checking in" in summary.summary_sentence.lower()
    validate_user_facing_text(summary.summary_sentence)


def test_most_frequent_factor_is_the_plain_language_majority_category() -> None:
    checkins = [
        CheckInForSummary(previous_engagement="yes", top_category="academic"),
        CheckInForSummary(previous_engagement="no", top_category="academic"),
        CheckInForSummary(previous_engagement="yes", top_category="social"),
    ]

    summary = build_development_summary(checkins, total_checkin_count=3)

    assert summary.most_frequent_factor_label == "academic pressure"
    assert summary.most_frequent_factor_count == 2
    assert "academic pressure" in summary.summary_sentence


def test_engagement_count_excludes_first_ever_checkin() -> None:
    checkins = [
        CheckInForSummary(previous_engagement="no_previous_checkin", top_category=None),
        CheckInForSummary(previous_engagement="yes", top_category="academic"),
        CheckInForSummary(previous_engagement="yes", top_category="academic"),
        CheckInForSummary(previous_engagement="no", top_category="academic"),
    ]

    summary = build_development_summary(checkins, total_checkin_count=4)

    # 4 check-ins total, but only 3 had a real previous check-in to report
    # engagement against.
    assert summary.engaged_considered == 3
    assert summary.engaged_count == 2
    assert "2 of your last 3 suggestions" in summary.summary_sentence


def test_no_recommendations_in_window_omits_the_factor_clause() -> None:
    """Every considered check-in was an affirmation or escalation (no
    top_category anywhere) -- the sentence should still be coherent."""
    checkins = [
        CheckInForSummary(previous_engagement="yes", top_category=None),
        CheckInForSummary(previous_engagement="yes", top_category=None),
    ]

    summary = build_development_summary(checkins, total_checkin_count=2)

    assert summary.most_frequent_factor_label is None
    assert "engaged with" in summary.summary_sentence
    validate_user_facing_text(summary.summary_sentence)


def test_closing_message_is_deterministic_for_the_same_seed() -> None:
    checkins = [CheckInForSummary(previous_engagement="yes", top_category="academic")]

    first = build_development_summary(checkins, total_checkin_count=7)
    second = build_development_summary(checkins, total_checkin_count=7)

    assert first.closing_message == second.closing_message
    assert first.closing_message in CLOSING_MESSAGES


# ---------------------------------------------------------------------------
# Layer 2 — a real multi-check-in sequence through the live endpoints
# ---------------------------------------------------------------------------


def test_real_sequence_summary_reflects_actual_history(client: TestClient) -> None:
    """Submit the same real, deterministic fixture three times (identical to
    `test_adaptive_recovery.py`'s own live sequence), then read the summary.

    Expected, from that fixture's known behaviour:
      - 3 check-ins considered.
      - The 1st and 2nd both have `extracurricular_activities` as their
        priority-1 driver (category "academic" per the catalogue, before and
        after the round-2 factor switch); the 3rd is an escalation with no
        actions at all. So "academic pressure" is the majority factor, 2 of 3.
      - previous_engagement is "no_previous_checkin", "no", "no" -- 2 of the
        3 check-ins had a real prior check-in to report on, and neither
        reported "yes", so engaged_count is 0 of 2.
    """
    credentials = {"email": "summary.sequence@example.ac.uk", "password": "a-long-enough-password"}
    client.post("/auth/register", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/assessments",
        json=dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no_previous_checkin"),
        headers=headers,
    )
    client.post(
        "/assessments",
        json=dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no"),
        headers=headers,
    )
    client.post(
        "/assessments",
        json=dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no"),
        headers=headers,
    )

    response = client.get("/assessments/summary", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["checkins_considered"] == 3
    assert body["most_frequent_factor_label"] == "academic pressure"
    assert body["most_frequent_factor_count"] == 2
    assert body["engaged_considered"] == 2
    assert body["engaged_count"] == 0
    assert "academic pressure" in body["summary_sentence"]
    assert "0 of your last 2 suggestions" in body["summary_sentence"]
    assert body["closing_message"] in CLOSING_MESSAGES


def test_summary_requires_authentication(client: TestClient) -> None:
    response = client.get("/assessments/summary")
    assert response.status_code == 401


def test_summary_does_not_leak_across_users(client: TestClient) -> None:
    """A second user with no check-ins of their own gets the graceful
    zero-history response, not the first user's data."""
    first = {"email": "summary.first@example.ac.uk", "password": "a-long-enough-password"}
    second = {"email": "summary.second@example.ac.uk", "password": "a-long-enough-password"}
    client.post("/auth/register", json=first)
    token1 = client.post("/auth/login", json=first).json()["access_token"]
    client.post(
        "/assessments",
        json=dict(NOTEBOOK_CASE_HIGH_STRESS, previous_engagement="no_previous_checkin"),
        headers={"Authorization": f"Bearer {token1}"},
    )

    client.post("/auth/register", json=second)
    token2 = client.post("/auth/login", json=second).json()["access_token"]

    response = client.get(
        "/assessments/summary", headers={"Authorization": f"Bearer {token2}"}
    )

    assert response.json()["checkins_considered"] == 0
