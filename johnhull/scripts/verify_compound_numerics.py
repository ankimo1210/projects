"""Compare all four Geske prices with independent T1 payoff integrals."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

from hullkit import compound

try:
    from . import build_compound_reference as reference
except ImportError:
    import build_compound_reference as reference

PROJECT = Path(__file__).resolve().parents[1]
BASE = "docs/validation/section-26-7/"
OUT = PROJECT / BASE / "numerical-check.json"
FIELDS = ("S", "K1", "K2", "r", "sigma", "T1", "T2", "q")


def _market(row):
    return {key: row[key] for key in FIELDS}


def _price(market, kind):
    value = compound.compound_price(**market, kind=kind)
    if not math.isfinite(value):
        raise ValueError("compound API produced a nonfinite value")
    return value


def verify(data):
    if data != reference.build():
        raise ValueError("saved §26.7 reference differs from independent recomputation")
    errors, parity, linearity, roots = [], [], [], []
    for row in [*data["cases"], *data["example"].values()]:
        market, kind = _market(row), row["kind"]
        actual = _price(market, kind)
        errors.append(abs(actual - row["price"]))
        scaled = {**market, **{key: market[key] * 1.7 for key in ("S", "K1", "K2")}}
        linearity.append(abs(_price(scaled, kind) - 1.7 * actual))
        inner = kind.split("_on_")[1]
        plain = reference.vanilla(
            market["S"],
            market["K2"],
            market["r"],
            market["sigma"],
            market["T2"],
            market["q"],
            inner,
        )
        parity.append(
            abs(
                _price(market, "call_on_" + inner)
                - _price(market, "put_on_" + inner)
                - plain
                + market["K1"] * math.exp(-market["r"] * market["T1"])
            )
        )
        if market["sigma"] > 0 and market["K1"] > 0:
            root = compound._critical_spot(
                market["K1"],
                market["K2"],
                market["r"],
                market["sigma"],
                market["T2"] - market["T1"],
                market["q"],
                inner,
            )
            if root is not None:
                roots.append(
                    abs(
                        reference.vanilla(
                            root,
                            market["K2"],
                            market["r"],
                            market["sigma"],
                            market["T2"] - market["T1"],
                            market["q"],
                            inner,
                        )
                        - market["K1"]
                    )
                )
    for name, axis in (("strikes", "K1"), ("timing", "T1")):
        curve = data["figure"][name]
        for kind in reference.KINDS:
            for x, expected in zip(curve[axis], curve[kind], strict=True):
                errors.append(abs(_price({**curve["market"], axis: x}, kind) - expected))
    if max(errors) > 1e-8 or max(parity + linearity) > 1e-8 or max(roots) > 1e-9:
        raise ValueError(
            "compound price, parity, homogeneity or threshold differs from independent reference"
        )
    mc_z = [
        abs(row["price"] - row["reference_price"]) / row["standard_error"] for row in data["mc"]
    ]
    if not all(math.isfinite(value) for value in errors + parity + linearity + roots + mc_z):
        raise ValueError("compound diagnostics contain a nonfinite value")
    if max(mc_z) > 6:
        raise ValueError("compound conditional Monte Carlo differs by over six standard errors")
    return dict(
        case_count=len(data["cases"]),
        max_price_error=max(errors),
        max_parity_error=max(parity),
        max_linearity_error=max(linearity),
        max_root_residual=max(roots),
        max_quadrature_error=max(row["quadrature_error"] for row in data["cases"]),
        max_mc_standard_errors=max(mc_z),
        mc_paths=reference.MC_PATHS,
        example_prices={kind: _price(_market(row), kind) for kind, row in data["example"].items()},
    )


def negative_controls(data):
    rows = []
    for mutation in ("price", "critical", "strike", "mc_error"):
        changed = copy.deepcopy(data)
        if mutation == "price":
            changed["cases"][8]["price"] += 0.25
        elif mutation == "critical":
            changed["figure"]["threshold"]["critical"]["put"] *= 1.1
        elif mutation == "strike":
            changed["cases"][8]["K1"], changed["cases"][8]["K2"] = (
                changed["cases"][8]["K2"],
                changed["cases"][8]["K1"],
            )
        else:
            changed["mc"][0]["standard_error"] *= 2
        try:
            verify(changed)
        except ValueError:
            rejected = True
        else:
            rejected = False
        rows.append(dict(mutation=mutation, rejected=rejected))
    return rows


def digest(name):
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads((PROJECT / BASE / "reference.json").read_text(encoding="utf-8"))
    result = dict(
        section="26.7",
        status="PASS",
        **verify(data),
        negative_controls=negative_controls(data),
        source_sha256={
            name: digest(name)
            for name in (
                "scripts/build_compound_reference.py",
                "scripts/verify_compound_numerics.py",
                "hullkit/src/hullkit/compound.py",
                "hullkit/src/hullkit/bsm.py",
            )
        },
        artifact_sha256=digest(BASE + "reference.json"),
    )
    if any(not row["rejected"] for row in result["negative_controls"]):
        raise ValueError("compound negative control accepted")
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("compound numerical record missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §26.7 four formulas, critical spots, parity and Monte Carlo")


if __name__ == "__main__":
    main()
