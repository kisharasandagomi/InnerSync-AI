"""LightGBM — tree-based, scale-invariant, tuned via randomized search."""

from __future__ import annotations

import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.model_selection import BaseCrossValidator, RandomizedSearchCV


def train_lightgbm_with_cv(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv: BaseCrossValidator,
    random_state: int = 42,
    scoring: str = "f1_macro",
    n_iter: int = 20,
) -> RandomizedSearchCV:
    """Tune a LightGBM classifier via randomized search with stratified CV.

    Tree-based and scale-invariant like Random Forest and XGBoost — trained
    on the raw, unscaled features. RandomizedSearchCV is used because the
    hyperparameter space here (4 dimensions) is larger than RF/XGBoost's.

    `LGBMClassifier` is pinned to `n_jobs=1`: LightGBM does its own internal
    multi-threading per fit, and letting every one of RandomizedSearchCV's
    parallel workers *also* spawn its own LightGBM thread pool oversubscribes
    the CPU severely (observed: a 100-fit search hanging past 30 minutes on
    a resource-constrained VM). Parallelism instead happens at the
    RandomizedSearchCV level (`n_jobs=-1`, one process per candidate/fold).

    Args:
        X_train: Training feature matrix (raw, unscaled).
        y_train: Training target labels.
        cv: Cross-validation splitter (e.g. StratifiedKFold).
        random_state: Seed for reproducibility.
        scoring: Metric RandomizedSearchCV optimizes for during tuning.
        n_iter: Number of random hyperparameter combinations to try.

    Returns:
        The fitted RandomizedSearchCV object (`.best_estimator_`,
        `.best_params_` are available on it).
    """
    param_distributions = {
        "n_estimators": [100, 200, 300],
        "max_depth": [-1, 5, 10, 20],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "num_leaves": [15, 31, 63],
    }
    search = RandomizedSearchCV(
        LGBMClassifier(random_state=random_state, verbose=-1, n_jobs=1),
        param_distributions=param_distributions,
        n_iter=n_iter,
        cv=cv,
        scoring=scoring,
        random_state=random_state,
        n_jobs=-1,
    )
    search.fit(X_train, y_train)
    return search
