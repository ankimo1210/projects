"""RB-F04 light: hedge one monthly Asian in two worlds that share a vanilla surface.

The full RB-F04 dynamic-hedging study (branch ``codex/rbf04-storage-codec``) is
parked. This light version answers its first question with a small computation
that is regenerated, not stored: when two models price every European option
alike, how different are their Asian deltas and hedging P&L, and what does a
wrong hedge model cost?

- Worlds: the fixed RB-F04 Heston parameters, and the local-variance model
  built from the same Heston surface (Dupire / Markovian projection, the grid
  saved in ``../reference.npz``). Both use log-Euler with 192 steps per year,
  as in ``hullkit._model_dynamics``.
- Claim: arithmetic Asian call, K=100, T=1, twelve monthly observations
  (``../protocol.json``).
- Hedge models: Heston, local vol, and Black-Scholes with sigma=sqrt(theta).
  A model's delta at each hedge date is a regression of the pathwise payoff
  derivative on the observable state, fitted on that model's own training
  paths. Heston has two deltas: dV/dS at fixed variance, and the
  minimum-variance stock hedge dV/dS + rho*xi*(dV/dv)/S, whose dV/dv is the
  same kind of regression of the pathwise derivative with respect to the
  variance state (tangent of the full-truncation scheme). In the
  local-vol world the Heston deltas use v = local variance (E[v | S] by
  construction of the local-variance model).
- Strategies: stock-only delta hedge, rebalanced at every hedge date or only
  outside a no-trade band, with proportional costs on every trade including
  the initial purchase and the final unwind.

Only the code, seeds, and the summary ``results.json`` are kept
(``johnhull/AGENTS.md``, research data policy). Estimate: about 1 GB peak
memory, a few minutes on a laptop CPU, a results file of a few tens of KB.

    uv run --no-sync --package hullkit python johnhull/research/RB-F04/light/hedge_light.py
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import time
from pathlib import Path

import numpy as np
from hullkit._heston_local_surface import HestonParameters, LocalVarianceGrid

HERE = Path(__file__).resolve().parent
V1 = HERE.parent
PROTOCOL = json.loads((V1 / "protocol.json").read_text(encoding="utf-8"))
PARAMS = HestonParameters(**PROTOCOL["parameters"])
CONTRACT = PROTOCOL["contract"]
EXPIRY = float(CONTRACT["expiry"])
STRIKE = float(CONTRACT["asian_strike"])
OBSERVATIONS = np.asarray(CONTRACT["observations"], dtype=float)
BS_SIGMA = math.sqrt(PARAMS.theta)
SEED = 20261017
STEPS = 192
KNOTS = np.linspace(-4.0, 4.0, 17)
SLOPE_BUMP = 1e-5


def local_grid() -> LocalVarianceGrid:
    """The local-variance grid that RB-F04 v1 built from the Heston surface."""
    arrays = np.load(V1 / "reference.npz")
    options = {}
    if not arrays["surface.supported"].all():
        options["wing_boundaries"] = arrays["surface.wing_boundaries"]
    return LocalVarianceGrid(
        arrays["surface.times"],
        arrays["surface.z_nodes"],
        arrays["surface.local_variance"],
        PARAMS,
        **options,
    )


def normals(paths: int, stream: int, steps: int = STEPS) -> np.ndarray:
    """Fixed two-factor standard normals of shape (paths, steps, 2) for one stream."""
    rng = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(stream,)))
    return rng.standard_normal((paths, steps, 2))


def _local_variance(surface: LocalVarianceGrid, t: float, spots: np.ndarray) -> np.ndarray:
    evaluated = surface.evaluate(t, spots)
    variance = np.asarray(evaluated["variance"], dtype=float)
    status = np.asarray(evaluated["status"], dtype=str)
    if np.any(np.char.startswith(status, "unsupported")) or not np.all(variance > 0):
        raise ValueError(f"local variance unsupported at t={t}")
    return variance


def _local_variance_and_slope(surface, t, spots):
    """Variance and dVariance/dS; at t=0 the grid's early-time proxy row gives the slope."""
    if t == 0:
        variance = _local_variance(surface, 0.0, spots)
        t_slope = float(surface.times[0])
    else:
        variance = _local_variance(surface, t, spots)
        t_slope = t
    up = _local_variance(surface, t_slope, spots * (1 + SLOPE_BUMP))
    down = _local_variance(surface, t_slope, spots * (1 - SLOPE_BUMP))
    return variance, (up - down) / (2 * SLOPE_BUMP * spots)


