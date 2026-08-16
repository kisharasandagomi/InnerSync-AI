"""Experiment B: TF-IDF + Logistic Regression on Dreaddit's own text and label.

Dreaddit (Turcan & McKeown, 2019) is a Reddit corpus with a binary stress
label, used here as the sole source for the NLP-only ablation arm. It shares
no subjects with the Kaggle questionnaire dataset used for the deployed model
— see the module docstring in `ml_pipeline/src/nlp/__init__.py` and
`docs/research/methodology.md` for why that means Experiment A and Experiment
B results must never be placed in one comparison table as if directly
comparable.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import BaseCrossValidator, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer


def load_dreaddit(train_path: str, test_path: str) -> tuple[
    pd.Series, pd.Series, pd.Series, pd.Series
]:
    """Load Dreaddit using its own official train/test split.

    The split shipped with the dataset is used as-is rather than re-splitting
    from a pooled file, so results stay comparable to the published Dreaddit
    benchmark rather than to an arbitrary re-split of this project's own
    making.

    Args:
        train_path: Path to `dreaddit-train.csv`.
        test_path: Path to `dreaddit-test.csv`.

    Returns:
        `(X_train_text, y_train, X_test_text, y_test)`.
    """
    train = pd.read_csv(train_path)
    test = pd.read_csv(test_path)
    return train["text"], train["label"], test["text"], test["label"]


def train_tfidf_logreg_with_cv(
    X_train_text: Sequence[str],
    y_train: Sequence[int],
    cv: BaseCrossValidator,
    random_state: int = 42,
    scoring: str = "f1_macro",
) -> GridSearchCV:
    """Tune a TF-IDF + Logistic Regression pipeline via grid search.

    Mirrors the pattern used for every deployed-model candidate in
    `ml_pipeline/src/models/` (stratified CV, `f1_macro` tuning objective,
    `GridSearchCV` for a grid this size) — for consistency of method between
    the questionnaire and text pipelines, not because this feeds the deployed
    model.

    Args:
        X_train_text: Raw post text.
        y_train: Binary stress label (Dreaddit's own).
        cv: Cross-validation splitter (e.g. StratifiedKFold), applied to the
            training split only.
        random_state: Seed for reproducibility.
        scoring: Metric GridSearchCV optimizes for during tuning.

    Returns:
        The fitted GridSearchCV object.
    """
    pipeline = Pipeline(
        [
            ("tfidf", TfidfVectorizer(stop_words="english")),
            ("logreg", LogisticRegression(max_iter=1000, random_state=random_state)),
        ]
    )
    param_grid = {
        "tfidf__max_features": [3000, 5000, 10000],
        "tfidf__ngram_range": [(1, 1), (1, 2)],
        "logreg__C": [0.1, 1.0, 10.0],
    }
    search = GridSearchCV(
        pipeline, param_grid=param_grid, cv=cv, scoring=scoring, n_jobs=-1
    )
    search.fit(X_train_text, y_train)
    return search


def evaluate_binary_classifier(
    y_true: Sequence[int],
    y_pred: Sequence[int],
    y_score_positive: np.ndarray | None = None,
    labels: Sequence[int] = (0, 1),
) -> dict[str, float | np.ndarray]:
    """Compute the standard metric set for a binary classifier.

    Deliberately **not** `ml_pipeline.src.evaluation.metrics.evaluate_classifier`
    reused directly: that function's ROC-AUC path calls
    `roc_auc_score(..., multi_class="ovr")`, which requires an
    `(n_samples, n_classes)` score array and raises `ValueError: y should be a
    1d array` when given binary data (confirmed by hand before writing this).
    That function is also what `03_ModelTraining.ipynb` uses to evaluate the
    deployed v2 model — changing its behaviour to accommodate binary input was
    out of scope and risked altering already-verified multiclass results.
    This is a separate, binary-safe implementation with the same metric names
    and shape wherever the two overlap, so the two are easy to read side by
    side despite not sharing code.

    Args:
        y_true: Ground-truth labels.
        y_pred: Predicted labels.
        y_score_positive: Predicted probability of the positive class (label
            1), e.g. `model.predict_proba(X)[:, 1]`. If given, ROC-AUC is
            included.
        labels: Class label ordering for the confusion matrix.

    Returns:
        Dict with accuracy, balanced_accuracy, precision_macro, recall_macro,
        f1_macro, confusion_matrix, and roc_auc if `y_score_positive` was given.
    """
    metrics: dict[str, float | np.ndarray] = {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=list(labels)),
    }
    if y_score_positive is not None:
        metrics["roc_auc"] = roc_auc_score(y_true, y_score_positive)
    return metrics
