"""Compare §28.6 Black and exact Gaussian APIs with independent Q/T teachers.

Raw fixed-seed MC is never self-normalized. Stochastic zero-hit payoffs are
not treated as deterministic: an exact Gaussian importance likelihood is
used, with the direct sample diagnostics kept explicitly.
"""

import copy
import math
from types import SimpleNamespace

import numpy as np

from johnhull.hullkit.tests._forward_black_reference import build

SAMPLES = 262144
API_NAMES = ("forward_black_price", "gaussian_forward_statistics")


def compare_teacher(actual, expected):
    """Compare numeric teacher values tolerantly, with fixed structure/order."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            raise ValueError("independent reference structure mismatch")
        for key in expected:
            compare_teacher(actual[key], expected[key])
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError("independent reference matrix mismatch")
        for a, b in zip(actual, expected, strict=True):
            compare_teacher(a, b)
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not np.allclose(actual, expected, atol=1e-10, rtol=1e-11):
            raise ValueError("independent numerical reference mismatch")
    elif actual != expected:
        raise ValueError("independent reference metadata mismatch")


def close(actual, expected, label, atol=1e-9, rtol=1e-11):
    a, b = np.asarray(actual, dtype=float), np.asarray(expected, dtype=float)
    if (
        a.shape != b.shape
        or not np.all(np.isfinite(a))
        or not np.allclose(a, b, atol=atol, rtol=rtol)
    ):
        raise ValueError("forward Black numerical mismatch: " + label)
    return float(np.max(np.abs(a - b), initial=0))


def mc_summary(values, truth, *, stochastic):
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or len(x) < 2 or not np.all(np.isfinite(x)):
        raise ValueError("invalid MC sample")
    mean = float(np.mean(x))
    se = float(np.std(x, ddof=1) / math.sqrt(len(x)))
    if stochastic:
        if se <= 0:
            raise ValueError("zero SE for stochastic Monte Carlo")
        z = abs(mean - truth) / se
        if not math.isfinite(z) or z > 5:
            raise ValueError("MC exceeds five standard errors")
    else:
        if np.max(np.abs(x - truth)) > 1e-10:
            raise ValueError("deterministic MC mismatch")
        z = 0.0
    return dict(
        mean=mean,
        se=se,
        z=z,
        reference=truth,
        hit_count=int(np.count_nonzero(x)),
        stochastic=bool(stochastic),
        samples=len(x),
    )


def direct_diagnostic(x):
    return dict(
        mean=float(np.mean(x)),
        se=float(np.std(x, ddof=1) / math.sqrt(len(x))),
        hit_count=int(np.count_nonzero(x)),
        zero_hit=not bool(np.any(x)),
    )


def market_mc(row):
    inp, stat = row["inputs"], row["statistics"]
    t, eta, sigma, rho = (
        inp[k] for k in ("horizon", "rate_volatility", "stock_volatility", "correlation")
    )
    mj, vj, my, vy, cov = (
        stat[k]
        for k in (
            "mean_integral",
            "variance_integral",
            "mean_log_spot_Q",
            "terminal_variance",
            "cov_integral_log_spot",
        )
    )
    p, f = stat["discount"], stat["forward"]
    z = np.random.default_rng(row["seed"]).standard_normal((SAMPLES, 3))
    wr = math.sqrt(t) * z[:, 0]
    ws = math.sqrt(t) * (rho * z[:, 0] + math.sqrt(1 - rho * rho) * z[:, 1])
    j = mj + eta * (t / 2 * wr + math.sqrt(t**3 / 12) * z[:, 2])
    y = my + (j - mj) + sigma * ws
    yt = y - cov
    summaries = {
        "density": mc_summary(np.exp(-j) / p, 1.0, stochastic=eta > 0),
        "discounted_spot": mc_summary(np.exp(y - j), inp["spot"], stochastic=sigma > 0),
        "forward_mean": mc_summary(np.exp(yt), f, stochastic=vy > 0),
        "mean_integral": mc_summary(j, mj, stochastic=vj > 0),
        "log_mean_Q": mc_summary(y, my, stochastic=vy > 0),
        "log_mean_T": mc_summary(yt, my - cov, stochastic=vy > 0),
    }
    rows = []
    for price in row["prices"]:
        k = price["strike"]
        saved = {"strike": k}
        for kind in ("call", "put"):
            sign = 1 if kind == "call" else -1
            truth = price[kind]["t_quad"]
            xq = np.exp(-j) * np.maximum(sign * (np.exp(y) - k), 0.0)
            xt = p * np.maximum(sign * (np.exp(yt) - k), 0.0)
            direct_q, direct_t = direct_diagnostic(xq), direct_diagnostic(xt)
            importance = None
            if vy > 0 and (direct_q["se"] == 0 or direct_t["se"] == 0):
                sd = math.sqrt(vy)
                kink = (math.log(k) - my + cov) / sd
                theta = kink + 1 if kind == "call" else kink - 1
                seed = 286410 + (row["seed"] - 286310) * 100 + int(k) + (0 if kind == "call" else 1)
                zz = np.random.default_rng(seed).standard_normal((SAMPLES, 2))
                shifted = zz[:, 0] + theta
                conditional_j = (
                    mj + cov / sd * shifted + math.sqrt(max(vj - cov * cov / vy, 0)) * zz[:, 1]
                )
                conditional_y = my + sd * shifted
                conditional_yt = my - cov + sd * shifted
                likelihood = np.exp(-theta * zz[:, 0] - theta * theta / 2)
                xq = (
                    np.exp(-conditional_j)
                    * np.maximum(sign * (np.exp(conditional_y) - k), 0)
                    * likelihood
                )
                xt = p * np.maximum(sign * (np.exp(conditional_yt) - k), 0) * likelihood
                importance = dict(
                    normal_shift=theta,
                    seed=seed,
                    samples=SAMPLES,
                    likelihood="exp(-theta*Z-theta^2/2); raw, never self-normalized",
                    likelihood_mean=float(np.mean(likelihood)),
                    likelihood_se=float(np.std(likelihood, ddof=1) / math.sqrt(SAMPLES)),
                )
            saved[kind] = dict(
                reference=truth,
                direct_Q=direct_q,
                direct_T=direct_t,
                importance=importance,
                mc_Q=mc_summary(xq, truth, stochastic=vy > 0),
                mc_T=mc_summary(xt, truth, stochastic=vy > 0),
            )
        rows.append(saved)
    return summaries, rows


def verify(data, api=None, *, reference=None, mc=True):
    if reference is None:
        reference = build()
    compare_teacher(data, reference)
    if api is None:
        from hullkit import _forward_black as api
    from hullkit.ir_options import bond_option_black

    result = dict(
        section="28.6",
        case_count=len(data["cases"]),
        price_count=42,
        samples=SAMPLES,
        max_api_error=0.0,
        max_quadrature_error=0.0,
        max_moment_error=0.0,
        max_mc_se=0.0,
        cases=[],
        external_forward=[],
        limits=[],
    )
    for row in data["cases"]:
        inp, expected = row["inputs"], row["statistics"]
        actual = api.gaussian_forward_statistics(**inp)
        if set(actual) != set(expected):
            raise ValueError("Gaussian statistics key mismatch")
        for name in expected:
            result["max_api_error"] = max(
                result["max_api_error"], close(actual[name], expected[name], name, 1e-10, 1e-12)
            )
        my, vy, cov = (
            expected["mean_log_spot_Q"],
            expected["terminal_variance"],
            expected["cov_integral_log_spot"],
        )
        truths = dict(
            density_quad=1.0,
            discounted_spot_quad=inp["spot"],
            forward_quad=expected["forward"],
            log_first_Q=my,
            log_second_Q=my * my + vy,
            log_first_T=my - cov,
            log_second_T=(my - cov) ** 2 + vy,
            integrated_forward_variance=vy,
        )
        for name, truth in truths.items():
            result["max_moment_error"] = max(
                result["max_moment_error"], close(row["moments"][name], truth, name, 1e-10, 0)
            )
        output = dict(id=row["id"], statistics=actual, prices=[])
        for price in row["prices"]:
            p, f, sigma, t = (
                expected["discount"],
                expected["forward"],
                expected["forward_sigma"],
                inp["horizon"],
            )
            pr = dict(strike=price["strike"], parity=price["parity"])
            for kind in ("call", "put"):
                oracle = price[kind]
                value = api.forward_black_price(p, f, price["strike"], sigma, t, kind)
                result["max_api_error"] = max(
                    result["max_api_error"], close(value, oracle["t_quad"], kind)
                )
                # A rare positive tail is also checked relatively, not swallowed by abs tolerance.
                if 0 < oracle["t_quad"] < 1e-5:
                    close(value, oracle["t_quad"], "rare tail relative", 0, 1e-10)
                result["max_quadrature_error"] = max(
                    result["max_quadrature_error"],
                    close(oracle["q_quad"], oracle["t_quad"], "Q/T price"),
                    close(oracle["closed"], oracle["t_quad"], "pure closed price"),
                )
                if any(not 0 <= oracle[name] < 1e-9 for name in ("q_tail_bound", "t_tail_bound")):
                    raise ValueError("quadrature tail bound exceeds tolerance")
                if sigma > 0 and t > 0:
                    close(
                        bond_option_black(p, f, price["strike"], sigma, t, kind),
                        value,
                        "existing positive public Black",
                    )
                pr[kind] = dict(api=value, reference=oracle["t_quad"])
            close(pr["call"]["api"] - pr["put"]["api"], price["parity"], "parity")
            output["prices"].append(pr)
        if mc:
            summaries, mcprices = market_mc(row)
            output["mc_moments"] = summaries
            for pr, stochastic in zip(output["prices"], mcprices, strict=True):
                for kind in ("call", "put"):
                    pr[kind].update(stochastic[kind])
            zs = [s["z"] for s in summaries.values()]
            zs += [
                pr[kind][name]["z"]
                for pr in mcprices
                for kind in ("call", "put")
                for name in ("mc_Q", "mc_T")
            ]
            result["max_mc_se"] = max(result["max_mc_se"], *zs)
        result["cases"].append(output)
    for key in ("external_forward", "limits"):
        for row in data[key]:
            values = {
                name: api.forward_black_price(
                    row["discount"],
                    row["forward"],
                    row["strike"],
                    row["volatility"],
                    row["horizon"],
                    name,
                )
                for name in ("call", "put")
            }
            for name, value in values.items():
                result["max_api_error"] = max(
                    result["max_api_error"], close(value, row[name], key + name)
                )
            close(
                values["call"] - values["put"],
                row["discount"] * (row["forward"] - row["strike"]),
                key + "parity",
            )
            result[key].append(values)
    return result


def negative_controls(original):
    from hullkit import _forward_black as api

    names = (
        "futures_as_forward",
        "spot_vol_as_forward_vol",
        "Q_outer_discount",
        "inverse_RN",
        "zero_SE_stochastic",
        "saved_teacher",
        "saved_quadrature",
        "saved_tail",
        "matrix_order",
    )
    rows = []
    positive = original["cases"][1]
    stat = positive["statistics"]
    for name in names:
        data = copy.deepcopy(original)
        proxy = SimpleNamespace(**{n: getattr(api, n) for n in API_NAMES})
        try:
            if name == "futures_as_forward":
                proxy.forward_black_price = lambda p, f, k, s, t, kind="call": (
                    api.forward_black_price(p, f * stat["futures"] / stat["forward"], k, s, t, kind)
                )
                verify(data, proxy, reference=original, mc=False)
            elif name == "spot_vol_as_forward_vol":
                proxy.forward_black_price = lambda p, f, k, s, t, kind="call": (
                    api.forward_black_price(p, f, k, 0.25, t, kind)
                )
                verify(data, proxy, reference=original, mc=False)
            elif name == "Q_outer_discount":
                close(
                    positive["prices"][1]["call"]["wrong_outer_discount_Q"],
                    positive["prices"][1]["call"]["t_quad"],
                    name,
                )
            elif name == "inverse_RN":
                close(math.exp(stat["variance_integral"]), 1.0, name, 1e-10, 0)
            elif name == "zero_SE_stochastic":
                mc_summary(np.zeros(10), 7.168352139439199e-8, stochastic=True)
            else:
                if name == "saved_teacher":
                    data["cases"][1]["statistics"]["forward"] += 0.01
                elif name == "saved_quadrature":
                    data["cases"][1]["prices"][1]["call"]["q_quad"] += 0.1
                elif name == "saved_tail":
                    data["cases"][1]["prices"][1]["call"]["q_tail_bound"] = 1.0
                else:
                    data["cases"].reverse()
                verify(data, reference=original, mc=False)
        except ValueError:
            rows.append(dict(mutation=name, rejected=True))
        else:
            raise ValueError("negative control accepted: " + name)
    return rows
