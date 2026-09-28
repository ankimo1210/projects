"""Cross-check hullkit.american_mc with the independent §27.8 reference."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from build_american_mc_reference import (
    BIAS_EVALUATION,
    BIAS_REPLICATIONS,
    BIAS_SIZES,
    DATE_COUNTS,
    DATES_EVALUATION,
    DATES_FIT,
    EXCHANGE,
    PUT,
    SEED,
    build,
    exchange_paths,
    put_paths,
)
from hullkit.american_mc import (
    apply_boundary,
    apply_least_squares,
    exercise_boundary,
    least_squares,
)

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-8/numerical-check.json"
REF = OUT.with_name("reference.json")
SOURCES = (
    "scripts/build_american_mc_reference.py",
    "scripts/verify_american_mc_numerics.py",
    "hullkit/src/hullkit/american_mc.py",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _put(strike):
    return lambda s: np.maximum(strike - s, 0.0)


def _gap(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        raise AssertionError(f"shape mismatch {a.shape} != {b.shape}")
    return float(np.max(np.abs(a - b))) if a.size else 0.0


def _encode(value):
    """The reference writes the never-exercise candidate and open interval ends as strings."""
    if math.isinf(value):
        return "-inf" if value < 0 else "+inf"
    return value


def _hand(hand, strike):
    """Largest gap between hullkit and the reference on the eight paths for ``strike``."""
    paths = np.array(hand["paths"])
    times = tuple(hand["times"])
    reference = hand if strike == hand["strike"] else hand["problem_27_22"]
    lsm_ref, boundary_ref = reference["least_squares"], reference["boundary"]
    lsm = least_squares(paths, _put(strike), hand["rate"], times)
    boundary = exercise_boundary(paths, _put(strike), hand["rate"], times)
    gaps = [
        _gap(lsm.cash_flows, lsm_ref["cash_flows"]),
        abs(lsm.continuation_value - lsm_ref["value"]),
        _gap(boundary.cash_flows, boundary_ref["cash_flows"]),
        abs(boundary.continuation_value - boundary_ref["value"]),
    ]
    for step in lsm.steps:
        saved = lsm_ref["steps"][str(int(step.time))]
        if list(step.paths) != saved["paths"] or list(step.exercised) != saved["exercised"]:
            raise AssertionError(f"least-squares paths differ at t={step.time} for K={strike}")
        gaps += [
            _gap(step.coefficients, saved["coefficients"]),
            _gap(step.continuation, saved["continuation"]),
        ]
    for step in boundary.steps:
        saved = boundary_ref["steps"][str(int(step.time))]
        candidates = [_encode(c) for c in step.candidates]
        interval = [_encode(c) for c in step.interval]
        threshold = _encode(step.threshold)
        if candidates != saved["candidates"] or [threshold, interval] != [
            saved["threshold"],
            saved["interval"],
        ]:
            raise AssertionError(f"boundary search differs at t={step.time} for K={strike}")
        gaps += [_gap(step.averages, saved["averages"]), _gap(step.values, saved["values"])]
    return max(gaps)


def _bias(reference):
    """Recompute every replication of the bias study with hullkit."""
    times = (1.0, 2.0, 3.0)
    payoff = _put(PUT["strike"])
    keys = ("lsm_in", "lsm_out", "boundary_in", "boundary_out")
    gap = 0.0
    for i, n in enumerate(BIAS_SIZES):
        runs = {key: [] for key in keys}
        for rep in range(BIAS_REPLICATIONS):
            fit = put_paths(n, 3, [SEED, 3, n, rep, 0])
            fresh = put_paths(BIAS_EVALUATION, 3, [SEED, 3, n, rep, 1])
            lsm = least_squares(fit, payoff, PUT["rate"], times)
            boundary = exercise_boundary(fit, payoff, PUT["rate"], times)
            runs["lsm_in"].append(lsm.continuation_value)
            runs["lsm_out"].append(
                apply_least_squares(lsm, fresh, payoff, PUT["rate"], times).continuation_value
            )
            runs["boundary_in"].append(boundary.continuation_value)
            runs["boundary_out"].append(
                apply_boundary(boundary, fresh, payoff, PUT["rate"], times).continuation_value
            )
        for key in keys:
            gap = max(gap, abs(float(np.mean(runs[key])) - reference[key]["mean"][i]))
    return gap


def _discounted(value, times):
    return value.cash_flows @ np.exp(-PUT["rate"] * np.asarray(times))


def _paired(first, second):
    difference = first - second
    return float(difference.mean()), float(difference.std(ddof=1) / math.sqrt(difference.size))


def _dates(reference):
    payoff = _put(PUT["strike"])
    gap = 0.0
    for i, dates in enumerate(DATE_COUNTS):
        times = tuple(PUT["maturity"] * k / dates for k in range(1, dates + 1))
        fit = put_paths(DATES_FIT, dates, [SEED, dates, 0])
        fresh = put_paths(DATES_EVALUATION, dates, [SEED, dates, 1])
        fitted = {
            "lsm2": least_squares(fit, payoff, PUT["rate"], times, degree=2),
            "lsm3": least_squares(fit, payoff, PUT["rate"], times, degree=3),
        }
        values = {}
        for key, result in fitted.items():
            value = apply_least_squares(result, fresh, payoff, PUT["rate"], times)
            values[key] = _discounted(value, times)
            gap = max(
                gap,
                abs(result.continuation_value - reference[key]["in_sample"][i]),
                abs(value.continuation_value - reference[key]["value"][i]),
                abs(value.standard_error - reference[key]["standard_error"][i]),
            )
        boundary = exercise_boundary(fit, payoff, PUT["rate"], times)
        value = apply_boundary(boundary, fresh, payoff, PUT["rate"], times)
        values["boundary"] = _discounted(value, times)
        gap = max(
            gap,
            abs(boundary.continuation_value - reference["boundary"]["in_sample"][i]),
            abs(value.continuation_value - reference["boundary"]["value"][i]),
        )
        for name, (first, second) in {
            "lsm3_minus_lsm2": ("lsm3", "lsm2"),
            "boundary_minus_lsm2": ("boundary", "lsm2"),
        }.items():
            mean, error = _paired(values[first], values[second])
            saved = reference["paired"][name]
            gap = max(gap, abs(mean - saved["mean"][i]), abs(error - saved["standard_error"][i]))
    return gap


def _exchange(reference):
    times = tuple(
        EXCHANGE["maturity"] * k / EXCHANGE["dates"] for k in range(1, EXCHANGE["dates"] + 1)
    )

    def payoff(states):
        return np.maximum(states[:, 0] - states[:, 1], 0.0)

    fit = exchange_paths(DATES_FIT, [SEED, 99, 0])
    fresh = exchange_paths(DATES_EVALUATION, [SEED, 99, 1])
    fitted = least_squares(fit, payoff, EXCHANGE["rate"], times)
    value = apply_least_squares(fitted, fresh, payoff, EXCHANGE["rate"], times)
    return max(
        abs(fitted.continuation_value - reference["in_sample"]["raw"]),
        abs(value.continuation_value - reference["out_of_sample"]["raw"]),
    )


def evaluate():
    """Tie the public functions to the reference, then check the claims made from it."""
    reference = json.loads(REF.read_text(encoding="utf-8"))
    if reference != build():
        raise AssertionError("saved reference differs from fresh independent computation")
    hand = reference["hand_example"]
    printed = hand["printed"]
    hand_gap = max(_hand(hand, hand["strike"]), _hand(hand, hand["problem_27_22"]["strike"]))
    bias_gap = _bias(reference["bias"])
    dates_gap = _dates(reference["dates"])
    exchange_gap = _exchange(reference["exchange"])
    if max(hand_gap, bias_gap, dates_gap, exchange_gap) >= 1e-12:
        raise AssertionError("hullkit.american_mc differs from the independent reference")

    lsm = hand["least_squares"]
    # Hull prints every coefficient rounded to three decimals except c at t=2:
    # -1.813576 rounds to -1.814, but the book prints -1.813.
    off_half_unit = [
        f"{t}:{'abc'[j]}"
        for t in ("2", "1")
        for j, (fitted, shown) in enumerate(
            zip(lsm["steps"][t]["coefficients"], printed["coefficients"][t], strict=True)
        )
        if abs(fitted - shown) > 5e-4
    ]
    rounding = {
        "coefficients": max(
            _gap(lsm["steps"][t]["coefficients"], printed["coefficients"][t]) for t in ("1", "2")
        ),
        "coefficients_off_half_unit": off_half_unit,
        "continuation_exact": max(
            _gap(lsm["steps"][t]["continuation"], printed["continuation"][t]) for t in ("1", "2")
        ),
        "continuation_rounded": max(
            _gap(
                hand["rounded_coefficients"]["steps"][t]["continuation"], printed["continuation"][t]
            )
            for t in ("1", "2")
        ),
        "boundary_averages": max(
            _gap(hand["boundary"]["steps"][t]["averages"], printed["boundary_averages"][t])
            for t in ("1", "2")
        ),
    }
    if not (
        rounding["coefficients"] < 1e-3
        and off_half_unit == ["2:c"]
        and rounding["continuation_rounded"] < 7e-5 < 5e-4 < rounding["continuation_exact"] < 6e-4
        and rounding["boundary_averages"] <= 5e-5 + 1e-12
        and round(lsm["value"], 4) == printed["value"]
        and round(hand["boundary"]["value"], 4) == 0.1209
        and round(round(hand["boundary"]["value_at_1"], 4) * math.exp(-0.06), 4)
        == printed["boundary_value"]
    ):
        raise AssertionError("Hull's printed eight-path values are not reproduced as stated")

    exact = reference["exact"]
    rows = [*exact["bermudan"], reference["exchange"]["ratio_bermudan"]]
    grids = {
        "quadrature_change": max(row["quadrature_change"] for row in rows),
        "crank_nicolson_gap": max(row["crank_nicolson_gap"] for row in rows),
        "nested_three_dates_gap": exact["nested_three_dates"]["gap"],
        "american_crank_nicolson_gap": exact["american"]["crank_nicolson_gap"],
        "section_15_quadrature_change": reference["section_15"]["bermudan"]["quadrature_change"],
        "section_15_crank_nicolson_gap": reference["section_15"]["bermudan"]["crank_nicolson_gap"],
        "section_15_american_crank_nicolson_gap": reference["section_15"]["american"][
            "crank_nicolson_gap"
        ],
    }
    if not (
        grids["quadrature_change"] < 1e-8
        and grids["crank_nicolson_gap"] < 1e-6
        and grids["nested_three_dates_gap"] < 1e-8
        and grids["american_crank_nicolson_gap"] < 5e-6
        and grids["section_15_quadrature_change"] < 5e-7
        and grids["section_15_crank_nicolson_gap"] < 5e-5
        and grids["section_15_american_crank_nicolson_gap"] < 5e-5
    ):
        raise AssertionError("the exact-value methods disagree or are unconverged")
    values = [row["value"] for row in exact["bermudan"]]
    if not all(
        a < b for a, b in zip(values, [*values[1:], exact["american"]["value"]], strict=True)
    ):
        raise AssertionError("Bermudan values do not rise toward the American value")

    bias = reference["bias"]
    z = {
        key: [
            (m - bias["exact"]) / e
            for m, e in zip(bias[key]["mean"], bias[key]["standard_error"], strict=True)
        ]
        for key in ("lsm_in", "lsm_out", "boundary_in", "boundary_out")
    }
    small = [i for i, n in enumerate(bias["sizes"]) if n <= 1000]
    claims = {
        "boundary_in_sample_above_exact": all(v > 2 for v in z["boundary_in"]),
        "boundary_out_of_sample_below_exact_to_1000_paths": all(
            z["boundary_out"][i] < -2 for i in small
        ),
        "lsm_out_of_sample_below_exact_to_1000_paths": all(z["lsm_out"][i] < -2 for i in small),
        "lsm_in_sample_within_two_errors": all(abs(v) < 2 for v in z["lsm_in"]),
        "out_of_sample_never_two_errors_above_exact": all(
            v < 2 for key in ("lsm_out", "boundary_out") for v in z[key]
        ),
        "boundary_in_sample_above_out_of_sample": all(
            a > b
            for a, b in zip(bias["boundary_in"]["mean"], bias["boundary_out"]["mean"], strict=True)
        ),
    }
    dates = reference["dates"]
    dates_z = {
        key: [
            (v - x) / e
            for v, x, e in zip(
                dates[key]["value"], dates["exact"], dates[key]["standard_error"], strict=True
            )
        ]
        for key in ("lsm2", "lsm3", "boundary")
    }
    claims["dates_within_two_errors"] = all(abs(v) < 2 for row in dates_z.values() for v in row)
    paired_z = {
        name: [m / e for m, e in zip(row["mean"], row["standard_error"], strict=True)]
        for name, row in dates["paired"].items()
    }
    european = dates["european"]
    european_z = [
        (m - european["value"]) / e
        for m, e in zip(european["mean"], european["standard_error"], strict=True)
    ]
    at = {count: i for i, count in enumerate(dates["counts"])}
    claims["cubic_and_quadratic_within_two_errors_to_12_dates"] = all(
        abs(paired_z["lsm3_minus_lsm2"][at[n]]) < 2 for n in (3, 6, 12)
    )
    claims["cubic_above_quadratic_at_24_and_48_dates"] = all(
        paired_z["lsm3_minus_lsm2"][at[n]] > 2 for n in (24, 48)
    )
    claims["all_three_above_exact_at_24_dates"] = all(row[at[24]] > 0 for row in dates_z.values())
    claims["european_check_high_only_at_24_dates"] = european_z[at[24]] > 2 and all(
        abs(v) < 2 for i, v in enumerate(european_z) if i != at[24]
    )
    exchange = reference["exchange"]
    exchange_z = (exchange["out_of_sample"]["value"] - exchange["exact"]) / exchange[
        "out_of_sample"
    ]["standard_error"]
    claims["exchange_within_two_errors"] = abs(exchange_z) < 2
    section_15 = reference["section_15"]
    claims["section_15_bermudan_below_american"] = (
        0 < section_15["american"]["value"] - section_15["bermudan"]["value"] < 0.01
    )
    claims["control_variate_tightens_exchange"] = (
        exchange["out_of_sample"]["standard_error"]
        < 0.8 * exchange["out_of_sample"]["raw_standard_error"]
    )
    if not all(claims.values()):
        raise AssertionError(f"claims fail: {[k for k, v in claims.items() if not v]}")

    return {
        "section": "27.8",
        "status": "PASS",
        "method": (
            "Hull's eight paths by numpy.polyfit and a direct boundary search; exact Bermudan "
            "values by lognormal quadrature, checked by Crank-Nicolson and (three dates) nested "
            "Black-Scholes integrals; American limit by CRR, checked by Crank-Nicolson; seeded "
            "fit/fresh simulations and paired policy differences recomputed with hullkit"
        ),
        "tolerances": {
            "hullkit_currency": 1e-12,
            "printed_coefficients": 1e-3,
            "printed_coefficients_half_unit_except_t2_c": 5e-4,
            "printed_continuation_with_printed_coefficients": 7e-5,
            "printed_boundary_averages_half_unit": 5e-5,
            "quadrature_change": 1e-8,
            "crank_nicolson_gap_bermudan": 1e-6,
            "nested_three_dates_gap": 1e-8,
            "crank_nicolson_gap_american": 5e-6,
            "bias_z": 2.0,
        },
        "measured": {
            "hand_gap": hand_gap,
            "bias_gap": bias_gap,
            "dates_gap": dates_gap,
            "exchange_gap": exchange_gap,
            "printed_rounding": rounding,
            "exact_value_checks": grids,
            "bias_z": z,
            "dates_z": dates_z,
            "paired_z": paired_z,
            "european_z": european_z,
            "exchange_z": exchange_z,
            "claims": claims,
        },
        "source_sha256": {name: sha(PROJECT / name) for name in SOURCES},
        "artifact_sha256": sha(REF),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(evaluate(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: §27.8 numerical record is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §27.8 eight paths, exact Bermudan values and seeded fit/fresh simulations")


if __name__ == "__main__":
    main()
