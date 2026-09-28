"""Independent §27.7 reference: two-asset formulas, a 1-D reduction and forward lattice induction.

No hullkit imports. European values come from Stulz's formula for a call on the
maximum of two assets, cross-checked by integrating the payoff conditional on
the first asset, and from Margrabe's exchange formula. The American exchange
option is reduced to one dimension (the second asset times an American call on
the price ratio) and solved by CRR and by Crank–Nicolson. Tree prices use node
prices built from Hull's printed factors: European prices by forward induction
of the probability mass. American tree prices use the same vectorised
roll-back as hullkit on those node prices; small in-the-money American trees,
where exercise binds at the first steps, are also priced by plain recursion.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy import integrate, stats
from scipy.linalg import solve_banded

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-27-7/reference.json"
PARAMETERS = {
    "spots": [100.0, 100.0],
    "strike": 100.0,
    "rate": 0.05,
    "dividend_yields": [0.06, 0.02],
    "volatilities": [0.20, 0.30],
    "correlation": 0.5,
    "maturity": 1.0,
}
METHODS = ("transform", "rubinstein", "adjusted")
DENSE_STEPS = list(range(20, 201))
DOUBLING_STEPS = [25 * 2**k for k in range(6)]
HAND_STEPS = 100
RHO_GRID = [round(-1.0 + 0.05 * i, 2) for i in range(41)]
RHO_STEPS = 100
ODD_STEPS = 101
PARITY_RHO = (-1.0, -0.6, 0.0, 0.5, 0.6)
PARITY_STEPS = (99, 100, 101)
RECURSION_STEPS = 6
RECURSION_DIVIDENDS = [0.25, 0.0]
RECURSION_SPOTS = ([120.0, 100.0], [100.0, 100.0])
AMERICAN_MAX_STEPS = (200, 400, 800)
CRR_STEPS = (20000, 40000)
CN_GRIDS = (4000, 8000)
CASE_STEPS = (50, 100)
CASES = (
    ("min_put", -0.5),
    ("max_call", 0.0),
    ("exchange", 0.9),
    ("max_call", -1.0),
    ("exchange", 1.0),
)


def _payoff(kind, strike):
    if kind == "max_call":
        return lambda s1, s2: np.maximum(np.maximum(s1, s2) - strike, 0.0)
    if kind == "min_put":
        return lambda s1, s2: np.maximum(strike - np.minimum(s1, s2), 0.0)
    return lambda s1, s2: np.maximum(s1 - s2, 0.0)


def _forward_value(forward, strike, volatility, maturity, call):
    """Undiscounted Black value; a zero conditional volatility leaves the intrinsic value."""
    if volatility * math.sqrt(maturity) < 1e-14:
        return max(forward - strike, 0.0) if call else max(strike - forward, 0.0)
    if strike <= 0.0:
        return forward if call else 0.0
    sd = volatility * math.sqrt(maturity)
    d1 = math.log(forward / strike) / sd + sd / 2
    if call:
        return forward * stats.norm.cdf(d1) - strike * stats.norm.cdf(d1 - sd)
    return strike * stats.norm.cdf(sd - d1) - forward * stats.norm.cdf(-d1)


def conditional_value(p, kind, rho):
    """Price by integrating over the first asset's normal shock (payoff split into Black terms)."""
    (s1, s2), k, r = p["spots"], p["strike"], p["rate"]
    (q1, q2), (v1, v2), t = p["dividend_yields"], p["volatilities"], p["maturity"]
    root = math.sqrt(t)
    residual = v2 * math.sqrt(max(1.0 - rho**2, 0.0))

    def integrand(z):
        first = s1 * math.exp((r - q1 - v1**2 / 2) * t + v1 * root * z)
        forward = s2 * math.exp(
            (r - q2 - v2**2 / 2) * t + v2 * root * rho * z + residual**2 * t / 2
        )
        if kind == "max_call":
            value = max(first - k, 0.0) + _forward_value(forward, max(first, k), residual, t, True)
        else:
            value = max(k - first, 0.0) + _forward_value(forward, min(first, k), residual, t, False)
        return value * stats.norm.pdf(z)

    kink = (math.log(k / s1) - (r - q1 - v1**2 / 2) * t) / (v1 * root)
    value, _ = integrate.quad(
        integrand, -12.0, 12.0, points=[kink], limit=500, epsabs=1e-13, epsrel=1e-13
    )
    return math.exp(-r * t) * value


