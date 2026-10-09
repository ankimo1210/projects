"""Daily risk monitor: what the book is exposed to, how much it moves, what would hurt.

Exposures look through funds with the analysis reference — each instrument's
sector, issuer and asset rows, the country of each issuer, and an asset /
currency / country mix for a balanced fund. Statistics come from the daily JPY
returns of the holdings at today's weights: annualised volatility, historical-
simulation VaR and expected shortfall, single-regression betas, and each
holding's share of the portfolio variance (w_i (Σw)_i / wᵀΣw), allocated to
currency, sector and country with the same look-through weights. Stress comes
two ways: the reference's factor scenarios (Σ value × loading × shock, as the
main dashboard computes them) and past episodes replayed with the actual
returns of what is held now.

Float arithmetic on already-computed values; nothing here reads the network.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .core import FactorRisk, _is_static_balance, _measured_model_status

HOME_CURRENCY = "JPY"
HOME_COUNTRY = "日本"
CASH_CLASS = "現金"
NON_EQUITY_SECTOR = "債券・現金等"
UNMAPPED_SECTOR = "その他・未分類株式"
TRADING_DAYS = 252
COUNTRY_BY_CURRENCY = {"JPY": HOME_COUNTRY, "USD": "米国"}
# One taxonomy for 国・地域: a balanced fund reports regions, an ETF's issuers countries.
# Countries roll up to the region a fund would count them in (MSCI's classes, so Taiwan
# and Korea are emerging); the single-country limit reads the countries alone.
REGIONS = ("日本", "米国", "欧州", "その他先進国", "新興国")
REGION_OF = {
    **{r: r for r in REGIONS},
    **dict.fromkeys(
        (
            "英国",
            "ドイツ",
            "フランス",
            "オランダ",
            "スイス",
            "アイルランド",
            "スウェーデン",
            "デンマーク",
            "イタリア",
            "スペイン",
            "ベルギー",
            "フィンランド",
            "ノルウェー",
        ),
        "欧州",
    ),
    **dict.fromkeys(
        ("カナダ", "オーストラリア", "香港", "シンガポール", "イスラエル", "ニュージーランド"),
        "その他先進国",
    ),
    **dict.fromkeys(
        (
            "台湾",
            "韓国",
            "中国",
            "インド",
            "ブラジル",
            "メキシコ",
            "南アフリカ",
            "サウジアラビア",
            "インドネシア",
            "タイ",
        ),
        "新興国",
    ),
}
OTHER_REGION = "その他"
# labels that name a region and no single country (日本 and 米国 are both)
REGION_ONLY = frozenset({"欧州", "その他先進国", "新興国", OTHER_REGION})


@dataclass(frozen=True)
class Holding:
    symbol: str
    account_id: str
    value_jpy: float
    currency: str
    asset_class: str
    ticker: str | None = None

    @property
    def is_cash(self) -> bool:
        return self.asset_class == CASH_CLASS


def _instruments(reference: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(i["symbol"]): i for i in reference.get("instruments", [])}


def _rows(instrument: dict[str, Any], group: str) -> list[dict[str, Any]]:
    return [e for e in instrument.get("exposures", []) if e.get("group") == group]


def _bump(bucket: dict[str, float], key: str, value: float) -> None:
    if value:
        bucket[key] = bucket.get(key, 0.0) + value


def _mixes(holding: Holding, instrument: dict[str, Any]) -> dict[str, dict[str, float]]:
    """The holding's currency / country / sector split as fractions summing to 1."""
    currency = {
        str(k): float(v)
        for k, v in (instrument.get("currency_mix") or {holding.currency: 1.0}).items()
    }
    if instrument.get("country_mix"):
        country = {str(k): float(v) for k, v in instrument["country_mix"].items()}
    else:
        default = str(
            instrument.get("country_default") or COUNTRY_BY_CURRENCY.get(holding.currency, "その他")
        )
        country = {}
        covered = 0.0
        for e in _rows(instrument, "issuer"):
            w = float(e["weight"])
            covered += w
            _bump(country, str(e.get("country") or default), w)
        _bump(country, default, max(1.0 - covered, 0.0))
    sector: dict[str, float] = {}
    if holding.is_cash:
        sector[NON_EQUITY_SECTOR] = 1.0
    else:
        covered = 0.0
        for e in _rows(instrument, "sector"):
            w = float(e["weight"])
            covered += w
            _bump(sector, str(e["category"]), w)
        non_equity = min(sum(float(e["weight"]) for e in _rows(instrument, "asset")), 1.0)
        rest = max(1.0 - covered, 0.0)
        _bump(sector, NON_EQUITY_SECTOR, min(rest, non_equity))
        _bump(sector, UNMAPPED_SECTOR, max(rest - non_equity, 0.0))
    region: dict[str, float] = {}
    for label, w in country.items():
        _bump(region, REGION_OF.get(label, OTHER_REGION), w)
    return {"currency": currency, "country": country, "region": region, "sector": sector}


