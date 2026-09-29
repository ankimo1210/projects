"""Cross-check Hull GE §26.2 perpetual option prices against an independent reference."""

import argparse
import copy
import hashlib
import json
import math
from itertools import pairwise
from pathlib import Path

from build_perpetual_reference import MATURITIES, STEPS_PER_YEAR, crr_american
from hullkit.perpetual_american import perpetual_option

PROJECT = Path(__file__).resolve().parents[1]
REFERENCE = PROJECT / "docs/validation/section-26-2/reference.json"
RECORD = REFERENCE.with_name("numerical-check.json")
SOURCES = (
    "scripts/build_perpetual_reference.py",
    "scripts/verify_perpetual_numerics.py",
    "hullkit/src/hullkit/perpetual_american.py",
)
PRICE_ATOL = 2e-10
BOUNDARY_ATOL = 2e-10
EXPONENT_ATOL = 2e-12
IDENTITY_ATOL = 2e-12
LATTICE_FINAL_ATOL = 0.1


def _require(condition, message, findings):
    if not condition:
        findings.append(message)


def evaluate(reference):
    """Return differences between the saved independent results and the public API."""
    findings = []
    errors = {"price": 0.0, "boundary": 0.0, "exponent": 0.0}
    _require(reference.get("section") == "26.2", "wrong section", findings)
    cases = reference.get("cases", [])
    _require(len(cases) >= 6, "missing parameter cases", findings)
    for case in cases:
        label, p = case["label"], case["parameters"]
        market = dict(
            spot=p["spot"],
            strike=p["strike"],
            r=p["rate"],
            q=p["yield"],
            sigma=p["sigma"],
        )
        for kind, exponent_key, intrinsic_delta in (
            ("call", "a1", 1.0),
            ("put", "a2", -1.0),
        ):
            saved = case[kind]
            actual = perpetual_option(kind, **market)
            price_error = abs(actual.price - saved["value"])
            exponent_error = abs(actual.exponent - case[exponent_key])
            errors["price"] = max(errors["price"], price_error)
            errors["exponent"] = max(errors["exponent"], exponent_error)
            _require(price_error <= PRICE_ATOL, f"{label} {kind} value differs", findings)
            _require(
                exponent_error <= EXPONENT_ATOL,
                f"{label} {kind} exponent differs",
                findings,
            )
            if saved["boundary_kind"] == "infinite":
                _require(
                    kind == "call" and p["yield"] == 0.0 and saved["boundary"] is None,
                    f"{label} invalid infinite boundary reference",
                    findings,
                )
                _require(
                    math.isinf(actual.boundary) and actual.price == p["spot"],
                    f"{label} zero-yield call limit differs",
                    findings,
                )
            else:
                if kind == "call" and p["yield"] == 0.0:
                    findings.append(f"{label} zero-yield call boundary must be infinite")
                    continue
                boundary_error = abs(actual.boundary - saved["boundary"])
                errors["boundary"] = max(errors["boundary"], boundary_error)
                _require(
                    boundary_error <= BOUNDARY_ATOL,
                    f"{label} {kind} boundary differs",
                    findings,
                )
                for field in ("matching_residual", "smooth_pasting_residual"):
                    _require(
                        abs(saved[field]) <= IDENTITY_ATOL,
                        f"{label} {kind} {field} differs",
                        findings,
                    )
                at_boundary = perpetual_option(
                    kind, saved["boundary"], p["strike"], p["rate"], p["sigma"], p["yield"]
                )
                _require(
                    abs(at_boundary.price - saved["boundary_intrinsic"]) <= PRICE_ATOL,
                    f"{label} {kind} value matching differs",
                    findings,
                )
                _require(
                    abs(at_boundary.delta - intrinsic_delta) <= IDENTITY_ATOL,
                    f"{label} {kind} smooth pasting differs",
                    findings,
                )
            upper_bound = p["spot"] if kind == "call" else p["strike"]
            _require(
                0.0 <= actual.price <= upper_bound + 1e-12,
                f"{label} {kind} no-arbitrage bound fails",
                findings,
            )
            rows = case["lattice"]["rows"]
            _require(len(rows) == len(MATURITIES), f"{label} lattice row count differs", findings)
            gaps = []
            for row, maturity in zip(rows, MATURITIES, strict=False):
                steps = int(maturity * STEPS_PER_YEAR)
                _require(
                    row["maturity"] == maturity and row["steps"] == steps,
                    f"{label} {kind} lattice grid differs",
                    findings,
                )
                independently_rolled = crr_american(p, maturity, steps)[kind]
                _require(
                    abs(row[kind] - independently_rolled) <= PRICE_ATOL,
                    f"{label} {kind} lattice value differs",
                    findings,
                )
                recomputed_gap = actual.price - row[kind]
                _require(
                    abs(row[f"{kind}_gap"] - recomputed_gap) <= PRICE_ATOL,
                    f"{label} {kind} lattice gap differs",
                    findings,
                )
                gaps.append(recomputed_gap)
            _require(
                len(gaps) >= 3
                and all(gap >= -1e-10 for gap in gaps)
                and all(right <= left + 1e-10 for left, right in pairwise(gaps))
                and gaps[-1] <= LATTICE_FINAL_ATOL,
                f"{label} {kind} long-maturity lattice check fails",
                findings,
            )
        for name, residual in case["characteristic_residuals"].items():
            _require(
                abs(residual) <= IDENTITY_ATOL,
                f"{label} {name} characteristic residual differs",
                findings,
            )
    return findings, errors


