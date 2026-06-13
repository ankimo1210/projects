"""Small metric helpers used across notebooks."""

from __future__ import annotations

import numpy as np


def accuracy(y_pred, y_true) -> float:
    """Fraction of correct predictions."""
    return float((np.asarray(y_pred) == np.asarray(y_true)).mean())


def confusion_matrix(y_true, y_pred, n_classes: int | None = None):
    """Integer confusion matrix C[i, j] = #(true=i, pred=j)."""
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    if n_classes is None:
        n_classes = int(max(y_true.max(), y_pred.max())) + 1
    cm = np.zeros((n_classes, n_classes), dtype=int)
    for t, p in zip(y_true, y_pred, strict=True):
        cm[t, p] += 1
    return cm


def softmax_np(logits, axis: int = -1):
    """Numerically stable softmax for plotting next-token distributions etc."""
    logits = np.asarray(logits, dtype=float)
    z = logits - logits.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)


def count_parameters(model) -> int:
    """Total number of trainable parameters in a torch model."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
