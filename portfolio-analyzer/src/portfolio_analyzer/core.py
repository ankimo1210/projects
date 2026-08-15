"""Portfolio data validation, aggregation, and dashboard artifact generation."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any

ALLOWED_VALUE_STATUSES = {"exact", "estimated", "reconciliation"}
ALLOWED_POSITION_TYPES = {"asset", "short", "liability", "hedge"}
ALLOWED_VALUATION_BASIS_KINDS = {"trailing", "forward", "provider"}
ALLOWED_SCENARIO_KINDS = {"single", "compound", "historical"}
PERIODS_PER_YEAR = {"daily": Decimal("252"), "weekly": Decimal("52"), "monthly": Decimal("12")}
SCENARIO_KIND_LABELS = {"single": "単一", "compound": "複合", "historical": "実測"}
STATUS_LABELS = {
    "exact": "確定",
    "estimated": "推定",
    "reconciliation": "残高調整",
}
ACCOUNT_TYPE_LABELS = {
    "cash": "現金口座",
    "defined_contribution": "確定拠出年金",
    "unknown": "未確認",
}
TAX_CATEGORY_LABELS = {
    "nisa": "NISA",
    "tax_deferred": "課税繰延",
    "taxable": "課税口座",
    "unknown": "未確認",
}
FX_RATE_STATUS_LABELS = {
    "confirmed": "確認済み",
    "reconciliation_implied": "残高から逆算",
    "proposal": "提案固定値",
    "exact": "確定",
    "unknown": "未確認",
}
ASSET_CLASS_SCENARIOS: dict[str, dict[str, Decimal]] = {
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
    account_type: str
    base_currency: str
    purpose: str
    tax_category: str


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
    position_type: str
    average_cost: Decimal | None
    average_cost_currency: str | None
    tax_category: str
    fx_rate_status: str


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
    theme: str | None = None


@dataclass(frozen=True)
class Valuation:
    pe: Decimal
    basis: str
    as_of: str
    quality: str
    method: str
    note: str
    basis_kind: str


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
    kind: str


@dataclass(frozen=True)
class FactorRisk:
    """Measured factor covariance used to rank how plausible a shock set is."""

    factors: tuple[str, ...]
    covariance: tuple[tuple[Decimal, ...], ...]
    observations: int
    frequency: str
    estimated_at: str
    window_start: str
    dates: tuple[str, ...] = ()
    series: tuple[tuple[Decimal, ...], ...] = ()

    @property
    def periods_per_year(self) -> Decimal:
        return PERIODS_PER_YEAR.get(self.frequency, Decimal("1"))

    def column(self, factor: str) -> tuple[Decimal, ...]:
        """Return one factor's realised series."""
        index = self.factors.index(factor)
        return tuple(row[index] for row in self.series)

    def matvec(self, vector: dict[str, Decimal]) -> dict[str, Decimal]:
        """Return the covariance matrix applied to a factor-indexed vector."""
        return {
            row_factor: sum(
                (
                    self.covariance[row][column] * vector.get(column_factor, Decimal())
                    for column, column_factor in enumerate(self.factors)
                ),
                Decimal(),
            )
            for row, row_factor in enumerate(self.factors)
        }

    def quadratic_form(self, vector: dict[str, Decimal]) -> Decimal:
        """Return v' * covariance * v."""
        applied = self.matvec(vector)
        return sum(
            (vector.get(factor, Decimal()) * applied[factor] for factor in self.factors),
            Decimal(),
        )


@dataclass(frozen=True)
class ScenarioEvent:
    """A dated catalyst that a registered scenario is meant to describe."""

    id: str
    date: str
    label: str
    scenario_id: str | None
    note: str


@dataclass(frozen=True)
class PolicyLimit:
    id: str
    label: str
    metric: str
    operator: str
    threshold: Decimal
    note: str


@dataclass(frozen=True)
class AnalysisReference:
    reference_name: str
    as_of: str
    instruments: dict[str, InstrumentReference]
    scenarios: tuple[FactorScenario, ...]
    events: tuple[ScenarioEvent, ...]
    sources: tuple[dict[str, Any], ...]
    factor_definitions: dict[str, str]
    mutually_exclusive_factor_sets: tuple[tuple[str, ...], ...]
    policy_limits: tuple[PolicyLimit, ...]
    policy_status: str


@dataclass(frozen=True)
class ProposalResult:
    name: str
    portfolio: Portfolio
    trade_details: tuple[dict[str, Any], ...]
    assumptions: tuple[str, ...]


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
    raw = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
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
            account_type=str(row.get("account_type", "unspecified")),
            base_currency=str(row.get("base_currency", raw.get("base_currency", "JPY"))),
            purpose=str(row.get("purpose", "")),
            tax_category=str(row.get("tax_category", "unknown")),
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
            position_type=str(row.get("position_type", "asset")),
            average_cost=_decimal(row.get("average_cost"), "average_cost", nullable=True),
            average_cost_currency=(
                str(row["average_cost_currency"])
                if row.get("average_cost_currency") is not None
                else None
            ),
            tax_category=str(row.get("tax_category", "unknown")),
            fx_rate_status=str(row.get("fx_rate_status", "exact")),
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
    raw = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
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
                basis_kind=str(valuation_raw.get("basis_kind", "provider")),
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
                    theme=str(exposure["theme"]) if exposure.get("theme") else None,
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
            kind=str(row.get("kind", "single")),
        )
        for row in raw["scenarios"]
    )
    events = tuple(
        ScenarioEvent(
            id=str(row["id"]),
            date=str(row["date"]),
            label=str(row["label"]),
            scenario_id=str(row["scenario_id"]) if row.get("scenario_id") else None,
            note=str(row.get("note", "")),
        )
        for row in raw.get("events", [])
    )
    reference = AnalysisReference(
        reference_name=str(raw["reference_name"]),
        as_of=str(raw["as_of"]),
        instruments=instruments,
        scenarios=scenarios,
        events=events,
        sources=tuple(dict(source) for source in raw.get("sources", [])),
        factor_definitions={
            str(factor): str(definition)
            for factor, definition in raw.get("factor_definitions", {}).items()
        },
        mutually_exclusive_factor_sets=tuple(
            tuple(str(factor) for factor in factor_set)
            for factor_set in raw.get("mutually_exclusive_factor_sets", [])
        ),
        policy_limits=tuple(
            PolicyLimit(
                id=str(limit["id"]),
                label=str(limit["label"]),
                metric=str(limit["metric"]),
                operator=str(limit["operator"]),
                threshold=_decimal(limit["threshold"], f"policy.{limit['id']}.threshold"),
                note=str(limit.get("note", "")),
            )
            for limit in raw.get("policy", {}).get("limits", [])
        ),
        policy_status=str(raw.get("policy", {}).get("status", "not_configured")),
    )
    issues = validate_analysis_reference(reference)
    if issues:
        raise ValueError("; ".join(issues))
    return reference


def load_factor_risk(path: Path) -> FactorRisk:
    """Load the measured factor covariance written by scripts/estimate_factors.py."""
    raw = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
    block = raw["factor_risk"]
    factors = tuple(str(factor) for factor in block["factors"])
    covariance = tuple(
        tuple(_decimal(value, "factor_risk.covariance") for value in row)
        for row in block["covariance"]
    )
    history = raw.get("factor_series", {})
    dates: tuple[str, ...] = ()
    series: tuple[tuple[Decimal, ...], ...] = ()
    if history:
        if tuple(str(factor) for factor in history["factors"]) != factors:
            raise ValueError("factor_series columns do not match factor_risk factors")
        dates = tuple(str(stamp) for stamp in history["dates"])
        series = tuple(
            tuple(_decimal(value, "factor_series.values") for value in row)
            for row in history["values"]
        )
        if len(dates) != len(series):
            raise ValueError("factor_series dates and values disagree in length")
    risk = FactorRisk(
        factors=factors,
        covariance=covariance,
        observations=int(block["observations"]),
        frequency=str(block.get("frequency", "weekly")),
        estimated_at=str(raw.get("manifest", {}).get("generated_at", "")),
        window_start=str(raw.get("manifest", {}).get("estimation_window_start", "")),
        dates=dates,
        series=series,
    )
    issues = validate_factor_risk(risk)
    if issues:
        raise ValueError("; ".join(issues))
    return risk


def validate_factor_risk(risk: FactorRisk) -> list[str]:
    """Return problems that would make the covariance unusable."""
    issues: list[str] = []
    size = len(risk.factors)
    if size == 0:
        issues.append("factor risk has no factors")
    if len(set(risk.factors)) != size:
        issues.append("factor names must be unique")
    if len(risk.covariance) != size or any(len(row) != size for row in risk.covariance):
        issues.append("covariance must be square and match the factor list")
        return issues
    for index in range(size):
        if risk.covariance[index][index] <= 0:
            issues.append(f"non-positive variance: {risk.factors[index]}")
        for other in range(index + 1, size):
            upper = risk.covariance[index][other]
            lower = risk.covariance[other][index]
            if upper != lower:
                issues.append(
                    f"covariance is not symmetric: {risk.factors[index]}/{risk.factors[other]}"
                )
    if risk.observations <= size:
        issues.append("covariance needs more observations than factors")
    return issues


