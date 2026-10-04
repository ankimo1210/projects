"""Verify signed correlated factors, independent conditional oracle and raw MC."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np

try:
    from .build_multifactor_reference import build
except ImportError:
    from build_multifactor_reference import build

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "docs/validation/section-28-5/reference.json"
OUT = DATA.with_name("numerical-check.json")
API_NAMES = (
    "correlation_factor",
    "factor_ratio_drift",
    "factor_numeraire_drifts",
    "factor_ratio_conditional_mean",
)
SOURCES = (
    "scripts/build_multifactor_reference.py",
    "scripts/verify_multifactor_numerics.py",
    "hullkit/src/hullkit/_multi_factor_martingales.py",
)
SAMPLES = 262144


def close(actual, expected, label, tolerance=1e-12):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if (
        a.shape != b.shape
        or not np.all(np.isfinite(a))
        or not np.allclose(a, b, rtol=0, atol=tolerance)
    ):
        raise ValueError("multifactor numerical mismatch: " + label)
    return float(np.max(np.abs(a - b), initial=0))


def summary(values, truth):
    mean = float(np.mean(values))
    se = float(np.std(values, ddof=1) / math.sqrt(len(values)))
    if not math.isfinite(mean) or not math.isfinite(se):
        raise ValueError("nonfinite MC result")
    if se < 1e-14:
        if abs(mean - truth) > 1e-12:
            raise ValueError("degenerate Monte Carlo mismatch")
        z = 0.0
    else:
        z = abs(mean - truth) / se
        if z > 5:
            raise ValueError("Monte Carlo exceeds five standard errors")
    return dict(mean=mean, se=se, z=z, reference=truth)


def call_weighted(f0, k, mf, mg, vf, vg, cov, h):
    logmean = (mf - 0.5 * vf) * h - cov * h
    prefactor = math.exp((vg - mg) * h)
    if vf == 0:
        return prefactor * max(f0 * math.exp(logmean) - k, 0.0)
    sd = math.sqrt(vf * h)
    d2 = (math.log(f0 / k) + logmean) / sd

    def cdf(x):
        return 0.5 * math.erfc(-x / math.sqrt(2))

    return prefactor * (f0 * math.exp(logmean + 0.5 * vf * h) * cdf(d2 + sd) - k * cdf(d2))


def verify(data, api=None, reference=None, mc=True):
    if reference is None:
        reference = build()
    if data != reference:
        raise ValueError("independent multifactor reference changed")
    if api is None:
        from hullkit import _multi_factor_martingales as api
    market = data["market"]
    r, h, f0, g0, k = (market[n] for n in ("r", "horizon", "f0", "g0", "strike"))
    results = []
    conditional = []
    pricing = []
    mc_rows = []
    errors = []
    for number, row in enumerate(data["cases"]):
        sf, sg, C = (np.asarray(row[n], float) for n in ("f_loadings", "g_loadings", "correlation"))
        L = api.correlation_factor(C)
        errors.append(close(L @ L.T, C, "PSD factor", 2e-13))
        lf, lg = sf @ L, sg @ L
        vf, vg, cov = float(lf @ lf), float(lg @ lg), float(lf @ lg)
        drifts = api.factor_numeraire_drifts(r, sf, sg, C)
        a_q = api.factor_ratio_drift(r, r, sf, sg, C)
        a_g = api.factor_ratio_drift(*drifts, sf, sg, C)
        errors += [
            close(drifts, row["g_drifts"], "g drifts"),
            close(a_q, row["ratio_q_drift"], "Q ratio drift"),
            close(a_g, 0, "g ratio drift"),
        ]
        independent_drifts = api.factor_numeraire_drifts(r, lf, lg)
        errors.append(close(drifts, independent_drifts, "independent basis"))
        rotation, _ = np.linalg.qr(
            np.arange(1, len(sf) ** 2 + 1, dtype=float).reshape(len(sf), len(sf)) + np.eye(len(sf))
        )
        errors.append(
            close(api.factor_numeraire_drifts(r, lf @ rotation, lg @ rotation), drifts, "rotation")
        )
        vratio = float((lf - lg) @ (lf - lg))
        errors.append(close(vratio, row["relative_ratio_variance"], "ratio variance"))
        price_q = call_weighted(f0, k, r, r, vf, 0, 0, h)
        price_g = call_weighted(f0, k, *drifts, vf, vg, cov, h)
        errors += [
            close(price_q, row["prices"]["q_price"], "Q price", 1e-9),
            close(price_g, row["prices"]["g_price"], "same payoff G price", 1e-9),
        ]
        results.append(
            dict(
                id=row["id"],
                g_drifts=list(drifts),
                ratio_q_drift=a_q,
                ratio_g_drift=a_g,
                ratio_variance=vratio,
                f_variance=vf,
                g_variance=vg,
                covariance=cov,
            )
        )
        pricing.append(dict(id=row["id"], price_q=price_q, price_g=price_g))
        rng = np.random.default_rng(385730 + number)
        if mc:
            z = rng.standard_normal((SAMPLES, len(sf)))
            w = z @ L.T * math.sqrt(h)
            fq = f0 * np.exp((r - 0.5 * vf) * h + w @ sf)
            gq = g0 * np.exp((r - 0.5 * vg) * h + w @ sg)
            fg = f0 * np.exp((drifts[0] - 0.5 * vf) * h + w @ sf)
            gg = g0 * np.exp((drifts[1] - 0.5 * vg) * h + w @ sg)
            density = gq / g0 * math.exp(-r * h)
            mc_rows.append(
                dict(
                    id=row["id"],
                    seed=385730 + number,
                    density=summary(density, 1),
                    ratio_g=summary(fg / gg, f0 / g0),
                    ratio_reweighted_q=summary(density * fq / gq, f0 / g0),
                    call_q=summary(math.exp(-r * h) * np.maximum(fq - k, 0), price_q),
                    call_g=summary(g0 * np.maximum(fg - k, 0) / gg, price_q),
                )
            )
        for index, state in enumerate(row["conditional"]):
            value, step = state["observed_ratio"], state["horizon"]
            gm = api.factor_ratio_conditional_mean(value, *drifts, sf, sg, step, C)
            qm = api.factor_ratio_conditional_mean(value, r, r, sf, sg, step, C)
            errors += [
                close(gm, state["g_mean"], "conditioned G mean"),
                close(qm, state["q_mean"], "conditioned Q mean"),
            ]
            c = dict(id=row["id"], observed_ratio=value, horizon=step, g_mean=gm, q_mean=qm)
            if mc:
                normal = np.random.default_rng(485730 + number * 12 + index).standard_normal(
                    SAMPLES
                )
                future = value * np.exp(
                    (a_g - 0.5 * vratio) * step + math.sqrt(vratio * step) * normal
                )
                c["mc"] = summary(future, state["g_mean"])
            conditional.append(c)
    zvalues = [v["z"] for row in mc_rows for v in row.values() if isinstance(v, dict)]
    zvalues.extend(row["mc"]["z"] for row in conditional if "mc" in row)
    return dict(
        section="28.5",
        status="PASS",
        synthetic=True,
        source_requirement_count=6,
        case_count=len(results),
        conditional_count=len(conditional),
        samples=SAMPLES,
        max_api_error=max(errors),
        max_mc_se=max(zvalues, default=0.0),
        api_cases=results,
        api_conditional_means=conditional,
        pricing=pricing,
        pricing_mc=mc_rows,
    )


def result_digest(record):
    data = {
        name: record[name]
        for name in ("api_cases", "api_conditional_means", "pricing", "pricing_mc")
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True, allow_nan=False).encode()).hexdigest()


def negative_controls(data):
    from hullkit import _multi_factor_martingales as api

    rows = []
    original = verify(data, reference=data, mc=False)
    saved = copy.deepcopy(data)
    saved["cases"][0]["g_drifts"][0] += 0.01
    for name in (
        "saved_drift",
        "omit_correlation",
        "wrong_cross_sign",
        "double_C",
        "initial_ratio",
        "log_drift",
        "jitter_PSD",
        "missing_path_numeraire",
    ):
        proxy = SimpleNamespace(**{n: getattr(api, n) for n in API_NAMES})
        try:
            if name == "saved_drift":
                verify(saved, reference=data, mc=False)
            elif name == "omit_correlation":
                proxy.factor_numeraire_drifts = lambda r, f, g, C=None: api.factor_numeraire_drifts(
                    r, f, g
                )
                verify(data, proxy, reference=data, mc=False)
            elif name == "wrong_cross_sign":
                proxy.factor_ratio_drift = lambda mf, mg, f, g, C=None: (
                    api.factor_ratio_drift(mf, mg, f, g, C)
                    + 2 * float(np.asarray(f) @ C @ np.asarray(g))
                )
                verify(data, proxy, reference=data, mc=False)
            elif name == "double_C":
                proxy.factor_numeraire_drifts = lambda r, f, g, C=None: (
                    api.factor_numeraire_drifts(r, f, g)
                    if C is None
                    else (
                        r + np.asarray(f) @ C @ C @ np.asarray(g),
                        r + np.asarray(g) @ C @ C @ np.asarray(g),
                    )
                )
                verify(data, proxy, reference=data, mc=False)
            elif name == "initial_ratio":
                proxy.factor_ratio_conditional_mean = lambda value, mf, mg, f, g, h, C=None: (
                    api.factor_ratio_conditional_mean(1.25, mf, mg, f, g, h, C)
                )
                verify(data, proxy, reference=data, mc=False)
            elif name == "log_drift":
                proxy.factor_ratio_drift = lambda mf, mg, f, g, C=None: (
                    api.factor_ratio_drift(mf, mg, f, g, C)
                    - 0.5 * float((np.asarray(f) - g) @ C @ (np.asarray(f) - g))
                )
                verify(data, proxy, reference=data, mc=False)
            elif name == "jitter_PSD":
                proxy.correlation_factor = lambda C: (
                    api.correlation_factor(C) + 1e-5 * np.eye(len(C))
                )
                verify(data, proxy, reference=data, mc=False)
            else:
                row = data["cases"][0]
                C = np.array(row["correlation"])
                f = np.array(row["f_loadings"])
                g = np.array(row["g_loadings"])
                mf, _mg = api.factor_numeraire_drifts(0.04, f, g, C)
                wrong = 80 * call_weighted(100, 105, mf, 0, float(f @ C @ f), 0, 0, 1.5)
                close(wrong, original["pricing"][0]["price_g"], "missing random g divisor", 1e-9)
        except ValueError:
            rows.append(dict(mutation=name, rejected=True))
        else:
            raise ValueError("negative control accepted: " + name)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = json.loads(DATA.read_text())
    fresh = build()
    result = verify(data, reference=fresh)
    result["negative_controls"] = negative_controls(data)
    result["reference_sha256"] = hashlib.sha256(DATA.read_bytes()).hexdigest()
    result["source_sha256"] = {
        name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in SOURCES
    }
    result["result_sha256"] = result_digest(result)
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text() != payload:
            raise ValueError("multifactor numerical record is stale")
    else:
        OUT.write_text(payload)
    print("PASS: §28.5 correlated API/132 conditional MC/raw same-payoff prices/eight mutations")


if __name__ == "__main__":
    main()