def simulate(
    model: str,
    z: np.ndarray,
    surface: LocalVarianceGrid | None = None,
    start_step: int = 0,
    start_spot: np.ndarray | None = None,
    start_variance: float | None = None,
) -> dict:
    """Simulate every step of one model and its pathwise spot tangent.

    ``spot[:, n]`` is S at step n; ``tangent[:, n]`` is dS_n/dS_start of the
    discretized scheme for the given normals, so dS_m/dS_n = tangent_m/tangent_n.
    Heston returns its variance path; local vol returns the local variance at
    every left endpoint (used as the Heston state in the cross-model hedge).
    Heston also returns ``vega_level``/``vega_scale`` such that
    d log S_m / d v_n = (vega_level_m - vega_level_n) / vega_scale_n.
    ``start_step``/``start_spot`` restart a local-vol path mid-way (columns
    before the start are NaN) and ``start_variance`` replaces the initial
    Heston variance; the tests use them for finite differences.
    """
    paths, steps, _ = z.shape
    dt = EXPIRY / steps
    sqrt_dt = math.sqrt(dt)
    drift = PARAMS.rate - PARAMS.dividend_yield
    if start_step and model != "local":
        raise ValueError("only local-vol paths can be restarted")
    spot = np.full((paths, steps + 1), np.nan)
    tangent = np.full((paths, steps + 1), np.nan)
    state = np.full((paths, steps + 1), np.nan)
    spot[:, start_step] = PARAMS.spot if start_spot is None else start_spot
    tangent[:, start_step] = 1.0
    state[:, start_step] = PARAMS.v0 if model != "bs" else BS_SIGMA**2
    if start_variance is not None:
        state[:, start_step] = start_variance
    independent = math.sqrt(1 - PARAMS.rho**2)
    if model == "heston":
        # B_n = prod_{k<n} dv_{k+1}/dv_k and C_m = sum_{k<m} (dlogS_{k+1}/dv_k) B_k.
        vega_scale = np.ones((paths, steps + 1))
        vega_level = np.zeros((paths, steps + 1))
    for n in range(start_step, steps):
        s = spot[:, n]
        shock = z[:, n, 0]
        if model == "heston":
            v = np.maximum(state[:, n], 0.0)
            variance_shock = PARAMS.rho * shock + independent * z[:, n, 1]
            growth = np.exp((drift - 0.5 * v) * dt + np.sqrt(v) * sqrt_dt * shock)
            state[:, n + 1] = (
                state[:, n]
                + PARAMS.kappa * (PARAMS.theta - v) * dt
                + PARAMS.xi * np.sqrt(v) * sqrt_dt * variance_shock
            )
            factor = growth
            positive = state[:, n] > 0
            root = np.sqrt(np.where(positive, state[:, n], 1.0))
            dlog_dv = np.where(positive, -0.5 * dt + sqrt_dt * shock / (2 * root), 0.0)
            dv_dv = 1 + np.where(
                positive,
                -PARAMS.kappa * dt + PARAMS.xi * sqrt_dt * variance_shock / (2 * root),
                0.0,
            )
            vega_level[:, n + 1] = vega_level[:, n] + dlog_dv * vega_scale[:, n]
            vega_scale[:, n + 1] = vega_scale[:, n] * dv_dv
        elif model == "local":
            w, slope = _local_variance_and_slope(surface, n * dt, s)
            state[:, n] = w
            growth = np.exp((drift - 0.5 * w) * dt + np.sqrt(w) * sqrt_dt * shock)
            factor = growth * (1 + s * slope * (-0.5 * dt + sqrt_dt * shock / (2 * np.sqrt(w))))
        elif model == "bs":
            w = BS_SIGMA**2
            growth = np.exp((drift - 0.5 * w) * dt + BS_SIGMA * sqrt_dt * shock)
            state[:, n + 1] = w
            factor = growth
        else:
            raise ValueError(f"unknown model {model!r}")
        spot[:, n + 1] = s * growth
        tangent[:, n + 1] = tangent[:, n] * factor
    if model == "local":
        state[:, steps] = _local_variance(surface, EXPIRY, spot[:, steps])
    if not (np.isfinite(spot[:, start_step:]).all() and np.isfinite(tangent[:, start_step:]).all()):
        raise ValueError(f"{model}: nonfinite path")
    result = {"spot": spot, "tangent": tangent, "state": state, "dt": dt}
    if model == "heston":
        result.update(vega_level=vega_level, vega_scale=vega_scale)
    return result


