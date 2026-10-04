"""Check exact conditional numeraire APIs against independent kernel quadrature."""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.optimize import brentq

try:
    from .build_numeraire_reference import build, gaussian_avg
except ImportError:
    from build_numeraire_reference import build, gaussian_avg

PROJECT = Path(__file__).resolve().parents[1]
DATA = PROJECT / "docs/validation/section-28-4/reference.json"
OUT = DATA.with_name("numerical-check.json")
SAMPLES = 262144
SOURCES = (
    "scripts/build_numeraire_reference.py",
    "scripts/verify_numeraire_numerics.py",
    "hullkit/src/hullkit/_numeraire_choices.py",
    "hullkit/src/hullkit/hull_white.py",
    "hullkit/src/hullkit/rates.py",
)
API_NAMES = (
    "FlatHW",
    "ou_moments",
    "bond",
    "joint_moments",
    "sample_joint",
    "stock_statistics",
    "rate_statistics",
    "annuity_values",
    "annuity_statistics",
)
RESULT_KEYS = ("api_joint", "api_stock", "api_rates", "api_annuity", "pricing_mc")


def result_digest(result):
    return hashlib.sha256(
        json.dumps({k: result[k] for k in RESULT_KEYS}, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def close(actual, expected, label, atol=2e-12, rtol=0):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if (
        a.shape != b.shape
        or not np.all(np.isfinite(a))
        or not np.allclose(a, b, atol=atol, rtol=rtol)
    ):
        raise ValueError("numeraire numerical mismatch: " + label)
    return float(np.max(np.abs(a - b), initial=0))


def summary(values, expected):
    mean = float(np.mean(values))
    se = float(np.std(values, ddof=1) / math.sqrt(len(values)))
    if not math.isfinite(mean) or not math.isfinite(se) or se <= 0:
        raise ValueError("invalid raw iid MC statistics")
    z = abs(mean - expected) / se
    if z > 5:
        raise ValueError("numeraire MC exceeds five standard errors")
    return dict(mean=mean, se=se, z=z, reference=expected)


def verify(data, api=None, reference=None):
    oracle = build() if reference is None else reference
    if data != oracle:
        raise ValueError("independent numeraire reference changed")
    if api is None:
        from hullkit import _numeraire_choices as api
    from hullkit import hull_white as hw

    errors = []
    joints = []
    for row in data["joint"]:
        m = api.FlatHW(row["a"], row["eta"], row["r0"])
        mean, cov = api.joint_moments(row["t"], row["T"], row["x_t"], m)
        errors.append(close(mean, row["mean_X_I_W"], "joint mean"))
        errors.append(
            close(cov, row["covariance_X_I_W"], "joint covariance", atol=1e-25, rtol=2e-12)
        )
        price = api.bond(row["t"], row["T"], row["x_t"], m)
        errors.append(close(price, row["bond"], "conditional bond"))
        curve = ([0.0, 1.0, 2.0, 10.0], [m.zero] * 4)
        errors.append(
            close(
                hw.hw_discount_bond(
                    row["t"], row["T"], row["x_t"], curve, hw.HullWhiteParams(m.a, m.eta)
                ),
                price,
                "existing HW Q coordinate",
            )
        )
        # Independent measure tilt uses stored kernel covariance, not API moments.
        h = row["T"] - row["t"]
        tilted, _ = api.joint_moments(row["t"], row["T"], row["x_t"], m, payment=row["T"] + 0.5)
        b = -math.expm1(-m.a * 0.5) / m.a
        target = np.asarray(row["mean_X_I_W"]) - np.asarray(row["covariance_X_I_W"]) @ np.array(
            [b, 1.0, 0.0]
        )
        errors.append(close(tilted, target, "payment tilt"))
        del h
        joints.append(
            dict(
                mean=mean.tolist(), covariance=cov.tolist(), bond=price, tilted_mean=tilted.tolist()
            )
        )
    for row in data["stability"]:
        u = row["u_ah"]
        if u == 0:
            continue
        m = api.FlatHW(u, 1.0, 0.0)
        _, vi, _, _, ciw = api.ou_moments(1.0, m)
        errors.append(
            close([vi, ciw], [row["e"], row["d"]], "small-ah integrated moments", atol=2e-12)
        )
    stocks = []
    for row in data["stock"]:
        m = api.FlatHW(row["a"], row["eta"], row["r0"])
        result = api.stock_statistics(
            row["t"], row["T"], row["x_t"], row["S_t"], row["K"], row["stock_loading"], m
        )
        for name, want in [
            ("price_q", "call_Q_quad"),
            ("price_payment", "call_T_quad"),
            ("price_wrong_q_outer_discount", "wrong_external_Q_discount"),
            ("futures", "futures_Q"),
            ("forward", "forward_T"),
            ("discount", "P_tT"),
            ("log_variance", "var_log_S"),
        ]:
            errors.append(close(result[name], row[want], name, atol=1e-9))
        stocks.append(result)
    rates = []
    for row in data["rates"]:
        m = api.FlatHW(0.2, row["eta"], row["r0"])
        result = api.rate_statistics(row["t"], row["fix_T"], row["pay_U"], row["x_t"], m)
        for name, want in [
            ("forward", "forward"),
            ("term_q", "term_E_Q"),
            ("term_payment", "term_E_pay"),
            ("term_wrong_fix", "term_E_wrong_fix"),
            ("overnight_q", "overnight_E_Q"),
            ("overnight_payment", "overnight_E_pay"),
            ("overnight_wrong_fix", "overnight_E_wrong_fix"),
            ("fra_pv", "term_FRA_PV"),
        ]:
            errors.append(close(result[name], row[want], name))
        rates.append(result)
    annuities = []
    for row in data["annuity"]:
        if row["basis_mode"] == "multiplicative":
            continue  # independent contrasting model, never production basis
        m = api.FlatHW(0.2, row["eta"], row["r0"])
        basis = (
            None
            if row["basis_mode"] == "single"
            else [
                math.expm1((m.zero + row["basis"]) * d) / d - math.expm1(m.zero * d) / d
                for d in row["deltas"]
            ]
        )
        args = (row["t"], row["T"], row["payments"], row["x_t"], m, basis)
        result = api.annuity_statistics(*args)
        for name, want in [
            ("annuity", "A_t"),
            ("value", "V_t"),
            ("rate", "swap_rate_t"),
            ("weights", "mixture_weights"),
            ("component_means", "mixture_means_x_T"),
            ("state_variance", "variance_x_T"),
        ]:
            errors.append(close(result[name], row[want], name))

        def rate(x, m=m, row=row, basis=basis):
            return api.annuity_values(row["T"], row["T"], row["payments"], x, m, basis)[2]

        kink = brentq(lambda x, row=row: rate(x) - row["strike"], -1.0, 1.0)
        ea = sum(
            w * gaussian_avg(rate, mu, result["state_variance"])
            for w, mu in zip(result["weights"], result["component_means"], strict=True)
        )
        price_a = result["annuity"] * sum(
            w
            * gaussian_avg(
                lambda x, row=row: max(rate(x) - row["strike"], 0), mu, result["state_variance"], kink
            )
            for w, mu in zip(result["weights"], result["component_means"], strict=True)
        )
        errors.append(close(ea, row["mean_A_swap_rate"], "conditional annuity mean"))
        errors.append(close(price_a, row["payer_A_quad"], "annuity payer price", atol=1e-9))
        qmean, qcov = api.joint_moments(row["t"], row["T"], row["x_t"], m)

        def qpay(x, m=m, row=row, basis=basis, qmean=qmean, qcov=qcov):
            if qcov[0, 0] == 0:
                d = math.exp(-qmean[1])
            else:
                d = math.exp(
                    -qmean[1]
                    - qcov[0, 1] / qcov[0, 0] * (x - qmean[0])
                    + 0.5 * (qcov[1, 1] - qcov[0, 1] ** 2 / qcov[0, 0])
                )
            at, vt, _ = api.annuity_values(row["T"], row["T"], row["payments"], x, m, basis)
            return d * max(vt - row["strike"] * at, 0.0)

        price_q = gaussian_avg(qpay, qmean[0], qcov[0, 0], kink)
        errors.append(close(price_q, row["payer_Q_quad"], "Q path-discount payer", atol=1e-9))
        annuities.append(
            {
                **{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in result.items()},
                "mean_a_rate": ea,
                "price_a": price_a,
                "price_q": price_q,
            }
        )
    prices = []
    for index in (0, 1, 2, 3, 6):
        row = data["stock"][index]
        m = api.FlatHW(row["a"], row["eta"], row["r0"])
        for measure, payment in [("Q", None), ("T", row["T"])]:
            sample = api.sample_joint(
                row["t"],
                row["T"],
                row["x_t"],
                m,
                SAMPLES,
                290100 + 2 * index + (measure == "T"),
                payment,
            )
            h = row["T"] - row["t"]
            spot = row["S_t"] * np.exp(
                sample[:, 1]
                - 0.5 * row["stock_loading"] ** 2 * h
                + row["stock_loading"] * sample[:, 2]
            )
            payoff = np.maximum(spot - row["K"], 0)
            discount = np.exp(-sample[:, 1]) if measure == "Q" else row["P_tT"]
            out = dict(
                fixture_index=index,
                measure=measure,
                **summary(discount * payoff, row["call_Q_quad"]),
            )
            if measure == "Q":
                out["raw_rn"] = summary(np.exp(-sample[:, 1]) / row["P_tT"], 1.0)
            prices.append(out)
    result = dict(
        section="28.4",
        status="PASS",
        synthetic=True,
        source_requirement_count=12,
        joint_count=6,
        stock_count=18,
        rate_count=21,
        annuity_count=12,
        contrasting_basis_count=6,
        samples=SAMPLES,
        max_api_error=max(errors),
        max_mc_se=max(r["z"] for r in prices),
        api_joint=joints,
        api_stock=stocks,
        api_rates=rates,
        api_annuity=annuities,
        pricing_mc=prices,
    )
    result["result_sha256"] = result_digest(result)
    return result


def negative_controls(data):
    from hullkit import _numeraire_choices as original

    rows = []
    for name in ("stock price", "payment rate", "annuity rate", "kernel covariance"):
        bad = copy.deepcopy(data)
        if name == "stock price":
            bad["stock"][0]["call_Q_quad"] += 1
        elif name == "payment rate":
            bad["rates"][0]["term_E_pay"] += 0.01
        elif name == "annuity rate":
            bad["annuity"][0]["swap_rate_t"] += 0.01
        else:
            bad["joint"][0]["covariance_X_I_W"][0][1] += 0.01
        try:
            verify(bad, reference=data)
            rejected = False
        except ValueError:
            rejected = True
        rows.append(dict(mutation=name, rejected=rejected))
    for name in ("omit tilt", "Q outer discount", "fixing measure", "wrong annuity weights"):
        proxy = SimpleNamespace(**{n: getattr(original, n) for n in API_NAMES})
        if name == "omit tilt":
            proxy.joint_moments = lambda t, T, x, m, payment=None: original.joint_moments(
                t, T, x, m
            )
        elif name == "Q outer discount":

            def wrong_stock(*args):
                row = original.stock_statistics(*args)
                row["price_q"] = row["price_wrong_q_outer_discount"]
                return row

            proxy.stock_statistics = wrong_stock
        elif name == "fixing measure":

            def wrong_rate(*args):
                row = original.rate_statistics(*args)
                row["term_payment"] = row["term_wrong_fix"]
                return row

            proxy.rate_statistics = wrong_rate
        else:

            def wrong_annuity(*args):
                row = original.annuity_statistics(*args)
                row["weights"] = np.full(len(row["weights"]), 1 / len(row["weights"]))
                return row

            proxy.annuity_statistics = wrong_annuity
        try:
            verify(data, proxy, data)
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
    if not all(row["rejected"] for row in controls):
        raise ValueError("numerical mutation accepted")
    result.update(
        negative_controls=controls,
        artifact_sha256=hashlib.sha256(DATA.read_bytes()).hexdigest(),
        source_sha256={
            name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() for name in SOURCES
        },
    )
    payload = (
        json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    )
    if args.check:
        if not OUT.is_file() or OUT.read_text() != payload:
            raise ValueError("numeraire numerical record stale or missing")
    else:
        OUT.write_text(payload)
    print("PASS: §28.4 conditional API / independent quadrature / raw direct MC / eight mutations")


if __name__ == "__main__":
    main()
