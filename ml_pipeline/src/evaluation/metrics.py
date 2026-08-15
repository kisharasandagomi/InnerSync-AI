"""Classification metrics shared across every candidate model, so results are directly comparable."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_classifier(
    y_true: Sequence[int],
    y_pred: Sequence[int],
    y_score: np.ndarray | None = None,
    labels: Sequence[int] | None = None,
) -> dict[str, float | np.ndarray]:
    """Compute the standard metric set required for every model comparison.

    Precision/recall/F1 are macro-averaged: with a 3-class, near-balanced
    target, macro averaging weights each class equally rather than letting
    the majority class dominate, which matters for an early-warning system
    where the minority high-stress class is the one that counts most.

    Args:
        y_true: Ground-truth labels.
        y_pred: Predicted labels.
        y_score: Optional predicted class probabilities, shape
            (n_samples, n_classes), e.g. from `model.predict_proba(X)`. If
            given, one-vs-rest macro-averaged ROC-AUC is included.
        labels: Optional explicit class ordering for the confusion matrix
            and ROC-AUC (must match the column order of y_score).

    Returns:
        Dict with accuracy, balanced_accuracy, precision_macro, recall_macro,
        f1_macro, confusion_matrix (rows = true label, columns = predicted
        label), and roc_auc_macro_ovr if y_score was provided.

    Note:
        `balanced_accuracy` is by definition macro-averaged recall, so it is
        expected to equal `recall_macro` exactly. Both are reported because
        CLAUDE.md requires balanced accuracy explicitly in every model
        comparison; the redundancy is intentional, not an error.
    """
    metrics: dict[str, float | np.ndarray] = {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels),
    }
    if y_score is not None:
        metrics["roc_auc_macro_ovr"] = roc_auc_score(
            y_true, y_score, multi_class="ovr", average="macro", labels=labels
        )
    return metrics


def confusion_matrix_to_frame(cm: np.ndarray, labels: Sequence[int]) -> pd.DataFrame:
    """Label a raw confusion matrix array for display.

    Args:
        cm: Confusion matrix as returned by evaluate_classifier.
        labels: Class labels in the same order used to compute cm.

    Returns:
        DataFrame with true-label rows and predicted-label columns.
    """
    index = [f"true_{label}" for label in labels]
    columns = [f"pred_{label}" for label in labels]
    return pd.DataFrame(cm, index=index, columns=columns)
