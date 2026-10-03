"""Compare factor API outputs with independent arithmetic and SVD risk cancellation."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

try:
    from .build_factor_risk_reference import build
except ImportError:
    from build_factor_risk_reference import build

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "docs/validation/section-28-2/reference.json"
OUT = DATA.with_name("numerical-check.json")


def close(actual, expected, label):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if (
        a.shape != b.shape
        or not np.all(np.isfinite(a))
        or not np.allclose(a, b, rtol=0, atol=1e-12)
    ):
        raise ValueError("factor numerical mismatch: " + label)
    return float(np.max(np.abs(a - b), initial=0))


def verify(data, api=None):
    if data != build():
        raise ValueError("factor independent reference differs from current source")
    if api is None:
        from hullkit import factor_risk as api
    errors = []
    for row in data["cases"]:
        args = (row["risk_prices"], row["loadings"])
        errors.append(
            close(api.factor_contributions(*args), row["contributions"], "signed contributions")
        )
        errors.append(close(api.factor_excess_return(*args), row["excess"], "excess"))
        errors.append(close(api.factor_required_return(row["r"], *args), row["mu"], "total return"))
    lam = [row["risk_prices"] for row in data["cases"]]
    signed = [row["loadings"] for row in data["cases"]]
    batched = api.factor_excess_return(lam, signed)
    errors.append(close(batched, [row["excess"] for row in data["cases"]], "final batch axis"))
    errors.append(close(api.factor_excess_return([0.2], [-0.3]), -0.06, "one-factor reduction"))
    z = data["zero_price_extension"]
    errors.append(
        close(api.factor_excess_return(z["risk_prices"], z["loadings"]), 0.06, "unpriced extra")
    )
    errors.append(
        close(api.factor_excess_return([0.2, -0.1, 0.4, 0.3], z["loadings"]), 0.30, "priced extra")
    )
    h = data["hedge"]
    matrix = np.asarray(h["loadings"])
    _, singular, vh = np.linalg.svd(matrix.T, full_matrices=True)
    if np.min(singular) < 0.1:
        raise ValueError("hedge does not span both factors")
    w = vh[-1] / np.sum(vh[-1])
    means = api.factor_required_return(h["r"], h["risk_prices"], matrix)
    hedge_error = max(
        close(w, h["weights"], "independent SVD money fractions"),
        close(w @ matrix, [0, 0], "local risk"),
        close(w @ means, h["r"], "risk-free return"),
    )
    rotation_error = max(
        max(
            close(
                api.factor_excess_return(row["risk_prices"], row["loadings"]),
                0.04,
                "orthogonal premium",
            ),
            close(np.linalg.norm(row["loadings"]), np.sqrt(0.05), "orthogonal volatility"),
        )
        for row in data["rotations"]
    )
    c = data["capm"]
    errors.append(
        close(api.factor_excess_return([0.3, 0], c["loadings"]), c["excess"], "conditional CAPM")
    )
    return dict(
        section="28.2",
        status="PASS",
        case_count=len(data["cases"]),
        max_api_error=max(errors),
        max_hedge_error=hedge_error,
        max_rotation_error=rotation_error,
        api_excess_returns=np.asarray(batched).tolist(),
    )


def negative_controls(data):
    rows = []
    for name in ("printed excess", "case total", "hedge money fraction", "rotated loading"):
        changed = copy.deepcopy(data)
        if name == "printed excess":
            changed["printed_pins"]["example_28_3_excess"] += 0.01
        elif name == "case total":
            changed["cases"][0]["mu"] += 0.01
        elif name == "hedge money fraction":
            changed["hedge"]["weights"][0] += 0.1
        else:
            changed["rotations"][1]["loadings"][0] += 0.1
        try:
            verify(changed)
            rejected = False
        except ValueError:
            rejected = True
        rows.append(dict(mutation=name, rejected=rejected))
    from hullkit import factor_risk as original

    for name in (
        "API absolute loading",
        "API drop last factor",
        "API sum all axes",
        "API add rate twice",
    ):
        proxy = SimpleNamespace(
            factor_contributions=original.factor_contributions,
            factor_excess_return=original.factor_excess_return,
            factor_required_return=original.factor_required_return,
        )
        if name == "API absolute loading":
            proxy.factor_contributions = lambda lam, s: original.factor_contributions(
                lam, np.abs(s)
            )
        elif name == "API drop last factor":
            proxy.factor_excess_return = lambda lam, s: original.factor_excess_return(
                np.asarray(lam)[..., :-1], np.asarray(s)[..., :-1]
            )
        elif name == "API sum all axes":
            proxy.factor_excess_return = lambda lam, s: float(
                np.sum(original.factor_contributions(lam, s))
            )
        else:
            proxy.factor_required_return = lambda r, lam, s: (
                original.factor_required_return(r, lam, s) + r
            )
        try:
            verify(data, proxy)
            rejected = False
        except ValueError:
            rejected = True
        rows.append(dict(mutation=name, rejected=rejected))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads(DATA.read_text())
    result = verify(data)
    controls = negative_controls(data)
    if not all(row["rejected"] for row in controls):
        raise ValueError("numerical mutation accepted")
    result.update(
        negative_controls=controls,
        artifact_sha256=hashlib.sha256(DATA.read_bytes()).hexdigest(),
        source_sha256={
            name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
            for name in (
                "scripts/build_factor_risk_reference.py",
                "scripts/verify_factor_risk_numerics.py",
                "hullkit/src/hullkit/factor_risk.py",
                "hullkit/src/hullkit/risk_premium.py",
            )
        },
    )
    payload = (
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
    )
    if args.check:
        if not OUT.is_file() or OUT.read_text() != payload:
            raise ValueError("factor numerical record missing or stale")
    else:
        OUT.write_text(payload)
    print("PASS: §28.2 factor API, SVD local hedge, rotations and eight negative controls")


if __name__ == "__main__":
    main()