def most_plausible_shock(
    exposures: dict[str, Decimal], risk: FactorRisk, target_loss: Decimal
) -> tuple[dict[str, Decimal], Decimal]:
    r"""Return the smallest shock set that produces ``target_loss``, and its distance.

    Loss is linear in the factor shocks, :math:`L(s) = b^\top s`, so asking which
    shock set is the least surprising one that still loses ``target_loss`` is

    .. math::

        \min_s s^\top \Sigma^{-1} s \quad \text{s.t.} \quad b^\top s = -L^*

    whose solution needs no matrix inverse:

    .. math::

        s^* = -L^* \frac{\Sigma b}{b^\top \Sigma b}, \qquad
        d = \frac{L^*}{\sqrt{b^\top \Sigma b}}

    ``d`` is the Mahalanobis distance in units of one period's standard
    deviation — the covariance's own frequency, not an annual figure. It ranks
    how far out a loss sits; it is not a probability.
    """
    scale = risk.quadratic_form(exposures)
    if scale <= 0:
        return {}, Decimal()
    applied = risk.matvec(exposures)
    shocks = {factor: -target_loss * applied[factor] / scale for factor in risk.factors}
    distance = target_loss / scale.sqrt()
    return shocks, distance


def replay_returns(exposures: dict[str, Decimal], risk: FactorRisk, total: Decimal) -> list[Decimal]:
    """Return the portfolio return the current holdings would have had each period.

    This is a replay, not a track record: past factor moves are applied to
    today's exposures, so it says nothing about what the portfolio actually
    earned.
    """
    if not risk.series or total <= 0:
        return []
    return [
        sum(
            (
                exposures.get(factor, Decimal()) * row[index]
                for index, factor in enumerate(risk.factors)
            ),
            Decimal(),
        )
        / total
        for row in risk.series
    ]


def expected_shortfall(returns: list[Decimal], level: Decimal = Decimal("0.975")) -> Decimal | None:
    """Return the mean of the worst losses beyond ``level``, as a positive number."""
    if not returns:
        return None
    # Decimal's // truncates toward zero, so ask for the ceiling explicitly.
    exact = Decimal(len(returns)) * (Decimal("1") - level)
    tail_size = int(exact.to_integral_value(rounding=ROUND_CEILING))
    if tail_size < 1:
        return None
    tail = sorted(returns)[:tail_size]
    return -sum(tail, Decimal()) / Decimal(len(tail))


def maximum_drawdown(returns: list[Decimal]) -> Decimal | None:
    """Return the deepest peak-to-trough fall of the compounded replay."""
    if not returns:
        return None
    level = Decimal("1")
    peak = Decimal("1")
    worst = Decimal()
    for period in returns:
        level *= Decimal("1") + period
        peak = max(peak, level)
        worst = max(worst, (peak - level) / peak)
    return worst


def correlation(left: tuple[Decimal, ...], right: tuple[Decimal, ...]) -> Decimal | None:
    """Return Pearson correlation, or None when either series does not vary."""
    count = len(left)
    if count < 2 or count != len(right):
        return None
    left_mean = sum(left, Decimal()) / count
    right_mean = sum(right, Decimal()) / count
    covariance = sum(
        ((a - left_mean) * (b - right_mean) for a, b in zip(left, right, strict=True)), Decimal()
    )
    left_spread = sum(((a - left_mean) ** 2 for a in left), Decimal())
    right_spread = sum(((b - right_mean) ** 2 for b in right), Decimal())
    if left_spread <= 0 or right_spread <= 0:
        return None
    return covariance / (left_spread * right_spread).sqrt()


def apply_proposal(portfolio: Portfolio, path: Path) -> ProposalResult:
    """Apply quantity changes and offset their value against same-account JPY cash."""
    raw = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
    positions = list(portfolio.positions)
    index = {(position.account_id, position.symbol): position for position in positions}
    cash_deltas: defaultdict[str, Decimal] = defaultdict(Decimal)
    trade_details: list[dict[str, Any]] = []

    for row in raw.get("trades", []):
        account_id = str(row["account_id"])
        symbol = str(row["symbol"])
        key = (account_id, symbol)
        current = index.get(key)
        quantity_delta = _decimal(row["quantity_delta"], f"proposal.{symbol}.quantity_delta")
        if quantity_delta == 0:
            raise ValueError(f"zero proposal quantity_delta: {account_id}/{symbol}")
        price = _decimal(
            row.get("price", current.price if current else None),
            f"proposal.{symbol}.price",
        )
        fx_rate = _decimal(
            row.get("fx_rate", current.fx_rate if current else None),
            f"proposal.{symbol}.fx_rate",
        )
        old_quantity = current.quantity if current and current.quantity is not None else Decimal()
        new_quantity = old_quantity + quantity_delta
        if new_quantity < 0:
            raise ValueError(f"proposal sells more than held: {account_id}/{symbol}")
        value_delta = quantity_delta * price * fx_rate
        cash_deltas[account_id] -= value_delta

        if current is None:
            current = Position(
                account_id=account_id,
                symbol=symbol,
                name=str(row["name"]),
                asset_class=str(row["asset_class"]),
                currency=str(row["currency"]),
                quantity=Decimal(),
                price=price,
                fx_rate=fx_rate,
                market_value_jpy=Decimal(),
                value_status=str(row.get("value_status", "estimated")),
                source_note="提案ファイルから追加",
                position_type="asset",
                average_cost=None,
                average_cost_currency=None,
                tax_category=str(row.get("tax_category", "unknown")),
                fx_rate_status=str(row.get("fx_rate_status", "proposal")),
            )
            positions.append(current)
            index[key] = current

        native_gain = None
        if quantity_delta < 0 and current.average_cost is not None:
            native_gain = (-quantity_delta) * (price - current.average_cost)
        updated = replace(
            current,
            quantity=new_quantity,
            price=price,
            fx_rate=fx_rate,
            market_value_jpy=new_quantity * price * fx_rate,
            value_status="estimated",
            source_note=f"提案適用: {quantity_delta:+f} units",
        )
        position_index = positions.index(current)
        positions[position_index] = updated
        index[key] = updated
        trade_details.append(
            {
                "account_id": account_id,
                "symbol": symbol,
                "quantity_before": _float(old_quantity),
                "quantity_delta": _float(quantity_delta),
                "quantity_after": _float(new_quantity),
                "price": _float(price),
                "fx_rate": _float(fx_rate),
                "value_delta_jpy": _float(value_delta),
                "native_realized_gain_estimate": _float(native_gain),
                "tax_status": (
                    "現地通貨損益のみ。税務上の円換算取得原価は未確認"
                    if native_gain is not None
                    else "取得原価未入力のため未計算"
                ),
            }
        )

    for account_id, cash_delta in cash_deltas.items():
        cash_key = (account_id, "CASH_JPY")
        cash = index.get(cash_key)
        if cash is None:
            cash = Position(
                account_id=account_id,
                symbol="CASH_JPY",
                name="円現金",
                asset_class="現金",
                currency="JPY",
                quantity=None,
                price=None,
                fx_rate=Decimal("1"),
                market_value_jpy=Decimal(),
                value_status="estimated",
                source_note="提案の資金差額",
                position_type="asset",
                average_cost=None,
                average_cost_currency=None,
                tax_category="unknown",
                fx_rate_status="exact",
            )
            positions.append(cash)
        updated_cash = replace(
            cash,
            market_value_jpy=cash.market_value_jpy + cash_delta,
            value_status="estimated",
            source_note="提案売買の資金差額（税・手数料を除く）",
        )
        if updated_cash.market_value_jpy < 0:
            raise ValueError(f"proposal creates negative cash: {account_id}")
        cash_index = positions.index(cash)
        positions[cash_index] = updated_cash
        index[cash_key] = updated_cash

    proposed = replace(
        portfolio,
        snapshot_name=f"{portfolio.snapshot_name}（提案後）",
        positions=tuple(position for position in positions if position.quantity != 0),
    )
    issues = validate_portfolio(proposed)
    if issues:
        raise ValueError("; ".join(issues))
    return ProposalResult(
        name=str(raw.get("proposal_name", path.stem)),
        portfolio=proposed,
        trade_details=tuple(trade_details),
        assumptions=tuple(str(value) for value in raw.get("assumptions", [])),
    )


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
    known_factors: set[str] = set()
    for instrument in reference.instruments.values():
        try:
            date.fromisoformat(instrument.as_of)
        except ValueError:
            issues.append(f"invalid instrument as_of: {instrument.symbol}")
        if any(exposure.weight < 0 for exposure in instrument.exposures):
            issues.append(f"negative exposure weight: {instrument.symbol}")
        primary_exposure_total = sum(
            (exposure.weight for exposure in instrument.exposures if exposure.group != "issuer"),
            Decimal(),
        )
        if primary_exposure_total > Decimal("1.01"):
            issues.append(
                "primary exposure weights exceed 101%: "
                f"{instrument.symbol} ({primary_exposure_total:.4f})"
            )
        issuer_total = sum(
            (exposure.weight for exposure in instrument.exposures if exposure.group == "issuer"),
            Decimal(),
        )
        if issuer_total > Decimal("1.01"):
            issues.append(
                f"issuer exposure weights exceed 101%: {instrument.symbol} ({issuer_total:.4f})"
            )
        exposure_keys = [(exposure.group, exposure.category) for exposure in instrument.exposures]
        if len(exposure_keys) != len(set(exposure_keys)):
            issues.append(f"duplicate exposure category: {instrument.symbol}")
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
            if instrument.valuation.basis_kind not in ALLOWED_VALUATION_BASIS_KINDS:
                issues.append(f"invalid valuation basis_kind: {instrument.symbol}")
            try:
                date.fromisoformat(instrument.valuation.as_of)
            except ValueError:
                issues.append(f"invalid valuation as_of: {instrument.symbol}")
        known_factors.update(instrument.factor_loadings)

    scenario_ids = [scenario.id for scenario in reference.scenarios]
    if len(scenario_ids) != len(set(scenario_ids)):
        issues.append("scenario ids must be unique")
    if any(not scenario.shocks for scenario in reference.scenarios):
        issues.append("every scenario must have at least one shock")
    for scenario in reference.scenarios:
        if scenario.kind not in ALLOWED_SCENARIO_KINDS:
            issues.append(f"invalid scenario kind: {scenario.id}")
        unknown_factors = set(scenario.shocks) - known_factors
        if unknown_factors:
            issues.append(
                f"unknown scenario factors for {scenario.id}: {', '.join(sorted(unknown_factors))}"
            )
        for factor_set in reference.mutually_exclusive_factor_sets:
            active = [
                factor for factor in factor_set if scenario.shocks.get(factor, Decimal()) != 0
            ]
            if len(active) > 1:
                issues.append(f"mutually exclusive factors in {scenario.id}: {', '.join(active)}")

    event_ids = [event.id for event in reference.events]
    if len(event_ids) != len(set(event_ids)):
        issues.append("event ids must be unique")
    known_scenario_ids = set(scenario_ids)
    for event in reference.events:
        try:
            date.fromisoformat(event.date)
        except ValueError:
            issues.append(f"invalid event date: {event.id}")
        if event.scenario_id is not None and event.scenario_id not in known_scenario_ids:
            issues.append(f"unknown scenario for event {event.id}: {event.scenario_id}")

    policy_ids = [limit.id for limit in reference.policy_limits]
    if len(policy_ids) != len(set(policy_ids)):
        issues.append("policy limit ids must be unique")
    supported_policy_metrics = {
        "cash_ratio",
        "largest_position_ratio",
        "max_sector_ratio",
        "sector_effective_count",
        "worst_compound_drawdown",
        "worst_historical_drawdown",
    }
    for limit in reference.policy_limits:
        if limit.operator not in {"<=", ">=", "between"}:
            issues.append(f"invalid policy operator: {limit.id}")
        if limit.metric not in supported_policy_metrics:
            issues.append(f"unsupported policy metric: {limit.id}/{limit.metric}")
        if limit.threshold < 0:
            issues.append(f"negative policy threshold: {limit.id}")
    return issues


