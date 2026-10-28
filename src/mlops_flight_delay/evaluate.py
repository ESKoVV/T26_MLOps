from __future__ import annotations

import os  # LR8 controlled failure: unused import, expected to fail the Lint step
from collections.abc import Sequence

import numpy as np
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score


def classification_metrics(
    y_true: Sequence[int],
    probabilities: Sequence[float],
    *,
    threshold: float = 0.5,
) -> dict[str, float]:
    """Calculate binary-classification metrics after validating inputs."""
    labels = np.asarray(y_true)
    scores = np.asarray(probabilities, dtype=float)

    if labels.ndim != 1 or scores.ndim != 1:
        raise ValueError("Метки и вероятности должны быть одномерными")
    if len(labels) == 0 or len(labels) != len(scores):
        raise ValueError("Метки и вероятности должны иметь одинаковую ненулевую длину")
    if not 0.0 < threshold < 1.0:
        raise ValueError("Порог должен находиться строго между 0 и 1")
    if not np.isin(labels, [0, 1]).all():
        raise ValueError("Допустимы только бинарные метки 0 и 1")
    if len(np.unique(labels)) != 2:
        raise ValueError("Для ROC AUC нужны примеры обоих классов")
    if not np.isfinite(scores).all() or ((scores < 0.0) | (scores > 1.0)).any():
        raise ValueError("Вероятности должны быть конечными числами от 0 до 1")

    predictions = (scores >= threshold).astype(int)
    return {
        "roc_auc": float(roc_auc_score(labels, scores)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
    }
