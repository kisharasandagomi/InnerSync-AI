"""Personalized Recommendation Engine — maps SHAP severity contributions to actions.

Rule-based and deterministic, driven by the same contributing factors the
explanation paragraph was built from, so explanation and advice always describe
the same attribution.

Scope: single point-in-time assessment only. The Adaptive Recovery Framework
(Component 5) is not implemented here — see `engine` module docstring.
"""

from .catalogue import (
    AFFIRMATION_BY_CLASS,
    RECOMMENDATION_CATALOGUE,
    RecommendationTemplate,
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
    "RecommendationTemplate",
    "MAX_RECOMMENDATIONS",
    "MIN_SEVERITY_FOR_ACTION",
    "SEVERITY_PERCENTILE_BASIS",
    "Recommendation",
    "RecommendationPlan",
    "build_recommendation_plan",
]