def validate_portfolio(portfolio: Portfolio, tolerance_jpy: Decimal = Decimal("1")) -> list[str]:
    """Return validation issues; an empty list means the snapshot reconciles."""
    issues: list[str] = []
    account_ids = [account.id for account in portfolio.accounts]
    if len(account_ids) != len(set(account_ids)):
        issues.append("account ids must be unique")

    known_accounts = set(account_ids)
    known_asset_classes = set().union(*(set(shocks) for shocks in ASSET_CLASS_SCENARIOS.values()))
    totals: defaultdict[str, Decimal] = defaultdict(Decimal)
    position_keys: set[tuple[str, str]] = set()
    for position in portfolio.positions:
        if position.account_id not in known_accounts:
            issues.append(f"unknown account_id: {position.account_id}")
        if position.position_type not in ALLOWED_POSITION_TYPES:
            issues.append(f"invalid position_type: {position.account_id}/{position.symbol}")
        if position.position_type == "asset" and position.market_value_jpy < 0:
            issues.append(f"negative market value: {position.account_id}/{position.symbol}")
        if position.asset_class not in known_asset_classes:
            issues.append(f"unsupported asset_class: {position.account_id}/{position.symbol}")
        if position.value_status not in ALLOWED_VALUE_STATUSES:
            issues.append(f"invalid value_status: {position.value_status}")
        if position.average_cost is not None and position.average_cost <= 0:
            issues.append(f"non-positive average_cost: {position.account_id}/{position.symbol}")
        if (position.average_cost is None) != (position.average_cost_currency is None):
            issues.append(
                f"average cost currency mismatch: {position.account_id}/{position.symbol}"
            )
        has_quantity = position.quantity is not None
        has_price = position.price is not None
        if has_quantity != has_price:
            issues.append(f"partial quantity/price: {position.account_id}/{position.symbol}")
        if has_quantity and position.fx_rate is None:
            issues.append(f"missing fx_rate: {position.account_id}/{position.symbol}")
        if has_quantity and position.fx_rate is not None:
            expected_value = position.quantity * position.price * position.fx_rate
            value_difference = expected_value - position.market_value_jpy
            if abs(value_difference) > tolerance_jpy:
                issues.append(
                    "position value mismatch: "
                    f"{position.account_id}/{position.symbol} ({value_difference:+,.2f} JPY)"
                )
        key = (position.account_id, position.symbol)
        if key in position_keys:
            issues.append(f"duplicate position: {position.account_id}/{position.symbol}")
        position_keys.add(key)
        totals[position.account_id] += position.market_value_jpy

    for account in portfolio.accounts:
        try:
            date.fromisoformat(account.as_of)
        except ValueError:
            issues.append(f"invalid account as_of: {account.id}")
        if account.total_value_jpy < 0:
            issues.append(f"negative account total: {account.id}")
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


def _proposal_source(path: str) -> dict[str, Any]:
    return {
        "id": "proposal",
        "label": "ローカルのリバランス提案",
        "path": path,
    }


def _dataset_projection_queries(
    datasets: dict[str, list[dict[str, Any]]],
) -> dict[str, str]:
    """Return deterministic SQL projections without mutating reviewed dataset rows."""
    queries: dict[str, str] = {}
    for dataset, rows in datasets.items():
        if not rows:
            continue
        fields = list(rows[0])
        if any(list(row) != fields for row in rows):
            raise ValueError(f"inconsistent dataset columns: {dataset}")
        selected_fields = ", ".join(f'"{field}"' for field in fields)
        queries[dataset] = f'SELECT {selected_fields} FROM "{dataset}" ORDER BY rowid'
    return queries


def _attach_widget_sources(
    artifact: dict[str, Any],
    queries: dict[str, str],
    *,
    generated_at: str,
    source_path: str,
    reference_source_path: str | None,
    proposal_source_path: str | None,
) -> None:
    """Attach deterministic projection SQL and transformation provenance."""
    inputs = [source_path]
    if reference_source_path is not None:
        inputs.append(reference_source_path)
    if proposal_source_path is not None:
        inputs.append(proposal_source_path)
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
                    "description": (
                        f"Pythonで検証済みの {dataset} スナップショット行を表示用に投影。"
                    ),
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


def _instrument_equity_weight(reference: InstrumentReference) -> Decimal:
    sector_weight = sum(
        (exposure.weight for exposure in reference.exposures if exposure.group == "sector"),
        Decimal(),
    )
    return min(sector_weight, Decimal("1"))


def _equity_loading(position: Position, reference: InstrumentReference | None) -> Decimal:
    if reference is not None:
        return _instrument_equity_weight(reference)
    return Decimal("1") if position.asset_class in {"日本株", "米国株"} else Decimal()


