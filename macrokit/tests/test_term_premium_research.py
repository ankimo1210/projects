import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from macrokit.termstructure import acm, shadow, synthetic
from macrokit.termstructure.curve import ZeroPanel, month_ends

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


@pytest.fixture(scope="module")
def run_japan():
    return _load("run_japan")


def test_canonical_ignores_the_hash_field(run_japan):
    config = {"b": 1, "a": [1, 2], "sha256": "x"}
    assert run_japan.canonical(config) == b'{"a":[1,2],"b":1}'


def test_check_hash_accepts_a_frozen_config_and_rejects_an_edit(run_japan):
    config = json.loads((RESEARCH / "config.json").read_text())
    config["sha256"] = run_japan.config_hash(config)
    run_japan.check_hash(config)
    config["verdict_band"] = [0.3, 0.7]
    with pytest.raises(ValueError, match="sha256"):
        run_japan.check_hash(config)


def test_interval_or_none_is_none_for_no_draws_and_a_percentile_band_otherwise(run_japan):
    assert run_japan._interval_or_none(np.empty((0, 5)), 0.90) is None
    assert run_japan._interval_or_none([], 0.90) is None
    samples = np.arange(1, 101)
    expected = np.percentile(samples, [5, 95])
    assert run_japan._interval_or_none(samples, 0.90) == pytest.approx(list(expected))
    assert run_japan._interval_or_none(samples, 0.90) == pytest.approx([5.95, 95.05])


def test_attempt_returns_the_value_or_the_error_text(run_japan):
    assert run_japan._attempt(lambda: 5) == 5
    assert run_japan._attempt(lambda: 1 / 0) == {"error": "ZeroDivisionError: division by zero"}


def test_to_json_makes_numpy_values_serialisable(run_japan):
    nested = {
        "a": {"b": np.bool_(True), "c": np.float64(1.5), "d": np.arange(3), "e": (np.int64(2),)},
        "f": [np.array([[1.0, 2.0]]), {"g": np.float64("nan")}],
        np.int64(7): None,
    }
    plain = run_japan._to_json(nested)
    assert json.loads(json.dumps(plain))["a"] == {"b": True, "c": 1.5, "d": [0, 1, 2], "e": [2]}
    assert plain["f"][0] == [[1.0, 2.0]]
    assert 7 in plain


def test_to_json_maps_non_finite_floats_to_none_so_the_file_is_standard_json(run_japan):
    values = {
        "a": float("nan"),
        "b": np.float64("inf"),
        "c": np.float32("nan"),
        "d": np.array([1.0, -np.inf, np.nan]),
        "e": (float("-inf"), 2.5),
    }
    plain = run_japan._to_json(values)
    assert plain == {"a": None, "b": None, "c": None, "d": [1.0, None, None], "e": [None, 2.5]}
    json.dumps(plain, allow_nan=False)


def test_a_penalised_optimum_is_not_finite_or_at_least_half_the_penalty(run_japan):
    penalty = shadow.PENALTY
    assert run_japan._unpenalised(12345.6)
    assert run_japan._unpenalised(0.4 * penalty)
    for value in (penalty, 2 * penalty, 0.5 * penalty, np.nan, np.inf, -np.inf):
        assert not run_japan._unpenalised(value)


def test_start_order_puts_none_and_non_finite_values_last(run_japan):
    rows = [{"negloglik": v} for v in (np.nan, 3.0, None, 1.0, np.inf, 2.0)]
    ordered = [row["negloglik"] for row in sorted(rows, key=run_japan._start_order)]
    assert ordered[:3] == [1.0, 2.0, 3.0]
    assert all(v is None or not np.isfinite(v) for v in ordered[3:])