def observation_steps(steps: int = STEPS) -> np.ndarray:
    """Step indices of the twelve observation dates."""
    indices = np.rint(OBSERVATIONS / EXPIRY * steps).astype(int)
    if not np.allclose(indices * EXPIRY / steps, OBSERVATIONS):
        raise ValueError("observation dates must fall on simulation steps")
    return indices


def discounted_payoff(spot: np.ndarray) -> np.ndarray:
    average = spot[:, observation_steps(spot.shape[1] - 1)].mean(axis=1)
    return math.exp(-PARAMS.rate * EXPIRY) * np.maximum(average - STRIKE, 0.0)


def _state_features(spot_n, realized_sum, n, steps):
    """Forward moneyness of the remaining average, standardized; exact-ITM mask; forwards."""
    dt = EXPIRY / steps
    obs = observation_steps(steps)
    future = obs[obs > n]
    t = n * dt
    forwards = np.exp((PARAMS.rate - PARAMS.dividend_yield) * (future * dt - t))
    strike_left = len(OBSERVATIONS) * STRIKE - realized_sum
    exact_itm = strike_left <= 0
    effective = np.where(exact_itm, 1.0, strike_left) / len(future)
    moneyness = np.log(spot_n * forwards.mean() / effective)
    scale = math.sqrt(PARAMS.theta * max(EXPIRY - t, dt) / 3)
    return np.clip(moneyness / scale, KNOTS[0], KNOTS[-1]), exact_itm, forwards


def _hats(x: np.ndarray) -> np.ndarray:
    """Piecewise-linear (hat) basis on KNOTS; rows sum to one."""
    index = np.clip(np.searchsorted(KNOTS, x, side="right") - 1, 0, len(KNOTS) - 2)
    weight = (x - KNOTS[index]) / (KNOTS[index + 1] - KNOTS[index])
    basis = np.zeros((x.size, len(KNOTS)))
    rows = np.arange(x.size)
    basis[rows, index] = 1 - weight
    basis[rows, index + 1] = weight
    return basis


def _design(x, variance, uses_variance):
    hats = _hats(x)
    if not uses_variance:
        return hats
    u = (variance - PARAMS.theta) / PARAMS.theta
    return np.hstack([hats, hats * u[:, None], hats * (u**2)[:, None]])


def _realized_sums(spot, steps):
    obs = observation_steps(steps)
    sums = np.zeros_like(spot)
    for index in obs:
        sums[:, index:] += spot[:, [index]]
    return sums


