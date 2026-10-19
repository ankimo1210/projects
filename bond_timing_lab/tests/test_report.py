import json

from bond_timing.report import render


def test_render_skips_missing_stages_and_shows_the_verdict(tmp_path):
    assert render(tmp_path).startswith("# 結果の表")
    (tmp_path / "g0.json").write_text(
        json.dumps({"etf": {"tlt": {"months": 290, "corr": 0.97, "pass": True}}, "pass": True})
    )
    (tmp_path / "oos_b.json").write_text(
        json.dumps(
            {
                "window": ["2019-01", "2026-08"],
                "verdict": "no_usable_signal",
                "diffs": {"P1": {"vs_hold": -0.01, "vs_p1": 0.0}},
            }
        )
    )
    text = render(tmp_path)
    assert "## G0" in text and "0.9700" in text
    assert "no_usable_signal" in text and "-1.00%" in text


def test_render_shows_the_g1_counts_and_power_table(tmp_path):
    oracle = {"raw": 12, "holm_bound": 2, "mean_delta_cer": 0.061}
    proxy = {"raw": 0, "holm_bound": 0, "mean_delta_cer": 0.021}
    g1 = {
        "counts": {"W0": {"P1": 0}, "W2": {"P1": 3}},
        "counts_raw": {"W0": {"P1": 1}, "W2": {"P1": 9}},
        "pass": True,
        "k": 0.00674,
        "power": {"1": {"oracle": oracle, "proxy": proxy}},
    }
    (tmp_path / "g1.json").write_text(json.dumps(g1))
    text = render(tmp_path)
    assert "| P1 | 0 | 3 | 9 |" in text
    assert "| 1 | 12 / 2（6.10%） | 0 / 0（2.10%） |" in text


def test_render_shows_the_monthly_decomposition_and_its_reading(tmp_path):
    table = {"ols_p": {"avg": -0.3}, "nn_fm": {"avg": 0.25}}
    payload = {name: table for name in ("V0m_liuwu", "V0m_gsw", "V1m_liuwu", "V1m_gsw")}
    payload["reading"] = {
        "v0m": 0.25,
        "v1m": 0.05,
        "v0_annual": -0.14,
        "reproduces": True,
        "leak_gap": 0.2,
        "leak_large": True,
        "dilution": 0.39,
        "dilution_large": True,
        "reading": "leak_explains_paper",
    }
    payload["meta"] = {"git_commit": "x"}
    (tmp_path / "decompose_monthly.json").write_text(json.dumps(payload))
    text = render(tmp_path)
    assert "## 毎月推定し直した分解" in text
    assert "| V1m_gsw | -30.00% | 25.00% |" in text
    assert "20.00ポイント" in text and "39.00ポイント" in text
    assert "`leak_explains_paper`" in text
