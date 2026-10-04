"""M29 independent Gaussian reference; no hullkit imports.

All market inputs are synthetic. Exact stochastic-integral kernels provide the
oracle; stable dimensionless series are a separately coded proposal, not a
production-function substitute. Run with the existing workspace Python.
"""

from __future__ import annotations

import argparse
import json
import math
from itertools import pairwise
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq

EPS_PRICE = 1e-9
EPS_RATE = 2e-12
EPS_MOMENT_REL = 2e-12
EPS_MOMENT_ABS = 1e-25
SQRT2PI = math.sqrt(2 * math.pi)


def normal_pdf(z):
    return math.exp(-0.5 * z * z) / SQRT2PI


def normal_cdf(z):
    return 0.5 * math.erfc(-z / math.sqrt(2))


def b1(u):
    if u == 0:
        return 1.0
    return -math.expm1(-u) / u


def stable_dimensionless(u):
    """Independent numerical proposal for production's scalar moment core.

    q/(eta^2 h)=b2; cov(I,W)/(eta h^2)=d;
    var(I)/(eta^2 h^3)=e. Series avoids catastrophic cancellation.
    """
    if abs(u) <= 0.1:
        d = math.fsum((-u) ** k / math.factorial(k + 2) for k in range(20))
        e = math.fsum((-u) ** k * (2 ** (k + 2) - 2) / math.factorial(k + 3) for k in range(20))
    else:
        d = (1 - b1(u)) / u
        e = (1 - 2 * b1(u) + b1(2 * u)) / (u * u)
    return b1(u), b1(2 * u), d, e


def kernel_dimensionless(u):
    """Oracle integrates positive kernels on a unit interval."""

    def kx(v):
        return math.exp(-u * v)

    def ki(v):
        return v * b1(u * v)

    q = quad(lambda v: kx(v) ** 2, 0, 1, epsabs=1e-14, epsrel=1e-13)[0]
    ix = quad(lambda v: ki(v) * kx(v), 0, 1, epsabs=1e-14, epsrel=1e-13)[0]
    iw = quad(ki, 0, 1, epsabs=1e-14, epsrel=1e-13)[0]
    ii = quad(lambda v: ki(v) ** 2, 0, 1, epsabs=1e-14, epsrel=1e-13)[0]
    xw = quad(kx, 0, 1, epsabs=1e-14, epsrel=1e-13)[0]
    return {"var_x": q, "cov_x_i": ix, "cov_i_w": iw, "var_i": ii, "cov_x_w": xw, "var_w": 1.0}


class Model:
    def __init__(self, a=0.2, eta=0.02, r0=0.04):
        if not (a > 0 and eta >= 0):
            raise ValueError("a>0, eta>=0")
        self.a, self.eta, self.r0 = a, eta, r0

    def b(self, h):
        return h * b1(self.a * h)

    def c(self, t):
        return 0.5 * self.eta**2 * self.b(t) ** 2

    def phi_int(self, t, u):
        # Integrates the absolute-time deterministic shift independently.
        h = u - t
        return h * quad(lambda v: self.r0 + self.c(t + h * v), 0, 1, epsabs=1e-14, epsrel=1e-13)[0]

    def moments(self, t, u, x=0.0):
        h = u - t
        if h < 0:
            raise ValueError("u>=t")
        k = kernel_dimensionless(self.a * h)
        eta = self.eta
        mx = math.exp(-self.a * h) * x
        mi = self.b(h) * x + self.phi_int(t, u)
        covariance = np.array(
            [
                [eta**2 * h * k["var_x"], eta**2 * h**2 * k["cov_x_i"], eta * h * k["cov_x_w"]],
                [
                    eta**2 * h**2 * k["cov_x_i"],
                    eta**2 * h**3 * k["var_i"],
                    eta * h**2 * k["cov_i_w"],
                ],
                [eta * h * k["cov_x_w"], eta * h**2 * k["cov_i_w"], h],
            ]
        )
        return np.array([mx, mi, 0.0]), covariance

    def bond(self, t, u, x=0.0):
        # Conditional Gaussian expectation E_Q[exp(-integral r)|x_t].
        _, cov = self.moments(t, u, x)
        return math.exp(-self.b(u - t) * x - self.phi_int(t, u) + 0.5 * cov[1, 1])

    def payment_moments(self, t, fix, pay, x=0.0):
        mean, cov = self.moments(t, fix, x)
        # RN tilt -integral(t,fix) r - B(fix,pay) X_fix.
        tilt = np.array([-self.b(pay - fix), -1.0, 0.0])
        return mean + cov @ tilt, cov


