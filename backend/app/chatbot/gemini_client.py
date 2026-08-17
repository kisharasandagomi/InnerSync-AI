"""Constructs the Gemini API client.

Fails loudly, not silently, if `GEMINI_API_KEY` is missing — per `CLAUDE.md`,
hiding a missing key behind a hardcoded fallback reply is exactly what this
module must not do. A missing key is a deployment/configuration problem,
surfaced as a clear `ChatConfigError` (and, from the route layer, an HTTP
503 with an explicit detail message) — not silently swapped for a canned
assistant message. That treatment is reserved for genuine *runtime* failures
of an otherwise correctly configured client; see `app/chatbot/service.py`.
"""

from __future__ import annotations

from functools import lru_cache

from google import genai

from app.core.config import get_settings


class ChatConfigError(RuntimeError):
    """Raised when the Gemini client cannot be constructed or authenticates."""


@lru_cache
def get_gemini_client() -> genai.Client:
    """Return the process-wide Gemini client, constructed once.

    Returns:
        A configured `genai.Client`.

    Raises:
        ChatConfigError: If `GEMINI_API_KEY` is unset or blank. The SDK does
            not validate a key at construction time — an invalid-but-present
            key surfaces later, from the first real call in
            `app.chatbot.service`, which raises this same exception type for
            a 401/403 response so both failure modes are handled identically
            by the API layer.
    """
    settings = get_settings()
    key = settings.gemini_api_key.strip()
    if not key:
        raise ChatConfigError(
            "GEMINI_API_KEY is not set. Copy backend/.env.example to backend/.env "
            "and add a real Gemini API key from https://aistudio.google.com/apikey — "
            "the chatbot cannot start without one."
        )
    return genai.Client(api_key=key)
