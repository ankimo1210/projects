"""The saved vol10 §26.1 lesson: six subsections, four shared figures and prose tied to data."""

import json
import math
from itertools import pairwise
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]
NOTEBOOK = PROJECT / "volumes/10_exotics_martingales/exotics.ipynb"
PLOTLY = "application/vnd.plotly.v1+json"


def _lesson(notebook):
    cells = notebook.cells
    start = next(i for i, c in enumerate(cells) if c.source.startswith("### 4.8 "))
    end = next(i for i, c in enumerate(cells) if c.source.startswith("### 4.9 "))
    return cells[start:end]


def test_packages_saved_cells_and_figures():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    headings = [
        cell.source.splitlines()[0]
        for cell in notebook.cells
        if cell.cell_type == "markdown" and cell.source.startswith("### 4.")
    ]
    expected = [
        "### 4.7 静的オプション複製（§26.17）",
        "### 4.8 パッケージ（§26.1、GE pp.614–615）",
    ]
    start = headings.index(expected[0])
    assert headings[start : start + 2] == expected
    lesson = _lesson(notebook)
    numbers = [
        line.split(" ", 2)[1]
        for cell in lesson
        if cell.cell_type == "markdown"
        for line in cell.source.splitlines()
        if line.startswith("#### 4.8.")
    ]
    assert numbers == [f"4.8.{n}" for n in range(1, 7)]
    keys = []
    for cell in lesson:
        for output in cell.get("outputs", ()):
            assert output.output_type != "error"
            payload = output.get("data", {}).get(PLOTLY)
            if payload and payload["layout"].get("meta", {}).get("section") == "26.1":
                keys.append(payload["layout"]["meta"]["figure"])
    assert keys == [
        "packages_range_forward",
        "packages_strikes",
        "packages_deferred",
        "packages_risk",
    ]


def test_packages_prose_numbers_follow_the_saved_reference():
    root = PROJECT / "docs/validation/section-26-1"
    data = json.loads((root / "reference.json").read_text(encoding="utf-8"))
    record = json.loads((root / "numerical-check.json").read_text(encoding="utf-8"))
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    text = "\n".join(c.source for c in _lesson(notebook) if c.cell_type == "markdown")
    anchor, risk, pay = data["anchor_17_2"], data["risk_comparison"], data["figure_payoffs"]
    market = data["parameters"]
    forward = data["strike_curve"]["forward"]
    curve = data["strike_curve"]["points"]
    z_scores = record["measured"]["risk"]["monte_carlo"]
    loss_pv = {name: row["loss_pv_quadrature"] for name, row in risk.items()}
    loss_probability = {name: row["probability_of_loss"] for name, row in risk.items()}
    claims = {
        "$S_0=1.32$、$r=r_f=2\\%$、\n$\\sigma=14\\%$、$T=0.25$ 年、なので $F=1.32$": (
            market["spot"],
            market["rate"],
            market["yield"],
            market["sigma"],
            market["maturity"],
            forward,
        )
        == (1.32, 0.02, 0.02, 0.14, 0.25, 1.32),
        "原典は $K_1=1.3000$ に対して $K_2=1.3414$": anchor["put_strike"] == 1.3
        and round(anchor["call_strike"], 4) == anchor["printed"]["call_strike"] == 1.3414,
        "$p(1.30)=0.0273$": round(anchor["premium"], 4) == anchor["printed"]["premium"] == 0.0273
        and anchor["put_at_printed_strikes"] == anchor["premium"],
        f"保存参照の{len(curve)}点で確認": len(curve) == 70
        and all(a["call_strike"] > b["call_strike"] for a, b in pairwise(curve)),
        f"$K_1=0.3F$ で $K_2$ は ${curve[0]['call_strike'] / forward:.2f}F$": math.isclose(
            curve[0]["put_strike"], 0.3 * forward
        ),
        f"先渡しが最大（{loss_pv['forward']:.4f}）": loss_pv["forward"] == max(loss_pv.values()),
        f"レンジ先渡しが最小（{loss_pv['range_forward']:.4f}）": loss_pv["range_forward"]
        == min(loss_pv.values()),
        f"ブレークフォワードは{loss_pv['break_forward']:.4f}。": loss_pv["range_forward"]
        < loss_pv["break_forward"]
        < loss_pv["forward"],
        f"先渡し{loss_probability['forward']:.1%}、"
        f"レンジ先渡し{loss_probability['range_forward']:.1%}、"
        f"ブレークフォワード{loss_probability['break_forward']:.1%}": loss_probability[
            "break_forward"
        ]
        == max(loss_probability.values())
        and loss_probability["range_forward"] == min(loss_probability.values()),
        f"先渡し{risk['forward']['max_loss']:.2f}（$S_T\\to0$）": risk["forward"]["max_loss"]
        == forward,
        f"レンジ先渡し{risk['range_forward']['max_loss']:.3f}（$K_1$）": math.isclose(
            risk["range_forward"]["max_loss"], 0.95 * forward
        )
        and risk["range_forward"]["max_loss"] == risk["range_forward"]["strikes"]["put"],
        f"ブレークフォワード{risk['break_forward']['max_loss']:.4f}（$A$）": risk["break_forward"][
            "max_loss"
        ]
        == pay["amount"],
        "$2^{19}$ 組": data["monte_carlo"]["antithetic_pairs"] == 2**19,
        "4標準誤差以内で一致": all(abs(z) < 4 for row in z_scores.values() for z in row.values()),
    }
    for phrase, holds in claims.items():
        assert phrase in text, phrase
        assert holds, phrase
    assert "$K_1=0.95F$" in text
    assert "満期に原資産を買う側（ロング）" in text
    assert "hullkit の関数には含まれません" in text


def test_packages_zero_cost_root_argument_has_the_right_direction():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    text = "\n".join(c.source for c in _lesson(notebook) if c.cell_type == "markdown")
    assert "$c(K_2)=p(K_1)<p(F)=c(F)$" in text
    assert "$c(K_2)=p(K_1)>p(F)=c(F)$" not in text
