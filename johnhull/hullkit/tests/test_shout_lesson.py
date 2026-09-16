"""Semantic figure tests against independent, frozen lesson references."""

import copy
import importlib
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = json.loads((ROOT / "docs/validation/section-26-12/browser-reference.json").read_text())
KEYS = ["shout_payoff", "shout_decision", "shout_boundary", "shout_comparison"]


@pytest.fixture(scope="module")
def lesson():
    return importlib.import_module("hullkit._shout_lesson")


@pytest.fixture(scope="module")
def figures(lesson):
    return lesson._figures()


def trace(fig, role, scenario):
    return next(t for t in fig.data if t.meta["role"] == role and t.meta["scenario"] == scenario)


def test_keys_metadata_and_every_menu(figures):
    assert list(figures) == KEYS
    for key, fig in figures.items():
        assert fig.layout.meta["section"] == "26.12"
        assert fig.layout.meta["figure"] == key
        assert fig.layout.meta["units"]["money"] == "currency"
        for menu in fig.layout.updatemenus:
            for button in menu.buttons:
                visibility, layout = button.args
                state = layout["meta"]["scenario"]
                assert visibility["visible"] == [t.meta["scenario"] == state for t in fig.data]
    assert len(figures["shout_payoff"].layout.updatemenus[0].buttons) == 2
    assert len(figures["shout_boundary"].layout.updatemenus[0].buttons) == 3
    assert len(figures["shout_comparison"].layout.updatemenus[0].buttons) == 7


def test_literal_payoffs_and_separate_positive_legs(figures):
    fig = figures["shout_payoff"]
    for pin in REFERENCE["payoff"]:
        for role in ("locked", "european", "cash", "reset_call"):
            t = trace(fig, role, f"shout{pin['shouted']:.0f}")
            assert t.y[list(t.x).index(pin["terminal"])] == pytest.approx(pin[role])


def assert_node(actual, expected):
    if expected["action"] == "expiry":
        assert actual["action"] == "maturity"
        assert actual["spot"] == pytest.approx(expected["spot"])
        assert actual["value"] == pytest.approx(expected["value"])
        for field in ("continuation", "immediate", "discounted_cash", "reset_atm"):
            assert actual[field] is None
        return
    for field, ref in [
        ("spot", "spot"),
        ("continuation", "continuation"),
        ("immediate", "shout"),
        ("discounted_cash", "cash"),
        ("reset_atm", "reset_european"),
        ("value", "value"),
    ]:
        if expected[ref] is None:
            assert actual[field] is None
        else:
            assert actual[field] == pytest.approx(expected[ref], abs=1e-11)
    assert actual["action"] == expected["action"]


def test_actual_tree_signed_legs_and_negative_control(figures):
    t = trace(figures["shout_decision"], "nodes", "positive-carry")
    for node, pin in zip(t.customdata, REFERENCE["small_tree"]["nodes"], strict=True):
        assert_node(node, pin)
        if node["action"] != "maturity":
            assert node["immediate"] == pytest.approx(node["discounted_cash"] + node["reset_atm"])
    bad = copy.deepcopy(t.customdata[1])
    bad["discounted_cash"] += 1
    bad["reset_atm"] -= 1
    with pytest.raises(AssertionError):
        assert_node(bad, REFERENCE["small_tree"]["nodes"][1])


def test_all_comparison_states_against_independent_prices(figures):
    fig = figures["shout_comparison"]
    for pin in REFERENCE["comparison"]:
        for role, ref, tol in [
            ("european", "european", 1e-8),
            ("shout", "shout_reference", 0.005),
            ("lookback", "lookback", 1e-8),
        ]:
            if pin[ref] is None:
                assert not any(
                    t.meta["role"] == role and t.meta["scenario"] == pin["market"] for t in fig.data
                )
            else:
                t = trace(fig, role, pin["market"])
                assert t.y[list(t.x).index(pin["spot"])] == pytest.approx(pin[ref], abs=tol)


def test_boundary_actual_layers_and_same_case_residual(lesson, figures):
    data = lesson._load_data()
    fig = figures["shout_boundary"]
    for case in data["boundaries"]["data"]:
        state = case["market"]
        for role in ("lower", "upper"):
            t = trace(fig, role, state)
            assert list(t.x) == case["remaining_times"]
            assert list(t.y) == case[role]
            assert t.mode == "markers"
        reference = next(r for r in REFERENCE["boundaries"] if r["market"] == state)
        t = trace(fig, "reference", state)
        np.testing.assert_allclose(
            t.y, np.interp(t.x, reference["remaining_times"], reference["levels"])
        )
        residual = trace(fig, "residual", state)
        assert list(residual.x) == [128, 256, 512, 1024]
        expected = [
            next(
                r["residual"]
                for r in c["rows"]
                if r["market"] == state and r["contract"] == "call" and r["spot_ratio"] == 1
            )
            for c in data["convergence"]["data"]
        ]
        assert list(residual.y) == expected
    upper = trace(fig, "upper", "positive-carry")
    ref = trace(fig, "reference", "positive-carry")
    i = list(upper.x).index(0.5)
    assert ref.y[i] - upper.y[i] == pytest.approx(0.126183816, abs=1e-8)


def test_refuse_stale_hashes(lesson, tmp_path):
    data = lesson._load_data()
    data["payoff"]["source_hashes"]["hullkit/src/hullkit/_shout.py"] = "0" * 64
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="stale"):
        lesson._load_data(path)


@pytest.mark.parametrize(
    "family", ["contract", "payoff", "decision_tree", "prices", "convergence", "boundaries"]
)
@pytest.mark.parametrize(
    "source",
    [
        "hullkit/src/hullkit/_shout.py",
        "scripts/build_shout_lesson_data.py",
        "scripts/build_shout_reference.py",
        "docs/validation/section-26-12/prices.json",
        "docs/validation/section-26-12/numerical-check.json",
        "hullkit/src/hullkit/exotics.py",
    ],
)
def test_refuse_missing_required_source_hash(lesson, tmp_path, family, source):
    data = lesson._load_data()
    del data[family]["source_hashes"][source]
    path = tmp_path / "missing-hash.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match=r"missing.*source"):
        lesson._load_data(path)


def test_figures_do_not_price_again(lesson, monkeypatch):
    from hullkit import _shout, exotics

    def forbidden(*args, **kwargs):
        raise AssertionError("figure construction must use saved prices")

    monkeypatch.setattr(_shout, "_tree", forbidden)
    monkeypatch.setattr(_shout, "_price", forbidden)
    monkeypatch.setattr(exotics, "lookback_fixed_call", forbidden)
    assert list(lesson._figures()) == KEYS