def test_write_results_replaces_the_file_whole_and_keeps_the_old_one_on_a_failure(
    run_japan, monkeypatch, tmp_path
):
    monkeypatch.setattr(run_japan, "HERE", tmp_path)
    run_japan._write_results({"a": np.float64(1.5), "b": float("nan")})
    assert json.loads((tmp_path / "results.json").read_text()) == {"a": 1.5, "b": None}
    assert not (tmp_path / "results.json.tmp").exists()
    with pytest.raises(TypeError):
        run_japan._write_results({"a": object()})
    assert json.loads((tmp_path / "results.json").read_text()) == {"a": 1.5, "b": None}
    assert not (tmp_path / "results.json.tmp").exists()


def test_check_constants_accepts_the_real_config_and_names_a_changed_field(run_japan):
    config = json.loads((RESEARCH / "config.json").read_text())
    run_japan._check_constants(config)
    config["verdict_band"] = [0.3, 0.7]
    with pytest.raises(SystemExit, match="verdict_band"):
        run_japan._check_constants(config)
    config = json.loads((RESEARCH / "config.json").read_text())
    config["shadow"]["forward_months"] = [3, 6, 12, 24, 60, 84, 119]
    config["acm"]["return_months"] = [6, 12]
    with pytest.raises(SystemExit, match=r"acm\.return_months, shadow\.forward_months"):
        run_japan._check_constants(config)


def test_shares_gives_the_share_or_none_for_a_failed_model(run_japan):
    class Stub:
        def share(self, t0, t1):
            return t1 - t0

    assert run_japan._shares({"acm": Stub(), "shadow": None}, 1, 4, ["acm", "shadow"]) == {
        "acm": 3,
        "shadow": None,
    }


def _japan_panel():
    syn = synthetic.simulate_affine(
        synthetic.AFFINE_TRUE, 480, np.random.default_rng(5), max_months=360
    )
    return ZeroPanel(month_ends(480, 1987), syn.panel.months, syn.panel.yields)


_MISSING = object()
GATES_COMMIT = "gates123"


def _gates(
    controls_ok=True, *, code_commit=GATES_COMMIT, passed=("acm", "acm_bc", "shadow", "dns")
):
    gates = {"code_commit": code_commit, "passed_models": list(passed)}
    if controls_ok is not _MISSING:
        gates["controls_ok"] = controls_ok
    return gates