def _analysis_rows(
    portfolio: Portfolio, reference: AnalysisReference
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, float | None]]]:
    lookthrough: list[dict[str, Any]] = []
    sectors: list[dict[str, Any]] = []
    sensitivity: list[dict[str, Any]] = []
    sensitivity_contributions: list[dict[str, Any]] = []
    factor_loadings: list[dict[str, Any]] = []
    valuations: list[dict[str, Any]] = []
    issuers: list[dict[str, Any]] = []
    event_calendar: list[dict[str, Any]] = []
    themes: list[dict[str, Any]] = []
    summary_metrics: dict[str, dict[str, float | None]] = {}

    for scope, positions in _scopes(portfolio):
        total = sum((position.market_value_jpy for position in positions), Decimal())
        if total <= 0:
            continue

        exposure_values: defaultdict[tuple[str, str, bool], Decimal] = defaultdict(Decimal)
        issuer_values: defaultdict[str, Decimal] = defaultdict(Decimal)
        theme_values: defaultdict[str, Decimal] = defaultdict(Decimal)
        theme_members: defaultdict[str, set[str]] = defaultdict(set)
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
            primary_exposures = tuple(
                exposure for exposure in raw_exposures if exposure.group != "issuer"
            )
            issuer_exposures = tuple(
                exposure for exposure in raw_exposures if exposure.group == "issuer"
            )
            raw_weight = sum((exposure.weight for exposure in primary_exposures), Decimal())
            scale = Decimal("1") / raw_weight if raw_weight > Decimal("1") else Decimal("1")
            assigned = Decimal()
            for exposure in primary_exposures:
                weight = exposure.weight * scale
                assigned += weight
                exposure_values[(exposure.group, exposure.category, exposure.mapped)] += (
                    position.market_value_jpy * weight
                )
            for exposure in issuer_exposures:
                issuer_values[exposure.category] += position.market_value_jpy * exposure.weight
                if exposure.theme:
                    theme_values[exposure.theme] += position.market_value_jpy * exposure.weight
                    theme_members[exposure.theme].add(exposure.category)
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
        sector_hhi = sum(
            (value / sector_total) ** 2
            for (group, _category, _mapped), value in exposure_values.items()
            if group == "sector" and sector_total
        )
        max_sector_value = max(
            (
                value
                for (group, _category, _mapped), value in exposure_values.items()
                if group == "sector"
            ),
            default=Decimal(),
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

        issuer_known_total = sum(issuer_values.values(), Decimal())
        for issuer, value in sorted(issuer_values.items(), key=lambda item: item[1], reverse=True):
            issuers.append(
                {
                    "scope": scope,
                    "issuer": issuer,
                    "market_value_jpy": _float(value),
                    "portfolio_weight": _float(value / total),
                    "known_issuer_weight": (
                        _float(value / issuer_known_total) if issuer_known_total else None
                    ),
                }
            )

        for theme, value in sorted(theme_values.items(), key=lambda item: item[1], reverse=True):
            themes.append(
                {
                    "scope": scope,
                    "theme": theme,
                    "market_value_jpy": _float(value),
                    "portfolio_weight": _float(value / total),
                    "issuer_count": len(theme_members[theme]),
                    "issuers": "、".join(sorted(theme_members[theme])),
                }
            )

        pe_value = Decimal()
        fresh_pe_value = Decimal()
        pe_values: defaultdict[str, Decimal] = defaultdict(Decimal)
        pe_earnings: defaultdict[str, Decimal] = defaultdict(Decimal)
        fresh_pe_values: defaultdict[str, Decimal] = defaultdict(Decimal)
        high_pe_values: defaultdict[str, Decimal] = defaultdict(Decimal)
        for symbol, market_value in by_symbol.items():
            instrument = reference.instruments.get(symbol)
            if instrument is None or instrument.valuation is None:
                continue
            valuation = instrument.valuation
            equity_weight = _instrument_equity_weight(instrument)
            covered_value = market_value * equity_weight
            if covered_value <= 0:
                continue
            pe_value += covered_value
            pe_values[valuation.basis_kind] += covered_value
            pe_earnings[valuation.basis_kind] += covered_value / valuation.pe
            if valuation.quality == "current":
                fresh_pe_value += covered_value
                fresh_pe_values[valuation.basis_kind] += covered_value
            if valuation.pe >= Decimal("30"):
                high_pe_values[valuation.basis_kind] += covered_value
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
                    "basis_kind": {
                        "trailing": "実績",
                        "forward": "予想",
                        "provider": "提供会社基準",
                    }[valuation.basis_kind],
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

        compound_impact_ratios: list[Decimal] = []
        historical_impact_ratios: list[Decimal] = []
        for symbol, market_value in by_symbol.items():
            instrument = reference.instruments.get(symbol)
            if instrument is None:
                continue
            factor_loadings.extend(
                {
                    "scope": scope,
                    "position": f"{symbol} · {position_names[symbol]}",
                    "factor": factor,
                    "loading": _float(loading),
                    "market_value_jpy": _float(market_value),
                    "portfolio_weighted_loading": _float(market_value / total * loading),
                    "method_note": instrument.note,
                }
                for factor, loading in sorted(instrument.factor_loadings.items())
            )
        scenario_impacts: dict[str, tuple[Decimal, Decimal, str]] = {}
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
                    "scenario_kind": SCENARIO_KIND_LABELS[scenario.kind],
                    "impact_jpy": _float(scenario_impact),
                    "impact_ratio": _float(scenario_impact / total),
                    "ending_value_jpy": _float(total + scenario_impact),
                    "affected_value_jpy": _float(affected_value),
                    "assumption": scenario.assumption,
                }
            )
            scenario_impacts[scenario.id] = (
                scenario_impact,
                scenario_impact / total,
                scenario.label,
            )
            if scenario.kind == "compound":
                compound_impact_ratios.append(scenario_impact / total)
            if scenario.kind == "historical":
                historical_impact_ratios.append(scenario_impact / total)
            for _magnitude, symbol, impact in sorted(contributions, reverse=True):
                sensitivity_contributions.append(
                    {
                        "scope": scope,
                        "scenario": scenario.label,
                        "scenario_kind": SCENARIO_KIND_LABELS[scenario.kind],
                        "position": f"{symbol} · {position_names[symbol]}",
                        "impact_jpy": _float(impact),
                        "portfolio_impact": _float(impact / total),
                    }
                )

        reference_date = date.fromisoformat(reference.as_of)
        for event in sorted(reference.events, key=lambda item: (item.date, item.id)):
            linked = scenario_impacts.get(event.scenario_id) if event.scenario_id else None
            event_calendar.append(
                {
                    "scope": scope,
                    "event_date": event.date,
                    "days_until": (date.fromisoformat(event.date) - reference_date).days,
                    "event": event.label,
                    "scenario": linked[2] if linked else "対応シナリオ未登録",
                    "impact_jpy": _float(linked[0]) if linked else None,
                    "impact_ratio": _float(linked[1]) if linked else None,
                    "note": event.note,
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
            "trailing_pe": (
                _float(pe_values["trailing"] / pe_earnings["trailing"])
                if pe_earnings["trailing"]
                else None
            ),
            "forward_pe": (
                _float(pe_values["forward"] / pe_earnings["forward"])
                if pe_earnings["forward"]
                else None
            ),
            "provider_pe": (
                _float(pe_values["provider"] / pe_earnings["provider"])
                if pe_earnings["provider"]
                else None
            ),
            "trailing_valuation_coverage_ratio": (
                _float(pe_values["trailing"] / equity_total) if equity_total else None
            ),
            "forward_valuation_coverage_ratio": (
                _float(pe_values["forward"] / equity_total) if equity_total else None
            ),
            "provider_valuation_coverage_ratio": (
                _float(pe_values["provider"] / equity_total) if equity_total else None
            ),
            "trailing_fresh_coverage_ratio": (
                _float(fresh_pe_values["trailing"] / equity_total) if equity_total else None
            ),
            "forward_fresh_coverage_ratio": (
                _float(fresh_pe_values["forward"] / equity_total) if equity_total else None
            ),
            "trailing_high_pe_equity_ratio": (
                _float(high_pe_values["trailing"] / equity_total) if equity_total else None
            ),
            "forward_high_pe_equity_ratio": (
                _float(high_pe_values["forward"] / equity_total) if equity_total else None
            ),
            "sector_effective_count": _float(Decimal("1") / sector_hhi) if sector_hhi else None,
            "max_sector_ratio": _float(max_sector_value / total),
            "largest_theme_ratio": (
                _float(max(theme_values.values()) / total) if theme_values else None
            ),
            "issuer_coverage_ratio": (
                _float(issuer_known_total / equity_total) if equity_total else None
            ),
            "worst_compound_drawdown": (
                _float(max(-min(compound_impact_ratios), Decimal()))
                if compound_impact_ratios
                else None
            ),
            "worst_historical_drawdown": (
                _float(max(-min(historical_impact_ratios), Decimal()))
                if historical_impact_ratios
                else None
            ),
        }

    return (
        {
            "lookthrough_allocation": lookthrough,
            "sector_exposure": sectors,
            "factor_sensitivity": sensitivity,
            "sensitivity_contributions": sensitivity_contributions,
            "factor_loadings": factor_loadings,
            "valuation_detail": valuations,
            "issuer_exposure": issuers,
            "theme_exposure": themes,
            "event_calendar": event_calendar,
        },
        summary_metrics,
    )


def _scope_rows(portfolio: Portfolio) -> dict[str, list[dict[str, Any]]]:
    account_names = {account.id: account.name for account in portfolio.accounts}
    accounts_by_id = {account.id: account for account in portfolio.accounts}
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
        investable_total = sum((position.market_value_jpy for position in investable), Decimal())
        investable_by_symbol: defaultdict[str, Decimal] = defaultdict(Decimal)
        for position in investable:
            investable_by_symbol[position.symbol] += position.market_value_jpy
        position_hhi = (
            sum(
                (market_value / investable_total) ** 2
                for market_value in investable_by_symbol.values()
            )
            if investable_total
            else Decimal()
        )
        cost_covered_value = sum(
            (
                position.market_value_jpy
                for position in investable
                if position.average_cost is not None
            ),
            Decimal(),
        )
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
                "position_effective_count": (
                    _float(Decimal("1") / position_hhi) if position_hhi else None
                ),
                "cost_basis_coverage_ratio": (
                    _float(cost_covered_value / investable_total) if investable_total else None
                ),
            }
        )

        by_account: defaultdict[str, Decimal] = defaultdict(Decimal)
        by_asset: defaultdict[str, Decimal] = defaultdict(Decimal)
        by_currency: defaultdict[str, Decimal] = defaultdict(Decimal)
        for position in positions:
            by_account[position.account_id] += position.market_value_jpy
            by_asset[position.asset_class] += position.market_value_jpy
            by_currency[position.currency] += position.market_value_jpy

        account_allocation.extend(
            {
                "scope": scope,
                "account": accounts_by_id[account_id].name,
                "market_value_jpy": _float(value),
                "weight": _float(value / total),
                "unrealized_pnl_jpy": _float(accounts_by_id[account_id].unrealized_pnl_jpy),
                "implied_cost_basis_jpy": (
                    _float(value - accounts_by_id[account_id].unrealized_pnl_jpy)
                    if accounts_by_id[account_id].unrealized_pnl_jpy is not None
                    else None
                ),
                "unrealized_return": (
                    _float(
                        accounts_by_id[account_id].unrealized_pnl_jpy
                        / (value - accounts_by_id[account_id].unrealized_pnl_jpy)
                    )
                    if accounts_by_id[account_id].unrealized_pnl_jpy is not None
                    and value - accounts_by_id[account_id].unrealized_pnl_jpy > 0
                    else None
                ),
                "daily_pnl_jpy": _float(accounts_by_id[account_id].daily_pnl_jpy),
                "account_type": ACCOUNT_TYPE_LABELS.get(
                    accounts_by_id[account_id].account_type,
                    accounts_by_id[account_id].account_type,
                ),
                "base_currency": accounts_by_id[account_id].base_currency,
                "purpose": accounts_by_id[account_id].purpose,
                "tax_category": TAX_CATEGORY_LABELS.get(
                    accounts_by_id[account_id].tax_category,
                    accounts_by_id[account_id].tax_category,
                ),
                "as_of": accounts_by_id[account_id].as_of,
                "quality_note": accounts_by_id[account_id].quality_note,
            }
            for account_id, value in sorted(
                by_account.items(), key=lambda item: item[1], reverse=True
            )
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
                "fx_rate_status": FX_RATE_STATUS_LABELS.get(
                    position.fx_rate_status, position.fx_rate_status
                ),
                "market_value_jpy": _float(position.market_value_jpy),
                "weight": _float(position.market_value_jpy / total),
                "value_status": STATUS_LABELS[position.value_status],
                "average_cost": _float(position.average_cost),
                "average_cost_currency": position.average_cost_currency,
                "native_unrealized_pnl": (
                    _float((position.price - position.average_cost) * position.quantity)
                    if position.price is not None
                    and position.quantity is not None
                    and position.average_cost is not None
                    and position.average_cost_currency == position.currency
                    else None
                ),
                "native_unrealized_return": (
                    _float(position.price / position.average_cost - Decimal("1"))
                    if position.price is not None
                    and position.average_cost is not None
                    and position.average_cost_currency == position.currency
                    else None
                ),
                "tax_category": TAX_CATEGORY_LABELS.get(
                    position.tax_category, position.tax_category
                ),
                "source_note": position.source_note,
            }
            for position in positions
        )

        for scenario_name, shocks in ASSET_CLASS_SCENARIOS.items():
            impact = Decimal()
            for position in positions:
                shock = shocks.get(position.asset_class)
                if shock is None:
                    raise ValueError(
                        f"unsupported asset_class in stress model: {position.asset_class}"
                    )
                impact += position.market_value_jpy * shock
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