def lookthrough(holdings: Sequence[Holding], reference: dict[str, Any]) -> dict[str, Any]:
    """Value by asset class, currency, country, sector and issuer after looking through funds."""
    instruments = _instruments(reference)
    by: dict[str, dict[str, float]] = {
        k: {} for k in ("asset_class", "currency", "country", "region", "sector")
    }
    issuers: dict[str, dict[str, Any]] = {}
    mix: dict[str, dict[str, dict[str, float]]] = {}
    equity_value = mapped_value = 0.0
    total = sum(float(h.value_jpy) for h in holdings)
    for h in holdings:
        v = float(h.value_jpy)
        inst = instruments.get(h.symbol, {})
        m = _mixes(h, inst)
        mix.setdefault(h.symbol, m)
        for key in ("currency", "country", "region", "sector"):
            for label, w in m[key].items():
                _bump(by[key], label, v * w)
        asset_mix = inst.get("asset_mix")
        if asset_mix:
            for label, w in asset_mix.items():
                _bump(by["asset_class"], str(label), v * float(w))
        else:
            _bump(by["asset_class"], h.asset_class, v)
        if not h.is_cash:
            equity_value += v * (1.0 - m["sector"].get(NON_EQUITY_SECTOR, 0.0))
        for e in _rows(inst, "issuer"):
            name, w = str(e["category"]), float(e["weight"])
            row = issuers.setdefault(
                name, {"label": name, "value": 0.0, "country": e.get("country"), "via": {}}
            )
            row["value"] += v * w
            row["via"][h.symbol] = row["via"].get(h.symbol, 0.0) + v * w
            mapped_value += v * w

    def table(bucket: dict[str, float]) -> list[dict[str, Any]]:
        return [
            {"label": k, "value": val, "pct": (val / total if total else None)}
            for k, val in sorted(bucket.items(), key=lambda kv: -kv[1])
        ]

    issuer_rows = sorted(
        (
            {
                "label": r["label"],
                "value": r["value"],
                "pct": (r["value"] / total if total else None),
                "country": r["country"],
                "via": sorted(r["via"], key=lambda s: -r["via"][s]),
            }
            for r in issuers.values()
        ),
        key=lambda r: -r["value"],
    )
    return {
        "total": total,
        **{k: table(b) for k, b in by.items()},
        "issuers": issuer_rows,
        "coverage": {"issuer": (mapped_value / equity_value if equity_value else None)},
        "mix": mix,
    }


def _hhi(values: Sequence[float]) -> float:
    s = sum(values)
    return sum((v / s) ** 2 for v in values) if s else 0.0


