import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research/2026-10-jgb-term-premium"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"tp_{name}", RESEARCH / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gates():
    return _load("gates")


def _report(**overrides):
    report = {
        "g1": {m: {"pass": True} for m in ("acm", "acm_bc", "dns", "shadow")},
        "g2": {"pass": True},
        "g3": {"pass": True},
        "g4": {"pass": True},
    }
    report.update(overrides)
    return report


def test_all_gates_pass_all_models(gates):
    assert gates.passed_models(_report()) == ["acm", "acm_bc", "shadow", "dns"]


def test_g2_failure_removes_both_acm_variants(gates):
    assert gates.passed_models(_report(g2={"pass": False})) == ["shadow", "dns"]


def test_g3_failure_removes_the_shadow_model(gates):
    assert gates.passed_models(_report(g3={"pass": False})) == ["acm", "acm_bc", "dns"]


def test_a_data_failure_stops_everything(gates):
    assert gates.passed_models(_report(g4={"pass": False})) == []


def test_g1_summary_uses_the_mean_error_and_the_median_rmse(gates):
    draws = [
        {"share_error": e, "tp_rmse": r} for e, r in ((0.08, 0.05), (-0.06, 0.12), (0.02, 0.30))
    ]
    out = gates._summary(draws)
    assert out["mean_share_error"] == pytest.approx(0.04 / 3)
    assert out["median_tp_rmse"] == pytest.approx(0.12)
    assert out["pass"]
    assert not gates._summary([{"share_error": 0.06, "tp_rmse": 0.05}] * 3)["pass"]
    assert not gates._summary([{"share_error": 0.0, "tp_rmse": 0.16}] * 3)["pass"]


def test_g1_draws_use_distinct_fixed_seeds(gates):
    first = gates._rng(1, 0).standard_normal(3)
    np.testing.assert_array_equal(first, gates._rng(1, 0).standard_normal(3))
    assert not np.allclose(first, gates._rng(1, 1).standard_normal(3))
    assert not np.allclose(first, gates._rng(2, 0).standard_normal(3))
    assert not np.allclose(first, gates._rng(1, 0, 1).standard_normal(3))


def test_g1_acm_failure_removes_only_the_plain_acm_model(gates):
    g1 = _report()["g1"] | {"acm": {"pass": False}}
    assert gates.passed_models(_report(g1=g1)) == ["acm_bc", "shadow", "dns"]


def test_g1_dns_failure_removes_only_the_dns_model(gates):
    g1 = _report()["g1"] | {"dns": {"pass": False}}
    assert gates.passed_models(_report(g1=g1)) == ["acm", "acm_bc", "shadow"]


def _attempt(*, passed=True, one_factor=0.7, shuffled=0.1):
    return {
        "corr": 0.9998 if passed else 0.5,
        "pass": passed,
        "control_one_factor_corr": one_factor,
        "control_shuffled_corr": shuffled,
    }


def _controls(*attempts, g1_fails=("acm", "dns", "shadow"), zero_bound_fails=True):
    return {
        "g1": {
            f"{m}_control": {"fails_as_required": m in g1_fails} for m in ("acm", "dns", "shadow")
        },
        "g2": {"attempts": list(attempts or [_attempt()]), "pass": True},
        "g3": {"equality": {"control_fails_as_required": zero_bound_fails}},
    }


def test_controls_that_fail_as_required_are_not_reported(gates):
    assert gates.controls_not_failing(_controls()) == []


@pytest.mark.parametrize("model", ["acm", "dns", "shadow"])
def test_a_g1_control_that_does_not_fail_is_reported(gates, model):
    fails = tuple(m for m in ("acm", "dns", "shadow") if m != model)
    assert gates.controls_not_failing(_controls(g1_fails=fails)) == [f"g1.{model}_control"]


def test_g2_controls_that_reach_the_pass_level_are_reported(gates):
    assert gates.controls_not_failing(_controls(_attempt(one_factor=0.95))) == ["g2.one_factor"]
    assert gates.controls_not_failing(_controls(_attempt(shuffled=0.99))) == ["g2.shuffled"]
    both = _controls(_attempt(one_factor=0.97, shuffled=0.96))
    assert gates.controls_not_failing(both) == ["g2.one_factor", "g2.shuffled"]


def test_a_g3_control_that_does_not_fail_is_reported(gates):
    assert gates.controls_not_failing(_controls(zero_bound_fails=False)) == ["g3.zero_bound"]