def _evaluate_policy(
    summary_rows: list[dict[str, Any]], limits: tuple[PolicyLimit, ...]
) -> list[dict[str, Any]]:
    """Evaluate draft portfolio guardrails against each dashboard scope."""
    checks: list[dict[str, Any]] = []
    for summary in summary_rows:
        breach_count = 0
        for limit in limits:
            raw_value = summary.get(limit.metric)
            if raw_value is None:
                passed = None
                distance = None
            else:
                value = Decimal(str(raw_value))
                if limit.operator == "<=":
                    passed = value <= limit.threshold
                    distance = limit.threshold - value
                elif limit.operator == ">=":
                    passed = value >= limit.threshold
                    distance = value - limit.threshold
                else:  # validated before evaluation
                    raise ValueError(f"unsupported policy operator: {limit.operator}")
            if passed is False:
                breach_count += 1
            checks.append(
                {
                    "scope": summary["scope"],
                    "rule": limit.label,
                    "metric": limit.metric,
                    "operator": limit.operator,
                    "value": raw_value,
                    "threshold": _float(limit.threshold),
                    "distance_to_limit": _float(distance),
                    "status": (
                        "範囲内" if passed is True else "超過" if passed is False else "未計算"
                    ),
                    "note": limit.note,
                }
            )
        summary["policy_breach_count"] = breach_count
    return checks


DRAWDOWN_POLICY_METRICS = ("worst_compound_drawdown", "worst_historical_drawdown")


def _factor_exposures(
    positions: tuple[Position, ...], reference: AnalysisReference, factors: tuple[str, ...]
) -> dict[str, Decimal]:
    """Return b: the JPY value that moves per unit of each factor."""
    exposures = dict.fromkeys(factors, Decimal())
    for position in positions:
        instrument = reference.instruments.get(position.symbol)
        if instrument is None:
            continue
        for factor in factors:
            loading = instrument.factor_loadings.get(factor)
            if loading:
                exposures[factor] += position.market_value_jpy * loading
    return exposures


def _reverse_stress_rows(
    portfolio: Portfolio, reference: AnalysisReference, risk: FactorRisk
) -> tuple[list[dict[str, Any]], dict[str, dict[str, float | None]]]:
    """Solve, for each policy drawdown limit, the least surprising way to breach it."""
    targets = [
        (limit.label, limit.threshold)
        for limit in reference.policy_limits
        if limit.metric in DRAWDOWN_POLICY_METRICS and limit.operator == "<="
    ]
    rows: list[dict[str, Any]] = []
    metrics: dict[str, dict[str, float | None]] = {}
    for scope, positions in _scopes(portfolio):
        total = sum((position.market_value_jpy for position in positions), Decimal())
        if total <= 0:
            continue
        exposures = _factor_exposures(positions, reference, risk.factors)
        variance = risk.quadratic_form(exposures)
        period_volatility = variance.sqrt() / total if variance > 0 else None
        metrics[scope] = {
            "factor_period_volatility": _float(period_volatility),
            "factor_annual_volatility": (
                _float(period_volatility * risk.periods_per_year.sqrt())
                if period_volatility is not None
                else None
            ),
            "nearest_limit_distance_sigma": None,
        }
        distances: list[Decimal] = []
        for label, threshold in targets:
            target_loss = threshold * total
            shocks, distance = most_plausible_shock(exposures, risk, target_loss)
            if not shocks:
                continue
            distances.append(distance)
            for factor, shock in sorted(
                shocks.items(), key=lambda item: abs(item[1]), reverse=True
            ):
                contribution = exposures[factor] * shock
                rows.append(
                    {
                        "scope": scope,
                        "limit": label,
                        "target_loss_ratio": _float(threshold),
                        "distance_sigma": _float(distance),
                        "distance_sigma_annual": _float(distance / risk.periods_per_year.sqrt()),
                        "factor": factor,
                        "shock": _float(shock),
                        "loss_contribution_jpy": _float(contribution),
                        "loss_share": _float(contribution / -target_loss),
                    }
                )
        if distances:
            metrics[scope]["nearest_limit_distance_sigma"] = _float(min(distances))

        replayed = replay_returns(exposures, risk, total)
        shortfall = expected_shortfall(replayed)
        metrics[scope].update(
            {
                "replayed_expected_shortfall": _float(shortfall),
                "replayed_worst_period": _float(-min(replayed)) if replayed else None,
                "replayed_max_drawdown": _float(maximum_drawdown(replayed)),
            }
        )
    return rows, metrics


HEDGE_MONITOR_WINDOW = 26


def _correlation_monitor_rows(risk: FactorRisk) -> list[dict[str, Any]]:
    """Track whether Japanese bonds still move against equities.

    Bond returns move opposite to yields, so the usual stock-bond correlation
    is the negative of the equity/yield correlation. A negative reading means
    bonds cushion equity falls; a positive one means they fall together, which
    is what removes the diversification a bond sleeve is held for.
    """
    if len(risk.series) < HEDGE_MONITOR_WINDOW or "日本金利" not in risk.factors:
        return []
    equity = risk.column("株式全体")
    yields = risk.column("日本金利")
    rows: list[dict[str, Any]] = []
    for end in range(HEDGE_MONITOR_WINDOW, len(risk.series) + 1):
        window = slice(end - HEDGE_MONITOR_WINDOW, end)
        measured = correlation(equity[window], yields[window])
        if measured is None:
            continue
        stock_bond = -measured
        rows.append(
            {
                "date": risk.dates[end - 1],
                "stock_bond_correlation": _float(stock_bond),
                "regime": "債券がヘッジとして機能" if stock_bond < 0 else "株債同時安（ヘッジ失効）",
            }
        )
    return rows


def _portfolio_datasets(
    portfolio: Portfolio,
    analysis_reference: AnalysisReference | None,
    factor_risk: FactorRisk | None = None,
) -> dict[str, list[dict[str, Any]]]:
    datasets = _scope_rows(portfolio)
    if analysis_reference is None:
        return datasets
    analysis_datasets, analysis_summary = _analysis_rows(portfolio, analysis_reference)
    datasets.update(analysis_datasets)
    for row in datasets["summary"]:
        row.update(analysis_summary[row["scope"]])
    if factor_risk is not None:
        reverse_rows, reverse_metrics = _reverse_stress_rows(
            portfolio, analysis_reference, factor_risk
        )
        datasets["reverse_stress"] = reverse_rows
        monitor = _correlation_monitor_rows(factor_risk)
        if monitor:
            datasets["correlation_monitor"] = monitor
        for row in datasets["summary"]:
            row.update(reverse_metrics.get(row["scope"], {}))
            if monitor:
                row["stock_bond_correlation"] = monitor[-1]["stock_bond_correlation"]
    datasets["policy_checks"] = _evaluate_policy(
        datasets["summary"], analysis_reference.policy_limits
    )
    return datasets


