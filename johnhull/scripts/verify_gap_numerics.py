"""Compare Hull §26.4 public gap pricing with the independent saved reference."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
from unittest import mock

import build_gap_reference as reference
from hullkit import exotics
from hullkit.gap_options import gap_option

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "docs/validation/section-26-4/reference.json"
OUT = DATA.with_name("numerical-check.json")
SOURCES = (
    "hullkit/src/hullkit/gap_options.py",
    "hullkit/src/hullkit/exotics.py",
    "hullkit/src/hullkit/bsm.py",
    "scripts/build_gap_reference.py",
    "scripts/verify_gap_numerics.py",
)
FIELDS = ("price", "regular_price", "trigger_adjustment", "trigger_probability")


def _api(row):
    return gap_option(
        row["kind"], row["spot"], row["K1"], row["K2"], row["r"], row["sigma"], row["T"], row["q"]
    )


def verify(data):
    """Reject a changed saved reference or a public API that departs from it."""
    if data != reference.build():
        raise ValueError("saved §26.4 reference differs from independent recomputation")
    worst = {field: 0.0 for field in FIELDS}
    for row in data["cases"]:
        result = _api(row)
        for field in FIELDS:
            scale = max(1.0, abs(row[field]))
            worst[field] = max(worst[field], abs(getattr(result, field) - row[field]) / scale)
    base = reference.MARKETS["base"]
    level_error = 0.0
    for kind, row in data["conditional_mean"].items():
        level = gap_option(
            kind, base["spot"], 90.0, 100.0, base["r"], base["sigma"], base["T"], base["q"]
        )
        level_error = max(level_error, abs(level.zero_value_settlement - row["closed_form"]))
    example = data["example_26_1"]
    market = (example["spot"], example["r"], example["sigma"], example["T"], example["q"])
    K1, K2 = example["K1"], example["K2"]
    holder = K1 - example["transfer_cost"]

    def put(settlement, trigger):
        return gap_option("put", market[0], settlement, trigger, *market[1:]).price

    example_error = max(
        abs(put(K1, K1) - example["regular_put"]),
        abs(put(K1, K2) - example["insurer_gap_put"]),
        abs(put(holder, holder) - example["policyholder_put"]),
    )
    if max(worst.values()) > 1e-12 or level_error > 1e-10 or example_error > 1e-8:
        raise ValueError(
            f"public API differs from reference: {worst}, level={level_error}, example={example_error}"
        )
    return {
        "case_count": len(data["cases"]),
        "max_relative_error": worst,
        "zero_value_settlement_error": level_error,
        "example_26_1_error": example_error,
        "example_26_1_printed": {
            "regular_put": round(example["regular_put"]),
            "gap_put": round(example["insurer_gap_put"]),
            "reduction_percent": round(100.0 * example["reduction"]),
        },
    }


def negative_controls(data):
    controls = []
    for name in ("price", "settlement_strike", "trigger", "printed_value", "seed"):
        changed = copy.deepcopy(data)
        if name == "price":
            changed["cases"][0]["price"] += 0.01
        elif name == "settlement_strike":
            changed["cases"][4]["K1"] = 105.0
        elif name == "trigger":
            changed["example_26_1"]["K2"] = 360_000.0
        elif name == "printed_value":
            changed["example_26_1"]["printed"]["gap_put"] = 1_900
        else:
            next(row for row in changed["cases"] if "monte_carlo" in row)["monte_carlo"][
                "seed"
            ] += 1
        try:
            verify(changed)
        except ValueError:
            rejected = True
        else:
            rejected = False
        controls.append({"mutation": name, "rejected": rejected})
    return controls


def _wrong_formulas(name):
    """Deliberately broken versions of Hull eq. 26.1/26.2 that the API delegates to."""
    call, put = exotics.gap_call, exotics.gap_put
    if name == "d_at_settlement_strike":
        return (
            lambda S, K1, K2, *rest: call(S, K1, K1 or K2, *rest),
            lambda S, K1, K2, *rest: put(S, K1, K1 or K2, *rest),
        )
    if name == "swapped_put_strikes":
        return call, lambda S, K1, K2, *rest: put(S, K2, K1 or K2, *rest)
    return (
        lambda *args: call(*args) * (1.0 + 1e-9),
        lambda *args: put(*args) * (1.0 + 1e-9),
    )


def api_negative_controls(data):
    """Break the public API, not the data: the comparison itself must reject it."""
    controls = []
    for name in ("d_at_settlement_strike", "swapped_put_strikes", "relative_bias_1e-9"):
        call, put = _wrong_formulas(name)
        with (
            mock.patch.object(exotics, "gap_call", call),
            mock.patch.object(exotics, "gap_put", put),
        ):
            try:
                verify(data)
            except ValueError as error:
                rejected = str(error).startswith("public API differs")
            else:
                rejected = False
        controls.append({"mutation": name, "rejected": rejected})
    return controls


def build():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    summary = verify(data)
    controls = negative_controls(data)
    api_controls = api_negative_controls(data)
    if not all(row["rejected"] for row in controls + api_controls):
        raise ValueError("a negative control was not rejected")
    return {
        "section": "26.4",
        "status": "PASS",
        "method": data["method"],
        **summary,
        "negative_controls": controls,
        "api_negative_controls": api_controls,
        "artifact_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
        "source_sha256": {
            path: hashlib.sha256((PROJECT / path).read_bytes()).hexdigest() for path in SOURCES
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = json.dumps(build(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("missing or stale §26.4 numerical record")
        print("PASS: §26.4 thirty-eight cases, Example 26.1, five data and three API controls")
    else:
        OUT.write_text(expected, encoding="utf-8")
        print(OUT)


if __name__ == "__main__":
    main()
