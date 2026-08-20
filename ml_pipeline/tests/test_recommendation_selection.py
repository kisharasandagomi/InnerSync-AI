"""Core recommendation selection logic: `build_recommendation_plan()`.

See `ml_pipeline/src/recommendation/engine.py` -- the pure, point-in-time
selection function (not the backend's Adaptive Recovery Framework wrapper,
which lives in `backend/app/services/adaptive_recovery.py` and is out of
scope here).
"""

from __future__ import annotations

import pytest

from ml_pipeline.src.explainability.generator import ExplanationFactor
from ml_pipeline.src.recommendation.catalogue import AFFIRMATION_BY_CLASS, RECOMMENDATION_CATALOGUE
from ml_pipeline.src.recommendation.engine import (
    MIN_SEVERITY_FOR_ACTION,
    build_recommendation_plan,
)


def _factor(feature: str, shap_value: float, rank: int = 1) -> ExplanationFactor:
    return ExplanationFactor(
        feature=feature,
        feature_value=1.0,
        shap_value=shap_value,
        direction="raising" if shap_value > 0 else "easing",
        rank=rank,
        phrase=f"{feature} placeholder phrase",
    )


def test_correct_template_picked_for_the_dominant_factor() -> None:
    factors = [_factor("study_load", 0.10)]

    plan = build_recommendation_plan(factors, predicted_class=2)

    assert len(plan.recommendations) == 1
    expected = RECOMMENDATION_CATALOGUE["study_load"][0]
    rec = plan.recommendations[0]
    assert rec.title == expected.title
    assert rec.action == expected.action
    assert rec.category == expected.category
    assert rec.feature == "study_load"


def test_ranks_multiple_raising_factors_by_severity_magnitude() -> None:
    factors = [
        _factor("study_load", 0.05),
        _factor("social_support", 0.15),
        _factor("basic_needs", 0.10),
    ]

    plan = build_recommendation_plan(factors, predicted_class=2)

    assert [r.feature for r in plan.recommendations] == [
        "social_support",
        "basic_needs",
        "study_load",
    ]
    assert [r.priority for r in plan.recommendations] == [1, 2, 3]


def test_easing_factors_are_never_recommended_even_if_large() -> None:
    factors = [_factor("safety", -0.50)]  # strongly protective, not raising

    plan = build_recommendation_plan(factors, predicted_class=0)

    assert plan.recommendations == []
    assert plan.affirmation == AFFIRMATION_BY_CLASS[0]


def test_factor_below_severity_floor_is_excluded_and_yields_an_affirmation() -> None:
    below_floor = MIN_SEVERITY_FOR_ACTION - 0.001
    factors = [_factor("noise_level", below_floor)]

    plan = build_recommendation_plan(factors, predicted_class=1)

    assert plan.recommendations == []
    assert plan.affirmation == AFFIRMATION_BY_CLASS[1]


def test_caps_at_max_recommendations() -> None:
    factors = [
        _factor("study_load", 0.40),
        _factor("social_support", 0.35),
        _factor("basic_needs", 0.30),
        _factor("peer_pressure", 0.25),
    ]

    plan = build_recommendation_plan(factors, predicted_class=2, max_recommendations=3)

    assert len(plan.recommendations) == 3
    assert [r.feature for r in plan.recommendations] == [
        "study_load",
        "social_support",
        "basic_needs",
    ]


def test_hobby_personalisation_used_when_safe() -> None:
    factors = [_factor("mental_health_history", 0.10)]

    plan = build_recommendation_plan(factors, predicted_class=2, hobby="painting")

    generic = RECOMMENDATION_CATALOGUE["mental_health_history"][0].action
    assert plan.recommendations[0].action != generic
    assert "painting" in plan.recommendations[0].action


def test_falls_back_to_generic_action_when_hobby_text_fails_the_safety_gate() -> None:
    """A hobby value that happens to embed forbidden vocabulary must not
    reach the student -- the interpolated text fails validate_user_facing_text
    internally, and the generic, catalogue-reviewed action is used instead."""
    factors = [_factor("mental_health_history", 0.10)]

    plan = build_recommendation_plan(factors, predicted_class=2, hobby="model training")

    generic = RECOMMENDATION_CATALOGUE["mental_health_history"][0].action
    assert plan.recommendations[0].action == generic
    assert "training" not in plan.recommendations[0].action


def test_unknown_predicted_class_raises() -> None:
    with pytest.raises(ValueError, match="Unknown predicted_class"):
        build_recommendation_plan([_factor("study_load", 0.10)], predicted_class=5)
