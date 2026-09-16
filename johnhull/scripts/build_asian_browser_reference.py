"""Independent browser pins for §26.13; never imports the lesson or hullkit pricer.

Every displayed number is pinned either to the frozen M4a-style reference table
in prices.json or to algebra recomputed here (payoffs, continuous moments by
quadrature, the matched lognormal density and its skewness).
"""

import hashlib
import json
import math
from pathlib import Path

from scipy.integrate import quad

PROJECT = Path(__file__).resolve().parents[1]
VALIDATION = PROJECT / "docs/validation/section-26-13"
SOURCE_PATHS = (
    "scripts/build_asian_browser_reference.py",
    "scripts/build_asian_reference.py",
    "docs/validation/section-26-13/prices.json",
    "docs/validation/section-26-13/numerical-check.json",
)
EXAMPLE_PATH = [100.0, 112.0, 94.0, 121.0, 90.0, 105.0, 84.0, 116.0, 108.0]
DISTRIBUTION_MARKETS = ("low-vol-short", "positive-carry", "high-vol-long")
OBSERVATION_COUNTS = (12, 52, 250)
STRIKE = 100.0


def _normal_cdf(x):
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _black(forward, strike, vol, rate, expiry, kind):
    """Black 76 written out here; the pricer under test is never imported."""
    scale = vol * math.sqrt(expiry)
    d1 = (math.log(forward / strike) + 0.5 * scale**2) / scale
    d2 = d1 - scale
    if kind == "call":
        value = forward * _normal_cdf(d1) - strike * _normal_cdf(d2)
    else:
        value = strike * _normal_cdf(-d2) - forward * _normal_cdf(-d1)
    return math.exp(-rate * expiry) * value


def _continuous_moments(spot, rate, dividend, sigma, expiry):
    """E[A] and E[A^2] of the continuous average by quadrature, not by formula."""
    drift = rate - dividend
    first, error = quad(lambda t: spot * math.exp(drift * t), 0.0, expiry, epsabs=1e-13)
    assert error < 1e-9
    delta = drift + sigma**2

    def inner(t):
        if abs(delta * t) < 1e-10:
            return t * (1.0 + 0.5 * delta * t)
        return math.expm1(delta * t) / delta

    second, error = quad(
        lambda t: spot**2 * math.exp(drift * t) * inner(t), 0.0, expiry, epsabs=1e-13
    )
    assert error < 1e-7
    return first / expiry, 2.0 * second / expiry**2


def _matched(first, second, expiry):
    scale = math.sqrt(math.log(second / first**2))
    return scale / math.sqrt(expiry), scale


def _payoff_pins():
    observed = EXAMPLE_PATH[1:]
    average = sum(observed) / len(observed)
    terminal = EXAMPLE_PATH[-1]
    return {
        "path": EXAMPLE_PATH,
        "strike": STRIKE,
        "average": average,
        "terminal": terminal,
        "payoffs": {
            "average_price": [max(average - STRIKE, 0.0), max(STRIKE - average, 0.0)],
            "average_strike": [max(terminal - average, 0.0), max(average - terminal, 0.0)],
            "vanilla_call": max(terminal - STRIKE, 0.0),
        },
    }


def _market_parameters(rows, market):
    row = next(r for r in rows if r["market"] == market)
    return {k: row[k] for k in ("rate", "dividend", "volatility", "expiry")}


