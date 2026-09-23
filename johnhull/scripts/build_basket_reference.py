"""Offline, independent references for Hull GE section 26.15.

No hullkit pricing routines are imported. Markets are synthetic; time is years,
rates/yields continuously compounded, and prices in common currency units.
"""
import math


def moments_direct(spots, weights, rate, dividends, volatilities, correlations, expiry):
    """Return exact GBM first and raw second basket moments using direct loops."""
    forwards = [w * s * math.exp((rate - q) * expiry)
                for s, w, q in zip(spots, weights, dividends, strict=True)]
    first = math.fsum(forwards)
    second = math.fsum(
        fi * fj * math.exp(correlations[i][j] * volatilities[i] * volatilities[j] * expiry)
        for i, fi in enumerate(forwards) for j, fj in enumerate(forwards)
    )
    return first, second


def _lognormal_payoff(forward, strike, variance, kind):
    """Undiscounted lognormal option expectation, including a cash boundary."""
    from scipy.special import ndtr

    if strike <= 0:
        return forward - strike if kind == "call" else 0.
    if variance == 0 or forward == 0:
        return max(forward - strike, 0.) if kind == "call" else max(strike - forward, 0.)
    sd = math.sqrt(variance)
    d1 = (math.log(forward / strike) + variance / 2) / sd
    d2 = d1 - sd
    if kind == "call":
        return float(forward * ndtr(d1) - strike * ndtr(d2))
    return float(strike * ndtr(-d2) - forward * ndtr(-d1))


def conditional_two_asset(spots, weights, strike, rate, dividends, volatilities,
                          correlations, expiry, kind="call"):
    """Return (discounted conditional quadrature price, quadrature error estimate).

    Integrate over Z1; the second weighted asset is conditionally lognormal.
    |rho|=1 is deliberately excluded and belongs to separate analytic anchors.
    """
    from scipy.integrate import quad

    if len(spots) != 2 or abs(correlations[0][1]) >= 1:
        raise ValueError("conditional integral requires two assets and nondegenerate correlation")
    if kind not in ("call", "put"):
        raise ValueError("kind must be call or put")
    rho = correlations[0][1]
    sd1, sd2 = [v * math.sqrt(expiry) for v in volatilities]
    a1, a2 = [w * s * math.exp((rate - q - v*v/2) * expiry)
              for s, w, q, v in zip(spots, weights, dividends, volatilities, strict=True)]
    variance = sd2 * sd2 * (1 - rho*rho)

    def integrand(z):
        first = a1 * math.exp(sd1 * z)
        second_mean = a2 * math.exp(sd2 * rho * z + variance / 2)
        payoff = _lognormal_payoff(second_mean, strike - first, variance, kind)
        return payoff * math.exp(-z*z/2) / math.sqrt(2 * math.pi)

    # Finite Gaussian bounds avoid overflow in exp at QUADPACK's infinite nodes.
    # The extra volatility shift controls exponentially tilted first-moment tails.
    bound = 12 + max(sd1, abs(rho * sd2))
    points = []
    if sd1 > 0 and a1 > 0:
        crossing = math.log(strike / a1) / sd1
        if -bound < crossing < bound:
            points.append(crossing)
    price, error = quad(integrand, -bound, bound, points=points,
                        epsabs=1e-10, epsrel=1e-11, limit=300)
    discount = math.exp(-rate * expiry)
    return discount * price, discount * error


