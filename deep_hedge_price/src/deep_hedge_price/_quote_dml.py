"""Private array-only quote/parameter DML and reduced differential regression.

Raw inputs are curve coordinates, spot and maturity. Physical risk is saved as
spot delta followed by five quote derivatives. Calibration Jacobians are passed
as arrays; this learner neither imports hullkit nor fits validation/test scales.
"""

from dataclasses import dataclass
from time import perf_counter

import numpy as np
import torch
from torch import nn

MODES = ("q_price", "theta_price", "theta_dml", "theta_quote_metric", "q_dml")


def _inputs(values):
    x = np.asarray(values, dtype=float)
    if x.ndim != 2 or x.shape[1] != 7 or len(x) == 0 or not np.all(np.isfinite(x)):
        raise ValueError("finite nonempty [curve5,spot,maturity] rows required")
    if np.any(x[:, 5:] <= 0):
        raise ValueError("positive spot and maturity required")
    return x


def _array(values, shape, name):
    x = np.asarray(values, dtype=float)
    if x.shape != shape or not np.all(np.isfinite(x)):
        raise ValueError(f"finite {name} array of shape {shape} required")
    return x


def _feature_values(x):
    features = x.copy()
    features[:, 5] = np.log(x[:, 5] / 100.0)
    features[:, 6] = np.log(x[:, 6])
    return features


def _scale(features, price, risk):
    std = features.std(axis=0)
    return {
        "feature_mean": features.mean(axis=0),
        "feature_std": np.where(np.ptp(features, axis=0) > 0, std, 1.0),
        "price_mean": float(price.mean()),
        "price_scale": max(float(price.std()), 1e-8),
        "risk_scale": np.maximum(np.sqrt(np.mean(risk**2, axis=0)), 1e-8),
    }


class _QuoteNet(nn.Module):
    def __init__(self, scale):
        super().__init__()
        self.register_buffer(
            "feature_mean", torch.tensor(scale["feature_mean"], dtype=torch.float64, device="cpu")
        )
        self.register_buffer(
            "feature_std", torch.tensor(scale["feature_std"], dtype=torch.float64, device="cpu")
        )
        self.price_mean = scale["price_mean"]
        self.price_scale = scale["price_scale"]
        self.layers = nn.ModuleList(
            [
                nn.Linear(7, 64, dtype=torch.float64, device="cpu"),
                nn.Linear(64, 64, dtype=torch.float64, device="cpu"),
                nn.Linear(64, 1, dtype=torch.float64, device="cpu"),
            ]
        )

    def forward(self, raw):
        features = torch.cat(
            [
                raw[:, :5],
                torch.log(raw[:, 5:6] / 100.0),
                torch.log(raw[:, 6:7]),
            ],
            dim=1,
        )
        h = (features - self.feature_mean) / self.feature_std
        for layer in self.layers[:-1]:
            h = torch.tanh(layer(h))
        return self.price_mean + self.price_scale * self.layers[-1](h).squeeze(-1)


@dataclass
class Fit:
    """A private model, train scales and actual update/time/failure record."""

    model: nn.Module
    scale: dict
    stats: dict
    mode: str


def _native_gradient(value, raw, *, create_graph):
    gradient = torch.autograd.grad(value.sum(), raw, create_graph=create_graph)[0]
    return torch.cat([gradient[:, 5:6], gradient[:, :5]], dim=1)


def _quoted(native, a, mode):
    if mode.startswith("theta"):
        return torch.cat(
            [
                native[:, :1],
                torch.einsum("nij,ni->nj", a, native[:, 1:]),
            ],
            dim=1,
        )
    return native


