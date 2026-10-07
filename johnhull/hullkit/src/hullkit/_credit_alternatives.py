"""Private computational scope for Hull §25.11 static credit alternatives.

PDs are cumulative Q inputs for pricing; rates/hazards annual fractions. Factor
loading/recovery functions below are explicitly specified illustrative models,
not a reproduction of every parameterization in Andersen/Sidenius. Dynamic
structural, jump-intensity and top-down models require separate research design.
"""

from itertools import pairwise

import numpy as np
from scipy.optimize import brentq, linprog
from scipy.stats import norm

from . import credit_portfolio as cp
from ._credit_portfolio_extensions import _factor_integral, _normal_transition_points


def heterogeneous_factor_counts(cumulative_pds, loadings, *, nodes=60):
    """ASB count recursion with individual signed loadings and adaptive factor integration.

    Equal-sized names and nondegenerate Gaussian residuals |a_i|<1. Returned
    factor/weights are a diagnostic pilot grid, not the final integration weights.
    """
    pd = np.asarray(cumulative_pds, dtype=float)
    a = np.broadcast_to(np.asarray(loadings, dtype=float), pd.shape)
    if (
        pd.ndim != 1
        or pd.size == 0
        or not np.isfinite(pd).all()
        or np.any((pd < 0) | (pd > 1))
        or not np.isfinite(a).all()
        or np.any(abs(a) >= 1)
    ):
        raise ValueError("PD vector in [0,1] and loadings strictly in (-1,1) required")
    factor, weights = cp.gauss_hermite_factor(nodes)
    threshold = norm.ppf(pd)

    def conditional(f):
        return norm.cdf((threshold - a * f) / np.sqrt(1 - a * a))

    def integrand(f):
        probabilities = conditional(f)
        return np.r_[cp.heterogeneous_default_pmf(probabilities), probabilities]

    values, error = _factor_integral(
        integrand, points=np.r_[factor, _normal_transition_points(threshold, a)]
    )
    integrated = values[pd.size + 1 :]
    if np.max(abs(integrated - pd)) > 5e-10:
        raise ValueError("factor integration failed to preserve marginal default probabilities")
    return {
        "pmf": values[: pd.size + 1],
        "conditional_pds": conditional(factor[:, None]),
        "factor": factor,
        "weights": weights,
        "integrated_pds": integrated,
        "integration_error": error,
    }


def double_t_counts(names, cumulative_pd, rho, *, nu=4, nodes=200, threshold_nodes=240):
    """Double-t threshold and full count PMF with adaptive integration in factor CDF space.

    Factor and residual t variables have independent scales and unit variance.
    Node parameters set pilot partitions; fixed-node threshold biases are avoided.
    """
    if (
        not np.isfinite([names, cumulative_pd, rho, nu, nodes, threshold_nodes]).all()
        or int(names) != names
        or names < 1
        or not 0 < cumulative_pd < 1
        or not 0 <= rho < 1
        or nu <= 2
        or min(nodes, threshold_nodes) < 1
        or int(nodes) != nodes
        or int(threshold_nodes) != threshold_nodes
    ):
        raise ValueError(
            "positive integer grids/names, interior PD, rho in [0,1) and nu>2 required"
        )
    if rho == 0:
        return {
            "threshold": cp.standardized_t_ppf(cumulative_pd, nu),
            "pmf": cp.binomial_pmf(int(names), cumulative_pd),
            "marginal_pd": cumulative_pd,
        }
    a, noise = np.sqrt(rho), np.sqrt(1 - rho)

    def integrate(threshold, count=False):
        pilot, _ = np.polynomial.legendre.leggauss(
            min(int(nodes if count else threshold_nodes), 32)
        )
        anchors = np.r_[
            (pilot + 1) / 2,
            cp.standardized_t_cdf(
                threshold / a + np.array([-12, -4, -1, 0, 1, 4, 12]) * noise / a, nu
            ),
        ]

        def integrand(u):
            factor = cp.standardized_t_ppf(u, nu)
            pd = cp.standardized_t_cdf((threshold - a * factor) / noise, nu)
            return np.r_[cp.binomial_pmf(int(names), pd), pd] if count else pd

        return _factor_integral(
            integrand, points=anchors, bounds=(0.0, 1.0), density=lambda _: 1.0
        )[0]

    lower, upper = -8.0, 8.0
    while integrate(lower) > cumulative_pd:
        lower *= 2
    while integrate(upper) < cumulative_pd:
        upper *= 2
    threshold = brentq(lambda x: float(integrate(x)) - cumulative_pd, lower, upper, xtol=1e-12)
    values = integrate(threshold, count=True)
    if abs(values[-1] - cumulative_pd) > 5e-10:
        raise ValueError("double-t integration failed to preserve the marginal PD")
    return {"threshold": threshold, "pmf": values[:-1], "marginal_pd": float(values[-1])}