def simulate(spots, weights, rate, dividends, volatilities, correlations, expiry,
             *, strikes, paths=1_000_000, seed=2615, chunk_size=50_000, pilot_paths=20_000):
    """Return MC estimates keyed by (strike, kind), with iid sample standard errors.

    An independent pilot estimates the first-moment control coefficient. Production
    samples estimate residual variance with that coefficient held fixed, avoiding
    fitting bias. Calls and puts share paths and controls (beta_put=beta_call-1).
    Eigenvalue factorization also handles positive semidefinite singular matrices.
    """
    import numpy as np

    if paths < 2 or pilot_paths < 2 or chunk_size < 1:
        raise ValueError("paths and pilot_paths >= 2 and chunk_size >= 1 required")
    weights, spots = np.asarray(weights), np.asarray(spots)
    vol, yields = np.asarray(volatilities), np.asarray(dividends)
    eigenvalues, vectors = np.linalg.eigh(correlations)
    if np.min(eigenvalues) < -1e-12:
        raise ValueError("correlation must be positive semidefinite")
    factor = vectors @ np.diag(np.sqrt(np.maximum(eigenvalues, 0.)))
    main_seed, pilot_seed = np.random.SeedSequence(seed).spawn(2)
    main_rng, pilot_rng = np.random.default_rng(main_seed), np.random.default_rng(pilot_seed)
    first, _ = moments_direct(spots, weights, rate, dividends, vol, correlations, expiry)
    discount = math.exp(-rate * expiry)

    def draw(rng, size):
        z = rng.standard_normal((size, len(spots))) @ factor.T
        terminal = spots * np.exp((rate - yields - vol*vol/2)*expiry + vol*math.sqrt(expiry)*z)
        return terminal @ weights

    pilot = draw(pilot_rng, pilot_paths)
    centered = pilot - pilot.mean()
    denominator = float(centered @ centered)
    betas = {}
    for strike in strikes:
        payoff = np.maximum(pilot - strike, 0.)
        betas[strike] = float(centered @ (payoff - payoff.mean())) / denominator if denominator else 0.

    # Merge centered chunk sums of squares (stable even for near-deterministic payoffs).
    stats = {strike: np.zeros(5) for strike in strikes}  # n, adjusted mean/M2, raw mean/M2
    for start in range(0, paths, chunk_size):
        basket = draw(main_rng, min(chunk_size, paths-start))
        for strike in strikes:
            raw = discount * np.maximum(basket-strike, 0.)
            adjusted = raw - betas[strike]*discount*(basket-first)
            state = stats[strike]
            old, count = state[0], len(raw)
            total = old + count
            for offset, values in ((1, adjusted), (3, raw)):
                mean = float(values.mean())
                delta = mean - state[offset]
                state[offset+1] += float((values-mean) @ (values-mean)) + delta*delta*old*count/total
                state[offset] += delta*count/total
            state[0] = total
    result = {}
    for strike, state in stats.items():
        _, price, square, raw, raw_square = state
        standard_error = math.sqrt(max(square, 0.) / (paths-1) / paths)
        # Put's controlled residual is pathwise call residual minus a fixed parity amount.
        for kind in ("call", "put"):
            parity = discount * (first-strike) if kind == "put" else 0.
            result[(strike, kind)] = {
                "price": float(price-parity), "standard_error": standard_error,
                "raw_price": float(raw) if kind == "call" else None,
                "raw_standard_error": math.sqrt(max(raw_square, 0.)/(paths-1)/paths)
                if kind == "call" else None,
                "control_beta": betas[strike] - (kind == "put"),
            }
    return result


def moment_match_price(spots, weights, strike, rate, dividends, volatilities,
                       correlations, expiry, kind="call"):
    """Independent Black proxy fitted to the first two exact GBM moments."""
    first, second = moments_direct(spots, weights, rate, dividends, volatilities,
                                   correlations, expiry)
    variance = max(math.log(second / (first*first)), 0.)
    return math.exp(-rate*expiry) * _lognormal_payoff(first, strike, variance, kind)


# (name, spots, weights, volatilities, dividends, correlations, rate, expiry, anchor)
MARKETS = [
    ("baseline", [100., 80.], [.6, .5], [.2, .3], [.01, .025],
     [[1., .35], [.35, 1.]], .03, 1., None),
    ("negative-correlation", [100., 80.], [.6, .5], [.2, .3], [.01, .025],
     [[1., -.65], [-.65, 1.]], .03, 1., None),
    ("high-correlation", [100., 80.], [.6, .5], [.2, .3], [.01, .025],
     [[1., .9], [.9, 1.]], .03, 1., None),
    ("short-expiry", [100., 80.], [.6, .5], [.2, .3], [.01, .025],
     [[1., .35], [.35, 1.]], .03, .1, None),
    ("long-high-volatility", [100., 80.], [.6, .5], [.65, .4], [.01, .025],
     [[1., -.65], [-.65, 1.]], .03, 3., None),
    ("negative-rate", [100., 80.], [.6, .5], [.35, .5], [.03, .01],
     [[1., .2], [.2, 1.]], -.015, 1.5, None),
    ("three-diversified", [100., 80., 120.], [.4, .3, .3], [.2, .3, .25],
     [.01, .025, .02], [[1., .2, -.15], [.2, 1., .35], [-.15, .35, 1.]], .03, 1., None),
    ("three-high-volatility", [100., 80., 120.], [.4, .3, .3], [.6, .45, .5],
     [.02, .01, .03], [[1., -.3, .1], [-.3, 1., .25], [.1, .25, 1.]], -.01, 2.5, None),
    ("single-asset", [100.], [1.], [.2], [.02], [[1.]], .05, 1., "single_asset"),
    ("perfect-correlation", [100., 80.], [.6, .5], [.2, .2], [.01, .01],
     [[1., 1.], [1., 1.]], .03, 1., "proportional"),
    ("singular-single-exposure", [100., 80.], [1., 0.], [.2, .4], [.02, .01],
     [[1., -1.], [-1., 1.]], .05, 1., "single_nonzero_weight"),
    ("cash-basket", [100., 80.], [.6, .5], [0., 0.], [0., 0.],
     [[1., .3], [.3, 1.]], 0., 1., "deterministic"),
]


