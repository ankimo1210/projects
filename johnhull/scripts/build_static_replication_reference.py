"""Independent offline reference for Hull 11e GE §26.17 static options replication.

The call ladder is solved as a triangular linear system, separately from
``hullkit``'s sequential construction. The continuously monitored barrier
price comes from a one-dimensional absorbed transition-density integral.
No hullkit routines, market data, or network calls are used.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.linalg import solve_triangular
from scipy.special import ndtr


def call_price(spot, strike, rate, sigma, remaining, dividend_yield=0.0):
    """European call from the lognormal distribution, independently of hullkit."""
    if remaining <= 0.0:
        return max(spot - strike, 0.0)
    stdev = sigma * math.sqrt(remaining)
    d1 = (math.log(spot / strike) + (rate - dividend_yield) * remaining) / stdev + stdev / 2
    d2 = d1 - stdev
    return float(
        spot * math.exp(-dividend_yield * remaining) * ndtr(d1)
        - strike * math.exp(-rate * remaining) * ndtr(d2)
    )


def absorbed_up_and_out_call(spot, strike, barrier, rate, sigma, expiry, dividend_yield=0.0):
    """Integrate the killed log-GBM transition density below the up barrier."""
    if strike >= barrier:
        return 0.0
    x0, top = math.log(spot), math.log(barrier)
    drift = rate - dividend_yield - sigma * sigma / 2
    width = sigma * math.sqrt(expiry)
    reflection = math.exp(2 * drift * (top - x0) / sigma**2)

    def density(x):
        z = (x - x0 - drift * expiry) / width
        reflected_z = (x - (2 * top - x0) - drift * expiry) / width

        def normal(arg):
            return math.exp(-arg * arg / 2) / (math.sqrt(2 * math.pi) * width)

        return normal(z) - reflection * normal(reflected_z)

    price, error = quad(
        lambda x: (math.exp(x) - strike) * density(x),
        math.log(strike),
        top,
        epsabs=1e-12,
        epsrel=1e-12,
    )
    if error > 1e-10:
        raise ArithmeticError(f"absorbed-density quadrature error {error}")
    return math.exp(-rate * expiry) * price


def linear_system_hedge(spot, strike, barrier, rate, sigma, expiry, steps, dividend_yield=0.0):
    """Solve the Hull boundary-matching equations as a lower-triangular system."""
    maturities = [expiry] + [expiry * (steps - j) / steps for j in range(steps)]
    strikes = [strike] + [barrier] * steps
    node_times = [expiry * (steps - i - 1) / steps for i in range(steps)]
    matrix = np.zeros((steps, steps))
    target = np.empty(steps)
    for i, time in enumerate(node_times):
        target[i] = -call_price(barrier, strike, rate, sigma, expiry - time, dividend_yield)
        for j in range(i + 1):
            matrix[i, j] = call_price(
                barrier, barrier, rate, sigma, maturities[j + 1] - time, dividend_yield
            )
    positions = [1.0, *solve_triangular(matrix, target, lower=True).tolist()]
    leg_values = [
        position * call_price(spot, k, rate, sigma, maturity, dividend_yield)
        for position, k, maturity in zip(positions, strikes, maturities, strict=True)
    ]

    def value(at_spot, time):
        return math.fsum(
            position * call_price(at_spot, k, rate, sigma, maturity - time, dividend_yield)
            for position, k, maturity in zip(positions, strikes, maturities, strict=True)
            if maturity >= time
        )

    return {
        "steps": steps,
        "strikes": strikes,
        "maturities": maturities,
        "positions": positions,
        "leg_values": leg_values,
        "initial_value": math.fsum(leg_values),
        "boundary_nodes": node_times,
        "boundary_residuals": [value(barrier, time) for time in node_times],
        "boundary_curve": [
            {"time": expiry * i / 200, "value": value(barrier, expiry * i / 200)}
            for i in range(200)
        ],
    }


def build_artifacts():
    """Return saved numerical data and a byte-reproducibility record."""
    market = {
        "spot": 50.0,
        "strike": 50.0,
        "barrier": 60.0,
        "rate": 0.10,
        "volatility": 0.30,
        "expiry": 0.75,
        "dividend_yield": 0.0,
    }
    args = tuple(
        market[key] for key in ("spot", "strike", "barrier", "rate", "volatility", "expiry")
    )
    ladders = {
        str(steps): linear_system_hedge(*args, steps, market["dividend_yield"])
        for steps in (3, 18, 100)
    }
    analytic = absorbed_up_and_out_call(*args, market["dividend_yield"])
    reference = {
        "section": "26.17",
        "source": "Hull 11e Global Edition pp.632–634, Figure 26.1 and Table 26.1",
        "units": "stock and option prices in currency; time in years; continuously compounded annual rates",
        "market": market,
        "analytic_barrier_price": analytic,
        "ladders": ladders,
        "limits": (
            "The call portfolio matches the barrier only at its selected nodes. "
            "On a hit it must be unwound; continuous-market BSM parameters are assumed."
        ),
    }
    project = Path(__file__).resolve().parents[1]
    serialized = json.dumps(reference, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    record = {
        "section": "26.17",
        "status": "PASS",
        "method": "independent triangular system and absorbed-density quadrature",
        "printed_table_positions": [1.0, -2.66, 0.97, 0.28],
        "printed_initial_values": {"3": 0.73, "18": 0.38, "100": 0.32},
        "measured": {
            "analytic_price": analytic,
            "initial_values": {key: row["initial_value"] for key, row in ladders.items()},
            "max_boundary_node_residual": max(
                abs(value) for row in ladders.values() for value in row["boundary_residuals"]
            ),
        },
        "source_sha256": {
            name: hashlib.sha256((project / name).read_bytes()).hexdigest()
            for name in (
                "scripts/build_static_replication_reference.py",
                "hullkit/tests/test_static_replication_reference.py",
            )
        },
        "artifact_sha256": hashlib.sha256(serialized.encode()).hexdigest(),
    }
    return reference, record


def main():
    """Write the committed reference, or compare it byte for byte with --check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = Path(__file__).resolve().parents[1] / "docs/validation/section-26-17"
    for name, value in zip(
        ("reference.json", "numerical-check.json"), build_artifacts(), strict=True
    ):
        content = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        path = output / name
        if args.check:
            if not path.is_file() or path.read_bytes() != content.encode():
                raise SystemExit(f"FAIL: {name} is stale")
        else:
            output.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print("PASS: static replication reference " + ("byte check" if args.check else "generated"))


if __name__ == "__main__":
    main()
