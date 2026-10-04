"""Independent pure math/conditional quadrature for Hull GE §28.6.

No hullkit imports. All markets are synthetic; the original contains no
printed price pins. This exact Ho-Lee experiment is not a flat-curve HW model.
"""

import math
from itertools import pairwise

from scipy.integrate import quad

CUT = 12.0
SAMPLES = 262144
MARKETS = (
    ("constant_rate", 0.04, 0.0, 0.25, 0.5, 2.0),
    ("stochastic_positive", 0.04, 0.03, 0.25, 0.75, 2.0),
    ("stochastic_negative", 0.04, 0.03, 0.25, -0.75, 2.0),
    ("stochastic_zero_stock_correlation", 0.04, 0.03, 0.25, 0.0, 2.0),
    ("negative_rates", -0.02, 0.03, 0.25, 0.5, 2.0),
    ("zero_convexity_covariance", 0.04, 0.03, 0.25, -2 * 0.03 * 2 / (3 * 0.25), 2.0),
    ("zero_spot_vol_stochastic_rate", 0.04, 0.03, 0.0, 0.0, 2.0),
)


def phi(z):
    return math.exp(-z * z / 2) / math.sqrt(2 * math.pi)


def cdf(z):
    return math.erfc(-z / math.sqrt(2)) / 2


def integrate(fun, kink=None):
    points = [-CUT, CUT] if kink is None or not -CUT < kink < CUT else [-CUT, kink, CUT]
    return math.fsum(
        (quad(fun, a, b, epsabs=2e-11, epsrel=2e-12, limit=250)[0] for a, b in pairwise(points))
    )


def tilted_tail(coefficient):
    return (
        math.exp(coefficient**2 / 2)
        * (
            math.erfc((CUT + coefficient) / math.sqrt(2))
            + math.erfc((CUT - coefficient) / math.sqrt(2))
        )
        / 2
    )


def closed(p, f, k, sigma, t, kind):
    w = sigma * math.sqrt(t)
    if w == 0:
        return p * max(f - k if kind == "call" else k - f, 0.0)
    if f == k:
        return p * f * math.erf(w / (2 * math.sqrt(2)))
    d1 = (math.log(f / k) + w * w / 2) / w
    d2 = d1 - w
    return p * (f * cdf(d1) - k * cdf(d2) if kind == "call" else k * cdf(-d2) - f * cdf(-d1))