class DeltaModel:
    """Regression delta of one model, fitted on its own simulated paths."""

    def __init__(self, name: str, paths: dict, hedge_steps: np.ndarray, ridge: float = 1e-8):
        self.name = name
        self.uses_variance = name == "heston"
        spot, tangent, variance = paths["spot"], paths["tangent"], paths["state"]
        steps = spot.shape[1] - 1
        self.steps = steps
        obs = observation_steps(steps)
        in_the_money = (spot[:, obs].mean(axis=1) > STRIKE).astype(float)
        sums = _realized_sums(spot, steps)
        self.coefficients = {}
        self.vega_coefficients = {}
        self.initial = None
        for n in hedge_steps:
            future = obs[obs > n]
            if not len(future):
                continue
            discount = math.exp(-PARAMS.rate * (EXPIRY - n * paths["dt"]))
            target = (
                discount
                * in_the_money
                * (tangent[:, future] / tangent[:, [n]]).sum(axis=1)
                / len(OBSERVATIONS)
            )
            if n == 0:
                self.initial = float(target.mean())
                self.initial_se = float(target.std(ddof=1) / math.sqrt(target.size))
                continue
            x, exact, _ = _state_features(spot[:, n], sums[:, n], n, steps)
            keep = ~exact
            design = _design(x[keep], variance[keep, n], self.uses_variance)
            gram = design.T @ design + ridge * len(design) * np.eye(design.shape[1])
            self.coefficients[int(n)] = np.linalg.solve(gram, design.T @ target[keep])
            if self.uses_variance:
                level, scale = paths["vega_level"], paths["vega_scale"]
                vega_target = (
                    discount
                    * in_the_money
                    * (spot[:, future] * (level[:, future] - level[:, [n]])).sum(axis=1)
                    / scale[:, n]
                    / len(OBSERVATIONS)
                )
                self.vega_coefficients[int(n)] = np.linalg.solve(gram, design.T @ vega_target[keep])

    def delta(self, n: int, spot_n, realized_sum, variance_n) -> np.ndarray:
        """Shares of stock to hold after hedge step ``n`` for the given states."""
        if n == 0:
            return np.full(spot_n.shape, self.initial)
        x, exact, forwards = _state_features(spot_n, realized_sum, n, self.steps)
        discount = math.exp(-PARAMS.rate * (EXPIRY - n * EXPIRY / self.steps))
        exact_delta = discount * forwards.sum() / len(OBSERVATIONS)
        fitted = _design(x, variance_n, self.uses_variance) @ self.coefficients[int(n)]
        return np.where(exact, exact_delta, np.clip(fitted, 0.0, exact_delta))

    def vega(self, n: int, spot_n, realized_sum, variance_n) -> np.ndarray:
        """dV/dv per unit of instantaneous variance, regressed like the delta."""
        x, exact, _ = _state_features(spot_n, realized_sum, n, self.steps)
        fitted = _design(x, variance_n, True) @ self.vega_coefficients[int(n)]
        return np.where(exact, 0.0, fitted)


class MinimumVarianceDelta:
    """Heston stock-only minimum-variance hedge: dV/dS + rho*xi*(dV/dv)/S."""

    def __init__(self, heston: DeltaModel, first_step: int):
        self.heston = heston
        self.first_step = first_step

    def delta(self, n, spot_n, realized_sum, variance_n):
        fixed = self.heston.delta(n, spot_n, realized_sum, variance_n)
        # At t=0 the state is a single point; use the vega fitted at the first
        # later hedge date, evaluated at the initial state.
        m = self.first_step if n == 0 else n
        vega = self.heston.vega(m, spot_n, realized_sum, variance_n)
        return fixed + PARAMS.rho * PARAMS.xi * vega / spot_n


