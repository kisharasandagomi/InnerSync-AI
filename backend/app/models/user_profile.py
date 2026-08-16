"""Optional demographic context for a user.

Deliberately minimal. These fields are **not** model inputs — the v2 model uses
14 questionnaire features and no demographics (see `feature_schema.json`). They
exist solely to enable the subgroup fairness analysis that
`docs/governance/model_card.md` records as impossible on the benchmark dataset,
which contains no demographic fields at all.

All fields are nullable: collection is opt-in per `ethical_framework.md`, and a
student may complete assessments without supplying any of this.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class UserProfile(Base):
    """Self-reported demographic context, used only for fairness evaluation."""

    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )

    # Banded rather than exact, to reduce re-identification risk in a
    # single-institution sample.
    age_group: Mapped[str | None] = mapped_column(String(16), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    degree_field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    year_of_study: Mapped[str | None] = mapped_column(String(16), nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")  # noqa: F821
