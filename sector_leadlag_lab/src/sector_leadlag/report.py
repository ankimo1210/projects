"""Markdown tables from the results JSON; README's result tables are copied from summary.md.

``render_corrected`` writes the corrected data's summary with the record beside it (PREREG §5).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from .evaluate import ALPHA
from .timing import VARIANTS

SCENARIO_LABELS = {
    "base": "基準（500万円・0bp）",
    "cost_2bp": "片道 2bp",
    "capital_3m": "300万円",
    "capital_10m": "1,000万円",
    "cost_5bp": "片道 5bp（報告だけ）",
}
RULE_LABELS = {
    "C2": "C2 始値0",
    "C1": "C1 桁の跳び",
    "C4": "C4 分割の日の配当",
    "C5": "C5 終値を超える配当",
    "C6": "C6 ETF の配当日",
    "C3": "C3 行の欠け",
}
STAGES = ("g0", "g1", "main_a", "main_b", "diagnostics")
CONDITIONS: tuple[tuple[str, Callable[[dict], bool]], ...] = (
    ("G0 の再現", lambda e: e["replicated"]),
    (
        "①（H1 が有意で、本番 B の係数が正）",
        lambda e: e["h1_p"] < ALPHA and e["beta_b_period_b"] > 0,
    ),
    ("②（H2 の1と2が有意）", lambda e: e["h2_p_cash"] < ALPHA and e["h2_p_spread"] < ALPHA),
    ("③（費用と元手を変えても符号が同じ）", lambda e: e["robust"]),
    ("④（本番 B で1と2が正）", lambda e: e["b_mean_cash"] > 0 and e["b_mean_spread"] > 0),
)
SIGNAL_LABELS = {
    "pca_lambda0": "正則化なしの PCA（λ=0）",
    "momentum": "モメンタム",
    "k1": "PCA SUB（K=1）",
    "variant_b": "副の型B（日本側をバスケットに）",
}


def _load(results: Path, name: str) -> dict | None:
    path = results / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _missing(x: float | None) -> bool:
    return x is None or x != x  # None, or NaN (an empty period)


def _pct(x: float | None) -> str:
    return "—" if _missing(x) else f"{100 * x:.2f}%"


def _num(x: float | None, digits: int = 2) -> str:
    return "—" if _missing(x) else f"{x:.{digits}f}"


def _fit(fit: dict | None) -> str:
    if fit is None:
        return "—"
    return f"{fit['beta_1e4']:.2f}（t={fit['t']:.2f}、p={fit['p']:.3f}）"


def _g0(g0: dict) -> list[str]:
    p = g0["published"]
    lines = [
        "## G0 再現（ETF だけ、2026-07-23 まで）",
        "",
        "| 並べ方 | AR 2015–2025 | RISK | R/R | MDD | A 年率 | B1 年率 | B1 累積 | C2O A→B1 "
        "| 係数 A（×1e-4） | 係数 B1 | A の日数 | 合格 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        f"| 公開値 | {_pct(p['ar'])} | {_pct(p['risk'])} | {p['rr']:.2f} | {_pct(p['mdd'])} "
        f"| {_pct(p['mean_a'])} | {_pct(p['mean_b1'])} | {_pct(p['cumulative_b1'])} "
        f"| {_pct(p['c2o_a'])}→{_pct(p['c2o_b1'])} | {p['beta_a_1e4']:.2f} "
        f"| {p['beta_b1_1e4']:.2f} | {p['days_a']} | |",
    ]
    for name, row in g0["variants"].items():
        o = row["original"]
        lines.append(
            f"| {name} | {_pct(o['ar'])} | {_pct(o['risk'])} | {o['rr']:.2f} | {_pct(o['mdd'])} "
            f"| {_pct(row['a']['mean_ann'])} | {_pct(row['b1']['mean_ann'])} "
            f"| {_pct(row['b1']['cumulative'])} | {_pct(row['c2o_a'])}→{_pct(row['c2o_b1'])} "
            f"| {_fit(row['fit_a'])} | {_fit(row['fit_b1'])} | {row['a']['days']} "
            f"| {'○' if row['pass'] else '×'} |"
        )
    chosen = g0["selected"] or "なし（replication_failed）"
    names = g0["checks"]["names"]
    lines += [
        "",
        f"選んだ並べ方：{chosen}。",
        "",
        f"銘柄：TOPIX500 {names['topix500']}、価格あり {names['with_prices']}、"
        f"なし {len(names['missing'])}（{', '.join(names['missing']) or 'なし'}）。",
        "",
        "| ETF（業種） | 日数 | 出来高ゼロ | 割合 | うち前日終値のまま |",
        "|---|---|---|---|---|",
    ]
    for sector, row in g0["checks"]["etf_zero_volume"].items():
        lines.append(
            f"| {sector} | {row['days']} | {row['zero']} | {_pct(row['share'])} "
            f"| {_pct(row['stale'])} |"
        )
    checks = g0["checks"]
    lines += [
        "",
        f"外れ値（|O2C| か |C2O| が 20% 超、除外しない）：{checks['outliers']['count']} 件。"
        f"分割 {checks['splits']['events']} 件のうち権利落ち日の C2O が外れたもの "
        f"{checks['splits']['flagged_count']} 件。配当 {checks['dividends']['events']} 件"
        f"（権利落ち日の |C2O| の平均：配当込み {_pct(checks['dividends']['mean_abs_c2o_with'])}、"
        f"配当なし {_pct(checks['dividends']['mean_abs_c2o_without'])}）。",
        "",
    ]
    cells = [
        (corr, sector, year)
        for sector, years in checks["coverage"].items()
        for year, corr in years.items()
        if not _missing(corr)
    ]
    lowest = sorted(cells)[:10]
    lines += [
        "ETF と H1 のバスケットの C2C の相関が低い業種と年（下位10）：",
        "",
        "| 業種 | 年 | 相関 |",
        "|---|---|---|",
        *[f"| {sector} | {year} | {corr:.3f} |" for corr, sector, year in lowest],
        "",
    ]
    return lines


def _g1(g1: dict) -> list[str]:
    return [
        "## G1 合成データ（米国を循環的にずらした世界）",
        "",
        f"H1 の検定が有意になった回数：{g1['significant']} / {g1['count']}"
        f"（合格の条件は2回以下）。合格：{'○' if g1['pass'] else '×'}。",
        f"検出力：係数 {g1['planted_beta_1e4']:.2f}×1e-4（0.5 β_ETF）を埋め込んで検出できた回数 "
        f"{g1['detected']} / {g1['count']}。",
        "",
    ]


def _main_a(a: dict) -> list[str]:
    low, high = a["h1"]["ratio_ci"]
    lines = [
        f"## 本番 A（2015-01-05〜2026-03-18、並べ方 {a['variant']}）",
        "",
        "| 価格 | 係数（×1e-4） |",
        "|---|---|",
        f"| H1 のバスケット | {_fit(a['h1']['basket'])} |",
        f"| ETF | {_fit(a['h1']['etf'])} |",
        "",
        f"比 β_B/β_ETF の95%区間：{low:.2f}〜{high:.2f}。H1：{'有意' if a['h1']['pass'] else '有意でない'}。",
        "",
        "| 設定 | 現物の買い 年率 | シャープ | CER | p | 平均の銘柄数 | 使った元手 "
        "| 業種の選び方の差 年率 | p |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, row in a["h2"].items():
        cash, spread = row["cash"], row["spread"]
        lines.append(
            f"| {SCENARIO_LABELS.get(name, name)} | {_pct(cash['mean_ann'])} "
            f"| {_num(cash['sharpe'])} | {_pct(cash['cer'])} | {_num(cash['p'], 4)} "
            f"| {_num(cash['mean_names'], 1)} | {_pct(cash['invested'])} "
            f"| {_pct(spread['mean_ann'])} | {_num(spread['p'], 4)} |"
        )
    lines += [
        "",
        f"H2：{'両方有意' if a['h2_pass'] else '有意でない'}。頑健性（2bp・300万円・1,000万円で符号が同じ）："
        f"{'○' if a['robust'] else '×'}。",
        "",
    ]
    return lines


def _main_b(b: dict) -> list[str]:
    h3 = b["h3"]
    return [
        "## 本番 B（2026-03-19〜2026-10-05）と判定",
        "",
        f"- H1 のバスケットの係数：{_fit(b['h1']['basket'])}。ETF：{_fit(b['h1']['etf'])}。",
        f"- 現物の買い：年率 {_pct(b['h2']['cash']['mean_ann'])}（{b['h2']['cash']['days']}日）。"
        f"業種の選び方の差：年率 {_pct(b['h2']['spread']['mean_ann'])}。",
        f"- ETF のロング・ショート：B1 年率 {_pct(b['etf_long_short']['b1']['mean_ann'])}"
        f"（累積 {_pct(b['etf_long_short']['b1']['cumulative'])}）、"
        f"B2 年率 {_pct(b['etf_long_short']['b2']['mean_ann'])}"
        f"（累積 {_pct(b['etf_long_short']['b2']['cumulative'])}、{h3['days_b2']}日）。",
        f"- H3：`{h3['label']}`（0 より低い p={h3['p_below_zero']:.3f}、"
        f"A より低い p={h3['p_below_a']:.3f}）。",
        "",
        f"**判定：`{b['verdict']}`**",
        "",
    ]


def _diagnostics(d: dict) -> list[str]:
    lines = [
        "## 診断（判定には使わない）",
        "",
        "| 始値の置き換え | 係数（×1e-4） |",
        "|---|---|",
    ]
    lines += [f"| {name} | {_fit(fit)} |" for name, fit in d["stale_opens"].items()]
    lines += [
        "",
        "| プラセボ | 実際の変化 年率 | 疑似の最小 | 疑似のうち実際以下 |",
        "|---|---|---|---|",
    ]
    for name, row in d["placebo"].items():
        lines.append(
            f"| {name} | {_pct(row['actual_ann'])} | {_pct(row['pseudo_min_ann'])} "
            f"| {_pct(row['share_at_or_below'])} |"
        )
    lines += ["", "| 分解 | 区間 | A | B1 | B2 |", "|---|---|---|---|---|"]
    for name, legs in d["decomposition"].items():
        for leg, row in legs.items():
            lines.append(
                f"| {name} | {leg} | {_pct(row['a'])} | {_pct(row['b1'])} | {_pct(row['b2'])} |"
            )
    lines += [
        "",
        f"- C2O を加えた回帰：ETF {_fit(d['c2o_control']['etf'])}、"
        f"バスケット {_fit(d['c2o_control']['basket'])}。",
        f"- 取引時間の延長の前後（バスケット）：{_fit(d['session_change']['basket']['before'])} → "
        f"{_fit(d['session_change']['basket']['after'])}。ETF：{_fit(d['session_change']['etf']['before'])} → "
        f"{_fit(d['session_change']['etf']['after'])}。",
        f"- 上位10銘柄のバスケット：A {_fit(d['top10_basket']['a'])}、B {_fit(d['top10_basket']['b'])}。",
        "",
        "| 別のシグナル | バスケットの係数 | ETF の係数 | ETF の AR 2015–2025 |",
        "|---|---|---|---|",
    ]
    for name, row in d["other_signals"].items():
        lines.append(
            f"| {SIGNAL_LABELS.get(name, name)} | {_fit(row['basket'])} | {_fit(row['etf'])} "
            f"| {_pct(row['etf_original']['ar'])} |"
        )
    c = d["reference_c"]
    lines += [
        "",
        f"参考 C（{c['days']}日）：バスケット {_fit(c['basket'])}、ETF {_fit(c['etf'])}、"
        f"ETF のロング・ショート 年率 {_pct(c['etf_long_short']['mean_ann'])}、"
        f"現物の買い 年率 {_pct(c['cash']['mean_ann'])}。",
        "",
    ]
    return lines


def _sections(results: Path) -> list[str]:
    lines: list[str] = []
    for name, part in (
        ("g0", _g0),
        ("g1", _g1),
        ("main_a", _main_a),
        ("main_b", _main_b),
        ("diagnostics", _diagnostics),
    ):
        result = _load(results, name)
        if result is not None:
            lines += part(result)
    return lines


def render(results: Path) -> str:
    lines = ["# 日米業種リードラグ（候補12）の結果", "", *_sections(results)]
    return "\n".join(lines).rstrip() + "\n"


def _at(result: dict | None, *keys):
    """result[k1][k2]...; None when any level is missing."""
    for key in keys:
        if not isinstance(result, dict) or key not in result:
            return None
        result = result[key]
    return result


def _mark(x: bool | None) -> str:
    return "—" if x is None else "○" if x else "×"


def _mean_p(part: dict | None) -> str:
    if part is None:
        return "—"
    return f"{_pct(part['mean_ann'])}（p={_num(part['p'], 4)}）"


def _interval(ci: list | None) -> str:
    return "—" if ci is None else f"{ci[0]:.2f}〜{ci[1]:.2f}"


def _g1_count(g1: dict | None) -> str:
    if g1 is None:
        return "—"
    return f"{g1['significant']} / {g1['count']}（合格 {_mark(g1['pass'])}）"


def _h3(h3: dict | None) -> str:
    if h3 is None:
        return "—"
    return f"`{h3['label']}`（0 より低い p={h3['p_below_zero']:.3f}）"


def _verdict(b: dict | None) -> str:
    return "—" if b is None else f"`{b['verdict']}`"


def _comparison_rows() -> list[tuple[str, Callable[[dict], str]]]:
    rows: list[tuple[str, Callable[[dict], str]]] = [
        ("並べ方", lambda r: _at(r["g0"], "selected") or "—")
    ]
    for v in VARIANTS:
        rows += [
            (
                f"G0 {v}：AR 2015–2025",
                lambda r, v=v: _pct(_at(r["g0"], "variants", v, "original", "ar")),
            ),
            (
                f"G0 {v}：本番 A の ETF の係数",
                lambda r, v=v: _fit(_at(r["g0"], "variants", v, "fit_a")),
            ),
            (f"G0 {v}：合格", lambda r, v=v: _mark(_at(r["g0"], "variants", v, "pass"))),
        ]
    rows += [
        ("G1：有意になった回数", lambda r: _g1_count(r["g1"])),
        ("H1：バスケットの係数（×1e-4）", lambda r: _fit(_at(r["main_a"], "h1", "basket"))),
        ("H1：ETF の係数", lambda r: _fit(_at(r["main_a"], "h1", "etf"))),
        ("比 β_B/β_ETF の95%区間", lambda r: _interval(_at(r["main_a"], "h1", "ratio_ci"))),
    ]
    for s in ("base", "cost_2bp", "cost_5bp"):
        rows += [
            (
                f"H2 {SCENARIO_LABELS[s]}：現物の買い 年率",
                lambda r, s=s: _mean_p(_at(r["main_a"], "h2", s, "cash")),
            ),
            (
                f"H2 {SCENARIO_LABELS[s]}：業種の選び方の差 年率",
                lambda r, s=s: _mean_p(_at(r["main_a"], "h2", s, "spread")),
            ),
        ]
    rows += [
        ("頑健性（③）", lambda r: _mark(_at(r["main_a"], "robust"))),
        ("本番 B：バスケットの係数", lambda r: _fit(_at(r["main_b"], "h1", "basket"))),
        ("本番 B：ETF の係数", lambda r: _fit(_at(r["main_b"], "h1", "etf"))),
        ("本番 B：現物の買い 年率", lambda r: _pct(_at(r["main_b"], "h2", "cash", "mean_ann"))),
        (
            "本番 B：業種の選び方の差 年率",
            lambda r: _pct(_at(r["main_b"], "h2", "spread", "mean_ann")),
        ),
        (
            "ETF のロング・ショート B1 年率",
            lambda r: _pct(_at(r["main_b"], "etf_long_short", "b1", "mean_ann")),
        ),
        (
            "ETF のロング・ショート B2 年率",
            lambda r: _pct(_at(r["main_b"], "etf_long_short", "b2", "mean_ann")),
        ),
        ("H3", lambda r: _h3(_at(r["main_b"], "h3"))),
    ]
    for name, label in (("basket", "バスケット"), ("etf", "ETF")):
        for when, word in (("before", "前"), ("after", "後")):
            rows.append(
                (
                    f"取引時間の延長の{word}（{label}）",
                    lambda r, n=name, w=when: _fit(_at(r["diagnostics"], "session_change", n, w)),
                )
            )
    rows.append(("判定", lambda r: _verdict(r["main_b"])))
    return rows


def reading(record: dict, corrected: dict) -> tuple[str | None, str]:
    """PREREG §5: the label, and one line on what the corrected data changed."""
    g0, g1, b = corrected["g0"], corrected["g1"], corrected["main_b"]
    pairing = ""
    if g0 is not None and g0["selected"] != _at(record["g0"], "selected"):
        pairing = (
            f"並べ方が {_at(record['g0'], 'selected')} から {g0['selected'] or 'なし'} に変わった。"
        )
    if g0 is not None and not g0["pass"]:
        return (
            "verdict_data_dependent",
            "直したデータでは G0 で止まった（`replication_failed`）。" + pairing,
        )
    if g1 is not None and not g1["pass"]:
        return "verdict_data_dependent", "直したデータでは G1 が不合格で止まった。" + pairing
    if b is None or record["main_b"] is None:
        return None, "直したデータの本番 B はまだない。" + pairing
    kept = record["main_b"]["verdict"]
    if b["verdict"] == kept:
        return "verdict_robust", f"直したデータの判定も `{kept}`。" + pairing
    changed = [
        label
        for label, holds in CONDITIONS
        if holds(record["main_b"]["evidence"]) != holds(b["evidence"])
    ]
    return (
        "verdict_data_dependent",
        f"直したデータの判定は `{b['verdict']}`（記録は `{kept}`）。"
        f"変わった条件：{'、'.join(changed) or 'なし'}。" + pairing,
    )


def _corrections(c: dict | None) -> list[str]:
    if c is None:
        return []
    lines = [
        "## 直したもの（corrections.json）",
        "",
        "| 規則 | ETF | 株 | 米国 |",
        "|---|---|---|---|",
    ]
    for rule, label in RULE_LABELS.items():
        n = c["counts"].get(rule, {})
        lines.append(f"| {label} | {n.get('etf', 0)} | {n.get('stock', 0)} | {n.get('us', 0)} |")
    missing = c["missing_known"]
    known = (
        "すべて直った" if not missing else "直っていない：" + "、".join(m["label"] for m in missing)
    )
    return [*lines, "", f"既知の誤り（設計書 §2）：{known}。", ""]


def _decomposition(record: dict | None, fixed: dict | None) -> list[str]:
    lines = [
        "## 分解（区間ごとのロング・ショートの年率。記録／直したデータ）",
        "",
        "| 価格 | 区間 | A | B1 | B2 |",
        "|---|---|---|---|---|",
    ]
    for name, label in (("etf", "ETF"), ("basket", "バスケット")):
        for leg in ("c2o", "o2c", "c2c"):
            cells = [
                f"{_pct(_at(record, 'decomposition', name, leg, p))}／"
                f"{_pct(_at(fixed, 'decomposition', name, leg, p))}"
                for p in ("a", "b1", "b2")
            ]
            lines.append(f"| {label} | {leg.upper()} | {' | '.join(cells)} |")
    return [*lines, ""]


def render_corrected(record: Path, corrected: Path) -> str:
    """The corrected data's summary: the reading of PREREG §5, the record beside it, every table."""
    kept = {name: _load(record, name) for name in STAGES}
    fixed = {name: _load(corrected, name) for name in STAGES}
    label, line = reading(kept, fixed)
    lines = [
        "# 日米業種リードラグ（候補12）：直したデータでの再計算",
        "",
        "PREREG §5 の確認で、判定のあとに回した。記録の判定（`results/main_b.json`）は変えない。",
        "",
        "## 読み方（PREREG §5）",
        "",
        f"**`{label}`**：{line}" if label else line,
        "",
        *_corrections(_load(corrected, "corrections")),
        "## 記録と並べた表",
        "",
        "| 項目 | 記録 | 直したデータ |",
        "|---|---|---|",
        *[f"| {name} | {cell(kept)} | {cell(fixed)} |" for name, cell in _comparison_rows()],
        "",
        *_decomposition(kept["diagnostics"], fixed["diagnostics"]),
        "## 直したデータの各段の結果",
        "",
        *[f"#{text}" if text.startswith("## ") else text for text in _sections(corrected)],
    ]
    return "\n".join(lines).rstrip() + "\n"