def fit_nn(train, *, mode, seed, updates=512, budget_s=120.0):
    """Fit a fixed 7→64→64→1 comparison model on one CPU thread.

    Five modes share architecture, initialization and mini-batch schedule. The
    watchdog covers setup and training; incomplete/over-budget fits remain
    inspectable with ``budget_failure=True`` and are not successful full fits.
    Global CPU RNG state and thread count are restored even after exceptions.
    """
    if mode not in MODES:
        raise ValueError("unknown quote DML mode")
    if updates < 1 or not np.isfinite(budget_s) or budget_s <= 0:
        raise ValueError("positive update count and time budget required")
    start = perf_counter()
    x = _inputs(train["x_theta" if mode.startswith("theta") else "x_quote"])
    n = len(x)
    price = _array(train["price"], (n,), "price")
    risk = _array(train["g_theta" if mode == "theta_dml" else "g_quote"], (n, 6), "risk")
    a = _array(train["A"], (n, 5, 5), "calibration Jacobian")
    scale = _scale(_feature_values(x), price, risk)
    old_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        # The local device context also covers Adam's internal scalar state,
        # whose allocation otherwise inherits an application's default device.
        with torch.device("cpu"), torch.random.fork_rng(devices=[]):
            torch.random.default_generator.manual_seed(seed)
            model = _QuoteNet(scale)
            optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
            xx = torch.tensor(x, dtype=torch.float64, device="cpu")
            pp = torch.tensor(price, dtype=torch.float64, device="cpu")
            gg = torch.tensor(risk, dtype=torch.float64, device="cpu")
            aa = torch.tensor(a, dtype=torch.float64, device="cpu")
            ss = torch.tensor(scale["risk_scale"], dtype=torch.float64, device="cpu")
            batch_rng = torch.Generator(device="cpu").manual_seed(seed + 104729)
            differential = mode not in ("q_price", "theta_price")

            def objective(indices):
                raw = xx[indices].detach().requires_grad_(differential)
                value = model(raw)
                price_loss = (((value - pp[indices]) / scale["price_scale"]) ** 2).mean()
                risk_loss = value.new_zeros(())
                if differential:
                    native = _native_gradient(value, raw, create_graph=True)
                    predicted = (
                        native if mode == "theta_dml" else _quoted(native, aa[indices], mode)
                    )
                    risk_loss = (((predicted - gg[indices]) / ss) ** 2).mean()
                return price_loss, risk_loss

            full = torch.arange(n, device="cpu")
            initial_parts = objective(full)
            initial_price, initial_risk = (float(part.detach()) for part in initial_parts)
            setup_s = perf_counter() - start
            training_start = perf_counter()
            completed = 0
            for _ in range(updates):
                if perf_counter() - start >= budget_s:
                    break
                indices = torch.randperm(n, generator=batch_rng, device="cpu")[: min(256, n)]
                optimizer.zero_grad(set_to_none=True)
                price_loss, risk_loss = objective(indices)
                loss = price_loss + risk_loss
                if not torch.isfinite(loss):
                    raise ArithmeticError("nonfinite quote DML training loss")
                loss.backward()
                optimizer.step()
                completed += 1
            final_parts = objective(full)
            final_price, final_risk = (float(part.detach()) for part in final_parts)
            training_s = perf_counter() - training_start
    finally:
        torch.set_num_threads(old_threads)
    elapsed = perf_counter() - start
    return Fit(
        model.eval(),
        scale,
        {
            "seed": int(seed),
            "mode": mode,
            "updates": completed,
            "requested_updates": int(updates),
            "batch_size": min(256, n),
            "batch_seed": int(seed + 104729),
            "threads": 1,
            "setup_s": setup_s,
            "training_s": training_s,
            "elapsed_s": elapsed,
            "budget_s": float(budget_s),
            "overrun_s": max(0.0, elapsed - budget_s),
            "budget_failure": completed != updates or elapsed > budget_s,
            "initial_price_loss": initial_price,
            "initial_risk_loss": initial_risk,
            "initial_loss": initial_price + initial_risk,
            "final_price_loss": final_price,
            "final_risk_loss": final_risk,
            "final_loss": final_price + final_risk,
        },
        mode,
    )


def predict_nn(fit, x, A):
    """Return physical prices, native-coordinate risk and quote-transformed risk."""
    x = _inputs(x)
    a = _array(A, (len(x), 5, 5), "calibration Jacobian")
    raw = torch.tensor(x, dtype=torch.float64, device="cpu", requires_grad=True)
    value = fit.model(raw)
    native = _native_gradient(value, raw, create_graph=False)
    quoted = _quoted(native, torch.tensor(a, dtype=torch.float64, device="cpu"), fit.mode)
    return {
        "price": value.detach().numpy(),
        "g_native": native.detach().numpy(),
        "g_quote": quoted.detach().numpy(),
    }


