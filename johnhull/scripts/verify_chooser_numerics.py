"""Compare chooser API against independent conditional integrals and invariants."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

from hullkit import bsm, chooser

try:
    from . import build_chooser_reference as reference
except ImportError:
    import build_chooser_reference as reference

PROJECT = Path(__file__).resolve().parents[1]
BASE = "docs/validation/section-26-8/"
OUT = PROJECT / BASE / "numerical-check.json"
FIELDS = ("S", "K", "r", "sigma", "T1", "T2", "q")


def _market(row):
    return {k: row[k] for k in FIELDS}


def _price(m):
    value = chooser.chooser_price(**m)
    if not math.isfinite(value):
        raise ValueError("chooser API produced a nonfinite value")
    return value


def verify(data):
    if data != reference.build():
        raise ValueError("saved §26.8 reference differs from independent recomputation")
    errors, linearity, replication, bounds = [], [], [], []
    for row in [*data["cases"], data["example"]]:
        m = _market(row)
        actual = _price(m)
        errors.append(abs(actual - row["price"]))
        if errors[-1] > 1e-8:
            raise ValueError("chooser price differs from independent reference")
        scaled = {**m, "S": 1.7 * m["S"], "K": 1.7 * m["K"]}
        linearity.append(abs(_price(scaled) - 1.7 * actual))
        c = reference.vanilla(m["S"], m["K"], m["r"], m["sigma"], m["T2"], m["q"], "call")
        p = reference.vanilla(m["S"], m["K"], m["r"], m["sigma"], m["T2"], m["q"], "put")
        bounds.append(max(max(c, p) - actual, actual - c - p, 0.0))
        tau = m["T2"] - m["T1"]
        h = m["K"] * math.exp(-(m["r"] - m["q"]) * tau)
        extra = math.exp(-m["q"] * tau) * bsm.put_price(
            m["S"], h, m["r"], m["sigma"], m["T1"], m["q"]
        )
        replication.append(abs(actual - c - extra))
    for name, axis in (("package", "S"), ("timing", "T1")):
        curve = data["figure"][name]
        xs = curve["spot" if axis == "S" else axis]
        for x, expected in zip(xs, curve["chooser"], strict=True):
            errors.append(abs(_price({**curve["market"], axis: x}) - expected))
    mc_z = [
        abs(row["price"] - row["reference_price"]) / row["standard_error"] for row in data["mc"]
    ]
    if not all(math.isfinite(v) for v in errors + linearity + replication + bounds + mc_z):
        raise ValueError("chooser diagnostics contain a nonfinite value")
    if max(errors + linearity + replication + bounds) > 1e-8:
        raise ValueError("chooser invariants differ from independent reference")
    if max(mc_z) > 6:
        raise ValueError("chooser MC differs by over six standard errors")
    return dict(
        case_count=len(data["cases"]),
        max_price_error=max(errors),
        max_linearity_error=max(linearity),
        max_replication_error=max(replication),
        max_bound_violation=max(bounds),
        max_quadrature_error=max(row["quadrature_error"] for row in data["cases"]),
        max_mc_standard_errors=max(mc_z),
        mc_paths=reference.MC_PATHS,
        example_price=_price(_market(data["example"])),
    )


def negative_controls(data):
    rows = []
    for mutation in ("price", "boundary", "weight", "mc_error"):
        changed = copy.deepcopy(data)
        if mutation == "price":
            changed["cases"][4]["price"] += 0.25
        elif mutation == "boundary":
            changed["figure"]["choice"]["boundary"] *= 1.1
        elif mutation == "weight":
            changed["figure"]["package"]["weight"] *= 1.1
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
        section="26.8",
        status="PASS",
        **verify(data),
        negative_controls=negative_controls(data),
        source_sha256={
            n: digest(n)
            for n in (
                "scripts/build_chooser_reference.py",
                "scripts/verify_chooser_numerics.py",
                "hullkit/src/hullkit/chooser.py",
                "hullkit/src/hullkit/bsm.py",
            )
        },
        artifact_sha256=digest(BASE + "reference.json"),
    )
    if any(not r["rejected"] for r in result["negative_controls"]):
        raise ValueError("chooser negative control accepted")
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("chooser numerical record missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §26.8 chooser conditional integrals, replication, bounds and Monte Carlo")


if __name__ == "__main__":
    main()
