"""Compare the existing gap API with independent §26.4 payoff quadrature."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

from hullkit import bsm, exotics

try:
    from . import build_gap_reference as reference
except ImportError:
    import build_gap_reference as reference

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "docs/validation/section-26-4/reference.json"
OUT = DATA.with_name("numerical-check.json")
SOURCES = (
    "hullkit/src/hullkit/exotics.py",
    "hullkit/src/hullkit/bsm.py",
    "scripts/build_gap_reference.py",
    "scripts/verify_gap_numerics.py",
)


def _market(row):
    return {key: row[key] for key in ("S", "r", "sigma", "T", "q")}


def verify(data):
    if data != reference.build():
        raise ValueError("saved §26.4 reference differs from independent recomputation")
    prices, decompositions, parities = [], [], []
    for row in [*data["cases"], *data["figure"]["decomposition"]]:
        market = _market(row)
        pricer = exotics.gap_call if row["kind"] == "call" else exotics.gap_put
        actual = float(pricer(**market, K1=row["K1"], K2=row["K2"]))
        prices.append(abs(actual - row["price"]))
        vanilla = bsm.call_price if row["kind"] == "call" else bsm.put_price
        vanilla_price = float(vanilla(**market, K=row["K2"]))
        binary = exotics.cash_or_nothing(**market, K=row["K2"], kind=row["kind"])
        factor = row["K2"] - row["K1"] if row["kind"] == "call" else row["K1"] - row["K2"]
        decompositions.append(abs(actual - (vanilla_price + factor * binary)))
    for call, put in zip(data["cases"][::2], data["cases"][1::2], strict=True):
        forward = call["S"] * math.exp(-call["q"] * call["T"]) - call["K1"] * math.exp(
            -call["r"] * call["T"]
        )
        parities.append(abs(call["price"] - put["price"] - forward))
    example = data["example"]
    market = _market(example)
    for value, K1, K2 in (
        (example["ordinary_put"], 400000, 400000),
        (example["insurer_gap_put"], 400000, 350000),
        (example["policyholder_net_put"], 350000, 350000),
    ):
        prices.append(abs(float(exotics.gap_put(**market, K1=K1, K2=K2)) - value))
    for row in data["figure"]["premium"]:
        prices.extend(
            [
                abs(
                    float(exotics.gap_put(**market, K1=400000, K2=row["trigger"])) - row["insurer"]
                ),
                abs(
                    float(exotics.gap_put(**market, K1=row["trigger"], K2=row["trigger"]))
                    - row["holder"]
                ),
            ]
        )
    maximum = max(prices)
    if max(maximum, max(decompositions), max(parities)) > 1e-7:
        raise ValueError(f"public gap API differs from reference: {maximum}")
    if (round(example["ordinary_put"]), round(example["insurer_gap_put"])) != (3436, 1896):
        raise ValueError("printed Example26.1 pins differ")
    if abs(example["reduction_percent"] - 45) > 0.5:
        raise ValueError("printed approximate 45 percent reduction differs")
    if (
        abs(
            example["insurer_gap_put"]
            - example["policyholder_net_put"]
            - example["discounted_transfer_cost"]
        )
        > 1e-7
    ):
        raise ValueError("insurer/holder transfer-cost identity failed")
    return dict(
        case_count=len(data["cases"]),
        max_price_error=maximum,
        max_decomposition_error=max(decompositions),
        max_parity_error=max(parities),
        max_quadrature_error=max(
            example["quadrature_error"], *(row["quadrature_error"] for row in data["cases"])
        ),
        negative_price_cases=sum(row["price"] < 0 for row in data["cases"]),
        printed_prices=[3436, 1896],
        reduction_percent=example["reduction_percent"],
    )


def negative_controls(data):
    rows = []
    for name in ("price", "trigger", "insurer_as_holder", "clipped_payoff"):
        changed = copy.deepcopy(data)
        if name == "price":
            changed["cases"][0]["price"] += 1
            changed["cases"][1]["price"] += 1
        elif name == "trigger":
            changed["example"]["K2"] = 400000
        elif name == "insurer_as_holder":
            changed["example"]["insurer_gap_put"] = changed["example"]["policyholder_net_put"]
        else:
            changed["figure"]["payoff"]["call"] = [
                max(value, 0) for value in changed["figure"]["payoff"]["call"]
            ]
        try:
            verify(changed)
        except ValueError:
            rejected = True
        else:
            rejected = False
        rows.append(dict(mutation=name, rejected=rejected))
    return rows


def build():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    result = verify(data)
    controls = negative_controls(data)
    if not all(row["rejected"] for row in controls):
        raise ValueError("numerical negative control accepted")
    return dict(
        section="26.4",
        status="PASS",
        **result,
        negative_controls=controls,
        artifact_sha256=hashlib.sha256(DATA.read_bytes()).hexdigest(),
        source_sha256={
            name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in SOURCES
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise SystemExit("missing or stale §26.4 numerical record")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §26.4 quadrature, decomposition, parity and printed pins")


if __name__ == "__main__":
    main()