def hedge(
    world: dict, model: DeltaModel, every: int, price: float, cost=0.0, band=0.0, keep_pnl=False
) -> dict:
    """Discounted terminal P&L of a short Asian hedged with ``model``'s delta in ``world``.

    The seller receives ``price`` and holds delta shares, financed at the rate.
    With a band, a trade happens only when the target leaves the band and then
    moves the holding to the nearer band edge. Proportional costs apply to the
    initial purchase, every rebalance, and the final unwind.
    """
    spot = world["spot"]
    steps = spot.shape[1] - 1
    dt = EXPIRY / steps
    discounted_spot = spot * np.exp(-PARAMS.rate * dt * np.arange(steps + 1))
    sums = _realized_sums(spot, steps)
    hedge_steps = np.arange(0, steps, every)
    holding = np.zeros(spot.shape[0])
    gains = np.zeros(spot.shape[0])
    costs = np.zeros(spot.shape[0])
    turnover = np.zeros(spot.shape[0])
    for j, n in enumerate(hedge_steps):
        target = model.delta(int(n), spot[:, n], sums[:, n], world["state"][:, n])
        if band and j:
            new = np.clip(holding, target - band, target + band)
        else:
            new = target
        traded = np.abs(new - holding)
        costs += cost * traded * discounted_spot[:, n]
        turnover += traded
        holding = new
        following = hedge_steps[j + 1] if j + 1 < len(hedge_steps) else steps
        gains += holding * (discounted_spot[:, following] - discounted_spot[:, n])
    costs += cost * holding * discounted_spot[:, steps]
    turnover += holding
    pnl = price + gains - costs - discounted_payoff(spot)
    worst = np.sort(pnl)[: max(1, int(0.05 * pnl.size))]
    result = {
        "mean": float(pnl.mean()),
        "std": float(pnl.std(ddof=1)),
        "es_5pct": float(-worst.mean()),
        "mean_cost": float(costs.mean()),
        "mean_turnover_shares": float(turnover.mean()),
    }
    if keep_pnl:
        result["pnl"] = pnl
    return result


def paired_std_differences(pnls: dict, baseline: str, resamples: int = 200) -> dict:
    """Bootstrap SE of std(model) - std(baseline) on the same world paths."""
    rng = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(99,)))
    size = len(pnls[baseline])
    base = pnls[baseline]
    out = {}
    draws = {name: np.empty(resamples) for name in pnls}
    for b in range(resamples):
        index = rng.integers(0, size, size)
        reference = base[index].std(ddof=1)
        for name, pnl in pnls.items():
            draws[name][b] = pnl[index].std(ddof=1) - reference
    for name, pnl in pnls.items():
        if name == baseline:
            continue
        out[name] = {
            "difference": float(pnl.std(ddof=1) - base.std(ddof=1)),
            "bootstrap_se": float(draws[name].std(ddof=1)),
        }
    return out


