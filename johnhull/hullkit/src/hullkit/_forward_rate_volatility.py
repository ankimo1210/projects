"""Private Hull §32.3 finite-tenor forward vol; common tenor and explicit units."""

import math

import numpy as np

from ._two_factor_rates import two_factor_loadings


def finite_tenor_forward_volatility(
    observation, start, end, a, b, sigma1, sigma2, rho, start_bond, end_bond
):
    """Instantaneous vol of R=(P(t,start)/P(t,end)-1)/(end-start).

    Ho–Lee is a=0,sigma2=0; HW1F uses sigma2=0; coupled HW2F uses both
    loadings. Normal vol is an absolute annual rate/sqrt(year). Black
    equivalent divides by a positive forward; zero/negative forwards have
    no unshifted Black equivalent. Neither is an implied cap volatility.
    The instantaneous-forward limit end→start is a different contract.
    """
    if (
        observation < 0
        or start < observation
        or end <= start
        or min(a, b, sigma1, sigma2) < 0
        or abs(rho) > 1
        or min(start_bond, end_bond) <= 0
    ):
        raise ValueError("ordered times, positive bonds and valid model parameters required")
    first = two_factor_loadings(a, b, start - observation)
    second = two_factor_loadings(a, b, end - observation)
    loading = np.array([second["B"] - first["B"], second["C"] - first["C"]])
    x = sigma1 * loading[0]
    y = sigma2 * loading[1]
    variance = (x + rho * y) ** 2 + (1 - rho * rho) * y * y
    tenor = end - start
    ratio = start_bond / end_bond
    forward = (ratio - 1) / tenor
    normal = ratio / tenor * math.sqrt(variance)
    return {
        "forward": forward,
        "tenor": tenor,
        "normal_vol": normal,
        "black_equivalent_vol": normal / forward if forward > 0 else None,
        "state_loadings": loading,
    }
