"""Loads the trained artifact and produces predictions plus SHAP attributions.

**ADR-001 boundary.** This module only *loads* artifacts produced by
`ml_pipeline/`. It contains no `fit()`, `.train()`, `GridSearchCV`, or any other
training call, and must never acquire one. If a change here appears to require
training, that logic belongs in `ml_pipeline/src/` and should be exported as a
new versioned artifact instead.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Sequence

import joblib
import numpy as np
import shap

from app.core.config import get_settings
from ml_pipeline.src.explainability import severity_contributions


class ArtifactError(RuntimeError):
    """Raised when a required model artifact is missing or inconsistent."""


class StressPredictor:
    """Wraps the trained model, its schema, and its SHAP explainer.

    Attributes:
        feature_order: Feature names in the exact positional order the model was
            fitted with. Order matters — scikit-learn models are positional, so a
            reordered vector silently yields wrong predictions rather than an
            error.
        class_labels: Ordered class labels.
        model_version: Version string from the schema.
    """

    def __init__(self, artifacts_dir: Path, model_filename: str) -> None:
        """Load model, feature schema and SHAP config from disk.

        Args:
            artifacts_dir: Directory holding the versioned artifacts.
            model_filename: Model artifact filename.

        Raises:
            ArtifactError: If a required artifact is missing, or the model and
                schema disagree about the feature set.
        """
        model_path = artifacts_dir / model_filename
        schema_path = artifacts_dir / "feature_schema.json"
        shap_config_path = artifacts_dir / "shap_config.json"

        for path in (model_path, schema_path, shap_config_path):
            if not path.exists():
                raise ArtifactError(
                    f"Required artifact missing: {path}. Model binaries are gitignored; "
                    "run ml_pipeline/notebooks/03_ModelTraining.ipynb to regenerate."
                )

        self._model = joblib.load(model_path)
        self._schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self._shap_config = json.loads(shap_config_path.read_text(encoding="utf-8"))

        self.feature_order: list[str] = [
            f["name"] for f in sorted(self._schema["features"], key=lambda d: d["position"])
        ]
        self.class_labels: list[int] = [int(c) for c in self._schema["target"]["classes"]]
        self.class_meaning: dict[str, str] = self._schema["target"]["class_meaning"]
        self.model_version: str = str(self._schema["model_version"])

        fitted_features = list(getattr(self._model, "feature_names_in_", self.feature_order))
        if fitted_features != self.feature_order:
            raise ArtifactError(
                "feature_schema.json does not match the fitted model's features.\n"
                f"  schema: {self.feature_order}\n  model:  {fitted_features}"
            )

        self._explainer = shap.TreeExplainer(self._model)

    def predict(self, feature_values: Sequence[float]) -> dict:
        """Predict a stress class and explain it, for one student.

        Args:
            feature_values: Values in `feature_order` order.

        Returns:
            Dict with `predicted_class`, `probabilities` (label -> probability),
            `severity` (per-feature signed contributions toward higher stress),
            and `feature_order`.

        Raises:
            ValueError: If the wrong number of features is supplied.
        """
        if len(feature_values) != len(self.feature_order):
            raise ValueError(
                f"Expected {len(self.feature_order)} features "
                f"({self.feature_order}); got {len(feature_values)}"
            )

        row = np.asarray(feature_values, dtype=float).reshape(1, -1)
        probabilities = self._model.predict_proba(row)[0]
        predicted_class = int(self._model.classes_[int(np.argmax(probabilities))])

        shap_values = self._explainer.shap_values(row)  # (1, n_features, n_classes)
        severity = severity_contributions(shap_values[0], self.class_labels)

        return {
            "predicted_class": predicted_class,
            "probabilities": {
                str(int(label)): float(p)
                for label, p in zip(self._model.classes_, probabilities)
            },
            "severity": severity,
            "feature_order": self.feature_order,
            "model_version": self.model_version,
        }


@lru_cache
def get_predictor() -> StressPredictor:
    """Return the process-wide predictor, loading artifacts once.

    Returns:
        The cached `StressPredictor`.
    """
    settings = get_settings()
    return StressPredictor(settings.artifacts_dir, settings.model_filename)
