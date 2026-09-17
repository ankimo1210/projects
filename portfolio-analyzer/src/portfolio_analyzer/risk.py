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
from typing import Any

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
    holdings: Sequence[Holding], reference: dict[str, Any]
) -> list[dict[str, Any]]:
    """Σ value × factor loading × shock for every scenario in the reference (worst first)."""
    instruments = _instruments(reference)
    total = sum(float(h.value_jpy) for h in holdings)
    out = []
    for sc in reference.get("scenarios", []):
        impact = 0.0
        for h in holdings:
            loadings = instruments.get(h.symbol, {}).get("factor_loadings", {})
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
            }
        )
    return sorted(out, key=lambda r: r["impact_jpy"])


def episode_impacts(
    values_by_ticker: dict[str, float],
    episodes: Sequence[dict[str, Any]],
    dates: Sequence[str],
    prices_jpy: dict[str, Sequence[float | None]],
) -> list[dict[str, Any]]:
    """Each episode replayed on today's holdings: last close before ``start`` → close at ``end``."""
    total = sum(values_by_ticker.values())
    out = []
    for ep in episodes:
        before = [i for i, d in enumerate(dates) if d < str(ep["start"])]
        upto = [i for i, d in enumerate(dates) if d <= str(ep["end"])]
        if not before or not upto or upto[-1] <= before[-1]:
            continue
        i0, i1 = before[-1], upto[-1]
        impact = covered = 0.0
        for t, v in values_by_ticker.items():
            series = prices_jpy.get(t)
            if not series or series[i0] in (None, 0) or series[i1] is None:
                continue
            impact += v * (float(series[i1]) / float(series[i0]) - 1.0)
            covered += v
        out.append(
            {
                "id": str(ep["id"]),
                "label": str(ep.get("label", ep["id"])),
                "start": str(ep["start"]),
                "end": str(ep["end"]),
                "impact_jpy": impact,
                "impact_pct": (impact / total if total else None),
                "coverage": (covered / total if total else None),
            }
        )
    return sorted(out, key=lambda r: r["impact_jpy"])


# ---- limits ----


def evaluate_limits(
    limits: Sequence[dict[str, Any]], metrics: dict[str, Any]
) -> list[dict[str, Any]]:
    out = []
    for limit in limits:
        value = metrics.get(str(limit["metric"]))
        op, threshold = str(limit["operator"]), float(limit["threshold"])
        if value is None or op not in ("<=", ">="):
            status = "na"
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
                "status": status,
                "note": str(limit.get("note", "")),
            }
        )
    return out


# ---- the payload block ----


def _worst(scenarios: Sequence[dict[str, Any]], kind: str) -> float | None:
    """The largest loss ratio among scenarios of one kind, as a positive number."""
    ratios = [
        r["impact_pct"] for r in scenarios if r["kind"] == kind and r["impact_pct"] is not None
    ]
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
    returns: dict[str, list[float]],
    benchmarks: dict[str, list[float]],
    dates: Sequence[str],
    prices_jpy: dict[str, Sequence[float | None]],
    as_of: str,
    previous: dict[str, Any] | None = None,
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
        if h.ticker and not h.is_cash and total:
            weights[h.ticker] = weights.get(h.ticker, 0.0) + float(h.value_jpy) / total
            values[h.ticker] = values.get(h.ticker, 0.0) + float(h.value_jpy)
            symbol_of[h.ticker] = h.symbol
    port = portfolio_returns(weights, returns)
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
        "beta": {name: beta(port, series) for name, series in benchmarks.items()},
        "prev": previous or {},
    }
    shares = risk_contributions(weights, returns)
    standalone = {
        t: volatility([x if x is not None else 0.0 for x in returns[t][-len(port) :]])
        for t in weights
        if t in returns and len(returns[t]) > 1
    }
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
    scenarios = scenario_impacts(holdings, reference)
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
    policy = evaluate_limits(limits, metrics)
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
            "scenarios": scenarios,
            "episodes": episode_impacts(values, reference.get("episodes", []), dates, prices_jpy),
        },
        "policy": policy,
        "policy_breaches": breaches,
        "history": history,
    }
