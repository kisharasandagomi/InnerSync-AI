"""Human-Centered Explanation Generator — turns SHAP output into language a student can read.

Nothing in this package may emit a SHAP value, a feature name, a numeric
weight, or any ML terminology into user-facing text. See
`.claude/skills/explainable-ai/SKILL.md` and `IMPLEMENTATION_RULES.md`.
"""

from .generator import (
    ExplanationFactor,
    StressExplanation,
    assemble_explanation_paragraph,
    extract_top_factors,
    generate_explanation,
    severity_contributions,
    validate_user_facing_text,
)

__all__ = [
    "ExplanationFactor",
    "StressExplanation",
    "assemble_explanation_paragraph",
    "extract_top_factors",
    "generate_explanation",
    "severity_contributions",
    "validate_user_facing_text",
]
