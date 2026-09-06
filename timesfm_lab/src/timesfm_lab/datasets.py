"""Public benchmark series: loading, sampling, and rolling-origin windowing.

Sources are the Monash Time Series Forecasting Repository (Zenodo, ``.tsf``)
and the ETDataset ETT-small CSVs.  Files are expected under ``_data/``; see
``scripts/fetch_data.sh``.

Nothing here touches the network — download is a separate, explicit step so a
benchmark run cannot silently depend on what a remote host served today.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "_data"


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

SPEC_BY_KEY = {s.key: s for s in SPECS}


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
    """One rolling-origin evaluation window."""

    dataset: str
    series_id: str
    cutoff: int  # index of the first held-out point
    context: np.ndarray
    actual: np.ndarray
    season: int

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
