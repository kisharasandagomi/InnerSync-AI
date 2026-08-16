"""Selects and ranks a small number of recommendations from SHAP severity contributions.

**Scope boundary — read before extending this module.**

This component produces a recommendation for a **single point-in-time
assessment** only. It has no memory, no notion of a previous check-in, and no
engagement signal — nothing here changed to support the Adaptive Recovery
Framework.

The Adaptive Recovery Framework (Module 8 Component 5) — changing strategy when
recommendations are repeatedly ignored across consecutive check-ins, and
escalating toward university wellbeing services under sustained high stress —
is now implemented, in `backend/app/services/adaptive_recovery.py`, not here.
It needs to query live, per-user assessment history from the production
database, which this research-world module structurally cannot depend on (see
ADR-001; `ml_pipeline/` must never import from `backend/`). It does reuse this
module's catalogue directly — `ml_pipeline.src.recommendation.catalogue` now
carries a primary and an alternate template per feature specifically so the
adaptive component has something to switch to — so recommendation content and
the vocabulary-safety guarantee stay identical between the point-in-time and
adaptive paths rather than being duplicated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from ..explainability.generator import ExplanationFactor, validate_user_facing_text
from .catalogue import AFFIRMATION_BY_CLASS, RECOMMENDATION_CATALOGUE, RecommendationTemplate

# Minimum severity contribution before a factor earns a recommendation.
#
# Derivation: the 25th percentile of |severity| across the full held-out test
# set (220 students x 14 features = 3,080 attributions), computed in
# 07_RecommendationEngine.ipynb. p25 = 0.0200. The quartile is the choice being
# made here; the round number is a coincidence of this dataset, not the reason
# for the value.
#
# IMPORTANT — this threshold does not currently bind. Across the same test set
# there are 430 raising factors inside the top-4 selection, and none falls below
# 0.0200; the smallest |severity| among all top-4 factors is 0.0346. It is
# therefore a **guard rail for out-of-distribution input**, not an active filter
# on this data: it exists so that a student whose attributions are uniformly
# tiny (a profile unlike anything in this dataset, or a future model with
# flatter attributions) receives an affirmation rather than an action built on
# noise.
#
# Consequence worth being precise about: the affirmation path observed for the
# low-stress case is triggered by that student having no raising factors at all,
# NOT by this floor. Raising the value until it visibly binds would be tuning a
# parameter to look useful, which is why it is left at the empirical quartile.
SEVERITY_PERCENTILE_BASIS = 25
MIN_SEVERITY_FOR_ACTION = 0.0200

# Hard ceiling on plan size. Three actions is already a lot to receive at once;
# more reads as a to-do list and reliably gets ignored, which would also corrupt
# the engagement signal the adaptive component will later depend on.
MAX_RECOMMENDATIONS = 3


@dataclass(frozen=True)
class Recommendation:
    """One prioritized, actionable suggestion for a student."""

    priority: int
    feature: str
    category: str
    title: str
    action: str
    rationale: str
    severity_contribution: float


@dataclass
class RecommendationPlan:
    """The full set of suggestions for one assessment, or an affirmation instead.

    Only `recommendations` / `affirmation` are shown to a student; the
    faithfulness record is retained for research evaluation.
    """

    predicted_class: int
    recommendations: list[Recommendation]
    affirmation: str | None = None
    faithfulness_record: dict = field(default_factory=dict)

    @property
    def has_actions(self) -> bool:
        """Whether this plan contains any action items."""
        return bool(self.recommendations)

    def user_facing_lines(self) -> list[str]:
        """Return the display text: either the affirmation, or the action list."""
        if not self.has_actions:
            return [self.affirmation or ""]
        return [f"{r.title}: {r.action}" for r in self.recommendations]


def build_recommendation_plan(
    factors: Sequence[ExplanationFactor],
    predicted_class: int,
    max_recommendations: int = MAX_RECOMMENDATIONS,
    min_severity: float = MIN_SEVERITY_FOR_ACTION,
    context: dict | None = None,
) -> RecommendationPlan:
    """Turn the explanation's contributing factors into a short, ranked plan.

    Takes the same `ExplanationFactor` list the explanation paragraph was built
    from, so the two outputs always describe the same attribution — a student
    never reads about one set of pressures and then receives advice about a
    different set.

    Selection rules:
      1. Only "raising" factors qualify. A protective factor needs no fixing.
      2. A factor must exceed `min_severity` to earn an action.
      3. Rank by severity magnitude, strongest first.
      4. Cap at `max_recommendations`.
      5. If nothing qualifies, return an affirmation rather than a forced action.

    Args:
        factors: Output of `extract_top_factors`, already severity-ranked.
        predicted_class: 0 (low), 1 (moderate) or 2 (high).
        max_recommendations: Ceiling on plan size.
        min_severity: Minimum severity contribution to warrant an action.
        context: Optional metadata for the faithfulness record; never shown.

    Returns:
        A `RecommendationPlan`, possibly with zero recommendations.

    Raises:
        ValueError: If `predicted_class` is unknown or a factor has no catalogue
            entry.
        ExplanationSafetyError: If any generated text fails the vocabulary gate.
    """
    if predicted_class not in AFFIRMATION_BY_CLASS:
        raise ValueError(f"Unknown predicted_class {predicted_class!r}; expected 0, 1 or 2")

    qualifying = [
        f
        for f in factors
        if f.direction == "raising" and abs(f.shap_value) >= min_severity
    ]
    qualifying.sort(key=lambda f: abs(f.shap_value), reverse=True)
    selected = qualifying[:max_recommendations]

    missing = [f.feature for f in selected if f.feature not in RECOMMENDATION_CATALOGUE]
    if missing:
        raise ValueError(f"No recommendation defined for: {missing}")

    recommendations: list[Recommendation] = []
    for priority, factor in enumerate(selected, start=1):
        # [0] = primary template. The point-in-time engine never uses the
        # alternate at [1] — that exists only for the Adaptive Recovery
        # Framework (backend/app/services/adaptive_recovery.py).
        template: RecommendationTemplate = RECOMMENDATION_CATALOGUE[factor.feature][0]
        validate_user_facing_text(f"{template.title} {template.action} {template.rationale}")
        recommendations.append(
            Recommendation(
                priority=priority,
                feature=factor.feature,
                category=template.category,
                title=template.title,
                action=template.action,
                rationale=template.rationale,
                severity_contribution=float(factor.shap_value),
            )
        )

    affirmation = None
    if not recommendations:
        affirmation = AFFIRMATION_BY_CLASS[predicted_class]
        validate_user_facing_text(affirmation)

    record = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "component": "recommendation_engine",
        "scope": "single point-in-time assessment; no engagement history used",
        "adaptive_recovery_applied": False,
        "predicted_class": int(predicted_class),
        "selection_rules": {
            "min_severity_for_action": min_severity,
            "max_recommendations": max_recommendations,
            "raising_factors_only": True,
        },
        "candidate_factors": [
            {
                "feature": f.feature,
                "severity_contribution": f.shap_value,
                "direction": f.direction,
                "qualified": f in selected,
            }
            for f in factors
        ],
        "recommendations": [asdict(r) for r in recommendations],
        "affirmation_used": affirmation is not None,
    }
    if context:
        record["context"] = context

    return RecommendationPlan(
        predicted_class=int(predicted_class),
        recommendations=recommendations,
        affirmation=affirmation,
        faithfulness_record=record,
    )
