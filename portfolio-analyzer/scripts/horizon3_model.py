"""Three-year repositioning model: buy-and-hold terminal values, solved break-evens.

Reads ``data/horizon3-inputs.private.json`` and writes ``data/horizon3-results.private.json``.
The code carries no portfolio data, so it is safe to commit; every figure lives in the
private JSON beside it.

Two corrections over the first version of this analysis, both from the 2026-08-18 review:

**Aggregation.** The first version reported ``sum(w_i * r_i)`` — the weighted mean of the
sleeves' three-year CAGRs. That is the return of a portfolio rebalanced to fixed weights
every year, not of one left alone. Buy-and-hold compounds each sleeve separately and
annualises the total, which is what a plan you execute once actually earns::

    R = (sum_i w_i (1 + r_i)^3)^(1/3) - 1

The difference is not cosmetic: it is worth 1.5pp in the worst quadrant.

**Break-evens are solved, not asserted.** The first version claimed no crossing existed
between the current portfolio and plan E, and that three of the four quadrants could not
be overturned at any multiple. Both were false — the current portfolio holds more 6857, so
a high enough terminal multiple must cross, and three quadrants carry EPS growth. Anything
of that shape is now found numerically over a wide bracket and reported with its value.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent.parent
INPUTS = HERE / "data" / "horizon3-inputs.private.json"
RESULTS = HERE / "data" / "horizon3-results.private.json"


def solve(f: Callable[[float], float], lo: float, hi: float, tol: float = 1e-9) -> float | None:
    """Bisect for a sign change in ``f`` over ``[lo, hi]``. None if the bracket holds none."""
    a, b = f(lo), f(hi)
    if a == 0:
        return lo
    if b == 0:
        return hi
    if (a > 0) == (b > 0):
        return None
    for _ in range(400):
        mid = (lo + hi) / 2
        if f(mid) == 0 or (hi - lo) < tol:
            return mid
        if (f(mid) > 0) == (a > 0):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


class Model:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        self.quads: list[str] = cfg["quadrants"]
        self.years: int = cfg["horizon_years"]
        self.sleeves: dict[str, dict] = cfg["sleeves"]
        self.tax: float = cfg["tax"]["capital_gains_rate"]

    # ---- sleeve level -------------------------------------------------

    def spec(self, name: str) -> dict[str, Any]:
        return self.sleeves.get(name) or self.cfg["reference_sleeves"][name]

    def pe0(self, name: str) -> float:
        """Starting multiple.  An equal-money basket aggregates by harmonic mean.

        Averaging the constituents' P/Es arithmetically would answer a different
        question — the mean multiple per *name* rather than per yen invested. Earnings
        yields are what add linearly across an equal-money basket, so their reciprocal
        is the basket's multiple.
        """
        s = self.spec(name)
        if "pe0" in s:
            return float(s["pe0"])
        pes = [c["pe"] for c in s["constituents"].values()]
        return len(pes) / sum(1 / p for p in pes)

    def sleeve_return(self, name: str, q: int, *, pe1: float | None = None) -> float:
        """Annualised three-year return for one sleeve, before any FX move."""
        s = self.spec(name)
        if s["kind"] == "fixed":
            return s["returns"][q]
        terminal = s["pe1"][q] if pe1 is None else pe1
        growth = s["eps3"][q] * terminal / self.pe0(name)
        return growth ** (1 / self.years) - 1 + s["dividend_yield"]

    def breakeven_pe(self, name: str, q: int, hurdle: float) -> float:
        """Terminal multiple at which `name` clears `hurdle` annualised."""
        s = self.spec(name)
        return self.pe0(name) * (1 + hurdle - s["dividend_yield"]) ** self.years / s["eps3"][q]

    # ---- portfolio level ----------------------------------------------

    def portfolio_return(
        self,
        weights: dict[str, float],
        q: int,
        *,
        mode: str = "buy_and_hold",
        fx_shock: float = 0.0,
        pe1_override: tuple[str, float] | None = None,
    ) -> float:
        """Annualised three-year portfolio return.

        ``buy_and_hold`` compounds each sleeve then annualises the sum.  ``rebalanced``
        reproduces the weighted-mean-of-CAGRs figure the first version reported, kept so
        the two can be shown side by side.  ``fx_shock`` is the three-year change in
        USD/JPY and lands only on the sleeves denominated in USD.
        """
        total = sum(weights.values())
        acc = 0.0
        for name, value in weights.items():
            over = pe1_override[1] if pe1_override and pe1_override[0] == name else None
            r = self.sleeve_return(name, q, pe1=over)
            spec = self.spec(name)
            gross = (1 + r) ** self.years
            if fx_shock and spec.get("currency") == "USD":
                gross *= 1 + fx_shock
            acc += value / total * (gross if mode == "buy_and_hold" else r)
        return acc ** (1 / self.years) - 1 if mode == "buy_and_hold" else acc

    # ---- plan construction ---------------------------------------------

    def weights(self, plan: str) -> dict[str, float]:
        w = {k: float(v["value_jpy"]) for k, v in self.sleeves.items()}
        if plan == "現状":
            return w
        spec = self.cfg["plans"][plan]
        base = self.cfg["plans"][spec["inherits"]] if "inherits" in spec else spec

        pool = 0.0
        for name in base["sell"]:
            pool += w.pop(name)
        floor = base["cash_floor_jpy"]
        pool += w["現金"] - floor
        w["現金"] = float(floor)
        for name, share in base["allocate"].items():
            w[name] = w.get(name, 0.0) + pool * share

        if "halve" in spec:
            half = w[spec["halve"]] / 2
            w[spec["halve"]] -= half
            w[spec["halve_into"]] += half
        if "liquidate" in spec:
            w[spec["liquidate_into"]] += w.pop(spec["liquidate"])
        return w

    # ---- derived reporting ---------------------------------------------

    def usd_share(self, weights: dict[str, float]) -> float:
        total = sum(weights.values())
        return sum(
            v for k, v in weights.items()
            if (self.sleeves.get(k) or {}).get("currency") == "USD"
        ) / total

    def basket_pe(self, name: str) -> dict[str, float]:
        """Equal-money baskets aggregate by harmonic mean, not arithmetic."""
        pes = [c["pe"] for c in self.cfg["reference_sleeves"][name]["constituents"].values()]
        gr = [c["revenue_growth"] for c in self.cfg["reference_sleeves"][name]["constituents"].values()]
        return {
            "arithmetic_pe": sum(pes) / len(pes),
            "harmonic_pe": len(pes) / sum(1 / p for p in pes),
            "revenue_growth_min": min(gr),
            "revenue_growth_max": max(gr),
        }

    def nisa_crossover(self, q: int, alternative: str = "QQQ") -> dict[str, float]:
        """Terminal multiple at which holding 6857 inside NISA matches a taxed switch.

        The comparison is deliberately generous to holding: 6857 stays untaxed, the
        replacement is taxed in full.  A loss on the replacement is credited at the
        capital-gains rate, which assumes gains elsewhere to offset it.
        """
        name = "6857 アドバンテスト"
        v = self.sleeves[name]["value_jpy"]
        alt_r = self.sleeve_return(alternative, q)
        gross = v * (1 + alt_r) ** self.years
        gain = gross - v
        net = gross - gain * self.tax if gain > 0 else gross + (-gain) * self.tax
        def gap(pe: float) -> float:
            return v * (1 + self.sleeve_return(name, q, pe1=pe)) ** self.years - net

        pe = solve(gap, 0.01, 100_000.0)
        return {
            "alternative_after_tax_jpy": net,
            "hold_at_base_pe_jpy": v * (1 + self.sleeve_return(name, q)) ** self.years,
            "crossover_pe": pe,
            "base_pe1": self.sleeves[name]["pe1"][q],
        }


def main() -> None:
    cfg = json.loads(INPUTS.read_text(encoding="utf-8"))
    m = Model(cfg)
    quads, plans = m.quads, ["現状", "D", "E", "F"]
    weights = {p: m.weights(p) for p in plans}
    out: dict[str, Any] = {
        "generated_from": str(INPUTS.name),
        "as_of": cfg["as_of"],
        "aggregation": cfg["aggregation"],
        "horizon_years": m.years,
    }

    # 1. Sleeve returns.
    out["sleeve_returns"] = {
        name: {q: m.sleeve_return(name, i) for i, q in enumerate(quads)}
        for name in list(m.sleeves) + list(cfg["reference_sleeves"])
    }

    # 2. Portfolio returns, both aggregations, so the difference stays visible.
    out["portfolio_returns"] = {
        mode: {
            p: {q: m.portfolio_return(weights[p], i, mode=mode) for i, q in enumerate(quads)}
            for p in plans
        }
        for mode in ("buy_and_hold", "rebalanced")
    }
    out["improvement_vs_current"] = {
        mode: {
            p: {
                q: out["portfolio_returns"][mode][p][q] - out["portfolio_returns"][mode]["現状"][q]
                for q in quads
            }
            for p in plans if p != "現状"
        }
        for mode in ("buy_and_hold", "rebalanced")
    }

    # 3. Composition and currency exposure.
    out["composition"] = {
        p: {k: v / sum(weights[p].values()) for k, v in sorted(
            weights[p].items(), key=lambda kv: -kv[1])}
        for p in plans
    }
    out["usd_share"] = {p: m.usd_share(weights[p]) for p in plans}

    # 4. Break-even multiples.
    out["breakeven_pe"] = {
        name: {
            f"hurdle_{int(h * 100)}pct": {q: m.breakeven_pe(name, i, h) for i, q in enumerate(quads)}
            for h in (0.0, 0.10)
        }
        for name in ("6857 アドバンテスト", "TER テラダイン", "SMH 半導体ETF", "需要側4社バスケット")
    }

    # 5. Where the current portfolio would overtake plan E, if anywhere.
    out["current_vs_E_crossover"] = {}
    for mode in ("buy_and_hold", "rebalanced"):
        row: dict[str, Any] = {}
        for i, q in enumerate(quads):
            def gap(pe: float, i: int = i, mode: str = mode) -> float:
                over = ("6857 アドバンテスト", pe)
                return (m.portfolio_return(weights["現状"], i, mode=mode, pe1_override=over)
                        - m.portfolio_return(weights["E"], i, mode=mode, pe1_override=over))

            pe = solve(gap, 1.0, 100_000.0)
            row[q] = {
                "crossover_pe": pe,
                "sleeve_return_at_crossover":
                    m.sleeve_return("6857 アドバンテスト", i, pe1=pe) if pe else None,
                "within_charted_range": bool(pe is not None and pe <= 73.2),
            }
        out["current_vs_E_crossover"][mode] = row

    # 6. Sensitivity of the whole portfolio to 6857's terminal multiple (the chart).
    grid = [30.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 73.2]
    out["pe_sensitivity_q1"] = {
        mode: [
            {
                "pe1": pe,
                "sleeve_return": m.sleeve_return("6857 アドバンテスト", 0, pe1=pe),
                "現状": m.portfolio_return(weights["現状"], 0, mode=mode,
                                         pe1_override=("6857 アドバンテスト", pe)),
                "E": m.portfolio_return(weights["E"], 0, mode=mode,
                                        pe1_override=("6857 アドバンテスト", pe)),
            }
            for pe in grid
        ]
        for mode in ("buy_and_hold", "rebalanced")
    }

    # 7. NISA: hold 6857 untaxed vs switch to a fully taxed QQQ, in every quadrant.
    out["nisa"] = {q: m.nisa_crossover(i) for i, q in enumerate(quads)}
    v6857 = m.sleeves["6857 アドバンテスト"]["value_jpy"]
    out["nisa_wrapper_value"] = {}
    for i, q in enumerate(quads):
        end = v6857 * (1 + m.sleeve_return("6857 アドバンテスト", i)) ** m.years
        pnl = end - v6857
        out["nisa_wrapper_value"][q] = {
            "terminal_jpy": end,
            "pnl_jpy": pnl,
            "wrapper_value_jpy": pnl * m.tax,
            "kind": "非課税メリット" if pnl >= 0 else "通算できず消える損失価値",
        }

    # 8. FX: plan E raises USD exposure by 20pp, so the comparison cannot hold it fixed.
    out["fx_sensitivity"] = {
        f"{int(s * 100):+d}%": {
            p: {q: m.portfolio_return(weights[p], i, fx_shock=s) for i, q in enumerate(quads)}
            for p in plans
        }
        for s in cfg["scenarios"]["fx_shocks"]
    }
    out["fx_improvement_E_vs_current"] = {
        f"{int(s * 100):+d}%": {
            q: (m.portfolio_return(weights["E"], i, fx_shock=s)
                - m.portfolio_return(weights["現状"], i, fx_shock=s))
            for i, q in enumerate(quads)
        }
        for s in cfg["scenarios"]["fx_shocks"]
    }
    # The yen move at which plan E stops improving each quadrant.
    out["fx_breakeven"] = {}
    for i, q in enumerate(quads):
        def gap(shock: float, i: int = i) -> float:
            return (m.portfolio_return(weights["E"], i, fx_shock=shock)
                    - m.portfolio_return(weights["現状"], i, fx_shock=shock))

        out["fx_breakeven"][q] = solve(gap, -0.95, 5.0)

    # 9. Basket aggregation, arithmetic vs harmonic.
    out["baskets"] = {n: m.basket_pe(n) for n in ("需要側4社バスケット", "前工程5社バスケット")}

    RESULTS.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- console summary ------------------------------------------------
    def row(label: str, vals: dict[str, float], unit: str = "%") -> str:
        return f"{label:22}" + "".join(f"{vals[q] * 100:>10.2f}{unit}" for q in quads)

    print("=== ポートフォリオ3年年率：集計方式の比較 ===")
    print(f"{'':22}" + "".join(f"{q:>11}" for q in quads))
    for mode, tag in (("rebalanced", "年次リバランス"), ("buy_and_hold", "買い持ち")):
        for p in plans:
            print(row(f"{p} ({tag})", out["portfolio_returns"][mode][p]))
        print()

    print("=== 案E − 現状 の改善幅 ===")
    print(f"{'':22}" + "".join(f"{q:>11}" for q in quads))
    for mode, tag in (("rebalanced", "年次リバランス"), ("buy_and_hold", "買い持ち")):
        print(row(f"{tag}", out["improvement_vs_current"][mode]["E"], "pp"))

    print("\n=== 現状が案Eを上回る 6857 終端PER（前版は『存在しない』と断定）===")
    for mode in ("rebalanced", "buy_and_hold"):
        for q in quads:
            c = out["current_vs_E_crossover"][mode][q]
            pe = c["crossover_pe"]
            s = f"{pe:,.1f}倍" if pe else "1〜100,000倍に交点なし"
            r = c["sleeve_return_at_crossover"]
            extra = f"（6857 年率 {r * 100:.1f}%）" if r is not None else ""
            print(f"  {mode:13} {q:8} {s}{extra}")

    print("\n=== NISA: 6857保有(非課税) vs QQQ乗換(全額課税) の逆転PER ===")
    print(f"{'象限':10}{'基準終端PER':>12}{'逆転PER':>10}{'保有(基準)':>12}{'乗換(税引後)':>14}")
    for q in quads:
        n = out["nisa"][q]
        print(f"{q:10}{n['base_pe1']:>12.0f}{n['crossover_pe']:>10.2f}"
              f"{n['hold_at_base_pe_jpy'] / 1e4:>11,.0f}万{n['alternative_after_tax_jpy'] / 1e4:>13,.0f}万")

    print("\n=== 為替感応度：案E − 現状 の改善幅 ===")
    print(f"{'USD/JPY':22}" + "".join(f"{q:>11}" for q in quads))
    for s in cfg["scenarios"]["fx_shocks"]:
        k = f"{int(s * 100):+d}%"
        print(row(k, out["fx_improvement_E_vs_current"][k], "pp"))
    print("\n  改善が消える円高水準:")
    for q in quads:
        b = out["fx_breakeven"][q]
        print(f"    {q:10} " + (f"USD/JPY {b * 100:+.1f}%" if b is not None else "検証範囲では消えない"))

    print("\n=== 直接USD資産の比率 ===")
    for p in plans:
        print(f"  {p:6} {out['usd_share'][p] * 100:>6.2f}%")

    print("\n=== バスケット集約PER ===")
    for n, b in out["baskets"].items():
        print(f"  {n}: 算術 {b['arithmetic_pe']:.2f} / 調和 {b['harmonic_pe']:.2f} "
              f"（売上成長 {b['revenue_growth_min'] * 100:.1f}〜{b['revenue_growth_max'] * 100:.1f}%）")

    print(f"\n書き出し: {RESULTS}")


if __name__ == "__main__":
    main()
