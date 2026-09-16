"""Independent acceptance of the private CRR single-shout teaching engine."""

import json
import math
from pathlib import Path

import numpy as np
import pytest
from hullkit._shout import _price, _tree
from scipy.integrate import quad
from scipy.stats import lognorm

VALIDATION = Path(__file__).resolve().parents[2] / "docs/validation/section-26-12"
ROWS = json.loads((VALIDATION / "prices.json").read_text())["rows"]


def args(row):
    return (
        row["spot"],
        row["strike"],
        row["rate"],
        row["dividend"],
        row["volatility"],
        row["expiry"],
        row["contract"],
    )


def integrated_shout(spot, strike, rate, dividend, sigma, tau, kind):
    law = lognorm(
        sigma * math.sqrt(tau), scale=spot * math.exp((rate - dividend - sigma**2 / 2) * tau)
    )
    sign = 1 if kind == "call" else -1

    def integrand(terminal):
        return (sign * (spot - strike) + max(sign * (terminal - spot), 0)) * law.pdf(terminal)

    return math.exp(-rate * tau) * (
        quad(integrand, 0, spot, epsabs=1e-10)[0] + quad(integrand, spot, np.inf, epsabs=1e-10)[0]
    )


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("spot", [60.0, 100.0, 140.0])
def test_signed_immediate_value_by_direct_payoff_integration(spot, kind):
    inputs = (spot, 100.0, 0.06, 0.02, 0.30, 1.4, kind)
    assert _tree(*inputs, steps=4)["immediate"] == pytest.approx(
        integrated_shout(*inputs), abs=1e-9
    )


@pytest.mark.parametrize(
    "row", ROWS, ids=lambda row: f"{row['market']}-{row['contract']}-{row['spot_ratio']}"
)
def test_all_saved_independent_prices(row):
    result = _tree(*args(row), steps=1024)
    assert result["price"] == pytest.approx(row["price"], abs=0.005)
    assert result["immediate"] == pytest.approx(row["shout_immediately"], abs=1e-11)
    assert result["price"] == max(result["immediate"], result["continuation"])
    if abs(row["price"] - row["shout_immediately"]) < 1e-4:
        assert result["root_decision"] == "shout"
        assert result["price"] == result["immediate"]


@pytest.mark.parametrize("kind", ["call", "put"])
def test_three_step_values_are_independent_backward_payoff_expectations(kind):
    spot, strike, rate, dividend, sigma, expiry = 100.0, 100.0, 0.05, 0.02, 0.2, 1.0
    dt = expiry / 3
    up = math.exp(sigma * math.sqrt(dt))
    probability = (math.exp((rate - dividend) * dt) - 1 / up) / (up - 1 / up)
    sign = 1 if kind == "call" else -1

    def value(step, ups):
        level = spot * up ** (2 * ups - step)
        if step == 3:
            return max(sign * (level - strike), 0)
        continuation = math.exp(-rate * dt) * (
            probability * value(step + 1, ups + 1) + (1 - probability) * value(step + 1, ups)
        )
        return max(
            continuation,
            integrated_shout(level, strike, rate, dividend, sigma, expiry - step * dt, kind),
        )

    tree = _tree(spot, strike, rate, dividend, sigma, expiry, kind, 3)
    assert tree["price"] == pytest.approx(value(0, 0), abs=1e-9)
    assert len(tree["small_tree_nodes"]) == 10
    for node in tree["small_tree_nodes"]:
        assert node["value"] == pytest.approx(value(node["step"], node["upcount"]), abs=1e-9)


def test_put_is_not_call_with_swapped_spot_strike_and_rates():
    actual = _price(100, 100, 0.05, 0.02, 0.3, 2, "put", 512)
    swapped = _price(100, 100, 0.02, 0.05, 0.3, 2, "call", 512)
    assert abs(actual - swapped) > 1


@pytest.mark.parametrize(
    "field,value",
    [
        (0, 0),
        (1, -1),
        (2, np.nan),
        (3, np.inf),
        (4, 0),
        (5, 0),
        (6, "bad"),
        (7, 0),
        (7, 1.5),
        (7, True),
    ],
)
def test_invalid_inputs_are_rejected(field, value):
    inputs = [100.0, 100.0, 0.05, 0.02, 0.2, 1.0, "call", 16]
    inputs[field] = value
    with pytest.raises(ValueError):
        _price(*inputs)


def test_invalid_crr_probability_is_not_clamped():
    with pytest.raises(ValueError, match="probability"):
        _price(100, 100, 2.0, 0.0, 0.01, 1.0, steps=1)