def build():
    data = dict(
        schema=1,
        section="28.6",
        source_pages=[680, 681],
        source_equations=["28.26", "28.27", "28.28", "28.29"],
        source_requirements=[f"BF{i:02}" for i in range(1, 7)],
        source_printed_pins=[],
        synthetic=True,
        n_paths=SAMPLES,
        quadrature_cutoff=CUT,
        cases=[],
        external_forward=[],
        limits=[],
    )
    for name, r, eta, sigma, rho, t in MARKETS:
        spot = 100.0
        mj, vj = (r * t, eta**2 * t**3 / 3)
        vy = vj + sigma * sigma * t + rho * eta * sigma * t * t
        cov = vj + rho * eta * sigma * t * t / 2
        my = math.log(spot) + mj - sigma * sigma * t / 2
        p = math.exp(-mj + vj / 2)
        f, futures, sd = (spot / p, math.exp(my + vy / 2), math.sqrt(vy))
        residual = max(vj - cov * cov / vy, 0.0)
        stat = dict(
            discount=p,
            forward=f,
            futures=futures,
            forward_sigma=math.sqrt(vy / t),
            terminal_variance=vy,
            mean_integral=mj,
            variance_integral=vj,
            mean_log_spot_Q=my,
            mean_log_spot_T=my - cov,
            cov_integral_log_spot=cov,
        )
        moments = {
            "density_quad": integrate(
                lambda z, mj=mj, vj=vj: math.exp(-mj - math.sqrt(vj) * z) * phi(z)
            )
            / p,
            "discounted_spot_quad": integrate(
                lambda z, cov=cov, mj=mj, my=my, residual=residual, sd=sd: (
                    math.exp(my - mj + (sd - cov / sd) * z + residual / 2) * phi(z)
                )
            ),
            "forward_quad": integrate(
                lambda z, cov=cov, my=my, sd=sd: math.exp(my - cov + sd * z) * phi(z)
            ),
            "log_first_Q": integrate(lambda z, my=my, sd=sd: (my + sd * z) * phi(z)),
            "log_second_Q": integrate(lambda z, my=my, sd=sd: (my + sd * z) ** 2 * phi(z)),
            "log_first_T": integrate(lambda z, cov=cov, my=my, sd=sd: (my - cov + sd * z) * phi(z)),
            "log_second_T": integrate(
                lambda z, cov=cov, my=my, sd=sd: (my - cov + sd * z) ** 2 * phi(z)
            ),
            "integrated_forward_variance": quad(
                lambda u, eta=eta, rho=rho, sigma=sigma, t=t: (
                    sigma * sigma + 2 * rho * eta * sigma * (t - u) + eta * eta * (t - u) ** 2
                ),
                0.0,
                t,
            )[0],
        }
        row = dict(
            id=name,
            inputs=dict(
                spot=spot,
                rate=r,
                rate_volatility=eta,
                stock_volatility=sigma,
                correlation=rho,
                horizon=t,
            ),
            statistics=stat,
            moments=moments,
            seed=286310 + len(data["cases"]),
            prices=[],
        )
        for k in (70.0, 105.0, 140.0):
            price = {"strike": k, "parity": p * (f - k)}
            for kind in ("call", "put"):
                sign = 1 if kind == "call" else -1

                def payoff(y, sign=sign, k=k):
                    return max(sign * (math.exp(y) - k), 0.0)

                qk = (math.log(k) - my) / sd
                tk = (math.log(k) - my + cov) / sd
                qprice = integrate(
                    lambda z, cov=cov, mj=mj, my=my, payoff=payoff, residual=residual, sd=sd: (
                        math.exp(-mj - cov / sd * z + residual / 2) * payoff(my + sd * z) * phi(z)
                    ),
                    qk,
                )
                tprice = p * integrate(
                    lambda z, cov=cov, my=my, payoff=payoff, sd=sd: (
                        payoff(my - cov + sd * z) * phi(z)
                    ),
                    tk,
                )
                naive = p * integrate(
                    lambda z, my=my, payoff=payoff, sd=sd: payoff(my + sd * z) * phi(z), qk
                )
                qtail = (
                    math.exp(my - mj + residual / 2) * tilted_tail(sd - cov / sd)
                    if kind == "call"
                    else k * math.exp(-mj + residual / 2) * tilted_tail(-cov / sd)
                )
                ttail = (
                    p * math.exp(my - cov) * tilted_tail(sd)
                    if kind == "call"
                    else p * k * tilted_tail(0.0)
                )
                price[kind] = dict(
                    q_quad=qprice,
                    t_quad=tprice,
                    closed=closed(p, f, k, math.sqrt(vy / t), t, kind),
                    q_tail_bound=qtail,
                    t_tail_bound=ttail,
                    wrong_outer_discount_Q=naive,
                    wrong_futures=closed(p, futures, k, math.sqrt(vy / t), t, kind),
                    wrong_spot_vol=closed(p, f, k, sigma, t, kind),
                )
            row["prices"].append(price)
        data["cases"].append(row)
    for market_type, f, k, p, sigma, t in (
        ("investment", 98.0, 100.0, 0.93, 0.35, 0.5),
        ("consumption", 98.0, 100.0, 0.93, 0.35, 0.5),
        ("negative_rate_discount", 102.0, 100.0, 1.04, 0.2, 1.0),
    ):
        location, sd = (math.log(f) - sigma * sigma * t / 2, sigma * math.sqrt(t))
        kink = (math.log(k) - location) / sd
        data["external_forward"].append(
            dict(
                market_type=market_type,
                forward=f,
                strike=k,
                discount=p,
                volatility=sigma,
                horizon=t,
                call=p
                * integrate(
                    lambda z, k=k, location=location, sd=sd: (
                        max(math.exp(location + sd * z) - k, 0.0) * phi(z)
                    ),
                    kink,
                ),
                put=p
                * integrate(
                    lambda z, k=k, location=location, sd=sd: (
                        max(k - math.exp(location + sd * z), 0.0) * phi(z)
                    ),
                    kink,
                ),
            )
        )
    for t, sigma in ((0.0, 0.25), (1.0, 0.0), (1e-08, 0.25), (1.0, 1e-08)):
        for f, k in ((80.0, 100.0), (100.0, 100.0), (125.0, 100.0)):
            p = 1.0 if t == 0 else math.exp(-0.04 * t)
            data["limits"].append(
                dict(
                    discount=p,
                    forward=f,
                    strike=k,
                    volatility=sigma,
                    horizon=t,
                    call=closed(p, f, k, sigma, t, "call"),
                    put=closed(p, f, k, sigma, t, "put"),
                )
            )
    return data