def stulz_max_call(p):
    """Stulz (1982) call on the maximum of two assets with continuous yields."""
    (s1, s2), k, r = p["spots"], p["strike"], p["rate"]
    (q1, q2), (v1, v2), t = p["dividend_yields"], p["volatilities"], p["maturity"]
    rho = p["correlation"]
    v = math.sqrt(v1**2 + v2**2 - 2 * rho * v1 * v2)
    root = math.sqrt(t)
    d = (math.log(s1 / s2) + (q2 - q1 + v**2 / 2) * t) / (v * root)
    y1 = (math.log(s1 / k) + (r - q1 + v1**2 / 2) * t) / (v1 * root)
    y2 = (math.log(s2 / k) + (r - q2 + v2**2 / 2) * t) / (v2 * root)

    def bivariate(a, b, c):
        return stats.multivariate_normal(mean=[0.0, 0.0], cov=[[1.0, c], [c, 1.0]]).cdf([a, b])

    return (
        s1 * math.exp(-q1 * t) * bivariate(y1, d, (v1 - rho * v2) / v)
        + s2 * math.exp(-q2 * t) * bivariate(y2, -d + v * root, (v2 - rho * v1) / v)
        - k * math.exp(-r * t) * (1 - bivariate(-y1 + v1 * root, -y2 + v2 * root, rho))
    )


def margrabe(p, rho=None):
    """European option to receive S1 and deliver S2 (Hull eq. 26.5 with S1, S2)."""
    (s1, s2), (q1, q2), (v1, v2), t = (
        p["spots"],
        p["dividend_yields"],
        p["volatilities"],
        p["maturity"],
    )
    rho = p["correlation"] if rho is None else rho
    v = math.sqrt(v1**2 + v2**2 - 2 * rho * v1 * v2)
    if v * math.sqrt(t) < 1e-14:
        return max(s1 * math.exp(-q1 * t) - s2 * math.exp(-q2 * t), 0.0)
    d1 = (math.log(s1 / s2) + (q2 - q1 + v**2 / 2) * t) / (v * math.sqrt(t))
    return s1 * math.exp(-q1 * t) * stats.norm.cdf(d1) - s2 * math.exp(-q2 * t) * stats.norm.cdf(
        d1 - v * math.sqrt(t)
    )


def _ratio_problem(p):
    """American exchange = S2 x American call on X = S1/S2, strike 1, rate q2, yield q1."""
    (s1, s2), (q1, q2), (v1, v2), rho = (
        p["spots"],
        p["dividend_yields"],
        p["volatilities"],
        p["correlation"],
    )
    return s1 / s2, s2, q2, q1, math.sqrt(v1**2 + v2**2 - 2 * rho * v1 * v2)


def crr_ratio_call(p, steps):
    x0, scale, rate, dividend, v = _ratio_problem(p)
    dt = p["maturity"] / steps
    up = math.exp(v * math.sqrt(dt))
    prob = (math.exp((rate - dividend) * dt) - 1 / up) / (up - 1 / up)
    discount = math.exp(-rate * dt)
    values = np.maximum(x0 * up ** (2 * np.arange(steps + 1) - steps) - 1.0, 0.0)
    for step in range(steps - 1, -1, -1):
        values = discount * (prob * values[1:] + (1 - prob) * values[:-1])
        values = np.maximum(values, x0 * up ** (2 * np.arange(step + 1) - step) - 1.0)
    return scale * float(values[0])


