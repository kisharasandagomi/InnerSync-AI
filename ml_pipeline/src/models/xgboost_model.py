"""XGBoost — tree-based, scale-invariant, tuned via grid search."""

from __future__ import annotations

import pandas as pd
from sklearn.model_selection import BaseCrossValidator, GridSearchCV
from xgboost import XGBClassifier


def train_xgboost_with_cv(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    cv: BaseCrossValidator,
    random_state: int = 42,
    scoring: str = "f1_macro",
) -> GridSearchCV:
    """Tune an XGBoost classifier via grid search with stratified CV.

    Tree-based and scale-invariant like Random Forest — trained on the raw,
    unscaled features. XGBoost's sklearn API auto-detects the multi-class
    setting (3 classes here) and configures its objective accordingly.

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
        "max_depth": [3, 5, 7],
        "learning_rate": [0.01, 0.1, 0.2],
    }
    search = GridSearchCV(
        XGBClassifier(eval_metric="mlogloss", random_state=random_state),
        param_grid=param_grid,
        cv=cv,
        scoring=scoring,
        n_jobs=-1,
    )
    search.fit(X_train, y_train)
    return search
