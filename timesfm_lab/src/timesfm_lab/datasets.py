"""Public benchmark series: loading, sampling, and rolling-origin windowing.

Sources are the Monash Time Series Forecasting Repository (Zenodo, ``.tsf``)
and the ETDataset ETT-small CSVs.  Files are expected under ``_data/``; see
``scripts/fetch_data.sh``.

Nothing here touches the network — download is a separate, explicit step so a
benchmark run cannot silently depend on what a remote host served today.
"""

from __future__ import annotations

import dataclasses
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from .paths import DATA_DIR


@dataclasses.dataclass(frozen=True)
class DatasetSpec:
    """One benchmark dataset and the sampling protocol applied to it."""

    key: str
    title: str
    filename: str
    loader: str  # "tsf" | "ett"
    season: int  # dominant seasonal period, in steps
    freq_label: str
    context_length: int
    horizon: int
    n_series: int  # how many series to sample
    n_windows: int  # rolling-origin cutoffs per series
    note: str = ""

    @property
    def path(self) -> Path:
        return DATA_DIR / self.filename


# Chosen to span the difficulty range on purpose: electricity / traffic / solar
# have a seasonality a naive method can exploit, weather and river flow do not.
SPECS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        key="electricity_hourly",
        title="Electricity (hourly)",
        filename="electricity_hourly_dataset.tsf",
        loader="tsf",
        season=24,
        freq_label="1 hour",
        context_length=1024,
        horizon=48,
        n_series=40,
        n_windows=6,
        note="321 client load series. Daily + weekly cycle, very regular.",
    ),
    DatasetSpec(
        key="traffic_hourly",
        title="Traffic (hourly)",
        filename="traffic_hourly_dataset.tsf",
        loader="tsf",
        season=24,
        freq_label="1 hour",
        context_length=1024,
        horizon=48,
        n_series=40,
        n_windows=6,
        note="862 SF freeway occupancy sensors. Strong daily + weekday/weekend cycle.",
    ),
    DatasetSpec(
        key="solar_10_minutes",
        title="Solar (10 minutes)",
        filename="solar_10_minutes_dataset.tsf",
        loader="tsf",
        season=144,
        freq_label="10 minutes",
        context_length=2048,
        horizon=144,
        n_series=25,
        n_windows=6,
        note="137 PV plants. Hard floor at zero overnight; the daily shape is near-deterministic.",
    ),
    DatasetSpec(
        key="weather_daily",
        title="Weather (daily)",
        filename="weather_dataset.tsf",
        loader="tsf",
        season=7,
        freq_label="1 day",
        context_length=512,
        horizon=30,
        n_series=40,
        n_windows=6,
        note="3010 Australian station series (rain, temp, solar). No usable weekly cycle.",
    ),
    DatasetSpec(
        key="saugeen_river",
        title="Saugeen river flow (daily)",
        filename="saugeenday_dataset.tsf",
        loader="tsf",
        season=7,
        freq_label="1 day",
        context_length=512,
        horizon=30,
        n_series=1,
        n_windows=40,
        note="One 65-year series. Spiky, heavy-tailed, no short seasonality.",
    ),
    DatasetSpec(
        key="ett_h1",
        title="ETTh1 (hourly)",
        filename="ETTh1.csv",
        loader="ett",
        season=24,
        freq_label="1 hour",
        context_length=1024,
        horizon=48,
        n_series=7,
        n_windows=12,
        note="Transformer station 1, all 7 channels. The standard long-horizon benchmark.",
    ),
    DatasetSpec(
        key="ett_h2",
        title="ETTh2 (hourly)",
        filename="ETTh2.csv",
        loader="ett",
        season=24,
        freq_label="1 hour",
        context_length=1024,
        horizon=48,
        n_series=7,
        n_windows=12,
        note="Transformer station 2. Noisier than ETTh1 and prone to level shifts.",
    ),
)



