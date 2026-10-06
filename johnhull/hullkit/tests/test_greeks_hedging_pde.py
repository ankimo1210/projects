"""Hull 19.7 equation19.4 checked with independent Crank-Nicolson prices."""

import numpy as np
import pytest
from hullkit import _greeks_hedging as greeks
from hullkit import bsm
from hullkit.fd import fd_vanilla


@pytest.mark.parametrize("kind,yield_rate", [("call", 0), ("put", 0.03)])
def test_greek_pde_from_independent_spatial_grid_and_time_differences(kind, yield_rate):
    residuals = []
    for space, steps in [(300, 400), (600, 800)]:
        value, delta, gamma = fd_vanilla(
            49,
            50,
            0.05,
            0.2,
            0.3846,
            q=yield_rate,
            kind=kind,
            n_s=space,
            n_t=steps,
            return_greeks=True,
        )

        def price(time, space=space, steps=steps):
            return fd_vanilla(
                49, 50, 0.05, 0.2, time, q=yield_rate, kind=kind, n_s=space, n_t=steps
            )

        theta = -(price(0.3846 + 0.0001) - price(0.3846 - 0.0001)) / 0.0002
        residuals.append(
            abs(
                greeks.greek_pde_residual(
                    49, 0.05, 0.2, value, theta, delta, gamma, yield_rate=yield_rate
                )
            )
        )
    assert residuals[1] < 2e-6
    assert residuals[1] < residuals[0] / 3


@pytest.mark.parametrize("kind,yield_rate", [("call", 0), ("put", 0.03)])
def test_analytic_greek_relation_and_calendar_theta_sign(kind, yield_rate):
    price = bsm.call_price if kind == "call" else bsm.put_price
    delta = bsm.call_delta if kind == "call" else bsm.put_delta
    args = (49, 50, 0.05, 0.2, 0.3846)
    value = float(price(*args, q=yield_rate))
    d = float(delta(*args, q=yield_rate))
    g = float(bsm.gamma(*args, q=yield_rate))
    th = greeks.theta_units(*args, kind=kind, yield_rate=yield_rate)["annual"]
    assert greeks.greek_pde_residual(
        49, 0.05, 0.2, value, th, d, g, yield_rate=yield_rate
    ) == pytest.approx(0, abs=1e-12)
    assert (
        abs(greeks.greek_pde_residual(49, 0.05, 0.2, value, -th, d, g, yield_rate=yield_rate)) > 1
    )


def test_delta_neutral_portfolio_relation_including_stock_and_bank():
    quantities = np.array([-200.0, 50.0])
    args = (49, 50, 0.05, 0.2, 0.3846)
    delta = np.array([bsm.call_delta(*args), bsm.put_delta(*args)])
    prices = np.array([bsm.call_price(*args), bsm.put_price(*args)])
    theta = np.array([bsm.call_theta(*args), bsm.put_theta(*args)])
    stock = greeks.delta_stock_hedge(quantities, delta)
    bank = 1000.0
    value = float(quantities @ prices) + stock * 49 + bank
    gamma = float(quantities.sum() * bsm.gamma(*args))
    annual_theta = float(quantities @ theta) + 0.05 * bank
    assert annual_theta + 0.5 * 0.2**2 * 49**2 * gamma == pytest.approx(0.05 * value, abs=1e-10)
    assert gamma < 0 and annual_theta > 0
    assert greeks.greek_pde_residual(49, 0.05, 0.2, value, annual_theta, 0, gamma) == pytest.approx(
        0, abs=1e-10
    )
