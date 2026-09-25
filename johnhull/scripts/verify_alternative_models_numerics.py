"""Compare §27.1 public prices against the independent saved reference."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from build_alternative_models_reference import build
from hullkit import alternative_models as am

PROJECT = Path(__file__).resolve().parents[1]
REF = PROJECT / "docs/validation/section-27-1/reference.json"
RECORD = REF.with_name("numerical-check.json")
SOURCES = (
    "scripts/build_alternative_models_reference.py",
    "scripts/verify_alternative_models_numerics.py",
    "hullkit/src/hullkit/alternative_models.py",
)


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate():
    """Recompute and compare every saved price, with explicit tolerances."""
    data = json.loads(REF.read_text(encoding="utf-8"))
    if data != build():
        raise AssertionError("saved independent reference differs from fresh computation")
    cev = data["cev"]
    cev_errors = {
        strike: abs(am.cev_price(100, float(strike), 0.05, 0.2 * 100**0.2, 0.5, 0.8) - reference)
        for strike, reference in cev["pde_beta_0_8_calls"].items()
    }
    merton = data["merton"]
    merton_errors = [
        abs(am.merton_jump_price(100, strike, 0.05, 0.2, 0.25, 1, -0.1, 0.15) - price)
        for strike, price in zip(merton["strikes"], merton["prices"], strict=True)
    ]
    vg = data["variance_gamma"]
    vg_errors = [
        abs(am.variance_gamma_price(100, strike, 0, 0.2, 0.5, 0.5, 0.1) - price)
        for strike, price in zip(vg["strikes"], vg["prices"], strict=True)
    ]
    table = data["poisson_table"]
    if np.round(table["probability"], 4).tolist() != [
        0.3679,
        0.3679,
        0.1839,
        0.0613,
        0.0153,
        0.0031,
        0.0005,
        0.0001,
        0.0,
    ]:
        raise AssertionError("Hull Table 27.1 displayed probabilities differ")
    if max(cev_errors.values()) >= 0.002 or max(merton_errors) >= 1e-9 or max(vg_errors) >= 2e-4:
        raise AssertionError("alternative-model independent price tolerance exceeded")
    return {
        "section": "27.1",
        "status": "PASS",
        "method": "CEV local-volatility PDE; original-Poisson conditional Merton; VG gamma-density integration",
        "measured": {
            "cev_pde_max_abs_currency": max(cev_errors.values()),
            "merton_26_strikes_max_abs_currency": max(merton_errors),
            "vg_26_strikes_max_abs_currency": max(vg_errors),
            "poisson_table_probability_sum_m0_to_8": sum(table["probability"]),
        },
        "tolerances": {"cev_currency": 0.002, "merton_currency": 1e-9, "vg_currency": 2e-4},
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
        raise SystemExit("FAIL: §27.1 numerical record is stale")
    print("PASS: §27.1 independent prices", record["measured"])


if __name__ == "__main__":
    main()