def negative_controls(reference):
    """Changed values, boundaries and q=0 handling must be rejected."""
    rows = []

    def changed_value(data):
        data["cases"][0]["call"]["value"] += 1.0

    def changed_boundary(data):
        data["cases"][0]["put"]["boundary"] += 1.0

    def changed_zero_yield(data):
        case = next(c for c in data["cases"] if c["label"] == "zero_yield")
        case["call"]["boundary_kind"] = "finite"
        case["call"]["boundary"] = 1e12

    def changed_lattice(data):
        data["cases"][0]["lattice"]["rows"][0]["call"] -= 1.0

    for label, mutate in (
        ("call value", changed_value),
        ("put boundary", changed_boundary),
        ("zero-yield call boundary", changed_zero_yield),
        ("finite-maturity lattice value", changed_lattice),
    ):
        altered = copy.deepcopy(reference)
        mutate(altered)
        findings, _ = evaluate(altered)
        rows.append({"mutation": label, "rejected": bool(findings), "findings": findings[:2]})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, help="validate a candidate reference without writing")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = args.reference or REFERENCE
    reference = json.loads(source.read_text(encoding="utf-8"))
    findings, errors = evaluate(reference)
    if not args.reference:
        controls = negative_controls(reference)
        findings += [
            f"negative control accepted: {row['mutation']}"
            for row in controls
            if not row["rejected"]
        ]
    if findings:
        for finding in findings:
            print("FAIL:", finding)
        raise SystemExit(1)
    if args.reference:
        print("PASS: §26.2 independent reference agrees with public API")
        return
    record = {
        "section": "26.2",
        "status": "PASS",
        "cases": [case["label"] for case in reference["cases"]],
        "max_abs_error": errors["price"],
        "max_boundary_error": errors["boundary"],
        "max_exponent_error": errors["exponent"],
        "negative_controls": controls,
        "checks": [
            "public prices, exponents and boundaries equal the independent reference",
            "characteristic residuals, value matching and smooth pasting",
            "zero-dividend call has no finite exercise boundary",
            "saved finite-maturity lattice prices and gaps equal independent CRR rollback",
        ],
        "source_sha256": {
            name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in SOURCES
        },
        "artifact_sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
    }
    payload = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not RECORD.exists() or RECORD.read_text(encoding="utf-8") != payload:
            raise SystemExit("FAIL: §26.2 numerical record missing or stale")
    else:
        RECORD.write_text(payload, encoding="utf-8")
    print("PASS: §26.2 six markets, boundary identities, lattice limit and negative controls")


if __name__ == "__main__":
    main()
