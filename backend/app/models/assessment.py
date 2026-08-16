"""A single point-in-time stress assessment: raw inputs plus model output.

The 14 feature columns mirror `ml_pipeline/artifacts/feature_schema.json`
(model v2) exactly, in schema order. Storing them as explicit columns rather
than a JSON blob keeps them queryable for the Phase 8 external-validation
analysis, and makes a schema drift between model and database a migration
failure rather than a silent mismatch.

`sleep_quality`, `future_career_concerns`, `blood_pressure`, `depression`,
`bullying` and `anxiety_level` are intentionally absent: they were excluded
from the model as leaking the target label (ADR-003).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.base import Base

# JSONB on PostgreSQL, plain JSON elsewhere (e.g. SQLite in tests).
JSONType = JSON().with_variant(JSONB(), "postgresql")


class Assessment(Base):
    """One completed questionnaire and the prediction derived from it."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    # --- the 14 model input features, in feature_schema.json order ---
    self_esteem: Mapped[int] = mapped_column(Integer, nullable=False)
    mental_health_history: Mapped[int] = mapped_column(Integer, nullable=False)
    headache: Mapped[int] = mapped_column(Integer, nullable=False)
    breathing_problem: Mapped[int] = mapped_column(Integer, nullable=False)
    noise_level: Mapped[int] = mapped_column(Integer, nullable=False)
    living_conditions: Mapped[int] = mapped_column(Integer, nullable=False)
    safety: Mapped[int] = mapped_column(Integer, nullable=False)
    basic_needs: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_performance: Mapped[int] = mapped_column(Integer, nullable=False)
    study_load: Mapped[int] = mapped_column(Integer, nullable=False)
    teacher_student_relationship: Mapped[int] = mapped_column(Integer, nullable=False)
    social_support: Mapped[int] = mapped_column(Integer, nullable=False)
    peer_pressure: Mapped[int] = mapped_column(Integer, nullable=False)
    extracurricular_activities: Mapped[int] = mapped_column(Integer, nullable=False)

    # --- model output ---
    predicted_class: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_probabilities: Mapped[dict] = mapped_column(JSONType, nullable=False)
    model_version: Mapped[str] = mapped_column(String(16), nullable=False)

    user: Mapped["User"] = relationship(back_populates="assessments")  # noqa: F821
    explanation: Mapped["ExplanationRecord | None"] = relationship(  # noqa: F821
        back_populates="assessment", uselist=False, cascade="all, delete-orphan"
    )
    recommendation: Mapped["Recommendation | None"] = relationship(  # noqa: F821
        back_populates="assessment", uselist=False, cascade="all, delete-orphan"
    )
