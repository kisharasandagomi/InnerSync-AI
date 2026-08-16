"""Personalized Recommendation Engine — maps SHAP severity contributions to actions.

Rule-based and deterministic, driven by the same contributing factors the
explanation paragraph was built from, so explanation and advice always describe
the same attribution.

Scope: this package (point-in-time selection + the shared catalogue) has no
notion of a previous check-in. The Adaptive Recovery Framework (Component 5)
is implemented in `backend/app/services/adaptive_recovery.py`, which reuses
`RECOMMENDATION_CATALOGUE`'s alternate templates and
`SUSTAINED_HIGH_STRESS_ESCALATION_MESSAGE` from this package — see `engine`
and `catalogue` module docstrings for why it lives there and not here.
"""

from .catalogue import (
    AFFIRMATION_BY_CLASS,
    RECOMMENDATION_CATALOGUE,
    SUSTAINED_HIGH_STRESS_ESCALATION_MESSAGE,
    RecommendationTemplate,
    get_alternate_template,
)
from .engine import (
    MAX_RECOMMENDATIONS,
    MIN_SEVERITY_FOR_ACTION,
    SEVERITY_PERCENTILE_BASIS,
    Recommendation,
    RecommendationPlan,
    build_recommendation_plan,
)

__all__ = [
    "AFFIRMATION_BY_CLASS",
    "RECOMMENDATION_CATALOGUE",
    "SUSTAINED_HIGH_STRESS_ESCALATION_MESSAGE",
    "RecommendationTemplate",
    "get_alternate_template",
    "MAX_RECOMMENDATIONS",
    "MIN_SEVERITY_FOR_ACTION",
    "SEVERITY_PERCENTILE_BASIS",
    "Recommendation",
    "RecommendationPlan",
    "build_recommendation_plan",
]
