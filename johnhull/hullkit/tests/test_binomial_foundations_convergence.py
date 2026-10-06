"""Hull GE section 13.9: recombination and even/odd European convergence."""

import math

import pytest
from hullkit import _binomial_foundations as foundations
from hullkit.bsm import put_price
from hullkit.trees import crr_params, crr_price
from scipy.integrate import quad
from scipy.stats import norm


def test_hull_five_step_coefficients_and_thirty_step_state_count():
    moments = foundations.crr_moments(0.3, 0.4, 0.05)
    assert [
        moments["up"],
        moments["down"],
        moments["mean"],
        moments["probability"],
    ] == pytest.approx([1.2089, 0.8272, 1.0202, 0.5056], abs=0.00005)
    up, down = crr_params(0.3, 2 / 30)
    result = foundations.terminal_binomial_value(50, 52, 0.05, 2, 30, up, down, kind="put")
    assert len(result["stock"]) == 31
    assert sum(result["weights"]) == pytest.approx(1, abs=1e-12)
    # Each sequence is distinct before recombination, while terminal states are only N+1.
    assert 2**30 == 1_073_741_824


@pytest.mark.parametrize("parity", [0, 1])
def test_even_and_odd_european_trees_converge_to_independent_payoff_integral(parity):
    z_strike = (math.log(52 / 50) - (0.05 - 0.3**2 / 2) * 2) / (0.3 * math.sqrt(2))
    integral = (
        math.exp(-0.1)
        * quad(
            lambda z: (
                (52 - 50 * math.exp((0.05 - 0.3**2 / 2) * 2 + 0.3 * math.sqrt(2) * z)) * norm.pdf(z)
            ),
            -math.inf,
            z_strike,
            epsabs=1e-10,
        )[0]
    )
    assert float(put_price(50, 52, 0.05, 0.3, 2)) == pytest.approx(integral, abs=1e-10)
    errors = []
    for base in [100, 500, 2000]:
        n = base + parity
        up, down = crr_params(0.3, 2 / n)
        direct = foundations.terminal_binomial_value(50, 52, 0.05, 2, n, up, down, kind="put")[
            "price"
        ]
        backward = crr_price(50, 52, 0.05, 0.3, 2, n, kind="put")
        assert direct == pytest.approx(backward, abs=2e-10)
        errors.append(abs(direct - integral))
    assert errors[-1] < 0.002
    assert errors[-1] < errors[0]
