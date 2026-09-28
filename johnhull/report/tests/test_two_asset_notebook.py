"""The saved vol06 §27.7 lesson has six subsections and four shared figures."""

import json
import math
from pathlib import Path

import nbformat

NOTEBOOK = Path(__file__).resolve().parents[2] / "volumes/06_numerical_methods/numerical.ipynb"
METHODS = ("transform", "rubinstein", "adjusted")


def test_two_asset_saved_cells_and_figures():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    headings = [
        cell.source.splitlines()[0]
        for cell in notebook.cells
        if cell.cell_type == "markdown" and cell.source.startswith("## ")
    ]
    assert headings[6:15] == [
        "## 7. Black–Scholes–Merton 以外のモデル（§27.1）",
        "## 8. 確率ボラティリティ・モデル（§27.2）",
        "## 9. IVF（局所ボラティリティ）モデル（§27.3）",
        "## 10. 転換社債（§27.4）",
        "## 11. 経路依存デリバティブ（§27.5）",
        "## 12. バリア・オプションのツリー評価（§27.6）",
        "## 13. 相関のある二資産のオプション（§27.7）",
        "## 14. Longstaff-Schwartz（LSM）— MC でアメリカン（Ch.27）",
        "## 15. 練習問題",
    ]
    text = "\n".join(cell.source for cell in notebook.cells)
    for number in range(1, 7):
        assert f"### 13.{number} " in text
    keys = []
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            assert output.output_type != "error"
            payload = output.get("data", {}).get("application/vnd.plotly.v1+json")
            if payload and payload["layout"].get("meta", {}).get("section") == "27.7":
                keys.append(payload["layout"]["meta"]["figure"])
    assert keys == [
        "two_asset_nodes",
        "two_asset_convergence",
        "two_asset_errors",
        "two_asset_correlation",
    ]


def _section_text(notebook):
    cells = notebook.cells
    start = next(i for i, c in enumerate(cells) if c.source.startswith("## 13. "))
    end = next(i for i, c in enumerate(cells) if c.source.startswith("## 14. "))
    return "\n".join(c.source for c in cells[start:end] if c.cell_type == "markdown")


def test_two_asset_prose_numbers_follow_the_saved_reference():
    root = Path(__file__).resolve().parents[2] / "docs/validation/section-27-7"
    data = json.loads((root / "reference.json").read_text(encoding="utf-8"))
    measured = json.loads((root / "numerical-check.json").read_text(encoding="utf-8"))["measured"]
    text = _section_text(nbformat.read(NOTEBOOK, as_version=4))
    p = data["parameters"]
    american = data["analytic"]["american_exchange"]
    errors = data["errors"]
    parity = data["parity"]
    sweep = parity["transform"]
    rows = dict(zip(parity["rho"], sweep, strict=True))
    gaps = measured["max_gap_100_vs_101_steps"]
    dt = 0.01
    s1, s2 = p["volatilities"]
    m1 = p["rate"] - p["dividend_yields"][0] - s1**2 / 2
    m2 = p["rate"] - p["dividend_yields"][1] - s2**2 / 2
    h = []
    for sign in (1, -1):
        m = (s2 * m1 + sign * s1 * m2) * dt
        h.append(math.sqrt((s1 * s2) ** 2 * 2 * (1 + sign * p["correlation"]) * dt + m * m))
    raw = measured["american_max_call_800_steps"]["raw"]
    control = measured["american_max_call_800_steps"]["control_variate"]
    step200 = {m: data["convergence"]["american"][m][-1] - american["value"] for m in METHODS}
    claims = {
        f"{data['analytic']['max_call']['stulz']:.4f}ドル": True,
        f"{data['analytic']['exchange']:.4f}ドル": True,
        f"{american['value']:.4f}ドル": True,
        f"$h_1={h[0]:.5f}$、$h_2={h[1]:.5f}$": True,
        f"{measured['early_exercise_premium']:.3f}ドル": True,
        "$10^{-14}$ドル未満で一致": abs(data["analytic"]["max_call"]["difference"]) < 1e-14,
        "差は $1.4\\times10^{-5}$ドル": round(
            abs(american["crr_extrapolated"] - american["cn_extrapolated"]), 6
        )
        == 1.4e-5,
        f"変数変換 {step200['transform']:+.4f}ドル": True,
        f"Rubinstein {step200['rubinstein']:+.4f}ドル": True,
        f"確率調整 {step200['adjusted']:+.4f}ドル".replace("-", "−"): True,
        f"傾き{measured['transform_max_call_order']:.2f}": True,
        "200段で $-2\\times10^{-4}$ドル": f"{errors['rubinstein_max_call'][3]:.0e}" == "-2e-04",
        "400段で $3.4\\times10^{-3}$ドル": f"{errors['rubinstein_max_call'][4]:.1e}" == "3.4e-03",
        "0.0012ドル未満": max(measured["final_errors_800_steps"].values()) < 0.0012,
        "差は0.0022ドル以下": round(gaps["adjusted"], 4) == 0.0022,
        "最大0.013ドル違う": round(gaps["rubinstein"], 3) == 0.013,
        "0.002ドルは100段だけ": {round(rows[r][1], 3) for r in (-0.6, 0.6)} == {0.002},
        "99段・101段では0.012–0.014ドル": all(
            0.0115 <= rows[r][i] < 0.0145 for r in (-0.6, 0.6) for i in (0, 2)
        ),
        "99・100・101段とも−0.009ドル": {round(v, 3) for v in rows[0.0]} == {-0.009},
        "100段で+0.045ドル": round(rows[-1.0][1], 3) == 0.045,
        "−0.049・−0.048ドル": [round(rows[-1.0][i], 3) for i in (0, 2)] == [-0.049, -0.048],
        f"{max(raw) - min(raw):.4f}ドルの幅": True,
        f"{min(control):.4f}–{max(control):.4f}ドルの{max(control) - min(control):.4f}ドルの幅": True,
    }
    for phrase, holds in claims.items():
        assert phrase in text, phrase
        assert holds, phrase
