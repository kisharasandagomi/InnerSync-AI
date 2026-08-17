"""A single message in a student's ongoing wellbeing chat (Module 3).

**Hard boundary — read before touching this file.** Per `CLAUDE.md`: "the
chatbot does NOT perform stress prediction. Machine Learning models perform
stress prediction." Nothing in `app.chatbot` reads a column of this table
into `StressPredictor`, and nothing here changes `POST /assessments` or its
14-feature contract. This table is written and read entirely independently
of `Assessment`/`ExplanationRecord`/`Recommendation`. See
`docs/research/methodology.md` § Conversational Interaction Layer for why:
no dataset available to this project pairs structured questionnaire features
with free text from the same person, so a combined model stays documented
future work rather than something improvised here.

**No `Conversation`/session table.** Continuity is just chronological
`created_at` order per `user_id`; `app.chatbot.service` replays enough recent
history back to Gemini as context. A "session," for the per-session turn cap,
is inferred from a gap between consecutive timestamps rather than tracked as
a persisted field — see `app.chatbot.service`'s `SESSION_GAP` for the
reasoning. This keeps the schema to the one lightweight table the session's
scope asked for.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ChatMessage(Base):
    """One message: either the student's own text, or the AI companion's reply."""

    __tablename__ = "chat_messages"

    __table_args__ = (
        CheckConstraint("role in ('user','assistant')", name="ck_chat_messages_role"),
    )

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

    # "user" or "assistant". Plain String rather than a native Postgres ENUM —
    # same reasoning as Assessment.previous_engagement (see
    # docs/research/methodology.md § Adaptive Recovery Framework): avoids an
    # ALTER TYPE migration if a role is ever added. Validated at the Pydantic
    # schema layer for inbound data; the CHECK constraint above is the
    # database-level backstop for rows this table ever actually receives,
    # including the assistant's own persisted replies.
    role: Mapped[str] = mapped_column(String(16), nullable=False)

    # The text actually shown to the student. Always safe: either Gemini's
    # own output after it passed validate_user_facing_text(), or one of the
    # fixed canned fallbacks in app.chatbot.prompts. A rejected raw Gemini
    # draft is never written here or anywhere else — see
    # app.chatbot.service._get_validated_reply.
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # None for a genuine, validated Gemini reply (and always None for a
    # "user" row). Set on an "assistant" row only when `content` is a canned
    # fallback rather than Gemini's own output — one of
    # "safety_gate_rejected" (Gemini's draft failed validate_user_facing_text),
    # "gemini_rate_limited" (HTTP 429), or "gemini_unavailable" (any other
    # runtime failure of an otherwise-correctly-configured client). Mirrors
    # Recommendation.adaptive_recovery_reason: a short, non-user-facing audit
    # string kept so an automated substitution is traceable after the fact,
    # per IMPLEMENTATION_RULES.md.
    fallback_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)

    user: Mapped["User"] = relationship(back_populates="chat_messages")  # noqa: F821
