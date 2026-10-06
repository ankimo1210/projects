"""Hull GE 15.6: source symbolic contracts and independent PDE/integral checks."""

import math

import pytest
from hullkit import _bsm_foundations as foundations
from scipy.integrate import quad
from scipy.stats import lognorm


def finite_derivatives(value, s, tau):
    dx, dt = .001, .00001
    f = value(s, tau)
    ft = (value(s, tau-dt)-value(s, tau+dt))/(2*dt)
    fs = (value(s+dx, tau)-value(s-dx, tau))/(2*dx)
    fss = (value(s+dx, tau)-2*f+value(s-dx, tau))/dx**2
    return f, ft, fs, fss


@pytest.mark.parametrize("s,k,r,tau", [(40, 42, .1, .5), (100, 90, -.02, 2), (50, 50, 0, 1)])
def test_source_forward_contract_and_independent_finite_pde(s, k, r, tau):
    def value(stock, time):
        return foundations.forward_contract_value(stock, k, r, time)
    f, ft, fs, fss = finite_derivatives(value, s, tau)
    assert f == pytest.approx(s-k*math.exp(-r*tau))
    assert foundations.bsm_pde_residual(s, r, .3, f, ft, fs, fss) == pytest.approx(0, abs=1e-7)


def test_inverse_stock_contract_against_negative_moment_integral_and_pde():
    s, r, sigma, tau = 40, .05, .3, 2
    density = lognorm(s=sigma*math.sqrt(tau), scale=s*math.exp((r-sigma**2/2)*tau))
    integral = math.exp(-r*tau)*quad(lambda stock: density.pdf(stock)/stock, 0, math.inf, epsabs=1e-11)[0]
    def value(stock, time):
        return foundations.inverse_stock_value(stock, r, sigma, time)
    f, ft, fs, fss = finite_derivatives(value, s, tau)
    assert f == pytest.approx(integral, abs=1e-11)
    assert f == pytest.approx(math.exp((sigma**2-2*r)*tau)/s)
    assert foundations.bsm_pde_residual(s, r, sigma, f, ft, fs, fss) == pytest.approx(0, abs=2e-9)


@pytest.mark.parametrize("s", [40, 160])
def test_perpetual_contract_against_first_passage_density(s):
    h, payment, r, sigma = 80, 10, .05, .3
    distance, drift = math.log(h/s), r-sigma**2/2
    def discounted_density(t):
        exponent = -(distance-drift*t)**2/(2*sigma**2*t)-r*t
        return payment*abs(distance)*math.exp(exponent)/(sigma*math.sqrt(2*math.pi*t**3))
    integral = quad(discounted_density, 0, math.inf, epsabs=1e-10)[0]
    price = foundations.perpetual_hit_value(s, h, payment, r, sigma)
    source = payment*s/h if s < h else payment*(s/h)**(-2*r/sigma**2)
    assert price == pytest.approx(source)
    assert price == pytest.approx(integral, abs=1e-9)
    f, ft, fs, fss = finite_derivatives(lambda stock, time: foundations.perpetual_hit_value(stock, h, payment, r, sigma), s, 1)
    assert foundations.bsm_pde_residual(s, r, sigma, f, ft, fs, fss) == pytest.approx(0, abs=1e-6)


def test_source_exponential_stock_is_not_pde_solution():
    f = math.exp(2)
    assert abs(foundations.bsm_pde_residual(2, .05, .3, f, 0, f, f)) > 1


@pytest.mark.parametrize("mu", [-.3, .7])
def test_ito_delta_hedge_cancels_stock_drift_and_diffusion(mu):
    drift, diffusion = foundations.delta_hedged_coefficients(40, mu, .3, -.8, .4, .02)
    # Independent generator of the hedged value has no mu term.
    assert drift == pytest.approx(-.8+.5*.3**2*40**2*.02, abs=1e-12)
    assert diffusion == pytest.approx(0, abs=1e-12)


def test_perpetual_source_boundary_conditions_and_domain():
    assert foundations.perpetual_hit_value(80, 80, 10, .05, .3) == pytest.approx(10)
    assert foundations.perpetual_hit_value(1e-8, 80, 10, .05, .3) < 1e-8
    assert foundations.perpetual_hit_value(1e12, 80, 10, .05, .3) < 1e-8
    with pytest.raises(ValueError):
        foundations.perpetual_hit_value(40, 80, 10, -.01, .3)


def test_inverse_terminal_condition_and_invalid_horizon():
    assert foundations.inverse_stock_value(40, .05, .3, 0) == pytest.approx(1/40)
    with pytest.raises(ValueError):
        foundations.inverse_stock_value(40, .05, .3, -1)
