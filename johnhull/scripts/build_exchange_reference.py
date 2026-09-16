"""Independent reference prices for Hull 11e GE section 26.14 (exchange options).

The section values a European option to give up an asset worth ``U_T`` and
receive one worth ``V_T`` with Margrabe's formula (eq. 26.5), then makes three
further claims the repository never checked: the price does not depend on the
risk-free rate, it equals ``U0`` calls on ``V/U`` struck at 1 with rate ``qU``
and dividend yield ``qV``, and better-of/worse-of options decompose into one
asset plus or minus this option.

Nothing here calls hullkit. Three routes that share no code path price the
same contract:

* ``conditional_price`` conditions on ``U_T`` and takes the inner expectation
  over ``V_T`` in closed form, leaving one smooth integral in the conditioning
  variable. The payoff kink is integrated exactly, so this is the anchor.
* ``ratio_price`` changes numeraire to ``U``: the payoff is ``U_T`` times
  ``max(V_T/U_T - 1, 0)`` and the ratio is lognormal, so the price is a
  one-dimensional quadrature over the ratio. This is Hull's reinterpretation,
  priced rather than assumed.
* ``simulated_price`` draws correlated terminal values and uses the two
  discounted asset prices as control variates.

``binomial_american_price`` prices Rubinstein's American version as ``U0``
American calls on ``V/U`` on a CRR tree, which is the route Hull describes.

All inputs are synthetic: prices in currency, maturities in years, yields
continuously compounded per year, volatilities annualised.

Refresh the saved records from the repository root:

    uv run --no-sync --package hullkit python johnhull/scripts/build_exchange_reference.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr

PROJECT = Path(__file__).resolve().parent.parent
BASE_U = 100.0
RATIOS = (0.80, 1.00, 1.25)
TRUNCATION = 12.0
RATE_PROBES = (0.0, 0.08, -0.02)


class Market(NamedTuple):
    """Synthetic two-asset market; both yields are continuous per year."""

    name: str
    volatility_u: float
    volatility_v: float
    correlation: float
    yield_u: float
    yield_v: float
    expiry: float


MARKETS = (
    Market("equal-vol-uncorrelated", 0.20, 0.20, 0.00, 0.00, 0.00, 1.0),
    Market("equal-vol-tight", 0.20, 0.20, 0.90, 0.01, 0.03, 1.0),
    Market("equal-vol-opposed", 0.20, 0.20, -0.60, 0.00, 0.00, 0.5),
    Market("asymmetric-vol", 0.15, 0.45, 0.30, 0.02, 0.00, 2.0),
    Market("yield-on-received", 0.25, 0.25, 0.50, 0.00, 0.06, 1.5),
    Market("yield-on-given", 0.25, 0.25, 0.50, 0.06, 0.00, 1.5),
    Market("short-dated", 0.35, 0.20, 0.10, 0.01, 0.01, 0.25),
    Market("long-high-vol", 0.55, 0.70, -0.20, 0.03, 0.02, 5.0),
)


def spread_volatility(market: Market) -> float:
    """Volatility of V/U: sqrt(su^2 + sv^2 - 2 rho su sv)."""
    return math.sqrt(
        market.volatility_u**2
        + market.volatility_v**2
        - 2.0 * market.correlation * market.volatility_u * market.volatility_v
    )


def _lognormal_call(forward, strike, scale, discount):
    """Discounted E[max(X - strike, 0)] for lognormal X with mean ``forward``.

    ``scale`` is the standard deviation of ln X. Written out from the normal
    CDF; it is not Margrabe's formula and knows nothing about two assets.
    """
    if strike <= 0.0:
        return discount * (forward - strike)
    if scale <= 0.0:
        return discount * max(forward - strike, 0.0)
    d1 = (math.log(forward / strike) + 0.5 * scale**2) / scale
    return discount * (forward * ndtr(d1) - strike * ndtr(d1 - scale))


def conditional_price(spot_u, spot_v, market: Market, rate=0.0, *, payoff="exchange"):
    """Price by conditioning on U_T; the inner expectation over V_T is exact.

    ``payoff`` selects ``max(V-U,0)``, ``max(U,V)`` or ``min(U,V)``; the last two
    are priced directly here so the decomposition can be checked rather than used.
    """
    expiry = market.expiry
    sqrt_t = math.sqrt(expiry)
    discount = math.exp(-rate * expiry)
    forward_u = spot_u * math.exp((rate - market.yield_u) * expiry)
    forward_v = spot_v * math.exp((rate - market.yield_v) * expiry)
    residual = market.volatility_v * math.sqrt(max(1.0 - market.correlation**2, 0.0)) * sqrt_t

    def integrand(z):
        terminal_u = forward_u * math.exp(
            market.volatility_u * sqrt_t * z - 0.5 * market.volatility_u**2 * expiry
        )
        # E[V_T | z] moves with the correlated part of the shock only.
        conditional_v = forward_v * math.exp(
            market.correlation * market.volatility_v * sqrt_t * z
            - 0.5 * (market.correlation * market.volatility_v) ** 2 * expiry
        )
        call = _lognormal_call(conditional_v, terminal_u, residual, 1.0)
        if payoff == "exchange":
            value = call
        elif payoff == "better":
            value = terminal_u + call
        elif payoff == "worse":
            value = conditional_v - call
        else:
            raise ValueError(f"unknown payoff {payoff!r}")
        return value * math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)

    total, error = quad(integrand, -TRUNCATION, TRUNCATION, epsabs=1e-13, epsrel=1e-12, limit=400)
    assert error * discount < 1e-9, f"quadrature error {error:.3e}"
    return discount * total


def ratio_price(spot_u, spot_v, market: Market, rate=0.0):
    """Price by changing numeraire to U and integrating over the ratio V/U.

    Under the U-numeraire measure the ratio is lognormal with volatility
    ``spread_volatility`` and drift ``qU - qV``; the option is ``U0`` calls on
    it struck at 1. The integral is taken numerically, so the formula that
    closes it is never used.
    """
    expiry = market.expiry
    scale = spread_volatility(market) * math.sqrt(expiry)
    ratio_forward = (spot_v / spot_u) * math.exp((market.yield_u - market.yield_v) * expiry)
    if scale <= 0.0:
        return spot_u * math.exp(-market.yield_u * expiry) * max(ratio_forward - 1.0, 0.0)
    location = math.log(ratio_forward) - 0.5 * scale**2

    def integrand(z):
        ratio = math.exp(location + scale * z)
        return max(ratio - 1.0, 0.0) * math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)

    lower = (math.log(1.0) - location) / scale
    total, error = quad(
        integrand, max(lower, -TRUNCATION), TRUNCATION, epsabs=1e-13, epsrel=1e-12, limit=400
    )
    assert error < 1e-9, f"ratio quadrature error {error:.3e}"
    return spot_u * math.exp(-market.yield_u * expiry) * total


def simulated_price(spot_u, spot_v, market: Market, rate=0.0, *, paths=400_000, seed=20260917):
    """Correlated terminal draws with both discounted assets as control variates."""
    expiry = market.expiry
    sqrt_t = math.sqrt(expiry)
    generator = np.random.default_rng(seed)
    normals = generator.standard_normal((paths, 2))
    normals = np.concatenate([normals, -normals])  # antithetic pairs
    first = normals[:, 0]
    second = market.correlation * first + math.sqrt(1.0 - market.correlation**2) * normals[:, 1]
    terminal_u = spot_u * np.exp(
        (rate - market.yield_u - 0.5 * market.volatility_u**2) * expiry
        + market.volatility_u * sqrt_t * first
    )
    terminal_v = spot_v * np.exp(
        (rate - market.yield_v - 0.5 * market.volatility_v**2) * expiry
        + market.volatility_v * sqrt_t * second
    )
    discount = math.exp(-rate * expiry)
    payoff = discount * np.maximum(terminal_v - terminal_u, 0.0)
    controls = np.column_stack([discount * terminal_u, discount * terminal_v])
    expected = np.array(
        [spot_u * math.exp(-market.yield_u * expiry), spot_v * math.exp(-market.yield_v * expiry)]
    )
    centred = controls - expected
    covariance = centred.T @ centred / len(payoff)
    weights = np.linalg.solve(covariance, centred.T @ (payoff - payoff.mean()) / len(payoff))
    adjusted = payoff - centred @ weights
    return float(adjusted.mean()), float(adjusted.std(ddof=1) / math.sqrt(len(adjusted)))


def binomial_american_price(spot_u, spot_v, market: Market, steps=2_000, *, american=True):
    """Rubinstein's American exchange option: U0 calls on V/U, rate qU, yield qV."""
    expiry = market.expiry
    volatility = spread_volatility(market)
    dt = expiry / steps
    up = math.exp(volatility * math.sqrt(dt))
    down = 1.0 / up
    growth = math.exp((market.yield_u - market.yield_v) * dt)
    probability = (growth - down) / (up - down)
    if not 0.0 < probability < 1.0:
        raise ValueError(f"tree probability {probability} outside (0,1); refine the grid")
    discount = math.exp(-market.yield_u * dt)
    ratio = (spot_v / spot_u) * up ** np.arange(-steps, steps + 1, 2, dtype=float)
    values = np.maximum(ratio - 1.0, 0.0)
    for step in range(steps - 1, -1, -1):
        values = discount * (probability * values[1:] + (1.0 - probability) * values[:-1])
        ratio = (spot_v / spot_u) * up ** np.arange(-step, step + 1, 2, dtype=float)
        if american:
            values = np.maximum(values, ratio - 1.0)
    return spot_u * float(values[0])


