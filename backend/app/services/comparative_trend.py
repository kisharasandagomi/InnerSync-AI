"""Comparative trend message: how this check-in compares to the last one (round 3).

**Reuses, does not recompute, the Adaptive Recovery Framework's own history
data.** `determine_comparative_trend` takes the same
`Sequence[CheckInSummary]` `adaptive_recovery.fetch_recent_history` already
produces — `assessment_service.py` fetches history once and passes it to
both this module and `plan_with_adaptive_recovery`, per this session's
explicit instruction not to compute the same thing twice. See
`app.services.adaptive_recovery` for why that history-fetching logic lives
in `backend/`, not `ml_pipeline/` (same ADR-001 reasoning applies here).

**Escalation coordination.** By construction, escalation (three-or-more
consecutive check-ins at the highest severity class) can only fire when the
immediately previous check-in was *also* at the highest class — so the raw
ordinal comparison is always "same" whenever escalation fires. Rather than
lean on that as an implicit coincidence, `is_escalation` is an explicit
input here: when it is `True`, the message shown is always
`COMPARATIVE_ESCALATION_COORDINATED_MESSAGE`, a short, factual, secondary
note that adds no new emotionally-loaded framing of its own — the
escalation signpost (`adaptive_recovery.py`'s
`SUSTAINED_HIGH_STRESS_ESCALATION_MESSAGE`) is already carrying that weight,
and stacking a second heavy message on top of it is exactly what this
session's task asked to avoid. The true ordinal outcome is still computed
and logged either way, for audit — see `ComparativeTrendResult.outcome`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.services.adaptive_recovery import CheckInSummary
from ml_pipeline.src.explainability.generator import validate_user_facing_text

# Shown when this check-in's predicted class is lower (less severe) than the
# immediately previous one. Hedged, and deliberately avoids implying a
# precise measurement ("improved by X%") or overclaiming ("you're fixed") —
# same discipline as every other user-facing template in this system.
COMPARATIVE_IMPROVED_MESSAGE = (
    "Things seem to be feeling a bit lighter than your last check-in, and that's worth "
    "noticing, even if it's a small shift."
)

# Shown when the predicted class is unchanged from the immediately previous
# check-in. Deliberately brief and neutral, not forced positivity.
COMPARATIVE_SAME_MESSAGE = "This check-in looks fairly similar to your last one."

# Shown when the predicted class is higher (more severe) than the
# immediately previous one, and escalation is NOT also firing. Supportive,
# self-compassion-focused, explicitly not clinical or alarming.
COMPARATIVE_WORSE_MESSAGE = (
    "It looks like things have felt a bit harder since your last check-in. Be gentle "
    "with yourself: this is a snapshot, not a verdict."
)

# Shown instead of any of the three above whenever this check-in also
# triggers Adaptive Recovery's escalation — see module docstring for why a
# separate, quieter message is used rather than COMPARATIVE_WORSE_MESSAGE
# (which would duplicate the escalation signpost's own supportive framing).
COMPARATIVE_ESCALATION_COORDINATED_MESSAGE = (
    "This continues a pattern from your last few check-ins."
)


@dataclass(frozen=True)
class ComparativeTrendResult:
    """What to show, and what actually happened, for audit.

    Attributes:
        outcome: `"improved"`, `"same"`, `"worse"`, or `None` for a
            genuine first-ever check-in (nothing to compare against). This
            is always the *true* ordinal comparison, even when
            `is_escalation` changes which message is shown for it — see
            module docstring.
        message: The exact template text to show, or `None` if `outcome`
            is `None`.
    """

    outcome: str | None
    message: str | None


def determine_comparative_trend(
    current_predicted_class: int,
    history: Sequence[CheckInSummary],
    is_escalation: bool,
) -> ComparativeTrendResult:
    """Compare this check-in's severity to the immediately previous one.

    Args:
        current_predicted_class: This check-in's predicted class (0/1/2).
        history: Prior check-ins, most-recent-first — the same list
            `adaptive_recovery.fetch_recent_history` produces. Only
            `history[0]` (the immediately previous check-in) is used; older
            entries don't change a comparison against "last time".
        is_escalation: Whether Adaptive Recovery's escalation rule fired for
            this same check-in — see module docstring for the coordination
            this triggers.

    Returns:
        The outcome and the message to show, both safety-gate-checked
        already (except when `outcome` is `None`, since there is nothing to
        check).
    """
    if not history:
        return ComparativeTrendResult(outcome=None, message=None)

    previous_class = history[0].predicted_class

    if current_predicted_class < previous_class:
        outcome = "improved"
    elif current_predicted_class > previous_class:
        outcome = "worse"
    else:
        outcome = "same"

    if is_escalation:
        message = COMPARATIVE_ESCALATION_COORDINATED_MESSAGE
    elif outcome == "improved":
        message = COMPARATIVE_IMPROVED_MESSAGE
    elif outcome == "worse":
        message = COMPARATIVE_WORSE_MESSAGE
    else:
        message = COMPARATIVE_SAME_MESSAGE

    validate_user_facing_text(message)
    return ComparativeTrendResult(outcome=outcome, message=message)