def export_nn(fit):
    """Copy every weight and train scale needed for independent NumPy replay."""
    result = {
        "kind": "nn",
        "mode": fit.mode,
        **{
            key: value.copy() if isinstance(value, np.ndarray) else value
            for key, value in fit.scale.items()
        },
    }
    for i, layer in enumerate(fit.model.layers):
        result[f"layer{i}_weight"] = layer.weight.detach().numpy().copy()
        result[f"layer{i}_bias"] = layer.bias.detach().numpy().copy()
    return result


def _reduced(dataset):
    x = _inputs(dataset["x_quote"])
    r = _array(dataset["integrated_rate"], (len(x),), "integrated rate")
    a = _array(dataset["a_quote"], (len(x), 5), "integrated-rate quote risk")
    return np.column_stack([np.log(x[:, 5] / 100.0), r, np.log(x[:, 6])]), x, a


def _monomials(u, powers):
    values = np.prod(u[:, None, :] ** powers[None, :, :], axis=-1)
    derivatives = np.zeros((len(u), 3, len(powers)))
    for coordinate in range(3):
        positive = powers[:, coordinate] > 0
        reduced = powers[positive].copy()
        reduced[:, coordinate] -= 1
        derivatives[:, coordinate, positive] = powers[positive, coordinate][None, :] * np.prod(
            u[:, None, :] ** reduced[None, :, :], axis=-1
        )
    return values, derivatives


def _ridge_features(fit, dataset):
    u, x, a = _reduced(dataset)
    values, derivative = _monomials((u - fit["feature_mean"]) / fit["feature_std"], fit["powers"])
    derivative /= fit["feature_std"][None, :, None]
    physical = np.empty((len(x), 6, len(fit["powers"])))
    physical[:, 0] = derivative[:, 0] / x[:, 5:6]
    physical[:, 1:] = derivative[:, 1:2] * a[:, :, None]
    return values, physical


def fit_ridge(train, *, differential):
    """Fit all 20 total-degree≤3 monomials in log-moneyness, R(T), log(T).

    Price rows have weight 1/sqrt(n); differential rows 1/sqrt(6n), with the
    same physical quote risk RMS as Q-DML. The 1e-8 coefficient penalty leaves
    the intercept unpenalized. No normal equations or test-fitted scales.
    """
    start = perf_counter()
    u, x, _ = _reduced(train)
    n = len(x)
    price = _array(train["price"], (n,), "price")
    risk = _array(train["g_quote"], (n, 6), "quote risk")
    fit = {
        "kind": "ridge",
        "differential": bool(differential),
        **_scale(u, price, risk),
        "powers": np.array(
            [(i, j, k) for i in range(4) for j in range(4) for k in range(4) if i + j + k <= 3],
            dtype=int,
        ),
    }
    phi, derivative = _ridge_features(fit, train)
    blocks = [phi / np.sqrt(n)]
    labels = [(price - fit["price_mean"]) / (fit["price_scale"] * np.sqrt(n))]
    if differential:
        weight = fit["price_scale"] / (fit["risk_scale"] * np.sqrt(6 * n))
        blocks.append((derivative * weight[None, :, None]).reshape(6 * n, 20))
        labels.append((risk / (fit["risk_scale"] * np.sqrt(6 * n))).ravel())
    penalty = np.eye(20) * np.sqrt(1e-8)
    penalty[0, 0] = 0.0
    blocks.append(penalty)
    labels.append(np.zeros(20))
    design = np.vstack(blocks)
    target = np.concatenate(labels)
    coefficients, _, rank, singular = np.linalg.lstsq(design, target, rcond=None)
    fit.update(
        coefficients=coefficients,
        rank=int(rank),
        singular_values=singular,
        training_s=perf_counter() - start,
    )
    return fit


def predict_ridge(fit, dataset):
    """Evaluate reduced-regression prices and analytic spot/quote derivatives."""
    values, physical = _ridge_features(fit, dataset)
    return {
        "price": fit["price_mean"] + fit["price_scale"] * (values @ fit["coefficients"]),
        "g_quote": fit["price_scale"] * np.einsum("nrf,f->nr", physical, fit["coefficients"]),
    }
