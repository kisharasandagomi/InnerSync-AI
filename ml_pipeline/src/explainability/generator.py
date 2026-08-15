"""Converts a single prediction's SHAP attribution into a warm, non-clinical paragraph.

Pipeline, per `.claude/skills/explainable-ai/SKILL.md`:
    technical explanation (SHAP) -> human-centred translation

The technical side is retained in a faithfulness record attached to every
generated explanation, so that the plain-language text can later be checked
against the attribution it claims to describe. The record is never surfaced to
the student.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np

from .templates import (
    CLOSING_BY_CLASS,
    EASING_ADDITIONAL,
    EASING_LEAD_IN,
    EASING_ONLY_LEAD_IN,
    FEATURE_PHRASES,
    FORBIDDEN_CLINICAL_TERMS,
    FORBIDDEN_ML_TERMS,
    OPENING_BY_CLASS,
    RAISING_ADDITIONAL,
    RAISING_LEAD_IN,
)


class ExplanationSafetyError(RuntimeError):
    """Raised when generated text would expose clinical or ML vocabulary to a user."""


def severity_contributions(
    shap_row: np.ndarray,
    class_labels: Sequence[int],
    low_class: int = 0,
    high_class: int = 2,
) -> np.ndarray:
    """Collapse per-class SHAP into a single signed stress-severity axis.

    For a 3-class ordinal target, no single class column supports a coherent
    "raises / eases stress" reading:

    - The **high-stress column alone** describes only distance from the top of
      the scale. For a student predicted moderate, almost every contribution is
      negative (pushing away from high), so the explanation degenerates into an
      all-protective list that contradicts the stated moderate level.
    - The **predicted class's own column** is worse, because its sign means
      "pushed toward this outcome", not "increased stress". For a low-stress
      prediction every strong contributor is positive, which would report
      protective factors such as met basic needs as *raising* stress.

    Taking `SHAP(high) - SHAP(low)` measures how far a factor moves the student
    toward the severe end of the scale relative to the calm end. It respects the
    ordering of the target, and yields a genuine mix of raising and easing
    factors for mid-scale predictions while still resolving to all-easing at the
    low end and all-raising at the high end.

    Args:
        shap_row: SHAP values for a single sample, shape (n_features, n_classes).
        class_labels: Class labels in the same order as `shap_row`'s columns.
        low_class: Label of the least severe class.
        high_class: Label of the most severe class.

    Returns:
        Signed per-feature severity contributions; positive raises stress.

    Raises:
        ValueError: If `shap_row` is not 2-D, or a class label is absent.
    """
    arr = np.asarray(shap_row, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"shap_row must be 2-D (n_features, n_classes); got shape {arr.shape}")
    labels = list(class_labels)
    for label in (low_class, high_class):
        if label not in labels:
            raise ValueError(f"class label {label!r} not in {labels!r}")
    return arr[:, labels.index(high_class)] - arr[:, labels.index(low_class)]


@dataclass(frozen=True)
class ExplanationFactor:
    """One contributing factor, with both its technical and translated form.

    Attributes:
        feature: Source feature name. Internal only — never rendered to a user.
        feature_value: The student's raw value for that feature. Internal only.
        shap_value: Signed severity contribution (positive raises stress).
            Internal only.
        direction: "raising" or "easing".
        rank: 1-based position among the selected factors, by |shap_value|.
        phrase: The user-facing plain-language phrase for this factor.
    """

    feature: str
    feature_value: float
    shap_value: float
    direction: str
    rank: int
    phrase: str


@dataclass
class StressExplanation:
    """A generated explanation plus the attribution it was derived from.

    Only `paragraph` is ever shown to a student. Everything else exists for
    research evaluation of explanation faithfulness.
    """

    paragraph: str
    predicted_class: int
    factors: list[ExplanationFactor]
    faithfulness_record: dict = field(default_factory=dict)

    def user_facing(self) -> str:
        """Return the only field that may be displayed to a student."""
        return self.paragraph


def validate_user_facing_text(text: str) -> None:
    """Reject any text containing clinical or ML vocabulary.

    This is a hard safety gate, not a lint: `IMPLEMENTATION_RULES.md` requires
    that a change which would expose a SHAP value, feature name, or numeric
    weight to a user causes a stop rather than a silent pass.

    Args:
        text: Candidate user-facing string.

    Raises:
        ExplanationSafetyError: If a forbidden term is present.
    """
    # Word-boundary matching, not naive substring: a plain `in` check produces
    # false positives on innocuous words that merely contain a banned term
    # ("secure" contains "cure", "features" would trip on "feature"). The
    # trailing \w* still catches inflections, so "treat" matches "treatment"
    # and "treated" while "secure" is correctly left alone.
    lowered = text.lower()
    found = [
        t
        for t in FORBIDDEN_CLINICAL_TERMS + FORBIDDEN_ML_TERMS
        if re.search(rf"\b{re.escape(t)}\w*\b", lowered)
    ]
    if found:
        raise ExplanationSafetyError(
            f"Generated text contains forbidden vocabulary {sorted(set(found))}. "
            "See docs/governance/ethical_framework.md and "
            ".claude/skills/explainable-ai/SKILL.md."
        )


def extract_top_factors(
    shap_values: Sequence[float],
    feature_values: Sequence[float],
    feature_names: Sequence[str],
    top_n: int = 4,
) -> list[ExplanationFactor]:
    """Select the strongest contributing factors and translate each into a phrase.

    `shap_values` must be a **signed severity axis** — normally the output of
    `severity_contributions()`. Positive means the factor pushes the student
    toward the severe end of the scale, negative toward the calm end. See that
    function for why neither the high-stress column nor the predicted class's
    own column works on its own.

    Args:
        shap_values: Per-feature signed severity contributions.
        feature_values: The student's raw feature values, same order.
        feature_names: Feature names, same order.
        top_n: How many factors to select, by absolute contribution.

    Returns:
        Factors ordered strongest first.

    Raises:
        ValueError: If the three sequences differ in length, or a feature has no
            template defined.
    """
    if not (len(shap_values) == len(feature_values) == len(feature_names)):
        raise ValueError(
            f"Length mismatch: shap_values={len(shap_values)}, "
            f"feature_values={len(feature_values)}, feature_names={len(feature_names)}"
        )

    missing = [f for f in feature_names if f not in FEATURE_PHRASES]
    if missing:
        raise ValueError(f"No plain-language template defined for: {missing}")

    shap_arr = np.asarray(shap_values, dtype=float)
    order = np.argsort(np.abs(shap_arr))[::-1][:top_n]

    factors: list[ExplanationFactor] = []
    for rank, idx in enumerate(order, start=1):
        name = feature_names[idx]
        value = float(shap_arr[idx])
        direction = "raising" if value > 0 else "easing"
        factors.append(
            ExplanationFactor(
                feature=name,
                feature_value=float(feature_values[idx]),
                shap_value=value,
                direction=direction,
                rank=rank,
                phrase=FEATURE_PHRASES[name][direction],
            )
        )
    return factors


def assemble_explanation_paragraph(
    factors: Sequence[ExplanationFactor],
    predicted_class: int,
) -> str:
    """Assemble selected factors into a short, warm, non-clinical paragraph.

    Produces 3-5 sentences: an opening that sets the overall picture, the
    pressures that stood out, anything working protectively, and a closing that
    frames the result as a changeable snapshot rather than a verdict.

    Args:
        factors: Output of `extract_top_factors`, strongest first.
        predicted_class: 0 (low), 1 (moderate) or 2 (high).

    Returns:
        The paragraph shown to the student.

    Raises:
        ValueError: If `predicted_class` is not a known class.
        ExplanationSafetyError: If the assembled text fails the vocabulary gate.
    """
    if predicted_class not in OPENING_BY_CLASS:
        raise ValueError(f"Unknown predicted_class {predicted_class!r}; expected 0, 1 or 2")

    raising = [f for f in factors if f.direction == "raising"]
    easing = [f for f in factors if f.direction == "easing"]

    sentences: list[str] = [OPENING_BY_CLASS[predicted_class]]

    if raising:
        sentences.append(f"{RAISING_LEAD_IN} {raising[0].phrase}.")
        # Cap at two further phrases: three stacked clauses joined by "and"
        # produce a run-on that fails the "understand in one read" test.
        if len(raising) > 1:
            joined = _join_phrases([f.phrase for f in raising[1:3]])
            sentences.append(f"{RAISING_ADDITIONAL} {joined}.")

    if easing:
        if raising:
            sentences.append(f"{EASING_LEAD_IN} {easing[0].phrase}.")
        else:
            # No pressures surfaced. "Encouragingly, ..." would sit oddly after an
            # opening that already stated a moderate or high level, so use a
            # lead-in that acknowledges the level instead of contradicting it.
            sentences.append(f"{EASING_ONLY_LEAD_IN} {easing[0].phrase}.")
        if len(easing) > 1:
            joined = _join_phrases([f.phrase for f in easing[1:3]])
            sentences.append(f"{EASING_ADDITIONAL} {joined}.")

    sentences.append(CLOSING_BY_CLASS[predicted_class])

    paragraph = " ".join(_capitalise_first(s) for s in sentences)
    validate_user_facing_text(paragraph)
    return paragraph


def generate_explanation(
    shap_values: Sequence[float],
    feature_values: Sequence[float],
    feature_names: Sequence[str],
    predicted_class: int,
    top_n: int = 4,
    context: dict | None = None,
) -> StressExplanation:
    """Full pipeline: SHAP attribution in, student-readable explanation out.

    Args:
        shap_values: Per-feature signed severity contributions, normally from
            `severity_contributions()`.
        feature_values: The student's raw feature values, same order.
        feature_names: Feature names, same order.
        predicted_class: 0 (low), 1 (moderate) or 2 (high).
        top_n: How many contributing factors to mention.
        context: Optional extra fields to store in the faithfulness record
            (e.g. true label, model version) — never shown to the student.

    Returns:
        A `StressExplanation` whose `.paragraph` is safe to display and whose
        `.faithfulness_record` retains the attribution it was derived from.
    """
    factors = extract_top_factors(shap_values, feature_values, feature_names, top_n=top_n)
    paragraph = assemble_explanation_paragraph(factors, predicted_class)

    record = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "predicted_class": int(predicted_class),
        "top_n": int(top_n),
        "factors": [asdict(f) for f in factors],
        "total_abs_shap_all_features": float(np.abs(np.asarray(shap_values, dtype=float)).sum()),
        "abs_shap_covered_by_explanation": float(sum(abs(f.shap_value) for f in factors)),
        "paragraph": paragraph,
    }
    total = record["total_abs_shap_all_features"]
    record["coverage_ratio"] = (
        record["abs_shap_covered_by_explanation"] / total if total else 0.0
    )
    if context:
        record["context"] = context

    return StressExplanation(
        paragraph=paragraph,
        predicted_class=int(predicted_class),
        factors=factors,
        faithfulness_record=record,
    )


def save_faithfulness_log(
    explanations: Sequence[StressExplanation],
    out_path: str | Path,
) -> Path:
    """Write faithfulness records to newline-delimited JSON for later evaluation.

    Args:
        explanations: Generated explanations to log.
        out_path: Destination `.jsonl` file.

    Returns:
        The path written.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for exp in explanations:
            f.write(json.dumps(exp.faithfulness_record) + "\n")
    return out_path


def _join_phrases(phrases: Sequence[str]) -> str:
    """Join phrases with commas and a trailing 'and'."""
    if len(phrases) == 1:
        return phrases[0]
    return f"{', '.join(phrases[:-1])}, and {phrases[-1]}"


def _capitalise_first(sentence: str) -> str:
    """Capitalise only the first character, preserving the rest."""
    return sentence[0].upper() + sentence[1:] if sentence else sentence
