from __future__ import annotations

import numpy as np
import torch

from deep_hedge_price.pricing_evaluation import _hard_report, bucket_metrics


def test_bucket_metrics_keep_moneyness_and_maturity_visible():
    inputs = np.array(
        [
            [0.8, 0.1, 0.0, 0.0, 0.2],
            [1.0, 0.5, 0.0, 0.0, 0.2],
            [1.2, 1.5, 0.0, 0.0, 0.2],
        ]
    )
    target = np.array([0.01, 0.10, 0.25])
    metrics = bucket_metrics(inputs, target + 0.001, target)
    assert set(metrics) == {"deep_otm", "near_atm", "deep_itm", "short", "medium", "long"}
    assert all(value["n"] == 1 for value in metrics.values())
    assert all(np.isclose(value["mae"], 0.001) for value in metrics.values())


def test_main_hard_report_covers_every_applicable_check_and_discloses_derived_put():
    class LinearCall(torch.nn.Module):
        def forward(self, inputs):
            return (0.5 + 0.01 * inputs[:, 1]) * inputs[:, 0]

    report = _hard_report(LinearCall(), torch.device("cpu"))
    expected = {
        "price_bounds",
        "put_call_parity",
        "strike_monotonicity",
        "strike_convexity",
        "calendar_monotonicity",
        "spot_monotonicity",
        "nonnegative_gamma",
        "greek_consistency",
    }

    assert report["arbitrage_free"]
    assert report["check_set_complete"]
    assert set(report["applicable_checks"]) == expected
    assert {item["name"] for item in report["checks"]} == expected
    assert report["metadata"] == {
        "option_policy": "call_only",
        "put_call_parity_put_source": "derived_from_call",
        "put_call_parity_is_identity_by_construction": True,
    }
