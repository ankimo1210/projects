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
