"""The saved vol06 §27.8 lesson: six subsections, four shared figures and prose tied to data."""

import json
import math
from pathlib import Path

import nbformat

PROJECT = Path(__file__).resolve().parents[2]
NOTEBOOK = PROJECT / "volumes/06_numerical_methods/numerical.ipynb"
KEYS = ("lsm2", "lsm3", "boundary")


def test_american_mc_saved_cells_and_figures():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    headings = [
        cell.source.splitlines()[0]
        for cell in notebook.cells
        if cell.cell_type == "markdown" and cell.source.startswith("## ")
    ]
    assert headings[6:16] == [
        "## 7. Black–Scholes–Merton 以外のモデル（§27.1）",
        "## 8. 確率ボラティリティ・モデル（§27.2）",
        "## 9. IVF（局所ボラティリティ）モデル（§27.3）",
        "## 10. 転換社債（§27.4）",
        "## 11. 経路依存デリバティブ（§27.5）",
        "## 12. バリア・オプションのツリー評価（§27.6）",
        "## 13. 相関のある二資産のオプション（§27.7）",
        "## 14. モンテカルロ法とアメリカン・オプション（§27.8）",
        "## 15. 三つの数値解法の比較（CRR・FD・LSM）",
        "## 16. 練習問題",
    ]
    text = "\n".join(cell.source for cell in notebook.cells)
    for number in range(1, 7):
        assert f"### 14.{number} " in text
    keys = []
    for cell in notebook.cells:
        for output in cell.get("outputs", ()):
            assert output.output_type != "error"
            payload = output.get("data", {}).get("application/vnd.plotly.v1+json")
            if payload and payload["layout"].get("meta", {}).get("section") == "27.8":
                keys.append(payload["layout"]["meta"]["figure"])
    assert keys == [
        "american_mc_regression",
        "american_mc_boundary",
        "american_mc_bias",
        "american_mc_dates",
    ]


def _section_text(notebook):
    cells = notebook.cells
    start = next(i for i, c in enumerate(cells) if c.source.startswith("## 14. "))
    end = next(i for i, c in enumerate(cells) if c.source.startswith("## 15. "))
    return "\n".join(c.source for c in cells[start:end] if c.cell_type == "markdown")


def _printed(values, printed):
    """Each value rounds to Hull's four-decimal figure (within half a unit)."""
    return all(
        abs(v - float(p)) <= 5e-5 + 1e-12 for v, p in zip(values, printed.split("・"), strict=True)
    )


def _signed(value, digits):
    return f"{value:+.{digits}f}".replace("-", "−")


