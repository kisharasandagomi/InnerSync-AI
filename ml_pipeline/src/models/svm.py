"""SVM — distance-based, scale-sensitive, tuned via randomized search."""

from __future__ import annotations

import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import BaseCrossValidator, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC


def train_svm_with_cv(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv: BaseCrossValidator,
    random_state: int = 42,
    scoring: str = "f1_macro",
    n_iter: int = 15,
) -> RandomizedSearchCV:
    """Tune an SVM classifier via randomized search with stratified CV.

    Unlike the tree-based models, SVM relies on distances between points, so
    it is scale-sensitive and needs feature scaling. The scaler is placed
    inside a Pipeline rather than fit once on X_train up front: with a
    Pipeline, RandomizedSearchCV refits StandardScaler on each CV fold's
    training portion only, on every fold, so no fold's validation data (or
    the outer held-out test set) ever influences the scaler.

    Probability estimates (needed for ROC-AUC) come from wrapping SVC in
    `CalibratedClassifierCV` rather than `SVC(probability=True)` — the
    latter is deprecated as of scikit-learn 1.9 in favour of the former,
    which does the same Platt-scaling calibration explicitly.
    RandomizedSearchCV is used instead of GridSearchCV because that
    calibration makes each fit expensive (an internal CV of its own).

    Args:
        X_train: Training feature matrix (raw, unscaled — scaling happens
            inside the pipeline, per CV fold).
        y_train: Training target labels.
        cv: Cross-validation splitter (e.g. StratifiedKFold).
        random_state: Seed for reproducibility.
        scoring: Metric RandomizedSearchCV optimizes for during tuning.
        n_iter: Number of random hyperparameter combinations to try.

    Returns:
        The fitted RandomizedSearchCV object (`.best_estimator_`,
        `.best_params_` are available on it).
    """
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("svc", CalibratedClassifierCV(SVC(random_state=random_state), ensemble=False)),
        ]
    )
    param_distributions = [
        {
            "svc__estimator__kernel": ["rbf"],
            "svc__estimator__C": [0.1, 1, 10, 100],
            "svc__estimator__gamma": ["scale", "auto"],
        },
        {"svc__estimator__kernel": ["linear"], "svc__estimator__C": [0.1, 1, 10, 100]},
    ]
    search = RandomizedSearchCV(
        pipeline,
        param_distributions=param_distributions,
        n_iter=n_iter,
        cv=cv,
        scoring=scoring,
        random_state=random_state,
        n_jobs=-1,
    )
    search.fit(X_train, y_train)
    return search
