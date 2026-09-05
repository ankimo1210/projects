"""Update the previously requested static runtime chart from final audited data.

Contract: four models, one observed run each, main+resume turn wall time in
minutes, sorted horizontal bars starting at zero. Compare work rather than
idle gaps; disclose Opus's idle gap separately. Reuse prior PNG/SVG surface
and model palette (blue/gold/orange/pink), with direct labels, no legend.
"""
import csv
import math
from pathlib import Path
import unicodedata

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
COLORS = {"astra": "#1769aa", "sol": "#b77912", "opus": "#cc5a18", "fable": "#a84378"}


def main():
    with (HERE / "matched/runtime_tokens.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4 and {r["model"] for r in rows} == set(COLORS)
    for row in rows:
        row["minutes"] = float(row["work_minutes"])
        assert math.isfinite(row["minutes"]) and row["minutes"] > 0
    rows.sort(key=lambda r: r["minutes"])
    opus = next(r for r in rows if r["model"] == "opus")
    font = next(p for p in Path("/System/Library/Fonts").glob("*.ttc")
                if unicodedata.normalize("NFC", p.name) == "ヒラギノ角ゴシック W3.ttc")
    font_manager.fontManager.addfont(str(font))
    plt.rcParams.update({"font.family": font_manager.FontProperties(fname=str(font)).get_name(),
                         "font.size": 12, "text.color": "#252b33", "axes.labelcolor": "#252b33",
                         "xtick.color": "#58616c", "ytick.color": "#252b33", "svg.fonttype": "path"})
    fig, ax = plt.subplots(figsize=(10, 6), dpi=180)
    fig.subplots_adjust(left=0.13, right=0.96, top=0.76, bottom=0.30)
    fig.text(0.06, 0.93, "モデル別の実行時間（最終確認）", fontsize=21, weight="bold")
    fig.text(0.06, 0.865, "2026年9月5日 ｜ 各モデル1回 ｜ 本実行＋再開ターン、ツール待ち込み",
             fontsize=11, color="#58616c")
    bars = ax.barh([r["model"].title() for r in rows], [r["minutes"] for r in rows],
                   color=[COLORS[r["model"]] for r in rows], height=0.56,
                   edgecolor="#343b45", linewidth=0.5, zorder=3)
    ax.invert_yaxis()
    ax.set_xlim(0, 145)
    ax.set_xticks(range(0, 141, 20))
    ax.set_xlabel("作業ターンの実時間合計（分）", labelpad=12)
    ax.grid(axis="x", color="#e4e7eb", linewidth=0.7, zorder=0)
    ax.tick_params(axis="y", length=0, pad=10, labelsize=13)
    ax.tick_params(axis="x", length=0, pad=8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#c6ccd3")
    for bar, row in zip(bars, rows):
        ax.text(row["minutes"]+2.0, bar.get_y()+bar.get_height()/2,
                f'{row["minutes"]:.1f} 分', va="center", fontsize=13, weight="bold")
    note = (f'Opus：再開待ち {float(opus["between_work_turn_idle_minutes"]):.1f} 分は棒に含めず。'
            f'開始〜最終終了は {float(opus["work_span_minutes"]):.1f} 分。')
    fig.text(0.06, 0.16, note, fontsize=10, color="#58616c")
    fig.text(0.06, 0.114, "設定確認・出力先対応・終了後の表示依頼は除外。純粋な推論時間ではありません。",
             fontsize=10, color="#58616c")
    fig.text(0.06, 0.065, "出典：final-review-20260905/matched/runtime_tokens.csv（work_minutes）",
             fontsize=9, color="#737c87")
    destination = ROOT / "evaluations"
    destination.mkdir(exist_ok=True)
    for ext in ("png", "svg"):
        path = destination / f"execution_time_final.{ext}"
        fig.savefig(path, facecolor="white")
        print(path)
    plt.close(fig)


if __name__ == "__main__":
    main()
