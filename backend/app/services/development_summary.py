"""Aggregated, multi-check-in summary for the Progress page (round 7).

Reuses data already computed and persisted by earlier rounds --
`previous_engagement` (Assessment), `comparative_trend_outcome`,
`adaptive_recovery_applied`, `is_escalation`, and each check-in's priority-1
recommendation `category` (Recommendation) -- rather than computing anything
new from scratch. This module only aggregates across the rows
`app.api.assessments.get_assessment_history` already fetches; it runs no
prediction, SHAP, or explanation logic of its own.

Template-based, not LLM-generated, the same discipline every other
user-facing string in this system follows (see
`app.services.comparative_trend` for the closest precedent: fixed strings,
safety-gate-validated). `CLOSING_MESSAGES` is a small pool rather than one
fixed sentence specifically so a student checking in repeatedly does not see
identical closing text every time.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ml_pipeline.src.explainability.generator import validate_user_facing_text

# How many of the most recent check-ins the summary considers. Matches the
# "recent check-ins" framing in the summary sentence itself -- chosen as a
# small, human-sized window rather than the full history, which could span
# months and dilute a genuinely recent pattern.
SUMMARY_WINDOW = 5

# Plain-language labels for the internal category codes already stored on
# each recommendation action (ml_pipeline/src/recommendation/catalogue.py).
# Never the raw feature name -- see that catalogue's own category values,
# already one step removed from any ML/feature vocabulary.
CATEGORY_LABELS: dict[str, str] = {
    "academic": "academic pressure",
    "environment": "your everyday environment",
    "physical": "physical wellbeing",
    "practical_support": "everyday practical support",
    "self_reflection": "self-reflection",
    "social": "relationships and social support",
}

# A small, varied pool -- warm, non-alarming, never identical to the last
# few times a student sees this section. Each entry is validated against the
# safety gate directly below, by name, in test_development_summary.py.
CLOSING_MESSAGES: tuple[str, ...] = (
    "However things have been going, showing up to check in on yourself is worth noticing.",
    "Small, steady check-ins add up to a clearer picture than any single day ever could.",
    "Whatever this stretch has looked like, you're doing something genuinely useful by tracking it.",
    "Keep going at whatever pace works for you. There's no schedule to keep here except your own.",
    "Noticing a pattern is already a step toward doing something about it.",
)


@dataclass(frozen=True)
class CheckInForSummary:
    """The minimal, already-stored facts one check-in contributes to the summary."""

    previous_engagement: str
    top_category: str | None


@dataclass(frozen=True)
class DevelopmentSummary:
    """What the Progress page's aggregated summary section renders.

    Attributes:
        checkins_considered: How many of the most recent check-ins were
            actually available (`<= SUMMARY_WINDOW`).
        most_frequent_factor_label: Plain-language label for the category
            appearing most often as the top driver across the considered
            check-ins, or `None` if none had a ranked recommendation to draw
            from (e.g. every recent check-in was an affirmation).
        most_frequent_factor_count: How many of `checkins_considered` had
            that category as their top driver.
        engaged_count: How many of the considered check-ins (excluding a
            genuine first-ever check-in, which has no prior recommendations
            to engage with) reported `previous_engagement == "yes"`.
        engaged_considered: How many considered check-ins had a real prior
            check-in to report engagement against at all.
        summary_sentence: The synthesised, safety-gate-validated sentence.
        closing_message: One safety-gate-validated message from
            `CLOSING_MESSAGES`.
    """

    checkins_considered: int
    most_frequent_factor_label: str | None
    most_frequent_factor_count: int
    engaged_count: int
    engaged_considered: int
    summary_sentence: str
    closing_message: str


def _pick_closing_message(seed: int) -> str:
    """Deterministically pick one closing message from the pool.

    Args:
        seed: Any stable integer derived from the check-ins being
            summarised (this module uses the total historical check-in
            count) -- deterministic rather than random, so the same
            underlying data always renders the same message within one
            page load and, importantly, so this function stays exactly
            unit-testable without mocking randomness.

    Returns:
        One message from `CLOSING_MESSAGES`.
    """
    return CLOSING_MESSAGES[seed % len(CLOSING_MESSAGES)]


def build_development_summary(
    recent_checkins: list[CheckInForSummary], total_checkin_count: int
) -> DevelopmentSummary:
    """Synthesise a plain-language pattern summary from recent check-ins.

    Args:
        recent_checkins: The most recent check-ins, **most-recent-first**,
            already truncated to at most `SUMMARY_WINDOW` entries by the
            caller (mirrors `adaptive_recovery.fetch_recent_history`'s own
            ordering convention).
        total_checkin_count: The student's total number of check-ins ever
            (may exceed `len(recent_checkins)`) -- used only to seed
            `_pick_closing_message` deterministically, not for any count
            shown to the student.

    Returns:
        The aggregated summary, ready to render verbatim.
    """
    n = len(recent_checkins)

    category_counts = Counter(
        c.top_category for c in recent_checkins if c.top_category is not None
    )
    most_frequent_label: str | None = None
    most_frequent_count = 0
    if category_counts:
        top_category, most_frequent_count = category_counts.most_common(1)[0]
        most_frequent_label = CATEGORY_LABELS.get(top_category, top_category)

    engaged_considered = sum(
        1 for c in recent_checkins if c.previous_engagement != "no_previous_checkin"
    )
    engaged_count = sum(1 for c in recent_checkins if c.previous_engagement == "yes")

    sentence_parts: list[str] = []
    if most_frequent_label is not None:
        sentence_parts.append(
            f"Over your last {n} check-in{'s' if n != 1 else ''}, "
            f"{most_frequent_label} has come up most often as a factor worth "
            "acting on."
        )
    if engaged_considered > 0:
        sentence_parts.append(
            f"You've engaged with {engaged_count} of your last "
            f"{engaged_considered} suggestion{'s' if engaged_considered != 1 else ''}."
        )
    if not sentence_parts:
        sentence_parts.append(
            "Keep checking in and this section will start showing patterns across your visits."
        )
    summary_sentence = " ".join(sentence_parts)

    closing_message = _pick_closing_message(total_checkin_count)

    validate_user_facing_text(summary_sentence)
    validate_user_facing_text(closing_message)

    return DevelopmentSummary(
        checkins_considered=n,
        most_frequent_factor_label=most_frequent_label,
        most_frequent_factor_count=most_frequent_count,
        engaged_count=engaged_count,
        engaged_considered=engaged_considered,
        summary_sentence=summary_sentence,
        closing_message=closing_message,
    )
