"""Portfolio data validation, aggregation, and dashboard artifact generation."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

ALLOWED_VALUE_STATUSES = {"exact", "estimated", "reconciliation"}
STATUS_LABELS = {
    "exact": "確定",
    "estimated": "推定",
    "reconciliation": "残高調整",
}
SCENARIOS: dict[str, dict[str, Decimal]] = {
    "軽い調整": {
        "日本株": Decimal("-0.08"),
        "米国株": Decimal("-0.08"),
        "日本債券": Decimal("-0.01"),
        "J-REIT": Decimal("-0.06"),
        "バランス型": Decimal("-0.04"),
        "現金": Decimal("0"),
        "未分類": Decimal("-0.02"),
    },
    "株式20%下落": {
        "日本株": Decimal("-0.20"),
        "米国株": Decimal("-0.20"),
        "日本債券": Decimal("0.02"),
        "J-REIT": Decimal("-0.15"),
        "バランス型": Decimal("-0.10"),
        "現金": Decimal("0"),
        "未分類": Decimal("-0.05"),
    },
    "深いリスクオフ": {
        "日本株": Decimal("-0.35"),
        "米国株": Decimal("-0.35"),
        "日本債券": Decimal("0.04"),
        "J-REIT": Decimal("-0.30"),
        "バランス型": Decimal("-0.18"),
        "現金": Decimal("0"),
        "未分類": Decimal("-0.10"),
    },
}


@dataclass(frozen=True)
class Account:
    id: str
    name: str
    as_of: str
    total_value_jpy: Decimal
    unrealized_pnl_jpy: Decimal | None
    daily_pnl_jpy: Decimal | None
    quality_note: str


@dataclass(frozen=True)
class Position:
    account_id: str
    symbol: str
    name: str
    asset_class: str
    currency: str
    quantity: Decimal | None
    price: Decimal | None
    fx_rate: Decimal | None
    market_value_jpy: Decimal
    value_status: str
    source_note: str


@dataclass(frozen=True)
class Portfolio:
    snapshot_name: str
    base_currency: str
    accounts: tuple[Account, ...]
    positions: tuple[Position, ...]


@dataclass(frozen=True)
class Exposure:
    category: str
    group: str
    weight: Decimal
    mapped: bool


@dataclass(frozen=True)
class Valuation:
    pe: Decimal
    basis: str
    as_of: str
    quality: str
    method: str
    note: str


@dataclass(frozen=True)
class InstrumentReference:
    symbol: str
    label: str
    as_of: str
    exposures: tuple[Exposure, ...]
    factor_loadings: dict[str, Decimal]
    valuation: Valuation | None
    source_ids: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class FactorScenario:
    id: str
    label: str
    shocks: dict[str, Decimal]
    assumption: str


@dataclass(frozen=True)
class AnalysisReference:
    reference_name: str
    as_of: str
    instruments: dict[str, InstrumentReference]
    scenarios: tuple[FactorScenario, ...]
    sources: tuple[dict[str, Any], ...]


def _decimal(value: Any, field: str, *, nullable: bool = False) -> Decimal | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{field} must be numeric")
    try:
        return Decimal(str(value))
    except Exception as exc:  # pragma: no cover - Decimal exposes multiple parse errors
        raise ValueError(f"{field} must be numeric") from exc


def load_portfolio(path: Path) -> Portfolio:
    """Load a portfolio snapshot from JSON with strict numeric conversion."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    accounts = tuple(
        Account(
            id=str(row["id"]),
            name=str(row["name"]),
            as_of=str(row["as_of"]),
            total_value_jpy=_decimal(row["total_value_jpy"], "total_value_jpy"),
            unrealized_pnl_jpy=_decimal(
                row.get("unrealized_pnl_jpy"), "unrealized_pnl_jpy", nullable=True
            ),
            daily_pnl_jpy=_decimal(row.get("daily_pnl_jpy"), "daily_pnl_jpy", nullable=True),
            quality_note=str(row.get("quality_note", "")),
        )
        for row in raw["accounts"]
    )
    positions = tuple(
        Position(
            account_id=str(row["account_id"]),
            symbol=str(row["symbol"]),
            name=str(row["name"]),
            asset_class=str(row["asset_class"]),
            currency=str(row["currency"]),
            quantity=_decimal(row.get("quantity"), "quantity", nullable=True),
            price=_decimal(row.get("price"), "price", nullable=True),
            fx_rate=_decimal(row.get("fx_rate"), "fx_rate", nullable=True),
            market_value_jpy=_decimal(row["market_value_jpy"], "market_value_jpy"),
            value_status=str(row["value_status"]),
            source_note=str(row.get("source_note", "")),
        )
        for row in raw["positions"]
    )
    return Portfolio(
        snapshot_name=str(raw["snapshot_name"]),
        base_currency=str(raw.get("base_currency", "JPY")),
        accounts=accounts,
        positions=positions,
    )