def concentration(holdings: Sequence[Holding], exposures: dict[str, Any]) -> dict[str, Any]:
    """Concentration as ratios of total assets (the sector effective count over the equity part)."""
    total = float(exposures["total"])
    # by symbol, not by holding: the same ETF in two accounts is one position's worth of risk
    by_symbol: dict[str, float] = {}
    for h in holdings:
        if not h.is_cash:
            by_symbol[h.symbol] = by_symbol.get(h.symbol, 0.0) + float(h.value_jpy)
    invested = sorted(by_symbol.values(), reverse=True)
    sectors = [r for r in exposures["sector"] if r["label"] != NON_EQUITY_SECTOR]
    # countries only: a region row (欧州, 新興国, …) is not a single country
    foreign = [
        r
        for r in exposures["country"]
        if r["label"] != HOME_COUNTRY and r["label"] not in REGION_ONLY
    ]
    jpy = next((r["value"] for r in exposures["currency"] if r["label"] == HOME_CURRENCY), 0.0)
    issuers = exposures["issuers"]
    cash = sum(float(h.value_jpy) for h in holdings if h.is_cash)

    def effective(rows: list[dict[str, Any]]) -> float | None:
        h = _hhi([r["value"] for r in rows])
        return 1.0 / h if h else None

    def ratio(v: float) -> float | None:
        return v / total if total else None

    return {
        "largest_position_ratio": ratio(invested[0]) if invested else None,
        "top5_ratio": ratio(sum(invested[:5])) if invested else None,
        "effective_positions": (1.0 / _hhi(invested)) if invested else None,
        "effective_sectors": effective(sectors),
        "effective_currencies": effective(exposures["currency"]),
        "effective_countries": effective(exposures["region"]),
        "max_sector_ratio": ratio(sectors[0]["value"]) if sectors else None,
        "max_sector": sectors[0]["label"] if sectors else None,
        "largest_issuer_lookthrough_ratio": ratio(issuers[0]["value"]) if issuers else None,
        "largest_issuer": issuers[0]["label"] if issuers else None,
        "foreign_currency_ratio": (1.0 - jpy / total) if total else None,
        "largest_foreign_country_ratio": ratio(foreign[0]["value"]) if foreign else 0.0,
        "largest_foreign_country": foreign[0]["label"] if foreign else None,
        "cash_ratio": ratio(cash),
    }


# ---- statistics on daily JPY returns at today's weights ----


def portfolio_returns(weights: dict[str, float], returns: dict[str, list[float]]) -> list[float]:
    """Σ w_i r_i per day. A ticker with no return series (cash) contributes nothing."""
    n = max((len(r) for t, r in returns.items() if t in weights), default=0)
    out = []
    for i in range(n):
        day = 0.0
        for t, w in weights.items():
            series = returns.get(t)
            if series is not None and i < len(series) and series[i] is not None:
                day += w * series[i]
        out.append(day)
    return out


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs)


def _variance(xs: Sequence[float]) -> float:
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def volatility(rs: Sequence[float]) -> float | None:
    """Annualised standard deviation of daily returns (√252)."""
    return math.sqrt(_variance(rs) * TRADING_DAYS) if len(rs) > 1 else None


