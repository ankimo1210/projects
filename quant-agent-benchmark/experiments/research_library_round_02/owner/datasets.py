"""Generate new public observations and an unpublished, parameter-randomized suite.

Never import or overwrite the original benchmark generator. The master seed,
parameters, labels, and truth stay in an owner-only directory outside Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from pricing import quote

GRID = np.linspace(1 / 12, 30, 721)
FAMILIES = ("negative", "front", "humps", "long", "inverted", "mixed")


def outside_git(path: Path) -> Path:
    path = path.expanduser().resolve()
    if any((p / ".git").exists() for p in (path, *path.parents)):
        raise ValueError("owner private data must be OUTSIDE every Git checkout")
    return path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def parameters(rng, family):
    p = dict(
        level=float(rng.uniform(0.012, 0.045)),
        slope=float(rng.uniform(-0.013, 0.013)),
        tau=float(rng.uniform(0.25, 3.5)),
        step=float(rng.uniform(-0.004, 0.004)),
        step_center=float(rng.uniform(3, 22)),
        step_width=float(rng.uniform(1.5, 5)),
        centers=rng.uniform(0.3, 28, 3).tolist(),
        widths=rng.uniform(0.6, 4, 3).tolist(),
        amplitudes=rng.uniform(-0.004, 0.004, 3).tolist(),
    )
    if family == "negative":
        p.update(level=float(rng.uniform(-0.008, -0.003)), slope=-0.004, step=0.001)
    elif family == "front":
        p.update(slope=-0.02, tau=float(rng.uniform(0.15, 0.6)))
    elif family == "long":
        p["centers"][0], p["widths"][0], p["amplitudes"][0] = float(rng.uniform(17, 26)), 2.2, 0.006
    elif family == "inverted":
        p.update(slope=0.025, tau=float(rng.uniform(2, 6)), step=-0.004)
    elif family == "humps":
        p["amplitudes"] = [0.006, -0.005, 0.004]
    return p


def rates(t, p):
    t = np.asarray(t, dtype=float)
    exp = np.exp(-t / p["tau"])
    u = (t - p["step_center"]) / p["step_width"]
    z = p["level"] + p["slope"] * exp + p["step"] * np.tanh(u)
    dz = -p["slope"] / p["tau"] * exp + p["step"] / p["step_width"] * (1 - np.tanh(u) ** 2)
    for center, width, amplitude in zip(p["centers"], p["widths"], p["amplitudes"], strict=True):
        v = (t - center) / width
        bump = amplitude * np.exp(-v * v)
        z += bump
        dz += -2 * v / width * bump
    return z, z + t * dz


def make_instruments(rng, p, prefix, *, holdout=False):
    # Independent holdout tenors/IDs; all pricing terms retain authoritative T.
    tenors = {
        "deposit": rng.uniform(1 / 12, 1.95, 18),
        "ois_swap": np.r_[np.linspace(1 / 12, 2, 12), np.linspace(2.25, 30, 46)],
        "bond": rng.uniform(0.12, 30, 48),
    }
    if holdout:
        tenors = {
            "deposit": rng.uniform(0.09, 1.95, 8),
            "ois_swap": rng.uniform(0.2, 30, 16),
            "bond": rng.uniform(0.12, 30, 16),
        }

    def df(x):
        return np.exp(-np.asarray(x) * rates(x, p)[0])

    rows = []
    for kind, ts in tenors.items():
        for t in ts:
            t = float(t)
            m = 1 if kind == "deposit" or (kind == "ois_swap" and t <= 2) else 2
            row = dict(
                instrument_id=f"{prefix}{len(rows):04d}",
                currency="USD",
                instrument_type=kind,
                maturity_date=(date(2026, 1, 15) + timedelta(days=round(t * 365))).isoformat(),
                maturity_years=t,
                start_years=0.0,
                payment_frequency=m,
                day_count="ACT/365F",
                coupon_rate=float(rng.uniform(0, 0.06)) if kind == "bond" else np.nan,
                quote_type={
                    "deposit": "simple_rate",
                    "ois_swap": "par_rate",
                    "bond": "clean_price",
                }[kind],
                quote_unit="PRICE_POINTS" if kind == "bond" else "PERCENT",
                settlement_days=2,
            )
            row["true_quote"] = quote(row, df)
            rows.append(row)
    return pd.DataFrame(rows)


def observe(clean, rng, stress):
    data = clean.drop(columns="true_quote").copy()
    n = len(data)
    data["obs_id"] = [f"OBS{i:04d}" for i in range(n)]
    data["source"] = "COMPOSITE"
    data["timestamp"] = "2026-01-15T16:00:00Z"
    data["liquidity_score"] = np.clip(
        1 - 0.02 * data.maturity_years + rng.normal(0, 0.08, n), 0.08, 1
    )
    bond = data.instrument_type.eq("bond").to_numpy()
    spread = np.where(bond, 0.04, 0.006) * (2 - data.liquidity_score.to_numpy())
    data["quote_value"] = clean.true_quote + rng.normal(0, spread * 0.30)
    data["bid"], data["ask"] = data.quote_value - spread / 2, data.quote_value + spread / 2
    labels = []
    indices = rng.permutation(n)
    count = 4 if stress == "ordinary" else 8
    for group, issue in enumerate(("missing", "outlier", "unit", "stale", "inverted")):
        for i in indices[group * count : (group + 1) * count]:
            i = int(i)
            labels.append(dict(obs_id=data.at[i, "obs_id"], issue=issue))
            if issue == "missing":
                data.at[i, "quote_value"] = np.nan
            elif issue == "outlier":
                data.loc[i, ["quote_value", "bid", "ask"]] += (
                    1.5 if bond[i] else 0.35
                ) * rng.choice([-1, 1])
            elif issue == "unit":
                data.loc[i, ["quote_value", "bid", "ask"]] /= 100
            elif issue == "stale":
                data.at[i, "timestamp"] = "2026-01-02T16:00:00Z"
            else:
                data.loc[i, ["bid", "ask"]] = data.loc[i, ["ask", "bid"]].to_numpy()
    if stress == "sparse":
        # Missing observations, not deleted grid regions or mislabeled truth.
        data = data.drop(indices[-25:])
    dup = data.iloc[:5].copy()
    dup["obs_id"] = [f"DUP{i:04d}" for i in range(len(dup))]
    dup["source"], dup["timestamp"] = "BACKUP", "2026-01-15T12:00:00Z"
    labels.extend(dict(obs_id=x, issue="duplicate") for x in dup.obs_id)
    data = pd.concat([data, dup]).sort_values(["maturity_years", "obs_id"]).reset_index(drop=True)
    return data, pd.DataFrame(labels)


def create_suite(root: Path, seed=None):
    root = outside_git(root)
    if root.exists():
        raise FileExistsError("refusing to overwrite an existing suite")
    root.mkdir(parents=True, mode=0o700)
    seed = secrets.randbits(128) if seed is None else seed
    rng = np.random.default_rng(seed)
    cases = []
    specs = [("training", "mixed", "ordinary")]
    specs += [
        (f"case_{i:02d}", family, stress)
        for i, (family, stress) in enumerate(
            ((f, s) for f in FAMILIES for s in ("ordinary", "sparse")), 1
        )
    ]
    for name, family, stress in specs:
        directory = root / name
        directory.mkdir(mode=0o700)
        p = parameters(rng, family)
        clean = make_instruments(rng, p, "TRAIN")
        holdout = make_instruments(rng, p, "HOLD", holdout=True)
        market, labels = observe(clean, rng, stress)
        z, f = rates(GRID, p)
        market.to_csv(directory / "market_observations.csv", index=False)
        clean.to_csv(directory / "instrument_truth.csv", index=False)
        holdout.to_csv(directory / "holdout.csv", index=False)
        labels.to_csv(directory / "labels.csv", index=False)
        pd.DataFrame(
            dict(
                maturity_years=GRID, zero_rate=z, discount_factor=np.exp(-GRID * z), forward_rate=f
            )
        ).to_csv(directory / "truth_curve.csv", index=False)
        save_json(directory / "parameters.json", p)
        cases.append(
            dict(
                case_id=name,
                family=family,
                stress=stress,
                observations=len(market),
                unique_instruments=int(market.instrument_id.nunique()),
                holdout_instruments=len(holdout),
            )
        )
    save_json(root / "private_seed.json", {"seed": seed})
    save_json(
        root / "manifest.json",
        dict(
            contract_version="2.0",
            cases=cases,
            hashes={
                str(p.relative_to(root)): digest(p) for p in sorted(root.rglob("*")) if p.is_file()
            },
        ),
    )
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-dir", type=Path, required=True)
    args = parser.parse_args()
    create_suite(args.private_dir)
    print("Created owner-only suite outside Git. No candidate isolation is implied.")
