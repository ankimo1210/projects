"""Offline threshold screening with explicit unknown outcomes."""

from __future__ import annotations

import math
import operator
from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Real

import pandas as pd

from .fundamentals import FundamentalField

_COMPARISONS = {"lt": operator.lt, "le": operator.le, "gt": operator.gt, "ge": operator.ge}
_TECHNICAL_UNITS = {
    "momentum": "fraction",
    "volatility_annualized": "fraction",
    "drawdown": "fraction",
    "zscore": "sigma",
    "periods_per_year": "periods/year",
}


@dataclass(frozen=True, slots=True)
class ThresholdRule:
    name: str
    source: str
    field: str
    comparison: str
    threshold: float
    unit: str
    field_definition: FundamentalField | None = None

    def __post_init__(self) -> None:
        for name in ("name", "field", "unit"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"rule {name} must be nonempty")
        if self.source not in {"technical", "fundamental"}:
            raise ValueError("rule source must be technical or fundamental")
        if self.source == "fundamental":
            if not isinstance(self.field_definition, FundamentalField):
                raise ValueError("fundamental rule requires its field definition")
            if self.field_definition.name != self.field or self.field_definition.unit != self.unit:
                raise ValueError("fundamental rule field definition differs from its alias or unit")
        elif self.field_definition is not None:
            raise ValueError("technical rule cannot have a fundamental field definition")
        if self.comparison not in _COMPARISONS:
            raise ValueError("rule operator must be lt, le, gt or ge")
        if isinstance(self.threshold, bool) or not isinstance(self.threshold, Real):
            raise ValueError("rule threshold must be finite numeric")
        if not math.isfinite(self.threshold):
            raise ValueError("rule threshold must be finite numeric")


def _number(value: object) -> float | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError("screen value must be numeric or missing")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("screen value must be finite")
    return number


def screen_research(
    indicators: pd.DataFrame,
    fundamentals: pd.DataFrame,
    rules: Sequence[ThresholdRule],
) -> pd.DataFrame:
    """Evaluate each asset; missing evidence stays unknown rather than false."""
    if not rules:
        raise ValueError("screen rules are required")
    if len({rule.name for rule in rules}) != len(rules):
        raise ValueError("screen rule names must be unique")
    if indicators.index.has_duplicates:
        raise ValueError("indicator asset index must be unique")
    if not isinstance(fundamentals.index, pd.MultiIndex) or fundamentals.index.nlevels != 2:
        raise ValueError("fundamental index must contain asset and field")
    if fundamentals.index.has_duplicates:
        raise ValueError("fundamental asset and field must be unique")
    if not set(fundamentals.index.get_level_values(0)).issubset(indicators.index):
        raise ValueError("fundamental asset is outside indicator universe")

    results = []
    for asset, indicator in indicators.iterrows():
        failed = []
        unknown = []
        for rule in rules:
            if rule.source == "technical":
                if rule.field not in indicators.columns:
                    raise ValueError(f"technical field unavailable: {rule.field}")
                actual_unit = (
                    indicator.get("currency")
                    if rule.field == "latest_close"
                    else _TECHNICAL_UNITS.get(rule.field)
                )
                if actual_unit is None:
                    raise ValueError(f"unsupported technical field: {rule.field}")
                value = indicator[rule.field]
                reason = indicator.get("missing_reason") or "missing_value"
            else:
                key = (asset, rule.field)
                if key not in fundamentals.index:
                    unknown.append(f"{rule.name}:not_collected")
                    continue
                fact = fundamentals.loc[key]
                actual_unit = fact["unit"]
                value = fact["value"]
                reason = fact["missing_reason"] or "missing_value"
                if fact["missing_reason"]:
                    unknown.append(f"{rule.name}:{reason}")
                    continue
            if actual_unit != rule.unit:
                unknown.append(f"{rule.name}:unit_mismatch")
                continue
            if rule.source == "fundamental":
                expected = rule.field_definition
                if any(
                    fact.get(name) != getattr(expected, name)
                    for name in ("taxonomy", "concept", "form")
                ):
                    unknown.append(f"{rule.name}:definition_mismatch")
                    continue
            number = _number(value)
            if number is None:
                unknown.append(f"{rule.name}:{reason}")
            elif not _COMPARISONS[rule.comparison](number, rule.threshold):
                failed.append(rule.name)
        results.append(
            {
                "instrument_id": asset,
                "status": "fail" if failed else "unknown" if unknown else "pass",
                "failed_rules": tuple(failed),
                "unknown_rules": tuple(unknown),
                "quality_reasons": indicator.get("quality_reasons", ()),
            }
        )
    return pd.DataFrame.from_records(results).set_index("instrument_id")
