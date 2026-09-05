"""Render audited primary-turn runtimes from session_summary.csv.

Chart contract: compare four observed model runtimes, one primary run each on
2026-09-05, using sorted horizontal bars with a zero baseline. Static PNG/SVG
fallback because the inline widget rejected CSV provenance without SQL.
Keep model identity consistent with the token plot: blue/gold/orange/pink,
plus direct category/value labels (no redundant legend). Inspect the PNG.
"""

import csv
import math
from pathlib import Path
import unicodedata

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


ROOT = Path(__file__).resolve().parent
COLORS = {
    "astra": "#1769aa", "sol": "#b77912",
    "opus": "#cc5a18", "fable": "#a84378",
}


def main():
    with (ROOT / "session_summary.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4 and {r["model"] for r in rows} == set(COLORS)
    for row in rows:
        row["minutes"] = float(row["primary_elapsed_minutes"])
        assert math.isfinite(row["minutes"]) and row["minutes"] > 0
    rows.sort(key=lambda r: r["minutes"])

    # Normalize macOS decomposed filenames when selecting the Japanese font.
    fonts = [p for p in Path("/System/Library/Fonts").glob("*.ttc")
             if unicodedata.normalize("NFC", p.name) == "ヒラギノ角ゴシック W3.ttc"]
    if not fonts:
        raise RuntimeError("Japanese font not found; select a local Japanese font.")
    font_manager.fontManager.addfont(str(fonts[0]))
    font = font_manager.FontProperties(fname=str(fonts[0])).get_name()
    plt.rcParams.update({"font.family": font, "font.size": 12,
                         "text.color": "#252b33", "axes.labelcolor": "#252b33",
                         "xtick.color": "#58616c", "ytick.color": "#252b33",
                         "svg.fonttype": "path", "axes.unicode_minus": False})

    fig, ax = plt.subplots(figsize=(10, 5.7), dpi=180)
    fig.subplots_adjust(left=0.13, right=0.96, top=0.76, bottom=0.28)
    fig.text(0.06, 0.93, "モデル別の本実行時間", fontsize=21, weight="bold")
    fig.text(0.06, 0.862, "2026年9月5日 ｜ 各モデル1回の実測 ｜ ツール待ち・自動要約を含む",
             fontsize=11, color="#58616c")

    bars = ax.barh([r["model"].title() for r in rows], [r["minutes"] for r in rows],
                   color=[COLORS[r["model"]] for r in rows], height=0.56,
                   edgecolor="#343b45", linewidth=0.5, zorder=3)
    ax.invert_yaxis()
    ax.set_xlim(0, 80)
    ax.set_xticks(range(0, 81, 10))
    ax.set_xlabel("本実行時間（分）", labelpad=12)
    ax.grid(axis="x", color="#e4e7eb", linewidth=0.7, zorder=0)
    ax.tick_params(axis="y", length=0, pad=10, labelsize=13)
    ax.tick_params(axis="x", length=0, pad=8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#c6ccd3")
    for bar, row in zip(bars, rows):
        ax.text(row["minutes"] + 1.3, bar.get_y() + bar.get_height() / 2,
                f'{row["minutes"]:.1f} 分', va="center", fontsize=13, weight="bold")

    fig.text(0.06, 0.13, "対象：本実行ターンのみ。設定確認・終了後のやり取りは除外。",
             fontsize=10, color="#58616c")
    fig.text(0.06, 0.09, "Solの終了後の出力先修正は含みません。純粋な推論時間や品質の比較ではありません。",
             fontsize=10, color="#58616c")
    fig.text(0.06, 0.044, "出典：session_summary.csv ／ primary_elapsed_minutes", fontsize=9,
             color="#737c87")
    for ext in ("png", "svg"):
        path = ROOT / f"execution_time.{ext}"
        fig.savefig(path, facecolor="white")
        print(path)
    plt.close(fig)
    print("Validated: 4 unique models; finite positive times; zero baseline.")
    for row in rows:
        print(f'{row["model"]}: {row["minutes"]:.1f} min')


if __name__ == "__main__":
    main()