def _factor_loading(factor, loading_function):
    a = np.asarray(loading_function(factor), dtype=float)
    if not np.isfinite(a).all() or np.any(abs(a) >= 1):
        raise ValueError("factor loadings must lie strictly in (-1,1)")
    return a


def factor_dependent_pool(
    names, cumulative_pd, loading_function, recovery_function, attach, detach, *, nodes=120
):
    """Illustrative static terminal loss with loading/recovery functions of the factor.

    X=a(F)F+sqrt(1-a(F)^2)Z is generally not standard normal. Recalibrate its
    threshold to the supplied marginal PD using adaptive integration before
    adaptively integrating conditional count losses. Recovery_given_default is PD-weighted;
    preserving PD alone does not preserve single-name CDS quotes when R changes.
    """
    if (
        not np.isfinite([names, cumulative_pd, attach, detach]).all()
        or int(names) != names
        or names < 1
        or not 0 < cumulative_pd < 1
        or not 0 <= attach < detach <= 1
    ):
        raise ValueError("positive integer names, interior PD and a valid tranche required")
    factor, _weights = cp.gauss_hermite_factor(nodes)
    _factor_loading(factor, loading_function)
    recovery = np.broadcast_to(np.asarray(recovery_function(factor), dtype=float), factor.shape)
    if not np.isfinite(recovery).all() or np.any((recovery < 0) | (recovery > 1)):
        raise ValueError("factor-dependent recoveries must lie in [0,1]")

    def transitions(threshold):
        grid = np.linspace(-12, 12, 65)

        def residual(f):
            return float(_factor_loading(f, loading_function)) * f - threshold

        difference = np.array([residual(float(f)) for f in grid])
        anchors = []
        for lo, hi, dlo, dhi in zip(
            grid[:-1], grid[1:], difference[:-1], difference[1:], strict=True
        ):
            if dlo * dhi < 0:
                center = brentq(residual, lo, hi)
                load = float(_factor_loading(center, loading_function))
                derivative = (residual(center + 1e-5) - residual(center - 1e-5)) / 2e-5
                width = np.sqrt(1 - load * load) / max(abs(derivative), 1e-8)
                anchors.extend(center + width * np.array([-8, -4, -1, 0, 1, 4, 8]))
        return anchors

    def conditional(f, threshold):
        load = _factor_loading(f, loading_function)
        return norm.cdf((threshold - load * f) / np.sqrt(1 - load * load))

    def cdf(threshold):
        return float(
            _factor_integral(lambda f: conditional(f, threshold), points=transitions(threshold))[0]
        )

    lower, upper = -8.0, 8.0
    while cdf(lower) > cumulative_pd:
        lower *= 2
    while cdf(upper) < cumulative_pd:
        upper *= 2
    threshold = brentq(lambda x: cdf(x) - cumulative_pd, lower, upper, xtol=1e-12)
    count = np.arange(int(names) + 1)

    def integrand(f):
        probability = float(conditional(f, threshold))
        r = float(recovery_function(f))
        if not np.isfinite(r) or not 0 <= r <= 1:
            raise ValueError("factor-dependent recoveries must lie in [0,1]")
        pmf = cp.binomial_pmf(int(names), probability)
        loss = np.clip((count * (1 - r) / names - attach) / (detach - attach), 0, 1)
        return np.array([probability, probability * r, pmf @ loss])

    values, error = _factor_integral(integrand, points=transitions(threshold))
    if abs(values[0] - cumulative_pd) > 5e-10:
        raise ValueError("factor integration failed to preserve the marginal PD")
    return {
        "threshold": threshold,
        "marginal_pd": float(values[0]),
        "expected_tranche_loss": float(values[2]),
        "recovery_given_default": float(values[1] / values[0]),
        "integration_error": error,
    }


def _mixture_components(hazards, recovery, rate, maturity, boundaries, names, frequency):
    h = np.asarray(hazards, dtype=float)
    bounds = np.asarray(boundaries, dtype=float)
    if (
        h.ndim != 1
        or h.size == 0
        or not np.isfinite(h).all()
        or np.any(h < 0)
        or bounds.ndim != 1
        or bounds.size < 2
        or not np.isfinite(bounds).all()
        or bounds[0] != 0
        or bounds[-1] > 1
        or np.any(np.diff(bounds) <= 0)
        or not np.isfinite(rate)
    ):
        raise ValueError(
            "nonnegative finite hazard grid and increasing tranche boundaries required"
        )
    components = np.empty((h.size, bounds.size - 1, 3))
    for i, hazard in enumerate(h):
        for j, (lo, hi) in enumerate(pairwise(bounds)):
            val = cp.cdo_tranche_valuation(
                float(hazard),
                recovery,
                rate,
                maturity,
                float(lo),
                float(hi),
                names,
                0,
                freq=frequency,
                m=1,
            )
            components[i, j] = val.annuity, val.accrual, val.protection
    return components


