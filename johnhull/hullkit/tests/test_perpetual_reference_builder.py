"""Independent reference-builder checks for Hull §26.2."""

import math
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_perpetual_reference as ref  # noqa: E402

SYMMETRIC = {"spot": 100.0, "strike": 100.0, "rate": 0.04, "yield": 0.04, "sigma": 0.20}


def test_symmetric_market_has_hand_derived_boundaries_and_prices():
    case = ref.analytic_case("symmetric", SYMMETRIC)
    assert case["a1"] == pytest.approx(2.0)
    assert case["a2"] == pytest.approx(1.0)
    assert case["call"]["boundary"] == pytest.approx(200.0)
    assert case["put"]["boundary"] == pytest.approx(50.0)
    assert case["call"]["value"] == pytest.approx(25.0)
    assert case["put"]["value"] == pytest.approx(25.0)
    assert abs(case["characteristic_residuals"]["positive"]) < 1e-14
    assert abs(case["characteristic_residuals"]["negative"]) < 1e-14
    for kind in ("call", "put"):
        assert abs(case[kind]["matching_residual"]) < 1e-12
        assert abs(case[kind]["smooth_pasting_residual"]) < 1e-12


def test_exercise_regions_and_zero_yield_call_limit():
    case = ref.analytic_case("symmetric", SYMMETRIC)
    assert ref.option_value("call", 240.0, case) == pytest.approx(140.0)
    assert ref.option_value("put", 40.0, case) == pytest.approx(60.0)
    assert ref.option_value("call", 50.0, case) == pytest.approx(6.25)
    assert ref.option_value("put", 200.0, case) == pytest.approx(12.5)

    no_yield = ref.analytic_case("no_yield", {**SYMMETRIC, "yield": 0.0})
    assert no_yield["a1"] == pytest.approx(1.0)
    assert no_yield["call"]["boundary"] is None
    assert no_yield["call"]["boundary_kind"] == "infinite"
    assert no_yield["call"]["value"] == pytest.approx(SYMMETRIC["spot"])
    assert ref.option_value("call", 240.0, no_yield) == pytest.approx(240.0)
    assert math.isfinite(no_yield["put"]["boundary"])


@pytest.mark.parametrize(
    "change",
    [
        {"spot": 0.0},
        {"strike": -1.0},
        {"rate": 0.0},
        {"yield": -0.01},
        {"sigma": 0.0},
        {"sigma": math.inf},
        {"sigma": 1e200},
        {"yield": 1e308},
    ],
)
def test_unsupported_market_is_rejected(change):
    with pytest.raises(ValueError):
        ref.analytic_case("bad", {**SYMMETRIC, **change})


def test_long_finite_maturity_lattice_approaches_perpetual_values():
    case = ref.analytic_case("symmetric", SYMMETRIC)
    short = ref.crr_american(SYMMETRIC, 20.0, 200)
    long = ref.crr_american(SYMMETRIC, 80.0, 800)
    assert short["call"] < long["call"] < case["call"]["value"]
    assert short["put"] < long["put"] < case["put"]["value"]
    assert case["call"]["value"] - long["call"] < 0.2
    assert case["put"]["value"] - long["put"] < 0.2


def test_lattice_rejects_unresolvable_time_step():
    with pytest.raises(ValueError):
        ref.crr_american(SYMMETRIC, 1e-100, 1)


def test_standard_dividend_anchor_is_saved():
    cases = {case["label"]: case for case in ref.build()["cases"]}
    anchor = cases["standard_dividend"]
    assert anchor["parameters"] == {
        "spot": 100.0,
        "strike": 100.0,
        "rate": 0.05,
        "yield": 0.03,
        "sigma": 0.20,
    }
    assert anchor["call"]["boundary"] == pytest.approx(272.07592200561265)
    assert anchor["put"]["boundary"] == pytest.approx(61.25741132772069)
    assert anchor["call"]["value"] == pytest.approx(35.352057418829865)
    assert anchor["put"]["value"] == pytest.approx(17.850767636980986)


def test_check_mode_detects_stale_saved_json(monkeypatch, tmp_path):
    output = tmp_path / "reference.json"
    monkeypatch.setattr(ref, "OUT", output)
    monkeypatch.setattr(sys, "argv", ["build_perpetual_reference.py"])
    ref.main()
    monkeypatch.setattr(sys, "argv", ["build_perpetual_reference.py", "--check"])
    ref.main()
    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="missing or stale"):
        ref.main()
