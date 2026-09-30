"""Independent §26.4 reference: formula, quadrature, Monte Carlo and Example 26.1."""

import ast
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_gap_reference as ref  # noqa: E402

TEXTBOOK = dict(spot=100.0, r=0.05, sigma=0.20, T=1.0, q=0.0)


@pytest.fixture(scope="module")
def data():
    return ref.build()


def test_reference_imports_only_the_standard_library_and_numpy():
    tree = ast.parse((SCRIPTS / "build_gap_reference.py").read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots == {"argparse", "itertools", "json", "math", "pathlib", "numpy"}


def test_equal_strikes_reproduce_the_textbook_black_scholes_call():
    # S = K = 100, r = 5%, sigma = 20%, T = 1: the standard BSM call 10.4506.
    assert ref.closed_form("call", K1=100.0, K2=100.0, **TEXTBOOK) == pytest.approx(
        10.450583572, abs=1e-8
    )
    assert ref.quadrature("call", K1=100.0, K2=100.0, **TEXTBOOK) == pytest.approx(
        10.450583572, abs=1e-8
    )


def test_quadrature_matches_the_formula_on_every_case(data):
    assert len(data["cases"]) == 38
    for row in data["cases"]:
        assert row["quadrature_price"] == pytest.approx(row["price"], rel=1e-10, abs=1e-10)
        assert row["quadrature_trigger_probability"] == pytest.approx(
            row["trigger_probability"], abs=1e-14
        )
        assert row["price"] == pytest.approx(
            row["regular_price"] + row["trigger_adjustment"], abs=1e-9
        )


def test_monte_carlo_uses_distinct_seeds_and_stays_within_four_standard_errors(data):
    runs = [row["monte_carlo"] for row in data["cases"] if "monte_carlo" in row]
    assert len(runs) == 10
    assert len({run["seed"] for run in runs}) == 10
    assert all(abs(run["z"]) <= 4.0 for run in runs)


def test_example_26_1_matches_the_printed_values(data):
    example = data["example_26_1"]
    assert round(example["regular_put"]) == 3_436
    assert round(example["insurer_gap_put"]) == 1_896
    assert example["reduction"] == pytest.approx(0.448277597587, abs=1e-11)
    assert example["insurer_gap_put"] == pytest.approx(
        example["policyholder_put"] + example["transfer_cost_present_value"], abs=1e-9
    )
    assert example["insurer_gap_put_quadrature"] == pytest.approx(
        example["insurer_gap_put"], abs=1e-9
    )


def test_conditional_mean_settlement_prices_the_gap_at_zero(data):
    means = data["conditional_mean"]
    assert means["call"]["closed_form"] > 100.0 > means["put"]["closed_form"]
    for row in means.values():
        assert row["quadrature"] == pytest.approx(row["closed_form"], rel=1e-10)
        assert abs(row["price_at_level"]) < 1e-12


def test_payoff_dataset_keeps_the_jump_and_the_negative_region(data):
    payoff = data["figure"]["payoff"]
    grid = payoff["grid"]
    above = grid.index(100.5)
    assert payoff["gap_call_K1_110"][above] == pytest.approx(-9.5)
    assert payoff["gap_call_K1_90"][above] == pytest.approx(10.5)
    assert payoff["regular_call"][grid.index(100.0)] == 0.0
    assert min(payoff["gap_call_K1_110"]) == pytest.approx(-9.5)


def test_transfer_cost_rows_split_insurer_cost(data):
    rows = data["figure"]["transfer_cost"]["rows"]
    assert rows[0]["reduction"] == pytest.approx(0.0, abs=1e-15)
    fifty = next(row for row in rows if row["transfer_cost"] == 50_000.0)
    assert fifty["insurer_cost"] == pytest.approx(data["example_26_1"]["insurer_gap_put"])
    costs = [row["insurer_cost"] for row in rows]
    assert costs == sorted(costs, reverse=True)


def test_check_mode_rejects_stale_saved_reference(monkeypatch, tmp_path):
    output = tmp_path / "reference.json"
    monkeypatch.setattr(ref, "OUT", output)
    monkeypatch.setattr(sys, "argv", ["build_gap_reference.py"])
    ref.main()
    monkeypatch.setattr(sys, "argv", ["build_gap_reference.py", "--check"])
    ref.main()
    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="missing or stale"):
        ref.main()
