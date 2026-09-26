"""Compare the §27.2 public API against the independent saved reference."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from build_stochastic_volatility_reference import build
from hullkit import bsm, sabr
from hullkit import stochastic_volatility as sv

PROJECT = Path(__file__).resolve().parents[1]
REF = PROJECT / "docs/validation/section-27-2/reference.json"
RECORD = REF.with_name("numerical-check.json")
SOURCES = (
    "scripts/build_stochastic_volatility_reference.py",
    "scripts/verify_stochastic_volatility_numerics.py",
    "hullkit/src/hullkit/stochastic_volatility.py",
    "hullkit/src/hullkit/sabr.py",
)
MIXING = {"n_steps": 250, "n_paths": 200_000, "seed": 2702}
TOLERANCES = {
    "term_pde_currency": 5e-4,
    "mixing_standard_errors": 3.0,
    "heston_cos_currency": 1e-8,
    "rho_zero_symmetry_vol": 1e-10,
    "sabr_transcription_vol": 1e-12,
    "sabr_monte_carlo_standard_errors": 3.0,
    "sabr_monte_carlo_vol": 2e-3,
    "small_xi_currency": 1e-5,
}


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def evaluate():
    """Recompute every comparison, enforce the tolerances and return the record."""
    data = json.loads(REF.read_text(encoding="utf-8"))
    _require(data == build(), "saved independent reference differs from fresh computation")

    term = data["term_structure"]
    average = sv.average_variance_rate(term["durations"], term["volatilities"])
    _require(round(average, 3) == 0.065, "Hull's average variance rate 0.065 not reproduced")
    _require(round(math.sqrt(average), 3) == 0.255, "Hull's 25.5% not reproduced")
    term_errors = {
        strike: abs(
            sv.time_dependent_bsm_price(
                term["spot"], float(strike), term["rate"], term["durations"], term["volatilities"]
            )
            - row["pde"]
        )
        for strike, row in term["prices"].items()
    }
    arithmetic_gap = abs(
        term["prices"]["100.0"]["arithmetic_vol_bsm"] - term["prices"]["100.0"]["pde"]
    )

    heston = data["heston"]
    params = (
        heston["v0"],
        heston["reversion"],
        heston["long_run"],
        heston["vol_of_variance"],
    )
    expected = sv.expected_average_variance(
        heston["v0"], heston["reversion"], heston["long_run"], heston["expiry"]
    )
    _require(abs(expected - heston["expected_average_variance"]) < 1e-15, "E[V_bar] differs")
    samples = sv.simulate_average_variance(*params, heston["expiry"], **MIXING)
    sample_mean_z = (samples.mean() - expected) / (samples.std(ddof=1) / math.sqrt(samples.size))
    mixing_z = []
    for strike, reference in zip(
        heston["strikes"], heston["smiles"]["+0.0"]["prices"], strict=True
    ):
        price, error = sv.mixing_price(
            heston["spot"], strike, heston["rate"], heston["expiry"], samples
        )
        mixing_z.append((price - reference) / error)
    differences = [
        sv_price - flat
        for sv_price, flat in zip(
            heston["smiles"]["+0.0"]["prices"], heston["flat_prices"], strict=True
        )
    ]
    by_strike = dict(zip(heston["strikes"], differences, strict=True))
    _require(by_strike[100.0] < 0.0, "BSM with E[V_bar] does not overprice the ATM option")
    _require(by_strike[60.0] > 0.0 and by_strike[156.0] > 0.0, "wings are not underpriced")
    overpriced = [k for k, d in by_strike.items() if d < 0.0]
    _require(
        overpriced == [k for k in heston["strikes"] if min(overpriced) <= k <= max(overpriced)],
        "overpriced strikes are not one contiguous near-the-money band",
    )

    cos_errors = []
    slopes = {}
    for label, row in heston["smiles"].items():
        rho = float(label)
        for strike, reference in zip(heston["strikes"], row["prices"], strict=True):
            cos_errors.append(
                abs(
                    sv.heston_price(
                        heston["spot"], strike, heston["rate"], heston["expiry"], *params, rho
                    )
                    - reference
                )
            )
        vols = dict(zip(heston["strikes"], row["implied_vol"], strict=True))
        slopes[label] = (vols[104.0] - vols[96.0]) / 8.0
    _require(slopes["-0.7"] < 0.0 < slopes["+0.7"], "correlation does not set the skew direction")
    symmetry = max(abs(row["upper_vol"] - row["lower_vol"]) for row in heston["rho_zero_symmetry"])
    small_xi = abs(
        sv.heston_price(
            heston["spot"], 100.0, heston["rate"], heston["expiry"], 0.04, 1.5, 0.04, 1e-3, 0.0
        )
        - float(bsm.call_price(heston["spot"], 100.0, heston["rate"], 0.2, heston["expiry"]))
    )
    deterministic = sv.mixing_price(
        heston["spot"], 100.0, heston["rate"], heston["expiry"], [expected, expected]
    )
    deterministic_error = abs(
        deterministic[0]
        - float(bsm.call_price(heston["spot"], 100.0, heston["rate"], math.sqrt(expected), 1.0))
    )

    smile = data["sabr"]
    transcription = []
    groups = [(float(k), smile["rho_group_nu"], v) for k, v in smile["rho_group"].items()]
    groups += [(smile["nu_group_rho"], float(k), v) for k, v in smile["nu_group"].items()]
    for rho, nu, vols in groups:
        for strike, reference in zip(smile["strikes"], vols, strict=True):
            library = sabr.sabr_implied_vol(
                smile["forward"], strike, smile["expiry"], smile["sigma0"], smile["beta"], rho, nu
            )
            transcription.append(abs(library - reference))
    atm_gap = abs(smile["atm"]["near_atm_vol"] - smile["atm"]["limit_vol"])
    rows = smile["monte_carlo"]["rows"]
    mc_vol = [abs(row["hull_formula_vol"] - row["implied_vol"]) for row in rows]
    mc_z = [
        abs(row["hull_formula_vol"] - row["implied_vol"]) / row["implied_vol_standard_error"]
        for row in rows
    ]
    strikes = smile["strikes"]
    _require(len(set(strikes)) == len(strikes), "duplicate SABR strikes")
    near = next(i for i, k in enumerate(strikes) if abs(k - smile["forward"]) < 1e-12)

    def slope(vols):
        return vols[near + 1] - vols[near - 1]

    def curvature(vols):
        return vols[0] + vols[-1] - 2 * vols[near]

    _require(
        slope(smile["rho_group"]["-0.6"]) < 0.0 < slope(smile["rho_group"]["+0.6"]),
        "SABR rho does not set the slope",
    )
    zero = smile["rho_group"]["+0.0"]
    _require(0 < int(np.argmin(zero)) < len(zero) - 1, "rho=0 SABR smile has no interior minimum")
    curvatures = [curvature(smile["nu_group"][key]) for key in ("0.2", "0.4", "0.8")]
    _require(curvatures[0] < curvatures[1] < curvatures[2], "larger nu does not deepen the smile")

    measured = {
        "average_variance_rate": average,
        "average_volatility": math.sqrt(average),
        "term_pde_max_abs_currency": max(term_errors.values()),
        "term_arithmetic_vol_gap_atm_currency": arithmetic_gap,
        "mixing_sample_mean_z": sample_mean_z,
        "mixing_max_abs_z_26_strikes": max(abs(z) for z in mixing_z),
        "overpriced_strike_band": [min(overpriced), max(overpriced)],
        "atm_price_minus_flat_bsm": by_strike[100.0],
        "heston_cos_max_abs_currency_78_prices": max(cos_errors),
        "heston_atm_vol_slope_per_currency": slopes,
        "rho_zero_symmetry_max_vol": symmetry,
        "small_xi_1e-3_minus_bsm_currency": small_xi,
        "deterministic_mixing_minus_bsm_currency": deterministic_error,
        "sabr_transcription_max_abs_vol_216": max(transcription),
        "sabr_atm_limit_gap_vol": atm_gap,
        "sabr_monte_carlo_max_abs_vol": max(mc_vol),
        "sabr_monte_carlo_max_abs_z": max(mc_z),
        "sabr_smile_curvature_by_nu": dict(zip(("0.2", "0.4", "0.8"), curvatures, strict=True)),
    }
    checks = {
        "term_pde_currency": measured["term_pde_max_abs_currency"],
        "mixing_standard_errors": measured["mixing_max_abs_z_26_strikes"],
        "heston_cos_currency": measured["heston_cos_max_abs_currency_78_prices"],
        "rho_zero_symmetry_vol": symmetry,
        "sabr_transcription_vol": measured["sabr_transcription_max_abs_vol_216"],
        "sabr_monte_carlo_standard_errors": measured["sabr_monte_carlo_max_abs_z"],
        "sabr_monte_carlo_vol": measured["sabr_monte_carlo_max_abs_vol"],
        "small_xi_currency": small_xi,
    }
    for name, value in checks.items():
        _require(value < TOLERANCES[name], f"{name} tolerance exceeded: {value}")
    _require(abs(sample_mean_z) < 3.0, "simulated E[V_bar] outside 3 SE")
    _require(deterministic_error < 1e-12, "deterministic mixing is not BSM")
    _require(atm_gap < 1e-6, "SABR ATM limit does not match the general formula")
    return {
        "section": "27.2",
        "status": "PASS",
        "method": (
            "time-dependent-vol Crank–Nicolson PDE; Gil-Pelaez Heston quadrature against "
            "hullkit COS and the Hull–White conditional Monte Carlo; transcription of "
            "Hull's SABR formula and an Euler SABR Monte Carlo"
        ),
        "mixing_simulation": MIXING,
        "measured": measured,
        "tolerances": TOLERANCES,
        "artifact_sha256": _digest(REF),
        "source_sha256": {relative: _digest(PROJECT / relative) for relative in SOURCES},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    record = evaluate()
    payload = json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.write:
        RECORD.write_text(payload, encoding="utf-8")
    elif not RECORD.is_file() or RECORD.read_text(encoding="utf-8") != payload:
        raise SystemExit("FAIL: §27.2 numerical record is stale")
    print("PASS: §27.2 independent checks", json.dumps(record["measured"], ensure_ascii=False))


if __name__ == "__main__":
    main()
