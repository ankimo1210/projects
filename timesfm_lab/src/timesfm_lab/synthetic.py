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


# --------------------------------------------------------------------------- #
# processes the classical baselines cannot represent
#
# The eight above were, with hindsight, a rigged test: a sine plus noise *is*
# a Fourier regression, AR(1) *is* inside ETS, and the optimal forecast of a
# random walk *is* the naive method. Measured as headroom — the distance from
# the best baseline down to the floor — five of them left under 3% to win, so
# no forecaster could have looked good.
#
# These five leave room, because a fixed-coefficient linear model cannot express
# them at all: a coefficient that switches on the state, a period that drifts,
# an amplitude that is itself periodic, a fractional integration order, and a
# saturating response to an unobserved driver.
# --------------------------------------------------------------------------- #


@dataclasses.dataclass(frozen=True)
class ThresholdAR(Process):
    """SETAR: the persistence coefficient switches on which side of the mean it is.

    Rises are sticky and falls are fast, so the series spends its time in an
    asymmetric sawtooth. Any single linear AR fits the average of the two
    regimes and is wrong in both.
    """

    mu: float = 10.0
    phi_lo: float = 0.95
    phi_hi: float = 0.30
    sd: float = 1.0

    def _step(self, prev: np.ndarray, eps: np.ndarray) -> np.ndarray:
        phi = np.where(prev < self.mu, self.phi_lo, self.phi_hi)
        return self.mu + phi * (prev - self.mu) + eps

    def generate(self, rng, n):
        burn = 300
        x = np.empty(n + burn)
        x[0] = self.mu
        eps = _noise(rng, self.sd, n + burn)
        for i in range(1, n + burn):
            x[i] = float(self._step(np.array([x[i - 1]]), np.array([eps[i]]))[0])
        path = x[burn:]
        return path, {"path": path}

    def simulate(self, aux, cutoff, horizon, rng):
        cur = np.full(N_ORACLE_PATHS, aux["path"][cutoff - 1], dtype=float)
        out = np.empty((N_ORACLE_PATHS, horizon))
        eps = _noise(rng, self.sd, (N_ORACLE_PATHS, horizon))
        for h in range(horizon):
            cur = self._step(cur, eps[:, h])
            out[:, h] = cur
        return out


@dataclasses.dataclass(frozen=True)
class PhaseDrift(Process):
    """A seasonal cycle whose period slowly lengthens, 24 steps toward about 30.

    No fixed-frequency basis can track this: the Fourier terms and the seasonal
    state both assume the period they were given, and drift puts them
    progressively out of phase with the data.
    """

    amp: float = 3.0
    sd: float = 0.4
    level: float = 10.0
    drift: float = 3.6e-4

    def _phase(self, t: np.ndarray) -> np.ndarray:
        # theta(t) = integral of 2*pi/m(t) dt with m(t) = season * (1 + drift*t)
        return (2 * np.pi / (self.season * self.drift)) * np.log1p(self.drift * t)

    def _mean(self, t, phi0):
        return self.level + self.amp * np.sin(self._phase(t) + phi0)

    def generate(self, rng, n):
        phi0 = float(rng.uniform(0, 2 * np.pi))
        t = np.arange(n, dtype=float)
        return self._mean(t, phi0) + _noise(rng, self.sd, n), {"phi0": phi0}

    def simulate(self, aux, cutoff, horizon, rng):
        t = np.arange(cutoff, cutoff + horizon, dtype=float)
        return self._mean(t, aux["phi0"]) + _noise(rng, self.sd, (N_ORACLE_PATHS, horizon))


@dataclasses.dataclass(frozen=True)
class AmplitudeModulated(Process):
    """A daily cycle whose amplitude is itself on a slower cycle.

    Harmonics of the daily period cannot express this — the product of two
    sinusoids lives at the sum and difference frequencies, which are not in a
    basis built from multiples of the daily period alone.
    """

    amp_base: float = 1.0
    amp_swing: float = 2.5
    slow_period: float = 240.0
    sd: float = 0.35
    level: float = 10.0

    def _mean(self, t, phi0, psi0):
        a = self.amp_base + self.amp_swing * (
            1 + np.sin(2 * np.pi * t / self.slow_period + psi0)
        ) / 2
        return self.level + a * np.sin(2 * np.pi * t / self.season + phi0)

    def generate(self, rng, n):
        phi0 = float(rng.uniform(0, 2 * np.pi))
        psi0 = float(rng.uniform(0, 2 * np.pi))
        t = np.arange(n, dtype=float)
        return self._mean(t, phi0, psi0) + _noise(rng, self.sd, n), {"phi0": phi0, "psi0": psi0}

    def simulate(self, aux, cutoff, horizon, rng):
        t = np.arange(cutoff, cutoff + horizon, dtype=float)
        return self._mean(t, aux["phi0"], aux["psi0"]) + _noise(
            rng, self.sd, (N_ORACLE_PATHS, horizon)
        )