def quantile(sorted_values: Sequence[float], q: float) -> float:
    """Linear-interpolated quantile of an ascending sequence (numpy's default)."""
    pos = (len(sorted_values) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def value_at_risk(rs: Sequence[float], level: float) -> float | None:
    """Historical-simulation VaR as a positive loss fraction of assets."""
    if not rs:
        return None
    return max(-quantile(sorted(rs), 1.0 - level), 0.0)


def expected_shortfall(rs: Sequence[float], level: float) -> float | None:
    """Mean loss beyond the VaR quantile, as a positive fraction."""
    if not rs:
        return None
    ordered = sorted(rs)
    cut = quantile(ordered, 1.0 - level)
    tail = [x for x in ordered if x <= cut]
    return max(-_mean(tail), 0.0) if tail else None


def beta(rs: Sequence[float], bench: Sequence[float]) -> float | None:
    """Slope of the portfolio's daily return on the benchmark's (single regression)."""
    n = min(len(rs), len(bench))
    if n < 3:
        return None
    a, b = list(rs[-n:]), list(bench[-n:])
    ma, mb = _mean(a), _mean(b)
    var_b = sum((x - mb) ** 2 for x in b)
    if var_b == 0:
        return None
    return sum((x - ma) * (y - mb) for x, y in zip(a, b, strict=True)) / var_b


def risk_contributions(
    weights: dict[str, float], returns: dict[str, list[float]]
) -> dict[str, float]:
    """Each ticker's share of the portfolio variance: w_i (Σw)_i / wᵀΣw. Sums to 1."""
    tickers = [t for t, w in weights.items() if t in returns and w]
    if not tickers:
        return {}
    n = min(len(returns[t]) for t in tickers)
    if n < 2:
        return {}
    series = {t: [x if x is not None else 0.0 for x in returns[t][-n:]] for t in tickers}
    means = {t: _mean(series[t]) for t in tickers}

    def cov(a: str, b: str) -> float:
        pairs = zip(series[a], series[b], strict=True)
        return sum((x - means[a]) * (y - means[b]) for x, y in pairs) / (n - 1)

    sigma_w = {a: sum(cov(a, b) * weights[b] for b in tickers) for a in tickers}
    var_p = sum(weights[a] * sigma_w[a] for a in tickers)
    if var_p <= 0:
        return dict.fromkeys(tickers, 0.0)
    return {a: weights[a] * sigma_w[a] / var_p for a in tickers}


# ---- stress ----


def scenario_impacts(
    holdings: Sequence[Holding], reference: dict[str, Any], *, factor_risk: FactorRisk | None = None
) -> list[dict[str, Any]]:
    """Σ value × factor loading × shock for every scenario in the reference (worst first)."""
    instruments = _instruments(reference)
    total = sum(float(h.value_jpy) for h in holdings)
    values: dict[str, Decimal] = {}
    for h in holdings:
        if not _is_static_balance(h.symbol, h.currency, h.asset_class):
            values[h.symbol] = values.get(h.symbol, Decimal()) + Decimal(str(h.value_jpy))
    coverage, measured_reason = _measured_model_status(values, factor_risk)
    out = []
    for sc in reference.get("scenarios", []):
        historical = sc.get("kind") == "historical"
        reason = measured_reason if historical else ""
        if (
            historical
            and not reason
            and values
            and factor_risk is not None
            and set(sc.get("shocks", {})) - set(factor_risk.factors)
        ):
            reason = "実測ファクター基準にないショックが含まれています"
        if reason:
            out.append(
                {
                    "id": str(sc["id"]),
                    "label": str(sc.get("label", sc["id"])),
                    "kind": "historical",
                    "impact_jpy": None,
                    "impact_pct": None,
                    "reason": reason,
                    "model_basis": "measured_joint",
                    "coverage": coverage,
                }
            )
            continue
        impact = 0.0
        for h in holdings:
            if historical and _is_static_balance(h.symbol, h.currency, h.asset_class):
                continue
            loadings = (
                factor_risk.instrument_loadings.get(h.symbol, {})
                if historical and factor_risk is not None
                else instruments.get(h.symbol, {}).get("factor_loadings", {})
            )
            impact += float(h.value_jpy) * sum(
                float(loadings.get(f, 0.0)) * float(shock)
                for f, shock in sc.get("shocks", {}).items()
            )
        out.append(
            {
                "id": str(sc["id"]),
                "label": str(sc.get("label", sc["id"])),
                "kind": str(sc.get("kind", "hypothetical")),
                "impact_jpy": impact,
                "impact_pct": (impact / total if total else None),
                "reason": "",
                "model_basis": "measured_joint" if historical else "manual_linear",
            }
        )
    return sorted(out, key=lambda r: (r["impact_jpy"] is None, r["impact_jpy"] or 0.0))


def episode_impacts(
    values_by_ticker: dict[str, float],
    episodes: Sequence[dict[str, Any]],
    dates: Sequence[str],
    prices_jpy: dict[str, Sequence[float | None]],
    *,
    total_nav: float | None = None,
    missing_holdings: Sequence[str] = (),
) -> list[dict[str, Any]]:
    """Keep priced partial P&L separate from a complete replay of today's market assets."""
    invested = sum(values_by_ticker.values())
    total = invested if total_nav is None else total_nav
    out = []
    for ep in episodes:
        before = [i for i, d in enumerate(dates) if d < str(ep["start"])]
        upto = [i for i, d in enumerate(dates) if d <= str(ep["end"])]
        boundary_known = bool(
            before and upto and upto[-1] > before[-1] and dates[-1] >= str(ep["end"])
        )
        static_only = not values_by_ticker and not missing_holdings
        impact = 0.0 if boundary_known or static_only else None
        covered = 0.0
        missing = list(missing_holdings)
        if boundary_known:
            i0, i1 = before[-1], upto[-1]
            for ticker, value in values_by_ticker.items():
                series = prices_jpy.get(ticker)
                if (
                    not series
                    or len(series) <= i1
                    or series[i0] is None
                    or series[i1] is None
                    or not math.isfinite(series[i0])
                    or not math.isfinite(series[i1])
                    or series[i0] <= 0
                ):
                    missing.append(ticker)
                    continue
                impact += value * (float(series[i1]) / float(series[i0]) - 1.0)
                covered += value
        complete = (boundary_known or static_only) and not missing
        reason = (
            "局面の開始前・終了時の価格履歴がありません"
            if not boundary_known and not static_only
            else f"局面価格が未計算: {', '.join(sorted(set(missing)))}"
            if missing
            else ""
        )
        if not static_only and covered == 0:
            impact = None
        ratio = impact / total if impact is not None and total else None
        out.append(
            {
                "id": str(ep["id"]),
                "label": str(ep.get("label", ep["id"])),
                "start": str(ep["start"]),
                "end": str(ep["end"]),
                "impact_jpy": impact,
                "impact_pct": ratio,
                "total_impact_jpy": impact if complete else None,
                "total_impact_pct": ratio if complete else None,
                "complete": complete,
                "reason": reason,
                "coverage": covered / invested if invested else None,
                "coverage_basis": "priced_positions",
                "priced_nav_ratio": covered / total if total else None,
            }
        )
    return sorted(out, key=lambda row: (row["impact_jpy"] is None, row["impact_jpy"] or 0.0))


# ---- limits ----


def evaluate_limits(
    limits: Sequence[dict[str, Any]],
    metrics: dict[str, Any],
    *,
    lower_bounds: dict[str, float | None] | None = None,
    reasons: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    out = []
    for limit in limits:
        metric = str(limit["metric"])
        value = metrics.get(metric)
        lower_bound = (lower_bounds or {}).get(metric)
        reason = (reasons or {}).get(metric, "")
        op, threshold = str(limit["operator"]), float(limit["threshold"])
        if value is None or op not in ("<=", ">="):
            status = "na"
            if value is None and op == "<=" and lower_bound is not None and lower_bound > threshold:
                status = "breach"
                reason = f"{reason}。少なくとも {lower_bound:.1%} の損失を確認"
        elif op == "<=":
            status = "ok" if value <= threshold else "breach"
        else:
            status = "ok" if value >= threshold else "breach"
        out.append(
            {
                "id": str(limit["id"]),
                "label": str(limit.get("label", limit["id"])),
                "metric": str(limit["metric"]),
                "operator": op,
                "threshold": threshold,
                "value": value,
                "lower_bound_value": lower_bound,
                "reason": reason,
                "status": status,
                "note": str(limit.get("note", "")),
            }
        )
    return out


# ---- the payload block ----


def _worst(
    scenarios: Sequence[dict[str, Any]], kind: str, *, require_complete: bool = True
) -> float | None:
    """An exact worst loss needs every configured scenario; known losses give a lower bound."""
    rows = [row for row in scenarios if row["kind"] == kind]
    if require_complete and any(row["impact_pct"] is None for row in rows):
        return None
    ratios = [row["impact_pct"] for row in rows if row["impact_pct"] is not None]
    return max(-min(ratios), 0.0) if ratios else None


HISTORY_KEYS = (
    "vol_annual",
    "var_1d_95",
    "es_1d_975",
    "foreign_currency_ratio",
    "largest_issuer_lookthrough_ratio",
    "max_sector_ratio",
    "beta_topix",
    "beta_sp500",
    "beta_usdjpy",
    "policy_breaches",
)


def assemble(
    holdings: Sequence[Holding],
    reference: dict[str, Any],
    returns: dict[str, list[float | None]],
    benchmarks: dict[str, list[float | None]],
    dates: Sequence[str],
    prices_jpy: dict[str, Sequence[float | None]],
    as_of: str,
    previous: dict[str, Any] | None = None,
    *,
    factor_risk: FactorRisk | None = None,
) -> dict[str, Any]:
    """Everything the report shows, from today's holdings and the price history.

    ``returns`` / ``prices_jpy`` are per ticker, in JPY, aligned to ``dates``;
    ``benchmarks`` holds ``topix`` / ``sp500`` (local currency) and ``usdjpy``
    daily returns over the same window as ``returns``; ``previous`` is the
    ``history`` block of the last report, for day-over-day comparison.
    """
    exposures = lookthrough(holdings, reference)
    total = float(exposures["total"])
    conc = concentration(holdings, exposures)
    weights: dict[str, float] = {}
    values: dict[str, float] = {}
    symbol_of: dict[str, str] = {}
    for h in holdings:
        if h.ticker and not h.is_cash and h.symbol != "RECONCILIATION" and total:
            weights[h.ticker] = weights.get(h.ticker, 0.0) + float(h.value_jpy) / total
            values[h.ticker] = values.get(h.ticker, 0.0) + float(h.value_jpy)
            symbol_of[h.ticker] = h.symbol
    window = max((len(returns[t]) for t in weights if t in returns), default=0)
    modeled = [
        h for h in holdings if not h.is_cash and h.symbol != "RECONCILIATION" and h.value_jpy
    ]

    def complete_history(h: Holding) -> bool:
        observations = returns.get(h.ticker or "", [])
        return (
            window >= 2
            and len(observations) == window
            and all(x is not None and math.isfinite(x) for x in observations[-window:])
        )

    missing_history = [h.symbol for h in modeled if not complete_history(h)]
    modeled_value = sum(float(h.value_jpy) for h in modeled)
    covered_value = sum(float(h.value_jpy) for h in modeled if complete_history(h))
    history_reason = (
        f"価格履歴が不足: {', '.join(sorted(set(missing_history)))}" if missing_history else ""
    )
    port = [] if missing_history else portfolio_returns(weights, returns)
    var95, var99 = value_at_risk(port, 0.95), value_at_risk(port, 0.99)
    es = expected_shortfall(port, 0.975)
    worst_i = min(range(len(port)), key=lambda i: port[i]) if port else None
    offset = len(dates) - len(port)
    worst = None
    if worst_i is not None:
        j = offset + worst_i
        worst = {
            "date": dates[j] if 0 <= j < len(dates) else None,
            "pnl_jpy": port[worst_i] * total,
            "pct": port[worst_i],
        }
    beta_values: dict[str, float | None] = {}
    beta_reasons: dict[str, str] = {}
    for name, series in benchmarks.items():
        reason = (
            history_reason or "有効なポートフォリオリターンがありません"
            if not port
            else "ベンチマークの価格履歴が不足"
            if len(series) != len(port)
            or any(value is None or not math.isfinite(value) for value in series)
            else "共通観測が3件ありません"
            if len(port) < 3
            else ""
        )
        beta_values[name] = None if reason else beta(port, series)
        beta_reasons[name] = reason or (
            "ベンチマークに変動がありません" if beta_values[name] is None else ""
        )
    stats = {
        "window_days": len(port),
        "vol_annual": volatility(port),
        "var_1d_95": var95,
        "var_1d_99": var99,
        "es_1d_975": es,
        "var_20d_95": (None if var95 is None else var95 * math.sqrt(20)),
        "var_1d_95_jpy": (None if var95 is None else var95 * total),
        "var_1d_99_jpy": (None if var99 is None else var99 * total),
        "es_1d_975_jpy": (None if es is None else es * total),
        "var_20d_95_jpy": (None if var95 is None else var95 * math.sqrt(20) * total),
        "worst_day": worst,
        "beta": beta_values,
        "beta_reasons": beta_reasons,
        "prev": previous or {},
        "coverage_ratio": covered_value / modeled_value if modeled_value else None,
        "reason": history_reason,
    }
    shares = {} if missing_history else risk_contributions(weights, returns)
    standalone = (
        {}
        if missing_history
        else {
            t: volatility(returns[t][-len(port) :])
            for t in weights
            if t in returns and len(returns[t]) > 1
        }
    )
    positions = sorted(
        (
            {
                "ticker": t,
                "sym": symbol_of[t],
                "weight": weights[t],
                "risk_share": shares.get(t, 0.0),
                "vol_annual": standalone.get(t),
            }
            for t in weights
            if not missing_history
        ),
        key=lambda r: -r["risk_share"],
    )
    buckets: dict[str, dict[str, float]] = {
        "currency": {},
        "sector": {},
        "country": {},
        "region": {},
    }
    for t, share in shares.items():
        mixes = exposures["mix"].get(symbol_of[t], {})
        for key in buckets:
            for label, w in mixes.get(key, {}).items():
                _bump(buckets[key], label, share * w)

    def weight_of(key: str, label: str) -> float | None:
        return next((r["pct"] for r in exposures[key] if r["label"] == label), None)

    contributions = {
        "positions": positions,
        **{
            key: [
                {"label": label, "risk_share": share, "weight": weight_of(key, label)}
                for label, share in sorted(b.items(), key=lambda kv: -kv[1])
            ]
            for key, b in buckets.items()
        },
    }
    scenarios = scenario_impacts(holdings, reference, factor_risk=factor_risk)
    measured_reason = next((r["reason"] for r in scenarios if r.get("reason")), "")
    metrics = {
        **conc,
        # the names the main dashboard's policy uses (core.validate_analysis_reference)
        "sector_effective_count": conc["effective_sectors"],
        "worst_compound_drawdown": _worst(scenarios, "compound"),
        "worst_historical_drawdown": _worst(scenarios, "historical"),
    }
    # policy.limits is shared with the main dashboard, whose loader rejects metrics it
    # cannot compute; limits only this monitor evaluates sit in policy.daily_limits
    policy_ref = reference.get("policy") or {}
    limits = [*policy_ref.get("limits", []), *policy_ref.get("daily_limits", [])]
    lower_bounds = {
        f"worst_{kind}_drawdown": _worst(scenarios, kind, require_complete=False)
        for kind in ("compound", "historical")
    }
    worst_reasons = {
        f"worst_{kind}_drawdown": "未計算のシナリオ: "
        + ", ".join(
            row["label"] for row in scenarios if row["kind"] == kind and row["impact_pct"] is None
        )
        for kind in ("compound", "historical")
        if any(row["kind"] == kind and row["impact_pct"] is None for row in scenarios)
    }
    policy = evaluate_limits(limits, metrics, lower_bounds=lower_bounds, reasons=worst_reasons)
    breaches = sum(1 for r in policy if r["status"] == "breach")
    history = {
        "vol_annual": stats["vol_annual"],
        "var_1d_95": var95,
        "es_1d_975": es,
        "foreign_currency_ratio": conc["foreign_currency_ratio"],
        "largest_issuer_lookthrough_ratio": conc["largest_issuer_lookthrough_ratio"],
        "max_sector_ratio": conc["max_sector_ratio"],
        "beta_topix": stats["beta"].get("topix"),
        "beta_sp500": stats["beta"].get("sp500"),
        "beta_usdjpy": stats["beta"].get("usdjpy"),
        "policy_breaches": breaches,
    }
    return {
        "as_of": as_of,
        "total": total,
        "exposures": {
            k: exposures[k]
            for k in (
                "asset_class",
                "currency",
                "country",
                "region",
                "sector",
                "issuers",
                "coverage",
            )
        },
        "concentration": conc,
        "stats": stats,
        "contributions": contributions,
        "stress": {
            "measured_factor_reason": measured_reason,
            "scenarios": scenarios,
            "episodes": episode_impacts(
                values,
                reference.get("episodes", []),
                dates,
                prices_jpy,
                total_nav=total,
                missing_holdings=[h.symbol for h in modeled if not h.ticker],
            ),
        },
        "policy": policy,
        "policy_breaches": breaches,
        "history": history,
    }
