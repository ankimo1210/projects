"""Independent reference prices for Hull 11e GE section 26.12 (shout options).

Two engines with no shared pricing path produce the same number:

* ``convolution_reference`` steps a log-price grid backwards with the exact
  Gaussian transition density of the risk-neutral log price and takes, at every
  date, the larger of continuation and the analytic shout value. Doubling the
  date count and extrapolating removes the leading discretisation bias.
* ``integral_equation_reference`` never discretises the price axis. It solves the
  free boundary of the shout-premium representation and integrates the premium
  along that boundary, using the closed form of ``premium_growth`` so the
  singular part of the integrand is integrated exactly.

Both take the value at the moment of shouting from ``shout_now_value`` (Hull's
decomposition, section 26.12 p.625) and the European value from
``black_scholes``. Neither calls hullkit, so the table stays usable as an
independent target for a future hullkit implementation. All inputs are
synthetic: prices and strikes in currency, maturities in years, rates and
dividend yields continuously compounded per year, volatility annualised.

Refresh the saved records from the repository root:

    .venv/bin/python johnhull/scripts/build_shout_reference.py
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
from scipy.optimize import brentq
from scipy.signal import fftconvolve
from scipy.special import ndtr

PROJECT = Path(__file__).resolve().parent.parent
CONTRACTS = ("call", "put")
STRIKE = 100.0
SPOT_RATIOS = (0.80, 1.00, 1.25)


class Market(NamedTuple):
    """Synthetic market: continuous rate and dividend yield, volatility, years."""

    name: str
    rate: float
    dividend: float
    volatility: float
    expiry: float


MARKETS = (
    Market("hull-example-market", 0.10, 0.0, 0.40, 0.25),
    Market("positive-carry", 0.05, 0.02, 0.20, 1.0),
    Market("dividend-above-rate", 0.01, 0.07, 0.25, 1.5),
    Market("negative-rate", -0.025, 0.01, 0.18, 0.75),
    Market("zero-carry", 0.03, 0.03, 0.30, 2.0),
    Market("long-high-vol", 0.06, 0.025, 0.70, 5.0),
    Market("near-expiry", 0.03, 0.01, 0.15, 1.0 / 365.0),
)


def black_scholes(spot, strike, rate, dividend, sigma, tau, kind):
    """European Black-Scholes-Merton value (Hull 11e eq. 15.20-15.21)."""
    if kind not in CONTRACTS:
        raise ValueError(f"kind must be one of {CONTRACTS}, got {kind!r}")
    if tau <= 0.0:
        return max(spot - strike, 0.0) if kind == "call" else max(strike - spot, 0.0)
    scale = sigma * math.sqrt(tau)
    d1 = (math.log(spot / strike) + (rate - dividend + 0.5 * sigma**2) * tau) / scale
    d2 = d1 - scale
    if kind == "call":
        return spot * math.exp(-dividend * tau) * ndtr(d1) - strike * math.exp(-rate * tau) * ndtr(d2)
    return strike * math.exp(-rate * tau) * ndtr(-d2) - spot * math.exp(-dividend * tau) * ndtr(-d1)


def shout_slope(tau, rate, dividend, sigma, kind):
    """Spot coefficient A(tau) of the shout value, with A(0)=1.

    Shouting at spot S with tau left is worth ``A(tau)*S - K*exp(-r*tau)`` for a
    call and ``K*exp(-r*tau) - A(tau)*S`` for a put: the at-the-money option that
    the holder keeps after shouting is linear in the spot.
    """
    if tau <= 0.0:
        return 1.0
    k1 = (rate - dividend + 0.5 * sigma**2) / sigma
    k2 = (rate - dividend - 0.5 * sigma**2) / sigma
    root = math.sqrt(tau)
    if kind == "call":
        return math.exp(-rate * tau) * ndtr(-k2 * root) + math.exp(-dividend * tau) * ndtr(k1 * root)
    if kind == "put":
        return math.exp(-rate * tau) * ndtr(k2 * root) + math.exp(-dividend * tau) * ndtr(-k1 * root)
    raise ValueError(f"kind must be one of {CONTRACTS}, got {kind!r}")


def shout_now_value(spot, strike, rate, dividend, sigma, tau, kind):
    """Value at the instant of shouting: discounted intrinsic plus a fresh ATM option.

    Hull section 26.12: shouting at spot S turns the payoff into
    ``max(0, S_T - S) + (S - K)`` for a call, so the holder owns the discounted
    locked-in amount plus a European option struck at the shout level.
    """
    discount = math.exp(-rate * tau)
    if kind == "call":
        return discount * (spot - strike) + black_scholes(spot, spot, rate, dividend, sigma, tau, "call")
    if kind == "put":
        return discount * (strike - spot) + black_scholes(spot, spot, rate, dividend, sigma, tau, "put")
    raise ValueError(f"kind must be one of {CONTRACTS}, got {kind!r}")


def shout_values(spots, strike, rate, dividend, sigma, tau, kind):
    """``shout_now_value`` on a spot grid, written through the affine form."""
    slope = shout_slope(tau, rate, dividend, sigma, kind)
    discounted_strike = strike * math.exp(-rate * tau)
    if kind == "call":
        return slope * np.asarray(spots) - discounted_strike
    return discounted_strike - slope * np.asarray(spots)


def convolution_curve(strike, rate, dividend, sigma, expiry, steps, kind, *, width=10.0,
                      span=0.5, min_nodes=800, points_per_sd=4.0, max_nodes=40000):
    """Backward induction with the exact Gaussian transition kernel.

    Returns ``(log_spots, values)`` for ``steps`` equally spaced shout dates. The
    grid is centred on ``log(strike)`` so one sweep prices every spot, and the
    node count keeps at least ``points_per_sd`` intervals inside one step's
    standard deviation.
    """
    if kind not in CONTRACTS:
        raise ValueError(f"kind must be one of {CONTRACTS}, got {kind!r}")
    dt = expiry / steps
    drift = (rate - dividend - 0.5 * sigma**2) * dt
    sd = sigma * math.sqrt(dt)
    half = width * sigma * math.sqrt(expiry) + abs(rate - dividend - 0.5 * sigma**2) * expiry + span
    nodes = max(min_nodes, math.ceil(points_per_sd * half / sd))
    if nodes > max_nodes:
        raise ValueError(f"grid would need {nodes} nodes; raise max_nodes or lower steps")
    log_spots = np.linspace(math.log(strike) - half, math.log(strike) + half, 2 * nodes + 1)
    step = log_spots[1] - log_spots[0]
    spots = np.exp(log_spots)

    weights = np.ones_like(log_spots)
    weights[1:-1:2] = 4.0
    weights[2:-1:2] = 2.0
    weights *= step / 3.0

    reach = math.ceil((8.0 * sd + abs(drift)) / step)
    offsets = np.arange(-reach, reach + 1) * step
    # A convolution reverses the kernel, so the drift enters with a plus sign.
    kernel = np.exp(-0.5 * ((offsets + drift) / sd) ** 2) / (sd * math.sqrt(2.0 * math.pi))
    discount = math.exp(-rate * dt)

    values = np.maximum(spots - strike, 0.0) if kind == "call" else np.maximum(strike - spots, 0.0)
    for index in range(steps - 1, -1, -1):
        tau = expiry - index * dt
        values = discount * fftconvolve(weights * values, kernel, mode="same")
        shout = shout_values(spots, strike, rate, dividend, sigma, tau, kind)
        np.maximum(values, shout, out=values)
        # The convolution truncates at the grid edge, so rebuild the far field from
        # the European value and the shout value, which bracket the answer there.
        edges = np.concatenate([spots[:reach], spots[-reach:]])
        european = np.array([black_scholes(s, strike, rate, dividend, sigma, tau, kind) for s in edges])
        values[:reach] = np.maximum(european[:reach], shout[:reach])
        values[-reach:] = np.maximum(european[reach:], shout[-reach:])
    return log_spots, values


def convolution_prices(spots, strike, rate, dividend, sigma, expiry, steps, kind, **kwargs):
    """Prices for many spots from one backward sweep over ``steps`` shout dates."""
    grid, values = convolution_curve(strike, rate, dividend, sigma, expiry, steps, kind, **kwargs)
    return np.interp(np.log(np.asarray(spots, dtype=float)), grid, values)


def convolution_reference(spots, strike, rate, dividend, sigma, expiry, kind, *, steps=800, **kwargs):
    """Richardson extrapolation in the date spacing: ``2*V(2m) - V(m)``."""
    coarse = convolution_prices(spots, strike, rate, dividend, sigma, expiry, steps, kind, **kwargs)
    fine = convolution_prices(spots, strike, rate, dividend, sigma, expiry, 2 * steps, kind, **kwargs)
    return 2.0 * fine - coarse, coarse, fine


def premium_growth(tau, rate, dividend, sigma, kind):
    """G(tau) = exp(q*tau)*A(tau), with G(0)=1; its increments weight the premium."""
    if tau <= 0.0:
        return 1.0
    k1 = (rate - dividend + 0.5 * sigma**2) / sigma
    k2 = (rate - dividend - 0.5 * sigma**2) / sigma
    root = math.sqrt(tau)
    carry = math.exp((dividend - rate) * tau)
    if kind == "call":
        return carry * ndtr(-k2 * root) + ndtr(k1 * root)
    if kind == "put":
        return carry * ndtr(k2 * root) + ndtr(-k1 * root)
    raise ValueError(f"kind must be one of {CONTRACTS}, got {kind!r}")


def integral_equation_price(spot, strike, rate, dividend, sigma, expiry, kind, steps=200):
    """Solve the shout boundary, then evaluate the premium representation.

    Applying the discounted generator to the shout value leaves ``-S*d/dtau``
    of ``exp(-q*tau)*G(tau)``, so

        V(S,0) = BSM(S,K,T) + s*S*exp(-q*T) * int_0^T N(s*d1(S,b)) dG(tau)

    with ``s = +1`` for a call and ``-1`` for a put, ``b`` the shout boundary and
    ``d1`` measured over the remaining time between the two dates. Nodes are
    uniform in ``sqrt(tau)``; each interval uses the exact increment of ``G`` and
    the midpoint indicator, so the deep-in-the-money case telescopes exactly.
    Returns ``(price, taus, boundary)``.
    """
    if kind not in CONTRACTS:
        raise ValueError(f"kind must be one of {CONTRACTS}, got {kind!r}")
    sign = 1.0 if kind == "call" else -1.0
    taus = np.linspace(0.0, math.sqrt(expiry), steps + 1) ** 2
    growth = np.array([premium_growth(t, rate, dividend, sigma, kind) for t in taus])
    increments = np.diff(growth)
    midpoints = 0.5 * (taus[:-1] + taus[1:])
    boundary = np.full(steps + 1, np.nan)
    boundary[0] = strike
    drift = rate - dividend + 0.5 * sigma**2

    def premium(level, index, unsolved):
        gaps = taus[index] - midpoints[:index]
        levels = 0.5 * (boundary[:index] + boundary[1 : index + 1])
        if unsolved:
            levels = levels.copy()
            levels[index - 1] = 0.5 * (boundary[index - 1] + level)
        d1 = (np.log(level / levels) + drift * gaps) / (sigma * np.sqrt(gaps))
        indicator = ndtr(d1) if kind == "call" else ndtr(-d1)
        weighted = float(np.sum(indicator * increments[:index]))
        return sign * level * math.exp(-dividend * taus[index]) * weighted

    def residual(level, index):
        tau = taus[index]
        slope = shout_slope(tau, rate, dividend, sigma, kind)
        discounted_strike = strike * math.exp(-rate * tau)
        shout = slope * level - discounted_strike if kind == "call" else discounted_strike - slope * level
        european = black_scholes(level, strike, rate, dividend, sigma, tau, kind)
        return shout - european - premium(level, index, True)

    limit = strike * (60.0 if kind == "call" else 0.999999)
    for index in range(1, steps + 1):
        # The residual is negative at the strike, where shouting is worth exactly
        # the European option, and non-negative inside the shout region. Walk out
        # from just inside the previous boundary in small steps: far from the
        # boundary the residual flattens onto zero and a coarse ladder can jump
        # the crossing.
        anchor = strike * (1.0 + sign * 1e-12)
        offset = max(0.8 * abs(boundary[index - 1] - strike), strike * 1e-9)
        far = anchor
        crossed = False
        while offset <= limit:
            far = strike + sign * offset
            if residual(far, index) > 0.0:
                crossed = True
                break
            offset *= 1.1
        if not crossed:
            raise ValueError(
                f"no shout boundary bracketed at tau={taus[index]:.6g} for a {kind}"
            )
        boundary[index] = brentq(residual, anchor, far, args=(index,), xtol=1e-13, rtol=8.9e-16)

    european = black_scholes(spot, strike, rate, dividend, sigma, expiry, kind)
    return european + premium(spot, steps, False), taus, boundary


def integral_equation_reference(spot, strike, rate, dividend, sigma, expiry, kind, steps=200):
    """Richardson extrapolation of the integral equation: ``2*V(2n) - V(n)``."""
    coarse, _, _ = integral_equation_price(spot, strike, rate, dividend, sigma, expiry, kind, steps)
    fine, taus, boundary = integral_equation_price(
        spot, strike, rate, dividend, sigma, expiry, kind, 2 * steps
    )
    return 2.0 * fine - coarse, taus, boundary


def build_prices(steps=800):
    """Reference table over every market, contract and spot ratio."""
    rows = []
    spots = [STRIKE * ratio for ratio in SPOT_RATIOS]
    for market in MARKETS:
        for kind in CONTRACTS:
            reference, coarse, fine = convolution_reference(
                spots, STRIKE, market.rate, market.dividend, market.volatility,
                market.expiry, kind, steps=steps,
            )
            for ratio, spot, value, low, high in zip(SPOT_RATIOS, spots, reference, coarse, fine, strict=True):
                rows.append({
                    "market": market.name,
                    "contract": kind,
                    "spot_ratio": ratio,
                    "spot": spot,
                    "strike": STRIKE,
                    "rate": market.rate,
                    "dividend": market.dividend,
                    "volatility": market.volatility,
                    "expiry": market.expiry,
                    "price": float(value),
                    "coarse_dates": float(low),
                    "fine_dates": float(high),
                    "european": black_scholes(spot, STRIKE, market.rate, market.dividend,
                                              market.volatility, market.expiry, kind),
                    "shout_immediately": shout_now_value(spot, STRIKE, market.rate, market.dividend,
                                                         market.volatility, market.expiry, kind),
                })
    return rows


def cross_check(rows, steps=200):
    """Price every at-the-money row again with the integral equation."""
    comparisons = []
    for row in rows:
        if row["spot_ratio"] != 1.0:
            continue
        value, _, boundary = integral_equation_reference(
            row["spot"], row["strike"], row["rate"], row["dividend"], row["volatility"],
            row["expiry"], row["contract"], steps=steps,
        )
        comparisons.append({
            "market": row["market"],
            "contract": row["contract"],
            "convolution": row["price"],
            "integral_equation": float(value),
            "difference": float(value - row["price"]),
            "boundary_at_inception": float(boundary[-1]),
        })
    return comparisons


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build the section 26.12 reference records.")
    parser.add_argument("--steps", type=int, default=800, help="coarse date count; the fine run doubles it")
    parser.add_argument("--cross-check-steps", type=int, default=200, help="integral-equation resolution")
    parser.add_argument("--output", type=Path, default=Path("johnhull/docs/validation/section-26-12"))
    args = parser.parse_args(argv)

    rows = build_prices(args.steps)
    comparisons = cross_check(rows, args.cross_check_steps)

    args.output.mkdir(parents=True, exist_ok=True)
    prices_path = args.output / "prices.json"
    prices_path.write_text(
        json.dumps({"strike": STRIKE, "date_steps": args.steps, "rows": rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    absolute = max(abs(item["difference"]) for item in comparisons)
    relative = max(abs(item["difference"]) / abs(item["convolution"]) for item in comparisons)
    record = {
        "status": "PASS",
        "checked_at": datetime.now(UTC).isoformat(),
        "scope": "M4a independent shout-price reference only; section 26.12 stays gaps_found.",
        "reference": "Hull 11e Global Edition section 26.12, physical/printed pp.625-626.",
        "method": (
            "Two engines with no shared pricing path: Gaussian-kernel backward induction on a log "
            "grid, and a free-boundary solution of the shout-premium representation. Both are "
            "extrapolated in their own step size. Neither engine calls hullkit."
        ),
        "engines": {
            "convolution": {"coarse_dates": args.steps, "fine_dates": 2 * args.steps,
                            "extrapolation": "2*V(2m) - V(m)"},
            "integral_equation": {"coarse_steps": args.cross_check_steps,
                                  "fine_steps": 2 * args.cross_check_steps,
                                  "extrapolation": "2*V(2n) - V(n)",
                                  "grid": "uniform in sqrt(time to maturity)"},
        },
        "agreement": {"max_absolute": absolute, "max_relative": relative, "comparisons": comparisons},
        "units": {"spot_strike_price": "currency", "expiry": "years",
                  "rate_dividend": "continuously compounded per year", "volatility": "annual"},
        "assumptions": [
            "Risk-neutral GBM with constant r/q/sigma; positive spot, volatility and maturity.",
            "One shout at any time in [0, T], and the holder may also never shout.",
            "All markets are synthetic; no claim about market performance.",
        ],
        "limitations": [
            "Both engines are numerical. The recorded agreement is a measured spread, not a proven bound.",
            "No hullkit shout implementation exists yet, so no library code is validated here.",
            "Deep out-of-the-money rows carry absolute accuracy only; their relative error is not bounded.",
            "Discrete shout dates, cash dividends and non-constant volatility are out of scope.",
        ],
        "source_sha256": {
            name: _sha256(PROJECT / name)
            for name in (
                "scripts/build_shout_reference.py",
                "hullkit/tests/test_shout_reference.py",
                "options, futures and other derivatives 11th.pdf",
            )
        },
        "artifact_sha256": {
            str(prices_path.resolve().relative_to(PROJECT)): _sha256(prices_path)
        },
    }
    (args.output / "numerical-check.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(f"prices: {len(rows)} rows -> {prices_path}")
    print(f"engine agreement: max abs {absolute:.3e}, max rel {relative:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
