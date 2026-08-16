"""Recommendations produced for one assessment, or the affirmation used instead.

Scope: **single point-in-time output only.** There are deliberately no
engagement fields here — no `was_acted_on`, no `dismissed_at`, no
`times_shown`. Those belong to the Adaptive Recovery Framework (Module 8
Component 5), which is not built: it needs engagement history across multiple
check-ins, and adding speculative columns now would imply a capability the
system does not have.

`adaptive_recovery_applied` is stored as a constant False so that, once the
adaptive component does exist, historical rows are unambiguously identifiable
as pre-adaptive rather than as adaptive runs that happened to change nothing.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.assessment import JSONType


class Recommendation(Base):
    """The ranked action list for one assessment, or an affirmation."""

    __tablename__ = "recommendations"

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

    # Ranked actions. Empty list when `is_affirmation` is True.
    # One entry per action:
    # {priority, feature, category, title, action, rationale, severity_contribution}
    actions: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)

    # True when no factor was both raising and above the severity floor, so an
    # affirmation was returned rather than a forced action.
    is_affirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    affirmation_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Always False until Component 5 exists. See module docstring.
    adaptive_recovery_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    assessment: Mapped["Assessment"] = relationship(  # noqa: F821
        back_populates="recommendation"
    )