def _proposal_comparison_rows(
    before: dict[str, list[dict[str, Any]]],
    after: dict[str, list[dict[str, Any]]],
    proposal: ProposalResult,
    account_names: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    before_summary = next(row for row in before["summary"] if row["scope"] == "すべて")
    after_summary = next(row for row in after["summary"] if row["scope"] == "すべて")
    metric_specs = [
        ("現金比率", "cash_ratio", "比率"),
        ("最大ポジション比率", "largest_position_ratio", "比率"),
        ("実効ポジション数", "position_effective_count", "実効数"),
        ("最大セクター比率", "max_sector_ratio", "比率"),
        ("実効セクター数", "sector_effective_count", "実効数"),
        ("複合ショック最大下落", "worst_compound_drawdown", "比率"),
        ("実績PER", "trailing_pe", "倍"),
        ("予想PER", "forward_pe", "倍"),
        ("提供会社基準PER", "provider_pe", "倍"),
        ("暫定ルール超過", "policy_breach_count", "件"),
    ]
    comparison: list[dict[str, Any]] = []
    for label, field, unit in metric_specs:
        before_value = before_summary.get(field)
        after_value = after_summary.get(field)
        if before_value is None or after_value is None:
            continue
        change = after_value - before_value
        if abs(change) < 1e-9:
            change = 0.0
        comparison.append(
            {
                "scope": "すべて",
                "metric": label,
                "before": before_value,
                "after": after_value,
                "change": change,
                "unit": unit,
            }
        )

    sensitivity_comparison: list[dict[str, Any]] = []
    if "factor_sensitivity" in before and "factor_sensitivity" in after:
        before_rows = {
            row["scenario"]: row for row in before["factor_sensitivity"] if row["scope"] == "すべて"
        }
        for row in after["factor_sensitivity"]:
            if row["scope"] != "すべて" or row["scenario"] not in before_rows:
                continue
            before_row = before_rows[row["scenario"]]
            sensitivity_comparison.append(
                {
                    "scope": "すべて",
                    "scenario": row["scenario"],
                    "scenario_kind": row["scenario_kind"],
                    "before_impact_ratio": before_row["impact_ratio"],
                    "after_impact_ratio": row["impact_ratio"],
                    "improvement": row["impact_ratio"] - before_row["impact_ratio"],
                }
            )

    trade_details = [
        {
            "scope": "すべて",
            "account": account_names.get(str(row["account_id"]), str(row["account_id"])),
            "symbol": row["symbol"],
            "quantity_before": row["quantity_before"],
            "quantity_delta": row["quantity_delta"],
            "quantity_after": row["quantity_after"],
            "value_delta_jpy": row["value_delta_jpy"],
            "native_realized_gain_estimate": row["native_realized_gain_estimate"],
            "tax_status": row["tax_status"],
        }
        for row in proposal.trade_details
    ]
    return {
        "proposal_comparison": comparison,
        "proposal_sensitivity_comparison": sensitivity_comparison,
        "proposal_trade_details": trade_details,
    }


def build_artifact(
    portfolio: Portfolio,
    *,
    analysis_reference: AnalysisReference | None = None,
    factor_risk: FactorRisk | None = None,
    proposal: ProposalResult | None = None,
    generated_at: str | None = None,
    source_path: str = "data/portfolio.private.json",
    reference_source_path: str = "data/analysis_reference.private.json",
    factor_risk_source_path: str = "data/factor_estimates.json",
    proposal_source_path: str = "data/rebalancing-proposal.private.json",
) -> dict[str, Any]:
    """Build a canonical portable dashboard artifact."""
    issues = validate_portfolio(portfolio)
    if issues:
        raise ValueError("; ".join(issues))
    generated_at = generated_at or datetime.now(UTC).isoformat(timespec="seconds")
    datasets = _portfolio_datasets(portfolio, analysis_reference, factor_risk)
    source = _source()
    source["path"] = source_path
    sources = [source]
    if analysis_reference is not None:
        sources.append(_analysis_source(reference_source_path))
        sources.extend(dict(reference_source) for reference_source in analysis_reference.sources)
    if factor_risk is not None:
        sources.append(
            {
                "id": "factor_risk",
                "label": (
                    f"実測ファクター共分散（{factor_risk.frequency}・"
                    f"{factor_risk.observations}観測・{factor_risk.window_start}以降）"
                ),
                "path": factor_risk_source_path,
            }
        )
    if proposal is not None:
        proposal_datasets = _portfolio_datasets(
            proposal.portfolio, analysis_reference, factor_risk
        )
        datasets.update(
            _proposal_comparison_rows(
                datasets,
                proposal_datasets,
                proposal,
                {account.id: account.name for account in portfolio.accounts},
            )
        )
        sources.append(_proposal_source(proposal_source_path))
    dataset_queries = _dataset_projection_queries(datasets)
    latest_as_of = max(account.as_of for account in portfolio.accounts)
    account_notes = "\n".join(
        f"- **{account.name}**（{account.as_of}）: {account.quality_note}"
        for account in portfolio.accounts
    )
    scenario_notes = " / ".join(
        f"{name}: 日本株 {float(shocks['日本株']):+.0%}, 米国株 {float(shocks['米国株']):+.0%}"
        for name, shocks in ASSET_CLASS_SCENARIOS.items()
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
                        for name, rows in datasets.items()
                        if name != "summary" and rows and "scope" in rows[0]
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
                    "id": "effective_positions",
                    "description": (
                        "現金・残高調整を除くポジションのHHI逆数。均等保有なら同数になる。"
                    ),
                    "dataset": "summary",
                    "sourceId": source["id"],
                    "metrics": [
                        {
                            "label": "実効ポジション数",
                            "field": "position_effective_count",
                            "format": "number",
                            "unit": "銘柄",
                        }
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
                            },
                            {
                                "field": "unrealized_pnl_jpy",
                                "type": "quantitative",
                                "label": "口座損益",
                                "format": "currency",
                            },
                            {
                                "field": "unrealized_return",
                                "type": "quantitative",
                                "label": "元本比損益率",
                                "format": "percent",
                            },
                            {"field": "base_currency", "type": "text", "label": "基準通貨"},
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
                    "id": "accounts_detail",
                    "title": "口座状態と損益",
                    "subtitle": "損益率は表示評価額と口座損益から逆算。元明細との照合状態を注記",
                    "dataset": "account_allocation",
                    "sourceId": source["id"],
                    "defaultSort": {"field": "market_value_jpy", "direction": "desc"},
                    "density": "dense",
                    "layout": "full",
                    "columns": [
                        {"field": "account", "label": "口座", "type": "text"},
                        {"field": "as_of", "label": "基準日", "type": "text"},
                        {"field": "account_type", "label": "口座タイプ", "type": "text"},
                        {"field": "base_currency", "label": "基準通貨", "type": "text"},
                        {"field": "market_value_jpy", "label": "評価額", "format": "currency"},
                        {
                            "field": "unrealized_pnl_jpy",
                            "label": "口座損益",
                            "format": "currency",
                        },
                        {
                            "field": "implied_cost_basis_jpy",
                            "label": "逆算元本",
                            "format": "currency",
                        },
                        {"field": "unrealized_return", "label": "元本比", "format": "percent"},
                        {"field": "tax_category", "label": "税区分", "type": "text"},
                        {"field": "quality_note", "label": "照合メモ", "type": "text"},
                    ],
                },
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
                        {"field": "price", "label": "価格", "format": "number"},
                        {"field": "fx_rate", "label": "為替", "format": "number"},
                        {"field": "fx_rate_status", "label": "為替状態", "type": "text"},
                        {"field": "average_cost", "label": "平均取得価額", "format": "number"},
                        {
                            "field": "average_cost_currency",
                            "label": "取得価額通貨",
                            "type": "text",
                        },
                        {
                            "field": "native_unrealized_pnl",
                            "label": "現地通貨損益",
                            "format": "number",
                        },
                        {
                            "field": "native_unrealized_return",
                            "label": "取得価額比",
                            "format": "percent",
                        },
                        {"field": "tax_category", "label": "税区分", "type": "text"},
                        {"field": "market_value_jpy", "label": "評価額", "format": "currency"},
                        {"field": "weight", "label": "構成比", "format": "percent"},
                        {"field": "value_status", "label": "状態", "type": "text"},
                    ],
                },
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
                        "effective_positions",
                        "confirmed_ratio",
                    ],
                },
                {"id": "accounts_block", "type": "chart", "chartId": "accounts", "layout": "half"},
                {
                    "id": "accounts_detail_block",
                    "type": "table",
                    "tableId": "accounts_detail",
                    "layout": "full",
                },
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
    if proposal is not None:
        _extend_proposal_manifest(artifact, proposal)
    _attach_widget_sources(
        artifact,
        dataset_queries,
        generated_at=generated_at,
        source_path=source_path,
        reference_source_path=(reference_source_path if analysis_reference is not None else None),
        proposal_source_path=(proposal_source_path if proposal is not None else None),
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
                "id": "effective_sectors",
                "description": "ルックスルー・セクター構成のHHI逆数。均等配分なら同数になる。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "実効セクター数",
                        "field": "sector_effective_count",
                        "format": "number",
                        "unit": "セクター",
                    }
                ],
            },
            {
                "id": "issuer_coverage",
                "description": "実効株式評価額のうち、発行体ルックスルーを付与できた割合。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "発行体カバー率",
                        "field": "issuer_coverage_ratio",
                        "format": "percent",
                    }
                ],
            },
            {
                "id": "worst_compound",
                "description": "登録済み複合シナリオのうち最大の評価額下落率。予測ではない。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "複合ショック最大下落",
                        "field": "worst_compound_drawdown",
                        "format": "percent",
                    }
                ],
            },
            {
                "id": "policy_breaches",
                "description": "暫定投資方針の上限・下限を超えているルール数。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "暫定ルール超過",
                        "field": "policy_breach_count",
                        "format": "number",
                        "unit": "件",
                    }
                ],
            },
            {
                "id": "trailing_pe",
                "description": "実績PERだけを評価額加重調和平均した値。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {"label": "実績PER", "field": "trailing_pe", "format": "number", "unit": "倍"}
                ],
            },
            {
                "id": "trailing_pe_coverage",
                "description": "実効株式評価額のうち実績PERで集計できた割合。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "実績PERカバー率",
                        "field": "trailing_valuation_coverage_ratio",
                        "format": "percent",
                    }
                ],
            },
            {
                "id": "forward_pe",
                "description": "予想PERだけを評価額加重調和平均した値。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {"label": "予想PER", "field": "forward_pe", "format": "number", "unit": "倍"}
                ],
            },
            {
                "id": "forward_pe_coverage",
                "description": "実効株式評価額のうち予想PERで集計できた割合。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "予想PERカバー率",
                        "field": "forward_valuation_coverage_ratio",
                        "format": "percent",
                    }
                ],
            },
            {
                "id": "provider_pe",
                "description": "提供会社独自基準のPERだけを評価額加重調和平均した値。",
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "提供会社基準PER",
                        "field": "provider_pe",
                        "format": "number",
                        "unit": "倍",
                    }
                ],
            },
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
                "id": "issuer_exposure",
                "title": "確認できた発行体エクスポージャー",
                "subtitle": "直接保有とETF上位保有銘柄を合算。未カバー部分は含まない",
                "intent": "comparison",
                "question": "ETFをまたいで実質的に重複している発行体はどこか",
                "rationale": "発行体名とルックスルー評価額を比較しやすい横棒を使用。",
                "comparisonContext": {
                    "denominator": "選択範囲の総資産",
                    "grain": "発行体",
                    "unit": "JPY",
                },
                "type": "horizontalBar",
                "dataset": "issuer_exposure",
                "sourceId": analysis_source_id,
                "encodings": {
                    "x": {"field": "issuer", "type": "nominal", "label": "発行体"},
                    "y": {
                        "field": "market_value_jpy",
                        "type": "quantitative",
                        "label": "確認済み評価額",
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
                            "field": "known_issuer_weight",
                            "type": "quantitative",
                            "label": "発行体カバー部分内比率",
                            "format": "percent",
                        },
                    ],
                },
                "valueFormat": "currency",
                "unit": "JPY",
                "layout": "full",
                "palette": {"kind": "sequential", "name": "blue"},
                "settings": {"sort": "descending", "showValues": True, "limit": 12},
            },
            {
                "id": "factor_sensitivity",
                "title": "市場ショック感応度",
                "subtitle": "単一要因と複合ショックの線形近似。予測・VaRではない",
                "intent": "comparison",
                "question": "主要要因が単独または同時に動いたときの評価額影響はどの程度か",
                "rationale": "登録したショックごとの損益をゼロ基準の横棒で比較。",
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
                        {"field": "scenario_kind", "type": "text", "label": "種類"},
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
                "subtitle": "倍率。実績・予想・提供会社基準を分離して表示",
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
                "subtitle": "実績・予想・提供会社基準を区別し、基準日とカバー率を併読",
                "dataset": "valuation_detail",
                "sourceId": analysis_source_id,
                "defaultSort": {"field": "pe", "direction": "desc"},
                "density": "dense",
                "layout": "full",
                "columns": [
                    {"field": "position", "label": "商品", "type": "text"},
                    {"field": "pe", "label": "PER", "format": "number"},
                    {"field": "basis_kind", "label": "集計区分", "type": "text"},
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
                    {"field": "scenario_kind", "label": "種類", "type": "text"},
                    {"field": "position", "label": "商品", "type": "text"},
                    {"field": "impact_jpy", "label": "評価額変化", "format": "currency"},
                    {
                        "field": "portfolio_impact",
                        "label": "総資産比",
                        "format": "percent",
                    },
                ],
            },
            {
                "id": "factor_loadings",
                "title": "商品別ファクター係数",
                "subtitle": "市場β・セクター・為替・金利係数。ポートフォリオ寄与と算定メモを表示",
                "dataset": "factor_loadings",
                "sourceId": analysis_source_id,
                "defaultSort": {
                    "field": "portfolio_weighted_loading",
                    "direction": "desc",
                },
                "density": "dense",
                "layout": "full",
                "columns": [
                    {"field": "position", "label": "商品", "type": "text"},
                    {"field": "factor", "label": "ファクター", "type": "text"},
                    {"field": "loading", "label": "係数", "format": "number"},
                    {
                        "field": "portfolio_weighted_loading",
                        "label": "総資産加重係数",
                        "format": "number",
                    },
                    {"field": "market_value_jpy", "label": "評価額", "format": "currency"},
                    {"field": "method_note", "label": "算定メモ", "type": "text"},
                ],
            },
            {
                "id": "policy_checks",
                "title": "暫定投資方針チェック",
                "subtitle": f"状態: {reference.policy_status}。閾値は売買指示ではなく監視基準",
                "dataset": "policy_checks",
                "sourceId": analysis_source_id,
                "defaultSort": {"field": "status", "direction": "asc"},
                "density": "dense",
                "layout": "full",
                "columns": [
                    {"field": "rule", "label": "ルール", "type": "text"},
                    {"field": "value", "label": "現在値", "format": "number"},
                    {"field": "operator", "label": "条件", "type": "text"},
                    {"field": "threshold", "label": "閾値", "format": "number"},
                    {"field": "status", "label": "判定", "type": "text"},
                    {"field": "note", "label": "注記", "type": "text"},
                ],
            },
        ]
    )

    if artifact["snapshot"]["datasets"].get("reverse_stress"):
        manifest["cards"].extend(
            [
                {
                    "id": "factor_volatility",
                    "description": "実測ファクター共分散から求めた、1週間あたりの標準偏差。",
                    "dataset": "summary",
                    "sourceId": "factor_risk",
                    "metrics": [
                        {
                            "label": "週次ボラティリティ",
                            "field": "factor_period_volatility",
                            "format": "percent",
                        }
                    ],
                },
                {
                    "id": "limit_distance",
                    "description": "最も近い方針上限に届くまでの距離。週次σ単位で、確率ではない。",
                    "dataset": "summary",
                    "sourceId": "factor_risk",
                    "metrics": [
                        {
                            "label": "上限までの距離",
                            "field": "nearest_limit_distance_sigma",
                            "format": "number",
                            "unit": "σ",
                        }
                    ],
                },
            ]
        )
        manifest["cards"].extend(
            [
                {
                    "id": "replayed_shortfall",
                    "description": (
                        "過去3年の週次ファクター変化を現在の保有に当て直したときの、"
                        "下位2.5%の平均損失。実績ではなく再現。"
                    ),
                    "dataset": "summary",
                    "sourceId": "factor_risk",
                    "metrics": [
                        {
                            "label": "参考ES(97.5%)",
                            "field": "replayed_expected_shortfall",
                            "format": "percent",
                        }
                    ],
                },
                {
                    "id": "replayed_drawdown",
                    "description": "同じ再現での最大ドローダウン。",
                    "dataset": "summary",
                    "sourceId": "factor_risk",
                    "metrics": [
                        {
                            "label": "参考最大DD",
                            "field": "replayed_max_drawdown",
                            "format": "percent",
                        }
                    ],
                },
            ]
        )
        metric_block = next(block for block in manifest["blocks"] if block["id"] == "metrics")
        metric_block["cardIds"].extend(
            ["factor_volatility", "limit_distance", "replayed_shortfall", "replayed_drawdown"]
        )
        manifest["tables"].append(
            {
                "id": "reverse_stress",
                "title": "リバース・ストレステスト",
                "subtitle": (
                    "各方針上限を破る、最も無理のないショックの組合せ。"
                    "実測共分散に基づく最小マハラノビス距離解で、予測ではない"
                ),
                "dataset": "reverse_stress",
                "sourceId": "factor_risk",
                "defaultSort": {"field": "loss_share", "direction": "desc"},
                "density": "dense",
                "layout": "full",
                "columns": [
                    {"field": "limit", "label": "方針上限", "type": "text"},
                    {"field": "target_loss_ratio", "label": "目標損失", "format": "percent"},
                    {"field": "distance_sigma", "label": "距離", "format": "number"},
                    {"field": "factor", "label": "ファクター", "type": "text"},
                    {"field": "shock", "label": "必要ショック", "format": "percent"},
                    {
                        "field": "loss_contribution_jpy",
                        "label": "損失寄与",
                        "format": "currency",
                    },
                    {"field": "loss_share", "label": "損失シェア", "format": "percent"},
                ],
            }
        )

    if artifact["snapshot"]["datasets"].get("theme_exposure"):
        manifest["cards"].append(
            {
                "id": "largest_theme",
                "description": (
                    "同じ材料で動く銘柄群の合計。発行体を開示している部分だけの集計なので下限値。"
                ),
                "dataset": "summary",
                "sourceId": analysis_source_id,
                "metrics": [
                    {
                        "label": "最大テーマ比率",
                        "field": "largest_theme_ratio",
                        "format": "percent",
                    }
                ],
            }
        )
        next(block for block in manifest["blocks"] if block["id"] == "metrics")["cardIds"].append(
            "largest_theme"
        )
        manifest["tables"].append(
            {
                "id": "theme_exposure",
                "title": "テーマ別の合算エクスポージャー",
                "subtitle": (
                    "商品をまたいで同じ材料に賭けている合計額。"
                    "発行体を開示している部分だけの集計なので下限値"
                ),
                "dataset": "theme_exposure",
                "sourceId": analysis_source_id,
                "defaultSort": {"field": "market_value_jpy", "direction": "desc"},
                "density": "compact",
                "layout": "full",
                "columns": [
                    {"field": "theme", "label": "テーマ", "type": "text"},
                    {"field": "market_value_jpy", "label": "評価額", "format": "currency"},
                    {"field": "portfolio_weight", "label": "総資産比", "format": "percent"},
                    {"field": "issuer_count", "label": "銘柄数", "format": "number"},
                    {"field": "issuers", "label": "内訳", "type": "text"},
                ],
            }
        )

    if artifact["snapshot"]["datasets"].get("correlation_monitor"):
        manifest["charts"].append(
            {
                "id": "correlation_monitor",
                "title": "株債相関の推移（26週ローリング）",
                "subtitle": "負なら日本国債が株式のヘッジとして機能、正なら株債同時安",
                "intent": "trend",
                "question": "債券保有はいまヘッジとして効いているか",
                "rationale": "符号の反転そのものが論点なので、時系列を折れ線で見る。",
                "comparisonContext": {"grain": "週", "unit": "相関係数"},
                "type": "line",
                "dataset": "correlation_monitor",
                "sourceId": "factor_risk",
                "encodings": {
                    "x": {"field": "date", "type": "temporal", "label": "週"},
                    "y": {
                        "field": "stock_bond_correlation",
                        "type": "quantitative",
                        "label": "株債相関",
                        "format": "number",
                    },
                    "tooltip": [{"field": "regime", "type": "nominal", "label": "判定"}],
                },
                "valueFormat": "number",
                "layout": "full",
                "palette": {"kind": "sequential", "name": "blue"},
            }
        )

    if artifact["snapshot"]["datasets"].get("event_calendar"):
        manifest["tables"].append(
            {
                "id": "event_calendar",
                "title": "今後の既知イベント",
                "subtitle": (
                    f"参照データ基準日 {reference.as_of} からの日数と、対応シナリオの想定影響"
                ),
                "dataset": "event_calendar",
                "sourceId": analysis_source_id,
                "defaultSort": {"field": "days_until", "direction": "asc"},
                "density": "compact",
                "layout": "full",
                "columns": [
                    {"field": "event_date", "label": "日付", "type": "text"},
                    {"field": "days_until", "label": "残日数", "format": "number"},
                    {"field": "event", "label": "イベント", "type": "text"},
                    {"field": "scenario", "label": "対応シナリオ", "type": "text"},
                    {"field": "impact_ratio", "label": "想定影響", "format": "percent"},
                    {"field": "note", "label": "注記", "type": "text"},
                ],
            }
        )

    scenario_notes = "\n".join(
        f"- **{scenario.label}**: {scenario.assumption}" for scenario in reference.scenarios
    )
    factor_notes = "\n".join(
        f"- **{factor}**: {definition}"
        for factor, definition in reference.factor_definitions.items()
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
            "id": "advanced_metrics",
            "type": "metric-strip",
            "cardIds": [
                "sector_coverage",
                "effective_sectors",
                "issuer_coverage",
                "worst_compound",
                "policy_breaches",
                "trailing_pe",
                "trailing_pe_coverage",
                "forward_pe",
                "forward_pe_coverage",
                "provider_pe",
            ],
        },
        {
            "id": "policy_checks_block",
            "type": "table",
            "tableId": "policy_checks",
            "layout": "full",
        },
        {
            "id": "sector_analysis_block",
            "type": "chart",
            "chartId": "sector_exposure",
            "layout": "full",
        },
        {
            "id": "issuer_analysis_block",
            "type": "chart",
            "chartId": "issuer_exposure",
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
                f"{factor_notes}\n\n"
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
        *(
            [
                {
                    "id": "theme_exposure_block",
                    "type": "table",
                    "tableId": "theme_exposure",
                    "layout": "full",
                }
            ]
            if artifact["snapshot"]["datasets"].get("theme_exposure")
            else []
        ),
        *(
            [
                {
                    "id": "correlation_monitor_block",
                    "type": "chart",
                    "chartId": "correlation_monitor",
                    "layout": "full",
                },
                {
                    "id": "correlation_monitor_note",
                    "type": "markdown",
                    "body": (
                        "## 債券はいまヘッジとして効いているか\n\n"
                        "株債相関は日本国債リターンと株式全体の26週ローリング相関で、"
                        "金利ファクターの符号を反転して求めています。"
                        "**負なら債券が株安を和らげ、正なら両方まとめて下がります。**"
                        "インフレや金融政策が主因の下落では正に転びやすく、"
                        "そのとき債券保有は分散になりません。"
                    ),
                    "sourceId": "factor_risk",
                },
            ]
            if artifact["snapshot"]["datasets"].get("correlation_monitor")
            else []
        ),
        *(
            [
                {
                    "id": "reverse_stress_method",
                    "type": "markdown",
                    "body": (
                        "## リバース・ストレステスト\n\n"
                        "「このショックなら何%下がるか」ではなく、"
                        "**「上限まで下がるとしたら何が起きたときか」**を逆算します。"
                        "損失は各ファクターの一次結合なので、目標損失 $L^*$ を固定して"
                        "マハラノビス距離を最小化する解は閉形式で求まります。\n\n"
                        "$$s^* = -L^* \\frac{\\Sigma b}{b^\\top \\Sigma b}, \\qquad "
                        "d = \\frac{L^*}{\\sqrt{b^\\top \\Sigma b}}$$\n\n"
                        "$b$ は各ファクター1単位あたりに動く評価額、$\\Sigma$ は実測共分散です。"
                        "$d$ は週次標準偏差を単位とする距離で、**確率ではありません**。"
                        "正規性も相関の安定性も仮定していないため、順位づけの目安として読みます。"
                    ),
                    "sourceId": "factor_risk",
                },
                {
                    "id": "reverse_stress_block",
                    "type": "table",
                    "tableId": "reverse_stress",
                    "layout": "full",
                },
            ]
            if artifact["snapshot"]["datasets"].get("reverse_stress")
            else []
        ),
        *(
            [
                {
                    "id": "event_calendar_block",
                    "type": "table",
                    "tableId": "event_calendar",
                    "layout": "full",
                }
            ]
            if artifact["snapshot"]["datasets"].get("event_calendar")
            else []
        ),
        {
            "id": "factor_loadings_block",
            "type": "table",
            "tableId": "factor_loadings",
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
                "## PERの読み方\n\nPERは **実績・予想・提供会社基準** に分け、"
                "それぞれを評価額加重調和平均しています。異なる区分同士を単一の"
                "ポートフォリオPERとして比較しません。カバー率と基準日を併読してください。"
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


def _extend_proposal_manifest(artifact: dict[str, Any], proposal: ProposalResult) -> None:
    """Add before/after proposal tables to an existing dashboard manifest."""
    manifest = artifact["manifest"]
    proposal_source_id = "proposal"
    manifest["tables"].extend(
        [
            {
                "id": "proposal_trades",
                "title": "提案売買明細",
                "subtitle": "価格・為替は提案ファイルの固定値。税・手数料は資金差額に未反映",
                "dataset": "proposal_trade_details",
                "sourceId": proposal_source_id,
                "defaultSort": {"field": "value_delta_jpy", "direction": "asc"},
                "density": "dense",
                "layout": "full",
                "columns": [
                    {"field": "account", "label": "口座", "type": "text"},
                    {"field": "symbol", "label": "銘柄", "type": "text"},
                    {"field": "quantity_before", "label": "変更前", "format": "number"},
                    {"field": "quantity_delta", "label": "増減", "format": "number"},
                    {"field": "quantity_after", "label": "変更後", "format": "number"},
                    {"field": "value_delta_jpy", "label": "評価額増減", "format": "currency"},
                    {
                        "field": "native_realized_gain_estimate",
                        "label": "現地通貨の実現損益概算",
                        "format": "number",
                    },
                    {"field": "tax_status", "label": "税計算", "type": "text"},
                ],
            },
            {
                "id": "proposal_metrics",
                "title": "提案前後の主要指標",
                "subtitle": "同一価格・同一為替、税・手数料なしの比較",
                "dataset": "proposal_comparison",
                "sourceId": proposal_source_id,
                "defaultSort": {"field": "metric", "direction": "asc"},
                "density": "dense",
                "layout": "full",
                "columns": [
                    {"field": "metric", "label": "指標", "type": "text"},
                    {"field": "before", "label": "変更前", "format": "number"},
                    {"field": "after", "label": "変更後", "format": "number"},
                    {"field": "change", "label": "差分", "format": "number"},
                    {"field": "unit", "label": "単位", "type": "text"},
                ],
            },
            {
                "id": "proposal_sensitivity",
                "title": "提案前後の市場ショック感応度",
                "subtitle": "改善が正なら、同じショックで損失率が小さくなる",
                "dataset": "proposal_sensitivity_comparison",
                "sourceId": proposal_source_id,
                "defaultSort": {"field": "before_impact_ratio", "direction": "asc"},
                "density": "dense",
                "layout": "full",
                "columns": [
                    {"field": "scenario", "label": "シナリオ", "type": "text"},
                    {"field": "scenario_kind", "label": "種類", "type": "text"},
                    {
                        "field": "before_impact_ratio",
                        "label": "変更前",
                        "format": "percent",
                    },
                    {
                        "field": "after_impact_ratio",
                        "label": "変更後",
                        "format": "percent",
                    },
                    {"field": "improvement", "label": "改善幅", "format": "percent"},
                ],
            },
        ]
    )
    assumptions = "\n".join(f"- {assumption}" for assumption in proposal.assumptions)
    blocks = [
        {
            "id": "proposal_intro",
            "type": "markdown",
            "body": (
                f"## リバランス提案: {proposal.name}\n\n"
                f"{assumptions or '- 税・手数料を除く固定価格比較'}"
            ),
            "sourceId": proposal_source_id,
        },
        {
            "id": "proposal_trades_block",
            "type": "table",
            "tableId": "proposal_trades",
            "layout": "full",
        },
        {
            "id": "proposal_metrics_block",
            "type": "table",
            "tableId": "proposal_metrics",
            "layout": "full",
        },
        {
            "id": "proposal_sensitivity_block",
            "type": "table",
            "tableId": "proposal_sensitivity",
            "layout": "full",
        },
    ]
    insert_at = next(
        index + 1 for index, block in enumerate(manifest["blocks"]) if block["id"] == "metrics"
    )
    manifest["blocks"][insert_at:insert_at] = blocks
