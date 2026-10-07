"""RB-F05 CPU learner: physical delta, train-only scaling, budget and bounds."""

import numpy as np
import pytest
from hullkit import _digital_teachers as dt

from deep_hedge_price import _digital_dml as dml


def fixture():
    """A small smooth training fixture, distinct from the research test grid."""
    inputs = np.array([[s, t] for s in [85, 95, 105, 115] for t in [0.1, 0.5, 1.5]])
    price, delta = dt.analytic(inputs[:, 0], 100, 0.03, 0.2, inputs[:, 1])
    return inputs, price, delta


def test_normalization_uses_training_values_and_physical_units():
    x, price, delta = fixture()
    scale = dml.normalization(x, price, delta)
    features = np.column_stack([x[:, 0], np.log(x[:, 1])])
    assert np.allclose(scale["mean"], features.mean(axis=0))
    assert np.allclose(scale["std"], features.std(axis=0))
    assert scale["price_scale"] == pytest.approx(price.std())
    assert scale["delta_scale"] == pytest.approx(np.sqrt(np.mean(delta**2)))


@pytest.mark.parametrize("differential", [False, True])
def test_cpu_training_improves_objective_and_predicts_physical_delta(differential):
    x, price, delta = fixture()
    fit = dml.train(x, price, delta, seed=21, dml=differential, budget_s=5, max_updates=80)
    values, greeks = dml.predict(fit, x)
    assert fit.stats["updates"] == 80
    assert fit.stats["final_loss"] < fit.stats["initial_loss"]
    assert np.all(np.isfinite(values)) and np.all(np.isfinite(greeks))
    assert np.all((values >= 0) & (values <= np.exp(-0.03 * x[:, 1])))
    h = 1e-3
    plus, minus = x.copy(), x.copy()
    plus[:, 0] += h
    minus[:, 0] -= h
    central = (dml.predict(fit, plus)[0] - dml.predict(fit, minus)[0]) / (2 * h)
    assert np.allclose(greeks, central, rtol=1e-6, atol=1e-10)
    assert fit.stats["training_s"] > 0
    assert fit.stats["teacher_s"] == 0


def test_teacher_time_is_charged_and_budget_cannot_start_exhausted():
    x, price, delta = fixture()
    with pytest.raises(ValueError, match="budget"):
        dml.train(x, price, delta, seed=1, dml=True, budget_s=0.1, teacher_s=0.2)
    fit = dml.train(x, price, delta, seed=1, dml=False, budget_s=5, teacher_s=0.4, max_updates=2)
    assert fit.stats["teacher_and_training_s"] == pytest.approx(0.4 + fit.stats["training_s"])


def test_constant_feature_scale_is_safe_and_negative_maturity_rejected():
    x, price, delta = fixture()
    x[:, 1] = 1
    scale = dml.normalization(x, price, delta)
    assert np.all(scale["std"] > 0)
    x[0, 1] = -1
    with pytest.raises(ValueError):
        dml.normalization(x, price, delta)
