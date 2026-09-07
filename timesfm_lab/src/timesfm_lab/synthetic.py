"""Series from known generating processes, with the optimal forecast computed too.

Two things this buys that no public dataset can:

1. **Contamination is impossible.** These paths are generated here, from a seed,
   and have never existed anywhere a pretraining crawler could reach.
2. **There is a ceiling.** Because the process is known, the conditional
   distribution of the future given the state at the cutoff is known, so the
   *best achievable* forecast can be computed. That turns "TimesFM scored 0.7"
   into "TimesFM captured 85% of the achievable signal" — the question a
   baseline comparison cannot answer.

Every oracle here is Monte-Carlo: simulate many futures from the true state and
take the mean and the quantiles. That is uniform across processes and correct
for the nonlinear ones, where a closed form would be a source of bugs.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np

# The oracle mean is a Monte-Carlo average, so it carries sampling error of its
# own. At 4,000 paths that error was visible: the random-walk oracle scored
# slightly *worse* than the naive forecast it is supposed to equal. 20,000 puts
# it below the resolution of every comparison in the report.
N_ORACLE_PATHS = 20_000


@dataclasses.dataclass(frozen=True)
class Process:
    """A generating process, its sampling protocol, and the state its oracle needs."""

    key: str
    title: str
    note: str
    season: int
    context_length: int
    horizon: int
    n_series: int
    n_windows: int

    def generate(self, rng: np.random.Generator, n: int) -> tuple[np.ndarray, dict[str, Any]]:
        """Return one path of length ``n`` plus whatever the oracle needs to look ahead."""
        raise NotImplementedError

    def simulate(
        self, aux: dict[str, Any], cutoff: int, horizon: int, rng: np.random.Generator
    ) -> np.ndarray:
        """Simulate ``(N_ORACLE_PATHS, horizon)`` futures from the true state at ``cutoff``."""
        raise NotImplementedError


def _antithetic(draws: np.ndarray) -> np.ndarray:
    """Mirror a half-batch of draws about its centre and stack both halves.

    For every process here whose conditional mean is a linear function of its
    shocks — the random walk, AR(1), both seasonal ones — pairing each path with
    its mirror image makes the simulated mean *exactly* the conditional mean, so
    the ceiling carries no Monte-Carlo error of its own. For the nonlinear ones
    it is still a large variance reduction.
    """
    return np.concatenate([draws, -draws], axis=0)


def _noise(rng, sd, shape):
    """Normal shocks; antithetic along the path axis when the batch is a path batch."""
    if isinstance(shape, tuple) and len(shape) == 2 and shape[0] == N_ORACLE_PATHS:
        half = rng.normal(0.0, 1.0, (shape[0] // 2, shape[1]))
        return _antithetic(half) * sd
    if shape == N_ORACLE_PATHS:
        half = rng.normal(0.0, 1.0, shape // 2)
        return _antithetic(half) * sd
    return rng.normal(0.0, sd, shape)


def _uniform(rng, shape):
    """Uniforms; mirrored as ``1 - u`` so the jump/arrival counts balance too."""
    if isinstance(shape, tuple) and len(shape) == 2 and shape[0] == N_ORACLE_PATHS:
        half = rng.random((shape[0] // 2, shape[1]))
        return np.concatenate([half, 1.0 - half], axis=0)
    return rng.random(shape)


# --------------------------------------------------------------------------- #
# processes
# --------------------------------------------------------------------------- #


@dataclasses.dataclass(frozen=True)
class PureSeasonal(Process):
    amp: float = 3.0
    amp2: float = 1.0
    sd: float = 0.5
    level: float = 10.0

    def _mean(self, t: np.ndarray, phase: float) -> np.ndarray:
        return (
            self.level
            + self.amp * np.sin(2 * np.pi * t / self.season + phase)
            + self.amp2 * np.sin(4 * np.pi * t / self.season + 2 * phase)
        )

    def generate(self, rng, n):
        phase = float(rng.uniform(0, 2 * np.pi))
        t = np.arange(n, dtype=float)
        return self._mean(t, phase) + _noise(rng, self.sd, n), {"phase": phase}

    def simulate(self, aux, cutoff, horizon, rng):
        t = np.arange(cutoff, cutoff + horizon, dtype=float)
        return self._mean(t, aux["phase"]) + _noise(rng, self.sd, (N_ORACLE_PATHS, horizon))


@dataclasses.dataclass(frozen=True)
class TrendSeasonal(PureSeasonal):
    slope: float = 0.01

    def _mean(self, t, phase):
        return super()._mean(t, phase) + self.slope * t


@dataclasses.dataclass(frozen=True)
class AR1(Process):
    phi: float = 0.85
    mu: float = 5.0
    sd: float = 1.0

    def generate(self, rng, n):
        burn = 200
        x = np.empty(n + burn)
        x[0] = self.mu
        eps = _noise(rng, self.sd, n + burn)
        for i in range(1, n + burn):
            x[i] = self.mu + self.phi * (x[i - 1] - self.mu) + eps[i]
        path = x[burn:]
        return path, {"path": path}

    def simulate(self, aux, cutoff, horizon, rng):
        last = aux["path"][cutoff - 1]
        out = np.empty((N_ORACLE_PATHS, horizon))
        cur = np.full(N_ORACLE_PATHS, last, dtype=float)
        for h in range(horizon):
            cur = self.mu + self.phi * (cur - self.mu) + _noise(rng, self.sd, N_ORACLE_PATHS)
            out[:, h] = cur
        return out


@dataclasses.dataclass(frozen=True)
class RandomWalk(Process):
    sd: float = 1.0
    start: float = 100.0

    def generate(self, rng, n):
        path = self.start + np.cumsum(_noise(rng, self.sd, n))
        return path, {"path": path}

    def simulate(self, aux, cutoff, horizon, rng):
        last = aux["path"][cutoff - 1]
        return last + np.cumsum(_noise(rng, self.sd, (N_ORACLE_PATHS, horizon)), axis=1)


@dataclasses.dataclass(frozen=True)
class RegimeSwitch(Process):
    p_jump: float = 0.01
    jump_sd: float = 4.0
    sd: float = 0.5
    start: float = 20.0

    def generate(self, rng, n):
        jumps = (rng.random(n) < self.p_jump) * _noise(rng, self.jump_sd, n)
        level = self.start + np.cumsum(jumps)
        return level + _noise(rng, self.sd, n), {"level": level}

    def simulate(self, aux, cutoff, horizon, rng):
        lvl = aux["level"][cutoff - 1]
        jumps = (_uniform(rng, (N_ORACLE_PATHS, horizon)) < self.p_jump) * _noise(
            rng, self.jump_sd, (N_ORACLE_PATHS, horizon)
        )
        return lvl + np.cumsum(jumps, axis=1) + _noise(rng, self.sd, (N_ORACLE_PATHS, horizon))


@dataclasses.dataclass(frozen=True)
class LogisticMap(Process):
    r: float = 3.9

    def generate(self, rng, n):
        z = np.empty(n)
        z[0] = float(rng.uniform(0.2, 0.8))
        for i in range(1, n):
            z[i] = self.r * z[i - 1] * (1.0 - z[i - 1])
        return z, {"path": z}

    def simulate(self, aux, cutoff, horizon, rng):
        # Fully deterministic: the oracle error is exactly zero. Every path is
        # the same, which is the point — the ceiling here is perfection.
        z = aux["path"][cutoff - 1]
        out = np.empty(horizon)
        for h in range(horizon):
            z = self.r * z * (1.0 - z)
            out[h] = z
        return np.tile(out, (N_ORACLE_PATHS, 1))


@dataclasses.dataclass(frozen=True)
class SeasonalHeteroskedastic(Process):
    amp: float = 3.0
    sd_base: float = 0.25
    sd_amp: float = 2.0
    level: float = 10.0

    def _mean(self, t, phase):
        return self.level + self.amp * np.sin(2 * np.pi * t / self.season + phase)

    def _sd(self, t, phase):
        wave = (1.0 + np.sin(2 * np.pi * t / self.season + phase)) / 2.0
        return self.sd_base + self.sd_amp * wave

    def generate(self, rng, n):
        phase = float(rng.uniform(0, 2 * np.pi))
        t = np.arange(n, dtype=float)
        return self._mean(t, phase) + rng.normal(0, self._sd(t, phase)), {"phase": phase}

    def simulate(self, aux, cutoff, horizon, rng):
        t = np.arange(cutoff, cutoff + horizon, dtype=float)
        sd = self._sd(t, aux["phase"])
        z = _noise(rng, 1.0, (N_ORACLE_PATHS, horizon))
        return self._mean(t, aux["phase"]) + z * sd[None, :]


@dataclasses.dataclass(frozen=True)
class IntermittentDemand(Process):
    base_rate: float = 0.12
    rate_amp: float = 0.10
    size_mean: float = 6.0

    def _rate(self, t, phase):
        return np.clip(
            self.base_rate + self.rate_amp * np.sin(2 * np.pi * t / self.season + phase), 0.01, 0.95
        )

    def generate(self, rng, n):
        phase = float(rng.uniform(0, 2 * np.pi))
        t = np.arange(n, dtype=float)
        hit = rng.random(n) < self._rate(t, phase)
        size = rng.gamma(2.0, self.size_mean / 2.0, n)
        return np.round(hit * size), {"phase": phase}

    def simulate(self, aux, cutoff, horizon, rng):
        t = np.arange(cutoff, cutoff + horizon, dtype=float)
        rate = np.tile(self._rate(t, aux["phase"]), (N_ORACLE_PATHS, 1))
        hit = _uniform(rng, (N_ORACLE_PATHS, horizon)) < rate
        size = rng.gamma(2.0, self.size_mean / 2.0, (N_ORACLE_PATHS, horizon))
        return np.round(hit * size)


PROCESSES: tuple[Process, ...] = (
    PureSeasonal(
        key="syn_seasonal", title="合成: 純粋な周期", season=24,
        note="正弦2倍音 + 白色ノイズ。周期が完全に安定した理想形。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
    TrendSeasonal(
        key="syn_trend_seasonal", title="合成: 周期 + トレンド", season=24,
        note="上と同じ周期に線形トレンド。外挿できるかを見る。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
    AR1(
        key="syn_ar1", title="合成: AR(1) φ=0.85", season=1,
        note="平均回帰。最適予測は幾何的に平均へ戻る。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
    RandomWalk(
        key="syn_random_walk", title="合成: ランダムウォーク", season=1,
        note="最適予測は直前値そのもの。過剰に構造を読むと負ける。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
    RegimeSwitch(
        key="syn_regime", title="合成: 水準ジャンプ", season=1,
        note="1%の確率で水準が跳ぶ。最適予測は現水準の維持。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
    LogisticMap(
        key="syn_chaos", title="合成: ロジスティック写像 r=3.9", season=1,
        note="決定論的カオス。ノイズゼロなので理論限界は誤差0。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
    SeasonalHeteroskedastic(
        key="syn_heteroskedastic", title="合成: 周期的な分散", season=24,
        note="平均も分散も周期的に動く。分位点ヘッドを直接試す。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
    IntermittentDemand(
        key="syn_intermittent", title="合成: 間欠需要", season=24,
        note="発生確率が周期的なスパースな計数。ゼロが多い。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
)

PROCESS_BY_KEY = {p.key: p for p in PROCESSES}
PROCESS_KEYS = frozenset(PROCESS_BY_KEY)
