"""Logistic Regression baseline — the reference point every comparative model is judged against."""

from __future__ import annotations

import pandas as pd
from sklearn.linear_model import LogisticRegression


def train_logistic_regression_baseline(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int = 42,
    max_iter: int = 1000,
) -> LogisticRegression:
    """Fit a Logistic Regression baseline classifier.

    No scaling or regularization tuning is applied here — this is
    deliberately the simplest defensible baseline, fit on the raw features.
    `max_iter` is raised above scikit-learn's default of 100 because
    unscaled multi-class features can need more iterations to converge;
    if convergence is still not reached, scikit-learn raises a
    ConvergenceWarning rather than failing silently.

    Args:
        X_train: Training feature matrix.
        y_train: Training target labels.
        random_state: Seed for reproducibility.
        max_iter: Maximum solver iterations.

    Returns:
        The fitted LogisticRegression model.
    """
    model = LogisticRegression(max_iter=max_iter, random_state=random_state)
    model.fit(X_train, y_train)
    return model
