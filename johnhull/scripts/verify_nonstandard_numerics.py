"""Compare Hull §26.3 public pricing with an independent saved reference."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

import build_nonstandard_reference as reference
from hullkit.nonstandard_american import scheduled_option

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "docs/validation/section-26-3/reference.json"
OUT = DATA.with_name("numerical-check.json")
SOURCES = (
    "hullkit/src/hullkit/nonstandard_american.py",
    "scripts/build_nonstandard_reference.py",
    "scripts/verify_nonstandard_numerics.py",
)


def _schedule(row):
    return {int(step): strike for step, strike in row["exercise_strikes"].items()}


def verify(data):
    """Reject changed saved prices, terms or missing exercise-mask behavior."""
    if data != reference.build():
        raise ValueError("saved §26.3 reference differs from independent recomputation")
    rows = [*data["small_hand_check"], *data["cases"], data["warrant"]]
    maximum = 0.0
    forbidden = 0
    for row in rows:
        result = scheduled_option(
            row["kind"],
            row["spot"],
            row["r"],
            row["sigma"],
            row["maturity"],
            row["steps"],
            _schedule(row),
            q=row["q"],
        )
        maximum = max(maximum, abs(result.price - row["price"]))
        allowed = set(_schedule(row))
        forbidden += sum(
            any(flags) for step, flags in enumerate(result.exercise) if step not in allowed
        )
    if maximum > 1e-10 or forbidden:
        raise ValueError(
            f"public API differs from reference: error={maximum}, forbidden={forbidden}"
        )
    return {
        "case_count": len(rows),
        "max_price_error": maximum,
        "forbidden_exercise_count": forbidden,
    }


def negative_controls(data):
    controls = []
    for name in ("price", "exercise_date", "warrant_strike", "label"):
        changed = copy.deepcopy(data)
        if name == "price":
            changed["cases"][1]["price"] += 0.25
        elif name == "exercise_date":
            changed["cases"][1]["exercise_strikes"]["10"] = 110.0
        elif name == "warrant_strike":
            changed["warrant"]["exercise_strikes"]["50"] = 30.0
        else:
            changed["small_hand_check"][0]["label"] = "wrong"
        try:
            verify(changed)
        except ValueError:
            rejected = True
        else:
            rejected = False
        controls.append({"mutation": name, "rejected": rejected})
    return controls


def build():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    summary = verify(data)
    controls = negative_controls(data)
    if not all(row["rejected"] for row in controls):
        raise ValueError("a saved-reference negative control was not rejected")
    return {
        "section": "26.3",
        "status": "PASS",
        **summary,
        "negative_controls": controls,
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
            raise SystemExit("missing or stale §26.3 numerical record")
        print("PASS: §26.3 eleven cases and four negative controls")
    else:
        OUT.write_text(expected, encoding="utf-8")
        print(OUT)


if __name__ == "__main__":
    main()
