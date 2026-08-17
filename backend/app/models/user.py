"""User account. Holds the only direct identifiers in the schema."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class User(Base):
    """A registered student account.

    Direct identifiers (email) live only on this table. Assessment and
    wellbeing data are stored on separate tables keyed by `user_id`, per the
    anonymisation approach in `docs/governance/data_management_plan.md` — the
    surface where identity and sensitive data are directly joined is kept small.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    profile: Mapped["UserProfile | None"] = relationship(  # noqa: F821
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    assessments: Mapped[list["Assessment"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    chat_messages: Mapped[list["ChatMessage"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
