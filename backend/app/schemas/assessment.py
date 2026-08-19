"""Request/response schemas for the assessment endpoint.

The response deliberately exposes **no** SHAP value, feature name, numeric
weight, or ML terminology: per `.claude/skills/explainable-ai/SKILL.md` those
stay server-side. The attribution is persisted to `explanation_records` for
research audit, never returned to the caller.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Mirrors app.models.assessment.EngagementLevel's values. Kept as a Literal
# here (rather than importing the SQLAlchemy-adjacent enum into the schema
# layer) so this file has no dependency on the ORM module.
PreviousEngagement = Literal["yes", "partially", "no", "no_previous_checkin"]


class AssessmentCreateRequest(BaseModel):
    """The 14 questionnaire values plus one Adaptive Recovery Framework field.

    Bounds on the 14 features come from the schema's observed min/max per
    feature. `previous_engagement` asks, as part of this same submission
    (not a separate flow), whether the student engaged with their *previous*
    check-in's recommendations — the self-reported signal
    `app.services.adaptive_recovery` needs, since this system cannot observe
    real-world behaviour directly. `"no_previous_checkin"` covers a genuine
    first-ever assessment.
    """

    model_config = ConfigDict(extra="forbid")

    self_esteem: int = Field(ge=0, le=30)
    mental_health_history: int = Field(ge=0, le=1)
    headache: int = Field(ge=0, le=5)
    breathing_problem: int = Field(ge=0, le=5)
    noise_level: int = Field(ge=0, le=5)
    living_conditions: int = Field(ge=0, le=5)
    safety: int = Field(ge=0, le=5)
    basic_needs: int = Field(ge=0, le=5)
    academic_performance: int = Field(ge=0, le=5)
    study_load: int = Field(ge=0, le=5)
    teacher_student_relationship: int = Field(ge=0, le=5)
    social_support: int = Field(ge=0, le=3)
    peer_pressure: int = Field(ge=0, le=5)
    extracurricular_activities: int = Field(ge=0, le=5)

    previous_engagement: PreviousEngagement = Field(
        description=(
            "Engagement with the recommendations from the student's previous "
            "check-in. Use 'no_previous_checkin' if this is their first ever "
            "assessment."
        )
    )


class RecommendationItem(BaseModel):
    """One actionable suggestion."""

    priority: int
    title: str
    action: str
    rationale: str
    category: str


class AssessmentResponse(BaseModel):
    """What the caller receives: level, explanation, and next steps.

    `recommendations` is empty and `is_affirmation`/`is_escalation` are both
    False only when neither applies, which does not happen — every check-in
    is exactly one of: has recommendations, is an affirmation, or is an
    escalation.
    """

    model_config = ConfigDict(from_attributes=True)

    assessment_id: int
    created_at: datetime

    stress_level: int = Field(description="0 low, 1 moderate, 2 high")
    stress_level_label: str

    explanation: str = Field(description="Plain-language paragraph shown to the student")

    recommendations: list[RecommendationItem]
    is_affirmation: bool = Field(
        description="True when nothing warranted an action and an affirmation was returned"
    )
    affirmation: str | None = None

    is_escalation: bool = Field(
        default=False,
        description=(
            "True when sustained high stress across consecutive check-ins "
            "replaced the normal recommendations with a wellbeing-service "
            "signpost, regardless of engagement"
        ),
    )
    escalation_message: str | None = None

    comparative_trend_message: str | None = Field(
        default=None,
        description=(
            "A short message comparing this result to the student's immediately "
            "previous check-in, or null for a genuine first-ever check-in. When "
            "this check-in also triggers is_escalation, this is a brief, "
            "coordinated note rather than a second emotionally-loaded message — "
            "see docs/research/methodology.md § Comparative Trend Message."
        ),
    )


class AssessmentHistoryItem(BaseModel):
    """One past check-in, for the Progress Monitoring Dashboard's trend view.

    Deliberately carries no SHAP value, raw feature name, or numeric severity
    score. `top_factor_phrase` and `explanation` are both text the student
    already read at the time of that check-in, reused verbatim, not
    regenerated: `top_factor_phrase` is the same safety-gate-validated
    plain-language phrase used inside `AssessmentResponse.explanation` (see
    `ml_pipeline/src/explainability/templates.py`'s `FEATURE_PHRASES`) for
    that check-in's single strongest severity-axis factor, and `explanation`
    is that same check-in's full `ExplanationRecord.paragraph` — identical to
    what `AssessmentResponse.explanation` returned at submission time. The
    frontend shows `top_factor_phrase` as the one-line summary per entry and
    `explanation` behind an explicit expand action, never as a chart axis
    value.
    """

    model_config = ConfigDict(from_attributes=True)

    assessment_id: int
    created_at: datetime

    stress_level: int = Field(description="0 low, 1 moderate, 2 high")
    stress_level_label: str

    previous_engagement: PreviousEngagement
    adaptive_recovery_applied: bool = Field(
        description="Whether the Adaptive Recovery Framework altered this check-in's plan"
    )
    is_escalation: bool

    top_factor_phrase: str | None = Field(
        default=None,
        description=(
            "Plain-language phrase for the strongest contributing factor at "
            "this check-in, or null if none was recorded"
        ),
    )
    explanation: str = Field(
        description="This check-in's full plain-language explanation paragraph, verbatim"
    )

    # Round 6: the Progress page's expandable entries previously showed only
    # `explanation`, even though the ranked actions / affirmation / escalation
    # text for every past check-in already exists in the `recommendations`
    # table. Same reuse discipline as `explanation` and `top_factor_phrase`
    # above -- these are that check-in's exact, already safety-gated text,
    # never regenerated.
    recommendations: list[RecommendationItem] = Field(
        default_factory=list,
        description="This check-in's ranked actions, verbatim. Empty for an affirmation or escalation.",
    )
    is_affirmation: bool = Field(
        default=False,
        description="True when this check-in's plan was an affirmation rather than actions",
    )
    affirmation: str | None = Field(
        default=None, description="This check-in's affirmation text, verbatim, if any"
    )
    escalation_message: str | None = Field(
        default=None,
        description="This check-in's wellbeing-service signpost text, verbatim, if is_escalation",
    )
