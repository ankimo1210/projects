"""Build deterministic saved CRR lesson data; never run during notebook builds.

Run from the workspace root with hullkit/src on PYTHONPATH. This generator may
import the frozen independent engine; the private hullkit pricer never does.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from build_shout_reference import integral_equation_price
from hullkit import exotics
from hullkit._shout import _tree

PROJECT = Path(__file__).resolve().parents[1]
VALIDATION = PROJECT / "docs/validation/section-26-12"
ADOPTED_STEPS = 1024
REFINEMENTS = (128, 256, 512, 1024)
SOURCE_PATHS = (
    "hullkit/src/hullkit/_shout.py",
    "scripts/build_shout_lesson_data.py",
    "scripts/build_shout_reference.py",
    "docs/validation/section-26-12/prices.json",
    "docs/validation/section-26-12/numerical-check.json",
    "hullkit/src/hullkit/exotics.py",
)
LIMITATIONS = [
    "Synthetic constant-parameter GBM; positive S,K,T,sigma; continuous annual r,q.",
    "A finite CRR decision grid approximates continuous shouting; no pointwise monotonicity claim.",
    "Put is an independently priced extension, outside Hull's original call illustration.",
    "No cash dividends, nonconstant volatility, discrete contract calendars, T=0 or sigma=0.",
    "Independent numerical references are not exact solutions or proven error bounds.",
]


def _inputs(row):
    return (
        row["spot"],
        row["strike"],
        row["rate"],
        row["dividend"],
        row["volatility"],
        row["expiry"],
        row["contract"],
    )


def _family(data, method, hashes, limitations=()):
    return dict(
        units=dict(
            money="currency",
            time="years",
            rates="continuous per year",
            volatility="annualized",
            steps="decision intervals",
        ),
        method=method,
        limitations=LIMITATIONS + list(limitations),
        source_hashes=hashes,
        data=data,
    )


def _boundary_data(rows):
    families = []
    for market in ("positive-carry", "zero-carry", "long-high-vol"):
        row = next(
            r
            for r in rows
            if r["market"] == market and r["contract"] == "call" and r["spot_ratio"] == 1
        )
        tree = _tree(*_inputs(row), steps=ADOPTED_STEPS)
        _, coarse_times, coarse_boundary = integral_equation_price(*_inputs(row), steps=200)
        _, times, boundary = integral_equation_price(*_inputs(row), steps=400)
        selected = []
        for fraction in (0.1, 0.25, 0.5, 0.75, 0.9):
            step = round((1 - fraction) * ADOPTED_STEPS)
            tau = tree["remaining_times"][step]
            lower, upper = tree["boundary_lower"][step], tree["boundary_upper"][step]
            if lower is None:
                raise ValueError(f"missing actual node bracket: {market}, tau={tau}")
            reference = float(np.interp(tau, times, boundary))
            coarse = float(np.interp(tau, coarse_times, coarse_boundary))
            distance = max(lower - reference, reference - upper, 0.0)
            if distance > upper - lower:
                raise ValueError(f"boundary differs by more than one node gap: {market}, tau={tau}")
            selected.append(
                dict(
                    step=step,
                    remaining_time=tau,
                    requested_time_fraction=fraction,
                    lower=lower,
                    upper=upper,
                    reference=reference,
                    grid_width=upper - lower,
                    distance_outside_bracket=distance,
                    reference_200=coarse,
                    reference_refinement_delta=reference - coarse,
                )
            )
        # Only show layers with both adjacent decisions, excluding root and the
        # last 5% of life where boundary resolution is especially poor.
        indices = [
            i
            for i in range(0, ADOPTED_STEPS, 16)
            if tree["boundary_lower"][i] is not None
            and 0.05 * row["expiry"] <= tree["remaining_times"][i] <= 0.95 * row["expiry"]
        ]
        indices = sorted(set(indices + [x["step"] for x in selected]), reverse=True)
        remaining = [tree["remaining_times"][i] for i in indices]
        families.append(
            dict(
                market=market,
                parameters={
                    k: row[k]
                    for k in (
                        "spot",
                        "strike",
                        "rate",
                        "dividend",
                        "volatility",
                        "expiry",
                        "contract",
                    )
                },
                steps=ADOPTED_STEPS,
                step_indices=indices,
                remaining_times=remaining,
                lower=[tree["boundary_lower"][i] for i in indices],
                upper=[tree["boundary_upper"][i] for i in indices],
                reference=np.interp(remaining, times, boundary).tolist(),
                reference_method="Engine B, 400 sqrt(tau) intervals; linear interpolation in tau",
                reference_steps=400,
                selected_checks=selected,
            )
        )
    return families


def build():
    """Return lesson and acceptance records, with every saved residual exposed."""
    hashes = {
        path: hashlib.sha256((PROJECT / path).read_bytes()).hexdigest() for path in SOURCE_PATHS
    }
    rows = json.loads((VALIDATION / "prices.json").read_text())["rows"]
    convergence, comparisons = [], []
    for steps in REFINEMENTS:
        results = []
        for row in rows:
            tree = _tree(*_inputs(row), steps=steps)
            residual = tree["price"] - row["price"]
            results.append(
                dict(
                    market=row["market"],
                    contract=row["contract"],
                    spot_ratio=row["spot_ratio"],
                    tree=tree["price"],
                    reference=row["price"],
                    residual=residual,
                    root_decision=tree["root_decision"],
                    immediate=tree["immediate"],
                    continuation=tree["continuation"],
                )
            )
            if steps == ADOPTED_STEPS:
                fixed = None
                if row["rate"] != row["dividend"]:
                    fn = (
                        exotics.lookback_fixed_call
                        if row["contract"] == "call"
                        else exotics.lookback_fixed_put
                    )
                    fixed = float(
                        fn(
                            row["spot"],
                            row["strike"],
                            row["spot"],
                            row["rate"],
                            row["volatility"],
                            row["expiry"],
                            q=row["dividend"],
                        )
                    )
                comparisons.append(
                    {
                        **row,
                        "tree": tree["price"],
                        "tree_residual": residual,
                        "tree_steps": steps,
                        "root_decision": tree["root_decision"],
                        "fixed_lookback": fixed,
                        "fixed_lookback_status": "undefined in current API at r=q"
                        if fixed is None
                        else "defined",
                        "contract_scope": "Hull call"
                        if row["contract"] == "call"
                        else "put extension",
                    }
                )
        residuals = [x["residual"] for x in results]
        convergence.append(
            dict(
                steps=steps,
                rows=results,
                max_absolute=max(abs(x) for x in residuals),
                rms=math.sqrt(sum(x * x for x in residuals) / len(residuals)),
            )
        )
    if (
        convergence[-1]["max_absolute"] > 0.005
        or convergence[-1]["max_absolute"] >= convergence[0]["max_absolute"]
        or convergence[-1]["rms"] >= convergence[0]["rms"]
    ):
        raise ValueError(
            "fixed reference acceptance failed; refine the tree, never rewrite references"
        )
    boundaries = _boundary_data(rows)
    contract = dict(
        shouts_allowed=1,
        may_never_shout=True,
        original_kind="call",
        extension_kind="put",
        process="dS=(r-q)S dt + sigma S dW",
        decision_times="continuous target; finite CRR approximation",
        literal_call_payoff="max(S_T-K,S_shout-K)",
        intrinsic_floor_payoff="max(S_T-K,0,S_shout-K)",
        agreement="equal when S_shout>=K; below K, literal shouting is dominated by no shout",
    )
    payoff = dict(
        strike=50.0,
        shout_spot=60.0,
        terminal_spots=[30.0, 45.0, 50.0, 55.0, 60.0, 75.0, 90.0],
        locked_cash=10.0,
        payoffs=[10.0, 10.0, 10.0, 10.0, 10.0, 25.0, 40.0],
        european=[0.0, 0.0, 0.0, 5.0, 10.0, 25.0, 40.0],
        reset_call=[0.0, 0.0, 0.0, 0.0, 0.0, 15.0, 30.0],
    )
    decision = dict(
        market="positive-carry",
        parameters=dict(
            spot=100.0,
            strike=100.0,
            rate=0.05,
            dividend=0.02,
            volatility=0.2,
            expiry=1.0,
            contract="call",
        ),
        tree=_tree(100.0, 100.0, 0.05, 0.02, 0.2, 1.0, "call", 3),
    )
    record = dict(
        schema_version=1,
        adopted_steps=ADOPTED_STEPS,
        absolute_tolerance=0.005,
        initial_absolute_target=0.03,
        source_hashes=hashes,
        limitations=LIMITATIONS,
        convergence=convergence,
        boundaries=boundaries,
        boundary_acceptance="selected engine-B point is within one actual node gap of the finite-tree bracket; not exact containment",
        reference_rewritten=False,
    )
    lesson = dict(
        schema_version=1,
        adopted_steps=ADOPTED_STEPS,
        contract=_family(contract, "Hull §26.12 call contract and explicit put extension", hashes),
        payoff=_family(payoff, "Hull strike 50, shout 60; exact algebraic payoff pins", hashes),
        decision_tree=_family(
            decision,
            "N=3 CRR backward induction; signed cash plus ATM option at each nonterminal node",
            hashes,
        ),
        prices=_family(
            comparisons,
            "N=1024 independent CRR versus frozen M4a engine A; current fixed-lookback API",
            hashes,
            ["Lookback comparison defined for 36 rows / 6 markets; r=q 6 rows are null."],
        ),
        convergence=_family(
            convergence, "Every CRR residual against all 42 immutable M4a rows", hashes
        ),
        boundaries=_family(
            boundaries,
            "Actual adjacent CRR decision nodes, every 16th layer plus 5 selected checks, compared with independent engine B",
            hashes,
            [
                "Finite-tree brackets are not certified continuous boundary brackets.",
                "Root, last 5% of life and layers without both decisions are omitted.",
                "Only engine-B reference is interpolated; CRR node brackets are never interpolated.",
            ],
        ),
    )
    return lesson, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=VALIDATION)
    options = parser.parse_args()
    lesson, record = build()
    options.output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (("lesson-data.json", lesson), ("tree-check.json", record)):
        (options.output_dir / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        )
    for curve in record["convergence"]:
        print(f"N={curve['steps']}: max_abs={curve['max_absolute']:.10g}, RMS={curve['rms']:.10g}")
    for family in record["boundaries"]:
        print(
            f"{family['market']}: boundary selected checks={len(family['selected_checks'])}; "
            f"max outside bracket={max(x['distance_outside_bracket'] for x in family['selected_checks']):.10g}"
        )


if __name__ == "__main__":
    main()
