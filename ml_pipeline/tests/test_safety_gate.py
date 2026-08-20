"""Vocabulary safety gate: `validate_user_facing_text()`.

See `ml_pipeline/src/explainability/generator.py` -- the hard gate
`IMPLEMENTATION_RULES.md` requires so a change exposing clinical or ML
vocabulary to a student stops rather than passing silently.
"""

from __future__ import annotations

import pytest

from ml_pipeline.src.explainability.generator import (
    ExplanationSafetyError,
    validate_user_facing_text,
)


def test_forbidden_clinical_term_is_rejected() -> None:
    with pytest.raises(ExplanationSafetyError):
        validate_user_facing_text("This treatment plan should help.")


def test_forbidden_ml_term_is_rejected() -> None:
    with pytest.raises(ExplanationSafetyError):
        validate_user_facing_text("Your prediction for this week looks steady.")


def test_clean_text_passes() -> None:
    # Must not raise.
    validate_user_facing_text(
        "Things have felt manageable lately, and it's worth noticing that."
    )


def test_word_boundary_false_positive_does_not_trigger_rejection() -> None:
    """"secure" contains the substring "cure" but is not the forbidden word
    itself -- the module docstring calls this out explicitly as the reason
    naive substring matching was rejected in favour of \\b-anchored regex."""
    validate_user_facing_text("Your login is secure and your data stays private.")


def test_inflected_forbidden_term_is_still_caught() -> None:
    """The trailing \\w* in the match pattern must still catch inflections
    ("treated"/"treatment" from the stem "treat"), not just exact matches."""
    with pytest.raises(ExplanationSafetyError):
        validate_user_facing_text("You were treated unfairly by the system.")


def test_rejection_message_names_the_offending_terms() -> None:
    with pytest.raises(ExplanationSafetyError, match="disorder"):
        validate_user_facing_text("This could be an early sign of a disorder.")


def test_clinical_and_ml_terms_together_are_both_reported() -> None:
    with pytest.raises(ExplanationSafetyError) as excinfo:
        validate_user_facing_text("The model's diagnosis was clear.")
    message = str(excinfo.value)
    assert "diagnosis" in message
    assert "model" in message
