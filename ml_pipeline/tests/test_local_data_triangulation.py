"""Regression checks for local_data_triangulation.py.

These guard that the numbers already written up in the dissertation stay
correct if the CSV or the script ever changes -- they are not a proof that
the qualitative domain-coding judgement itself is correct, which is a
researcher call documented in the script, not something a test can verify.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ml_pipeline"))

from src.evaluation.local_data_triangulation import (  # noqa: E402
    CHALLENGE_DOMAIN_MAP,
    COL_BIGGEST_FACTOR,
    COL_MAJOR_CHALLENGES,
    FACTOR_DOMAIN_MAP,
    build_thematic_comparison_table,
    code_domain,
    compute_descriptive_statistics,
    load_data,
)

DATA_PATH = REPO_ROOT / "ml_pipeline" / "datasets" / "local_validation" / "student_responses.csv"


@pytest.fixture(scope="module")
def df():
    if not DATA_PATH.exists():
        pytest.skip(f"local validation CSV not present at {DATA_PATH}")
    return load_data(DATA_PATH)


def test_runs_without_error_against_the_checked_in_csv(df) -> None:
    """The basic contract: the script's functions run end-to-end against
    the real, checked-in CSV without raising."""
    stats = compute_descriptive_statistics(df)
    comparison = build_thematic_comparison_table(df)
    assert stats["n"] == 31
    assert comparison["n"] == 31


def test_sample_size_is_31(df) -> None:
    assert len(df) == 31


def test_every_distinct_raw_value_is_covered_by_the_coding_scheme(df) -> None:
    """Every real, non-blank value seen in the CSV must have an explicit
    entry in the coding dictionary -- an uncovered value would silently
    fall into "not_represented" via code_domain's default, which is correct
    behaviour for genuinely blank/vague responses but would hide a typo or
    a new response value introduced by a future data refresh."""
    for value in df[COL_BIGGEST_FACTOR].dropna():
        stripped = value.strip()
        if stripped:
            assert stripped in FACTOR_DOMAIN_MAP, f"uncoded biggest-factor value: {stripped!r}"

    for value in df[COL_MAJOR_CHALLENGES].dropna():
        stripped = value.strip()
        if stripped:
            assert stripped in CHALLENGE_DOMAIN_MAP, f"uncoded major-challenge value: {stripped!r}"


def test_academic_is_the_largest_domain_in_both_questions(df) -> None:
    """Regression check matching the published finding: Academic dominates
    both the free-text and categorical stress-cause questions at 58.1%."""
    comparison = build_thematic_comparison_table(df)
    assert comparison["biggest_factor_free_text"]["Academic"]["count"] == 18
    assert comparison["biggest_factor_free_text"]["Academic"]["pct"] == pytest.approx(58.1, abs=0.05)
    assert comparison["major_challenges_categorical"]["Academic"]["count"] == 18
    assert comparison["major_challenges_categorical"]["Academic"]["pct"] == pytest.approx(58.1, abs=0.05)


def test_row_wise_agreement_between_the_two_questions(df) -> None:
    comparison = build_thematic_comparison_table(df)
    assert comparison["row_wise_agreement"]["agreeing_respondents"] == 20
    assert comparison["row_wise_agreement"]["pct"] == pytest.approx(64.5, abs=0.05)


def test_code_domain_defaults_blank_to_not_represented() -> None:
    assert code_domain(None, FACTOR_DOMAIN_MAP) == "not_represented"
    assert code_domain(float("nan"), FACTOR_DOMAIN_MAP) == "not_represented"
    assert code_domain("   ", FACTOR_DOMAIN_MAP) == "not_represented"


def test_sleep_quality_mean_matches_published_figure(df) -> None:
    stats = compute_descriptive_statistics(df)
    assert stats["sleep_quality_1_to_5"]["mean"] == pytest.approx(2.871, abs=0.005)
