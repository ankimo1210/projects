from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LabelingResult:
    labels: np.ndarray
    percentage_change: np.ndarray
    threshold: float
    smoothing_length: int
    horizon: int


def author_repository_labels(
    orderbook: np.ndarray, *, smoothing_length: int, horizon: int
) -> LabelingResult:
    """Exact NumPy window endpoints and threshold from utils_data.py:127-160."""

    matrix = np.asarray(orderbook, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] < 3:
        raise ValueError("orderbook must contain ask at column 0 and bid at column 2")
    if smoothing_length <= 0 or horizon <= 0:
        raise ValueError("smoothing_length and horizon must be positive")
    length = min(smoothing_length, horizon)
    ask_windows = np.lib.stride_tricks.sliding_window_view(matrix[:, 0], length)
    bid_windows = np.lib.stride_tricks.sliding_window_view(matrix[:, 2], length)
    previous_mid = ((ask_windows[:-horizon] + bid_windows[:-horizon]) / 2).mean(axis=1)
    future_mid = ((ask_windows[horizon:] + bid_windows[horizon:]) / 2).mean(axis=1)
    change = (future_mid - previous_mid) / previous_mid
    threshold = float(np.abs(change).mean() / 2)
    labels = np.where(change < -threshold, 2, np.where(change > threshold, 0, 1))
    return LabelingResult(labels, change, threshold, length, horizon)