def test_american_mc_prose_numbers_follow_the_saved_reference():
    root = PROJECT / "docs/validation"
    data = json.loads((root / "section-27-8/reference.json").read_text(encoding="utf-8"))
    record = json.loads((root / "section-27-8/numerical-check.json").read_text(encoding="utf-8"))
    measured = record["measured"]
    two_asset = json.loads((root / "section-27-7/reference.json").read_text(encoding="utf-8"))
    text = _section_text(nbformat.read(NOTEBOOK, as_version=4))
    hand = data["hand_example"]
    lsm, boundary = hand["least_squares"], hand["boundary"]
    late, early = lsm["steps"]["2"]["coefficients"], lsm["steps"]["1"]["coefficients"]
    bias, dates, exchange = data["bias"], data["dates"], data["exchange"]
    exact3 = data["exact"]["bermudan"][0]
    errors = [e for key in KEYS for e in dates[key]["standard_error"]]
    american_exchange = two_asset["analytic"]["american_exchange"]["value"]
    problem = hand["problem_27_22"]
    out = exchange["out_of_sample"]
    claims_run = measured["claims"]
    paired = dates["paired"]["lsm3_minus_lsm2"]
    at = {n: i for i, n in enumerate(dates["counts"])}
    european = dates["european"]
    european_z = (european["mean"][at[24]] - european["value"]) / european["standard_error"][at[24]]
    exchange_z = (out["value"] - exchange["exact"]) / out["standard_error"]
    late_averages = "0.0636・0.0813・0.1032・0.0982・0.0938・0.0963"
    early_averages = "0.0972・0.1008・0.1283・0.1202・0.1215・0.1228"
    exact_values = "・".join(f"{row['value']:.4f}" for row in data["exact"]["bermudan"])
    claims = {
        f"$a={late[0]:.6f}$、$b={late[1]:.6f}$、$c={late[2]:.6f}$": True,
        f"$V={early[0]:.6f}{early[1]:.6f}S+{early[2]:.6f}S^2$": True,
        "キャッシュフローを時点0へ割り引いた平均は0.1144": round(lsm["value"], 4) == 0.1144,
        "最大 $5.4\\times10^{-4}$ 違い": round(
            measured["printed_rounding"]["continuation_exact"], 5
        )
        == 0.00054,
        f"1年目の経路1は{lsm['steps']['1']['continuation'][0]:.4f}": True,
        "2年目の $c$ は丸めれば −1.814 だが、印刷は −1.813": round(late[2], 3) == -1.814
        and hand["printed"]["coefficients"]["2"][2] == -1.813
        and measured["printed_rounding"]["coefficients_off_half_unit"] == ["2:c"],
        "10個とも $6\\times10^{-5}$ 以内": measured["printed_rounding"]["continuation_rounded"]
        < 6e-5,
        late_averages: _printed(boundary["steps"]["2"]["averages"], late_averages),
        early_averages: _printed(boundary["steps"]["1"]["averages"], early_averages),
        f"丸めない平均{boundary['value_at_1']:.6f}からは{boundary['value']:.5f}": True,
        f"厳密値は{exact3['value']:.6f}": exact3["dates"] == 3,
        "刻みを半分にしても変化は $10^{-8}$ 未満": exact3["quadrature_change"] < 1e-8,
        "Crank–Nicolson とは $4\\times10^{-7}$ 以内で一致": exact3["crank_nicolson_gap"] < 4e-7,
        f"推定と評価を{bias['replications']}回": True,
        "評価は毎回新しい1万本": bias["evaluation_paths"] == 10_000,
        "7つの経路数すべて": len(bias["sizes"]) == 7
        and claims_run["boundary_in_sample_above_exact"],
        "差はどれも標準誤差の2倍を超えた": claims_run["boundary_in_sample_above_exact"],
        f"250本で {_signed(bias['boundary_in']['mean'][0] - bias['exact'], 4)}": True,
        f"16000本でも {_signed(bias['boundary_in']['mean'][-1] - bias['exact'], 5)}": bias["sizes"][
            -1
        ]
        == 16000,
        f"250本で {_signed(bias['boundary_out']['mean'][0] - bias['exact'], 4)}、"
        f"1000本で {_signed(bias['boundary_out']['mean'][2] - bias['exact'], 4)}": bias["sizes"][2]
        == 1000,
        f"250本で {_signed(bias['lsm_out']['mean'][0] - bias['exact'], 4)} と低い": True,
        "どの経路数でも厳密値との差が標準誤差の2倍以内": measured["claims"][
            "lsm_in_sample_within_two_errors"
        ],
        exact_values: [row["dates"] for row in data["exact"]["bermudan"]] == [3, 6, 12, 24, 48],
        f"連続行使の値{data['exact']['american']['value']:.4f}": True,
        "5万本で推定し新しい20万本で評価": (dates["fit_paths"], dates["evaluation_paths"])
        == (50_000, 200_000),
        f"標準誤差（{min(errors):.5f}–{max(errors):.5f}）の2倍以内": measured["claims"][
            "dates_within_two_errors"
        ],
        f"{out['value']:.3f}±{out['standard_error']:.3f}": True,
        f"厳密値{exchange['exact']:.4f}": True,
        f"差は標準誤差の{abs(exchange_z):.1f}倍": claims_run["exchange_within_two_errors"],
        "12回までは標準誤差の2倍に届かない": claims_run[
            "cubic_and_quadratic_within_two_errors_to_12_dates"
        ],
        f"24回で {_signed(paired['mean'][at[24]], 5)}（差の標準誤差{paired['standard_error'][at[24]]:.5f}）、"
        f"48回で {_signed(paired['mean'][at[48]], 5)}（同{paired['standard_error'][at[48]]:.5f}）": claims_run[
            "cubic_above_quadratic_at_24_and_48_dates"
        ],
        "24回で三つとも厳密値を上回った": claims_run["all_three_above_exact_at_24_dates"],
        f"標準誤差の{european_z:.1f}倍高い": claims_run["european_check_high_only_at_24_dates"],
        f"連続行使の{american_exchange:.4f}（§13.5）との差"
        f"{american_exchange - exchange['exact']:.3f}": True,
        f"最小二乗法{problem['least_squares']['value']:.4f}、境界{problem['boundary']['value']:.4f}": True,
        "$S^*(1)=1.11$、$S^*(2)=0.84$": [
            problem["boundary"]["steps"][t]["threshold"] for t in ("1", "2")
        ]
        == [1.11, 0.84],
    }
    for phrase, holds in claims.items():
        assert phrase in text, phrase
        assert holds, phrase
    assert math.isclose(round(0.1283 * math.exp(-0.06), 4), 0.1208)


def test_section_15_introduction_follows_the_saved_bermudan_floor():
    root = PROJECT / "docs/validation"
    data = json.loads((root / "section-27-8/reference.json").read_text(encoding="utf-8"))
    floor = data["section_15"]
    bermudan, american = floor["bermudan"]["value"], floor["american"]["value"]
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    text = next(c.source for c in notebook.cells if c.source.startswith("## 15. "))
    assert floor["bermudan"]["dates"] == 50 and "行使できるのは50回" in text
    assert "n_steps=50" in "\n".join(
        c.source for c in notebook.cells if "price_american_lsm" in c.source
    )
    phrase = (
        f"その厳密値（バミューダン）{bermudan:.4f}でも\n"
        f"連続行使の{american:.4f}より{american - bermudan:.4f}低い"
    )
    assert phrase in text
