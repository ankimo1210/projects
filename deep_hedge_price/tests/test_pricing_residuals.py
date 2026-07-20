from __future__ import annotations

import numpy as np

from deep_hedge_price.pricing_data import black_scholes_labels
from deep_hedge_price.pricing_residuals import compare_heston_bsm_residual


def test_bsm_residual_comparison_uses_common_rows_and_reports_negative_results():
    rng = np.random.default_rng(9)
    train = rng.uniform(
        [0.7, 0.05, -0.01, 0.0, 0.10],
        [1.3, 1.5, 0.08, 0.05, 0.60],
        size=(96, 5),
    )
    test = rng.uniform(
        [0.7, 0.05, -0.01, 0.0, 0.10],
        [1.3, 1.5, 0.08, 0.05, 0.60],
        size=(32, 5),
    )

    def synthetic_heston(rows):
        baseline = black_scholes_labels(rows)["price"]
        residual = 0.003 * rows[:, 0] * rows[:, 1] + 0.001 * rows[:, 4] ** 2
        return baseline + residual

    result = compare_heston_bsm_residual(
        train,
        test,
        n_terms=16,
        teacher_function=synthetic_heston,
    )
    assert result["train_rows"] == 96 and result["test_rows"] == 32
    assert result["residual_improved"] is True
    assert result["bsm_residual_mae"] < result["raw_price_mae"]
    assert result["adopted"] == "bsm_residual"
