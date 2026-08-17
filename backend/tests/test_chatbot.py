"""Chatbot tests (Module 3).

Every test mocks the Gemini call — `app.chatbot.service.get_gemini_client`
is monkeypatched to a stand-in with the same `.models.generate_content(...)`
surface, so nothing here makes a real network call or spends real API quota.
The one exception is `test_missing_gemini_api_key_returns_a_clear_503`, which
deliberately does *not* patch anything: `GEMINI_API_KEY` is genuinely unset
in the test environment (see `tests/conftest.py`), so this exercises the
real "tell me, don't fail silently" path end-to-end.

`test_safety_gate_catches_and_replaces_an_unsafe_reply` is the case
`IMPLEMENTATION_RULES.md` and this session's task explicitly asked for: a
Gemini draft engineered to fail `validate_user_facing_text()` must be caught
and replaced, never shown to a student.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from google.genai import errors as genai_errors

import app.chatbot.service as chat_service
from app.chatbot.prompts import (
    RATE_LIMIT_FALLBACK_REPLY,
    SAFETY_FALLBACK_REPLY,
    SESSION_CAP_MESSAGE,
    SYSTEM_PROMPT,
    UNAVAILABLE_FALLBACK_REPLY,
    build_system_instruction,
)
from ml_pipeline.src.explainability.generator import validate_user_facing_text
from tests.test_assessments import NOTEBOOK_CASE_HIGH_STRESS


def _fake_client(reply_text: str | None = None, raise_: Exception | None = None) -> MagicMock:
    """Stand-in for `genai.Client`, exposing only what service.py calls."""
    client = MagicMock()
    if raise_ is not None:
        client.models.generate_content.side_effect = raise_
    else:
        client.models.generate_content.return_value = SimpleNamespace(text=reply_text)
    return client


def _headers(client: TestClient, email: str) -> dict[str, str]:
    credentials = {"email": email, "password": "a-long-enough-password"}
    client.post("/auth/register", json=credentials)
    token = client.post("/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_fallback_replies_pass_the_safety_gate() -> None:
    """Regression guard: every canned fallback must itself pass the gate it stands in for."""
    for text in (
        SAFETY_FALLBACK_REPLY,
        RATE_LIMIT_FALLBACK_REPLY,
        UNAVAILABLE_FALLBACK_REPLY,
        SESSION_CAP_MESSAGE,
    ):
        validate_user_facing_text(text)  # must not raise


def test_chat_requires_authentication(client: TestClient) -> None:
    response = client.post("/chat/messages", json={"content": "Hello"})

    assert response.status_code == 401


def test_missing_gemini_api_key_returns_a_clear_503(client: TestClient) -> None:
    """No GEMINI_API_KEY in the test environment — must fail loudly, not silently."""
    headers = _headers(client, "no.key@example.ac.uk")

    response = client.post("/chat/messages", json={"content": "Hello"}, headers=headers)

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_normal_reply_is_persisted_and_returned(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "chat.happy@example.ac.uk")
    fake = _fake_client(reply_text="Thanks for sharing that. What's felt hardest about today?")
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    response = client.post(
        "/chat/messages", json={"content": "I'm feeling a bit overwhelmed."}, headers=headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user_message"]["role"] == "user"
    assert body["user_message"]["content"] == "I'm feeling a bit overwhelmed."
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["content"] == (
        "Thanks for sharing that. What's felt hardest about today?"
    )
    assert body["assistant_message"]["fallback_reason"] is None
    fake.models.generate_content.assert_called_once()


def test_safety_gate_catches_and_replaces_an_unsafe_reply(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_session
) -> None:
    """The deliberately risky case: Gemini drafts a diagnostic-sounding reply."""
    headers = _headers(client, "chat.unsafe@example.ac.uk")
    risky_draft = (
        "Based on what you've told me, it sounds like you may have an anxiety "
        "disorder. I'd recommend starting treatment as soon as possible."
    )
    fake = _fake_client(reply_text=risky_draft)
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    response = client.post(
        "/chat/messages", json={"content": "I can't stop worrying about everything."}, headers=headers
    )

    assert response.status_code == 201
    assistant = response.json()["assistant_message"]
    assert assistant["content"] == SAFETY_FALLBACK_REPLY
    assert assistant["fallback_reason"] == "safety_gate_rejected"
    # The rejected raw draft must never reach the caller in any form.
    assert "disorder" not in response.text.lower()
    assert "treatment" not in response.text.lower()

    from app.models.chat_message import ChatMessage

    stored = (
        db_session.query(ChatMessage)
        .filter(ChatMessage.id == assistant["id"])
        .one()
    )
    assert stored.content == SAFETY_FALLBACK_REPLY
    assert stored.fallback_reason == "safety_gate_rejected"
    assert "disorder" not in stored.content


def test_gemini_rate_limit_returns_graceful_fallback(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "chat.ratelimited@example.ac.uk")
    err = genai_errors.ClientError(
        code=429, response_json={"error": {"message": "rate limited", "status": "RESOURCE_EXHAUSTED"}}
    )
    fake = _fake_client(raise_=err)
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    response = client.post("/chat/messages", json={"content": "hey"}, headers=headers)

    assert response.status_code == 201
    assistant = response.json()["assistant_message"]
    assert assistant["content"] == RATE_LIMIT_FALLBACK_REPLY
    assert assistant["fallback_reason"] == "gemini_rate_limited"


def test_gemini_server_error_returns_graceful_fallback(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "chat.serverdown@example.ac.uk")
    err = genai_errors.ServerError(code=503, response_json={"error": {"message": "overloaded"}})
    fake = _fake_client(raise_=err)
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    response = client.post("/chat/messages", json={"content": "hey"}, headers=headers)

    assert response.status_code == 201
    assistant = response.json()["assistant_message"]
    assert assistant["content"] == UNAVAILABLE_FALLBACK_REPLY
    assert assistant["fallback_reason"] == "gemini_unavailable"


def test_empty_gemini_response_returns_graceful_fallback(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "chat.empty@example.ac.uk")
    fake = _fake_client(reply_text="   ")
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    response = client.post("/chat/messages", json={"content": "hey"}, headers=headers)

    assert response.status_code == 201
    assert response.json()["assistant_message"]["fallback_reason"] == "gemini_unavailable"


def test_gemini_rejecting_the_key_returns_503_not_a_canned_reply(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_session
) -> None:
    """An invalid/revoked key is a configuration problem, not a runtime hiccup."""
    headers = _headers(client, "chat.badkey@example.ac.uk")
    err = genai_errors.ClientError(
        code=401, response_json={"error": {"message": "invalid api key", "status": "UNAUTHENTICATED"}}
    )
    fake = _fake_client(raise_=err)
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    response = client.post("/chat/messages", json={"content": "hey"}, headers=headers)

    assert response.status_code == 503

    from app.models.chat_message import ChatMessage
    from app.models.user import User

    user = db_session.query(User).filter(User.email == "chat.badkey@example.ac.uk").one()
    assert db_session.query(ChatMessage).filter(ChatMessage.user_id == user.id).count() == 0


def test_session_turn_cap_blocks_before_calling_gemini(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_session
) -> None:
    """Once a session is at its cap, no Gemini call is made at all."""
    headers = _headers(client, "chat.capped@example.ac.uk")

    from app.models.chat_message import ChatMessage
    from app.models.user import User

    user = db_session.query(User).filter(User.email == "chat.capped@example.ac.uk").one()
    now = datetime.now(timezone.utc)
    for i in range(chat_service.MAX_TURNS_PER_SESSION):
        db_session.add(ChatMessage(user_id=user.id, role="user", content=f"turn {i}", created_at=now))
        db_session.add(ChatMessage(user_id=user.id, role="assistant", content="ok", created_at=now))
    db_session.commit()

    fake = _fake_client(reply_text="should never be called")
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    response = client.post("/chat/messages", json={"content": "one more"}, headers=headers)

    assert response.status_code == 429
    assert "length limit" in response.json()["detail"].lower()
    fake.models.generate_content.assert_not_called()


def test_history_requires_authentication(client: TestClient) -> None:
    response = client.get("/chat/messages")

    assert response.status_code == 401


def test_history_scoped_to_the_authenticated_caller(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers_a = _headers(client, "chat.a@example.ac.uk")
    headers_b = _headers(client, "chat.b@example.ac.uk")
    fake = _fake_client(reply_text="Thanks for telling me that.")
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    client.post("/chat/messages", json={"content": "hello from A"}, headers=headers_a)

    body_a = client.get("/chat/messages", headers=headers_a).json()
    body_b = client.get("/chat/messages", headers=headers_b).json()

    assert len(body_a) == 2  # the user turn and the reply
    assert body_b == []


def test_history_is_returned_oldest_first(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "chat.order@example.ac.uk")
    fake = _fake_client(reply_text="Got it, thanks for letting me know.")
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    client.post("/chat/messages", json={"content": "first"}, headers=headers)
    client.post("/chat/messages", json={"content": "second"}, headers=headers)

    body = client.get("/chat/messages", headers=headers).json()

    assert [m["content"] for m in body if m["role"] == "user"] == ["first", "second"]
    timestamps = [m["created_at"] for m in body]
    assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------------------
# "Discuss my own past result" (round 2, item 3)
# ---------------------------------------------------------------------------


def test_build_system_instruction_omits_context_block_when_no_explanation() -> None:
    assert build_system_instruction(None) == SYSTEM_PROMPT


def test_build_system_instruction_appends_the_paragraph_verbatim_when_present() -> None:
    paragraph = "Your current wellbeing check-in suggests you are under a fair amount of pressure."
    instruction = build_system_instruction(paragraph)

    assert instruction.startswith(SYSTEM_PROMPT)
    assert paragraph in instruction


def test_chat_uses_the_students_own_recent_explanation_as_context(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_session
) -> None:
    """A student with a prior check-in gets that explanation folded into the system prompt."""
    headers = _headers(client, "chat.context@example.ac.uk")

    # A real check-in first, through the real (unchanged) pipeline — so this
    # is a genuine ExplanationRecord, not a hand-built fixture.
    assessment_response = client.post(
        "/assessments", json=NOTEBOOK_CASE_HIGH_STRESS, headers=headers
    )
    assert assessment_response.status_code == 201
    expected_paragraph = assessment_response.json()["explanation"]

    fake = _fake_client(reply_text="Sure, happy to talk through that with you.")
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    response = client.post(
        "/chat/messages", json={"content": "Why did it say I was stressed?"}, headers=headers
    )

    assert response.status_code == 201
    _, kwargs = fake.models.generate_content.call_args
    system_instruction = kwargs["config"].system_instruction
    assert expected_paragraph in system_instruction
    # The base rules are still present alongside the added context.
    assert "Never diagnose" in system_instruction


def test_chat_context_never_carries_shap_or_feature_vocabulary(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The context fold-in reads only the safety-gated paragraph — nothing technical."""
    headers = _headers(client, "chat.context.safe@example.ac.uk")
    client.post("/assessments", json=NOTEBOOK_CASE_HIGH_STRESS, headers=headers)

    fake = _fake_client(reply_text="Sure, happy to talk through that with you.")
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    client.post("/chat/messages", json={"content": "Why did it say that?"}, headers=headers)

    _, kwargs = fake.models.generate_content.call_args
    system_instruction = kwargs["config"].system_instruction.lower()
    for term in ("shap", "feature", "importance", "coefficient", "probability"):
        assert term not in system_instruction


