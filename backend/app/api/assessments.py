"""The core endpoint: submit a questionnaire, get a level, explanation and plan.

Also carries the read-only history endpoint behind the Progress Monitoring
Dashboard (Module 9/10) — no new write logic, it only reads back what
`POST /assessments` already persisted.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_model
from app.database.session import get_db
from app.ml.predictor import StressPredictor
from app.models.assessment import Assessment
from app.models.explanation_record import ExplanationRecord
from app.models.recommendation import Recommendation
from app.models.user import User
from app.schemas.assessment import (
    AssessmentCreateRequest,
    AssessmentHistoryItem,
    AssessmentResponse,
    DevelopmentSummaryResponse,
    EscalationStatusResponse,
    RecommendationItem,
)
from app.services.assessment_service import create_assessment
from app.services.development_summary import (
    SUMMARY_WINDOW,
    CheckInForSummary,
    build_development_summary,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])


def _fetch_history_rows(db: Session, user_id: int):
    """The join every read of a caller's own check-in history needs.

    Shared by `get_assessment_history` and `get_development_summary` so the
    two endpoints query the same rows once each, rather than each endpoint
    re-deriving its own version of "this user's check-ins with their
    recommendation and explanation" -- the same don't-compute-it-twice
    discipline `app.services.comparative_trend`'s module docstring already
    applies to history-fetching within one request.

    Args:
        db: Database session.
        user_id: Whose rows to fetch.

    Returns:
        `(Assessment, Recommendation, ExplanationRecord)` tuples, oldest first.
    """
    return (
        db.query(Assessment, Recommendation, ExplanationRecord)
        .join(Recommendation, Recommendation.assessment_id == Assessment.id)
        .join(ExplanationRecord, ExplanationRecord.assessment_id == Assessment.id)
        .filter(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.asc())
        .all()
    )


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
        comparative_trend_message=recommendation.comparative_trend_message,
    )


@router.get("/history", response_model=list[AssessmentHistoryItem])
def get_assessment_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    predictor: StressPredictor = Depends(get_model),
) -> list[AssessmentHistoryItem]:
    """Return the authenticated caller's own past check-ins, oldest first.

    Read-only: runs no prediction, explanation, or recommendation logic —
    it reads back rows `POST /assessments` already persisted. Powers the
    Progress Monitoring Dashboard's trend view. Carries no SHAP value, raw
    feature name, or numeric severity score, matching the vocabulary
    discipline every other student-facing response follows.

    Args:
        db: Database session.
        current_user: Authenticated caller — history is scoped to their own
            rows only; this never reads another user's assessments.
        predictor: Loaded model wrapper, for the class-label mapping.

    Returns:
        The caller's own assessments, ordered oldest to newest.
    """
    rows = _fetch_history_rows(db, current_user.id)

    history: list[AssessmentHistoryItem] = []
    for assessment, recommendation, explanation in rows:
        top_factor_phrase = (
            explanation.faithfulness_factors[0]["phrase"]
            if explanation.faithfulness_factors
            else None
        )
        history.append(
            AssessmentHistoryItem(
                assessment_id=assessment.id,
                created_at=assessment.created_at,
                stress_level=assessment.predicted_class,
                stress_level_label=predictor.class_meaning[str(assessment.predicted_class)],
                previous_engagement=assessment.previous_engagement,
                adaptive_recovery_applied=recommendation.adaptive_recovery_applied,
                is_escalation=recommendation.is_escalation,
                comparative_trend_outcome=recommendation.comparative_trend_outcome,
                top_factor_phrase=top_factor_phrase,
                explanation=explanation.paragraph,
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
                escalation_message=recommendation.escalation_message,
            )
        )
    return history


@router.get("/summary", response_model=DevelopmentSummaryResponse)
def get_development_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DevelopmentSummaryResponse:
    """Aggregated, plain-language pattern summary across recent check-ins (round 7).

    Read-only, and reuses the same rows `get_assessment_history` reads
    (`_fetch_history_rows`) rather than issuing a second query -- see that
    helper's docstring. Powers the Progress page's development-summary
    section; the existing trend graph and check-in list are unaffected.

    Args:
        db: Database session.
        current_user: Authenticated caller — scoped to their own rows only.

    Returns:
        A synthesised, safety-gate-validated summary of the caller's most
        recent check-ins (see `app.services.development_summary`).
    """
    rows = _fetch_history_rows(db, current_user.id)
    # Most-recent-first, truncated to the summary window -- the same
    # ordering convention `adaptive_recovery.fetch_recent_history` uses.
    recent = list(reversed(rows))[:SUMMARY_WINDOW]

    checkins = [
        CheckInForSummary(
            previous_engagement=assessment.previous_engagement,
            top_category=recommendation.actions[0]["category"]
            if recommendation.actions
            else None,
        )
        for assessment, recommendation, _explanation in recent
    ]

    summary = build_development_summary(checkins, total_checkin_count=len(rows))

    return DevelopmentSummaryResponse(
        checkins_considered=summary.checkins_considered,
        most_frequent_factor_label=summary.most_frequent_factor_label,
        most_frequent_factor_count=summary.most_frequent_factor_count,
        engaged_count=summary.engaged_count,
        engaged_considered=summary.engaged_considered,
        summary_sentence=summary.summary_sentence,
        closing_message=summary.closing_message,
    )


@router.get("/escalation-status", response_model=EscalationStatusResponse)
def get_escalation_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EscalationStatusResponse:
    """Whether the caller's most recent check-in is a sustained-high-stress escalation.

    Powers the profile page's persistent wellbeing signpost (round 7). Reads
    the same already-computed `Recommendation.is_escalation` flag
    `get_assessment_history` already exposes -- no new severity calculation,
    per `docs/decisions/ADR.md` ADR-004. Reuses `_fetch_history_rows` rather
    than a lighter dedicated query so this endpoint can never disagree with
    `/history` about which check-in is "most recent" or what its escalation
    status was.

    Args:
        db: Database session.
        current_user: Authenticated caller — scoped to their own rows only.

    Returns:
        `is_escalation=False` if the caller has no check-ins yet, otherwise
        the most recent check-in's own `is_escalation` value.
    """
    rows = _fetch_history_rows(db, current_user.id)
    if not rows:
        return EscalationStatusResponse(is_escalation=False)

    _assessment, most_recent_recommendation, _explanation = rows[-1]
    return EscalationStatusResponse(is_escalation=most_recent_recommendation.is_escalation)
