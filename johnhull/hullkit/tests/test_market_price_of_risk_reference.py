"""Independent real-world quadrature of growth and loading, with no hullkit import."""

import importlib

import pytest


def reference():
    return importlib.import_module("johnhull.scripts.build_market_price_of_risk_reference")


def test_quadrature_recovers_lambda_for_every_claim_and_sign():
    d = reference().build()
    assert len(d["contracts"]) + len(d["negative_contracts"]) == 38
    for row in [*d["contracts"], *d["negative_contracts"]]:
        lam = (row["mu"] - row["r"]) / row["sigma"]
        assert row["implied_lambda"] == pytest.approx(lam, abs=1e-9)
        if row["kind"].endswith("put"):
            assert row["loading"] < 0
    assert d["figure"]["line"]["negative_lambda"] == pytest.approx(-0.1)


def test_riskless_portfolio_grows_at_r_and_residual_shrinks_like_sqrt_step():
    for row in reference().build()["riskless"]:
        assert row["instantaneous_growth"] == pytest.approx(0.05, abs=1e-9)
        ratio = row["residual_std_ratio"]
        assert ratio[0] / ratio[-1] == pytest.approx((0.1 / 1e-4) ** 0.5, rel=0.1)


def test_examples_consumption_caveat_and_mc():
    d = reference().build()
    assert d["examples"]["example_28_2"]["m2"] == pytest.approx(0.015, abs=1e-15)
    c = d["consumption"]
    assert c["derivative_lambda"] == pytest.approx(0.2, abs=1e-9)
    assert c["naive_spot_lambda"] == pytest.approx(1 / 30, abs=1e-12)
    for row in d["mc"]["worlds"]:
        assert row["paths"] == 524288
        assert abs(row["direct_mean"] - row["analytic_mean"]) < 6 * row["direct_se"]
        assert abs(row["log_std"] - row["analytic_log_std"]) < 6 * row["log_std_se"]


def test_reference_recomputation_does_not_use_hullkit(monkeypatch):
    from hullkit import bsm
    from hullkit import market_price_of_risk as mpr

    def forbidden(*args, **kwargs):
        raise AssertionError("production dependency reached")

    for module, names in (
        (bsm, ("call_price", "put_price", "call_delta", "put_delta", "gamma")),
        (
            mpr,
            (
                "market_price_of_risk",
                "required_growth",
                "riskless_holdings",
                "ito_growth_and_loading",
            ),
        ),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    reference().build.cache_clear()
    assert reference().build()["consumption"]["derivative_lambda"] == pytest.approx(0.2, abs=1e-9)