def gaussian_avg(fun, mean, variance, kink=None):
    if variance == 0:
        return fun(mean)
    sd = math.sqrt(variance)
    points = [-12.0, 12.0]
    if kink is not None and -12 < (kink - mean) / sd < 12:
        points.insert(1, (kink - mean) / sd)
    return math.fsum(
        quad(
            lambda z: fun(mean + sd * z) * normal_pdf(z),
            left,
            right,
            epsabs=1e-12,
            epsrel=2e-12,
            limit=250,
        )[0]
        for left, right in pairwise(points)
    )


def call_fixture(model, t, T, x, S, K, loading):
    mean, cov = model.moments(t, T, x)
    h = T - t
    p = model.bond(t, T, x)
    my = math.log(S) + mean[1] - 0.5 * loading**2 * h
    vy = cov[1, 1] + loading**2 * h + 2 * loading * cov[1, 2]
    cyi = cov[1, 1] + loading * cov[1, 2]
    mt, _ = model.payment_moments(t, T, T, x)
    my_t = math.log(S) + mt[1] - 0.5 * loading**2 * h + loading * mt[2]
    # Pure Gaussian exp-moments, one-dimensional Q conditional-discount
    # integral, direct T-density integral, and erfc are separate paths.
    fq = math.exp(my + 0.5 * vy)
    ft = math.exp(my_t + 0.5 * vy)
    if vy == 0:
        q_price = p * max(math.exp(my) - K, 0.0)
        t_price = q_price
        closed = q_price
        wrong = q_price
    else:
        sd = math.sqrt(vy)
        klog = math.log(K)

        def q_integrand(y):
            md = -mean[1] - cyi / vy * (y - my)
            vd = cov[1, 1] - cyi**2 / vy
            return math.exp(md + 0.5 * max(vd, 0.0)) * max(math.exp(y) - K, 0.0)

        q_price = gaussian_avg(q_integrand, my, vy, klog)
        t_price = p * gaussian_avg(lambda y: max(math.exp(y) - K, 0), my_t, vy, klog)
        wrong = p * gaussian_avg(lambda y: max(math.exp(y) - K, 0), my, vy, klog)
        d1 = (math.log((S / p) / K) + 0.5 * vy) / sd
        closed = p * ((S / p) * normal_cdf(d1) - K * normal_cdf(d1 - sd))
    rn_mean = math.exp(-mean[1] + 0.5 * cov[1, 1]) / p
    out = {
        "t": t,
        "T": T,
        "x_t": x,
        "S_t": S,
        "K": K,
        "stock_loading": loading,
        "a": model.a,
        "eta": model.eta,
        "r0": model.r0,
        "P_tT": p,
        "var_log_S": vy,
        "cov_integral_log_S": cyi,
        "mean_log_S_Q": my,
        "mean_log_S_T": my_t,
        "futures_Q": fq,
        "forward_T": ft,
        "spot_over_bond": S / p,
        "call_Q_quad": q_price,
        "call_T_quad": t_price,
        "call_erfc": closed,
        "wrong_external_Q_discount": wrong,
        "raw_RN_mean": rn_mean,
        "forward_pv_Q": S - K * p,
        "forward_pv_T": p * (ft - K),
    }
    assert abs(q_price - t_price) < EPS_PRICE
    assert abs(q_price - closed) < EPS_PRICE
    assert abs(ft - S / p) < EPS_PRICE
    assert abs(rn_mean - 1) < EPS_RATE
    return out