def conditional_tail_bound(spots, weights, strike, rate, dividends, volatilities,
                           correlations, expiry):
    """Upper bound on omitted discounted payoff outside the finite Z1 interval."""
    from scipy.special import ndtr

    sd1, sd2 = [v*math.sqrt(expiry) for v in volatilities]
    shifts = [sd1, correlations[0][1]*sd2]
    bound = 12 + max(abs(shift) for shift in shifts)
    forwards = [s*w*math.exp((rate-q)*expiry)
                for s, w, q in zip(spots, weights, dividends, strict=True)]
    # Both payoffs <= B+K. Exponentially tilted Gaussian tails integrate B exactly.
    tail = strike * 2 * ndtr(-bound)
    for forward, shift in zip(forwards, shifts, strict=True):
        tail += forward * (ndtr(-bound-shift) + ndtr(shift-bound))
    return float(math.exp(-rate*expiry)*tail)


def build_artifacts(*, paths=1_000_000, pilot_paths=20_000):
    """Build deterministic JSON objects without importing hullkit or using a clock."""
    rows = []
    for market_index, market in enumerate(MARKETS):
        name, spots, weights, vols, dividends, corr, rate, expiry, anchor = market
        first, second = moments_direct(spots, weights, rate, dividends, vols, corr, expiry)
        strikes = [80., 100., 120.]
        seed = 261500 + market_index
        mc = simulate(spots, weights, rate, dividends, vols, corr, expiry,
                      strikes=strikes, paths=paths, pilot_paths=pilot_paths, seed=seed)
        for strike in strikes:
            for kind in ("call", "put"):
                approximation = moment_match_price(spots, weights, strike, rate, dividends,
                                                    vols, corr, expiry, kind)
                conditional, quad_error, tail, exact = None, None, None, None
                if anchor:
                    # Known terminal distribution of the anchor, independent of M2 matching.
                    exact = math.exp(-rate*expiry)*_lognormal_payoff(
                        first, strike, vols[0]**2*expiry, kind)
                elif len(spots) == 2:
                    conditional, quad_error = conditional_two_asset(
                        spots, weights, strike, rate, dividends, vols, corr, expiry, kind)
                    tail = conditional_tail_bound(
                        spots, weights, strike, rate, dividends, vols, corr, expiry)
                sample = mc[(strike, kind)]
                reference = exact if exact is not None else (
                    conditional if conditional is not None else sample["price"])
                source = "analytic" if exact is not None else (
                    "conditional_quadrature" if conditional is not None else "mc")
                uncertainty = (4*sample["standard_error"] if source == "mc"
                               else max(1e-10, (quad_error or 0.) + (tail or 0.)))
                error = approximation-reference
                rows.append({
                    "market": name, "spots": spots, "weights": weights, "volatilities": vols,
                    "dividends": dividends, "correlation": corr, "r": rate, "T": expiry,
                    "K": strike, "kind": kind, "M1": first, "M2": second, "anchor": anchor,
                    "approximation": approximation, "conditional": conditional,
                    "conditional_quadrature_error": quad_error, "conditional_tail_bound": tail,
                    "exact": exact, "mc": sample["price"], "standard_error": sample["standard_error"],
                    "control_beta": sample["control_beta"], "seed": seed, "paths": paths,
                    "pilot_paths": pilot_paths, "reference": reference, "reference_method": source,
                    "reference_uncertainty": uncertainty, "approximation_error": error,
                    "relative_error": error/reference if reference >= .5 else None,
                    "error_sign_established": abs(error) > uncertainty,
                })
    eligible = [row for row in rows if row["reference"] >= .5]
    mc_anchors = [row for row in rows if row["reference_method"] != "mc"
                  and row["standard_error"] > 1e-14]
    zscores = [abs(row["mc"]-row["reference"])/row["standard_error"] for row in mc_anchors]
    prices = {"schema_version": 1, "section": "26.15", "paths": paths,
              "pilot_paths": pilot_paths, "chunk_size": 50_000, "price_floor": .5, "rows": rows}
    record = {
        "schema_version": 1, "section": "26.15",
        "status": "PASS" if max(zscores) < 4. else "FAIL",
        "milestone_status": "gaps_found",
        "scope": "Independent synthetic numerical reference; API and teaching still pending.",
        "source_pages": [628, 629], "printed_price_anchor": None,
        "price_floor": .5, "paths_per_market": paths, "pilot_paths_per_market": pilot_paths,
        "row_count": len(rows), "ordinary_rows": 48, "exact_anchor_rows": 24,
        "units": {"price": "currency", "M2": "currency squared", "T": "years",
                  "rates": "continuously compounded annual", "volatilities": "annualized"},
        "method": {
            "moments": "Direct double loops under correlated risk-neutral GBM",
            "conditional": "Conditional lognormal payoff; one finite Gaussian quad integral",
            "quad_error": "QUADPACK estimate on finite interval only, not a certified total error",
            "tail": "Separate analytic upper bound using payoff <= B+K and tilted Gaussian tails",
            "mc": "IID terminal GBM; PSD eigendecomposition; independent pilot first-moment control",
            "parity": "Call/put share paths and controls; controlled residuals differ by constant",
            "reproducibility": "No timestamps; --check regenerates both files byte for byte",
        },
        "tolerances": {"mc_standard_errors": 4., "quad_epsabs": 1e-10, "quad_epsrel": 1e-11,
                       "deterministic_error_floor": 1e-10},
        "mc_validation": {
            "anchor_rows": len(mc_anchors), "max_standard_errors": max(zscores),
            "within_four_se": max(zscores) < 4.,
        },
        "empirical_error_floor": {
            "max_mc_standard_error": max(row["standard_error"] for row in rows),
            "max_four_se": max(4*row["standard_error"] for row in rows),
            "max_quadrature_estimate": max(row["conditional_quadrature_error"] or 0. for row in rows),
            "max_tail_bound": max(row["conditional_tail_bound"] or 0. for row in rows),
        },
        "approximation_error": {
            "max_absolute": max(abs(row["approximation_error"]) for row in rows),
            "max_relative": max(abs(row["relative_error"]) for row in eligible),
            "min_signed_relative": min(row["relative_error"] for row in eligible),
            "max_signed_relative": max(row["relative_error"] for row in eligible),
            "relative_error_rows": len(eligible),
            "below_price_floor_rows": len(rows)-len(eligible),
            "unresolved_sign_rows": sum(not row["error_sign_established"] for row in rows),
            "caveat": "Empirical market grid only; no universal error bound. MC gaps <=4SE have unresolved sign.",
        },
    }
    import hashlib
    import json
    from pathlib import Path

    project = Path(__file__).resolve().parents[1]
    record["source_sha256"] = {
        name: hashlib.sha256((project / name).read_bytes()).hexdigest()
        for name in ("scripts/build_basket_reference.py", "hullkit/tests/test_basket_reference.py")
    }
    serialized = json.dumps(prices, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    record["artifact_sha256"] = {
        "docs/validation/section-26-15/prices.json":
        hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    }
    return prices, record


def main():
    """Write reference JSON or check byte reproducibility with --check."""
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = Path(__file__).resolve().parents[1] / "docs" / "validation" / "section-26-15"
    objects = build_artifacts()
    for name, value in zip(("prices.json", "numerical-check.json"), objects, strict=True):
        content = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        path = output / name
        if args.check:
            if not path.is_file() or path.read_bytes() != content.encode("utf-8"):
                raise SystemExit(f"FAIL: {name} is stale")
        else:
            output.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print("PASS: basket reference " + ("byte reproducibility" if args.check else "generated"))


if __name__ == "__main__":
    main()
