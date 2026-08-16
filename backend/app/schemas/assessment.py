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
