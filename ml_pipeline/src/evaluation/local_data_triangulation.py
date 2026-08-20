"""Reproducible analysis of the locally-collected student questionnaire
(n=31), used to triangulate the deployed model's five stress-factor domains
against two independently-worded questions in the local survey.

This is evaluation/analysis only. It never trains, fits, or tunes a model
(per ADR-001), and its output is never fed into `POST /assessments` or any
part of the deployed pipeline -- the local survey responses are read here
purely to produce descriptive statistics and a thematic comparison table for
the dissertation, the same "Research World, evidence-only" boundary as
every other script in `ml_pipeline/`.

Previously this analysis was done outside the repo in a separate tool. This
script exists so the same numbers are reproducible and logged the same way
as every other finding in `ml_pipeline/experiments/`, per
`IMPLEMENTATION_RULES.md`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(REPO_ROOT / "ml_pipeline"))

from src.experiments.logger import log_experiment  # noqa: E402

DATA_PATH = REPO_ROOT / "ml_pipeline" / "datasets" / "local_validation" / "student_responses.csv"
EXPERIMENTS_DIR = REPO_ROOT / "ml_pipeline" / "experiments"

# Column names are the raw Google Forms export headers, kept verbatim rather
# than renamed, so a reader comparing this script against the CSV can match
# them by eye. Several carry trailing whitespace / an embedded newline in
# the source form -- copied exactly, not tidied, so `pd.read_csv` matches on
# the actual column string.
COL_AGE_GROUP = "Age Group "
COL_GENDER = " Gender  "
COL_YEAR = " Current Year of Study  "
COL_STUDY_HOURS = "How many hours do you usually spend studying per day?  "
COL_SLEEP_HOURS = " How many hours do you sleep on average per night?  "
COL_SLEEP_QUALITY = "How would you rate your sleep quality?  "
COL_EXERCISE_FREQ = "How often do you exercise or perform physical activities?  "
COL_MAJOR_CHALLENGES = "Have you experienced any major personal challenges recently?  "
COL_BIGGEST_FACTOR = "What is the biggest factor currently affecting your stress level?  "

# --- Domain coding scheme -----------------------------------------------
#
# The five domains mirror the categories already used throughout this
# dissertation for the deployed model's 14 features (see
# `ml_pipeline/src/recommendation/catalogue.py`'s category field and
# `docs/research/methodology.md`): academic, social, environmental,
# psychological, physiological. A sixth bucket, "not_represented", covers
# responses that are blank or too vague to code confidently (e.g. "Personal
# problems" alone, with no further detail) -- rather than force a guess, an
# honest open-coding practice marks these as uncoded.
#
# IMPORTANT: the *assignment* of each raw response to a domain is a
# researcher judgement call, made by reading the free text and the fixed
# category labels. What is auditable here is that the scheme is written
# down explicitly, in one place, and applied identically to every row by
# code -- not that the judgement itself is beyond dispute. A reader who
# disagrees with a specific mapping below can see exactly which one to
# contest, rather than trying to reverse-engineer an opaque manual step.
FACTOR_DOMAIN_MAP: dict[str, str] = {
    "Research and supervision": "academic",
    "Overload content of some subjects": "academic",
    "Academic workload": "academic",
    "Assignment deadlines": "academic",
    "Examination pressure": "academic",
    "Financial responsibility": "environmental",
    "Balancing responsibilities": "environmental",
    "Multiple responsibilities": "environmental",
    "Family expectations": "social",
    "Poor sleep": "physiological",
    "Career uncertainty": "psychological",
    "Career and internship uncertainty": "psychological",
    "No major factor": "not_represented",
    "Personal problems": "not_represented",
}

CHALLENGE_DOMAIN_MAP: dict[str, str] = {
    "Academic difficulties": "academic",
    "Financial concerns": "environmental",
    "Relationship issues": "social",
    "Family-related issues": "social",
    "No major challenges": "not_represented",
    "Other": "not_represented",
}

DOMAIN_ORDER = ["academic", "social", "environmental", "psychological", "physiological", "not_represented"]
DOMAIN_DISPLAY = {
    "academic": "Academic",
    "social": "Social",
    "environmental": "Environmental",
    "psychological": "Psychological",
    "physiological": "Physiological / Not represented",
    "not_represented": "Physiological / Not represented",
}


def _strip(series: pd.Series) -> pd.Series:
    """Trim whitespace from a free-text/categorical column, leaving NaN as NaN."""
    return series.apply(lambda v: v.strip() if isinstance(v, str) else v)


def _value_counts_dict(series: pd.Series) -> dict[str, int]:
    """`value_counts(dropna=False)` as a JSON-safe dict.

    A raw `float('nan')` dict key is technically not valid JSON (Python's
    `json` module will still write it as the literal `NaN`, which many
    strict JSON parsers reject) -- relabelled to the string "missing" so
    the logged experiment file is unambiguous and portable.
    """
    counts = series.value_counts(dropna=False)
    return {("missing" if pd.isna(k) else str(k)): int(v) for k, v in counts.items()}


def load_data(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load the local questionnaire CSV.

    Args:
        path: Path to the CSV.

    Returns:
        The raw dataframe, n=31.
    """
    return pd.read_csv(path)


