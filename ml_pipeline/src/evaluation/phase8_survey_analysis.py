"""Reproducible analysis of the two Phase 8 evaluation survey exports:
System Usability Scale (SUS) scoring, and explanation/chatbot/
recommendation-usefulness mean ratings.

Evaluation/analysis only, same boundary as `local_data_triangulation.py`:
no model is trained or retrained here, and nothing computed by this script
is fed into `POST /assessments` or the deployed pipeline. It exists so
figures previously computed outside the repo are reproducible and logged
the same way as every other finding in `ml_pipeline/experiments/`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(REPO_ROOT / "ml_pipeline"))

from src.experiments.logger import hash_file, log_experiment  # noqa: E402

PART1_PATH = REPO_ROOT / "docs" / "research" / "phase8_evaluation" / "survey_part1.csv"
PART2_PATH = REPO_ROOT / "docs" / "research" / "phase8_evaluation" / "survey_part2_followup.csv"
EXPERIMENTS_DIR = REPO_ROOT / "ml_pipeline" / "experiments"

# --- Column names, verbatim from the Google Forms export headers ---------

SUS_ITEM_COLUMNS_POSITIVE = [
    "  I think that I would like to use this system frequently.  ",
    "  I thought the system was easy to use.  ",
    "  I found the various functions in this system were well integrated.  ",
    "  I would imagine that most people would learn to use this system very quickly.  ",
    "  I felt very confident using the system.  ",
]
SUS_ITEM_COLUMNS_NEGATIVE = [
    "  I found the system unnecessarily complex.  ",
    "  I thought there was too much inconsistency in this system.  ",
    "  I found the system very cumbersome/awkward to use.  ",
    "  I needed to learn a lot of things before I could get going with this system.  ",
]

EXPLANATION_COLUMNS = [
    "  The explanation I received was easy to understand.  ",
    "The explanation avoided confusing technical or clinical language. ",
    "The explanation felt like it genuinely reflected my situation. ",
    "I trust that the explanation was based on my actual answers, not generic text. ",
    "The explanation felt supportive rather than alarming or judgmental. ",
]
CHATBOT_COLUMNS = [
    "  The chatbot felt supportive and easy to talk to.  ",
    "  The chatbot made it clear it wasn't a substitute for professional support.  ",
]
OVERALL_RATING_COLUMN = "Overall, how would you rate your experience with InnerSync AI? "

TECHNICAL_SUPPORT_COLUMN = (
    "I think that I would need the support of a technical person to be able to use this system. "
)
RECOMMENDATION_USEFULNESS_COLUMNS = [
    "  The suggestions I received felt relevant to what's actually affecting me.  ",
    "  The suggestions felt specific and actionable, not generic advice.  ",
    "  I would consider actually trying at least one of the suggestions.  ",
    "  The number of suggestions felt appropriate (not overwhelming, not too few).  ",
]


def load_part1(path: Path = PART1_PATH) -> pd.DataFrame:
    """Load the first Phase 8 survey export (SUS core items + explanation/
    chatbot ratings), n=7."""
    return pd.read_csv(path)


def load_part2(path: Path = PART2_PATH) -> pd.DataFrame:
    """Load the second, follow-up Phase 8 survey export (the SUS
    "technical support" item + recommendation-usefulness items), n=7."""
    return pd.read_csv(path)


def compute_sus_scores(df: pd.DataFrame) -> dict[str, Any]:
    """Score the System Usability Scale from `df`, documenting the 9-item
    modification explicitly.

    **9-item modification.** The standard SUS is 10 alternating
    positive/negative statements, scored 0-4 each (positive: response-1,
    negative: 5-response), summed to a 0-40 raw total, then multiplied by
    2.5 to a 0-100 scale. This survey's main form (`survey_part1.csv`)
    presents 9 of the 10 standard items; the 10th ("I think that I would
    need the support of a technical person to be able to use this
    system.") was moved to the short follow-up form
    (`survey_part2_followup.csv`) instead, to keep the main form shorter.

    That item is deliberately **excluded from the SUS total here**, not
    merged back in from the follow-up file -- the two forms were completed
    as separate response sessions, and folding a follow-up answer into a
    same-sitting SUS score would overstate what was actually measured in
    one sitting. The scale is adjusted accordingly: 9 items, each 0-4, for
    a raw range of 0-36, multiplied by 100/36 (rather than the standard
    2.5) to preserve the 0-100 SUS scale. The excluded item's own responses
    are reported separately (see `compute_technical_support_item`) rather
    than silently dropped.

    Args:
        df: `survey_part1.csv`, loaded via `load_part1`.

    Returns:
        Per-respondent scores and the sample mean/median/std.
    """
    n_items = len(SUS_ITEM_COLUMNS_POSITIVE) + len(SUS_ITEM_COLUMNS_NEGATIVE)
    assert n_items == 9, "expected exactly 9 SUS items on the main form"

    positive_scores = sum((df[col] - 1) for col in SUS_ITEM_COLUMNS_POSITIVE)
    negative_scores = sum((5 - df[col]) for col in SUS_ITEM_COLUMNS_NEGATIVE)
    raw_sum = positive_scores + negative_scores  # 0-36 per respondent

    multiplier = 100 / (n_items * 4)  # 100/36, replacing the standard 2.5 (=100/40)
    sus_scores = raw_sum * multiplier

    return {
        "n_items": n_items,
        "multiplier": round(multiplier, 6),
        "per_respondent": [round(float(s), 2) for s in sus_scores.tolist()],
        "mean": round(float(sus_scores.mean()), 1),
        "median": round(float(sus_scores.median()), 1),
        "std": round(float(sus_scores.std(ddof=1)), 2),
        "min": round(float(sus_scores.min()), 1),
        "max": round(float(sus_scores.max()), 1),
    }


def compute_technical_support_item(df: pd.DataFrame) -> dict[str, Any]:
    """Descriptive stats for the SUS item excluded from the 9-item total.

    Args:
        df: `survey_part2_followup.csv`, loaded via `load_part2`.

    Returns:
        Response distribution and mean for the standalone item (1=strongly
        disagree they'd need technical support ... 5=strongly agree).
    """
    col = df[TECHNICAL_SUPPORT_COLUMN]
    return {
        "mean_1_to_5": round(float(col.mean()), 2),
        "distribution": {str(k): int(v) for k, v in col.value_counts(dropna=False).items()},
        "note": "1 = strongly disagree they would need technical support (most usable end)",
    }


def _pooled_mean(df: pd.DataFrame, columns: list[str]) -> dict[str, Any]:
    """Mean/median across all respondents and all listed 1-5 items, pooled.

    Args:
        df: A survey dataframe.
        columns: The Likert-item column names to pool.

    Returns:
        The pooled mean/median plus each item's own mean, and the count of
        non-missing values actually averaged (some respondents skipped a
        question).
    """
    values = df[columns].to_numpy(dtype=float).flatten()
    values = values[~np.isnan(values)]
    return {
        "pooled_mean": round(float(values.mean()), 2),
        "pooled_median": round(float(np.median(values)), 2),
        "n_values": int(values.size),
        "per_item_mean": {col.strip(): round(float(df[col].mean()), 2) for col in columns},
    }


def run() -> dict[str, Any]:
    """Run the full Phase 8 survey analysis.

    Returns:
        SUS scoring, the excluded technical-support item, explanation/
        chatbot/recommendation-usefulness means, and the overall rating.
    """
    part1 = load_part1()
    part2 = load_part2()

    return {
        "n_part1": int(len(part1)),
        "n_part2": int(len(part2)),
        "sus": compute_sus_scores(part1),
        "sus_excluded_technical_support_item": compute_technical_support_item(part2),
        "explanation_usefulness": _pooled_mean(part1, EXPLANATION_COLUMNS),
        "chatbot_usefulness": _pooled_mean(part1, CHATBOT_COLUMNS),
        "recommendation_usefulness": _pooled_mean(part2, RECOMMENDATION_USEFULNESS_COLUMNS),
        "overall_rating_1_to_5": {
            "mean": round(float(part1[OVERALL_RATING_COLUMN].mean()), 2),
            "distribution": {
                str(k): int(v) for k, v in part1[OVERALL_RATING_COLUMN].value_counts(dropna=False).items()
            },
        },
    }


def main() -> None:
    results = run()

    log_path = log_experiment(
        experiments_dir=EXPERIMENTS_DIR,
        experiment_name="phase8_survey_analysis",
        model_name="descriptive_analysis_no_model_trained",
        hyperparameters={
            "sus_scoring": {
                "items_used": 9,
                "items_excluded": 1,
                "excluded_item": TECHNICAL_SUPPORT_COLUMN.strip(),
                "multiplier": 100 / 36,
                "standard_sus_multiplier_for_comparison": 2.5,
            }
        },
        dataset_path=PART1_PATH,
        split_info={
            "note": "no train/test split; full-sample survey analysis across two linked exports",
            "part1_path": str(PART1_PATH),
            "part2_path": str(PART2_PATH),
            "part2_sha256": hash_file(PART2_PATH),
        },
        metrics=results,
    )

    print(f"Wrote {log_path}\n")
    print("=== System Usability Scale (9-item modification) ===")
    sus = results["sus"]
    print(f"n = {results['n_part1']}, items = {sus['n_items']}, multiplier = {sus['multiplier']}")
    print(f"per-respondent scores: {sus['per_respondent']}")
    print(f"mean = {sus['mean']}, median = {sus['median']}, std = {sus['std']}")

    print("\n=== Excluded SUS item (technical support), reported separately ===")
    print(results["sus_excluded_technical_support_item"])

    print("\n=== Explanation usefulness (pooled across 5 items) ===")
    print(results["explanation_usefulness"])

    print("\n=== Chatbot usefulness (pooled across 2 items) ===")
    print(results["chatbot_usefulness"])

    print("\n=== Recommendation usefulness (pooled across 4 items, part 2) ===")
    print(results["recommendation_usefulness"])

    print("\n=== Overall rating ===")
    print(results["overall_rating_1_to_5"])


if __name__ == "__main__":
    main()
