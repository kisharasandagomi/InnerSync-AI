"""Regression checks for phase8_survey_analysis.py.

Guards that the SUS score and usefulness means already written up in the
dissertation stay correct if the CSVs or the script ever change -- not a
correctness proof of the survey instrument or the 9-item modification
decision itself, both of which are documented, reviewed research choices.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ml_pipeline"))

from src.evaluation.phase8_survey_analysis import (  # noqa: E402
    compute_sus_scores,
    compute_technical_support_item,
    load_part1,
    load_part2,
    run,
)

PART1_PATH = REPO_ROOT / "docs" / "research" / "phase8_evaluation" / "survey_part1.csv"
PART2_PATH = REPO_ROOT / "docs" / "research" / "phase8_evaluation" / "survey_part2_followup.csv"


@pytest.fixture(scope="module")
def part1():
    if not PART1_PATH.exists():
        pytest.skip(f"Phase 8 survey CSV not present at {PART1_PATH}")
    return load_part1(PART1_PATH)


@pytest.fixture(scope="module")
def part2():
    if not PART2_PATH.exists():
        pytest.skip(f"Phase 8 follow-up CSV not present at {PART2_PATH}")
    return load_part2(PART2_PATH)


def test_runs_without_error_against_the_checked_in_csvs() -> None:
    """The basic contract: the full analysis runs end-to-end against the
    real, checked-in CSVs without raising."""
    if not (PART1_PATH.exists() and PART2_PATH.exists()):
        pytest.skip("Phase 8 survey CSVs not present")
    results = run()
    assert results["n_part1"] == 7
    assert results["n_part2"] == 7


def test_sample_sizes_are_seven(part1, part2) -> None:
    assert len(part1) == 7
    assert len(part2) == 7


def test_sus_uses_nine_items_not_ten(part1) -> None:
    """The documented 9-item modification: confirms the scoring config
    itself, not just the resulting number, so a future edit that
    accidentally restores a 10-item/2.5 multiplier is caught directly."""
    sus = compute_sus_scores(part1)
    assert sus["n_items"] == 9
    assert sus["multiplier"] == pytest.approx(100 / 36, abs=1e-6)


def test_sus_mean_matches_published_figure_exactly(part1) -> None:
    """The regression check this task exists for: SUS mean = 80.6, matching
    the figure already reported (previously computed outside the repo)."""
    sus = compute_sus_scores(part1)
    assert sus["mean"] == 80.6


def test_sus_median_and_spread(part1) -> None:
    sus = compute_sus_scores(part1)
    assert sus["median"] == 80.6
    assert sus["min"] == pytest.approx(72.2, abs=0.05)
    assert sus["max"] == pytest.approx(86.1, abs=0.05)


def test_excluded_technical_support_item_is_reported_not_dropped(part2) -> None:
    """The SUS item excluded from the 9-item total must still be surfaced
    somewhere, not silently discarded."""
    item = compute_technical_support_item(part2)
    assert item["mean_1_to_5"] == 1.0
    assert item["distribution"] == {"1": 7}


def test_explanation_usefulness_pooled_mean() -> None:
    if not PART1_PATH.exists():
        pytest.skip("Phase 8 survey CSV not present")
    results = run()
    assert results["explanation_usefulness"]["pooled_mean"] == pytest.approx(4.14, abs=0.01)


def test_recommendation_usefulness_pooled_mean() -> None:
    if not (PART1_PATH.exists() and PART2_PATH.exists()):
        pytest.skip("Phase 8 survey CSVs not present")
    results = run()
    assert results["recommendation_usefulness"]["pooled_mean"] == pytest.approx(3.93, abs=0.01)


def test_overall_rating_is_perfect_across_respondents() -> None:
    if not PART1_PATH.exists():
        pytest.skip("Phase 8 survey CSV not present")
    results = run()
    assert results["overall_rating_1_to_5"]["mean"] == 5.0