def test_chat_without_a_prior_checkin_gets_no_context_block(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A student who has never completed a check-in gets the bare system prompt."""
    headers = _headers(client, "chat.no.checkin@example.ac.uk")
    fake = _fake_client(reply_text="Sure, tell me more.")
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    client.post("/chat/messages", json={"content": "Hi"}, headers=headers)

    _, kwargs = fake.models.generate_content.call_args
    assert kwargs["config"].system_instruction == SYSTEM_PROMPT


def test_chat_context_is_scoped_to_the_authenticated_caller(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """User B's chat context must never include user A's explanation."""
    headers_a = _headers(client, "chat.context.a@example.ac.uk")
    headers_b = _headers(client, "chat.context.b@example.ac.uk")

    assessment_response = client.post(
        "/assessments", json=NOTEBOOK_CASE_HIGH_STRESS, headers=headers_a
    )
    a_paragraph = assessment_response.json()["explanation"]

    fake = _fake_client(reply_text="Sure, tell me more.")
    monkeypatch.setattr(chat_service, "get_gemini_client", lambda: fake)

    client.post("/chat/messages", json={"content": "Hi"}, headers=headers_b)

    _, kwargs = fake.models.generate_content.call_args
    system_instruction = kwargs["config"].system_instruction
    assert a_paragraph not in system_instruction
    assert system_instruction == SYSTEM_PROMPT
