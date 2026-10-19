import json

import pytest
from sector_leadlag import cli
from sector_leadlag.diagnostics import run_diagnostics
from sector_leadlag.g0 import run_g0
from sector_leadlag.g1 import run_g1
from sector_leadlag.main import run_main_a, run_main_b
from sector_leadlag.report import render


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
