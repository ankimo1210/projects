"""Strategy evaluation harnesses with common random numbers.

* Classical world: fully vectorised Monte Carlo in chunks — every strategy
  sees the *same* price paths, volumes and spreads (CRN), so cross-strategy
  differences are driven by the schedules, not sampling noise.
* LOB world: episode loops over shared scenario seeds. Exogenous randomness
  is pre-drawn per scenario inside the OrderBook, so strategies face the
  same flow; the state reactions (and therefore realised paths) differ
  because the agent's footprint differs — which is the point.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict
from typing import Any

import numpy as np
import pandas as pd

from .config import Config
from .environment import ExecutionEnv
from .impact import ImpactChannels, classical_execution
from .liquidity import spread_paths
from .price_process import simulate_mid_paths
from .random import scenario_seeds, stream_rng
from .strategies import classical_schedules
from .tca import classical_tca, lob_tca
from .volume import simulate_step_volumes

ALL_CHANNELS = ImpactChannels(temporary=True, permanent=True, transient=True)


def classical_world_run(
    cfg: Config,
    purpose: str = "test",
    n_paths: int | None = None,
    channels: ImpactChannels = ALL_CHANNELS,
    strategy_ids: tuple[str, ...] | None = None,
) -> dict[str, pd.DataFrame]:
    """Evaluate all classical schedules on CRN scenarios; returns TCA frames."""
    n = n_paths if n_paths is not None else cfg.n_test_scenarios
    chunk = min(cfg.mc_chunk_size, n)
    results: dict[str, list[pd.DataFrame]] = {}
    done = 0
    chunk_idx = 0
    while done < n:
        m = min(chunk, n - done)
        rng_price = stream_rng(cfg.seed, "classical", purpose, "price", chunk_idx)
        rng_vol = stream_rng(cfg.seed, "classical", purpose, "volume", chunk_idx)
        rng_spread = stream_rng(cfg.seed, "classical", purpose, "spread", chunk_idx)
        mids = simulate_mid_paths(cfg, rng_price, m)
        vols = simulate_step_volumes(cfg, rng_vol, m)
        spreads = spread_paths(cfg, rng_spread, m)
        schedules = classical_schedules(cfg, vols)
        for name, q in schedules.items():
            if strategy_ids is not None and name not in strategy_ids:
                continue
            res = classical_execution(cfg, q, mids, spreads, channels)
            df = classical_tca(cfg, q, res, mids, vols)
            results.setdefault(name, []).append(df)
        done += m
        chunk_idx += 1
    return {name: pd.concat(parts, ignore_index=True) for name, parts in results.items()}


def run_lob_episode(
    env: ExecutionEnv, policy: Callable[[np.ndarray, ExecutionEnv], Any], seed: int
) -> dict:
    """Run one episode; returns the episode summary dict."""
    obs = env.reset(seed)
    done = False
    while not done:
        action = policy(obs, env)
        obs, _, done, info = env.step(action)
    return info["episode"]


def lob_world_run(
    cfg: Config,
    policies: Mapping[str, Callable[[np.ndarray, ExecutionEnv], Any]],
    purpose: str = "test",
    n_episodes: int | None = None,
    reactive: bool = True,
    baselines: Mapping[str, np.ndarray] | None = None,
    feature_masks: Mapping[str, np.ndarray] | None = None,
    n_traces: int = 0,
) -> tuple[dict[str, pd.DataFrame], dict[str, list[list[dict]]]]:
    """Evaluate LOB-world policies on shared scenario seeds.

    Returns (tca_frames, traces) keyed by strategy id. ``traces`` holds the
    first ``n_traces`` episodes' per-step traces (list of dicts per episode).
    """
    n = n_episodes if n_episodes is not None else cfg.lob_eval_episodes
    seeds = scenario_seeds(cfg.seed, purpose, n)
    frames: dict[str, pd.DataFrame] = {}
    traces: dict[str, list[list[dict]]] = {}
    for name, policy in policies.items():
        baseline = baselines.get(name) if baselines else None
        mask = feature_masks.get(name) if feature_masks else None
        env = ExecutionEnv(cfg, reactive=reactive, baseline=baseline, feature_mask=mask)
        episodes: list[dict] = []
        ep_traces: list[list[dict]] = []
        for i, s in enumerate(seeds):
            env.record_trace = i < n_traces
            if hasattr(policy, "reset"):
                policy.reset()
            episodes.append(run_lob_episode(env, policy, int(s)))
            if env.record_trace:
                ep_traces.append([asdict(t) for t in env.traces])
        frames[name] = lob_tca(episodes, cfg)
        traces[name] = ep_traces
    return frames, traces