def _synthetic_specs() -> tuple[DatasetSpec, ...]:
    from .synthetic import ALL_PROCESSES

    return tuple(
        DatasetSpec(
            key=p.key, title=p.title, filename="", loader="synthetic", season=p.season,
            freq_label="—", context_length=p.context_length, horizon=p.horizon,
            n_series=p.n_series, n_windows=p.n_windows, note=p.note,
        )
        for p in ALL_PROCESSES
    )


# Daily bars; the window plan in `finance.py` keeps every held-out point in 2026,
# which is after every cutoff the TimesFM 3.0 card names.
FINANCE_SPECS: tuple[DatasetSpec, ...] = (
    DatasetSpec(
        key="fin_log_volume", title="金融: 出来高（対数）", filename="finance_ohlcv.parquet",
        loader="finance", season=5, freq_label="1 営業日", context_length=512, horizon=20,
        n_series=18, n_windows=6,
        note="18銘柄の日次出来高。曜日周期がはっきりあり、金融系では最も予測余地がある。",
    ),
    DatasetSpec(
        key="fin_range_vol", title="金融: レンジボラ（対数）", filename="finance_ohlcv.parquet",
        loader="finance", season=5, freq_label="1 営業日", context_length=512, horizon=20,
        n_series=18, n_windows=6,
        note="Parkinson の高安レンジ推定量。クラスタリングするので HAR の主戦場。",
    ),
    DatasetSpec(
        key="fin_log_return", title="金融: 対数収益率", filename="finance_ohlcv.parquet",
        loader="finance", season=5, freq_label="1 営業日", context_length=512, horizon=20,
        n_series=18, n_windows=6,
        note="対照群。ここで有意に勝つ手法があったら、まず実装を疑うべき系列。",
    ),
)

TRAFFIC_UK_SPEC = DatasetSpec(
    key="traffic_uk_2026", title="Traffic UK 2026 (hourly)", filename="traffic_uk_2026.parquet",
    loader="traffic_uk", season=24, freq_label="1 hour", context_length=1024, horizon=48,
    n_series=28, n_windows=6,
    note=("英国高速道路のセンサー計数、2026年1〜6月。Monash traffic_hourly と"
          "同じ設計（時間足・多数センサー・日次+週次周期）で、確実に学習カットオフ後。"),
)

SYNTHETIC_SPECS = _synthetic_specs()
ALL_SPECS: tuple[DatasetSpec, ...] = (*SPECS, TRAFFIC_UK_SPEC, *SYNTHETIC_SPECS, *FINANCE_SPECS)
SPEC_BY_KEY = {s.key: s for s in ALL_SPECS}


def parse_tsf(path: Path) -> list[tuple[str, np.ndarray]]:
    """Parse a Monash ``.tsf`` file into ``(series_name, values)`` pairs.

    Missing values are encoded as ``?`` in the source and become ``nan`` here;
    callers decide what to do with them (we drop such series).
    """
    series: list[tuple[str, np.ndarray]] = []
    in_data = False
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not in_data:
                if line.strip().lower() == "@data":
                    in_data = True
                continue
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) < 2:
                continue
            name = parts[0]
            body = parts[-1]
            vals = np.fromiter(
                (np.nan if v == "?" else float(v) for v in body.split(",") if v != ""),
                dtype=np.float64,
            )
            series.append((name, vals))
    return series


def load_ett(path: Path) -> list[tuple[str, np.ndarray]]:
    """Load an ETT CSV as one series per channel column."""
    df = pd.read_csv(path)
    cols = [c for c in df.columns if c != "date"]
    return [(c, df[c].to_numpy(dtype=np.float64)) for c in cols]


def load_series(spec: DatasetSpec) -> list[tuple[str, np.ndarray]]:
    if not spec.path.exists():
        raise FileNotFoundError(
            f"{spec.path} is missing. Run scripts/fetch_data.sh first."
        )
    if spec.loader == "tsf":
        return parse_tsf(spec.path)
    if spec.loader == "ett":
        return load_ett(spec.path)
    raise ValueError(f"unknown loader {spec.loader!r}")


