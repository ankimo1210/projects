"""Build the saved §26.14 lesson numbers; never run during notebook builds.

Run from the workspace root with hullkit/src on PYTHONPATH. This generator may
import the independent reference engine; the lesson figures never do - they read
the saved JSON and refuse it when a source hash is stale.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

from build_exchange_reference import (
    MARKETS,
    RATE_PROBES,
    Market,
    binomial_american_price,
    conditional_price,
    spread_volatility,
)
from hullkit import bsm, exotics

PROJECT = Path(__file__).resolve().parents[1]
VALIDATION = PROJECT / "docs/validation/section-26-14"
SCHEMA_VERSION = 1
SPOT_U = 100.0
PAYOFF_TERMINALS = (60.0, 80.0, 100.0, 120.0, 140.0, 160.0)
PAYOFF_U = 100.0
CORRELATIONS = tuple(round(-0.95 + 0.05 * step, 2) for step in range(39))
CORRELATION_MARKETS = ("equal-vol-uncorrelated", "asymmetric-vol", "long-high-vol")
RATE_MARKETS = ("equal-vol-tight", "yield-on-received", "long-high-vol")
AMERICAN_MARKETS = ("equal-vol-uncorrelated", "yield-on-received", "equal-vol-tight")
AMERICAN_RATIOS = tuple(round(0.60 + 0.05 * step, 2) for step in range(17))
CONVERGENCE_STEPS = (64, 128, 256, 512, 1024)
SOURCE_PATHS = (
    "hullkit/src/hullkit/exotics.py",
    "scripts/build_exchange_lesson_data.py",
    "scripts/build_exchange_reference.py",
    "docs/validation/section-26-14/prices.json",
    "docs/validation/section-26-14/numerical-check.json",
)
LIMITATIONS = [
    "Two correlated GBM assets, constant sigma_u/sigma_v/rho/q_u/q_v; positive prices, T, sigma.",
    "European except in the American family; the tree is a finite grid, not an error bound.",
    "Synthetic markets. Section 26.14 prints no worked example, so nothing is pinned to Hull.",
    "The payoff family is a terminal payoff, not a price.",
]


def _family(data, method, hashes, limitations=()):
    return dict(
        units=dict(money="currency", time="years", yields="continuous per year",
                   volatility="annualized"),
        method=method,
        limitations=LIMITATIONS + list(limitations),
        source_hashes=hashes,
        data=data,
    )


def _market(name) -> Market:
    return next(item for item in MARKETS if item.name == name)


def _payoff_rows():
    """One terminal cross-section: what each of the three contracts pays."""
    rows = []
    for terminal_v in PAYOFF_TERMINALS:
        rows.append(
            {
                "terminal_v": terminal_v,
                "terminal_u": PAYOFF_U,
                "exchange": max(terminal_v - PAYOFF_U, 0.0),
                "better_of": max(PAYOFF_U, terminal_v),
                "worse_of": min(PAYOFF_U, terminal_v),
                "given_up": PAYOFF_U,
            }
        )
    return {"terminal_u": PAYOFF_U, "rows": rows}


def _correlation_rows():
    """Price and ratio volatility across the whole correlation range."""
    families = []
    for name in CORRELATION_MARKETS:
        market = _market(name)
        entries = []
        for correlation in CORRELATIONS:
            probe = market._replace(correlation=correlation)
            entries.append(
                {
                    "correlation": correlation,
                    "spread_volatility": spread_volatility(probe),
                    "price": exotics.exchange_option(
                        SPOT_U, SPOT_U, probe.volatility_u, probe.volatility_v, correlation,
                        probe.expiry, q_u=probe.yield_u, q_v=probe.yield_v),
                }
            )
        forward_spread = max(
            SPOT_U * math.exp(-market.yield_v * market.expiry)
            - SPOT_U * math.exp(-market.yield_u * market.expiry),
            0.0,
        )
        families.append(
            {
                "market": name,
                "volatility_u": market.volatility_u,
                "volatility_v": market.volatility_v,
                "yield_u": market.yield_u,
                "yield_v": market.yield_v,
                "expiry": market.expiry,
                "spot": SPOT_U,
                "forward_spread": forward_spread,
                "entries": entries,
            }
        )
    return families


def _rate_rows():
    """The price against the rate it is said not to depend on, plus the restatement."""
    families = []
    rates = sorted({*RATE_PROBES, 0.02, 0.05, 0.12, -0.05})
    for name in RATE_MARKETS:
        market = _market(name)
        spread = spread_volatility(market)
        library = exotics.exchange_option(
            SPOT_U, SPOT_U * 1.1, market.volatility_u, market.volatility_v, market.correlation,
            market.expiry, q_u=market.yield_u, q_v=market.yield_v)
        entries = [
            {
                "rate": rate,
                "reference": conditional_price(SPOT_U, SPOT_U * 1.1, market, rate=rate),
                # The usual wrong reading: a plain call on V struck at today's U0 and
                # discounted at r. Same sigma-hat, so only the strike treatment differs.
                "fixed_strike_misreading": bsm.call_price(
                    SPOT_U * 1.1, SPOT_U, rate, spread, market.expiry, q=0.0),
            }
            for rate in rates
        ]
        # Hull's restatement: U0 calls on V/U struck at 1, rate q_u, dividend yield q_v.
        restated = SPOT_U * bsm.call_price(
            1.1, 1.0, market.yield_u, spread, market.expiry, q=market.yield_v)
        families.append(
            {
                "market": name,
                "value_ratio": 1.1,
                "expiry": market.expiry,
                "yield_u": market.yield_u,
                "yield_v": market.yield_v,
                "spread_volatility": spread,
                "library_price": library,
                "restated_price": restated,
                "restatement_residual": restated - library,
                "entries": entries,
                "reference_spread": max(e["reference"] for e in entries)
                - min(e["reference"] for e in entries),
            }
        )
    return families


def _american_rows():
    """European, American and the premium across moneyness, plus the grid residual.

    The tree is a finite grid, so ``american - closed form`` mixes early exercise
    with discretisation. The same grid without the exercise test separates them:
    ``premium_on_grid`` is early exercise alone and ``grid_residual`` is what the
    grid costs. At q_v = 0 the first is zero and only the second is left.
    """
    families = []
    for name in AMERICAN_MARKETS:
        market = _market(name)
        entries = []
        for ratio in AMERICAN_RATIOS:
            spot_v = SPOT_U * ratio
            european = exotics.exchange_option(
                SPOT_U, spot_v, market.volatility_u, market.volatility_v, market.correlation,
                market.expiry, q_u=market.yield_u, q_v=market.yield_v)
            american = exotics.exchange_option_american(
                SPOT_U, spot_v, market.volatility_u, market.volatility_v, market.correlation,
                market.expiry, q_u=market.yield_u, q_v=market.yield_v)
            on_grid = binomial_american_price(
                SPOT_U, spot_v, market, steps=1024, american=False)
            entries.append(
                {
                    "value_ratio": ratio,
                    "european": european,
                    "american": american,
                    "european_on_grid": on_grid,
                    "premium": american - european,
                    "premium_on_grid": american - on_grid,
                    "grid_residual": on_grid - european,
                    "intrinsic": max(spot_v - SPOT_U, 0.0),
                }
            )
        convergence = []
        for steps in CONVERGENCE_STEPS:
            price = exotics.exchange_option_american(
                SPOT_U, SPOT_U, market.volatility_u, market.volatility_v, market.correlation,
                market.expiry, q_u=market.yield_u, q_v=market.yield_v, steps=steps)
            european = exotics.exchange_option(
                SPOT_U, SPOT_U, market.volatility_u, market.volatility_v, market.correlation,
                market.expiry, q_u=market.yield_u, q_v=market.yield_v)
            convergence.append(
                {"steps": steps, "american": price, "gap_to_european": price - european}
            )
        families.append(
            {
                "market": name,
                "yield_u": market.yield_u,
                "yield_v": market.yield_v,
                "expiry": market.expiry,
                "spread_volatility": spread_volatility(market),
                "entries": entries,
                "convergence": convergence,
                "early_exercise_possible": market.yield_v > 0.0,
            }
        )
    return families


def build():
    hashes = {
        path: hashlib.sha256((PROJECT / path).read_bytes()).hexdigest() for path in SOURCE_PATHS
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "spot_u": SPOT_U,
        "contract": _family(
            _payoff_rows(),
            "Terminal payoffs of the exchange, better-of and worse-of contracts on one grid",
            hashes,
        ),
        "correlation": _family(
            _correlation_rows(),
            "Price and ratio volatility across rho, against the discounted forward spread",
            hashes,
        ),
        "rate": _family(
            _rate_rows(),
            "The independent reference priced at seven risk-free rates, with Hull's restatement",
            hashes,
        ),
        "american": _family(
            _american_rows(),
            "European, American and the early-exercise premium by moneyness, plus the grid residual",
            hashes,
            ["The American prices come from a finite CRR tree on V/U."],
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=VALIDATION)
    options = parser.parse_args()
    lesson = build()
    options.output_dir.mkdir(parents=True, exist_ok=True)
    (options.output_dir / "lesson-data.json").write_text(
        json.dumps(lesson, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    for family in lesson["correlation"]["data"]:
        entries = family["entries"]
        print(
            f"{family['market']}: rho {entries[0]['correlation']} -> {entries[-1]['correlation']}, "
            f"price {entries[0]['price']:.4f} -> {entries[-1]['price']:.4f}"
        )
    for family in lesson["rate"]["data"]:
        print(
            f"{family['market']}: reference spread over rates {family['reference_spread']:.3e}, "
            f"restatement residual {family['restatement_residual']:.3e}"
        )
    for family in lesson["american"]["data"]:
        exercise = max(entry["premium_on_grid"] for entry in family["entries"])
        grid = max(abs(entry["grid_residual"]) for entry in family["entries"])
        print(
            f"{family['market']}: qV={family['yield_v']}, max early exercise {exercise:.3e}, "
            f"max grid residual {grid:.3e}"
        )


if __name__ == "__main__":
    main()
