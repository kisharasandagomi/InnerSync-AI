"""Supplementary sentiment logging for the student's own chatbot messages.

Non-model-facing evidence log only — the same spirit as the faithfulness
logging elsewhere in this system (see
`ml_pipeline/src/explainability/generator.py`'s `save_faithfulness_log`):
scores are never returned to the student, never fed into `StressPredictor`
or any other model, and never influence the chatbot's reply in any way.
Reuses the lexicon scoring already built for the NLP ablation study
(`ml_pipeline/src/nlp/lexicon_scores.py`) rather than re-implementing it.

**The raw message text is never logged, only the derived numeric scores.**
`docs/governance/ethical_framework.md`'s Risk Mitigation table lists "no
plaintext sensitive fields in logs" as the standing mitigation for a data
breach; a student's own wellbeing-chat text is exactly the kind of sensitive
field that principle is protecting. The text is read once, in memory, to
compute four numbers, and discarded — never written to a log line, a file,
or any table other than `chat_messages.content` itself (already covered by
the same database access controls as the rest of the system).

Best-effort only: a failure here is caught and logged, never allowed to
break a chat turn — this is optional evidence-gathering, not part of the
critical path Module 3's boundary or the safety gate depend on.
"""

from __future__ import annotations

import logging

from ml_pipeline.src.nlp.lexicon_scores import compute_textblob_scores, compute_vader_scores

logger = logging.getLogger("chatbot.sentiment")


def log_message_sentiment(user_id: int, message_id: int, text: str) -> None:
    """Score one student message and log the resulting numbers, best-effort.

    Args:
        user_id: Whose message this is.
        message_id: The persisted `ChatMessage` row id, so a score can later
            be cross-referenced back to its message without the log itself
            carrying any text.
        text: The student's own message text. Read only to compute scores;
            never included in the log line.
    """
    try:
        vader = compute_vader_scores([text]).iloc[0].to_dict()
        textblob = compute_textblob_scores([text]).iloc[0].to_dict()
        logger.info(
            "chat_message_sentiment user_id=%s message_id=%s "
            "vader_compound=%.4f textblob_polarity=%.4f textblob_subjectivity=%.4f",
            user_id,
            message_id,
            vader["vader_compound"],
            textblob["textblob_polarity"],
            textblob["textblob_subjectivity"],
        )
    except Exception:  # noqa: BLE001 - best-effort: must never break a chat turn
        logger.exception(
            "Sentiment logging failed for user_id=%s message_id=%s", user_id, message_id
        )