def _setup_japan(run_japan, monkeypatch, tmp_path, gates=None, *, connect=None):
    """A frozen tiny configuration in tmp_path, a synthetic Japanese-like panel, no real data."""
    panel = _japan_panel()
    cfg = json.loads((RESEARCH / "config.json").read_text())
    cfg["bias_correction"]["n_boot"] = 20
    cfg["intervals"] |= {"n_boot": 20, "n_draws": 5}
    cfg["shadow"]["maxiter"] = 2
    cfg["code_commit"] = "abc123"
    gates_text = json.dumps(_gates() if gates is None else gates)
    cfg["gates_commit"] = GATES_COMMIT
    cfg["gates_sha256"] = hashlib.sha256(gates_text.encode()).hexdigest()
    cfg["sha256"] = run_japan.config_hash(cfg)
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    (tmp_path / "gates.json").write_text(gates_text)
    monkeypatch.setattr(run_japan, "HERE", tmp_path)
    monkeypatch.setattr(run_japan, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(run_japan, "GATES", tmp_path / "gates.json")
    monkeypatch.setattr(run_japan, "_code_unchanged", lambda *args, **kwargs: True)
    monkeypatch.setattr(run_japan, "_git", lambda *args: "")
    monkeypatch.setattr(run_japan, "connect", connect or (lambda path: None))
    monkeypatch.setattr(run_japan, "fit_month_ends", lambda con, start, end: [])
    monkeypatch.setattr(run_japan, "zero_panel", lambda fits: panel)
    argv = ["run_japan.py", "--data-root", str(tmp_path), "--processes", "1"]
    monkeypatch.setattr(sys, "argv", argv)


def _run_japan_on_synthetic(run_japan, monkeypatch, tmp_path, capsys, fit, draws=None, gates=None):
    """main() on a synthetic Japanese-like panel with a tiny configuration."""
    _setup_japan(run_japan, monkeypatch, tmp_path, gates)
    monkeypatch.setattr(shadow, "fit_shadow", lambda *args, **kwargs: fit)
    if draws is not None:
        monkeypatch.setattr(shadow, "draw_expected", lambda *args, **kwargs: draws)
    seen = {"results_on_disk_at_each_fit": []}
    real_fit_acm = acm.fit_acm

    def fit_acm(panel, k=5, **kwargs):
        seen["results_on_disk_at_each_fit"].append((tmp_path / "results.json").exists())
        if k == 3:
            seen["on_disk"] = json.loads((tmp_path / "results.json").read_text())
            seen["printed"] = capsys.readouterr().out
            raise ZeroDivisionError("boom")
        return real_fit_acm(panel, k=k, **kwargs)

    monkeypatch.setattr(acm, "fit_acm", fit_acm)
    run_japan.main()
    assert not (tmp_path / "results.json.tmp").exists()
    return json.loads((tmp_path / "results.json").read_text()), seen


def _shadow_fit(negloglik, start_negloglik, start_theta):
    theta = synthetic.SHADOW_TRUE
    return shadow.ShadowFit(theta, negloglik, start_theta, np.array(start_negloglik), -0.10)


def test_a_failed_shadow_fit_excludes_only_that_model_and_main_results_are_written_first(
    run_japan, monkeypatch, tmp_path, capsys
):
    starts = np.tile(synthetic.SHADOW_TRUE, (2, 1))
    fit = _shadow_fit(shadow.PENALTY, [shadow.PENALTY, 2e12], starts)
    results, seen = _run_japan_on_synthetic(run_japan, monkeypatch, tmp_path, capsys, fit)

    assert results["models_used"] == ["acm", "acm_bc", "dns"]
    assert results["models_excluded_after_estimation"] == ["shadow"]
    assert results["verdict"] != "undetermined"
    failed = results["main"]["shadow"]
    assert failed == {
        "share": None,
        "interval": None,
        "contains_half": None,
        "delta_expected_pct": None,
        "passed_gates": True,
        "estimation_failed": True,
    }
    for name in ("acm", "acm_bc", "dns"):
        assert results["main"][name]["estimation_failed"] is False
        assert len(results["main"][name]["interval"]) == 2
    assert [row["share"] for row in results["shadow_starts"]] == [None, None]
    assert results["shadow_draws"] is None
    # the supplementary block is computed after the main block is on disk and on screen
    on_disk = seen["results_on_disk_at_each_fit"]
    assert on_disk[0] is False
    assert all(on_disk[1:])
    assert len(on_disk) > 3
    assert "supplementary" not in seen["on_disk"]
    assert seen["on_disk"]["main"] == results["main"]
    assert seen["printed"].startswith("MAIN RESULTS\n")
    supp = results["supplementary"]
    assert supp["acm_k3"] == {"error": "ZeroDivisionError: boom"}
    assert supp["maturity_60"]["shadow"] is None
    assert supp["maturity_60"]["dns"] is not None
    assert supp["t1_latest"]["shares"]["shadow"] is None
    assert supp["window_2004-01-01"]["shadow"] is None
    assert set(supp["long_acm"]) == {"maturity_120", "maturity_240", "maturity_360"}


def test_a_shadow_fit_with_no_accepted_draws_gives_a_point_estimate_and_no_interval(
    run_japan, monkeypatch, tmp_path, capsys
):
    # a penalised or NaN optimum must not have its filtered states requested (the NaN one is
    # listed first and must sort last); a finite value with unusable parameters records an error
    bad = np.full(shadow.N_PARAMS, np.nan)
    starts = np.vstack([bad, synthetic.SHADOW_TRUE, bad, bad])
    fit = _shadow_fit(10.0, [np.nan, 10.0, 11.0, shadow.PENALTY], starts)
    draws = (np.empty((0, 480)), 5, 0)
    results, _ = _run_japan_on_synthetic(run_japan, monkeypatch, tmp_path, capsys, fit, draws)

    assert results["models_used"] == ["acm", "acm_bc", "shadow", "dns"]
    assert results["models_excluded_after_estimation"] == []
    point = results["main"]["shadow"]
    assert point["estimation_failed"] is False
    assert isinstance(point["share"], float)
    assert point["interval"] is None
    assert point["contains_half"] is None
    *rows, not_finite = results["shadow_starts"]
    first, unusable, penalised = rows
    assert not_finite == {"negloglik": None, "share": None}  # NaN sorts last
    assert [first["negloglik"], unusable["negloglik"], penalised["negloglik"]] == [
        10.0,
        11.0,
        shadow.PENALTY,
    ]
    assert isinstance(first["share"], float)
    assert "error" not in first
    assert unusable["share"] is None
    assert unusable["error"].startswith("ValueError: parameters are penalised")
    assert penalised == {"negloglik": shadow.PENALTY, "share": None}
    assert results["shadow_draws"] == {"rejected": 5, "floored_eigenvalues": 0}


def test_a_model_that_failed_a_gate_is_still_estimated_but_leaves_the_verdict(
    run_japan, monkeypatch, tmp_path, capsys
):
    fit = _shadow_fit(10.0, [10.0], np.tile(synthetic.SHADOW_TRUE, (1, 1)))
    gates = _gates(passed=("acm", "acm_bc", "shadow"))
    draws = (np.empty((0, 480)), 5, 0)
    results, _ = _run_japan_on_synthetic(
        run_japan, monkeypatch, tmp_path, capsys, fit, draws, gates
    )

    assert results["models_used"] == ["acm", "acm_bc", "shadow"]
    assert results["models_excluded_after_estimation"] == []
    assert results["main"]["dns"]["passed_gates"] is False
    assert results["main"]["dns"]["estimation_failed"] is False
    assert isinstance(results["main"]["dns"]["share"], float)
    assert all(results["main"][m]["passed_gates"] for m in ("acm", "acm_bc", "shadow"))
    assert results["verdict"] != "undetermined"


def _no_data(path):
    raise AssertionError("the data must not be opened")


def test_main_refuses_to_run_twice_before_it_touches_any_data(run_japan, monkeypatch, tmp_path):
    _setup_japan(run_japan, monkeypatch, tmp_path, connect=_no_data)
    (tmp_path / "results.json").write_text('{"first": true}\n')
    with pytest.raises(SystemExit, match=r"results\.json exists"):
        run_japan.main()
    assert json.loads((tmp_path / "results.json").read_text()) == {"first": True}


def test_main_refuses_gates_that_changed_after_the_freeze_before_it_touches_any_data(
    run_japan, monkeypatch, tmp_path
):
    _setup_japan(run_japan, monkeypatch, tmp_path, _gates(code_commit="other"), connect=_no_data)
    with pytest.raises(SystemExit, match=r"gates\.json changed after the freeze"):
        run_japan.main()
    assert not (tmp_path / "results.json").exists()


@pytest.mark.parametrize(
    "edit", ["passed_models", "whitespace"], ids=["edited_passed_models", "reformatted"]
)
def test_main_refuses_gates_whose_bytes_changed_after_the_freeze(
    run_japan, monkeypatch, tmp_path, edit
):
    _setup_japan(run_japan, monkeypatch, tmp_path, connect=_no_data)
    config = json.loads((tmp_path / "config.json").read_text())
    gates_file = tmp_path / "gates.json"
    if edit == "passed_models":
        gates = _gates(passed=("acm", "acm_bc", "shadow"))
        gates_file.write_text(json.dumps(gates))
    else:
        gates_file.write_text(gates_file.read_text() + "\n")
    # the commit still matches: only the content differs from what was frozen
    assert json.loads(gates_file.read_text())["code_commit"] == config["gates_commit"]
    with pytest.raises(SystemExit, match=r"gates\.json changed after the freeze"):
        run_japan.main()
    assert not (tmp_path / "results.json").exists()


def test_main_refuses_a_config_frozen_without_the_gate_hash(run_japan, monkeypatch, tmp_path):
    _setup_japan(run_japan, monkeypatch, tmp_path, connect=_no_data)
    cfg = json.loads((tmp_path / "config.json").read_text())
    cfg["gates_sha256"] = None
    cfg["sha256"] = run_japan.config_hash(cfg)
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    with pytest.raises(SystemExit, match=r"gates\.json changed after the freeze"):
        run_japan.main()


@pytest.mark.parametrize("controls_ok", [False, _MISSING, "yes", 1, None])
def test_main_refuses_gates_whose_controls_did_not_all_fail(
    run_japan, monkeypatch, tmp_path, controls_ok
):
    _setup_japan(run_japan, monkeypatch, tmp_path, _gates(controls_ok), connect=_no_data)
    with pytest.raises(SystemExit, match="controls_ok is not true"):
        run_japan.main()
    assert not (tmp_path / "results.json").exists()


def test_main_refuses_a_config_that_differs_from_the_code_constants(
    run_japan, monkeypatch, tmp_path
):
    _setup_japan(run_japan, monkeypatch, tmp_path, connect=_no_data)
    cfg = json.loads((tmp_path / "config.json").read_text())
    cfg["verdict_band"] = [0.3, 0.7]
    cfg["sha256"] = run_japan.config_hash(cfg)  # a consistent but different freeze
    (tmp_path / "config.json").write_text(json.dumps(cfg))
    with pytest.raises(SystemExit, match="verdict_band"):
        run_japan.main()


def test_main_requires_a_data_root_for_the_run(run_japan, monkeypatch, tmp_path, capsys):
    _setup_japan(run_japan, monkeypatch, tmp_path, connect=_no_data)
    monkeypatch.setattr(sys, "argv", ["run_japan.py"])
    with pytest.raises(SystemExit) as stop:
        run_japan.main()
    assert stop.value.code == 2
    assert "--data-root is required for the run" in capsys.readouterr().err


def _research_repo(tmp_path):
    """A repository with the layout of the real one: src and the study directory under macrokit."""
    here = tmp_path / "macrokit/research/study"
    here.mkdir(parents=True)
    (tmp_path / "macrokit/src").mkdir()
    (tmp_path / "macrokit/src/module.py").write_text("a = 1\n")
    (here / "run_japan.py").write_text("b = 1\n")
    (here / "config.json").write_text((RESEARCH / "config.json").read_text())
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return here


def test_dirty_sees_tracked_changes_from_the_study_directory_and_ignores_untracked_files(
    run_japan, tmp_path, monkeypatch
):
    here = _research_repo(tmp_path)
    monkeypatch.setattr(run_japan, "HERE", here)
    (here / "gates.json").write_text("{}\n")  # untracked
    assert run_japan._dirty("macrokit") == ""
    (tmp_path / "macrokit/src/module.py").write_text("a = 2\n")
    assert "macrokit/src/module.py" in run_japan._dirty("macrokit")
    assert "macrokit/src/module.py" in run_japan._dirty("macrokit/src", "macrokit/research/study")
    assert run_japan._dirty("macrokit/research/study/run_japan.py") == ""


def _freeze_setup(run_japan, monkeypatch, tmp_path, gates=None):
    """The research repository with gates.json (untracked, as the gate run leaves it)."""
    here = _research_repo(tmp_path)
    head = _git(tmp_path, "rev-parse", "HEAD")
    gates = {"code_commit": head, "controls_ok": True} if gates is None else gates
    (here / "gates.json").write_text(json.dumps(gates))
    monkeypatch.setattr(run_japan, "HERE", here)
    monkeypatch.setattr(run_japan, "CONFIG", here / "config.json")
    monkeypatch.setattr(run_japan, "GATES", here / "gates.json")
    return here, head


def test_freeze_records_the_commits_and_a_valid_hash_and_refuses_a_dirty_tree(
    run_japan, tmp_path, monkeypatch
):
    here, _ = _freeze_setup(run_japan, monkeypatch, tmp_path)
    (tmp_path / "macrokit/src/module.py").write_text("a = 2\n")
    with pytest.raises(SystemExit, match="commit everything under macrokit"):
        run_japan.freeze()
    _git(tmp_path, "commit", "-q", "-a", "-m", "change the code after the gates")
    with pytest.raises(SystemExit, match="changed after the gates"):
        run_japan.freeze()
    head = _git(tmp_path, "rev-parse", "HEAD")
    (here / "gates.json").write_text(json.dumps({"code_commit": head, "controls_ok": True}))
    run_japan.freeze()
    config = json.loads((here / "config.json").read_text())
    assert config["code_commit"] == head
    assert config["gates_commit"] == config["code_commit"]
    gates_bytes = (here / "gates.json").read_bytes()
    assert config["gates_sha256"] == hashlib.sha256(gates_bytes).hexdigest()
    run_japan.check_hash(config)
    config["gates_sha256"] = "0" * 64  # the frozen hash covers the gate results
    with pytest.raises(ValueError, match="sha256"):
        run_japan.check_hash(config)


@pytest.mark.parametrize("controls_ok", [False, _MISSING, "yes", 1, None])
def test_freeze_refuses_gates_whose_controls_did_not_all_fail(
    run_japan, tmp_path, monkeypatch, controls_ok
):
    here, head = _freeze_setup(run_japan, monkeypatch, tmp_path)
    gates = {"code_commit": head}
    if controls_ok is not _MISSING:
        gates["controls_ok"] = controls_ok
    (here / "gates.json").write_text(json.dumps(gates))
    with pytest.raises(SystemExit, match="controls_ok is not true"):
        run_japan.freeze()
    assert json.loads((here / "config.json").read_text())["sha256"] is None


def test_freeze_refuses_a_configuration_that_is_already_frozen(run_japan, tmp_path, monkeypatch):
    here, _ = _freeze_setup(run_japan, monkeypatch, tmp_path)
    config = json.loads((here / "config.json").read_text())
    config["sha256"] = run_japan.config_hash(config)
    (here / "config.json").write_text(json.dumps(config))
    _git(tmp_path, "commit", "-q", "-a", "-m", "freeze")
    with pytest.raises(SystemExit, match="already frozen; a new configuration is a new study"):
        run_japan.freeze()
    assert json.loads((here / "config.json").read_text()) == config


def test_freeze_refuses_once_results_exist(run_japan, tmp_path, monkeypatch):
    here, _ = _freeze_setup(run_japan, monkeypatch, tmp_path)
    (here / "results.json").write_text("{}\n")  # untracked
    with pytest.raises(SystemExit, match="already frozen"):
        run_japan.freeze()
    assert json.loads((here / "config.json").read_text())["sha256"] is None


def test_freeze_refuses_a_config_that_main_would_refuse(run_japan, tmp_path, monkeypatch):
    here, _ = _freeze_setup(run_japan, monkeypatch, tmp_path)
    config = json.loads((here / "config.json").read_text())
    config["verdict_band"] = [0.3, 0.7]
    (here / "config.json").write_text(json.dumps(config))
    _git(tmp_path, "commit", "-q", "-a", "-m", "edit the band")
    with pytest.raises(SystemExit, match="verdict_band"):
        run_japan.freeze()
    assert json.loads((here / "config.json").read_text())["sha256"] is None
