"""Transaction-cost analysis: implementation shortfall, decomposition, risk.

Sign convention: implementation shortfall is **positive when execution is
worse than the arrival price** for both sides:

    IS_sell = X P_arrival - sum_i q_i P_i^exec + fees
    IS_buy  = sum_i q_i P_i^exec - X P_arrival + fees
            = sign * (X P_arrival - sum q P) + fees,  sign = +1 sell / -1 buy.

The decomposition (timing / spread / temporary / permanent / transient /
fees / cleanup / spread capture / adverse selection) is *exact* here because
the synthetic simulators expose the latent components; in real markets it is
not uniquely identifiable — see docs/METHODOLOGY.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Config

QUANTILES = (0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99)


# --------------------------------------------------------------------------
# classical world
# --------------------------------------------------------------------------
def classical_tca(
    cfg: Config,
    q: np.ndarray,
    exec_res: dict[str, np.ndarray],
    mid_paths: np.ndarray,
    volumes: np.ndarray | None = None,
) -> pd.DataFrame:
    """Path-level TCA for a classical-world run (see impact.classical_execution)."""
    sign = cfg.sign
    X = cfg.initial_inventory
    arrival = mid_paths[:, 0]
    exec_price = exec_res["exec_price"]

    gross = np.sum(q * exec_price, axis=1)
    fees = np.sum(q * exec_res["fee"], axis=1)
    is_total = sign * (np.sum(q, axis=1) * arrival - gross) + fees

    comp = {
        "timing": np.sum(sign * q * (arrival[:, None] - mid_paths[:, :-1]), axis=1),
        "spread": np.sum(q * exec_res["spread_cost"], axis=1),
        "temporary": np.sum(q * exec_res["temporary"], axis=1),
        "permanent": np.sum(q * exec_res["permanent"], axis=1),
        "transient": np.sum(q * exec_res["transient"], axis=1),
        "fees": fees,
    }
    to_bps = 1e4 / (X * cfg.arrival_price)
    df = pd.DataFrame(
        {
            "is_total": is_total,
            "is_bps": is_total * to_bps,
            "executed": np.sum(q, axis=1),
            "residual": is_total - sum(comp.values()),
        }
    )
    for name, val in comp.items():
        df[f"comp_{name}"] = val
        df[f"comp_{name}_bps"] = val * to_bps

    cum = np.cumsum(q, axis=1)
    complete = cum >= X - 1e-6
    df["completion_step"] = np.where(complete.any(axis=1), complete.argmax(axis=1) + 1, q.shape[1])
    df["terminal_inventory"] = X - cum[:, -1]

    if volumes is not None:
        df["participation"] = np.sum(q, axis=1) / np.maximum(volumes.sum(axis=1), 1e-9)
        df["max_step_participation"] = np.max(q / np.maximum(volumes, 1e-9), axis=1)
        mkt_vwap = np.sum(volumes * mid_paths[:, :-1], axis=1) / np.maximum(
            volumes.sum(axis=1), 1e-9
        )
        strat_vwap = gross / np.maximum(np.sum(q, axis=1), 1e-9)
        df["vwap_slippage_bps"] = sign * (mkt_vwap - strat_vwap) / cfg.arrival_price * 1e4
    return df


# --------------------------------------------------------------------------
# LOB world
# --------------------------------------------------------------------------
def lob_tca(episodes: list[dict], cfg: Config) -> pd.DataFrame:
    """Flatten environment episode summaries into a path-level TCA frame."""
    rows = []
    to_bps = 1e4 / cfg.notional
    for ep in episodes:
        row = {k: v for k, v in ep.items() if not isinstance(v, dict)}
        for name, val in ep["components"].items():
            row[f"comp_{name}"] = val
            row[f"comp_{name}_bps"] = val * to_bps
        rows.append(row)
    df = pd.DataFrame(rows)
    df["residual"] = df["decomposition_residual"]
    return df


# --------------------------------------------------------------------------
# summary metrics
# --------------------------------------------------------------------------
def var_cvar(is_bps: np.ndarray, level: float) -> tuple[float, float]:
    """VaR / CVaR of the cost distribution (positive = cost) at ``level``."""
    var = float(np.quantile(is_bps, level))
    tail = is_bps[is_bps >= var]
    cvar = float(tail.mean()) if len(tail) else var
    return var, cvar


def summarize(df: pd.DataFrame, cfg: Config, strategy_id: str = "") -> dict:
    """Risk/cost summary of a path-level TCA frame (spec §14.4)."""
    x = df["is_bps"].to_numpy()
    out: dict[str, float | str] = {"strategy_id": strategy_id, "n_paths": len(df)}
    out.update(
        {
            "is_mean_bps": float(x.mean()),
            "is_median_bps": float(np.median(x)),
            "is_std_bps": float(x.std(ddof=1)) if len(x) > 1 else 0.0,
            "is_rmse_bps": float(np.sqrt(np.mean(x**2))),
            "worst_bps": float(x.max()),
            "best_bps": float(x.min()),
        }
    )
    for qt in QUANTILES:
        out[f"q{int(qt * 100):02d}_bps"] = float(np.quantile(x, qt))
    for level in (0.95, 0.99):
        var, cvar = var_cvar(x, level)
        out[f"var{int(level * 100)}_bps"] = var
        out[f"cvar{int(level * 100)}_bps"] = cvar
    lo, hi = bootstrap_mean_ci(x, seed=cfg.seed)
    out["is_mean_ci_lo_bps"] = lo
    out["is_mean_ci_hi_bps"] = hi

    optional_means = {
        "fill_rate": "limit_fill_rate",
        "completion_time_s": "completion_time_s",
        "terminal_inventory": "terminal_inventory",
        "cleanup_qty": "cleanup_qty",
        "participation": "participation",
        "avg_spread_paid": "avg_spread_paid",
        "avg_transient": "avg_transient",
        "max_exposure": "max_exposure",
        "n_orders": "n_orders",
        "n_cancels": "n_cancels",
        "violations": "violations",
        "mkt_shares": "mkt_shares",
        "limit_shares": "limit_shares",
        "vwap_slippage_bps": "vwap_slippage_bps",
        "completion_step": "completion_step",
    }
    for out_key, col in optional_means.items():
        if col in df.columns:
            out[out_key] = float(df[col].mean())
    if {"mkt_shares", "limit_shares"} <= set(df.columns):
        tot = df["mkt_shares"] + df["limit_shares"] + df.get("cleanup_qty", 0.0)
        out["market_order_share"] = float(
            ((df["mkt_shares"] + df.get("cleanup_qty", 0.0)) / tot.clip(lower=1e-9)).mean()
        )
        out["limit_order_share"] = float((df["limit_shares"] / tot.clip(lower=1e-9)).mean())
    out["turnover"] = (
        float(df["executed"].mean() / cfg.initial_inventory) if "executed" in df else 1.0
    )
    comp_cols = [c for c in df.columns if c.startswith("comp_") and c.endswith("_bps")]
    for c in comp_cols:
        out[c.replace("comp_", "mean_comp_")] = float(df[c].mean())
    return out


def bootstrap_mean_ci(
    x: np.ndarray, n_boot: int = 1000, alpha: float = 0.05, seed: int = 0
) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean (uncertainty for any comparison)."""
    if len(x) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    means = x[idx].mean(axis=1)
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


def decomposition_means_bps(df: pd.DataFrame) -> dict[str, float]:
    """Mean cost decomposition in bps (exact synthetic ground truth)."""
    out = {}
    for c in sorted(df.columns):
        if c.startswith("comp_") and c.endswith("_bps"):
            out[c[len("comp_") : -len("_bps")]] = float(df[c].mean())
    return out
