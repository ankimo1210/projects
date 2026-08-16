"""Loading and validation of the curated reference tables.

The reference tables are TOML (not CSV) on purpose: they are curated,
hand-reviewed source-of-truth content that should be readable in a diff,
and they carry provenance comments that a CSV cannot hold.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

REFERENCE_DIR = Path(__file__).resolve().parent / "reference"

SHORTAGE_FILE = REFERENCE_DIR / "sector_labor_shortage.toml"
OCCUPATION_FILE = REFERENCE_DIR / "occupation_ai_exposure.toml"
MIX_FILE = REFERENCE_DIR / "sector_occupation_mix.toml"
UNIVERSE_FILE = REFERENCE_DIR / "universe_jp.toml"

#: 人手不足指標。すべて「高いほど不足が深刻」の向きに揃っている。
SHORTAGE_INDICATORS = (
    "vacancy_rate_pct",
    "job_openings_ratio",
    "tdb_shortage_pct",
    "age55_share_pct",
    "separation_rate_pct",
    "overtime_hours_month",
)

TILT_LEVELS = {"low": -1.0, "mid": 0.0, "high": 1.0}


@dataclass(frozen=True)
class ReferenceData:
    """All curated inputs, already validated and index-aligned."""

    shortage: pd.DataFrame  # index: sector33 name
    occupations: pd.DataFrame  # index: occupation key
    mix: pd.DataFrame  # index: sector33 name, columns: occupation keys (shares summing to 1)
    regulation_drag: pd.Series  # index: sector33 name
    universe: pd.DataFrame  # index: code
    shortage_weights: pd.Series  # index: indicator name, sums to 1
    vintages: dict[str, str]

    @property
    def sectors(self) -> list[str]:
        return list(self.shortage.index)


def _read_toml(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _load_shortage() -> tuple[pd.DataFrame, pd.Series, str]:
    raw = _read_toml(SHORTAGE_FILE)
    df = pd.DataFrame(raw["sector"]).set_index("name")
    missing = [c for c in SHORTAGE_INDICATORS if c not in df.columns]
    if missing:
        raise ValueError(f"{SHORTAGE_FILE.name}: missing indicator columns {missing}")
    if df.index.duplicated().any():
        dupes = df.index[df.index.duplicated()].tolist()
        raise ValueError(f"{SHORTAGE_FILE.name}: duplicated sector names {dupes}")
    if df[list(SHORTAGE_INDICATORS)].isna().any().any():
        raise ValueError(f"{SHORTAGE_FILE.name}: indicator table contains NaN")

    weights = pd.Series(raw["weights"], dtype=float)
    unknown = set(weights.index) - set(SHORTAGE_INDICATORS)
    if unknown:
        raise ValueError(f"{SHORTAGE_FILE.name}: unknown weight keys {sorted(unknown)}")
    if weights.sum() <= 0:
        raise ValueError(f"{SHORTAGE_FILE.name}: weights must sum to a positive number")
    weights = weights.reindex(SHORTAGE_INDICATORS).fillna(0.0)
    weights = weights / weights.sum()
    return df, weights, raw["meta"]["vintage"]


def _load_occupations() -> tuple[pd.DataFrame, str]:
    raw = _read_toml(OCCUPATION_FILE)
    df = pd.DataFrame(raw["occupation"]).set_index("key")
    for col in ("llm_potential", "phys_potential"):
        if col not in df.columns:
            raise ValueError(f"{OCCUPATION_FILE.name}: missing column {col}")
        if not df[col].between(0, 100).all():
            raise ValueError(f"{OCCUPATION_FILE.name}: {col} must be within 0-100")
    return df, raw["meta"]["vintage"]


def _load_mix(occupation_keys: list[str], sector_names: list[str]) -> tuple[pd.DataFrame, pd.Series, str]:
    raw = _read_toml(MIX_FILE)
    df = pd.DataFrame(raw["sector"]).set_index("name")

    missing_occ = [k for k in occupation_keys if k not in df.columns]
    if missing_occ:
        raise ValueError(f"{MIX_FILE.name}: missing occupation columns {missing_occ}")

    missing_sectors = sorted(set(sector_names) - set(df.index))
    if missing_sectors:
        raise ValueError(f"{MIX_FILE.name}: missing sectors {missing_sectors}")

    drag = df["regulation_drag"].astype(float)
    if not drag.between(0.0, 0.5).all():
        raise ValueError(f"{MIX_FILE.name}: regulation_drag must be within 0.0-0.5")

    mix = df[occupation_keys].astype(float)
    if (mix < 0).any().any():
        raise ValueError(f"{MIX_FILE.name}: occupation shares must be non-negative")

    row_totals = mix.sum(axis=1)
    if (row_totals <= 0).any():
        empty = row_totals[row_totals <= 0].index.tolist()
        raise ValueError(f"{MIX_FILE.name}: sectors with zero occupation mix {empty}")
    # Rows are analyst-mapped and need not sum to exactly 100; normalise to shares.
    mix = mix.div(row_totals, axis=0)

    return mix.reindex(sector_names), drag.reindex(sector_names), raw["meta"]["vintage"]


def _load_universe(sector_names: list[str]) -> tuple[pd.DataFrame, str]:
    raw = _read_toml(UNIVERSE_FILE)
    df = pd.DataFrame(raw["company"])
    df["code"] = df["code"].astype(str)

    bad_codes = df.loc[~df["code"].str.fullmatch(r"[0-9A-Z]{4}"), "code"].tolist()
    if bad_codes:
        raise ValueError(f"{UNIVERSE_FILE.name}: malformed securities codes {bad_codes}")
    if df["code"].duplicated().any():
        dupes = df.loc[df["code"].duplicated(), "code"].tolist()
        raise ValueError(f"{UNIVERSE_FILE.name}: duplicated codes {dupes}")

    unknown_sectors = sorted(set(df["sector33"]) - set(sector_names))
    if unknown_sectors:
        raise ValueError(f"{UNIVERSE_FILE.name}: sector33 values not in the 33-sector master {unknown_sectors}")

    for col in ("labor_intensity", "knowledge_tilt"):
        bad = sorted(set(df[col]) - set(TILT_LEVELS))
        if bad:
            raise ValueError(f"{UNIVERSE_FILE.name}: {col} must be one of {sorted(TILT_LEVELS)}, got {bad}")

    return df.set_index("code"), raw["meta"]["vintage"]


@lru_cache(maxsize=1)
def load_reference() -> ReferenceData:
    """Load, validate and cache every curated table.

    Raises ``ValueError`` with a specific message if any table is internally
    inconsistent — the tables are hand-edited, so failing loudly matters more
    than being permissive.
    """
    shortage, weights, v_shortage = _load_shortage()
    occupations, v_occ = _load_occupations()
    occupation_keys = list(occupations.index)
    sector_names = list(shortage.index)
    mix, drag, v_mix = _load_mix(occupation_keys, sector_names)
    universe, v_universe = _load_universe(sector_names)

    return ReferenceData(
        shortage=shortage,
        occupations=occupations,
        mix=mix,
        regulation_drag=drag,
        universe=universe,
        shortage_weights=weights,
        vintages={
            "sector_labor_shortage": v_shortage,
            "occupation_ai_exposure": v_occ,
            "sector_occupation_mix": v_mix,
            "universe_jp": v_universe,
        },
    )
