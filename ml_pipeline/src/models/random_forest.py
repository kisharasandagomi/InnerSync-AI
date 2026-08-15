"""Random Forest — tree-based, scale-invariant, tuned via grid search."""

from __future__ import annotations

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import BaseCrossValidator, GridSearchCV


def train_random_forest_with_cv(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv: BaseCrossValidator,
    random_state: int = 42,
    scoring: str = "f1_macro",
) -> GridSearchCV:
    """Tune a Random Forest classifier via grid search with stratified CV.

    Random Forest splits on feature thresholds, not distances or gradients,
    so it is scale-invariant — trained on the raw, unscaled features, same
    as the Logistic Regression baseline and the other tree-based models.

    Args:
        X_train: Training feature matrix (raw, unscaled).
        y_train: Training target labels.
        cv: Cross-validation splitter (e.g. StratifiedKFold).
        random_state: Seed for reproducibility.
        scoring: Metric GridSearchCV optimizes for during tuning.

    Returns:
        The fitted GridSearchCV object (`.best_estimator_`, `.best_params_`
        are available on it).
    """
    param_grid = {
        "n_estimators": [100, 200],
        "max_depth": [None, 10, 20],
        "min_samples_split": [2, 5],
        "min_samples_leaf": [1, 2],
    }
    search = GridSearchCV(
        RandomForestClassifier(random_state=random_state),
        param_grid=param_grid,
        cv=cv,
        scoring=scoring,
        n_jobs=-1,
    )
    search.fit(X_train, y_train)
    return search
