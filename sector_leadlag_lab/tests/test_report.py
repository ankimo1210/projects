import json

import pytest
from sector_leadlag import cli
from sector_leadlag.diagnostics import run_diagnostics
from sector_leadlag.g0 import run_g0
from sector_leadlag.g1 import run_g1
from sector_leadlag.main import run_main_a, run_main_b
from sector_leadlag.report import render, render_corrected


@pytest.fixture(scope="module")
def results(decayed_world, tmp_path_factory):
    """Every stage on the decayed world, written and read back as the CLI does."""
    root = tmp_path_factory.mktemp("results")

    def stage(name: str, result: dict) -> dict:
        cli.write_result(name, result, root, {"git_commit": "abc"})
        return json.loads((root / f"{name}.json").read_text(encoding="utf-8"))

    g0 = stage("g0", run_g0(decayed_world, {}))
    stage("g1", run_g1(decayed_world, {"g0": g0}, count=2))
    a = stage("main_a", run_main_a(decayed_world, {"g0": g0}, n_boot=200))
    b = stage("main_b", run_main_b(decayed_world, {"g0": g0, "main_a": a}))
    stage("diagnostics", run_diagnostics(decayed_world, {"g0": g0, "main_a": a, "main_b": b}))
    return root


def test_the_summary_has_every_section(results):
    text = render(results)
    for heading in ("## G0 再現", "## G1 合成データ", "## 本番 A", "## 本番 B", "## 診断"):
        assert heading in text
    assert "**判定：`usable`**" in text
    assert "| 公開値 | 23.79% |" in text
    assert "nan" not in text.lower()


def test_the_summary_skips_stages_that_have_not_run(tmp_path, results):
    (tmp_path / "g0.json").write_text((results / "g0.json").read_text(encoding="utf-8"))
    text = render(tmp_path)
    assert "## G0 再現" in text and "## 本番 A" not in text


def test_the_corrected_summary_puts_the_record_beside_it(results):
    text = render_corrected(results, results)
    assert "**`verdict_robust`**：直したデータの判定も `usable`。" in text
    assert "| 判定 | `usable` | `usable` |" in text
    assert "## 記録と並べた表" in text and "### G0 再現" in text
    assert "nan" not in text.lower()


def test_a_corrected_run_that_stopped_at_g0_depends_on_the_data(tmp_path, results):
    g0 = json.loads((results / "g0.json").read_text(encoding="utf-8"))
    cli.write_result("g0", {**g0, "pass": False, "selected": None}, tmp_path, {})
    cli.write_result(
        "corrections",
        {"counts": {"C1": {"etf": 3}}, "missing_known": [], "changes": []},
        tmp_path,
        {},
    )
    text = render_corrected(results, tmp_path)
    assert "**`verdict_data_dependent`**：直したデータでは G0 で止まった" in text
    assert f"並べ方が {g0['selected']} から なし に変わった" in text
    assert (
        "| C1 桁の跳び | 3 | 0 | 0 |" in text and "既知の誤り（設計書 §2）：すべて直った。" in text
    )
    assert "| 判定 | `usable` | — |" in text and "nan" not in text.lower()


def test_a_changed_verdict_names_the_conditions_that_changed(tmp_path, results):
    for name in ("g0", "g1", "main_a", "diagnostics"):
        (tmp_path / f"{name}.json").write_text((results / f"{name}.json").read_text("utf-8"))
    b = json.loads((results / "main_b.json").read_text(encoding="utf-8"))
    evidence = {**b["evidence"], "b_mean_cash": -0.001}
    cli.write_result(
        "main_b", {**b, "verdict": "real_not_usable", "evidence": evidence}, tmp_path, {}
    )
    text = render_corrected(results, tmp_path)
    assert "**`verdict_data_dependent`**：直したデータの判定は `real_not_usable`" in text
    assert "直したデータの判定は `real_not_usable`（記録は `usable`）。" in text
    assert "変わった条件：④（本番 B で1と2がどちらも正）。" in text


def test_a_corrected_run_that_stopped_at_g1_depends_on_the_data(tmp_path, results):
    (tmp_path / "g0.json").write_text((results / "g0.json").read_text("utf-8"))
    g1 = json.loads((results / "g1.json").read_text(encoding="utf-8"))
    cli.write_result("g1", {**g1, "pass": False}, tmp_path, {})
    text = render_corrected(results, tmp_path)
    assert "**`verdict_data_dependent`**：直したデータでは G1 が不合格で止まった。" in text


def test_the_decomposition_shows_the_record_before_the_corrected_value(tmp_path, results):
    d = json.loads((results / "diagnostics.json").read_text(encoding="utf-8"))
    kept = d["decomposition"]["etf"]["c2o"]["a"]
    d["decomposition"]["etf"]["c2o"]["a"] = 0.1234
    cli.write_result("diagnostics", d, tmp_path, {})
    text = render_corrected(results, tmp_path)
    assert f"| ETF | C2O | {100 * kept:.2f}%／12.34% |" in text


def test_the_records_summary_renders_as_committed():
    committed = (cli.RESULTS / "summary.md").read_text(encoding="utf-8")
    assert render(cli.RESULTS) == committed


def test_the_corrected_summary_renders_as_committed():
    committed = (cli.CORRECTED / "summary.md").read_text(encoding="utf-8")
    assert render_corrected(cli.RESULTS, cli.CORRECTED) == committed