def test_g2_controls_are_read_from_the_attempt_that_decided_the_gate(gates):
    failed_first = _attempt(passed=False, one_factor=0.99, shuffled=0.99)
    # the second attempt passed: the failed first attempt's controls do not count
    assert gates.controls_not_failing(_controls(failed_first, _attempt())) == []
    bad_second = _attempt(one_factor=0.97)
    assert gates.controls_not_failing(_controls(failed_first, bad_second)) == ["g2.one_factor"]
    # neither passed: the last attempt decides
    failed_last = _attempt(passed=False, shuffled=0.98)
    assert gates.controls_not_failing(_controls(failed_first, failed_last)) == ["g2.shuffled"]
    assert gates.controls_not_failing(_controls(failed_last, _attempt(passed=False))) == []


def test_plain_makes_numpy_values_json_serialisable(gates):
    nested = {
        "a": {"b": np.bool_(True), "c": np.float64(1.5), "d": np.arange(3), "e": [np.int64(2)]}
    }
    expected = {"a": {"b": True, "c": 1.5, "d": [0, 1, 2], "e": [2]}}
    assert json.loads(json.dumps(gates._plain(nested))) == expected


def _git(cwd, *args):
    base = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
    out = subprocess.run(
        [*base, "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def test_commit_refuses_uncommitted_changes_under_macrokit(gates, tmp_path, monkeypatch):
    here = tmp_path / "macrokit/research/study"
    here.mkdir(parents=True)
    (here / "gates.py").write_text("a = 1\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    monkeypatch.setattr(gates, "HERE", here)
    # untracked files, inside or outside macrokit, do not make the tree dirty
    (here / "gates.json").write_text("{}\n")
    (tmp_path / ".superpowers").mkdir()
    (tmp_path / ".superpowers/note.md").write_text("x\n")
    assert gates._commit() == _git(tmp_path, "rev-parse", "HEAD")
    (here / "gates.py").write_text("a = 2\n")
    with pytest.raises(SystemExit, match="uncommitted changes under macrokit"):
        gates._commit()


def _stub_gates(gates, monkeypatch, tmp_path, *, zero_bound_fails):
    g1 = {m: {"pass": True} for m in ("acm", "acm_bc", "dns", "shadow")}
    g1 |= {f"{m}_control": {"fails_as_required": True} for m in ("acm", "dns", "shadow")}
    g3 = {"equality": {"control_fails_as_required": zero_bound_fails}, "pass": True}
    monkeypatch.setattr(gates, "HERE", tmp_path)
    monkeypatch.setattr(gates, "_commit", lambda: "abc123")
    monkeypatch.setattr(gates, "g4", lambda data_root: {"pass": True})
    monkeypatch.setattr(gates, "g2", lambda raw: {"attempts": [_attempt()], "pass": True})
    monkeypatch.setattr(gates, "g3", lambda raw, processes: g3)
    monkeypatch.setattr(gates, "g1", lambda processes: g1)
    monkeypatch.setattr(sys, "argv", ["gates.py", "--data-root", str(tmp_path / "data")])


def test_main_writes_the_report_and_exits_zero_when_every_control_fails(
    gates, monkeypatch, tmp_path, capsys
):
    _stub_gates(gates, monkeypatch, tmp_path, zero_bound_fails=True)
    gates.main()
    report = json.loads((tmp_path / "gates.json").read_text())
    assert report["controls_ok"] is True
    assert report["controls_not_failing"] == []
    assert report["passed_models"] == ["acm", "acm_bc", "shadow", "dns"]
    assert report["code_commit"] == "abc123"
    assert report["settings"]["g1_draws"] == gates.G1_DRAWS
    assert "CONTROLS NOT FAILING" not in capsys.readouterr().out


def test_main_keeps_the_report_but_exits_2_when_a_control_does_not_fail(
    gates, monkeypatch, tmp_path, capsys
):
    _stub_gates(gates, monkeypatch, tmp_path, zero_bound_fails=False)
    with pytest.raises(SystemExit) as stop:
        gates.main()
    assert stop.value.code == 2
    report = json.loads((tmp_path / "gates.json").read_text())
    assert report["controls_ok"] is False
    assert report["controls_not_failing"] == ["g3.zero_bound"]
    assert "CONTROLS NOT FAILING: ['g3.zero_bound']" in capsys.readouterr().out