def rate_fixture(model, t, T, U, x):
    delta = U - T
    forward = math.expm1(math.log(model.bond(t, T, x) / model.bond(t, U, x))) / delta
    mq, cv = model.moments(t, T, x)
    mp, _ = model.payment_moments(t, T, U, x)
    mf, _ = model.payment_moments(t, T, T, x)
    b = model.b(delta)
    z = model.phi_int(T, U) - 0.5 * model.moments(T, U)[1][1, 1]

    def term(m):
        return math.expm1(z + b * m + 0.5 * b * b * cv[0, 0]) / delta

    # Overnight log accrual, from the same entire future Wiener trajectory.
    horizon = U - t
    fix_h = T - t

    def ki(s):
        return model.eta * (model.b(horizon - s) - (model.b(fix_h - s) if s < fix_h else 0))

    def kj_u(s):
        return model.eta * model.b(horizon - s)

    def kj_t(s):
        return model.eta * model.b(fix_h - s)

    def integral(fun, lower, upper):
        if upper == lower:
            return 0.0
        return quad(fun, lower, upper, epsabs=1e-16, epsrel=1e-13)[0]

    vi = integral(lambda s: ki(s) ** 2, 0, fix_h) + integral(lambda s: ki(s) ** 2, fix_h, horizon)
    ciu = integral(lambda s: ki(s) * kj_u(s), 0, fix_h) + integral(
        lambda s: ki(s) * kj_u(s), fix_h, horizon
    )
    cit = integral(lambda s: ki(s) * kj_t(s), 0, fix_h)
    mi = (model.b(horizon) - model.b(fix_h)) * x + model.phi_int(T, U)
    overnight_q = math.expm1(mi + 0.5 * vi) / delta
    overnight_p = math.expm1(mi - ciu + 0.5 * vi) / delta
    overnight_f = math.expm1(mi - cit + 0.5 * vi) / delta
    out = {
        "t": t,
        "fix_T": T,
        "pay_U": U,
        "delta": delta,
        "x_t": x,
        "eta": model.eta,
        "r0": model.r0,
        "forward": forward,
        "term_E_Q": term(mq[0]),
        "term_E_pay": term(mp[0]),
        "term_E_wrong_fix": term(mf[0]),
        "overnight_E_Q": overnight_q,
        "overnight_E_pay": overnight_p,
        "overnight_E_wrong_fix": overnight_f,
        "overnight_mean_integral_Q": mi,
        "overnight_var_integral": vi,
        "overnight_cov_payment_discount_integral": ciu,
        "overnight_cov_fix_discount_integral": cit,
        "term_FRA_PV": model.bond(t, U, x) * delta * (forward - term(mp[0])),
        "overnight_FRA_PV": model.bond(t, U, x) * delta * (forward - overnight_p),
    }
    assert abs(term(mp[0]) - forward) < EPS_RATE
    assert abs(overnight_p - forward) < EPS_RATE
    return out


def annuity_fixture(model, t, T, x, payments, deltas, mode="single", basis=0.01, strike=0.045):
    starts = [T, *list(payments[:-1])]

    def legs(time, state):
        p = [model.bond(time, u, state) for u in payments]
        prev = [model.bond(time, u, state) for u in starts]
        annuity = math.fsum(d * v for d, v in zip(deltas, p, strict=False))
        if mode == "single":
            floating = prev[0] - p[-1]
        elif mode == "additive":
            # Additive simple-rate deterministic basis matches the prepared design.
            spreads = [
                math.expm1((model.r0 + basis) * d) / d - math.expm1(model.r0 * d) / d
                for d in deltas
            ]
            floating = (
                prev[0]
                - p[-1]
                + math.fsum(d * s * v for d, s, v in zip(deltas, spreads, p, strict=False))
            )
        elif mode == "multiplicative":
            # Alternative deterministic zero-spread basis; distinct model contract.
            floating = math.fsum(
                math.exp(basis * d) * vprev - vpay
                for d, vprev, vpay in zip(deltas, prev, p, strict=False)
            )
        else:
            raise ValueError(mode)
        return annuity, floating

    at, vt = legs(t, x)
    target = vt / at
    weights = [d * model.bond(t, u, x) / at for d, u in zip(deltas, payments, strict=False)]
    means = [model.payment_moments(t, T, u, x)[0][0] for u in payments]
    mq, cv = model.moments(t, T, x)
    variance = cv[0, 0]

    def rate(y):
        return (lambda av: av[1] / av[0])(legs(T, y))

    # Payer payoff has one monotone threshold; split quadrature at exact root.
    kink = brentq(lambda y: rate(y) - strike, -1.0, 1.0)
    ea = math.fsum(
        w * gaussian_avg(rate, m, variance) for w, m in zip(weights, means, strict=False)
    )
    ea_option = at * math.fsum(
        w * gaussian_avg(lambda y: max(rate(y) - strike, 0), m, variance, kink)
        for w, m in zip(weights, means, strict=False)
    )
    eq = gaussian_avg(rate, mq[0], variance)
    et_mean = model.payment_moments(t, T, T, x)[0][0]
    et = gaussian_avg(rate, et_mean, variance)
    if variance == 0:

        def cond_discount(y):
            return math.exp(-mq[1])
    else:

        def cond_discount(y):
            return math.exp(
                -mq[1]
                - cv[0, 1] / variance * (y - mq[0])
                + 0.5 * max(cv[1, 1] - cv[0, 1] ** 2 / variance, 0.0)
            )

    eq_value = gaussian_avg(lambda y: cond_discount(y) * legs(T, y)[1], mq[0], variance)
    eq_option = gaussian_avg(
        lambda y: cond_discount(y) * max(legs(T, y)[1] - strike * legs(T, y)[0], 0),
        mq[0],
        variance,
        kink,
    )
    eq_rn = gaussian_avg(lambda y: cond_discount(y) * legs(T, y)[0] / at, mq[0], variance)
    out = {
        "t": t,
        "T": T,
        "x_t": x,
        "eta": model.eta,
        "r0": model.r0,
        "payments": payments,
        "deltas": deltas,
        "basis_mode": mode,
        "basis": 0 if mode == "single" else basis,
        "A_t": at,
        "V_t": vt,
        "swap_rate_t": target,
        "mixture_weights": weights,
        "mixture_means_x_T": means,
        "variance_x_T": variance,
        "mean_A_swap_rate": ea,
        "mean_Q_swap_rate": eq,
        "mean_T_swap_rate": et,
        "Q_discounted_V": eq_value,
        "raw_annuity_RN_mean": eq_rn,
        "strike": strike,
        "payer_Q_quad": eq_option,
        "payer_A_quad": ea_option,
    }
    assert abs(ea - target) < EPS_RATE
    assert abs(eq_value - vt) < EPS_PRICE
    assert abs(eq_rn - 1) < EPS_RATE
    assert abs(eq_option - ea_option) < EPS_PRICE
    return out


