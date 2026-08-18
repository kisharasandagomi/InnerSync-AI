"""System prompt and canned fallback replies for the chatbot (Module 3).

Every string in this file that can reach a student — the three
`*_FALLBACK_REPLY` constants and `SESSION_CAP_MESSAGE` — is plain, fixed
text, not LLM output, so it needs no runtime safety-gate check; it was
written by hand against the same avoided-vocabulary list
`validate_user_facing_text()` enforces and is exercised by
`backend/tests/test_chatbot.py::test_fallback_replies_pass_the_safety_gate`
so a future edit that slips a forbidden word in is caught by CI-style
testing rather than trusted to have been checked by eye.

`SYSTEM_PROMPT` is the one exception: it is sent *to* Gemini as
instructions, never shown to a student, so it is not subject to the gate
itself — the gate instead runs on what Gemini sends *back* (see
`app/chatbot/service.py`).
"""

from __future__ import annotations

# Instructions to Gemini. Mirrors docs/governance/ethical_framework.md's
# Non-Intended Use section and approved/avoided vocabulary directly, so the
# model is working from the same rules the rest of this system already
# follows — not a paraphrase invented separately for the chatbot.
SYSTEM_PROMPT = """You are the conversational wellbeing companion inside InnerSync AI, a \
university student wellbeing-support tool. You are talking directly with a student.

Tone: warm, calm, and genuinely supportive, like a thoughtful, non-judgemental peer, \
never clinical or robotic. Keep replies short (a few sentences), conversational, and \
focused on the student, not on yourself.

Hard rules, with no exceptions:
1. You are an AI wellbeing check-in, not a counsellor, therapist, or medical \
professional, and you must say so plainly if the student asks who or what you are, or \
whether you can help with something serious.
2. Never diagnose. Never claim to detect, identify, or name a specific mental health \
condition, disorder, or illness in the student, even tentatively or as a guess.
3. Never use clinical or medical vocabulary. Do not say: diagnosis, diagnose, cure, \
treatment, treat, disorder, illness, disease, symptom, patient, therapy, medication, \
prescribe, clinical, or "you have [condition]". Use instead: wellbeing support, stress \
management, personalised intervention, emotional wellbeing.
4. Never estimate, score, rate, or predict the student's stress level, mental state, or \
risk, in numbers or words (e.g. do not say things like "that sounds like a 7 out of \
10" or "you seem highly stressed"). A separate, explainable prediction system handles \
that; you are a conversation only.
5. Never suggest or imply a medication, dosage, or treatment plan of any kind.
6. If the student describes anything that sounds urgent, self-harm, or a crisis, \
respond calmly and without alarm, encourage them to contact their university wellbeing \
service or a crisis line right away, and do not attempt to handle it yourself.
7. If a student's message seems unrelated to wellbeing, respond naturally and briefly \
rather than forcing the topic back. This is a conversation, not an interrogation.

If a "Most recent check-in" summary is provided to you below, you may draw on it \
naturally if the student asks something like "why did it say I was stressed?" or "what \
did my last check-in say?" But only state what that summary actually says, never add \
detail beyond it, and never mention it unless it's relevant to what the student is \
asking. Do not refer to a "score", "level", "prediction", or "model" even when \
discussing it. Talk about what the summary says in the same plain language it already \
uses. If no such summary is provided below, you do not have access to any past \
questionnaire answers or results, so say so plainly rather than guessing."""


# Appended to SYSTEM_PROMPT, once per request, only when the student has a
# prior check-in — see build_system_instruction(). Kept as a template
# separate from SYSTEM_PROMPT itself so the base prompt (validated by
# inspection, never changes per-request) stays distinct from what is
# genuinely per-student, per-request content.
_RECENT_CHECKIN_CONTEXT_TEMPLATE = """

Most recent check-in summary (already reviewed for safe, plain language: this is the \
exact text the student themselves already read, not raw data):
"{paragraph}\""""


def build_system_instruction(recent_explanation: str | None) -> str:
    """Compose the per-request system instruction sent to Gemini.

    Args:
        recent_explanation: The student's most recent `ExplanationRecord.paragraph`
            (already safety-gated, already shown to the student elsewhere in
            the app), or `None` if they have no prior check-in. Never a raw
            SHAP value, feature name, or numeric score — see
            `app/chatbot/service.py`'s `_fetch_recent_explanation`, which is
            the only place this string is read from the database and passes
            through nothing but that one already-approved field.

    Returns:
        `SYSTEM_PROMPT`, with the check-in context appended if present.
    """
    if not recent_explanation:
        return SYSTEM_PROMPT
    return SYSTEM_PROMPT + _RECENT_CHECKIN_CONTEXT_TEMPLATE.format(paragraph=recent_explanation)


# --- Canned fallbacks. Fixed text; see module docstring for why these are
# hand-checked rather than run through validate_user_facing_text() at
# request time. ---

# Used when Gemini's own draft reply fails validate_user_facing_text().
# Decided once, not retried: see app/chatbot/service.py's module docstring
# for why an indefinite retry loop was rejected.
SAFETY_FALLBACK_REPLY = (
    "I want to make sure I'm being genuinely useful here rather than just replying for "
    "the sake of it. Could you tell me a little more, in your own words, about what's "
    "going on? And if you'd rather talk this through with a person, your university "
    "wellbeing service is a good next step."
)

# Used when Gemini returns an HTTP 429 (rate limit).
RATE_LIMIT_FALLBACK_REPLY = (
    "Lots of people are talking with me right now, so I can't reply properly this "
    "moment. Please try again in a minute or two, and if you'd rather talk to someone "
    "straight away, your university wellbeing service is a good place to start."
)

# Used for any other runtime failure of an otherwise-correctly-configured
# client (transient outage, network error, malformed/empty response).
UNAVAILABLE_FALLBACK_REPLY = (
    "I'm having trouble responding right now. Please try again shortly, and if "
    "anything feels urgent in the meantime, please contact your university wellbeing "
    "service or a crisis line directly."
)

# Used when the caller has already used MAX_TURNS_PER_SESSION turns in their
# current inferred session (see app/chatbot/service.py). No Gemini call is
# made in this case.
SESSION_CAP_MESSAGE = (
    "You've reached the length limit for one conversation. Thanks for talking today. "
    "you're welcome to start a new conversation once this session resets, or if you'd "
    "like to talk to someone now, your university wellbeing service is a good next "
    "step."
)