def _distribution_pins(rows):
    pins = []
    for market in DISTRIBUTION_MARKETS:
        parameters = _market_parameters(rows, market)
        times = [
            (index + 1) * parameters["expiry"] / 52 for index in range(52)
        ]
        forwards = [
            STRIKE * math.exp((parameters["rate"] - parameters["dividend"]) * t) for t in times
        ]
        first = sum(forwards) / len(times)
        second = sum(
            f_i * f_j * math.exp(parameters["volatility"] ** 2 * min(t_i, t_j))
            for f_i, t_i in zip(forwards, times, strict=True)
            for f_j, t_j in zip(forwards, times, strict=True)
        ) / len(times) ** 2
        matched, scale = _matched(first, second, parameters["expiry"])
        pins.append(
            {
                "market": market,
                **parameters,
                "observations": 52,
                "moment_1": first,
                "moment_2": second,
                "matched_volatility": matched,
                "location": math.log(first) - 0.5 * scale**2,
                "scale": scale,
                "fitted_skewness": (math.exp(scale**2) + 2.0) * math.sqrt(math.expm1(scale**2)),
            }
        )
    return pins


def _observation_pins(rows):
    pins = []
    for market in sorted({row["market"] for row in rows}):
        parameters = _market_parameters(rows, market)
        entries = []
        for count in OBSERVATION_COUNTS:
            row = next(
                r
                for r in rows
                if r["market"] == market
                and r["contract"] == "call"
                and r["spot_ratio"] == 1.0
                and r["observations"] == count
            )
            entries.append(
                {
                    "observations": count,
                    "turnbull_wakeman": row["turnbull_wakeman"],
                    "reference": row["reference"],
                    "standard_error": row["standard_error"],
                    "geometric": row["geometric"],
                }
            )
        first, second = _continuous_moments(
            STRIKE,
            parameters["rate"],
            parameters["dividend"],
            parameters["volatility"],
            parameters["expiry"],
        )
        matched, _ = _matched(first, second, parameters["expiry"])
        pins.append(
            {
                "market": market,
                **parameters,
                "entries": entries,
                "continuous_turnbull_wakeman": _black(
                    first, STRIKE, matched, parameters["rate"], parameters["expiry"], "call"
                ),
            }
        )
    return pins


def _error_pins(rows):
    pins = []
    for row in rows:
        if row["observations"] != 52 or row["reference"] <= 0.5:
            continue
        pins.append(
            {
                "market": row["market"],
                "contract": row["contract"],
                "spot_ratio": row["spot_ratio"],
                "scale": row["volatility"] * math.sqrt(row["expiry"]),
                "relative_error_percent": 100.0
                * (row["turnbull_wakeman"] - row["reference"])
                / row["reference"],
            }
        )
    return pins


def build():
    rows = json.loads((VALIDATION / "prices.json").read_text())["rows"]
    record = json.loads((VALIDATION / "numerical-check.json").read_text())
    extremes = record["approximation_error"]
    return {
        "method": (
            "Displayed values are pinned to the frozen independent table in prices.json and to "
            "algebra recomputed here; no hullkit pricer and no lesson module is imported."
        ),
        "source_sha256": {
            path: hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()
            for path in SOURCE_PATHS
        },
        "payoff": _payoff_pins(),
        "distribution": _distribution_pins(rows),
        "observations": _observation_pins(rows),
        "errors": _error_pins(rows),
        "record_extremes": {
            key: {
                k: extremes[key][k]
                for k in ("market", "contract", "spot_ratio", "observations", "relative_error")
            }
            for key in ("largest_overprice", "largest_underprice")
        },
        "limits": [
            "定義した折れ線の例であり、GBM標本ではない",
            "今日（0）は平均に入らない",
            "価格ではなく満期給付である",
            "固定シード",
            "近似誤差",
            "幾何平均",
            "σ√T",
        ],
    }


def main():
    reference = build()
    path = VALIDATION / "browser-reference.json"
    path.write_text(json.dumps(reference, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(f"wrote {path.relative_to(PROJECT)}")
    for row in reference["observations"]:
        print(
            f"  {row['market']}: continuous={row['continuous_turnbull_wakeman']:.6f}, "
            f"m=250 tw={row['entries'][-1]['turnbull_wakeman']:.6f}"
        )
    shown = [abs(row["relative_error_percent"]) for row in reference["errors"]]
    print(f"  error pins={len(shown)}, largest shown={max(shown):.3f}%")


if __name__ == "__main__":
    main()
