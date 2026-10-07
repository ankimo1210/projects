"""Hull GE 15.9: Example 15.6 normal probabilities and nominal breakevens."""

import math

import pytest
from hullkit import _bsm_foundations as foundations
from hullkit import bsm
from hullkit._option_mechanics import option_cashflows
from scipy.integrate import quad


def test_example_15_6_all_source_cdf_prices_and_pv_strike():
    result = foundations.bsm_call_decomposition(42, 40, 0.1, 0.2, 0.5)
    assert [result["d1"], result["d2"]] == pytest.approx([0.7693, 0.6278], abs=0.00005, rel=0)
    cdfs = [foundations.standard_normal_probability(d) for d in [result["d1"], result["d2"]]]
    tails = [
        foundations.standard_normal_probability(d, upper=True) for d in [result["d1"], result["d2"]]
    ]
    assert cdfs == pytest.approx([0.7791, 0.7349], abs=0.00005, rel=0)
    assert tails == pytest.approx([0.2209, 0.2651], abs=0.00005, rel=0)
    assert 40 * math.exp(-0.05) == pytest.approx(38.049, abs=0.0005, rel=0)
    assert [result["price"], float(bsm.put_price(42, 40, 0.1, 0.2, 0.5))] == pytest.approx(
        [4.76, 0.81], abs=0.005, rel=0
    )


@pytest.mark.parametrize("x", [0, 0.7693, 2, 8])
def test_normal_cdf_and_direct_tail_against_independent_density_integral(x):
    upper = quad(
        lambda z: math.exp(-z * z / 2) / math.sqrt(2 * math.pi),
        x,
        math.inf,
        epsabs=1e-25,
        epsrel=1e-10,
    )[0]
    tail = foundations.standard_normal_probability(x, upper=True)
    assert tail == pytest.approx(upper, rel=1e-10, abs=1e-25)
    assert foundations.standard_normal_probability(-x) == pytest.approx(upper, rel=1e-10, abs=1e-25)
    assert foundations.standard_normal_probability(x) + tail == pytest.approx(1, abs=2e-16)


def test_source_nominal_breakevens_use_rounded_premiums_without_financing():
    call_terminal, put_terminal = 40 + 4.76, 40 - 0.81
    assert [call_terminal - 42, put_terminal - 42] == pytest.approx([2.76, -2.81], abs=1e-12)
    assert float(option_cashflows(call_terminal, 40, 4.76)["profit"]) == pytest.approx(0, abs=1e-12)
    assert float(option_cashflows(put_terminal, 40, 0.81, kind="put")["profit"]) == pytest.approx(
        0, abs=1e-12
    )
