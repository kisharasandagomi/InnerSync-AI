"""Request/response schemas for the chatbot (Module 3).

Like `app.schemas.assessment`, these never carry SHAP values or ML
terminology — but for a different reason here: this module has no attribution
to leak, because the chatbot never runs a prediction. `fallback_reason` is
included so the frontend *could* show a subtle "having trouble" indicator if
it chooses to, but is never treated as sensitive; it is a short fixed
audit code (see `app.models.chat_message.ChatMessage.fallback_reason`), not
technical model output.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageIn(BaseModel):
    """One message the student sends."""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=4000)


class ChatMessageOut(BaseModel):
    """One persisted message, either role."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    fallback_reason: str | None = None


class ChatTurnResponse(BaseModel):
    """What `POST /chat/messages` returns: the pair from one exchange."""

    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
