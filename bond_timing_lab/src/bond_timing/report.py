"""Markdown tables from the results JSON; README's result tables are copied from summary.md."""

from __future__ import annotations

import json
from pathlib import Path

LABELS = {
    "P1": "P1 単純ルール",
    "P2": "P2 主成分3つの OLS",
    "P3": "P3 主成分＋マクロ8つの OLS",
    "P4": "P4 NN（フォワード＋マクロ）",
    "P5": "P5 Extra Trees（フォワード＋マクロ）",
}


def _load(results: Path, name: str) -> dict | None:
    path = results / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def _g0(g0: dict) -> list[str]:
    lines = ["## G0 データ", "", "| 型 | 月数 | 合成と ETF の相関 | 合格 |", "|---|---|---|---|"]
    for name, row in g0["etf"].items():
        lines.append(
            f"| {name} | {row['months']} | {row['corr']:.4f} | {'○' if row['pass'] else '×'} |"
        )
    return [*lines, ""]


def _dev(dev: dict) -> list[str]:
    lines = [
        f"## 開発期間（P1 = {dev['p1']}）",
        "",
        "| ルール | CER | シャープ | 切り替え |",
        "|---|---|---|---|",
    ]
    for name, row in dev["instruments"]["tlt"]["rules"].items():
        lines.append(f"| {name} | {_pct(row['cer'])} | {row['sharpe']:.2f} | {row['switches']} |")
    return [*lines, ""]


def _g1(g1: dict) -> list[str]:
    raw = g1.get("counts_raw", {}).get("W2", {})
    lines = [
        "## G1 合成データ（20回中、$H_A$ が有意になった回数）",
        "",
        "| 戦略 | W0（Holm 補正後） | W2（Holm 補正後） | W2（補正なし） |",
        "|---|---|---|---|",
    ]
    for name in g1["counts"]["W0"]:
        lines.append(
            f"| {name} | {g1['counts']['W0'][name]} | {g1['counts']['W2'][name]} "
            f"| {raw.get(name, '')} |"
        )
    lines += [
        "",
        f"合格（W0 だけで判定）：{'○' if g1['pass'] else '×'}。W2 の埋め込みの大きさ k = {g1['k']:.5f}。",
        "",
    ]
    if "power" in g1:
        lines += [
            "W2 の検出力（20回中、補正なし / Holm の上限 p×5 で有意になった回数、括弧は CER の差の平均）：",
            "",
            "| 埋め込みの倍率 | オラクル | 完全な特徴量の回帰 |",
            "|---|---|---|",
        ]
        for multiple, row in g1["power"].items():
            cells = [
                f"{row[name]['raw']} / {row[name]['holm_bound']}（{_pct(row[name]['mean_delta_cer'])}）"
                for name in ("oracle", "proxy")
            ]
            lines.append(f"| {multiple} | " + " | ".join(cells) + " |")
        lines.append("")
    return lines


def _oos_a(oos_a: dict) -> list[str]:
    tlt = oos_a["instruments"]["tlt"]
    names = {"P1": oos_a["p1"], "P2": "ols_p", "P3": "ols_pm", "P4": "nn_fm", "P5": "et"}
    hold = tlt["summary"]["hold"]
    lines = [
        "## 本番 A（判断 2000-01〜2018-12、TLT 型、費用 2bp）",
        "",
        "| 戦略 | CER | シャープ | 保有の割合 | L0 との差 | p（Holm） | P1 との差 | p（Holm） |",
        "|---|---|---|---|---|---|---|---|",
        f"| L0 ずっと保有 | {_pct(hold['cer'])} | {hold['sharpe']:.2f} | 100% | | | | |",
    ]
    for k, model in names.items():
        row, vs = tlt["summary"][model], tlt["tests"]["vs_hold"][k]
        p1 = tlt["tests"]["vs_p1"].get(k)
        tail = f"{_pct(p1['delta_cer'])} | {p1['p_holm']:.3f}" if p1 else " | "
        lines.append(
            f"| {LABELS[k]} | {_pct(row['cer'])} | {row['sharpe']:.2f} | {_pct(row['hold_share'])} "
            f"| {_pct(vs['delta_cer'])} | {vs['p_holm']:.3f} | {tail} |"
        )
    lines += [
        "",
        "| 戦略 | L0 との差（4bp） | L0 との差（5営業日遅れ） | P1 との差（4bp） | P1 との差（遅れ） |",
        "|---|---|---|---|---|",
    ]
    for k, row in tlt["robust"].items():
        lines.append(
            f"| {k} | {_pct(row['vs_hold_4bp'])} | {_pct(row['vs_hold_delay'])} "
            f"| {_pct(row['vs_p1_4bp'])} | {_pct(row['vs_p1_delay'])} |"
        )
    r2 = oos_a["r2_oos"]["rx12_10"]
    lines += [
        "",
        "R²oos（10年ゼロの rx12、過去平均に対して）："
        + "、".join(f"{m} {_pct(v)}" for m, v in r2.items()),
        "",
    ]
    return lines