def load_analysis_reference(path: Path) -> AnalysisReference:
    """Load look-through, factor, and valuation reference data from JSON."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    instruments: dict[str, InstrumentReference] = {}
    for row in raw["instruments"]:
        symbol = str(row["symbol"])
        if symbol in instruments:
            raise ValueError(f"duplicate analysis reference: {symbol}")
        valuation_raw = row.get("valuation")
        valuation = None
        if valuation_raw is not None:
            valuation = Valuation(
                pe=_decimal(valuation_raw["pe"], "valuation.pe"),
                basis=str(valuation_raw["basis"]),
                as_of=str(valuation_raw["as_of"]),
                quality=str(valuation_raw["quality"]),
                method=str(valuation_raw.get("method", "")),
                note=str(valuation_raw.get("note", "")),
            )
        instruments[symbol] = InstrumentReference(
            symbol=symbol,
            label=str(row.get("label", symbol)),
            as_of=str(row["as_of"]),
            exposures=tuple(
                Exposure(
                    category=str(exposure["category"]),
                    group=str(exposure["group"]),
                    weight=_decimal(exposure["weight"], "exposure.weight"),
                    mapped=bool(exposure.get("mapped", True)),
                )
                for exposure in row.get("exposures", [])
            ),
            factor_loadings={
                str(factor): _decimal(value, f"factor_loadings.{factor}")
                for factor, value in row.get("factor_loadings", {}).items()
            },
            valuation=valuation,
            source_ids=tuple(str(source_id) for source_id in row.get("source_ids", [])),
            note=str(row.get("note", "")),
        )

    scenarios = tuple(
        FactorScenario(
            id=str(row["id"]),
            label=str(row["label"]),
            shocks={
                str(factor): _decimal(value, f"scenario.{row['id']}.{factor}")
                for factor, value in row["shocks"].items()
            },
            assumption=str(row.get("assumption", "")),
        )
        for row in raw["scenarios"]
    )
    reference = AnalysisReference(
        reference_name=str(raw["reference_name"]),
        as_of=str(raw["as_of"]),
        instruments=instruments,
        scenarios=scenarios,
        sources=tuple(dict(source) for source in raw.get("sources", [])),
    )
    issues = validate_analysis_reference(reference)
    if issues:
        raise ValueError("; ".join(issues))
    return reference


def validate_analysis_reference(reference: AnalysisReference) -> list[str]:
    """Return reference-data issues that would make analysis misleading."""
    issues: list[str] = []
    try:
        date.fromisoformat(reference.as_of)
    except ValueError:
        issues.append(f"invalid reference as_of: {reference.as_of}")

    source_ids = [str(source.get("id", "")) for source in reference.sources]
    if "" in source_ids or len(source_ids) != len(set(source_ids)):
        issues.append("analysis source ids must be non-empty and unique")
    known_source_ids = set(source_ids)
    for instrument in reference.instruments.values():
        try:
            date.fromisoformat(instrument.as_of)
        except ValueError:
            issues.append(f"invalid instrument as_of: {instrument.symbol}")
        exposure_total = sum((exposure.weight for exposure in instrument.exposures), Decimal())
        if any(exposure.weight < 0 for exposure in instrument.exposures):
            issues.append(f"negative exposure weight: {instrument.symbol}")
        if exposure_total > Decimal("1.01"):
            issues.append(
                f"exposure weights exceed 101%: {instrument.symbol} ({exposure_total:.4f})"
            )
        missing_sources = set(instrument.source_ids) - known_source_ids
        if missing_sources:
            issues.append(
                f"unknown source ids for {instrument.symbol}: {', '.join(sorted(missing_sources))}"
            )
        if instrument.valuation is not None:
            if instrument.valuation.pe <= 0:
                issues.append(f"non-positive P/E: {instrument.symbol}")
            if instrument.valuation.quality not in {"current", "stale", "estimated"}:
                issues.append(f"invalid valuation quality: {instrument.symbol}")
            try:
                date.fromisoformat(instrument.valuation.as_of)
            except ValueError:
                issues.append(f"invalid valuation as_of: {instrument.symbol}")

    scenario_ids = [scenario.id for scenario in reference.scenarios]
    if len(scenario_ids) != len(set(scenario_ids)):
        issues.append("scenario ids must be unique")
    if any(not scenario.shocks for scenario in reference.scenarios):
        issues.append("every scenario must have at least one shock")
    return issues


def validate_portfolio(portfolio: Portfolio, tolerance_jpy: Decimal = Decimal("1")) -> list[str]:
    """Return validation issues; an empty list means the snapshot reconciles."""
    issues: list[str] = []
    account_ids = [account.id for account in portfolio.accounts]
    if len(account_ids) != len(set(account_ids)):
        issues.append("account ids must be unique")

    known_accounts = set(account_ids)
    totals: defaultdict[str, Decimal] = defaultdict(Decimal)
    position_keys: set[tuple[str, str]] = set()
    for position in portfolio.positions:
        if position.account_id not in known_accounts:
            issues.append(f"unknown account_id: {position.account_id}")
        if position.market_value_jpy < 0:
            issues.append(f"negative market value: {position.account_id}/{position.symbol}")
        if position.value_status not in ALLOWED_VALUE_STATUSES:
            issues.append(f"invalid value_status: {position.value_status}")
        key = (position.account_id, position.symbol)
        if key in position_keys:
            issues.append(f"duplicate position: {position.account_id}/{position.symbol}")
        position_keys.add(key)
        totals[position.account_id] += position.market_value_jpy

    for account in portfolio.accounts:
        difference = totals[account.id] - account.total_value_jpy
        if abs(difference) > tolerance_jpy:
            issues.append(f"account total mismatch: {account.id} ({difference:+,.2f} JPY)")
    return issues


def _scopes(portfolio: Portfolio) -> list[tuple[str, tuple[Position, ...]]]:
    return [("すべて", portfolio.positions)] + [
        (
            account.name,
            tuple(
                position for position in portfolio.positions if position.account_id == account.id
            ),
        )
        for account in portfolio.accounts
    ]


def _float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def _source() -> dict[str, Any]:
    return {
        "id": "portfolio_snapshot",
        "label": "ローカルのポートフォリオ・スナップショット",
        "path": "data/portfolio.private.json",
    }


def _analysis_source(path: str) -> dict[str, Any]:
    return {
        "id": "analysis_reference",
        "label": "公式資料から転記した分析参照データ",
        "path": path,
    }


def _materialize_datasets_with_sql(
    datasets: dict[str, list[dict[str, Any]]],
) -> dict[str, str]:
    """Pass reviewed rows through SQLite and return the SQL that produced each dataset."""
    queries: dict[str, str] = {}
    with sqlite3.connect(":memory:") as connection:
        for dataset, rows in datasets.items():
            if not rows:
                continue
            fields = list(rows[0])
            if any(list(row) != fields for row in rows):
                raise ValueError(f"inconsistent dataset columns: {dataset}")
            column_types = []
            for field in fields:
                values = [row[field] for row in rows if row[field] is not None]
                sql_type = (
                    "REAL"
                    if values and all(isinstance(value, int | float) for value in values)
                    else "TEXT"
                )
                column_types.append(f'"{field}" {sql_type}')
            connection.execute(f'CREATE TABLE "{dataset}" ({", ".join(column_types)})')
            placeholders = ", ".join("?" for _field in fields)
            connection.executemany(
                f'INSERT INTO "{dataset}" VALUES ({placeholders})',
                ([row[field] for field in fields] for row in rows),
            )
            selected_fields = ", ".join(f'"{field}"' for field in fields)
            query = f'SELECT {selected_fields} FROM "{dataset}" ORDER BY rowid'
            cursor = connection.execute(query)
            datasets[dataset] = [
                dict(zip(fields, values, strict=True)) for values in cursor.fetchall()
            ]
            queries[dataset] = query
    return queries


def _attach_widget_sources(
    artifact: dict[str, Any],
    queries: dict[str, str],
    *,
    generated_at: str,
    source_path: str,
    reference_source_path: str | None,
) -> None:
    """Attach exact executed SQL and reproducible transformation provenance."""
    inputs = [source_path]
    if reference_source_path is not None:
        inputs.append(reference_source_path)
    for collection in ("cards", "charts", "tables"):
        for item in artifact["manifest"][collection]:
            dataset = item["dataset"]
            query = queries.get(dataset)
            if query is None:
                continue
            item["source"] = {
                "query": {
                    "engine": "sqlite",
                    "sql": query,
                    "description": (f"Pythonで検証済みの {dataset} 行をSQLiteで再マテリアライズ。"),
                    "tables_used": [dataset],
                    "executed_at": generated_at,
                },
                "inputs": inputs,
                "transformation": {
                    "language": "python",
                    "path": "src/portfolio_analyzer/core.py",
                    "function": "_scope_rows / _analysis_rows",
                },
            }


def _fallback_exposure(position: Position) -> Exposure:
    if position.asset_class == "現金":
        return Exposure("現金", "asset", Decimal("1"), True)
    if position.asset_class == "日本債券":
        return Exposure("日本債券", "asset", Decimal("1"), True)
    if position.asset_class == "J-REIT":
        return Exposure("不動産", "sector", Decimal("1"), True)
    if position.asset_class in {"日本株", "米国株"}:
        return Exposure("未分類株式", "sector", Decimal("1"), False)
    return Exposure(position.asset_class, "other", Decimal("1"), False)


def _equity_loading(position: Position, reference: InstrumentReference | None) -> Decimal:
    if reference is not None:
        return reference.factor_loadings.get("株式全体", Decimal())
    return Decimal("1") if position.asset_class in {"日本株", "米国株"} else Decimal()


def _analysis_rows(
    portfolio: Portfolio, reference: AnalysisReference
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, float | None]]]:
    lookthrough: list[dict[str, Any]] = []
    sectors: list[dict[str, Any]] = []
    sensitivity: list[dict[str, Any]] = []
    sensitivity_contributions: list[dict[str, Any]] = []
    valuations: list[dict[str, Any]] = []
    summary_metrics: dict[str, dict[str, float | None]] = {}

    for scope, positions in _scopes(portfolio):
        total = sum((position.market_value_jpy for position in positions), Decimal())
        if total <= 0:
            continue

        exposure_values: defaultdict[tuple[str, str, bool], Decimal] = defaultdict(Decimal)
        equity_total = Decimal()
        by_symbol: defaultdict[str, Decimal] = defaultdict(Decimal)
        position_names: dict[str, str] = {}
        position_asset_classes: dict[str, str] = {}
        for position in positions:
            by_symbol[position.symbol] += position.market_value_jpy
            position_names[position.symbol] = position.name
            position_asset_classes[position.symbol] = position.asset_class
            instrument = reference.instruments.get(position.symbol)
            equity_total += position.market_value_jpy * _equity_loading(position, instrument)

            raw_exposures = instrument.exposures if instrument else (_fallback_exposure(position),)
            raw_weight = sum((exposure.weight for exposure in raw_exposures), Decimal())
            scale = Decimal("1") / raw_weight if raw_weight > Decimal("1") else Decimal("1")
            assigned = Decimal()
            for exposure in raw_exposures:
                weight = exposure.weight * scale
                assigned += weight
                exposure_values[(exposure.group, exposure.category, exposure.mapped)] += (
                    position.market_value_jpy * weight
                )
            residual = Decimal("1") - assigned
            if residual > Decimal("0.0001"):
                exposure_values[("other", "未分類・残差", False)] += (
                    position.market_value_jpy * residual
                )

        sector_total = sum(
            value
            for (group, _category, _mapped), value in exposure_values.items()
            if group == "sector"
        )
        mapped_sector_total = sum(
            value
            for (group, _category, mapped), value in exposure_values.items()
            if group == "sector" and mapped
        )
        for (group, category, mapped), value in sorted(
            exposure_values.items(), key=lambda item: item[1], reverse=True
        ):
            lookthrough.append(
                {
                    "scope": scope,
                    "group": group,
                    "category": category,
                    "market_value_jpy": _float(value),
                    "portfolio_weight": _float(value / total),
                    "mapped": "分類済み" if mapped else "その他・未分類",
                }
            )
            if group == "sector":
                sectors.append(
                    {
                        "scope": scope,
                        "sector": category,
                        "market_value_jpy": _float(value),
                        "portfolio_weight": _float(value / total),
                        "sector_weight": _float(value / sector_total) if sector_total else None,
                        "mapped": "分類済み" if mapped else "その他・未分類",
                    }
                )

        pe_value = Decimal()
        fresh_pe_value = Decimal()
        earnings_proxy = Decimal()
        high_pe_value = Decimal()
        for symbol, market_value in by_symbol.items():
            instrument = reference.instruments.get(symbol)
            if instrument is None or instrument.valuation is None:
                continue
            valuation = instrument.valuation
            equity_weight = instrument.factor_loadings.get("株式全体", Decimal())
            covered_value = market_value * equity_weight
            if covered_value <= 0:
                continue
            pe_value += covered_value
            earnings_proxy += covered_value / valuation.pe
            if valuation.quality == "current":
                fresh_pe_value += covered_value
            if valuation.pe >= Decimal("30"):
                high_pe_value += covered_value
            age_days = (
                date.fromisoformat(reference.as_of) - date.fromisoformat(valuation.as_of)
            ).days
            valuations.append(
                {
                    "scope": scope,
                    "position": f"{symbol} · {position_names[symbol]}",
                    "asset_class": position_asset_classes[symbol],
                    "pe": _float(valuation.pe),
                    "earnings_yield": _float(Decimal("1") / valuation.pe),
                    "pe_basis": valuation.basis,
                    "pe_as_of": valuation.as_of,
                    "age_days": age_days,
                    "quality": {
                        "current": "現行",
                        "stale": "要更新",
                        "estimated": "推定",
                    }[valuation.quality],
                    "market_value_jpy": _float(market_value),
                    "valuation_value_jpy": _float(covered_value),
                    "portfolio_weight": _float(market_value / total),
                    "method": valuation.method,
                    "note": valuation.note,
                    "source_ids": ", ".join(instrument.source_ids),
                }
            )

        for scenario in reference.scenarios:
            scenario_impact = Decimal()
            affected_value = Decimal()
            contributions: list[tuple[Decimal, str, Decimal]] = []
            for symbol, market_value in by_symbol.items():
                instrument = reference.instruments.get(symbol)
                if instrument is None:
                    continue
                coefficient = sum(
                    (
                        instrument.factor_loadings.get(factor, Decimal()) * shock
                        for factor, shock in scenario.shocks.items()
                    ),
                    Decimal(),
                )
                impact = market_value * coefficient
                if impact == 0:
                    continue
                scenario_impact += impact
                affected_value += market_value
                contributions.append((abs(impact), symbol, impact))
            sensitivity.append(
                {
                    "scope": scope,
                    "scenario": scenario.label,
                    "impact_jpy": _float(scenario_impact),
                    "impact_ratio": _float(scenario_impact / total),
                    "ending_value_jpy": _float(total + scenario_impact),
                    "affected_value_jpy": _float(affected_value),
                    "assumption": scenario.assumption,
                }
            )
            for _magnitude, symbol, impact in sorted(contributions, reverse=True):
                sensitivity_contributions.append(
                    {
                        "scope": scope,
                        "scenario": scenario.label,
                        "position": f"{symbol} · {position_names[symbol]}",
                        "impact_jpy": _float(impact),
                        "portfolio_impact": _float(impact / total),
                    }
                )

        summary_metrics[scope] = {
            "sector_coverage_ratio": (
                _float(mapped_sector_total / sector_total) if sector_total else None
            ),
            "valuation_coverage_ratio": _float(pe_value / equity_total) if equity_total else None,
            "fresh_valuation_coverage_ratio": (
                _float(fresh_pe_value / equity_total) if equity_total else None
            ),
            "mixed_basis_pe": _float(pe_value / earnings_proxy) if earnings_proxy else None,
            "high_pe_equity_ratio": _float(high_pe_value / equity_total) if equity_total else None,
        }

    return (
        {
            "lookthrough_allocation": lookthrough,
            "sector_exposure": sectors,
            "factor_sensitivity": sensitivity,
            "sensitivity_contributions": sensitivity_contributions,
            "valuation_detail": valuations,
        },
        summary_metrics,
    )


def _scope_rows(portfolio: Portfolio) -> dict[str, list[dict[str, Any]]]:
    account_names = {account.id: account.name for account in portfolio.accounts}
    summary: list[dict[str, Any]] = []
    account_allocation: list[dict[str, Any]] = []
    asset_allocation: list[dict[str, Any]] = []
    currency_allocation: list[dict[str, Any]] = []
    concentration: list[dict[str, Any]] = []
    holdings_detail: list[dict[str, Any]] = []
    stress: list[dict[str, Any]] = []

    for scope, positions in _scopes(portfolio):
        total = sum((position.market_value_jpy for position in positions), Decimal())
        if total <= 0:
            continue
        cash = sum((p.market_value_jpy for p in positions if p.asset_class == "現金"), Decimal())
        foreign = sum((p.market_value_jpy for p in positions if p.currency != "JPY"), Decimal())
        exact = sum((p.market_value_jpy for p in positions if p.value_status == "exact"), Decimal())
        investable = [p for p in positions if p.asset_class not in {"現金", "未分類"}]
        ranked = sorted(investable, key=lambda position: position.market_value_jpy, reverse=True)
        top_five = sum((position.market_value_jpy for position in ranked[:5]), Decimal())
        largest = ranked[0].market_value_jpy if ranked else Decimal()
        summary.append(
            {
                "scope": scope,
                "total_value_jpy": _float(total),
                "cash_ratio": _float(cash / total),
                "foreign_currency_ratio": _float(foreign / total),
                "largest_position_ratio": _float(largest / total),
                "top_five_ratio": _float(top_five / total),
                "confirmed_detail_ratio": _float(exact / total),
            }
        )

        by_account: defaultdict[str, Decimal] = defaultdict(Decimal)
        by_asset: defaultdict[str, Decimal] = defaultdict(Decimal)
        by_currency: defaultdict[str, Decimal] = defaultdict(Decimal)
        for position in positions:
            by_account[account_names[position.account_id]] += position.market_value_jpy
            by_asset[position.asset_class] += position.market_value_jpy
            by_currency[position.currency] += position.market_value_jpy

        account_allocation.extend(
            {
                "scope": scope,
                "account": account,
                "market_value_jpy": _float(value),
                "weight": _float(value / total),
            }
            for account, value in sorted(by_account.items(), key=lambda item: item[1], reverse=True)
        )
        asset_allocation.extend(
            {
                "scope": scope,
                "asset_class": asset_class,
                "market_value_jpy": _float(value),
                "weight": _float(value / total),
            }
            for asset_class, value in sorted(
                by_asset.items(), key=lambda item: item[1], reverse=True
            )
        )
        currency_allocation.extend(
            {
                "scope": scope,
                "currency": currency,
                "market_value_jpy": _float(value),
                "weight": _float(value / total),
            }
            for currency, value in sorted(
                by_currency.items(), key=lambda item: item[1], reverse=True
            )
        )

        concentration.extend(
            {
                "scope": scope,
                "position": f"{position.symbol} · {position.name}",
                "account": account_names[position.account_id],
                "market_value_jpy": _float(position.market_value_jpy),
                "weight": _float(position.market_value_jpy / total),
                "value_status": STATUS_LABELS[position.value_status],
            }
            for position in ranked[:8]
        )
        holdings_detail.extend(
            {
                "scope": scope,
                "account": account_names[position.account_id],
                "symbol": position.symbol,
                "name": position.name,
                "asset_class": position.asset_class,
                "currency": position.currency,
                "quantity": _float(position.quantity),
                "price": _float(position.price),
                "fx_rate": _float(position.fx_rate),
                "market_value_jpy": _float(position.market_value_jpy),
                "weight": _float(position.market_value_jpy / total),
                "value_status": STATUS_LABELS[position.value_status],
                "source_note": position.source_note,
            }
            for position in positions
        )

        for scenario_name, shocks in SCENARIOS.items():
            impact = sum(
                (
                    position.market_value_jpy * shocks.get(position.asset_class, Decimal("-0.10"))
                    for position in positions
                ),
                Decimal(),
            )
            stress.append(
                {
                    "scope": scope,
                    "scenario": scenario_name,
                    "impact_jpy": _float(impact),
                    "impact_ratio": _float(impact / total),
                    "ending_value_jpy": _float(total + impact),
                }
            )

    return {
        "summary": summary,
        "account_allocation": account_allocation,
        "asset_allocation": asset_allocation,
        "currency_allocation": currency_allocation,
        "concentration": concentration,
        "holdings_detail": holdings_detail,
        "stress": stress,
    }


def build_artifact(
    portfolio: Portfolio,
    *,
    analysis_reference: AnalysisReference | None = None,
    generated_at: str | None = None,
    source_path: str = "data/portfolio.private.json",
    reference_source_path: str = "data/analysis_reference.private.json",
) -> dict[str, Any]:
    """Build a canonical portable dashboard artifact."""
    issues = validate_portfolio(portfolio)
    if issues:
        raise ValueError("; ".join(issues))
    generated_at = generated_at or datetime.now(UTC).isoformat(timespec="seconds")
    datasets = _scope_rows(portfolio)
    source = _source()
    source["path"] = source_path
    sources = [source]
    if analysis_reference is not None:
        analysis_datasets, analysis_summary = _analysis_rows(portfolio, analysis_reference)
        datasets.update(analysis_datasets)
        for row in datasets["summary"]:
            row.update(analysis_summary[row["scope"]])
        sources.append(_analysis_source(reference_source_path))
        sources.extend(dict(reference_source) for reference_source in analysis_reference.sources)
    dataset_queries = _materialize_datasets_with_sql(datasets)
    latest_as_of = max(account.as_of for account in portfolio.accounts)
    account_notes = "\n".join(
        f"- **{account.name}**（{account.as_of}）: {account.quality_note}"
        for account in portfolio.accounts
    )
    scenario_notes = " / ".join(
        f"{name}: 日本株 {float(shocks['日本株']):+.0%}, 米国株 {float(shocks['米国株']):+.0%}"
        for name, shocks in SCENARIOS.items()
    )

    artifact = {
        "surface": "dashboard",
        "manifest": {
            "version": 1,
            "surface": "dashboard",
            "title": "ポジション・リスクレーダー",
            "description": (
                "複数口座のスナップショットを統合し、配分・集中度・通貨・簡易ストレスを確認"
            ),
            "generatedAt": generated_at,
            "filters": [
                {
                    "id": "scope",
                    "label": "表示する口座",
                    "dataset": "summary",
                    "field": "scope",
                    "defaultValue": "すべて",
                    "includeAll": False,
                    "targets": [
                        {"dataset": name, "field": "scope"}
                        for name in datasets
                        if name != "summary"
                    ],
                }
            ],
            "cards": [
                {
                    "id": "total_value",
                    "description": "選択した口座範囲の評価額合計。",
                    "dataset": "summary",
                    "sourceId": source["id"],
                    "metrics": [
                        {
                            "label": "総資産",
                            "field": "total_value_jpy",
                            "format": "currency",
                        }
                    ],
                },
                {
                    "id": "cash_ratio",
                    "description": "総資産のうち円現金として分類した割合。",
                    "dataset": "summary",
                    "sourceId": source["id"],
                    "metrics": [{"label": "現金比率", "field": "cash_ratio", "format": "percent"}],
                },
                {
                    "id": "foreign_ratio",
                    "description": "通貨がJPY以外のポジション評価額の割合。",
                    "dataset": "summary",
                    "sourceId": source["id"],
                    "metrics": [
                        {
                            "label": "外貨ポジション比率",
                            "field": "foreign_currency_ratio",
                            "format": "percent",
                        }
                    ],
                },
                {
                    "id": "largest_position",
                    "description": "現金・残高調整を除く最大ポジションの総資産比。",
                    "dataset": "summary",
                    "sourceId": source["id"],
                    "metrics": [
                        {
                            "label": "最大ポジション比率",
                            "field": "largest_position_ratio",
                            "format": "percent",
                        }
                    ],
                },
                {
                    "id": "top_five",
                    "description": "現金・残高調整を除く上位5ポジションの総資産比。",
                    "dataset": "summary",
                    "sourceId": source["id"],
                    "metrics": [
                        {"label": "上位5比率", "field": "top_five_ratio", "format": "percent"}
                    ],
                },
                {
                    "id": "confirmed_ratio",
                    "description": "明細評価額がスクリーンショット等で確定できた割合。",
                    "dataset": "summary",
                    "sourceId": source["id"],
                    "metrics": [
                        {
                            "label": "明細確定率",
                            "field": "confirmed_detail_ratio",
                            "format": "percent",
                        }
                    ],
                },
            ],
            "charts": [
                {
                    "id": "accounts",
                    "title": "口座別の評価額",
                    "subtitle": f"単位: 円 / 最新基準日: {latest_as_of}",
                    "intent": "comparison",
                    "question": "資産がどの口座に置かれているか",
                    "rationale": "長い口座名と金額を比較しやすい横棒を使用。",
                    "comparisonContext": {"grain": "口座", "unit": "JPY"},
                    "type": "horizontalBar",
                    "dataset": "account_allocation",
                    "sourceId": source["id"],
                    "encodings": {
                        "x": {"field": "account", "type": "nominal", "label": "口座"},
                        "y": {
                            "field": "market_value_jpy",
                            "type": "quantitative",
                            "label": "評価額",
                            "format": "currency",
                        },
                        "tooltip": [
                            {
                                "field": "weight",
                                "type": "quantitative",
                                "label": "構成比",
                                "format": "percent",
                            }
                        ],
                    },
                    "valueFormat": "currency",
                    "unit": "JPY",
                    "layout": "half",
                    "palette": {"kind": "sequential", "name": "blue"},
                    "settings": {"sort": "descending", "showValues": True},
                },
                {
                    "id": "asset_classes",
                    "title": "資産クラス別の評価額",
                    "subtitle": "単位: 円。分類は入力スナップショットに基づく",
                    "intent": "composition",
                    "question": "どの資産クラスに偏っているか",
                    "rationale": "金額差と小さな分類を正確に比較できる横棒を使用。",
                    "comparisonContext": {"denominator": "選択範囲の総資産", "unit": "JPY"},
                    "type": "horizontalBar",
                    "dataset": "asset_allocation",
                    "sourceId": source["id"],
                    "encodings": {
                        "x": {
                            "field": "asset_class",
                            "type": "nominal",
                            "label": "資産クラス",
                        },
                        "y": {
                            "field": "market_value_jpy",
                            "type": "quantitative",
                            "label": "評価額",
                            "format": "currency",
                        },
                        "tooltip": [
                            {
                                "field": "weight",
                                "type": "quantitative",
                                "label": "構成比",
                                "format": "percent",
                            }
                        ],
                    },
                    "valueFormat": "currency",
                    "unit": "JPY",
                    "layout": "half",
                    "palette": {"kind": "sequential", "name": "blue"},
                    "settings": {"sort": "descending", "showValues": True},
                },
                {
                    "id": "currencies",
                    "title": "通貨別の構成",
                    "subtitle": "JPY / USD。外貨は円換算後の評価額",
                    "intent": "composition",
                    "question": "為替変動の影響を受ける資産はどの程度か",
                    "rationale": "総資産を分母とする100%積み上げ棒で構成を表示。",
                    "comparisonContext": {
                        "denominator": "選択範囲の総資産",
                        "normalization": "100%",
                    },
                    "type": "stackedBar100",
                    "dataset": "currency_allocation",
                    "sourceId": source["id"],
                    "encodings": {
                        "x": {"field": "scope", "type": "nominal", "label": "表示範囲"},
                        "y": {
                            "field": "market_value_jpy",
                            "type": "quantitative",
                            "label": "評価額",
                        },
                        "color": {"field": "currency", "type": "nominal", "label": "通貨"},
                        "tooltip": [
                            {
                                "field": "weight",
                                "type": "quantitative",
                                "label": "構成比",
                                "format": "percent",
                            }
                        ],
                    },
                    "valueFormat": "percent",
                    "layout": "half",
                    "palette": {"kind": "categorical", "name": "blue-gold"},
                    "legend": {"position": "bottom", "title": "通貨"},
                    "settings": {"groupMode": "stacked100", "showPercent": True},
                },
                {
                    "id": "concentration",
                    "title": "上位ポジション",
                    "subtitle": "現金と残高調整を除く上位8件 / 単位: 円",
                    "intent": "comparison",
                    "question": "個別ポジションの集中はどこにあるか",
                    "rationale": "銘柄名を読みながら金額を比較できる横棒を使用。",
                    "comparisonContext": {"grain": "ポジション", "unit": "JPY"},
                    "type": "horizontalBar",
                    "dataset": "concentration",
                    "sourceId": source["id"],
                    "encodings": {
                        "x": {
                            "field": "position",
                            "type": "nominal",
                            "label": "ポジション",
                        },
                        "y": {
                            "field": "market_value_jpy",
                            "type": "quantitative",
                            "label": "評価額",
                            "format": "currency",
                        },
                        "tooltip": [
                            {"field": "account", "type": "text", "label": "口座"},
                            {
                                "field": "weight",
                                "type": "quantitative",
                                "label": "総資産比",
                                "format": "percent",
                            },
                            {"field": "value_status", "type": "text", "label": "データ状態"},
                        ],
                    },
                    "valueFormat": "currency",
                    "unit": "JPY",
                    "layout": "half",
                    "palette": {"kind": "sequential", "name": "blue"},
                    "settings": {"sort": "descending", "showValues": True, "limit": 8},
                },
                {
                    "id": "stress",
                    "title": "簡易ストレスシナリオ",
                    "subtitle": "仮定した価格ショックによる評価額変化。予測ではない",
                    "intent": "decomposition",
                    "question": "仮定した相場下落時に評価額がどの程度変化するか",
                    "rationale": "損失額をゼロ基準の横棒で比較。",
                    "comparisonContext": {"baseline": "現在評価額", "unit": "JPY"},
                    "type": "horizontalBar",
                    "dataset": "stress",
                    "sourceId": source["id"],
                    "encodings": {
                        "x": {
                            "field": "scenario",
                            "type": "nominal",
                            "label": "シナリオ",
                        },
                        "y": {
                            "field": "impact_jpy",
                            "type": "quantitative",
                            "label": "評価額変化",
                            "format": "currency",
                        },
                        "tooltip": [
                            {
                                "field": "impact_ratio",
                                "type": "quantitative",
                                "label": "変化率",
                                "format": "percent",
                            },
                            {
                                "field": "ending_value_jpy",
                                "type": "quantitative",
                                "label": "シナリオ後評価額",
                                "format": "currency",
                            },
                        ],
                    },
                    "valueFormat": "currency",
                    "unit": "JPY",
                    "layout": "full",
                    "palette": {"kind": "sequential", "name": "orange"},
                    "referenceLines": [
                        {"axis": "x", "value": 0, "label": "現在", "color": "neutral"}
                    ],
                    "settings": {"sort": "descending", "showValues": True},
                },
            ],
            "tables": [
                {
                    "id": "positions",
                    "title": "保有明細",
                    "subtitle": "確定・推定・残高調整を区別したスナップショット",
                    "dataset": "holdings_detail",
                    "sourceId": source["id"],
                    "defaultSort": {"field": "market_value_jpy", "direction": "desc"},
                    "density": "dense",
                    "layout": "full",
                    "columns": [
                        {"field": "account", "label": "口座", "type": "text"},
                        {"field": "symbol", "label": "銘柄", "type": "text"},
                        {"field": "name", "label": "名称", "type": "text"},
                        {"field": "asset_class", "label": "資産クラス", "type": "text"},
                        {"field": "currency", "label": "通貨", "type": "text"},
                        {"field": "market_value_jpy", "label": "評価額", "format": "currency"},
                        {"field": "weight", "label": "構成比", "format": "percent"},
                        {"field": "value_status", "label": "状態", "type": "text"},
                    ],
                }
            ],
            "sources": sources,
            "blocks": [
                {
                    "id": "intro",
                    "type": "markdown",
                    "body": (
                        "## 現在地\n\n口座を切り替えて、配分・集中・通貨・下落時の影響を確認できます。"
                        "まず **明細確定率** が低い口座では推定値を更新してください。"
                    ),
                },
                {
                    "id": "metrics",
                    "type": "metric-strip",
                    "cardIds": [
                        "total_value",
                        "cash_ratio",
                        "foreign_ratio",
                        "largest_position",
                        "top_five",
                        "confirmed_ratio",
                    ],
                },
                {"id": "accounts_block", "type": "chart", "chartId": "accounts", "layout": "half"},
                {
                    "id": "asset_block",
                    "type": "chart",
                    "chartId": "asset_classes",
                    "layout": "half",
                },
                {
                    "id": "currency_block",
                    "type": "chart",
                    "chartId": "currencies",
                    "layout": "half",
                },
                {
                    "id": "concentration_block",
                    "type": "chart",
                    "chartId": "concentration",
                    "layout": "half",
                },
                {"id": "stress_block", "type": "chart", "chartId": "stress", "layout": "full"},
                {
                    "id": "scenario_notes",
                    "type": "markdown",
                    "body": f"## シナリオ前提\n\n{scenario_notes}\n\n予測や売買推奨ではなく、感応度を見るための固定仮定です。",
                    "sourceId": source["id"],
                },
                {
                    "id": "positions_block",
                    "type": "table",
                    "tableId": "positions",
                    "layout": "full",
                },
                {
                    "id": "quality_notes",
                    "type": "markdown",
                    "body": f"## データ品質と更新日\n\n{account_notes}",
                    "sourceId": source["id"],
                },
            ],
        },
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": "ready",
            "datasets": datasets,
        },
        "sources": sources,
    }
    if analysis_reference is not None:
        _extend_analysis_manifest(
            artifact,
            analysis_reference,
            reference_source_path=reference_source_path,
        )
    _attach_widget_sources(
        artifact,
        dataset_queries,
        generated_at=generated_at,
        source_path=source_path,
        reference_source_path=(reference_source_path if analysis_reference is not None else None),
    )
    return artifact


def _extend_analysis_manifest(
    artifact: dict[str, Any],
    reference: AnalysisReference,
    *,
    reference_source_path: str,
) -> None:
    """Add look-through, factor sensitivity, and valuation views in place."""
    manifest = artifact["manifest"]
    analysis_source_id = "analysis_reference"
    manifest["cards"].extend(
        [
            {
                "id": "sector_coverage",
                "description": "セクターとして展開した評価額のうち、広義分類を付けた割合。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "セクター分類率",
                        "field": "sector_coverage_ratio",
                        "format": "percent",
                    }
                ],
            },
            {
                "id": "valuation_coverage",
                "description": "実効株式評価額のうち、PER参照値を持つ部分の割合。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "PERカバー率",
                        "field": "valuation_coverage_ratio",
                        "format": "percent",
                    }
                ],
            },
            {
                "id": "fresh_valuation_coverage",
                "description": "実効株式評価額のうち、現行扱いのPERで確認できた割合。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "現行PERカバー率",
                        "field": "fresh_valuation_coverage_ratio",
                        "format": "percent",
                    }
                ],
            },
            {
                "id": "mixed_pe",
                "description": (
                    "入手できたPERを評価額で調和平均した参考値。予想・実績基準が混在。"
                ),
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "参考・混在基準PER",
                        "field": "mixed_basis_pe",
                        "format": "number",
                        "unit": "倍",
                    }
                ],
            },
            {
                "id": "high_pe_exposure",
                "description": "実効株式評価額のうち、参照PERが30倍以上の部分。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "PER30倍以上の株式比率",
                        "field": "high_pe_equity_ratio",
                        "format": "percent",
                    }
                ],
            },
        ]
    )
    metric_block = next(block for block in manifest["blocks"] if block["id"] == "metrics")
    metric_block["cardIds"].extend(
        [
            "sector_coverage",
            "valuation_coverage",
            "fresh_valuation_coverage",
            "mixed_pe",
            "high_pe_exposure",
        ]
    )

    manifest["charts"].extend(
        [
            {
                "id": "sector_exposure",
                "title": "株式・REITのルックスルー・セクター",
                "subtitle": f"評価額ベース / 参照データ基準日: {reference.as_of}",
                "intent": "composition",
                "question": "ETFやバランスファンドの中身まで含めると何に偏っているか",
                "rationale": "長いセクター名と金額を比較しやすい横棒を使用。",
                "comparisonContext": {
                    "denominator": "選択範囲の総資産",
                    "grain": "広義セクター",
                    "unit": "JPY",
                },
                "type": "horizontalBar",
                "dataset": "sector_exposure",
                "sourceId": analysis_source_id,
                "encodings": {
                    "x": {"field": "sector", "type": "nominal", "label": "セクター"},
                    "y": {
                        "field": "market_value_jpy",
                        "type": "quantitative",
                        "label": "ルックスルー評価額",
                        "format": "currency",
                    },
                    "tooltip": [
                        {
                            "field": "portfolio_weight",
                            "type": "quantitative",
                            "label": "総資産比",
                            "format": "percent",
                        },
                        {
                            "field": "sector_weight",
                            "type": "quantitative",
                            "label": "株式・REIT内比率",
                            "format": "percent",
                        },
                        {"field": "mapped", "type": "text", "label": "分類状態"},
                    ],
                },
                "valueFormat": "currency",
                "unit": "JPY",
                "layout": "full",
                "palette": {"kind": "sequential", "name": "blue"},
                "settings": {"sort": "descending", "showValues": True},
            },
            {
                "id": "factor_sensitivity",
                "title": "1ファクター感応度",
                "subtitle": "他の条件を固定した線形近似。予測・VaR・最大損失ではない",
                "intent": "comparison",
                "question": "主要な市場要因が単独で動いたとき、評価額にどれだけ影響するか",
                "rationale": "標準ショックごとの損益をゼロ基準の横棒で比較。",
                "comparisonContext": {"baseline": "現在評価額", "unit": "JPY"},
                "type": "horizontalBar",
                "dataset": "factor_sensitivity",
                "sourceId": analysis_source_id,
                "encodings": {
                    "x": {"field": "scenario", "type": "nominal", "label": "標準ショック"},
                    "y": {
                        "field": "impact_jpy",
                        "type": "quantitative",
                        "label": "評価額変化",
                        "format": "currency",
                    },
                    "tooltip": [
                        {
                            "field": "impact_ratio",
                            "type": "quantitative",
                            "label": "総資産比",
                            "format": "percent",
                        },
                        {
                            "field": "ending_value_jpy",
                            "type": "quantitative",
                            "label": "ショック後評価額",
                            "format": "currency",
                        },
                        {"field": "assumption", "type": "text", "label": "前提"},
                    ],
                },
                "valueFormat": "currency",
                "unit": "JPY",
                "layout": "full",
                "palette": {"kind": "sequential", "name": "orange"},
                "referenceLines": [
                    {"axis": "x", "value": 0, "label": "変化なし", "color": "neutral"}
                ],
                "settings": {"sort": "ascending", "showValues": True},
            },
            {
                "id": "valuation_pe",
                "title": "保有商品のPER",
                "subtitle": "倍率。実績・予想・ETF提供値が混在するため基準欄と鮮度を併読",
                "intent": "comparison",
                "question": "PERを取得できた保有商品で割高・割安のばらつきはどうか",
                "rationale": "商品名ごとの倍率差を比較しやすい横棒を使用。",
                "comparisonContext": {"grain": "口座横断の商品", "unit": "x"},
                "type": "horizontalBar",
                "dataset": "valuation_detail",
                "sourceId": analysis_source_id,
                "encodings": {
                    "x": {"field": "position", "type": "nominal", "label": "商品"},
                    "y": {
                        "field": "pe",
                        "type": "quantitative",
                        "label": "PER",
                        "format": "number",
                    },
                    "tooltip": [
                        {"field": "pe_basis", "type": "text", "label": "基準"},
                        {"field": "pe_as_of", "type": "text", "label": "基準日"},
                        {"field": "quality", "type": "text", "label": "鮮度"},
                        {
                            "field": "portfolio_weight",
                            "type": "quantitative",
                            "label": "総資産比",
                            "format": "percent",
                        },
                    ],
                },
                "valueFormat": "number",
                "unit": "倍",
                "layout": "full",
                "palette": {"kind": "sequential", "name": "blue"},
                "referenceLines": [{"axis": "x", "value": 30, "label": "30倍", "color": "neutral"}],
                "settings": {"sort": "descending", "showValues": True},
            },
        ]
    )

    manifest["tables"].extend(
        [
            {
                "id": "valuation_details",
                "title": "PERの定義・鮮度",
                "subtitle": "混在基準のため、商品間比較は方向感として使用",
                "dataset": "valuation_detail",
                "sourceId": analysis_source_id,
                "defaultSort": {"field": "pe", "direction": "desc"},
                "density": "dense",
                "layout": "full",
                "columns": [
                    {"field": "position", "label": "商品", "type": "text"},
                    {"field": "pe", "label": "PER", "format": "number"},
                    {"field": "pe_basis", "label": "基準", "type": "text"},
                    {"field": "pe_as_of", "label": "基準日", "type": "text"},
                    {"field": "age_days", "label": "経過日", "format": "number"},
                    {"field": "quality", "label": "鮮度", "type": "text"},
                    {
                        "field": "market_value_jpy",
                        "label": "評価額",
                        "format": "currency",
                    },
                    {"field": "method", "label": "算出方法", "type": "text"},
                ],
            },
            {
                "id": "sensitivity_details",
                "title": "感応度の主な寄与ポジション",
                "subtitle": "各標準ショックのポジション別評価額変化",
                "dataset": "sensitivity_contributions",
                "sourceId": analysis_source_id,
                "defaultSort": {"field": "impact_jpy", "direction": "asc"},
                "density": "dense",
                "layout": "full",
                "columns": [
                    {"field": "scenario", "label": "標準ショック", "type": "text"},
                    {"field": "position", "label": "商品", "type": "text"},
                    {"field": "impact_jpy", "label": "評価額変化", "format": "currency"},
                    {
                        "field": "portfolio_impact",
                        "label": "総資産比",
                        "format": "percent",
                    },
                ],
            },
        ]
    )

    scenario_notes = "\n".join(
        f"- **{scenario.label}**: {scenario.assumption}" for scenario in reference.scenarios
    )
    source_links = " / ".join(
        f"[{source['label']}]({source['href']})"
        for source in reference.sources
        if source.get("href")
    )
    analysis_blocks = [
        {
            "id": "advanced_analysis_intro",
            "type": "markdown",
            "body": (
                "## ルックスルー分析\n\nETFとバランスファンドを内部構成へ展開し、"
                "セクター、主要ファクター、PERを別々に確認します。未分類と古い参照値は"
                "カバー率に残し、見えない部分をゼロとは扱いません。"
            ),
        },
        {
            "id": "sector_analysis_block",
            "type": "chart",
            "chartId": "sector_exposure",
            "layout": "full",
        },
        {
            "id": "factor_sensitivity_block",
            "type": "chart",
            "chartId": "factor_sensitivity",
            "layout": "full",
        },
        {
            "id": "factor_method",
            "type": "markdown",
            "body": (
                "## 感応度の前提\n\n"
                f"{scenario_notes}\n\n"
                "複数要因が同時に動く局面では相関や非線形性が生じるため、単純加算は概算です。"
            ),
            "sourceId": analysis_source_id,
        },
        {
            "id": "sensitivity_details_block",
            "type": "table",
            "tableId": "sensitivity_details",
            "layout": "full",
        },
        {
            "id": "valuation_pe_block",
            "type": "chart",
            "chartId": "valuation_pe",
            "layout": "full",
        },
        {
            "id": "valuation_method",
            "type": "markdown",
            "body": (
                "## PERの読み方\n\n**参考・混在基準PER**は、取得できた商品のPERを"
                "評価額で調和平均した一次診断です。個別株の会社予想PER、ETF提供会社の"
                "ポートフォリオPER、古い参照値が混在するため、厳密な市場横断比較には使えません。"
                "REIT、債券、現金、ハッピーエイジング40はPER集計から除外しています。"
            ),
            "sourceId": analysis_source_id,
        },
        {
            "id": "valuation_details_block",
            "type": "table",
            "tableId": "valuation_details",
            "layout": "full",
        },
        {
            "id": "analysis_sources",
            "type": "markdown",
            "body": (
                "## 分析参照データ\n\n"
                f"ローカル参照ファイル: `{reference_source_path}` / 基準日: {reference.as_of}\n\n"
                f"{source_links}"
            ),
        },
    ]
    insert_at = next(
        index for index, block in enumerate(manifest["blocks"]) if block["id"] == "accounts_block"
    )
    manifest["blocks"][insert_at:insert_at] = analysis_blocks