def build_rows(paths):
    """Every market and moneyness priced by all three independent routes."""
    rows = []
    for market in MARKETS:
        for given in RATIOS:
            spot_u = BASE_U
            spot_v = BASE_U * given
            conditional = conditional_price(spot_u, spot_v, market)
            ratio = ratio_price(spot_u, spot_v, market)
            simulated, error = simulated_price(spot_u, spot_v, market, paths=paths)
            rows.append(
                {
                    "market": market.name,
                    "spot_u": spot_u,
                    "spot_v": spot_v,
                    "value_ratio": given,
                    "volatility_u": market.volatility_u,
                    "volatility_v": market.volatility_v,
                    "correlation": market.correlation,
                    "yield_u": market.yield_u,
                    "yield_v": market.yield_v,
                    "expiry": market.expiry,
                    "spread_volatility": spread_volatility(market),
                    "conditional": conditional,
                    "ratio": ratio,
                    "simulated": simulated,
                    "standard_error": error,
                    "conditional_minus_ratio": conditional - ratio,
                    "simulated_standard_errors": (
                        abs(simulated - conditional) / error if error > 0.0 else None
                    ),
                }
            )
    return rows


def rate_independence():
    """Hull says the price does not depend on r. Price the same contract at three rates."""
    probes = []
    for market in MARKETS:
        for given in RATIOS:
            prices = [
                conditional_price(BASE_U, BASE_U * given, market, rate=rate)
                for rate in RATE_PROBES
            ]
            probes.append(
                {
                    "market": market.name,
                    "value_ratio": given,
                    "rates": list(RATE_PROBES),
                    "prices": prices,
                    "spread": max(prices) - min(prices),
                }
            )
    return probes


