"""Adaptive Recovery Framework (Module 8, Component 5).

Changes recommendation strategy across consecutive check-ins, and escalates
toward university wellbeing services when elevated stress persists regardless
of engagement. Builds directly on the point-in-time Recommendation Engine
(`ml_pipeline.src.recommendation`) — every existing recommendation log entry
already stamps `adaptive_recovery_applied: false` specifically so this could
be added later without confusion. This module is what makes that flag real.

**Why this lives in `backend/`, not `ml_pipeline/src/recommendation/`,
against ADR-001.** ADR-001 draws the line at training: `backend/` may only
*load* what `ml_pipeline/` produces, never fit anything. This module fits
nothing — no ML retraining is involved anywhere here — so ADR-001's letter
doesn't forbid either location. Its *spirit* does point one way, though: this
logic requires querying **live, per-user assessment history from the
production database**, a concept the research world has no notion of, since
`ml_pipeline/` notebooks operate on static, anonymised training datasets, not
a live `users`/`assessments` table. Putting this in `ml_pipeline/src/` would
mean importing SQLAlchemy sessions and ORM models into the research package —
inverting the one direction ADR-001 actually specifies ("`ml_pipeline/` must
never import from `backend/`"). This module instead **imports from**
`ml_pipeline.src.recommendation` (the catalogue's alternate templates, the
escalation message, the vocabulary safety gate) exactly as the point-in-time
engine's own consumers do, so recommendation content and its safety
guarantees are shared, not duplicated.

Two rules, checked in this order (escalation first, since it applies
"regardless of engagement" and must override a factor switch, not sit
alongside one):

1. **Escalation** — predicted stress at the highest severity level (class 2)
   across 3+ consecutive check-ins. Replaces the normal recommendation list
   with a wellbeing-service signpost.
2. **Factor switch** — the same feature was the top recommendation driver
   across 2+ consecutive check-ins *and* the student reported not engaging,
   or only partially engaging, with the previous one. Swaps that one
   recommendation for the catalogue's alternate; leaves any other
   recommendations in the plan untouched.

A first-ever check-in, or one with insufficient history to detect either
pattern, falls back to the point-in-time plan unchanged — this is the
default outcome of the same logic, not a special-cased branch.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Sequence

from sqlalchemy.orm import Session

from app.models.assessment import Assessment, EngagementLevel
from app.models.recommendation import Recommendation as RecommendationRow
from ml_pipeline.src.explainability.generator import validate_user_facing_text
from ml_pipeline.src.recommendation import (
    RecommendationPlan,
    SUSTAINED_HIGH_STRESS_ESCALATION_MESSAGE,
    get_alternate_template,
)
from ml_pipeline.src.recommendation.engine import Recommendation as RecommendationItem

# Class label for "high" stress — see feature_schema.json's target.class_meaning
# (0 low, 1 moderate, 2 high). Hardcoded here the same way
# app/schemas/assessment.py already documents the ordering, rather than
# threading it through as a parameter for a value that never changes.
HIGHEST_SEVERITY_CLASS = 2

# "3+ consecutive check-ins" — the current one plus at least 2 immediately
# preceding, unbroken.
ESCALATION_STREAK_THRESHOLD = 3

# "2+ consecutive check-ins" — the current one plus at least 1 immediately
# preceding, unbroken.
FACTOR_SWITCH_STREAK_THRESHOLD = 2

# History rows fetched per decision. Comfortably covers both thresholds above
# with headroom for the audit reason string; cheap given the existing indexes
# on assessments.user_id and assessments.created_at.
HISTORY_LOOKBACK_LIMIT = 10

_NOT_ENGAGED = {EngagementLevel.NO.value, EngagementLevel.PARTIALLY.value}


@dataclass(frozen=True)
class CheckInSummary:
    """The minimal facts about one past check-in the decision logic needs.

    Attributes:
        predicted_class: 0, 1, or 2.
        top_driver_feature: The feature name behind that check-in's
            priority-1 recommendation, or None if it had no recommendations
            (an affirmation or an escalation).
    """

    predicted_class: int
    top_driver_feature: str | None


@dataclass(frozen=True)
class AdaptiveDecision:
    """The outcome of applying the two rules to one current check-in.

    A pure value produced by `decide_adaptive_strategy` — no DB access, no
    side effects — which is what keeps that function directly unit-testable
    against constructed history rather than requiring a live database.
    """

    strategy: str  # "point_in_time" | "factor_switch" | "escalation"
    applied: bool
    reason: str
    switched_feature: str | None = None
    escalation_message: str | None = None


@dataclass
class AdaptiveResult:
    """What `assessment_service.py` persists and returns, after adaptation."""

    recommendations: list[RecommendationItem]
    is_affirmation: bool
    affirmation_text: str | None
    is_escalation: bool
    escalation_message: str | None
    adaptive_recovery_applied: bool
    adaptive_recovery_reason: str
    decision: AdaptiveDecision = field(repr=False)


def decide_adaptive_strategy(
    current_predicted_class: int,
    current_top_driver: str | None,
    previous_engagement: str,
    history: Sequence[CheckInSummary],
) -> AdaptiveDecision:
    """Pure decision function: given the current check-in and prior history, decide.

    Args:
        current_predicted_class: This check-in's predicted class (0/1/2).
        current_top_driver: This check-in's priority-1 recommendation feature,
            or None if it has no recommendations.
        previous_engagement: One of `EngagementLevel`'s values, self-reported
            for the *immediately preceding* check-in's recommendations.
        history: Prior check-ins only, **most-recent-first**, newest at
            index 0. Must not include the current check-in.

    Returns:
        The decision: which strategy applies, and why.
    """
    # Rule 1 — escalation. Checked first and unconditionally: it must override
    # a factor switch, not coexist with one, and applies regardless of
    # engagement.
    if current_predicted_class == HIGHEST_SEVERITY_CLASS:
        streak = 1
        for entry in history:
            if entry.predicted_class == HIGHEST_SEVERITY_CLASS:
                streak += 1
            else:
                break
        if streak >= ESCALATION_STREAK_THRESHOLD:
            return AdaptiveDecision(
                strategy="escalation",
                applied=True,
                reason=f"sustained_high_severity:streak={streak}",
                escalation_message=SUSTAINED_HIGH_STRESS_ESCALATION_MESSAGE,
            )

    # Rule 2 — factor switch. Only meaningful if this check-in actually has a
    # top driver, and only triggers on reported non-engagement with the
    # single most recent prior check-in (the only one `previous_engagement`
    # was ever asked about).
    if current_top_driver is not None and previous_engagement in _NOT_ENGAGED:
        streak = 1
        for entry in history:
            if entry.top_driver_feature == current_top_driver:
                streak += 1
            else:
                break
        if streak >= FACTOR_SWITCH_STREAK_THRESHOLD:
            return AdaptiveDecision(
                strategy="factor_switch",
                applied=True,
                reason=f"repeated_factor_switch:{current_top_driver}:streak={streak}",
                switched_feature=current_top_driver,
            )

    return AdaptiveDecision(strategy="point_in_time", applied=False, reason="no_pattern_detected")


def fetch_recent_history(
    db: Session, user_id: int, limit: int = HISTORY_LOOKBACK_LIMIT
) -> list[CheckInSummary]:
    """Load a user's own prior check-ins, most-recent-first.

    Must be called before the current check-in's `Assessment` row is added to
    the session, so it cannot see itself.

    Args:
        db: Open database session.
        user_id: Whose history to fetch — always the authenticated caller's
            own id; this module never reads another user's rows.
        limit: Maximum prior check-ins to consider.

    Returns:
        Prior check-ins, newest first.
    """
    rows = (
        db.query(Assessment, RecommendationRow)
        .join(RecommendationRow, RecommendationRow.assessment_id == Assessment.id)
        .filter(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.desc())
        .limit(limit)
        .all()
    )
    summaries = []
    for assessment, recommendation in rows:
        top_driver = recommendation.actions[0]["feature"] if recommendation.actions else None
        summaries.append(
            CheckInSummary(predicted_class=assessment.predicted_class, top_driver_feature=top_driver)
        )
    return summaries


def _apply_factor_switch(
    recommendations: Sequence[RecommendationItem], feature: str
) -> list[RecommendationItem]:
    """Replace the priority-1 recommendation for `feature` with its catalogue alternate.

    Other recommendations in the plan (priority 2, 3) are left untouched —
    the rule is about the one repeated factor, not the whole plan.

    Args:
        recommendations: The point-in-time plan's recommendations.
        feature: The feature whose priority-1 suggestion should be swapped.

    Returns:
        A new list with that one entry replaced.
    """
    alternate = get_alternate_template(feature)
    validate_user_facing_text(f"{alternate.title} {alternate.action} {alternate.rationale}")

    switched = []
    for item in recommendations:
        if item.feature == feature and item.priority == 1:
            switched.append(
                replace(
                    item,
                    category=alternate.category,
                    title=alternate.title,
                    action=alternate.action,
                    rationale=alternate.rationale,
                )
            )
        else:
            switched.append(item)
    return switched


def plan_with_adaptive_recovery(
    db: Session,
    user_id: int,
    current_predicted_class: int,
    base_plan: RecommendationPlan,
    previous_engagement: str,
) -> AdaptiveResult:
    """Apply the Adaptive Recovery Framework on top of a point-in-time plan.

    Args:
        db: Open database session.
        user_id: The authenticated caller — history is scoped to their own
            rows only.
        current_predicted_class: This check-in's predicted class.
        base_plan: The unmodified point-in-time plan for this check-in
            (`ml_pipeline.src.recommendation.build_recommendation_plan`'s
            output), computed before this function is called.
        previous_engagement: Self-reported engagement with the previous
            check-in's recommendations; one of `EngagementLevel`'s values.

    Returns:
        The final result to persist — identical to the point-in-time plan
        unless a pattern was actually detected.
    """
    history = fetch_recent_history(db, user_id)
    current_top_driver = base_plan.recommendations[0].feature if base_plan.has_actions else None

    decision = decide_adaptive_strategy(
        current_predicted_class=current_predicted_class,
        current_top_driver=current_top_driver,
        previous_engagement=previous_engagement,
        history=history,
    )

    if decision.strategy == "escalation":
        return AdaptiveResult(
            recommendations=[],
            is_affirmation=False,
            affirmation_text=None,
            is_escalation=True,
            escalation_message=decision.escalation_message,
            adaptive_recovery_applied=True,
            adaptive_recovery_reason=decision.reason,
            decision=decision,
        )

    if decision.strategy == "factor_switch":
        switched = _apply_factor_switch(base_plan.recommendations, decision.switched_feature)
        return AdaptiveResult(
            recommendations=switched,
            is_affirmation=False,
            affirmation_text=None,
            is_escalation=False,
            escalation_message=None,
            adaptive_recovery_applied=True,
            adaptive_recovery_reason=decision.reason,
            decision=decision,
        )

    # point_in_time fallback: unchanged, including first-ever check-ins and
    # any case where the patterns above simply weren't detected.
    return AdaptiveResult(
        recommendations=list(base_plan.recommendations),
        is_affirmation=not base_plan.has_actions,
        affirmation_text=base_plan.affirmation,
        is_escalation=False,
        escalation_message=None,
        adaptive_recovery_applied=False,
        adaptive_recovery_reason=decision.reason,
        decision=decision,
    )