@dataclasses.dataclass(frozen=True)
class Window:
    """One rolling-origin evaluation window.

    ``oracle_point`` / ``oracle_quantiles`` are filled only for the synthetic
    processes, where the true conditional distribution of the future is known.
    They are the ceiling: no forecaster can beat them in population, so they turn
    a relative score into a distance from what was achievable.

    ``oracle_point`` is the conditional **median**, not the mean, because every
    point metric reported here is built on absolute error and the median is what
    minimises that. Using the mean made the "optimum" lose to TimesFM by 43% on
    the intermittent process, whose distribution puts most of its mass on zero:
    there the mean is a positive number no realisation ever takes. For the
    symmetric processes the two coincide.
    """

    dataset: str
    series_id: str
    cutoff: int  # index of the first held-out point
    context: np.ndarray
    actual: np.ndarray
    season: int
    oracle_point: np.ndarray | None = None
    oracle_quantiles: np.ndarray | None = None
    # (n_covariates, context_length) — filled only for the covariate ablation.
    past_covariates: np.ndarray | None = None

    @property
    def uid(self) -> str:
        return f"{self.dataset}|{self.series_id}|{self.cutoff}"


def _usable(values: np.ndarray, need: int) -> bool:
    return (
        len(values) >= need
        and np.isfinite(values[-need:]).all()
        and float(np.nanstd(values[-need:])) > 0.0
    )


def build_windows(spec: DatasetSpec, seed: int = 0) -> list[Window]:
    """Sample series and cut rolling-origin windows from the tail of each.

    Windows are spaced by one horizon so the held-out segments never overlap;
    overlapping test windows would make the per-window errors dependent and
    inflate the apparent significance of any comparison built on them.
    """
    if spec.loader == "synthetic":
        return _build_synthetic_windows(spec, seed)
    if spec.loader == "finance":
        return _build_finance_windows(spec)
    if spec.loader == "traffic_uk":
        return _build_traffic_uk_windows(spec, seed)
    rng = np.random.default_rng(seed)
    raw = load_series(spec)
    need = spec.context_length + spec.horizon * spec.n_windows
    eligible = [(n, v) for n, v in raw if _usable(v, need)]
    if not eligible:
        raise ValueError(f"{spec.key}: no series long enough for {need} points")

    if len(eligible) > spec.n_series:
        idx = rng.choice(len(eligible), size=spec.n_series, replace=False)
        chosen = [eligible[int(i)] for i in sorted(idx)]
    else:
        chosen = eligible

    windows: list[Window] = []
    for name, values in chosen:
        n = len(values)
        for w in range(spec.n_windows):
            end = n - w * spec.horizon
            cut = end - spec.horizon
            start = cut - spec.context_length
            if start < 0:
                continue
            ctx = values[start:cut]
            act = values[cut:end]
            if not (np.isfinite(ctx).all() and np.isfinite(act).all()):
                continue
            if float(np.std(ctx)) == 0.0:
                continue
            windows.append(
                Window(
                    dataset=spec.key,
                    series_id=name,
                    cutoff=int(cut),
                    context=ctx.astype(np.float32),
                    actual=act.astype(np.float64),
                    season=spec.season,
                )
            )
    return windows


# --------------------------------------------------------------------------- #
# generated and derived series
# --------------------------------------------------------------------------- #