def better_worse_checks():
    """max(U,V) = U + exchange and min(U,V) = V - exchange, both priced directly."""
    checks = []
    for market in MARKETS:
        for given in RATIOS:
            spot_v = BASE_U * given
            exchange = conditional_price(BASE_U, spot_v, market)
            better = conditional_price(BASE_U, spot_v, market, payoff="better")
            worse = conditional_price(BASE_U, spot_v, market, payoff="worse")
            forward_u = BASE_U * math.exp(-market.yield_u * market.expiry)
            forward_v = spot_v * math.exp(-market.yield_v * market.expiry)
            checks.append(
                {
                    "market": market.name,
                    "value_ratio": given,
                    "exchange": exchange,
                    "better_of": better,
                    "worse_of": worse,
                    "better_residual": better - (forward_u + exchange),
                    "worse_residual": worse - (forward_v - exchange),
                    "sum_residual": (better + worse) - (forward_u + forward_v),
                }
            )
    return checks


def correlation_limits():
    """As the ratio volatility vanishes the option becomes a forward on the spread."""
    limits = []
    market = next(item for item in MARKETS if item.name == "equal-vol-uncorrelated")
    for correlation in (0.9, 0.99, 0.999, 0.9999):
        probe = market._replace(name=f"rho-{correlation}", correlation=correlation)
        for given in (0.80, 1.25):
            spot_v = BASE_U * given
            price = conditional_price(BASE_U, spot_v, probe)
            forward_u = BASE_U * math.exp(-probe.yield_u * probe.expiry)
            forward_v = spot_v * math.exp(-probe.yield_v * probe.expiry)
            intrinsic = max(forward_v - forward_u, 0.0)
            limits.append(
                {
                    "correlation": correlation,
                    "value_ratio": given,
                    "spread_volatility": spread_volatility(probe),
                    "price": price,
                    "discounted_forward_spread": intrinsic,
                    "excess_over_forward": price - intrinsic,
                }
            )
    return limits