def stable_moment_checks():
    out = []
    for u in [0, 1e-16, 1e-12, 1e-8, 1e-4, 0.01, 0.1, 0.1001, 1, 4, 10, 100]:
        b, q, d, e = stable_dimensionless(u)
        k = kernel_dimensionless(u)
        error = max(
            abs(q - k["var_x"]), abs(b - k["cov_x_w"]), abs(d - k["cov_i_w"]), abs(e - k["var_i"])
        )
        resid = e - d * d
        # Noise factor L maps only 2 independent normals to (X,I,W).
        # Unit eta,h; preserves X+aI=etaW exactly by construction.
        L = np.array([[1 - u * d, -u * math.sqrt(resid)], [d, math.sqrt(resid)], [1, 0]])
        corr_cov = L @ L.T
        oracle = np.array(
            [
                [k["var_x"], k["cov_x_i"], k["cov_x_w"]],
                [k["cov_x_i"], k["var_i"], k["cov_i_w"]],
                [k["cov_x_w"], k["cov_i_w"], 1],
            ]
        )
        assert resid > 0
        assert error < 2e-12
        assert np.max(np.abs(corr_cov - oracle)) < 2e-12
        out.append(
            {
                "u_ah": u,
                "d": d,
                "e": e,
                "residual_e_minus_d2": resid,
                "kernel_abs_error": error,
                "factor_covariance_abs_error": float(np.max(np.abs(corr_cov - oracle))),
                "factor_rank": int(np.linalg.matrix_rank(L)),
                "direct_covariance_min_eigenvalue": float(np.linalg.eigvalsh(oracle)[0]),
            }
        )
    return out


def independent_mc(model, T=2.0, S=100.0, K=105.0, loading=0.25, n=262144):
    """Kernel-quad Cholesky of (X,W), not proposed stable (I,W) factor.

    Non-antithetic IID samples; Q and T use independent seeds, direct prices;
    raw RN diagnostic. SE is unbiased sample SD / sqrt(n). The independent
    oracle remains deterministic quadrature; this MC is a separate exercise.
    """
    mean, cv = model.moments(0, T)
    L = np.linalg.cholesky(cv[np.ix_([0, 2], [0, 2])])
    out = {"n_iid": n, "antithetic": False, "Q_seed": 290041, "T_seed": 290042}
    prices = {}
    for measure, seed in [("Q", 290041), ("T", 290042)]:
        rng = np.random.default_rng(seed)
        xw = rng.standard_normal((n, 2)) @ L.T
        x_noise, w = xw[:, 0], xw[:, 1]
        i_noise = (model.eta * w - x_noise) / model.a
        noise = np.column_stack((x_noise, i_noise, w))
        tilted, _ = model.payment_moments(0, T, T)
        values = noise + (mean if measure == "Q" else tilted)
        logS = math.log(S) + values[:, 1] - 0.5 * loading**2 * T + loading * values[:, 2]
        payoff = np.maximum(np.exp(logS) - K, 0)
        p = model.bond(0, T)
        price_samples = np.exp(-values[:, 1]) * payoff if measure == "Q" else p * payoff
        estimate = float(price_samples.mean())
        se = float(price_samples.std(ddof=1) / math.sqrt(n))
        ref = call_fixture(model, 0, T, 0, S, K, loading)["call_Q_quad"]
        prices[measure] = {
            "estimate": estimate,
            "SE_iid": se,
            "oracle": ref,
            "z_score": (estimate - ref) / se,
        }
        if measure == "Q":
            rn = np.exp(-values[:, 1]) / p
            out["raw_RN"] = {
                "mean": float(rn.mean()),
                "SE_iid": float(rn.std(ddof=1) / math.sqrt(n)),
            }
        assert abs(estimate - ref) <= 5 * se + EPS_PRICE
    out["prices"] = prices
    return out