def run(paths: int, train_offset: int = 0) -> dict:
    """Fit the delta models, hedge in both worlds, and summarize.

    ``train_offset`` shifts the training streams (the test worlds stay fixed)
    to check that the conclusions do not hinge on one regression fit.
    """
    started = time.perf_counter()
    surface = local_grid()
    train_z = {
        name: normals(paths, train_offset + stream)
        for stream, name in enumerate(("heston", "local", "bs"))
    }
    training = {name: simulate(name, z, surface) for name, z in train_z.items()}
    test_z = normals(paths, 10)
    worlds = {name: simulate(name, test_z, surface) for name in ("heston", "local")}
    del train_z, test_z

    frequencies = {"monthly": 16, "weekly": 4, "twice_weekly": 2}
    hedge_steps = np.arange(0, STEPS, 2)
    models = {name: DeltaModel(name, training[name], hedge_steps) for name in training}
    models = {
        "heston": models["heston"],
        "heston_mv": MinimumVarianceDelta(models["heston"], int(hedge_steps[1])),
        "local": models["local"],
        "bs": models["bs"],
    }
    del training

    prices = {}
    for name, world in worlds.items():
        payoff = discounted_payoff(world["spot"])
        prices[name] = {
            "price": float(payoff.mean()),
            "se": float(payoff.std(ddof=1) / math.sqrt(payoff.size)),
        }
    paired = discounted_payoff(worlds["local"]["spot"]) - discounted_payoff(
        worlds["heston"]["spot"]
    )
    prices["local_minus_heston"] = {
        "difference": float(paired.mean()),
        "paired_se": float(paired.std(ddof=1) / math.sqrt(paired.size)),
    }

    mid = STEPS // 2
    deltas_at_mid = {}
    for name, world in worlds.items():
        sums = _realized_sums(world["spot"], STEPS)[:, mid]
        values = {
            m: models[m].delta(mid, world["spot"][:, mid], sums, world["state"][:, mid])
            for m in models
        }
        deltas_at_mid[name] = {
            "mean_abs_heston_minus_local": float(np.abs(values["heston"] - values["local"]).mean()),
            "mean_abs_heston_mv_minus_local": float(
                np.abs(values["heston_mv"] - values["local"]).mean()
            ),
            "mean_abs_heston_minus_bs": float(np.abs(values["heston"] - values["bs"]).mean()),
            "mean_abs_local_minus_bs": float(np.abs(values["local"] - values["bs"]).mean()),
            "p95_abs_heston_minus_local": float(
                np.quantile(np.abs(values["heston"] - values["local"]), 0.95)
            ),
        }

    no_cost, std_vs_local = {}, {}
    for world in worlds:
        no_cost[world], std_vs_local[world] = {}, {}
        for freq, every in frequencies.items():
            rows = {
                m: hedge(worlds[world], models[m], every, prices[world]["price"], keep_pnl=True)
                for m in models
            }
            std_vs_local[world][freq] = paired_std_differences(
                {m: row.pop("pnl") for m, row in rows.items()}, "local"
            )
            no_cost[world][freq] = rows
    bands = (0.0, 0.01, 0.02, 0.05, 0.1)
    with_cost = {
        world: {
            f"band_{band:g}": {
                m: hedge(worlds[world], models[m], 4, prices[world]["price"], cost=0.001, band=band)
                for m in models
            }
            for band in bands
        }
        for world in worlds
    }
    return {
        "schema_version": 1,
        "study": "RB-F04 light: Asian delta hedging across Heston and local-vol worlds",
        "settings": {
            "paths_per_set": paths,
            "steps_per_year": STEPS,
            "seed": SEED,
            "streams": {
                "train_heston": train_offset,
                "train_local": train_offset + 1,
                "train_bs": train_offset + 2,
                "test_worlds": 10,
            },
            "parameters": PROTOCOL["parameters"],
            "contract": CONTRACT,
            "bs_sigma": BS_SIGMA,
            "hedge_every_steps": frequencies,
            "cost_rate": 0.001,
            "bands_shares": list(bands),
            "basis": "17 hat functions on standardized forward moneyness of the remaining "
            "average; Heston adds the hats times u and u^2, u=(v-theta)/theta",
        },
        "prices": prices,
        "initial_delta": {
            **{
                m: {"delta": models[m].initial, "se": models[m].initial_se}
                for m in ("heston", "local", "bs")
            },
            "heston_mv": float(
                models["heston_mv"].delta(
                    0, np.array([PARAMS.spot]), np.zeros(1), np.array([PARAMS.v0])
                )[0]
            ),
        },
        "delta_differences_at_half_year": deltas_at_mid,
        "hedging_no_cost": no_cost,
        "std_minus_local_delta_hedge": std_vs_local,
        "hedging_weekly_cost_10bp": with_cost,
        "runtime": {
            "seconds": round(time.perf_counter() - started, 1),
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--paths", type=int, default=2**15)
    parser.add_argument("--train-offset", type=int, default=0, help="shift training streams")
    parser.add_argument("--output", type=Path, default=HERE / "results.json")
    args = parser.parse_args(argv)
    if args.train_offset in range(8, 13):
        parser.error("training streams must not overlap the test stream 10")
    results = run(args.paths, args.train_offset)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} in {results['runtime']['seconds']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