def test_saved_tree_acceptance_is_recomputed_from_every_residual():
    record = json.loads((VALIDATION / "tree-check.json").read_text())
    assert record["adopted_steps"] == 1024
    assert record["absolute_tolerance"] == 0.005
    summaries = []
    for curve in record["convergence"]:
        assert len(curve["rows"]) == 42
        residuals = []
        for row, saved in zip(ROWS, curve["rows"], strict=True):
            assert saved["tree"] == pytest.approx(
                _price(*args(row), steps=curve["steps"]), rel=0, abs=1e-12
            )
            assert saved["reference"] == row["price"]
            difference = saved["tree"] - saved["reference"]
            assert saved["residual"] == pytest.approx(difference, abs=1e-14)
            residuals.append(difference)
        maximum = max(abs(x) for x in residuals)
        rms = math.sqrt(sum(x * x for x in residuals) / 42)
        assert curve["max_absolute"] == pytest.approx(maximum)
        assert curve["rms"] == pytest.approx(rms)
        summaries.append((maximum, rms))
    assert summaries[-1][0] <= 0.005
    assert summaries[-1][0] < summaries[0][0]
    assert summaries[-1][1] < summaries[0][1]


def test_saved_boundary_checks_have_real_adjacent_nodes_and_honest_error():
    import sys

    sys.path.insert(0, str(VALIDATION.parents[2] / "scripts"))
    from build_shout_reference import integral_equation_price

    record = json.loads((VALIDATION / "tree-check.json").read_text())
    assert {x["market"] for x in record["boundaries"]} == {
        "positive-carry",
        "zero-carry",
        "long-high-vol",
    }
    for family in record["boundaries"]:
        source = next(
            r
            for r in ROWS
            if r["market"] == family["market"] and r["contract"] == "call" and r["spot_ratio"] == 1
        )
        tree = _tree(*args(source), steps=1024)
        _, times, reference = integral_equation_price(*args(source), steps=400)
        for check in family["selected_checks"]:
            i = check["step"]
            lower, upper = tree["boundary_lower"][i], tree["boundary_upper"][i]
            assert check["lower"] == lower
            assert check["upper"] == upper
            assert upper / lower == pytest.approx(tree["up"] ** 2)
            assert check["reference"] == pytest.approx(
                np.interp(check["remaining_time"], times, reference), rel=0, abs=1e-10
            )
            distance = max(lower - check["reference"], check["reference"] - upper, 0.0)
            assert check["distance_outside_bracket"] == pytest.approx(distance)
            assert distance <= upper - lower
        assert len(family["selected_checks"]) == 5


def test_lesson_artifact_matches_tree_and_frozen_sources():
    import hashlib

    lesson = json.loads((VALIDATION / "lesson-data.json").read_text())
    for name in ("contract", "payoff", "decision_tree", "prices", "convergence", "boundaries"):
        family = lesson[name]
        assert {"units", "method", "limitations", "source_hashes", "data"} <= family.keys()
        for path, digest in family["source_hashes"].items():
            project = VALIDATION.parents[2]
            assert hashlib.sha256((project / path).read_bytes()).hexdigest() == digest
    assert lesson["decision_tree"]["data"]["tree"] == _tree(100, 100, 0.05, 0.02, 0.2, 1, steps=3)
    assert len(lesson["prices"]["data"]) == 42
    record = json.loads((VALIDATION / "tree-check.json").read_text())
    assert lesson["boundaries"]["data"] == record["boundaries"]
    assert lesson["convergence"]["data"] == record["convergence"]
    for row, saved, result in zip(
        ROWS, lesson["prices"]["data"], record["convergence"][-1]["rows"], strict=True
    ):
        for key, value in row.items():
            assert saved[key] == value
        assert saved["tree"] == result["tree"]
        assert saved["tree_residual"] == result["residual"]
        assert saved["root_decision"] == result["root_decision"]
        if row["rate"] == row["dividend"]:
            assert saved["fixed_lookback"] is None


@pytest.mark.parametrize(
    "old,new",
    [
        ("math.exp((rate - dividend) * dt)", "math.exp((rate + dividend) * dt)"),
        ("discount = math.exp(-rate * dt)", "discount = math.exp(-dividend * dt)"),
        ("values = np.maximum(continuation, immediate)", "values = continuation"),
        ("values = np.maximum(continuation, immediate)", "values = immediate"),
    ],
)
def test_independent_price_rejects_drift_discount_and_nonoptimal_mutants(old, new):
    from types import ModuleType

    import hullkit._shout as engine

    source = Path(engine.__file__).read_text()
    assert old in source
    mutant = ModuleType("shout_mutant")
    exec(compile(source.replace(old, new), "shout_mutant", "exec"), mutant.__dict__)
    row = next(
        r
        for r in ROWS
        if r["market"] == "positive-carry" and r["contract"] == "call" and r["spot_ratio"] == 1
    )
    assert abs(mutant._price(*args(row), steps=1024) - row["price"]) > 0.005