def cn_ratio_call(p, grid, width=8.0):
    """Crank–Nicolson in ln X with Rannacher start and projection onto the exercise value."""
    x0, scale, rate, dividend, v = _ratio_problem(p)
    t = p["maturity"]
    centre = math.log(x0)
    y = np.linspace(centre - width * v * math.sqrt(t), centre + width * v * math.sqrt(t), grid + 1)
    h, dt = y[1] - y[0], t / grid
    exercise = np.maximum(np.exp(y) - 1.0, 0.0)
    drift = rate - dividend - v**2 / 2
    lower = v**2 / (2 * h * h) - drift / (2 * h)
    middle = -(v**2) / (h * h) - rate
    upper = v**2 / (2 * h * h) + drift / (2 * h)

    def advance(values, theta, tau):
        bands = np.zeros((3, grid - 1))
        bands[0, 1:] = -theta * tau * upper
        bands[1, :] = 1 - theta * tau * middle
        bands[2, :-1] = -theta * tau * lower
        rhs = values[1:-1] + (1 - theta) * tau * (
            lower * values[:-2] + middle * values[1:-1] + upper * values[2:]
        )
        rhs[-1] += theta * tau * upper * exercise[-1]
        new = np.empty_like(values)
        new[1:-1] = solve_banded((1, 1), bands, rhs)
        new[0], new[-1] = 0.0, exercise[-1]
        return np.maximum(new, exercise)

    values = exercise.copy()
    for step in range(grid):
        if step < 4:
            values = advance(advance(values, 1.0, dt / 2), 1.0, dt / 2)
        else:
            values = advance(values, 0.5, dt)
    return scale * float(values[grid // 2])


def american_exchange(p):
    crr = []
    for steps in CRR_STEPS:
        crr.append((crr_ratio_call(p, steps) + crr_ratio_call(p, steps + 1)) / 2)
    cn = [cn_ratio_call(p, grid) for grid in CN_GRIDS]
    crr_limit, cn_limit = 2 * crr[1] - crr[0], 2 * cn[1] - cn[0]
    if abs(crr_limit - cn_limit) >= 5e-5:
        raise ValueError("CRR and Crank–Nicolson American exchange references disagree")
    return {
        "crr_steps": list(CRR_STEPS),
        "crr_averaged": crr,
        "crr_extrapolated": crr_limit,
        "cn_grids": list(CN_GRIDS),
        "cn": cn,
        "cn_extrapolated": cn_limit,
        "value": (crr_limit + cn_limit) / 2,
        "half_spread": abs(crr_limit - cn_limit) / 2,
    }


def branches(p, method, dt, rho=None):
    """Hull's one-step factors: ((d ln S1, d ln S2) for uu, ud, du, dd, probabilities)."""
    rate, (q1, q2), (v1, v2) = p["rate"], p["dividend_yields"], p["volatilities"]
    rho = p["correlation"] if rho is None else rho
    m1, m2 = (rate - q1 - v1**2 / 2) * dt, (rate - q2 - v2**2 / 2) * dt
    root = math.sqrt(dt)
    ln_u1, ln_d1 = m1 + v1 * root, m1 - v1 * root
    if method == "rubinstein":
        orthogonal = math.sqrt(max(1.0 - rho**2, 0.0))
        ln_a = m2 + v2 * root * (rho + orthogonal)
        ln_b = m2 + v2 * root * (rho - orthogonal)
        ln_c = m2 - v2 * root * (rho - orthogonal)
        ln_d = m2 - v2 * root * (rho + orthogonal)
        moves = [(ln_u1, ln_a), (ln_u1, ln_b), (ln_d1, ln_c), (ln_d1, ln_d)]
        return moves, [0.25, 0.25, 0.25, 0.25]
    if method == "adjusted":
        ln_u2, ln_d2 = m2 + v2 * root, m2 - v2 * root
        moves = [(ln_u1, ln_u2), (ln_u1, ln_d2), (ln_d1, ln_u2), (ln_d1, ln_d2)]
        same, opposite = 0.25 * (1 + rho), 0.25 * (1 - rho)
        return moves, [same, opposite, opposite, same]
    drift_1, drift_2 = v2 * m1 + v1 * m2, v2 * m1 - v1 * m2
    var_1 = (v1 * v2) ** 2 * 2 * (1 + rho) * dt
    var_2 = (v1 * v2) ** 2 * 2 * (1 - rho) * dt
    h1, h2 = math.sqrt(var_1 + drift_1**2), math.sqrt(var_2 + drift_2**2)
    p1 = 0.5 + drift_1 / (2 * h1) if h1 > 0 else 0.5
    p2 = 0.5 + drift_2 / (2 * h2) if h2 > 0 else 0.5
    moves = [
        ((s1 * h1 + s2 * h2) / (2 * v2), (s1 * h1 - s2 * h2) / (2 * v1))
        for s1, s2 in ((1, 1), (1, -1), (-1, 1), (-1, -1))
    ]
    return moves, [p1 * p2, p1 * (1 - p2), (1 - p1) * p2, (1 - p1) * (1 - p2)]


def node_prices(p, method, steps, level, rho=None):
    """Stock prices at step ``level`` from Hull's printed relationships.

    ``a`` counts moves whose first sign is +, ``b`` those whose second sign is +.
    The transform tree maps (x1, x2) back with S1 = exp[(x1 + x2)/(2 sigma2)] and
    S2 = exp[(x1 - x2)/(2 sigma1)]; Rubinstein's S2 multiplies A, B, C, D along
    one path to the node; the adjusted tree uses the two alternative binomials.
    """
    moves, _ = branches(p, method, p["maturity"] / steps, rho)
    (s1, s2), (v1, v2) = p["spots"], p["volatilities"]
    a, b = np.meshgrid(np.arange(level + 1), np.arange(level + 1), indexing="ij")
    if method == "transform":
        h1 = v2 * moves[0][0] + v1 * moves[0][1]
        h2 = v2 * moves[0][0] - v1 * moves[0][1]
        x1 = v2 * math.log(s1) + v1 * math.log(s2) + (2 * a - level) * h1
        x2 = v2 * math.log(s1) - v1 * math.log(s2) + (2 * b - level) * h2
        return np.exp((x1 + x2) / (2 * v2)), np.exp((x1 - x2) / (2 * v1))
    ln_u1, ln_d1 = moves[0][0], moves[2][0]
    first = s1 * np.exp(a * ln_u1 + (level - a) * ln_d1)
    if method == "adjusted":
        ln_u2, ln_d2 = moves[0][1], moves[1][1]
        return first, s2 * np.exp(b * ln_u2 + (level - b) * ln_d2)
    n_a = np.minimum(a, b)
    n_b, n_c = a - n_a, b - n_a
    n_d = level - n_a - n_b - n_c
    ln_a, ln_b, ln_c, ln_d = (move[1] for move in moves)
    return first, s2 * np.exp(n_a * ln_a + n_b * ln_b + n_c * ln_c + n_d * ln_d)


def terminal_mass(p, method, steps, rho=None):
    """Forward (Kolmogorov) induction of the probability mass over (a, b)."""
    _, (p_uu, p_ud, p_du, p_dd) = branches(p, method, p["maturity"] / steps, rho)
    mass = np.ones((1, 1))
    for _ in range(steps):
        new = np.zeros((mass.shape[0] + 1, mass.shape[1] + 1))
        new[1:, 1:] += p_uu * mass
        new[1:, :-1] += p_ud * mass
        new[:-1, 1:] += p_du * mass
        new[:-1, :-1] += p_dd * mass
        mass = new
    return mass


def european(p, method, steps, kinds, rho=None):
    mass = terminal_mass(p, method, steps, rho)
    s1, s2 = node_prices(p, method, steps, steps, rho)
    discount = math.exp(-p["rate"] * p["maturity"])
    return {
        kind: discount * float(np.sum(mass * _payoff(kind, p["strike"])(s1, s2))) for kind in kinds
    }


def american(p, method, steps, kind, rho=None):
    """Vectorised backward induction with exercise at every node (hullkit's algorithm)."""
    _, (p_uu, p_ud, p_du, p_dd) = branches(p, method, p["maturity"] / steps, rho)
    payoff = _payoff(kind, p["strike"])
    discount = math.exp(-p["rate"] * p["maturity"] / steps)
    values = payoff(*node_prices(p, method, steps, steps, rho))
    for level in range(steps - 1, -1, -1):
        held = discount * (
            p_uu * values[1:, 1:]
            + p_ud * values[1:, :-1]
            + p_du * values[:-1, 1:]
            + p_dd * values[:-1, :-1]
        )
        values = np.maximum(held, payoff(*node_prices(p, method, steps, level, rho)))
    return float(values[0, 0])


def american_recursive(p, method, steps, kind):
    """Plain recursion over the four branches with exercise at every node."""
    moves, probs = branches(p, method, p["maturity"] / steps)
    payoff = _payoff(kind, p["strike"])
    discount = math.exp(-p["rate"] * p["maturity"] / steps)
    memo = {}

    def value(level, logs):
        key = (level, round(logs[0], 12), round(logs[1], 12))
        if key not in memo:
            exercise = float(payoff(np.array(math.exp(logs[0])), np.array(math.exp(logs[1]))))
            if level == steps:
                memo[key] = exercise
            else:
                held = discount * sum(
                    prob * value(level + 1, (logs[0] + d1, logs[1] + d2))
                    for (d1, d2), prob in zip(moves, probs, strict=True)
                )
                memo[key] = max(held, exercise)
        return memo[key]

    return value(0, (math.log(p["spots"][0]), math.log(p["spots"][1])))


def hand_example(p):
    dt = p["maturity"] / HAND_STEPS
    example = {"steps": HAND_STEPS, "dt": dt}
    for method in METHODS:
        moves, probs = branches(p, method, dt)
        mean = np.array(probs) @ np.array(moves)
        centred = np.array(moves) - mean
        covariance = (np.array(probs)[:, None] * centred).T @ centred
        example[method] = {
            "moves": [list(move) for move in moves],
            "probabilities": probs,
            "mean": mean.tolist(),
            "covariance": covariance.tolist(),
        }
    (v1, v2), rho = p["volatilities"], p["correlation"]
    example["target"] = {
        "mean": [
            (p["rate"] - q - v**2 / 2) * dt
            for q, v in zip(p["dividend_yields"], (v1, v2), strict=True)
        ],
        "covariance": [
            [v1**2 * dt, rho * v1 * v2 * dt],
            [rho * v1 * v2 * dt, v2**2 * dt],
        ],
    }
    return example


def build():
    """Return formulas, the 1-D American reference, tree prices, errors and sweeps."""
    p = PARAMETERS
    stulz = stulz_max_call(p)
    integrated = conditional_value(p, "max_call", p["correlation"])
    if abs(stulz - integrated) >= 1e-9:
        raise ValueError("Stulz and conditional integration disagree")
    exchange = margrabe(p)
    american_ref = american_exchange(p)

    dense = {method: [] for method in METHODS}
    dense_european = {method: [] for method in METHODS}
    for steps in DENSE_STEPS:
        for method in METHODS:
            dense[method].append(american(p, method, steps, "exchange"))
            dense_european[method].append(european(p, method, steps, ["exchange"])["exchange"])
    errors = {"steps": DOUBLING_STEPS}
    for method in METHODS:
        rows = [european(p, method, n, ["max_call", "exchange"]) for n in DOUBLING_STEPS]
        errors[f"{method}_max_call"] = [row["max_call"] - stulz for row in rows]
        errors[f"{method}_exchange"] = [row["exchange"] - exchange for row in rows]
    tail = [math.log(abs(e)) for e in errors["transform_max_call"][-4:]]
    order = -np.polyfit([math.log(n) for n in DOUBLING_STEPS[-4:]], tail, 1)[0]

    sweep = {"rho": RHO_GRID, "steps": RHO_STEPS, "odd_steps": ODD_STEPS, "reference": []}
    for method in METHODS:
        sweep[method] = []
        sweep[f"{method}_odd"] = []
    for rho in RHO_GRID:
        reference = conditional_value(p, "max_call", rho)
        sweep["reference"].append(reference)
        for method in METHODS:
            for steps, key in ((RHO_STEPS, method), (ODD_STEPS, f"{method}_odd")):
                value = european(p, method, steps, ["max_call"], rho)["max_call"]
                sweep[key].append(value - reference)
    parity = {"steps": list(PARITY_STEPS), "rho": list(PARITY_RHO), "transform": []}
    for rho in PARITY_RHO:
        reference = conditional_value(p, "max_call", rho)
        parity["transform"].append(
            [
                european(p, "transform", n, ["max_call"], rho)["max_call"] - reference
                for n in PARITY_STEPS
            ]
        )

    recursion = []
    for spots in RECURSION_SPOTS:
        q = dict(p, spots=spots, dividend_yields=RECURSION_DIVIDENDS)
        for method in METHODS:
            recursion.append(
                {
                    "spots": spots,
                    "dividend_yields": RECURSION_DIVIDENDS,
                    "method": method,
                    "steps": RECURSION_STEPS,
                    "recursive": american_recursive(q, method, RECURSION_STEPS, "exchange"),
                    "intrinsic": spots[0] - spots[1],
                }
            )

    max_american = {"steps": list(AMERICAN_MAX_STEPS)}
    for method in METHODS:
        amer = [american(p, method, n, "max_call") for n in AMERICAN_MAX_STEPS]
        euro = [european(p, method, n, ["max_call"])["max_call"] for n in AMERICAN_MAX_STEPS]
        max_american[method] = amer
        max_american[f"{method}_control_variate"] = [
            a - e + stulz for a, e in zip(amer, euro, strict=True)
        ]

    cases = []
    for kind, rho in CASES:
        reference = margrabe(p, rho) if kind == "exchange" else conditional_value(p, kind, rho)
        for method in METHODS:
            for steps in CASE_STEPS:
                cases.append(
                    {
                        "payoff": kind,
                        "correlation": rho,
                        "method": method,
                        "steps": steps,
                        "tree": european(p, method, steps, [kind], rho)[kind],
                        "reference": reference,
                    }
                )
    return {
        "section": "27.7",
        "source": "Hull 11e Global Edition pp.658–661, Tables 27.2–27.3",
        "units": "stock prices and option values in dollars; maturity in years; annual continuous rates, yields and volatilities",
        "parameters": p,
        "analytic": {
            "max_call": {
                "stulz": stulz,
                "integrated": integrated,
                "difference": stulz - integrated,
            },
            "exchange": exchange,
            "american_exchange": american_ref,
        },
        "hand_example": hand_example(p),
        "convergence": {"steps": DENSE_STEPS, "american": dense, "european": dense_european},
        "errors": {**errors, "transform_max_call_order": order},
        "correlation": sweep,
        "parity": parity,
        "american_max_call": max_american,
        "american_recursion": recursion,
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            raise SystemExit("FAIL: §27.7 independent reference is missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(content, encoding="utf-8")
    print("PASS: §27.7 Stulz, Margrabe, 1-D American reduction and forward lattice induction")


if __name__ == "__main__":
    main()