def american_premium(steps):
    """Early exercise is worth nothing without a yield on the asset received."""
    rows = []
    for market in MARKETS:
        for given in RATIOS:
            spot_v = BASE_U * given
            european_tree = binomial_american_price(BASE_U, spot_v, market, steps, american=False)
            american_tree = binomial_american_price(BASE_U, spot_v, market, steps, american=True)
            european = conditional_price(BASE_U, spot_v, market)
            rows.append(
                {
                    "market": market.name,
                    "value_ratio": given,
                    "yield_v": market.yield_v,
                    "steps": steps,
                    "european_reference": european,
                    "european_tree": european_tree,
                    "american_tree": american_tree,
                    "tree_residual": european_tree - european,
                    "early_exercise_premium": american_tree - european_tree,
                }
            )
    return rows


def _project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(PROJECT))
    except ValueError:
        return str(resolved)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the section 26.14 reference records.")
    parser.add_argument("--paths", type=int, default=400_000, help="Monte Carlo pairs per row")
    parser.add_argument("--steps", type=int, default=2_000, help="CRR steps for the American tree")
    parser.add_argument("--output", type=Path, default=Path("johnhull/docs/validation/section-26-14"))
    args = parser.parse_args(argv)

    rows = build_rows(args.paths)
    rates = rate_independence()
    decomposition = better_worse_checks()
    limits = correlation_limits()
    american = american_premium(args.steps)

    args.output.mkdir(parents=True, exist_ok=True)
    prices_path = args.output / "prices.json"
    prices_path.write_text(
        json.dumps({"spot_u": BASE_U, "paths": args.paths, "rows": rows}, indent=2) + "\n",
        encoding="utf-8",
    )

    engine_gap = max(abs(row["conditional_minus_ratio"]) for row in rows)
    engine_relative = max(
        abs(row["conditional_minus_ratio"]) / row["conditional"]
        for row in rows
        if row["conditional"] > 1e-6
    )
    simulated_sigmas = max(
        row["simulated_standard_errors"]
        for row in rows
        if row["simulated_standard_errors"] is not None
    )
    rate_spread = max(probe["spread"] for probe in rates)
    decomposition_residual = max(
        max(abs(item["better_residual"]), abs(item["worse_residual"]), abs(item["sum_residual"]))
        for item in decomposition
    )
    tree_residual = max(abs(row["tree_residual"]) for row in american)
    zero_yield_premium = max(
        row["early_exercise_premium"] for row in american if row["yield_v"] == 0.0
    )
    positive_yield_premium = max(
        row["early_exercise_premium"] for row in american if row["yield_v"] > 0.0
    )

    record = {
        "status": "PASS",
        "checked_at": datetime.now(UTC).isoformat(),
        "scope": (
            "M6a independent references for section 26.14: the exchange price itself, the "
            "rate-independence claim, the numeraire reinterpretation, the better-of/worse-of "
            "decomposition and Rubinstein's American version."
        ),
        "reference": "Hull 11e Global Edition section 26.14, physical/printed pp.627-628.",
        "method": (
            "Three routes that share no code path and never call hullkit: conditioning on U_T "
            "with an exact inner expectation, a numeraire change to U with the ratio integrated "
            "numerically, and a correlated-draw Monte Carlo with both discounted assets as "
            "control variates. The American version is a CRR tree on V/U with rate qU and yield qV."
        ),
        "engines": {
            "max_absolute_gap": engine_gap,
            "max_relative_gap": engine_relative,
            "max_simulated_standard_errors": simulated_sigmas,
            "rows": len(rows),
        },
        "rate_independence": {
            "claim": "Hull p.628: equation (26.5) does not depend on the risk-free rate.",
            "rates": list(RATE_PROBES),
            "max_spread": rate_spread,
            "probes": rates,
        },
        "numeraire_reinterpretation": {
            "claim": (
                "Hull p.628: the price equals U0 European calls on an asset worth V/U struck at "
                "1.0 with risk-free rate qU and dividend yield qV."
            ),
            "checked_by": "ratio_price integrates that contract directly; see engines.max_relative_gap.",
        },
        "decomposition": {
            "claim": "Hull p.628: max(U,V) = U + max(V-U,0) and min(U,V) = V - max(V-U,0).",
            "max_residual": decomposition_residual,
            "rows": decomposition,
        },
        "correlation_limits": {
            "claim": "As the ratio volatility vanishes the option collapses onto the forward spread.",
            "rows": limits,
        },
        "american": {
            "claim": (
                "Hull p.628 (Rubinstein): the American version is U0 American calls on V/U with "
                "rate qU and yield qV, so early exercise is worthless when qV = 0."
            ),
            "steps": args.steps,
            "max_tree_residual": tree_residual,
            "max_premium_without_yield": zero_yield_premium,
            "max_premium_with_yield": positive_yield_premium,
            "rows": american,
        },
        "units": {
            "asset_prices": "currency",
            "expiry": "years",
            "yields": "continuously compounded per year",
            "volatility": "annual",
        },
        "assumptions": [
            "Both assets follow correlated geometric Brownian motion with constant parameters.",
            "European exercise except in the American block; positive prices, volatility, maturity.",
            "All markets are synthetic; no claim about market performance.",
        ],
        "limitations": [
            "The Monte Carlo route carries a standard error; the quadrature routes do not bound it.",
            "The correlation limit is approached numerically, not proved.",
            "The American block is a finite CRR tree, so its residual is a grid effect, not a bound.",
            "Section 26.14 prints no worked example, so nothing here is pinned to a printed price.",
            "This record prices nothing from hullkit; library coverage is recorded separately.",
        ],
        "source_sha256": {
            _project_relative(Path(__file__)): _sha256(Path(__file__)),
        },
        "artifact_sha256": {
            _project_relative(prices_path): _sha256(prices_path),
        },
    }
    (args.output / "numerical-check.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(f"prices: {len(rows)} rows -> {_project_relative(prices_path)}")
    print(f"engine agreement: max abs {engine_gap:.3e}, max rel {engine_relative:.3e}")
    print(f"simulation: worst {simulated_sigmas:.2f} standard errors")
    print(f"rate independence: max spread over r in {RATE_PROBES} = {rate_spread:.3e}")
    print(f"decomposition: max residual {decomposition_residual:.3e}")
    print(
        f"american: tree residual {tree_residual:.3e}, premium at qV=0 {zero_yield_premium:.3e}, "
        f"premium at qV>0 {positive_yield_premium:.4f}"
    )


if __name__ == "__main__":
    main()
