"""The plain-language explanation shown to a student, plus its audit trail.

`paragraph` is the only field that may be displayed. `faithfulness_factors`
retains the SHAP attribution the paragraph was derived from — feature, raw
value, signed severity contribution, direction — so the text can later be
audited against what actually drove the prediction.

This is the persistence side of the requirement in `IMPLEMENTATION_RULES.md`
that every human-readable explanation be traceable back to the SHAP values that
produced it, "in a debug/log field the user never sees".
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.assessment import JSONType


class ExplanationRecord(Base):
    """One generated explanation and the attribution behind it."""

    __tablename__ = "explanation_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Shown to the student.
    paragraph: Mapped[str] = mapped_column(Text, nullable=False)

    # Never shown. One entry per contributing factor:
    # {feature, feature_value, shap_value, direction, rank, phrase}
    faithfulness_factors: Mapped[list] = mapped_column(JSONType, nullable=False)

    # Share of total |severity| the explanation accounts for.
    coverage_ratio: Mapped[float] = mapped_column(Float, nullable=False)

    assessment: Mapped["Assessment"] = relationship(  # noqa: F821
        back_populates="explanation"
    )
