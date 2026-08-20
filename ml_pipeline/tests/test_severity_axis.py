"""Signed severity axis: `severity_contributions()`.

See `ml_pipeline/src/explainability/generator.py` -- collapses per-class SHAP
into `SHAP(high) - SHAP(low)`, the axis `extract_top_factors()` consumes.
"""

from __future__ import annotations

import numpy as np
import pytest

from ml_pipeline.src.explainability.generator import severity_contributions

CLASS_LABELS = [0, 1, 2]  # low, moderate, high


def test_axis_is_shap_high_minus_shap_low() -> None:
    """Direct formula check on hand-computed values, per the function's own
    documented definition: SHAP(high) - SHAP(low)."""
    shap_row = np.array(
        [
            [0.1, 0.0, -0.3],  # low=0.1, moderate=0.0, high=-0.3
            [-0.2, 0.05, 0.25],  # low=-0.2, moderate=0.05, high=0.25
        ]
    )

    result = severity_contributions(shap_row, CLASS_LABELS)

    np.testing.assert_allclose(result, [-0.3 - 0.1, 0.25 - (-0.2)])


def test_low_prediction_case_resolves_to_all_easing() -> None:
    """Synthetic input representative of a low-stress prediction: SHAP(low)
    strongly positive, SHAP(high) near zero or negative for every feature.
    Per the module docstring, this must resolve to all-negative (easing)."""
    shap_row = np.array(
        [
            [0.30, 0.10, -0.10],
            [0.25, 0.05, -0.05],
            [0.15, 0.00, 0.00],
        ]
    )

    result = severity_contributions(shap_row, CLASS_LABELS)

    assert np.all(result < 0)
    np.testing.assert_allclose(result, [-0.40, -0.30, -0.15])


def test_high_prediction_case_resolves_to_all_raising() -> None:
    """Synthetic input representative of a high-stress prediction: SHAP(high)
    strongly positive, SHAP(low) negative for every feature. Must resolve to
    all-positive (raising)."""
    shap_row = np.array(
        [
            [-0.20, 0.00, 0.30],
            [-0.10, 0.05, 0.25],
            [-0.05, 0.00, 0.10],
        ]
    )

    result = severity_contributions(shap_row, CLASS_LABELS)

    assert np.all(result > 0)
    np.testing.assert_allclose(result, [0.50, 0.35, 0.15])


def test_moderate_prediction_case_gives_a_genuine_mix() -> None:
    """Synthetic input representative of a moderate prediction: neither
    extreme dominates, so some features should come out raising and others
    easing -- the "genuine mix" the docstring says only this axis produces
    at mid-scale."""
    shap_row = np.array(
        [
            [0.20, 0.00, -0.10],  # -> -0.30 (easing)
            [-0.15, 0.05, 0.20],  # -> +0.35 (raising)
            [0.05, 0.00, -0.02],  # -> -0.07 (easing)
        ]
    )

    result = severity_contributions(shap_row, CLASS_LABELS)

    assert np.any(result > 0)
    assert np.any(result < 0)
    np.testing.assert_allclose(result, [-0.30, 0.35, -0.07])


def test_class_label_order_does_not_affect_the_result() -> None:
    """Columns are looked up by label, not fixed position: permuting both
    the array's columns and `class_labels` together (so they still describe
    the same per-class values, just reordered) must give the same answer as
    the canonical [0, 1, 2] layout."""
    canonical_row = np.array([[0.1, 0.0, -0.3]])  # columns: low, moderate, high

    canonical = severity_contributions(canonical_row, [0, 1, 2])
    # Same data, columns permuted to [high, moderate, low] with labels to match.
    permuted_row = np.array([[-0.3, 0.0, 0.1]])
    permuted = severity_contributions(permuted_row, [2, 1, 0])

    np.testing.assert_allclose(canonical, permuted)


def test_rejects_non_2d_input() -> None:
    with pytest.raises(ValueError, match="2-D"):
        severity_contributions(np.array([0.1, 0.2, 0.3]), CLASS_LABELS)


def test_rejects_missing_class_label() -> None:
    shap_row = np.array([[0.1, 0.0, -0.3]])
    with pytest.raises(ValueError, match="not in"):
        severity_contributions(shap_row, [0, 1], high_class=2)
