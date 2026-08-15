"""Writes one JSON record per training run to ml_pipeline/experiments/, per IMPLEMENTATION_RULES.md."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


def hash_file(path: str | Path) -> str:
    """Compute the SHA-256 hex digest of a file.

    Used as a lightweight, reproducible dataset-version identifier in the
    absence of a formal data-versioning tool — if the dataset file changes,
    the hash changes, so any drift between logged experiments is detectable.

    Args:
        path: Path to the file to hash.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def log_experiment(
    experiments_dir: str | Path,
    experiment_name: str,
    model_name: str,
    hyperparameters: dict[str, Any],
    dataset_path: str | Path,
    split_info: dict[str, Any],
    metrics: dict[str, Any],
) -> Path:
    """Write a single experiment run to a timestamped JSON file.

    Args:
        experiments_dir: Directory to write the log file into.
        experiment_name: Short slug identifying this experiment.
        model_name: Class name of the model trained.
        hyperparameters: Hyperparameters used to train the model.
        dataset_path: Path to the dataset used; hashed for a version identifier.
        split_info: Train/test split configuration (test_size, stratify, etc.).
        metrics: Output of evaluate_classifier.

    Returns:
        Path to the written log file.
    """
    experiments_dir = Path(experiments_dir)
    experiments_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = Path(dataset_path)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    record = {
        "timestamp_utc": timestamp,
        "experiment_name": experiment_name,
        "model": model_name,
        "hyperparameters": _make_json_safe(hyperparameters),
        "dataset": {
            "path": str(dataset_path),
            "sha256": hash_file(dataset_path),
        },
        "split": _make_json_safe(split_info),
        "metrics": _make_json_safe(metrics),
    }

    out_path = experiments_dir / f"{timestamp}_{experiment_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    return out_path


def _make_json_safe(value: Any) -> Any:
    """Recursively convert numpy types (and any other non-JSON-safe object) for JSON serialization.

    `hyperparameters` for a Pipeline-based model (e.g. SVM's
    `Pipeline(StandardScaler(), SVC())`) includes nested estimator objects
    as values from `get_params()`, not just scalars — those fall through to
    the final `repr()` fallback below rather than crashing `json.dump`.
    """
    if isinstance(value, dict):
        return {k: _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)