@dataclasses.dataclass(frozen=True)
class LongMemory(Process):
    """Fractionally integrated noise, d = 0.4: autocorrelation that decays too slowly.

    ARIMA differences a whole number of times and ETS discounts geometrically;
    neither can produce a hyperbolic decay. The conditional mean depends on the
    *entire* past, which is what makes it a real test of a long context.
    """

    d: float = 0.4
    sd: float = 1.0
    n_weights: int = 1200

    def _psi(self) -> np.ndarray:
        # coefficients of (1 - L)^(-d), built by the stable recursion
        psi = np.empty(self.n_weights)
        psi[0] = 1.0
        for j in range(1, self.n_weights):
            psi[j] = psi[j - 1] * (j - 1 + self.d) / j
        return psi

    def generate(self, rng, n):
        psi = self._psi()
        eps = _noise(rng, self.sd, n + self.n_weights)
        x = np.convolve(eps, psi, mode="valid")[:n]
        return x, {"eps": eps, "psi": psi, "offset": self.n_weights}

    def simulate(self, aux, cutoff, horizon, rng):
        psi, eps, off = aux["psi"], aux["eps"], aux["offset"]
        j = np.arange(len(psi))
        out = np.empty((N_ORACLE_PATHS, horizon))
        future = _noise(rng, self.sd, (N_ORACLE_PATHS, horizon))
        for h in range(horizon):
            t = cutoff + h
            # the part already determined by innovations that have happened
            known = float(psi[h:] @ eps[off + t - j[h:]])
            # plus the innovations still to come
            out[:, h] = known + future[:, : h + 1] @ psi[h::-1][: h + 1]
        return out


@dataclasses.dataclass(frozen=True)
class NonlinearDriver(Process):
    """A saturating response to a slow, unobserved driver, seen 12 steps later.

    Only the response is observed. Its own lags carry the driver's information
    only through a nonlinearity, so a linear model extrapolates straight out of
    the saturating region. This is also the process the covariate experiment
    uses: hand the model the driver and the ceiling should come within reach.
    """

    phi_u: float = 0.98
    sd_u: float = 0.35
    lag: int = 12
    scale: float = 20.0
    steep: float = 2.0
    sd_y: float = 0.5

    def _respond(self, u: np.ndarray) -> np.ndarray:
        return self.scale / (1.0 + np.exp(-self.steep * u))

    def generate(self, rng, n):
        burn = 400
        total = n + burn + self.lag
        u = np.empty(total)
        u[0] = 0.0
        eps = _noise(rng, self.sd_u, total)
        for i in range(1, total):
            u[i] = self.phi_u * u[i - 1] + eps[i]
        y = self._respond(u[: total - self.lag]) + _noise(rng, self.sd_y, total - self.lag)
        return y[burn:][:n], {"u": u, "burn": burn, "n": n}

    def simulate(self, aux, cutoff, horizon, rng):
        u, burn, lag = aux["u"], aux["burn"], self.lag
        out = np.empty((N_ORACLE_PATHS, horizon))
        # y[t] responds to u[t]; the driver is already known up to lag steps ahead
        known_until = lag
        cur = np.full(N_ORACLE_PATHS, u[burn + cutoff + known_until - 1], dtype=float)
        eps = _noise(rng, self.sd_u, (N_ORACLE_PATHS, horizon))
        obs = _noise(rng, self.sd_y, (N_ORACLE_PATHS, horizon))
        for h in range(horizon):
            if h < known_until:
                drive = np.full(N_ORACLE_PATHS, u[burn + cutoff + h], dtype=float)
            else:
                cur = self.phi_u * cur + eps[:, h]
                drive = cur
            out[:, h] = self._respond(drive) + obs[:, h]
        return out

    def driver(self, aux: dict[str, Any], start: int, stop: int) -> np.ndarray:
        """The latent driver over ``[start, stop)`` — the covariate experiment's input."""
        return np.asarray(aux["u"][aux["burn"] + start : aux["burn"] + stop], dtype=float)


HARD_PROCESSES: tuple[Process, ...] = (
    ThresholdAR(
        key="syn_threshold_ar", title="合成: 閾値AR（係数が切替）", season=1,
        note="平均の上下で持続性が 0.95 と 0.30 に切り替わる。線形ARは両側で外す。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
    PhaseDrift(
        key="syn_phase_drift", title="合成: 周期が徐々にずれる", season=24,
        note="周期が 24 から約 30 へゆっくり伸びる。固定周期の基底は位相を外していく。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
    AmplitudeModulated(
        key="syn_amplitude_mod", title="合成: 振幅変調", season=24,
        note="日次周期の振幅自体が周期 240 で動く。日次高調波の基底には無い周波数。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
    LongMemory(
        key="syn_long_memory", title="合成: 長期記憶 d=0.4", season=1,
        note="分数階和分。自己相関が双曲的に減衰し、整数階差分でも幾何減衰でも表せない。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
    NonlinearDriver(
        key="syn_nonlinear_driver", title="合成: 未観測ドライバへの飽和応答", season=1,
        note="遅い潜在AR(1)にロジスティック応答、12ステップ遅れ。共変量実験の対象でもある。",
        context_length=512, horizon=48, n_series=30, n_windows=4,
    ),
)

ALL_PROCESSES: tuple[Process, ...] = PROCESSES + HARD_PROCESSES
PROCESS_BY_KEY = {p.key: p for p in ALL_PROCESSES}
PROCESS_KEYS = frozenset(PROCESS_BY_KEY)
