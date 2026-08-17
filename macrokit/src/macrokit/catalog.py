"""Indicator catalog: one YAML entry per indicator.

The catalog is the single source of truth for what exists and where it comes
from. It deliberately does NOT record implementation status -- status is derived
from reality (adapters, snapshots, database rows) in `status.py`, because a
hand-written status field always rots.

`source_ref` is an untyped dict on purpose: every source identifies series
differently (`series_id` for FRED, `stats_id` for e-Stat, a tenor for MoF), and
the owning adapter is what gives those keys meaning.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class CatalogError(Exception):
    """A catalog file is malformed or internally inconsistent."""


class ReleaseRule(BaseModel):
    """When a Japanese statistic is published.

    US indicators leave this unset: their calendar comes from the FRED
    `releases/dates` endpoint, which is authoritative and free.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["nth_business_day", "fixed_day", "nth_weekday", "manual"]
    n: int | None = None
    day: int | None = None
    weekday: int | None = None
    time: str = "00:00"
    tz: str = "Asia/Tokyo"
    calendar: Literal["jp", "us"] = "jp"


class Chain(BaseModel):
    """Causal links to other indicators, e.g. shunto -> earnings -> real wage."""

    model_config = ConfigDict(extra="forbid")

    upstream: list[str] = Field(default_factory=list)
    downstream: list[str] = Field(default_factory=list)


class Indicator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    country: Literal["JP", "US"]
    block: Literal["prices", "labor", "activity", "demand", "capex", "external", "policy", "market"]
    title_ja: str
    source: str
    source_ref: dict
    freq: Literal["D", "W", "M", "Q", "A"]
    unit: str
    sa: Literal["sa", "nsa"]
    release_lag_days: int
    release_rule: ReleaseRule | None = None
    vintage: Literal["alfred", "snapshot", "none"]
    chain: Chain = Field(default_factory=Chain)
    caveats: list[str] = Field(default_factory=list)


def load_catalog(root: Path) -> dict[str, Indicator]:
    """Load every ``*.yaml`` under ``root`` and validate the catalog as a whole."""
    catalog: dict[str, Indicator] = {}
    for path in sorted(root.rglob("*.yaml")):
        entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for entry in entries:
            try:
                indicator = Indicator(**entry)
            except ValidationError as exc:
                raise CatalogError(f"{path}: {exc}") from exc
            if indicator.name in catalog:
                raise CatalogError(f"duplicate indicator name: {indicator.name} ({path})")
            catalog[indicator.name] = indicator

    _check_chain_references(catalog)
    _check_no_cycles(catalog)
    return catalog


def _check_chain_references(catalog: dict[str, Indicator]) -> None:
    for name, indicator in catalog.items():
        for direction in ("upstream", "downstream"):
            for target in getattr(indicator.chain, direction):
                if target not in catalog:
                    raise CatalogError(f"{name}.{direction} refers to unknown indicator: {target}")


def _check_no_cycles(catalog: dict[str, Indicator]) -> None:
    """Depth-first search over the merged chain graph, tracking the active path.

    `chain.upstream` and `chain.downstream` can describe the same edge from
    either end -- `a.chain.upstream = [b]` means exactly the same edge as
    `b.chain.downstream = [a]` (b -> a) -- so both directions are normalised
    into one edge set before the search runs. Otherwise a cycle declared
    purely through `upstream` would have no downstream edge at all and load
    without error.
    """
    edges: dict[str, list[str]] = {
        name: list(indicator.chain.downstream) for name, indicator in catalog.items()
    }
    for name, indicator in catalog.items():
        for source in indicator.chain.upstream:
            edges[source].append(name)

    WHITE, GREY, BLACK = 0, 1, 2
    colour = dict.fromkeys(catalog, WHITE)

    def visit(name: str, path: list[str]) -> None:
        colour[name] = GREY
        for target in edges[name]:
            if colour[target] == GREY:
                raise CatalogError(f"cycle in chain graph: {' -> '.join([*path, name, target])}")
            if colour[target] == WHITE:
                visit(target, [*path, name])
        colour[name] = BLACK

    for name in catalog:
        if colour[name] == WHITE:
            visit(name, [])
