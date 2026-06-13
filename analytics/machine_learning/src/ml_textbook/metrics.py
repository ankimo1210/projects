"""Evaluation metrics.

Regression and the core classification metrics are implemented from scratch in
NumPy so the formulas are visible and verifiable; the few that are fiddly to get
right (ROC-AUC, PR-AUC) are thin wrappers around scikit-learn. Every from-scratch
metric is checked against scikit-learn in the test-suite.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Regression
# ---------------------------------------------------------------------------


def mse(y_true, y_pred) -> float:
    """Mean squared error: mean((y - yhat)^2)."""
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return float(np.mean((y_true - y_pred) ** 2))


def rmse(y_true, y_pred) -> float:
    """Root mean squared error (same units as the target)."""
    return float(np.sqrt(mse(y_true, y_pred)))


def mae(y_true, y_pred) -> float:
    """Mean absolute error: mean(|y - yhat|). Less sensitive to outliers than MSE."""
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return float(np.mean(np.abs(y_true - y_pred)))


def r2_score(y_true, y_pred) -> float:
    """Coefficient of determination R^2 = 1 - SS_res / SS_tot.

    1.0 is perfect; 0.0 means 'no better than predicting the mean'; negative is
    possible (worse than the mean).
    """
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 0.0


# ---------------------------------------------------------------------------
# Classification — counts and the rates derived from them
# ---------------------------------------------------------------------------


def confusion_matrix(y_true, y_pred, n_classes: int | None = None):
    """Integer confusion matrix C[i, j] = #(true=i, pred=j)."""
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    if n_classes is None:
        n_classes = int(max(y_true.max(initial=0), y_pred.max(initial=0))) + 1
    cm = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred, strict=True):
        cm[t, p] += 1
    return cm


def accuracy(y_true, y_pred) -> float:
    """Fraction of correct predictions. Misleading under class imbalance."""
    return float((np.asarray(y_true) == np.asarray(y_pred)).mean())


def _binary_counts(y_true, y_pred, pos_label: int = 1):
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    tp = int(np.sum((y_pred == pos_label) & (y_true == pos_label)))
    fp = int(np.sum((y_pred == pos_label) & (y_true != pos_label)))
    fn = int(np.sum((y_pred != pos_label) & (y_true == pos_label)))
    tn = int(np.sum((y_pred != pos_label) & (y_true != pos_label)))
    return tp, fp, fn, tn


def precision(y_true, y_pred, pos_label: int = 1) -> float:
    """TP / (TP + FP): of the predicted positives, how many are right."""
    tp, fp, _, _ = _binary_counts(y_true, y_pred, pos_label)
    return float(tp / (tp + fp)) if (tp + fp) else 0.0


def recall(y_true, y_pred, pos_label: int = 1) -> float:
    """TP / (TP + FN): of the actual positives, how many we caught (sensitivity)."""
    tp, _, fn, _ = _binary_counts(y_true, y_pred, pos_label)
    return float(tp / (tp + fn)) if (tp + fn) else 0.0


def f1_score(y_true, y_pred, pos_label: int = 1) -> float:
    """Harmonic mean of precision and recall."""
    p = precision(y_true, y_pred, pos_label)
    r = recall(y_true, y_pred, pos_label)
    return float(2 * p * r / (p + r)) if (p + r) else 0.0


# ---------------------------------------------------------------------------
# Ranking metrics (probabilities, not hard labels) — scikit-learn wrappers
# ---------------------------------------------------------------------------


def roc_auc(y_true, y_score) -> float:
    """Area under the ROC curve. 0.5 = random, 1.0 = perfect ranking."""
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(np.asarray(y_true), np.asarray(y_score)))


def pr_auc(y_true, y_score) -> float:
    """Area under the precision-recall curve (average precision).

    More informative than ROC-AUC when the positive class is rare, because it
    ignores the (usually huge and easy) true-negative mass.
    """
    from sklearn.metrics import average_precision_score

    return float(average_precision_score(np.asarray(y_true), np.asarray(y_score)))


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def expected_calibration_error(y_true, y_prob, n_bins: int = 10) -> float:
    """Expected Calibration Error (ECE).

    Bin predictions by confidence, then average |accuracy - confidence| over
    bins, weighted by bin size. 0 = perfectly calibrated (a predicted 0.7 really
    happens 70% of the time).
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for b in range(n_bins):
        lo, hi = bins[b], bins[b + 1]
        # First bin includes its lower edge so p == 0.0 is counted; every bin is
        # closed on the right, so the last bin includes p == 1.0.
        in_bin = (y_prob >= lo) & (y_prob <= hi) if b == 0 else (y_prob > lo) & (y_prob <= hi)
        count = int(np.sum(in_bin))
        if count == 0:
            continue
        conf = float(np.mean(y_prob[in_bin]))
        acc = float(np.mean(y_true[in_bin]))
        ece += (count / n) * abs(acc - conf)
    return float(ece)


def regression_report(y_true, y_pred) -> dict[str, float]:
    """Convenience dict of the four regression metrics."""
    return {
        "MSE": mse(y_true, y_pred),
        "RMSE": rmse(y_true, y_pred),
        "MAE": mae(y_true, y_pred),
        "R2": r2_score(y_true, y_pred),
    }


def classification_report(y_true, y_pred, pos_label: int = 1) -> dict[str, float]:
    """Convenience dict of the core binary-classification metrics."""
    return {
        "accuracy": accuracy(y_true, y_pred),
        "precision": precision(y_true, y_pred, pos_label),
        "recall": recall(y_true, y_pred, pos_label),
        "f1": f1_score(y_true, y_pred, pos_label),
    }
