"""Compare Hull §26.6 reset cashflows with independent multitime references."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from hullkit import cliquet

try:
    from . import build_cliquet_reference as reference
except ImportError:
    import build_cliquet_reference as reference

PROJECT = Path(__file__).resolve().parents[1]
BASE = "docs/validation/section-26-6/"
OUT = PROJECT / BASE / "numerical-check.json"


def _market(row):
    return {key: row[key] for key in ("S", "r", "sigma", "payment_times", "q")}


def verify(data):
    if data != reference.build():
        raise ValueError("saved §26.6 reference differs from independent recomputation")
    differences, parity, sums, linearity = [], [], [], []
    for row in [*data["cases"], *data["example"].values()]:
        market = _market(row)
        function = getattr(cliquet, "cliquet_" + row["kind"])
        actual = function(**market)
        differences.append(abs(actual - row["price"]))
        linearity.append(abs(function(**{**market, "S": row["S"] * 1.7}) - 1.7 * actual))
        sums.append(abs(actual - sum(row["components"])))
        dates = np.array(row["payment_times"])
        starts = np.r_[0, dates[:-1]]
        difference = np.sum(
            row["S"]
            * np.exp(-row["q"] * starts)
            * (np.exp(-row["q"] * (dates - starts)) - np.exp(-row["r"] * (dates - starts)))
        )
        parity.append(
            abs(cliquet.cliquet_call(**market) - cliquet.cliquet_put(**market) - difference)
        )
    frequency = data["figure"]["frequency"]
    for kind in ("call", "put"):
        for n, expected in zip(frequency["periods"], frequency[kind], strict=True):
            actual = getattr(cliquet, "cliquet_" + kind)(
                **frequency["market"], payment_times=np.linspace(2 / n, 2, n)
            )
            differences.append(abs(actual - expected))
    if max(differences) > 1e-9:
        raise ValueError("cliquet API differs from independent payoff integral")
    if max(parity + sums + linearity) > 1e-9:
        raise ValueError("cashflow parity, component sum or spot homogeneity failed")
    mc_z = [
        abs(row["price"] - row["reference_price"]) / row["standard_error"] for row in data["mc"]
    ]
    diagnostic = data["complex"]
    plain = diagnostic["contracts"][0]
    mc_z.append(abs(plain["price"] - diagnostic["reference_price"]) / plain["standard_error"])
    if max(mc_z) > 6:
        raise ValueError("multitime Monte Carlo differs by over six standard errors")
    return dict(
        case_count=len(data["cases"]),
        max_price_error=max(differences),
        max_quadrature_error=max(row["quadrature_error"] for row in data["cases"]),
        max_mc_standard_errors=max(mc_z),
        mc_paths=reference.MC_PATHS,
        max_parity_error=max(parity),
        max_component_sum_error=max(sums),
        max_linearity_error=max(linearity),
        example_call=data["example"]["call"]["price"],
        example_put=data["example"]["put"]["price"],
    )


def negative_controls(data):
    rows = []
    for mutation in ("price", "reset", "discount", "cap"):
        changed = copy.deepcopy(data)
        if mutation == "price":
            changed["cases"][8]["price"] += 0.25
        elif mutation == "reset":
            changed["figure"]["reset"]["strikes"][1] = changed["figure"]["reset"]["stock"][0]
        elif mutation == "discount":
            changed["mc"][0]["components"][0] *= math.exp(-0.05 * 1.5)
        else:
            changed["complex"]["global_cap"] = 5
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
    data = json.loads((PROJECT / BASE / "reference.json").read_text())
    result = dict(
        section="26.6",
        status="PASS",
        **verify(data),
        negative_controls=negative_controls(data),
        source_sha256={
            name: digest(name)
            for name in (
                "scripts/build_cliquet_reference.py",
                "scripts/verify_cliquet_numerics.py",
                "hullkit/src/hullkit/cliquet.py",
                "hullkit/src/hullkit/forward_start.py",
                "hullkit/src/hullkit/bsm.py",
            )
        },
        artifact_sha256=digest(BASE + "reference.json"),
    )
    if any(not row["rejected"] for row in result["negative_controls"]):
        raise ValueError("negative control accepted")
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text() != payload:
            raise ValueError("numerical record missing or stale")
    else:
        OUT.write_text(payload)
    print("PASS: §26.6 prices, reset/payment cashflows, parity and Monte Carlo")


if __name__ == "__main__":
    main()