def compute_descriptive_statistics(df: pd.DataFrame) -> dict[str, Any]:
    """Demographic and academic/sleep/exercise descriptive statistics.

    Args:
        df: The loaded local questionnaire dataframe.

    Returns:
        A JSON-serialisable dict of value-count distributions and means.
    """
    return {
        "n": int(len(df)),
        "age_group": _strip(df[COL_AGE_GROUP]).pipe(_value_counts_dict),
        "gender": _strip(df[COL_GENDER]).pipe(_value_counts_dict),
        "year_of_study": _strip(df[COL_YEAR]).pipe(_value_counts_dict),
        "study_hours_per_day": _strip(df[COL_STUDY_HOURS]).pipe(_value_counts_dict),
        "sleep_hours_per_night": _strip(df[COL_SLEEP_HOURS]).pipe(_value_counts_dict),
        "sleep_quality_1_to_5": {
            "mean": round(float(df[COL_SLEEP_QUALITY].mean()), 3),
            "distribution": df[COL_SLEEP_QUALITY].pipe(_value_counts_dict),
        },
        "exercise_frequency": _strip(df[COL_EXERCISE_FREQ]).pipe(_value_counts_dict),
    }


def code_domain(raw_value: Any, domain_map: dict[str, str]) -> str:
    """Apply the explicit coding scheme to one raw response.

    Args:
        raw_value: The raw cell value (a string, or NaN/float if blank).
        domain_map: One of `FACTOR_DOMAIN_MAP` or `CHALLENGE_DOMAIN_MAP`.

    Returns:
        A domain key from `DOMAIN_ORDER`, defaulting to "not_represented"
        for blank cells or any text not present in the coding scheme (the
        latter should not occur against the current CSV -- see the test
        that asserts every distinct raw value is covered).
    """
    if not isinstance(raw_value, str) or not raw_value.strip():
        return "not_represented"
    return domain_map.get(raw_value.strip(), "not_represented")


def build_thematic_comparison_table(df: pd.DataFrame) -> dict[str, Any]:
    """Triangulate two independently-worded stress-cause questions against
    the same five-domain coding scheme, and compare them.

    Args:
        df: The loaded local questionnaire dataframe.

    Returns:
        Per-domain counts/percentages from each question, plus a simple
        row-wise agreement rate between the two.
    """
    factor_domains = df[COL_BIGGEST_FACTOR].apply(lambda v: code_domain(v, FACTOR_DOMAIN_MAP))
    challenge_domains = df[COL_MAJOR_CHALLENGES].apply(lambda v: code_domain(v, CHALLENGE_DOMAIN_MAP))

    n = len(df)

    def _summarise(coded: pd.Series) -> dict[str, dict[str, float]]:
        display_counts: dict[str, int] = {}
        for domain in coded:
            label = DOMAIN_DISPLAY[domain]
            display_counts[label] = display_counts.get(label, 0) + 1
        return {
            label: {"count": count, "pct": round(100 * count / n, 1)}
            for label, count in display_counts.items()
        }

    agreement = (factor_domains.map(DOMAIN_DISPLAY) == challenge_domains.map(DOMAIN_DISPLAY)) | (
        # "Physiological / Not represented" is a merged display bucket for
        # two distinct underlying domain keys -- treat rows where both
        # signals land in that merged bucket as agreement, since they are
        # not distinguishable at the level this table reports.
        (factor_domains.isin(["physiological", "not_represented"]))
        & (challenge_domains.isin(["physiological", "not_represented"]))
    )

    return {
        "n": int(n),
        "biggest_factor_free_text": _summarise(factor_domains),
        "major_challenges_categorical": _summarise(challenge_domains),
        "row_wise_agreement": {
            "agreeing_respondents": int(agreement.sum()),
            "pct": round(100 * float(agreement.mean()), 1),
        },
    }


def run() -> dict[str, Any]:
    """Run the full local-data triangulation analysis.

    Returns:
        A dict with `descriptive_statistics` and `thematic_comparison`,
        ready to log and print.
    """
    df = load_data()
    return {
        "descriptive_statistics": compute_descriptive_statistics(df),
        "thematic_comparison": build_thematic_comparison_table(df),
    }


def main() -> None:
    results = run()

    log_path = log_experiment(
        experiments_dir=EXPERIMENTS_DIR,
        experiment_name="local_data_triangulation",
        # No model is trained here; `log_experiment`'s schema is reused
        # as-is (not forked into a parallel logging function) so this
        # analysis is logged identically to every training run, per
        # IMPLEMENTATION_RULES.md.
        model_name="descriptive_analysis_no_model_trained",
        hyperparameters={
            "factor_domain_coding_scheme": FACTOR_DOMAIN_MAP,
            "challenge_domain_coding_scheme": CHALLENGE_DOMAIN_MAP,
        },
        dataset_path=DATA_PATH,
        split_info={"note": "no train/test split; full-sample descriptive analysis", "n": len(load_data())},
        metrics=results,
    )

    print(f"Wrote {log_path}\n")
    print("=== Descriptive statistics ===")
    for key, value in results["descriptive_statistics"].items():
        print(f"{key}: {value}")

    print("\n=== Thematic comparison (biggest factor vs. major challenges) ===")
    comparison = results["thematic_comparison"]
    print(f"n = {comparison['n']}")
    print("\nBiggest factor (free text):")
    for label, stats in comparison["biggest_factor_free_text"].items():
        print(f"  {label}: {stats['count']} ({stats['pct']}%)")
    print("\nMajor challenges (categorical):")
    for label, stats in comparison["major_challenges_categorical"].items():
        print(f"  {label}: {stats['count']} ({stats['pct']}%)")
    print(
        f"\nRow-wise agreement between the two questions: "
        f"{comparison['row_wise_agreement']['agreeing_respondents']}/{comparison['n']} "
        f"({comparison['row_wise_agreement']['pct']}%)"
    )


if __name__ == "__main__":
    main()