def _r2_rows(title: str, tables: dict) -> list[str]:
    settings = [name for name in tables if name not in ("meta", "reading")]
    models = list(tables[settings[0]])
    lines = [
        title,
        "",
        "| 設定 | " + " | ".join(models) + " |",
        "|---" * (len(models) + 1) + "|",
    ]
    for name in settings:
        lines.append(
            f"| {name} | " + " | ".join(_pct(tables[name][m]["avg"]) for m in models) + " |"
        )
    return [*lines, ""]


def _decompose(decompose: dict) -> list[str]:
    return _r2_rows("## 見かけの予測力の分解（満期平均の R²oos）", decompose)


def _points(x: float) -> str:
    return f"{100 * x:.2f}ポイント"


def _decompose_monthly(monthly: dict) -> list[str]:
    r = monthly["reading"]
    return [
        *_r2_rows("## 毎月推定し直した分解（満期平均の R²oos、PREREG §5）", monthly),
        f"読み方（Liu–Wu の nn_fm）：V0m_liuwu は {_pct(r['v0m'])}（再現の基準は 20%）。"
        f"V0m_liuwu − V1m_liuwu は {_points(r['leak_gap'])}（基準は10ポイント）。"
        f"年1回の V0_liuwu（{_pct(r['v0_annual'])}）との差は {_points(r['dilution'])}。",
        "",
        f"判定：`{r['reading']}`",
        "",
    ]


def _g3(g3: dict) -> list[str]:
    return [
        "## G3（マクロが効かない世界との比較）",
        "",
        f"実データ：P4−P2 {_pct(g3['real']['P4'])}、P5−P2 {_pct(g3['real']['P5'])}。"
        f"p 値：P4 {g3['p']['P4']:.3f}、P5 {g3['p']['P5']:.3f}（{g3['worlds']}回）。",
        "",
    ]


def _oos_b(oos_b: dict) -> list[str]:
    lines = [
        f"## 本番 B（判断 {oos_b['window'][0]}〜{oos_b['window'][1]}、1回だけ）",
        "",
        "| 戦略 | L0 との CER 差 | P1 との CER 差 |",
        "|---|---|---|",
    ]
    for k, row in oos_b["diffs"].items():
        lines.append(f"| {k} | {_pct(row['vs_hold'])} | {_pct(row['vs_p1'])} |")
    return [*lines, "", f"判定：`{oos_b['verdict']}`", ""]


def render(results: Path) -> str:
    lines = ["# 結果の表（`bond-timing report` が生成）", ""]
    for name, section in (
        ("g0", _g0),
        ("dev", _dev),
        ("g1", _g1),
        ("oos_a", _oos_a),
        ("decompose", _decompose),
        ("g3", _g3),
        ("oos_b", _oos_b),
        ("decompose_monthly", _decompose_monthly),
    ):
        data = _load(results, name)
        if data:
            lines += section(data)
    return "\n".join(lines) + "\n"
