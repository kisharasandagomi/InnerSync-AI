"""Orchestrates one chat turn: history in, Gemini call, safety gate, persistence.

**Hard boundary — restated here, not just in `app/models/chat_message.py`,
because it is the easiest rule in this file to violate by accident while
wiring "send a message, get a reply".** This module never calls
`StressPredictor.predict()`, never imports `app.ml.predictor`, never touches
`app.models.assessment.Assessment`, and never changes `POST /assessments` or
its 14-feature contract. Chat messages are persisted to `chat_messages` only.
See `CLAUDE.md`'s Module 3 section and `docs/research/methodology.md` §
Conversational Interaction Layer: no dataset available to this project pairs
structured questionnaire features with free text from the same person (§ NLP
Feature Ablation Study, Experiments C/D), so a combined model is documented
future work, not something to improvise here as a shortcut.

**Every Gemini failure mode gets exactly one of two treatments, decided
once, never retried indefinitely:**
- A **configuration** problem (`GEMINI_API_KEY` missing, or Gemini rejects it
  as invalid/revoked) propagates as `ChatConfigError`, uncaught here, so the
  API layer can return a clear 503 — this must never be papered over with a
  canned reply, per `CLAUDE.md`.
- A **runtime** failure of an otherwise-correctly-configured client (HTTP
  429, a transient server error, an empty response) or a reply that fails
  `validate_user_facing_text()` is caught here and replaced with one of the
  fixed canned replies in `app.chatbot.prompts`, persisted like a genuine
  reply so the conversation stays coherent, and tagged with
  `fallback_reason` for audit. No retry loop: one Gemini call per turn.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from google.genai import errors as genai_errors
from google.genai import types as genai_types
from sqlalchemy.orm import Session

from app.chatbot.gemini_client import ChatConfigError, get_gemini_client
from app.chatbot.prompts import (
    RATE_LIMIT_FALLBACK_REPLY,
    SAFETY_FALLBACK_REPLY,
    SESSION_CAP_MESSAGE,
    SYSTEM_PROMPT,
    UNAVAILABLE_FALLBACK_REPLY,
)
from app.chatbot.sentiment import log_message_sentiment
from app.core.config import get_settings
from app.models.chat_message import ChatMessage
from ml_pipeline.src.explainability.generator import ExplanationSafetyError, validate_user_facing_text

logger = logging.getLogger(__name__)

# How many of the most recent messages are replayed back to Gemini as
# conversation context. Bounded for cost/latency on the free tier, not a
# claim about how much context makes a "good" conversation.
MAX_HISTORY_MESSAGES = 20

# A "session" for the turn cap is inferred from a gap between consecutive
# messages rather than tracked as a persisted field — see
# app/models/chat_message.py's module docstring for why no separate
# Conversation/session table exists. Three hours is long enough that a
# same-sitting conversation is never split, and short enough that a student
# returning the next day gets a fresh cap rather than inheriting yesterday's
# count.
SESSION_GAP = timedelta(hours=3)

# Cap on user turns within one inferred session. Chosen as a cost/abuse
# guard for the Gemini free tier's per-minute limits, not a claim about how
# long a supportive conversation "should" be.
MAX_TURNS_PER_SESSION = 30

# Keeps replies conversational rather than essay-length, and bounds
# per-request token cost.
MAX_OUTPUT_TOKENS = 400


class SessionLimitExceeded(RuntimeError):
    """Raised when the caller has already used MAX_TURNS_PER_SESSION turns."""


@dataclass
class ChatTurnResult:
    """Both rows persisted by one call to `send_message`."""

    user_message: ChatMessage
    assistant_message: ChatMessage


def _count_current_session_turns(db: Session, user_id: int) -> int:
    """Count user turns in the caller's current inferred session.

    Walks the user's messages newest-first and stops at the first gap larger
    than `SESSION_GAP`, so a conversation from days ago never counts against
    today's cap.

    Args:
        db: Database session.
        user_id: Whose history to count.

    Returns:
        Number of "user"-role messages in the current inferred session.
    """
    recent = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_TURNS_PER_SESSION * 2 + 5)  # generous headroom over what we can ever need
        .all()
    )
    count = 0
    previous_at: datetime | None = None
    for message in recent:
        if previous_at is not None and (previous_at - message.created_at) > SESSION_GAP:
            break
        if message.role == "user":
            count += 1
        previous_at = message.created_at
    return count


def _build_gemini_contents(
    history: list[ChatMessage], new_user_text: str
) -> list[genai_types.Content]:
    """Translate persisted history plus the new message into Gemini's Content list.

    Gemini calls the assistant role "model", not "assistant" — mapped only
    here, so the rest of this codebase keeps using "assistant", consistent
    with this project's role vocabulary elsewhere.

    Args:
        history: Prior messages, oldest first.
        new_user_text: The student's new message, not yet persisted.

    Returns:
        Contents ready to pass to `generate_content`.
    """
    contents = [
        genai_types.Content(
            role="model" if m.role == "assistant" else "user",
            parts=[genai_types.Part(text=m.content)],
        )
        for m in history
    ]
    contents.append(
        genai_types.Content(role="user", parts=[genai_types.Part(text=new_user_text)])
    )
    return contents


def send_message(db: Session, user_id: int, text: str) -> ChatTurnResult:
    """Run one chat turn: persist the student's message, get and validate a reply.

    Args:
        db: Database session.
        user_id: Authenticated caller.
        text: The student's message text.

    Returns:
        Both persisted rows.

    Raises:
        SessionLimitExceeded: If the caller has already used
            `MAX_TURNS_PER_SESSION` turns in their current inferred session.
            Nothing is persisted and no Gemini call is made.
        ChatConfigError: If `GEMINI_API_KEY` is missing or Gemini rejects it
            as invalid — a deployment problem, not something papered over
            with a canned reply. The user's message is not persisted in this
            case either, so a broken deployment cannot silently accumulate
            one-sided conversation history.
    """
    if _count_current_session_turns(db, user_id) >= MAX_TURNS_PER_SESSION:
        raise SessionLimitExceeded(SESSION_CAP_MESSAGE)

    history = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    history.reverse()  # oldest first, as Gemini expects

    reply_text, fallback_reason = _get_validated_reply(history, text)

    user_message = ChatMessage(user_id=user_id, role="user", content=text)
    db.add(user_message)
    db.flush()  # assign user_message.id without committing

    log_message_sentiment(user_id, user_message.id, text)  # best-effort; see sentiment.py

    assistant_message = ChatMessage(
        user_id=user_id,
        role="assistant",
        content=reply_text,
        fallback_reason=fallback_reason,
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    return ChatTurnResult(user_message=user_message, assistant_message=assistant_message)


def _get_validated_reply(
    history: list[ChatMessage], new_user_text: str
) -> tuple[str, str | None]:
    """Call Gemini and run its output through the existing safety gate.

    Config problems (missing/invalid key) propagate as `ChatConfigError`,
    deliberately not caught here — see module docstring. Every other
    failure mode (rate limit, transient outage, an empty or unsafe reply)
    resolves to exactly one canned fallback, chosen once, not retried.

    Args:
        history: Prior messages, oldest first. Not yet including the new one.
        new_user_text: The student's new message.

    Returns:
        `(text to show the student, fallback_reason or None if genuine)`.
    """
    client = get_gemini_client()  # raises ChatConfigError — not caught here
    settings = get_settings()
    contents = _build_gemini_contents(history, new_user_text)
    config = genai_types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT, max_output_tokens=MAX_OUTPUT_TOKENS
    )

    try:
        response = client.models.generate_content(
            model=settings.gemini_model, contents=contents, config=config
        )
        raw_text = (response.text or "").strip()
        if not raw_text:
            raise ValueError("Gemini returned an empty response")
    except genai_errors.ClientError as exc:
        if exc.code == 429:
            logger.warning("Gemini rate limit hit (429): %s", exc)
            return RATE_LIMIT_FALLBACK_REPLY, "gemini_rate_limited"
        if exc.code in (401, 403):
            # An invalid/revoked key is a configuration problem, not a
            # transient runtime failure — surfaced the same way a missing
            # key is, not swapped for a canned reply.
            raise ChatConfigError(
                f"Gemini rejected the configured API key (HTTP {exc.code}). "
                "Check GEMINI_API_KEY in backend/.env."
            ) from exc
        logger.warning("Gemini client error: %s", exc)
        return UNAVAILABLE_FALLBACK_REPLY, "gemini_unavailable"
    except (genai_errors.ServerError, genai_errors.APIError, ValueError) as exc:
        logger.warning("Gemini call failed: %s", exc)
        return UNAVAILABLE_FALLBACK_REPLY, "gemini_unavailable"

    try:
        validate_user_facing_text(raw_text)
    except ExplanationSafetyError:
        logger.warning(
            "Chatbot reply failed the safety gate and was replaced with the canned "
            "fallback. The rejected draft is not persisted anywhere."
        )
        return SAFETY_FALLBACK_REPLY, "safety_gate_rejected"

    return raw_text, None