def build():
    base = Model()
    out = {
        "schema": "m29-gaussian-reference-v1",
        "market_inputs": "synthetic",
        "production_imports": [],
        "tolerance_recommendation": {
            "price_abs": EPS_PRICE,
            "rate_abs": EPS_RATE,
            "moment_dimensionless_abs": 2e-12,
            "kernel_relative": EPS_MOMENT_REL,
            "kernel_absolute": EPS_MOMENT_ABS,
            "MC_max_SE": 5.0,
        },
        "stability": stable_moment_checks(),
        "joint": [],
        "stock": [],
        "rates": [],
        "annuity": [],
    }
    for a, eta, t, T, x, r in [
        (0.2, 0.02, 0, 2, 0, 0.04),
        (0.2, 0.02, 0.75, 1, -0.015, 0.04),
        (0.2, 0, 0.25, 1, 0.02, -0.01),
        (0.2, 0.02, 0, 1e-12, 0, -0.01),
        (1e-8, 0.02, 0, 2, 0, 0.04),
        (0.2, 0.02, 1, 1, -0.02, -0.01),
    ]:
        m = Model(a, eta, r)
        mean, cv = m.moments(t, T, x)
        out["joint"].append(
            {
                "a": a,
                "eta": eta,
                "t": t,
                "T": T,
                "x_t": x,
                "r0": r,
                "mean_X_I_W": mean.tolist(),
                "covariance_X_I_W": cv.tolist(),
                "bond": m.bond(t, T, x),
            }
        )
    for model, t, T, x in [
        (base, 0, 2, 0),
        (base, 0.25, 1, -0.015),
        (base, 0.75, 1, 0.02),
        (Model(eta=0), 0, 2, 0),
        (Model(r0=-0.01), 0.25, 1, -0.02),
        (base, 1, 1, -0.015),
    ]:
        for loading in [0.25, -0.25, 0]:
            out["stock"].append(call_fixture(model, t, T, x, 100, 105, loading))
    for model in [base, Model(eta=0), Model(r0=-0.01)]:
        for t, T, U, x in [
            (0, 1, 1.25, 0),
            (0, 1, 1.5, 0),
            (0, 2, 2.5, 0),
            (0.25, 1, 1.5, -0.015),
            (0.75, 1, 1.5, 0),
            (0.75, 1, 1.5, 0.02),
            (1, 1, 1.5, -0.01),
        ]:
            out["rates"].append(rate_fixture(model, t, T, U, x))
    for model, t, x, pay, delta in [
        (base, 0, 0, [1.5, 2, 2.5, 3], [0.5] * 4),
        (base, 0.25, -0.015, [1.5, 2, 2.5, 3], [0.5] * 4),
        (base, 0.75, 0.02, [1.5, 2, 2.5, 3], [0.5] * 4),
        (Model(eta=0), 0.25, 0.01, [1.5, 2], [0.5, 0.5]),
        (Model(r0=-0.01), 0.25, -0.02, [1.5, 2, 2.5, 3], [0.5] * 4),
        (base, 0.75, -0.01, [1.5], [0.5]),
    ]:
        for mode in ["single", "additive", "multiplicative"]:
            out["annuity"].append(annuity_fixture(model, t, 1, x, pay, delta, mode))
    out["MC"] = [independent_mc(base, loading=s) for s in [0.25, -0.25, 0]]
    out.update(
        section="28.4",
        synthetic=True,
        printed_pins=[],
        source_pages=[676, 677, 678, 679],
        source_requirements=[f"N{n:02d}" for n in range(1, 13)],
        units={
            "time": "years",
            "rate": "annualized decimal",
            "price": "nominal units",
            "annuity": "years times unit notional",
        },
        production_basis="additive simple-rate basis; multiplicative fixture is an independent contrasting model",
    )
    return out


PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-28-4/reference.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = (
        json.dumps(build(), sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
    )
    if args.check:
        if not OUT.is_file() or OUT.read_text() != payload:
            raise ValueError("independent numeraire reference stale or missing")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload)
    print(
        "PASS: §28.4 independent kernels, 6 joint /18 stock /21 rate /18 annuity fixtures and raw direct MC"
    )


if __name__ == "__main__":
    main()
