import numpy as np
import pandas as pd
from bond_timing.g1 import count_significant, g1_passed, proxy_forecast


def test_count_significant_uses_the_holm_p_values():
    runs = [{"p_holm": {"P1": 0.01, "P2": 0.5}}, {"p_holm": {"P1": 0.04, "P2": 0.05}}]
    assert count_significant(runs, ["P1", "P2"]) == {"P1": 2, "P2": 0}
    assert count_significant(runs, ["P2"], key="p_holm") == {"P2": 0}


def test_g1_pass_rule_uses_only_the_no_signal_worlds():
    w0 = {"P1": 2, "P2": 0, "P3": 1, "P4": 2, "P5": 0}
    assert g1_passed({"W0": w0, "W2": {name: 0 for name in w0}})
    assert not g1_passed({"W0": {**w0, "P5": 3}, "W2": {name: 20 for name in w0}})


def planted(seed: int = 0) -> tuple[pd.Series, pd.Series]:
    index = pd.period_range("1980-01", "2001-12", freq="M")
    rng = np.random.default_rng(seed)
    z = pd.Series(rng.normal(size=len(index)), index=index)
    rx = 0.01 + 0.05 * z + pd.Series(rng.normal(0, 0.001, len(index)), index=index)
    return rx, z


def test_proxy_forecast_recovers_the_planted_rule():
    rx, z = planted()
    decisions = pd.period_range("2000-01", "2001-12", freq="M")
    forecast = proxy_forecast(rx, z, decisions)
    assert forecast.index.equals(decisions)
    np.testing.assert_allclose(forecast, 0.01 + 0.05 * z.reindex(decisions), atol=0.002)


def test_proxy_forecast_uses_only_completed_targets():
    rx, z = planted(1)
    rx[rx.index > pd.Period("1999-01", "M")] = 1e6  # unrealized at the 2000-01 refit
    decisions = pd.period_range("2000-01", "2000-12", freq="M")
    np.testing.assert_allclose(
        proxy_forecast(rx, z, decisions), 0.01 + 0.05 * z.reindex(decisions), atol=0.002
    )