def _mixture_output(components, weights):
    values = np.einsum("i,ijk->jk", weights, components)
    a, b, c = values.T
    return {
        "annuity": a,
        "accrual": b,
        "protection": c,
        "spread": c / (a + b),
        "component_legs": components,
    }


def hazard_mixture_legs(
    hazards, weights, recovery, rate, maturity, boundaries, names, *, frequency=4
):
    """Static homogeneous implied-copula model: common lifetime hazard drawn from a finite mixture.

    Defaults are conditionally independent given hazard. Mixture prices legs, then
    takes C/(A+B); it does not average component par spreads. Weights are probability
    masses and must sum to one. This is not a term-structure or dynamic-spread model.
    """
    components = _mixture_components(
        hazards, recovery, rate, maturity, boundaries, names, frequency
    )
    w = np.asarray(weights, dtype=float)
    if (
        w.shape != (components.shape[0],)
        or not np.isfinite(w).all()
        or np.any(w < 0)
        or not np.isclose(w.sum(), 1, rtol=0, atol=1e-12)
    ):
        raise ValueError("nonnegative mixture probability weights summing to one required")
    return _mixture_output(components, w)


def calibrate_hazard_mixture(
    hazards,
    quotes,
    recovery,
    rate,
    maturity,
    boundaries,
    names,
    *,
    frequency=4,
    quote_kinds=None,
    fixed_coupons=None,
):
    """Feasible nonnegative mixture probabilities on a fixed hazard grid by linear quote equations.

    Quotes are spread fractions or upfront fractions of tranche principal, with
    specified running coupons for upfront quotes. No market data/prior or smoothness
    penalty is invented. Full linear rank is sufficient for unique weights; otherwise
    the feasible solution reported by the solver need not be unique.
    """
    components = _mixture_components(
        hazards, recovery, rate, maturity, boundaries, names, frequency
    )
    q = np.asarray(quotes, dtype=float)
    kinds = (
        np.full(components.shape[1], "spread") if quote_kinds is None else np.asarray(quote_kinds)
    )
    coupons = np.zeros(q.shape) if fixed_coupons is None else np.asarray(fixed_coupons, dtype=float)
    if (
        q.shape != (components.shape[1],)
        or coupons.shape != q.shape
        or kinds.shape != q.shape
        or not np.isfinite(q).all()
        or not np.isfinite(coupons).all()
        or np.any(coupons < 0)
        or np.any(~np.isin(kinds, ["upfront", "spread"]))
        or np.any(q[kinds == "spread"] < 0)
    ):
        raise ValueError(
            "matching finite spread/upfront quotes and nonnegative running coupons required"
        )
    running = np.where(kinds == "spread", q, coupons)
    target = np.where(kinds == "upfront", q, 0.0)
    duration = components[:, :, 0] + components[:, :, 1]
    residual = components[:, :, 2] - running * duration
    equations = np.vstack([np.ones(components.shape[0]), residual.T])
    rhs = np.r_[1, target]
    scale = np.maximum(np.max(abs(equations), axis=1), np.maximum(abs(rhs), 1e-12))
    normalized = equations / scale[:, None]
    result = linprog(
        np.zeros(components.shape[0]),
        A_eq=normalized,
        b_eq=rhs / scale,
        bounds=(0, None),
        method="highs",
        options={"primal_feasibility_tolerance": 1e-9, "dual_feasibility_tolerance": 1e-9},
    )
    if not result.success:
        raise ValueError("quotes have no feasible nonnegative mixture on the supplied hazard grid")
    if np.max(abs(normalized @ result.x - rhs / scale)) > 2e-9:
        raise ValueError("mixture quote residual exceeds solver tolerance")
    output = _mixture_output(components, result.x)
    model = np.where(
        kinds == "spread",
        output["spread"],
        output["protection"] - coupons * (output["annuity"] + output["accrual"]),
    )
    rank = int(np.linalg.matrix_rank(normalized))
    output.update(
        {
            "weights": result.x,
            "model_quotes": model,
            "linear_rank": rank,
            "unique_linear_solution": rank == components.shape[0],
        }
    )
    return output
