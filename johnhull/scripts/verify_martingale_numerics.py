"""Check conditional ratio API, direct Gaussian pricing and raw conditional MC."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.integrate import quad

try:
    from .build_martingale_reference import build
except ImportError:
    from build_martingale_reference import build

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "docs/validation/section-28-3/reference.json"
OUT = DATA.with_name("numerical-check.json")
SOURCES = (
    "scripts/build_martingale_reference.py",
    "scripts/verify_martingale_numerics.py",
    "hullkit/src/hullkit/_martingales.py",
    "hullkit/src/hullkit/risk_premium.py",
    "hullkit/src/hullkit/bsm.py",
)
SAMPLES = 262144


def close(actual, expected, label):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if (
        a.shape != b.shape
        or not np.all(np.isfinite(a))
        or not np.allclose(a, b, rtol=0, atol=1e-12)
    ):
        raise ValueError("martingale numerical mismatch: " + label)
    return float(np.max(np.abs(a - b), initial=0))


def result_digest(result):
    values = {k: result[k] for k in ("api_conditional_means", "conditional_mc", "pricing")}
    return hashlib.sha256(json.dumps(values, sort_keys=True, allow_nan=False).encode()).hexdigest()


def summary(values, expected):
    estimate = float(np.mean(values))
    se = float(np.std(values, ddof=1) / math.sqrt(len(values)))
    if not math.isfinite(estimate) or not math.isfinite(se) or se <= 0:
        raise ValueError("invalid Monte Carlo estimate")
    z = abs(estimate - expected) / se
    if z > 5:
        raise ValueError("Monte Carlo exceeds five standard errors")
    return dict(mean=estimate, se=se, z=z, reference=expected)


def verify(data, api=None):
    if data != build():
        raise ValueError("independent martingale reference changed")
    if api is None:
        from hullkit import _martingales as api
    from hullkit.bsm import call_price

    errors = []
    for row in data["cases"]:
        mf, mg = api.numeraire_drifts(row["r"], row["s_f"], row["s_g"])
        errors.append(close([mf, mg], [row["mu_f"], row["mu_g"]], "measure drift"))
        args = (mf, mg, row["s_f"], row["s_g"])
        errors.append(close(api.ratio_drift(*args), row["drift"], "Ito"))
        errors.append(
            close(api.ratio_conditional_mean(1.5, *args, 1.75), row["mean"], "own conditional")
        )
        wrong = (row["r"], row["r"], row["s_f"], row["s_g"])
        errors.append(close(api.ratio_drift(*wrong), row["wrong_drift"], "wrong measure drift"))
        errors.append(
            close(
                api.ratio_conditional_mean(1.5, *wrong, 1.75),
                row["wrong_mean"],
                "wrong conditional",
            )
        )
    rows = data["conditional"]
    api_means = api.ratio_conditional_mean(
        [r["value"] for r in rows], 0.085, 0.0625, 0.3, 0.15, [r["horizon"] for r in rows]
    )
    errors.append(close(api_means, [r["mean"] for r in rows], "batch conditional"))
    rng = np.random.default_rng(20261004)
    mc = []
    for row in rows:
        h, b = row["horizon"], row["s_f"] - row["s_g"]
        z = rng.standard_normal(SAMPLES)
        # Independent Wiener increments conditional on a specified observed state.
        values = row["value"] * np.exp(-0.5 * b * b * h + b * math.sqrt(h) * z)
        mc.append(summary(values, row["mean"]))
    prices = []
    quadrature_error = 0
    for row in data["pricing"]:
        S, K, G, r, sf, sg, T = (row[k] for k in ("S", "K", "G", "r", "s_f", "s_g", "T"))
        errors.append(close(call_price(S, K, r, abs(sf), T), row["price"], "independent call"))
        gf, gg = api.numeraire_drifts(r, sf, sg)
        for measure, mf, mg in (("Q", r, r), ("G", gf, gg)):
            threshold = (math.log(K / S) - (mf - 0.5 * sf * sf) * T) / (sf * math.sqrt(T))

            def value(z, S=S, K=K, G=G, r=r, sf=sf, sg=sg, T=T, mf=mf, mg=mg, measure=measure):
                ST = S * np.exp((mf - 0.5 * sf * sf) * T + sf * math.sqrt(T) * z)
                payoff = np.maximum(ST - K, 0)
                if measure == "Q":
                    return math.exp(-r * T) * payoff
                GT = G * np.exp((mg - 0.5 * sg * sg) * T + sg * math.sqrt(T) * z)
                return G * payoff / GT

            def integrand(z, value=value):
                return float(value(z)) * math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)

            integrated, reported_error = quad(integrand, threshold, 12, epsabs=1e-11, epsrel=1e-11)
            error = abs(integrated - row["price"])
            if error > 1e-9 or reported_error > 1e-9:
                raise ValueError("Gaussian price quadrature mismatch")
            quadrature_error = max(quadrature_error, error, reported_error)
            sampled = value(rng.standard_normal(SAMPLES))
            prices.append(
                dict(
                    measure=measure, s_g=sg, quadrature=integrated, **summary(sampled, row["price"])
                )
            )
    result = dict(
        section="28.3",
        status="PASS",
        case_count=6,
        conditional_count=9,
        samples=SAMPLES,
        max_api_error=max(errors),
        max_quadrature_error=quadrature_error,
        max_mc_se=max(v["z"] for v in [*mc, *prices]),
        api_conditional_means=np.asarray(api_means).tolist(),
        conditional_mc=mc,
        pricing=prices,
    )
    result["result_sha256"] = result_digest(result)
    return result


def negative_controls(data):
    rows = []
    for name in ("drift", "conditional state", "second moment", "call price"):
        bad = copy.deepcopy(data)
        if name == "drift":
            bad["cases"][0]["drift"] += 0.1
        elif name == "conditional state":
            bad["conditional"][0]["mean"] += 0.1
        elif name == "second moment":
            bad["cases"][0]["second_moment"] += 0.1
        else:
            bad["pricing"][0]["price"] += 1
        try:
            verify(bad)
            rejected = False
        except ValueError:
            rejected = True
        rows.append(dict(mutation=name, rejected=rejected))
    from hullkit import _martingales as original

    for name in ("zero drift", "omit Ito", "ignore horizon", "wrong measure"):
        proxy = SimpleNamespace(
            **{
                n: getattr(original, n)
                for n in ("ratio_drift", "ratio_conditional_mean", "numeraire_drifts")
            }
        )
        if name == "zero drift":
            proxy.ratio_drift = lambda *a: 0.0
        elif name == "omit Ito":
            proxy.ratio_drift = lambda mf, mg, sf, sg: mf - mg
        elif name == "ignore horizon":
            proxy.ratio_conditional_mean = lambda x, *a: x
        else:
            proxy.numeraire_drifts = lambda r, sf, sg: (r, r)
        try:
            verify(data, proxy)
            rejected = False
        except ValueError:
            rejected = True
        rows.append(dict(mutation="API " + name, rejected=rejected))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads(DATA.read_text())
    result = verify(data)
    controls = negative_controls(data)
    if not all(r["rejected"] for r in controls):
        raise ValueError("numerical mutation accepted")
    result.update(
        negative_controls=controls,
        artifact_sha256=hashlib.sha256(DATA.read_bytes()).hexdigest(),
        source_sha256={n: hashlib.sha256((PROJECT / n).read_bytes()).hexdigest() for n in SOURCES},
    )
    payload = (
        json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    )
    if args.check:
        if not OUT.is_file() or OUT.read_text() != payload:
            raise ValueError("numerical record stale or missing")
    else:
        OUT.write_text(payload)
    print(
        "PASS: §28.3 conditional API, nine conditional MCs, two-measure Gaussian prices and eight controls"
    )


if __name__ == "__main__":
    main()
