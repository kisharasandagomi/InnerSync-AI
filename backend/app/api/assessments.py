"""The core endpoint: submit a questionnaire, get a level, explanation and plan."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_model
from app.database.session import get_db
from app.ml.predictor import StressPredictor
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreateRequest,
    AssessmentResponse,
    RecommendationItem,
)
from app.services.assessment_service import create_assessment

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def submit_assessment(
    payload: AssessmentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    predictor: StressPredictor = Depends(get_model),
) -> AssessmentResponse:
    """Run predict -> explain -> recommend -> adapt for one questionnaire and persist it.

    Args:
        payload: The 14 questionnaire values plus self-reported engagement
            with the previous check-in's recommendations.
        db: Database session.
        current_user: Authenticated owner of the assessment.
        predictor: Loaded model wrapper.

    Returns:
        The stress level, plain-language explanation, and either recommended
        actions, an affirmation, or — if sustained high stress was detected
        across consecutive check-ins — an escalation message. No SHAP value,
        feature name or numeric weight is included — the attribution is
        persisted server-side for audit only.
    """
    payload_dict = payload.model_dump()
    previous_engagement = payload_dict.pop("previous_engagement")

    assessment, record, recommendation = create_assessment(
        db=db,
        user_id=current_user.id,
        feature_values=payload_dict,
        previous_engagement=previous_engagement,
        predictor=predictor,
    )

    return AssessmentResponse(
        assessment_id=assessment.id,
        created_at=assessment.created_at,
        stress_level=assessment.predicted_class,
        stress_level_label=predictor.class_meaning[str(assessment.predicted_class)],
        explanation=record.paragraph,
        recommendations=[
            RecommendationItem(
                priority=a["priority"],
                title=a["title"],
                action=a["action"],
                rationale=a["rationale"],
                category=a["category"],
            )
            for a in recommendation.actions
        ],
        is_affirmation=recommendation.is_affirmation,
        affirmation=recommendation.affirmation_text,
        is_escalation=recommendation.is_escalation,
        escalation_message=recommendation.escalation_message,
    )
