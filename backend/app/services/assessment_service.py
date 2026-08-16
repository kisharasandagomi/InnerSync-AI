"""Runs the full pipeline for one assessment and persists the result.

This is the first place predict -> explain -> recommend runs end-to-end as a
live request rather than in a notebook. The explanation and recommendation
logic is **imported** from `ml_pipeline/src/`, not reimplemented, so the API
cannot drift from the version evaluated in notebooks 06 and 07.

Since this session, the point-in-time recommendation plan is additionally
passed through the Adaptive Recovery Framework
(`app.services.adaptive_recovery`), which may swap one recommendation or
replace the whole plan with an escalation, based on the caller's own prior
check-ins. See that module's docstring for the full logic and its ADR-001
justification.
"""

from __future__ import annotations

from dataclasses import asdict

from sqlalchemy.orm import Session

from app.ml.predictor import StressPredictor
from app.models.assessment import Assessment
from app.models.explanation_record import ExplanationRecord
from app.models.recommendation import Recommendation
from app.services.adaptive_recovery import plan_with_adaptive_recovery
from ml_pipeline.src.explainability import generate_explanation
from ml_pipeline.src.recommendation import build_recommendation_plan


def create_assessment(
    db: Session,
    user_id: int,
    feature_values: dict[str, int],
    previous_engagement: str,
    predictor: StressPredictor,
) -> tuple[Assessment, ExplanationRecord, Recommendation]:
    """Predict, explain, recommend, adapt, and persist — as one transaction.

    Args:
        db: Open database session.
        user_id: Owner of the assessment.
        feature_values: The 14 questionnaire values, keyed by feature name.
        previous_engagement: Self-reported engagement with the previous
            check-in's recommendations; one of `EngagementLevel`'s values.
        predictor: Loaded model wrapper.

    Returns:
        The persisted `(assessment, explanation_record, recommendation)` rows.

    Raises:
        ValueError: If a required feature is missing.
    """
    missing = [f for f in predictor.feature_order if f not in feature_values]
    if missing:
        raise ValueError(f"Missing required features: {missing}")

    # Order matters: the model is positional.
    ordered_values = [feature_values[name] for name in predictor.feature_order]
    prediction = predictor.predict(ordered_values)

    explanation = generate_explanation(
        shap_values=prediction["severity"],
        feature_values=ordered_values,
        feature_names=predictor.feature_order,
        predicted_class=prediction["predicted_class"],
        top_n=4,
        context={"user_id": user_id, "model_version": prediction["model_version"]},
    )
    base_plan = build_recommendation_plan(
        factors=explanation.factors,
        predicted_class=prediction["predicted_class"],
        context={"user_id": user_id, "model_version": prediction["model_version"]},
    )

    # Adaptive Recovery Framework: may swap one recommendation or replace the
    # whole plan with an escalation, based on this user's own prior check-ins.
    # Runs before the current Assessment row is added below, so its internal
    # history query cannot see the row being created right now.
    adapted = plan_with_adaptive_recovery(
        db=db,
        user_id=user_id,
        current_predicted_class=prediction["predicted_class"],
        base_plan=base_plan,
        previous_engagement=previous_engagement,
    )

    assessment = Assessment(
        user_id=user_id,
        predicted_class=prediction["predicted_class"],
        predicted_probabilities=prediction["probabilities"],
        model_version=prediction["model_version"],
        previous_engagement=previous_engagement,
        **{name: int(feature_values[name]) for name in predictor.feature_order},
    )
    db.add(assessment)
    db.flush()  # assign assessment.id without committing

    record = ExplanationRecord(
        assessment_id=assessment.id,
        paragraph=explanation.paragraph,
        faithfulness_factors=[asdict(f) for f in explanation.factors],
        coverage_ratio=float(explanation.faithfulness_record["coverage_ratio"]),
    )
    recommendation = Recommendation(
        assessment_id=assessment.id,
        actions=[asdict(r) for r in adapted.recommendations],
        is_affirmation=adapted.is_affirmation,
        affirmation_text=adapted.affirmation_text,
        is_escalation=adapted.is_escalation,
        escalation_message=adapted.escalation_message,
        adaptive_recovery_applied=adapted.adaptive_recovery_applied,
        adaptive_recovery_reason=adapted.adaptive_recovery_reason,
    )
    db.add(record)
    db.add(recommendation)
    db.commit()
    db.refresh(assessment)
    db.refresh(record)
    db.refresh(recommendation)

    return assessment, record, recommendation
