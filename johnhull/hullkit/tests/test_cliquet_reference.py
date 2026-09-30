"""Independent multitime cashflow references and synthetic contract diagnostics."""

import importlib

import pytest


def reference():
    return importlib.import_module("johnhull.scripts.build_cliquet_reference")


def test_density_integrals_and_deterministic_limits():
    value, error, legs = reference().integrate_cliquet(100, 0.05, 0.2, [1, 2], 0.03)
    assert value == pytest.approx(17.04933624301734, abs=1e-10)
    assert sum(legs) == value
    assert error < 1e-8
    put, _, _ = reference().integrate_cliquet(100, 0.05, 0.2, [1, 2], 0.03, "put")
    assert put == pytest.approx(13.262906618476658, abs=1e-10)
    deterministic, _, _ = reference().integrate_cliquet(100, 0.05, 0, [1, 2], 0.03)
    assert deterministic == pytest.approx(3.7864296245407036, abs=1e-12)
    assert reference().integrate_period(100, 0.05, 0.2, 1, 1)[0] == 0


def test_mc_uses_random_resets_and_each_payment_date():
    data = reference().build()
    assert len(data["cases"]) == 60
    assert len(data["mc"]) == 4
    for row in data["mc"]:
        assert row["paths"] == 524288
        assert row["price"] == pytest.approx(sum(row["components"]), abs=1e-10)
        assert abs(row["price"] - row["reference_price"]) < 6 * row["standard_error"]


def test_global_and_local_caps_and_termination_are_distinct():
    data = reference().build()
    rows = {row["key"]: row for row in data["complex"]["contracts"]}
    assert data["complex"]["market"]["r"] == data["complex"]["market"]["q"] == 0
    assert rows["simple"]["price"] > rows["global"]["price"] > rows["local"]["price"]
    assert rows["simple"]["price"] > rows["termination"]["price"]
    path = data["figure"]["reset"]
    assert path["strikes"] == path["stock"][:-1]
    assert any(path["call_payoffs"]) and any(path["put_payoffs"])


@pytest.mark.parametrize(
    "args", [(100, 0.05, 0.2, -1, 2), (100, 0.05, 0.2, 2, 1), (100, 0.05, 0.2, 0, 1, 0, "bad")]
)
def test_invalid_period_is_rejected(args):
    with pytest.raises(ValueError):
        reference().integrate_period(*args)
