"""Tier-3 (neural) and Tier-4 (time-series) model tests.

The MLP recovers a learnable relationship out-of-sample through the same harness
as Tiers 0-2; the classical forecasters do what they claim; the foundation-model
loader fails clearly (not silently) when its optional backend is absent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from irp import backtest as B
from irp import models as MD


def _panels(n=400, k=5, seed=1):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2018-01-01", periods=n)
    assets = [f"A{i}" for i in range(k)]
    f1 = pd.DataFrame(rng.normal(0, 1, (n, k)), index=idx, columns=assets)
    f2 = pd.DataFrame(rng.normal(0, 1, (n, k)), index=idx, columns=assets)
    label = (
        1.5 * f1 - 0.8 * f2 + pd.DataFrame(rng.normal(0, 0.1, (n, k)), index=idx, columns=assets)
    )
    return {"f1": f1, "f2": f2}, label


# --- Tier 3: MLP --------------------------------------------------------------
def test_mlp_recovers_signal_out_of_sample():
    feats, label = _panels()
    X, y = MD.make_design(feats, label)
    folds = B.walk_forward(label.index, train=150, test=50, horizon=1, embargo=1)
    pred = MD.walk_forward_predict(
        lambda: MD.mlp(hidden_layer_sizes=(32,), max_iter=300), X, y, folds
    )
    assert not pred.empty
    truth = y.loc[pred.index]
    assert truth.corr(pred) > 0.8  # non-linear net recovers the (linear) signal OOS


def test_mlp_is_a_model():
    assert isinstance(MD.mlp(), MD.Model)


# --- Tier 4: classical forecasters --------------------------------------------
def test_seasonal_naive_repeats_last_season():
    y = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    f = MD.SeasonalNaiveForecaster(season=2).fit(y)
    # last season is [5, 6]; horizon 5 -> 5,6,5,6,5
    assert f.predict(5).tolist() == [5.0, 6.0, 5.0, 6.0, 5.0]


def test_seasonal_naive_season_one_is_persistence():
    y = pd.Series([10.0, 20.0, 30.0])
    assert MD.SeasonalNaiveForecaster(season=1).fit(y).predict(3).tolist() == [30.0, 30.0, 30.0]


def test_ar_forecaster_recovers_ar1_decay():
    # y_t = 0.8 * y_{t-1}  -> AR(1) should forecast ~0.8 * last, decaying toward 0
    v = [1.0]
    for _ in range(60):
        v.append(0.8 * v[-1])
    y = pd.Series(v)
    f = MD.ARForecaster(p=1).fit(y)
    pred = f.predict(3)
    assert pred[0] == pytest.approx(0.8 * v[-1], rel=0.05)
    assert abs(pred[2]) < abs(pred[0])  # decays


def test_foundation_loader_raises_clearly_without_backend():
    # chronos/torch are optional and not installed -> clear, actionable ImportError
    with pytest.raises(ImportError, match="chronos"):
        MD.load_foundation("chronos")
    with pytest.raises(KeyError):
        MD.load_foundation("not_a_model")


def test_chronos_adapter_wiring_with_fake_backend(monkeypatch):
    """Verify the Chronos adapter (load + fit + median extraction) without the
    heavy torch/chronos install, by injecting fake backend modules."""
    import sys
    import types

    fake_torch = types.ModuleType("torch")
    fake_torch.tensor = lambda x, **k: x
    fake_torch.cuda = types.SimpleNamespace(is_available=lambda: False)

    fake_chronos = types.ModuleType("chronos")

    class _FakePipeline:
        @classmethod
        def from_pretrained(cls, name, **kw):
            return cls()

        def predict(self, context, prediction_length=1):
            # [num_series=1, num_samples=3, horizon] — median of {1,2,3} is 2
            step = [1.0] * prediction_length
            return np.array([[step, [2.0] * prediction_length, [3.0] * prediction_length]])

    fake_chronos.ChronosPipeline = _FakePipeline
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setitem(sys.modules, "chronos", fake_chronos)

    fc = MD.load_foundation("chronos")
    assert isinstance(fc, MD.Forecaster)
    fc.fit(pd.Series([10.0, 11.0, 12.0]))
    pred = fc.predict(2)
    assert pred.tolist() == [2.0, 2.0]  # median sample-path
