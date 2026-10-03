"""Reference math is independent of the premium API and production weights."""

import importlib
import math

import pytest


def builder():
    return importlib.import_module("johnhull.scripts.build_risk_premium_reference")


def test_reference_printed_pins_and_power_claims():
    data = builder().build()
    assert data["printed_pins"] == pytest.approx(
        {"example_28_1_lambda": 0.2, "example_28_2_lambda": -0.15, "example_28_2_return": 0.015},
        abs=1e-14,
    )
    assert len(data["cases"]) == 12 and len(data["powers"]) == 6
    for row in data["powers"]:
        a = row["power"]
        exact = 100**a * math.exp((a - 1) * 0.04 + 0.5 * a * (a - 1) * 0.2**2)
        assert row["price"] == pytest.approx(exact, rel=1e-11)
        assert row["drift"] == pytest.approx(0.04 + a * (0.09 - 0.04), abs=1e-13)
        assert row["loading"] == pytest.approx(a * 0.2)
    assert abs(sum(data["figure"]["hedge"]["risk"])) < 1e-14
    assert sum(data["figure"]["hedge"]["returns"]) == pytest.approx(0.04)


def test_measure_mc_includes_negative_loadings_and_paired_errors():
    data = builder().build()
    assert len(data["mc"]) == 4 and data["mc_paths"] == 262144 and data["seed"] == 281
    assert {row["loading"] > 0 for row in data["mc"]} == {False, True}
    for row in data["mc"]:
        assert abs(row["weighted_price"] - 100) <= 6 * row["weighted_se"]
        assert abs(row["direct_price"] - 100) <= 6 * row["direct_se"]
        assert abs(row["weight_mean"] - 1) <= 6 * row["weight_se"]
        assert abs(row["paired_difference"]) <= 6 * row["paired_se"]
        assert not math.isclose(row["weight_mean"], 1, abs_tol=1e-13)


def test_builder_cannot_call_production(monkeypatch):
    import hullkit.risk_premium as premium
    import hullkit.sde as sde

    def forbidden(*args, **kwargs):
        raise AssertionError("independent reference called production")

    monkeypatch.setattr(premium, "market_price_of_risk", forbidden)
    monkeypatch.setattr(premium, "required_return", forbidden)
    monkeypatch.setattr(sde, "girsanov_weights", forbidden)
    assert builder().build()["printed_pins"]["example_28_2_return"] == pytest.approx(0.015)
