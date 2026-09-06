"""Which evaluation windows sit inside TimesFM 3.0's pretraining corpus.

The TimesFM 3.0 model card names ``GiftEvalPretrain`` as a pretraining source.
Two of the benchmark datasets here — Monash ``traffic_hourly`` and Monash
``weather`` — appear in that corpus under the same names.  This module verifies
they are the *same numbers*, not merely the same name, and then records how far
into each series the pretraining copy runs, so a window's held-out target can be
classified as seen or unseen.

That classification is the only thing in this project that separates "TimesFM
forecasts well" from "TimesFM remembers".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .datasets import DATA_DIR, SPEC_BY_KEY, Window, load_series

INDEX_PATH = DATA_DIR / "pretrain_coverage.json"

# GiftEvalPretrain directory name -> the DatasetSpec key it corresponds to.
GEP_ALIASES = {"traffic_hourly": "traffic_hourly", "weather": "weather_daily"}

GEP_REPO = "Salesforce/GiftEvalPretrain"
GEP_URL = "https://huggingface.co/datasets/{repo}/resolve/main/{name}/data-00000-of-00001.arrow"


@dataclass(frozen=True)
class Coverage:
    """How much of a benchmark dataset the pretraining corpus contains."""

    dataset: str
    gep_name: str
    n_series_gep: int
    n_series_local: int
    checked: int
    identical: int
    lengths: dict[str, int]  # series_id -> number of leading points in the corpus

    @property
    def verified(self) -> bool:
        return self.checked > 0 and self.checked == self.identical


def _read_arrow(path: Path):
    import pyarrow as pa

    with pa.memory_map(str(path), "rb") as src:
        return pa.ipc.open_stream(src).read_all()


def build_index(cache_dir: Path, sample: int = 25, tol: float = 1e-4) -> dict[str, Coverage]:
    """Compare each shared dataset against its GiftEvalPretrain copy.

    ``cache_dir`` must already hold ``<gep_name>.arrow`` downloads; the fetch is
    a separate step so this stays offline and reproducible.
    """
    out: dict[str, Coverage] = {}
    for gep_name, key in GEP_ALIASES.items():
        arrow = cache_dir / f"{gep_name}.arrow"
        if not arrow.exists():
            raise FileNotFoundError(f"{arrow} missing; run scripts/build_contamination_index.py")
        table = _read_arrow(arrow)
        gep_ids = table.column("item_id").to_pylist()
        gep_tgt = table.column("target").to_pylist()
        gep = dict(zip(gep_ids, gep_tgt, strict=True))

        local = load_series(SPEC_BY_KEY[key])
        checked = identical = 0
        for name, values in local[:sample]:
            if name not in gep:
                continue
            a = np.asarray(gep[name], dtype=np.float64)
            b = np.asarray(values, dtype=np.float64)
            n = min(len(a), len(b))
            checked += 1
            identical += int(
                np.allclose(a[:n], b[:n], rtol=tol, atol=tol, equal_nan=True)
            )
        out[key] = Coverage(
            dataset=key,
            gep_name=gep_name,
            n_series_gep=len(gep_ids),
            n_series_local=len(local),
            checked=checked,
            identical=identical,
            lengths={name: len(v) for name, v in gep.items()},
        )
    return out


def save_index(index: dict[str, Coverage], path: Path = INDEX_PATH) -> None:
    payload = {
        k: {
            "gep_name": c.gep_name,
            "n_series_gep": c.n_series_gep,
            "n_series_local": c.n_series_local,
            "checked": c.checked,
            "identical": c.identical,
            "lengths": c.lengths,
        }
        for k, c in index.items()
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def load_index(path: Path = INDEX_PATH) -> dict[str, Coverage]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        k: Coverage(
            dataset=k,
            gep_name=v["gep_name"],
            n_series_gep=v["n_series_gep"],
            n_series_local=v["n_series_local"],
            checked=v["checked"],
            identical=v["identical"],
            lengths=v["lengths"],
        )
        for k, v in raw.items()
    }


def covered_fraction(window: Window, index: dict[str, Coverage]) -> float:
    """Fraction of a window's *held-out* points that the pretraining copy contains.

    ``nan`` means the dataset is not in the corpus at all — a different claim
    from 0.0, which means it is in the corpus but this window's target is past
    where the corpus stops.
    """
    cov = index.get(window.dataset)
    if cov is None:
        return float("nan")
    n = cov.lengths.get(window.series_id)
    if n is None:
        return float("nan")
    horizon_idx = np.arange(window.cutoff, window.cutoff + len(window.actual))
    return float((horizon_idx < n).mean())


def label(fraction: float) -> str:
    if not np.isfinite(fraction):
        return "held out"
    if fraction >= 1.0:
        return "in corpus"
    if fraction <= 0.0:
        return "past corpus"
    return "partial"
