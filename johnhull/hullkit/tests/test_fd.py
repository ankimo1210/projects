"""Tests for hullkit.fd (finite differences, Hull 11e Ch.21)."""

import pytest
from hullkit import bsm, fd, trees

# Hull Ch.21 American-put example parameters
AM = dict(S0=50.0, K=50.0, r=0.10, sigma=0.40, T=5.0 / 12.0)


def test_european_cn_matches_bsm():
    c = fd.fd_vanilla(100.0, 100.0, 0.05, 0.25, 1.0, kind="call", method="cn")
    p = fd.fd_vanilla(100.0, 100.0, 0.05, 0.25, 1.0, kind="put", method="cn")
    assert c == pytest.approx(bsm.call_price(100.0, 100.0, 0.05, 0.25, 1.0), abs=2e-2)
    assert p == pytest.approx(bsm.put_price(100.0, 100.0, 0.05, 0.25, 1.0), abs=2e-2)


def test_cn_at_least_as_accurate_as_implicit():
    target = bsm.call_price(100.0, 100.0, 0.05, 0.25, 1.0)
    err_cn = abs(fd.fd_vanilla(100.0, 100.0, 0.05, 0.25, 1.0, method="cn") - target)
    err_im = abs(fd.fd_vanilla(100.0, 100.0, 0.05, 0.25, 1.0, method="implicit") - target)
    assert err_cn <= err_im + 1e-12


def test_american_put_matches_crr():
    ref = trees.crr_price(**AM, N=500, kind="put", american=True)
    got = fd.fd_vanilla(**AM, kind="put", american=True, method="cn")
    assert got == pytest.approx(ref, abs=2e-2)
    # American >= European
    assert got >= fd.fd_vanilla(**AM, kind="put", method="cn") - 1e-9


def test_dividend_yield_consistency():
    c = fd.fd_vanilla(100.0, 95.0, 0.04, 0.3, 0.75, q=0.02, kind="call", method="cn")
    assert c == pytest.approx(bsm.call_price(100.0, 95.0, 0.04, 0.3, 0.75, q=0.02), abs=2e-2)


@pytest.mark.parametrize(("kind", "strike"), [("call", 500.0), ("put", 20.0)])
def test_grid_expands_for_strike_outside_default_domain(kind, strike):
    price = fd.fd_vanilla(100.0, strike, 0.05, 1.0, 2.0, kind=kind, n_s=300, n_t=300)
    reference_fn = bsm.call_price if kind == "call" else bsm.put_price
    reference = reference_fn(100.0, strike, 0.05, 1.0, 2.0)
    assert price >= 0.0
    assert price == pytest.approx(reference, abs=0.15)


def test_boundary_extraction_for_american_put():
    price, taus, boundary = fd.fd_vanilla(
        **AM, kind="put", american=True, method="cn", return_boundary=True
    )
    assert price == pytest.approx(
        fd.fd_vanilla(**AM, kind="put", american=True, method="cn"), abs=1e-12
    )
    assert len(taus) == len(boundary)
    # boundary stays strictly below strike and is positive
    assert all(0.0 < b < AM["K"] for b in boundary)


def test_validation_errors():
    with pytest.raises(ValueError):
        fd.fd_vanilla(100.0, 100.0, 0.05, 0.2, 1.0, kind="cal")
    with pytest.raises(ValueError):
        fd.fd_vanilla(100.0, 100.0, 0.05, 0.2, 1.0, method="explicit")


def test_fd_greeks_european_match_bsm():
    price, delta, gamma = fd.fd_vanilla(
        100.0, 100.0, 0.05, 0.25, 1.0, method="cn", return_greeks=True
    )
    assert price == pytest.approx(bsm.call_price(100.0, 100.0, 0.05, 0.25, 1.0), abs=2e-2)
    assert delta == pytest.approx(bsm.call_delta(100.0, 100.0, 0.05, 0.25, 1.0), abs=5e-3)
    assert gamma == pytest.approx(bsm.gamma(100.0, 100.0, 0.05, 0.25, 1.0), abs=2e-3)


def test_fd_greeks_american_put_grid_stable_and_match_crr():
    # Hull Ch.21 American put. FD grid Greeks are stable across refinement and
    # agree with a *converged* CRR reference. (CRR gamma via bumping needs a
    # large N — it oscillates with N — so we use N=6000 as the reference.)
    P = dict(S0=50.0, K=50.0, r=0.10, sigma=0.40, T=5.0 / 12.0)
    _, delta_a, gamma_a = fd.fd_vanilla(
        **P, kind="put", american=True, method="cn", n_s=150, n_t=150, return_greeks=True
    )
    _, delta_b, gamma_b = fd.fd_vanilla(
        **P, kind="put", american=True, method="cn", n_s=600, n_t=600, return_greeks=True
    )
    # grid-stable readout (the value of reading Greeks off a converged FD grid)
    assert delta_a == pytest.approx(delta_b, abs=1e-3)
    assert gamma_a == pytest.approx(gamma_b, abs=1e-3)
    # converged CRR reference (N=6000, bump h=1.0)
    h = 1.0
    pu = trees.crr_price(51.0, 50.0, 0.10, 0.40, P["T"], 6000, kind="put", american=True)
    p0 = trees.crr_price(50.0, 50.0, 0.10, 0.40, P["T"], 6000, kind="put", american=True)
    pd_ = trees.crr_price(49.0, 50.0, 0.10, 0.40, P["T"], 6000, kind="put", american=True)
    assert delta_b == pytest.approx((pu - pd_) / (2 * h), abs=5e-3)
    assert gamma_b == pytest.approx((pu - 2 * p0 + pd_) / h**2, abs=1e-3)