def _build_synthetic_windows(spec: DatasetSpec, seed: int) -> list[Window]:
    """Generate paths from a known process and attach the optimal forecast.

    The seed is mixed with the dataset key so two processes with the same
    sampling protocol do not share a noise path — otherwise their results would
    be correlated in a way the per-window pairing does not expect.

    The key is folded in with ``crc32``, not ``hash()``: Python randomises string
    hashing per process, so a ``hash()``-derived seed silently regenerates
    *different* series on every run, and the benchmark stops being reproducible.
    """
    from .baselines import QUANTILE_LEVELS
    from .synthetic import PROCESS_BY_KEY

    proc = PROCESS_BY_KEY[spec.key]
    n = spec.context_length + spec.horizon * spec.n_windows + 64
    windows: list[Window] = []
    for s in range(spec.n_series):
        rng = np.random.default_rng([seed, zlib.crc32(spec.key.encode()), s])
        values, aux = proc.generate(rng, n)
        for w in range(spec.n_windows):
            end = n - w * spec.horizon
            cut = end - spec.horizon
            if cut - spec.context_length < 0:
                continue
            paths = proc.simulate(aux, cut, spec.horizon, rng)
            windows.append(
                Window(
                    dataset=spec.key,
                    series_id=f"S{s:03d}",
                    cutoff=int(cut),
                    context=values[cut - spec.context_length : cut].astype(np.float32),
                    actual=values[cut:end].astype(np.float64),
                    season=spec.season,
                    oracle_point=np.median(paths, axis=0),
                    oracle_quantiles=np.quantile(paths, QUANTILE_LEVELS, axis=0).T,
                )
            )
    return windows


def _build_finance_windows(spec: DatasetSpec) -> list[Window]:
    """Cut windows whose held-out target lies entirely after the training cutoff."""
    from .finance import TARGETS, FinanceWindowPlan, build_targets, load_ohlcv

    if spec.key not in TARGETS:
        raise ValueError(f"{spec.key} is not a financial target")
    plan = FinanceWindowPlan(
        context_length=spec.context_length, horizon=spec.horizon, n_windows=spec.n_windows
    )
    series = build_targets(load_ohlcv())[spec.key]
    windows: list[Window] = []
    for ticker, values, dates in series:
        for cut in plan.cutoffs(dates):
            ctx = values[cut - spec.context_length : cut]
            act = values[cut : cut + spec.horizon]
            if len(act) < spec.horizon or not (np.isfinite(ctx).all() and np.isfinite(act).all()):
                continue
            if float(np.std(ctx)) == 0.0:
                continue
            windows.append(
                Window(
                    dataset=spec.key,
                    series_id=ticker,
                    cutoff=int(cut),
                    context=ctx.astype(np.float32),
                    actual=act.astype(np.float64),
                    season=spec.season,
                )
            )
    return windows


def _build_traffic_uk_windows(spec: DatasetSpec, seed: int) -> list[Window]:
    """Windows whose held-out target contains no interpolated point.

    A window may sit on a context with a bridged one-to-six-hour gap — that is
    just slightly smoothed conditioning information — but never on a target with
    one, because a score against an interpolated value measures the interpolator.
    """
    from .traffic_uk import load_series as load_uk

    rng = np.random.default_rng(seed)
    segments = load_uk(min_length=spec.context_length + spec.horizon)
    if len(segments) > spec.n_series:
        idx = rng.choice(len(segments), size=spec.n_series, replace=False)
        segments = [segments[int(i)] for i in sorted(idx)]

    windows: list[Window] = []
    seen: dict[str, int] = {}
    for site, values, _ts, imputed in segments:
        # One site can contribute two segments (a >6h gap splits it). The id
        # must name the *segment*, not the window: the walk-forward selector
        # groups by series and needs several cutoffs under one id.
        k = seen[site] = seen.get(site, -1) + 1
        series_id = site if k == 0 else f"{site}#{k}"
        n = len(values)
        taken = 0
        for w in range(spec.n_windows * 4):  # look further back to skip bad windows
            if taken >= spec.n_windows:
                break
            end = n - w * spec.horizon
            cut = end - spec.horizon
            if cut - spec.context_length < 0:
                break
            if imputed[cut:end].any():
                continue
            ctx = values[cut - spec.context_length : cut]
            act = values[cut:end]
            if not (np.isfinite(ctx).all() and np.isfinite(act).all()) or float(np.std(ctx)) == 0.0:
                continue
            windows.append(
                Window(
                    dataset=spec.key,
                    series_id=series_id,
                    cutoff=int(cut),
                    context=ctx.astype(np.float32),
                    actual=act.astype(np.float64),
                    season=spec.season,
                )
            )
            taken += 1
    return windows
