"""Torch-free saved-weight replay, price interpolation and serving policy."""

from __future__ import annotations

import numpy as np
from scipy.interpolate import CubicHermiteSpline

CONTRACT = {"strike": 100.0, "barrier": 120.0, "rate": 0.03, "volatility": 0.2, "monitoring": 12}
DOMAIN = {"spot": (80.0, 119.0), "maturity": (0.25, 2.0)}


def _inputs(x):
    x = np.asarray(x, dtype=float)
    if x.ndim != 2 or x.shape[1] != 2:
        raise ValueError("physical [spot,maturity] rows required")
    return x


def predict_nn(model, inputs):
    """Evaluate physical price and its spot derivative from exported arrays."""
    x = _inputs(inputs)
    if not np.isfinite(x).all() or np.any(x <= 0) or model["kind"] != "barrier_nn":
        raise ValueError("finite positive inputs and barrier network required")
    features = np.column_stack([x[:, 0], np.log(x[:, 1])])
    std = np.asarray(model["feature_std"])
    h = (features - model["feature_mean"]) / std
    derivative = np.column_stack([np.full(len(x), 1 / std[0]), np.zeros(len(x))])
    for i in range(2):
        weight, bias = model[f"layer{i}_weight"], model[f"layer{i}_bias"]
        h = np.tanh(h @ weight.T + bias)
        derivative = (derivative @ weight.T) * (1 - h**2)
    w, b = model["layer2_weight"], model["layer2_bias"]
    price = model["price_mean"] + model["price_scale"] * (h @ w.T + b).ravel()
    delta = model["price_scale"] * (derivative @ w.T).ravel()
    return np.column_stack([price, delta])


class HermiteSurface:
    """Hermite in S and linear in log(T), with Delta from the same price."""

    def __init__(self, spots, times, prices, deltas):
        self.spots = np.asarray(spots, dtype=float)
        self.times = np.asarray(times, dtype=float)
        self.prices = np.asarray(prices, dtype=float)
        self.deltas = np.asarray(deltas, dtype=float)
        if (
            np.any(np.diff(self.spots) <= 0)
            or np.any(np.diff(self.times) <= 0)
            or np.any(self.times <= 0)
            or self.prices.shape != (len(self.times), len(self.spots))
            or self.deltas.shape != self.prices.shape
        ):
            raise ValueError("increasing S/T knots and aligned price/Delta grid required")
        self.splines = [
            CubicHermiteSpline(self.spots, p, d, extrapolate=False)
            for p, d in zip(self.prices, self.deltas, strict=True)
        ]

    def __call__(self, inputs):
        x = _inputs(inputs)
        s, t = x.T
        if np.any(
            (s < self.spots[0]) | (s > self.spots[-1]) | (t < self.times[0]) | (t > self.times[-1])
        ):
            raise ValueError("interpolation domain exceeded")
        index = np.clip(np.searchsorted(self.times, t) - 1, 0, len(self.times) - 2)
        ratio = (np.log(t) - np.log(self.times[index])) / (
            np.log(self.times[index + 1]) - np.log(self.times[index])
        )
        result = np.empty((len(x), 2))
        for i in np.unique(index):
            mask = index == i
            for derivative in (0, 1):
                result[mask, derivative] = (1 - ratio[mask]) * self.splines[i](
                    s[mask], nu=derivative
                ) + ratio[mask] * self.splines[i + 1](s[mask], nu=derivative)
        return result


def inside(inputs):
    """Declared training domain; the t0 barrier contact lies outside it."""
    x = _inputs(inputs)
    return (
        np.isfinite(x).all(axis=1)
        & (x[:, 0] >= DOMAIN["spot"][0])
        & (x[:, 0] <= DOMAIN["spot"][1])
        & (x[:, 1] >= DOMAIN["maturity"][0])
        & (x[:, 1] <= DOMAIN["maturity"][1])
    )


def serve(approximation, inputs, oracle, *, contract=None):
    """Route valid OOD/bounds failures to a checked oracle without clipping.

    This is an experimental policy. Price bounds do not certify Greek accuracy.
    S=H has price zero and an undefined ordinary Delta. Invalid inputs and
    changed contracts remain explicit failures, not silently repaired results.
    """
    x = _inputs(inputs)
    prediction = np.full((len(x), 2), np.nan)
    status = np.full(len(x), "invalid", dtype="<U20")
    if contract is not None and any(
        key not in CONTRACT or value != CONTRACT[key] for key, value in contract.items()
    ):
        status[:] = "unsupported"
        return {"prediction": prediction, "status": status}
    valid = np.isfinite(x).all(axis=1) & np.all(x > 0, axis=1)
    knock = valid & (x[:, 0] >= CONTRACT["barrier"])
    prediction[knock] = 0.0
    status[knock] = "knocked_out"
    contact = knock & (x[:, 0] == CONTRACT["barrier"])
    prediction[contact, 1] = np.nan
    status[contact] = "delta_undefined"
    live = valid & ~knock
    approximate = live & inside(x)
    if np.any(approximate):
        indices = np.flatnonzero(approximate)
        output = np.asarray(approximation(x[approximate]), dtype=float)
        if output.shape != (len(indices), 2):
            raise ValueError("price/Delta predictions required")
        cap = (CONTRACT["barrier"] - CONTRACT["strike"]) * np.exp(-CONTRACT["rate"] * x[indices, 1])
        good = np.isfinite(output).all(axis=1) & (output[:, 0] >= 0) & (output[:, 0] <= cap)
        prediction[indices[good]] = output[good]
        status[indices[good]] = "approximation"
    fallback = live & (status != "approximation")
    if np.any(fallback):
        output = np.asarray(oracle(x[fallback]), dtype=float)
        if output.shape != (np.sum(fallback), 2):
            raise ValueError("oracle must return aligned price/Delta rows")
        indices = np.flatnonzero(fallback)
        cap = (CONTRACT["barrier"] - CONTRACT["strike"]) * np.exp(-CONTRACT["rate"] * x[indices, 1])
        good = np.isfinite(output).all(axis=1) & (output[:, 0] >= 0) & (output[:, 0] <= cap)
        prediction[indices[good]] = output[good]
        status[indices[good]] = "fallback"
        status[indices[~good]] = "oracle_failure"
    return {"prediction": prediction, "status": status}


def metrics(prediction, target):
    """Physical price/Delta RMSE, p99 and maximum absolute error."""
    actual, target = np.asarray(prediction, dtype=float), np.asarray(target, dtype=float)
    if actual.shape != target.shape or actual.ndim != 2 or actual.shape[1] != 2 or len(actual) == 0:
        raise ValueError("aligned nonempty price/Delta arrays required")
    error = actual - target
    if not np.isfinite(error).all():
        raise ValueError("finite prediction/reference errors required")
    result = {}
    for i, name in enumerate(("price", "delta")):
        result[name + "_rmse"] = float(np.sqrt(np.mean(error[:, i] ** 2)))
        result[name + "_p99_abs"] = float(np.quantile(np.abs(error[:, i]), 0.99))
        result[name + "_max_abs"] = float(np.max(np.abs(error[:, i])))
    return result
