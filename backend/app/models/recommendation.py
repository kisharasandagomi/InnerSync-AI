"""Recommendations produced for one assessment — point-in-time or adaptive.

**Supersedes an earlier version of this docstring.** This table originally
stated that no engagement fields existed and that the Adaptive Recovery
Framework (Module 8 Component 5) was not built. Both are now out of date, in
the same way other superseded claims in this project have been corrected
rather than left stale (see `docs/decisions/ADR.md`).

`is_escalation` / `escalation_message` and `adaptive_recovery_reason` are new.
`adaptive_recovery_applied` is no longer a constant `False` — it now reflects
whether `backend/app/services/adaptive_recovery.py` actually altered this
check-in's recommendation or triggered escalation, computed from the
student's own assessment history plus the `previous_engagement` value on
`Assessment`. See that module's docstring for why the decision logic lives in
`backend/`, not `ml_pipeline/`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.assessment import JSONType


class Recommendation(Base):
    """The ranked action list for one assessment, an affirmation, or an escalation."""

    __tablename__ = "recommendations"

    # Enforces that a row is at most one of: an affirmation, an escalation, or
    # a plan with real actions — never two at once. `json_array_length` is
    # SQLite's function name; it is what actually runs here, since
    # `Base.metadata.create_all()` against SQLite is the only thing that
    # builds this table from these Python declarations (see
    # tests/conftest.py — production schema comes from Alembic only, per
    # IMPLEMENTATION_RULES.md). The equivalent constraint against the
    # production Postgres schema is created directly in Alembic migration
    # 9b4f2d7c1a06 using `jsonb_array_length`, the same way `JSONType` above
    # already varies JSON vs JSONB by dialect rather than forcing one
    # dialect's syntax onto the other.
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN is_affirmation THEN 1 ELSE 0 END)"
            " + (CASE WHEN is_escalation THEN 1 ELSE 0 END)"
            " + (CASE WHEN json_array_length(actions) > 0 THEN 1 ELSE 0 END) <= 1",
            name="ck_recommendations_mutually_exclusive_output_mode",
        ),
    )

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

    # Ranked actions. Empty when `is_affirmation` or `is_escalation` is True.
    # One entry per action:
    # {priority, feature, category, title, action, rationale, severity_contribution}
    actions: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)

    # True when no factor was both raising and above the severity floor, so an
    # affirmation was returned rather than a forced action.
    is_affirmation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    affirmation_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # True when predicted stress has been at the highest severity level across
    # 3+ consecutive check-ins (regardless of engagement) and the normal
    # recommendation list was replaced with a wellbeing-service signpost.
    # Mutually exclusive with is_affirmation and with a non-empty `actions`.
    is_escalation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    escalation_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # True only when this check-in's recommendation was actually altered by
    # adaptive_recovery.py (a factor switch or an escalation) — not merely
    # because that code path ran. Most check-ins, including every first-ever
    # one, leave this False.
    adaptive_recovery_applied: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # Short, non-user-facing audit string, e.g. "factor_switch:study_load:streak=2"
    # or "sustained_high_severity:streak=3" — never shown to the student, kept
    # for the same faithfulness-auditing reason ExplanationRecord logs its
    # factors: IMPLEMENTATION_RULES.md requires automated decisions affecting a
    # student to be traceable after the fact.
    adaptive_recovery_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Round 3: comparative trend message (see
    # app/services/comparative_trend.py). `comparative_trend_outcome` is the
    # true ordinal comparison against the immediately previous check-in —
    # "improved" | "same" | "worse" — always logged for audit even when
    # escalation coordination changes which *message* is actually shown.
    # Both are None only for a genuine first-ever check-in, which has no
    # previous result to compare against.
    comparative_trend_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The exact template text shown to the student, verbatim — never shown
    # twice with different wording for the same outcome, since it is always
    # one of the fixed templates in comparative_trend.py.
    comparative_trend_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    assessment: Mapped["Assessment"] = relationship(  # noqa: F821
        back_populates="recommendation"
    )
