"""Independent §27.6 reference: barrier formulas, a PDE and forward lattice induction.

No hullkit imports. The continuous-monitoring value comes from Hull's §26.9
formulas and is cross-checked by a Crank–Nicolson PDE with the barrier as an
absorbing boundary. Tree prices are recomputed by forward (Kolmogorov)
induction of the surviving probability mass, rather than by backward
induction of option values, on lattices built from Hull's §27.6 rules.
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.linalg import solve_banded

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-27-6/reference.json"
PARAMETERS = {
    "spot": 100.0,
    "strike": 100.0,
    "barrier": 120.0,
    "rate": 0.05,
    "volatility": 0.30,
    "maturity": 1.0,
    "dividend_yield": 0.0,
}
DENSE_STEPS = list(range(20, 301))
DOUBLING_STEPS = [25 * 2**k for k in range(8)]
LATTICE_STEPS = 10
HAND_STEPS = 100
NEAR_STEPS = (100, 400)
NEAR_BARRIERS = [round(100.25 + 0.05 * i, 2) for i in range(116)]
NEAR_CASES = (102.0, 102.8)


def normal_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def up_and_out_call(spot, strike, barrier, rate, dividend_yield, volatility, maturity):
    """Hull GE §26.9 continuous up-and-out call: vanilla minus up-and-in (H > K)."""
    if barrier <= strike:
        return 0.0
    root = volatility * math.sqrt(maturity)
    lam = (rate - dividend_yield + volatility**2 / 2) / volatility**2
    d1 = (math.log(spot / strike) + (rate - dividend_yield + volatility**2 / 2) * maturity) / root
    growth, discount = math.exp(-dividend_yield * maturity), math.exp(-rate * maturity)
    vanilla = spot * growth * normal_cdf(d1) - strike * discount * normal_cdf(d1 - root)
    x1 = math.log(spot / barrier) / root + lam * root
    y1 = math.log(barrier / spot) / root + lam * root
    y = math.log(barrier**2 / (spot * strike)) / root + lam * root
    ratio = barrier / spot
    up_and_in = (
        spot * growth * normal_cdf(x1)
        - strike * discount * normal_cdf(x1 - root)
        - spot * growth * ratio ** (2 * lam) * (normal_cdf(-y) - normal_cdf(-y1))
        + strike
        * discount
        * ratio ** (2 * lam - 2)
        * (normal_cdf(-y + root) - normal_cdf(-y1 + root))
    )
    return vanilla - up_and_in


def crank_nicolson(p, intervals_to_barrier=400, time_steps=1000, span_below=1.5):
    """Up-and-out call PDE in log price, absorbing at the barrier, Rannacher start."""
    x_spot, x_barrier = math.log(p["spot"]), math.log(p["barrier"])
    h = (x_barrier - x_spot) / intervals_to_barrier
    below = round(span_below / h)
    x = x_spot + h * np.arange(-below, intervals_to_barrier + 1)
    values = np.maximum(np.exp(x) - p["strike"], 0.0)
    values[0] = values[-1] = 0.0
    drift = p["rate"] - p["dividend_yield"] - p["volatility"] ** 2 / 2
    diffusion = p["volatility"] ** 2 / (2 * h * h)
    lower, centre, upper = (
        diffusion - drift / (2 * h),
        -2 * diffusion - p["rate"],
        diffusion + drift / (2 * h),
    )
    size = len(x)

    def step(v, dt, theta):
        operator = np.zeros(size)
        operator[1:-1] = lower * v[:-2] + centre * v[1:-1] + upper * v[2:]
        rhs = v + (1 - theta) * dt * operator
        rhs[0] = rhs[-1] = 0.0
        bands = np.zeros((3, size))
        bands[1] = 1.0
        bands[1, 1:-1] = 1 - theta * dt * centre
        bands[0, 2:] = -theta * dt * upper
        bands[2, :-2] = -theta * dt * lower
        return solve_banded((1, 1), bands, rhs)

    dt = p["maturity"] / time_steps
    for _ in range(4):
        values = step(values, dt / 2, 1.0)
    for _ in range(time_steps - 2):
        values = step(values, dt, 0.5)
    return float(values[below])


def probabilities(log_spacing, dt, p):
    """Hull §27.6 moment-matching branch probabilities (up, middle, down)."""
    drift = (p["rate"] - p["dividend_yield"] - p["volatility"] ** 2 / 2) * dt
    spread = p["volatility"] ** 2 * dt / log_spacing**2
    return (
        drift / (2 * log_spacing) + spread / 2,
        1 - spread,
        -drift / (2 * log_spacing) + spread / 2,
    )


def forward_price(p, steps, log_spacing, branch, kill_level):
    """Discounted payoff under surviving lattice mass, levels >= kill_level absorbed."""
    p_up, p_mid, p_down = branch
    mass = np.zeros(2 * steps + 1)
    mass[steps] = 1.0
    levels = np.arange(-steps, steps + 1)
    dead = levels >= kill_level
    for _ in range(steps):
        moved = p_mid * mass
        moved[1:] += p_up * mass[:-1]
        moved[:-1] += p_down * mass[1:]
        moved[dead] = 0.0
        mass = moved
    payoff = np.maximum(p["spot"] * np.exp(levels * log_spacing) - p["strike"], 0.0)
    return math.exp(-p["rate"] * p["maturity"]) * float(mass @ payoff)


def outer_level(p, log_spacing):
    ratio = math.log(p["barrier"] / p["spot"]) / log_spacing
    return round(ratio) if abs(ratio - round(ratio)) <= 1e-9 else math.ceil(ratio)


def tree_prices(p, steps):
    """Simple CRR binomial, simple/inner/interpolated trinomial and nodes on the barrier."""
    dt = p["maturity"] / steps
    binomial_spacing = p["volatility"] * math.sqrt(dt)
    u = math.exp(binomial_spacing)
    q = (math.exp((p["rate"] - p["dividend_yield"]) * dt) - 1 / u) / (u - 1 / u)
    binomial = forward_price(
        p, steps, binomial_spacing, (q, 0.0, 1 - q), outer_level(p, binomial_spacing)
    )
    spacing = p["volatility"] * math.sqrt(3 * dt)
    branch = probabilities(spacing, dt, p)
    outer = outer_level(p, spacing)
    simple = forward_price(p, steps, spacing, branch, outer)
    inner = forward_price(p, steps, spacing, branch, outer - 1)
    outer_barrier = p["spot"] * math.exp(outer * spacing)
    inner_barrier = p["spot"] * math.exp((outer - 1) * spacing)
    weight = (p["barrier"] - inner_barrier) / (outer_barrier - inner_barrier)
    levels = int(math.log(p["barrier"] / p["spot"]) / spacing + 0.5)
    on_spacing = math.log(p["barrier"] / p["spot"]) / levels
    on_barrier = forward_price(p, steps, on_spacing, probabilities(on_spacing, dt, p), levels)
    return {
        "binomial_simple": binomial,
        "trinomial_simple": simple,
        "interpolated": inner + weight * (simple - inner),
        "on_barrier": on_barrier,
        "outer_barrier": outer_barrier,
    }


def lattice_example(p):
    """Figure 27.4/27.5 geometry: node prices for a small standard and barrier-aligned tree."""
    dt = p["maturity"] / LATTICE_STEPS
    spacing = p["volatility"] * math.sqrt(3 * dt)
    outer = outer_level(p, spacing)
    levels = int(math.log(p["barrier"] / p["spot"]) / spacing + 0.5)
    on_spacing = math.log(p["barrier"] / p["spot"]) / levels

    def nodes(log_spacing):
        return [
            [step * dt, p["spot"] * math.exp(level * log_spacing)]
            for step in range(LATTICE_STEPS + 1)
            for level in range(-step, step + 1)
        ]

    return {
        "steps": LATTICE_STEPS,
        "standard": {
            "log_spacing": spacing,
            "outer_barrier": p["spot"] * math.exp(outer * spacing),
            "inner_barrier": p["spot"] * math.exp((outer - 1) * spacing),
            "nodes": nodes(spacing),
        },
        "on_barrier": {"levels": levels, "log_spacing": on_spacing, "nodes": nodes(on_spacing)},
    }


def near_barrier(p):
    """Barrier-aligned spacing and probabilities as the barrier approaches the spot."""
    curves = {}
    for steps in NEAR_STEPS:
        dt = p["maturity"] / steps
        standard = p["volatility"] * math.sqrt(3 * dt)
        rows = {"barrier": [], "levels": [], "p_up": [], "p_middle": [], "p_down": []}
        for barrier in NEAR_BARRIERS:
            levels = int(math.log(barrier / p["spot"]) / standard + 0.5)
            if levels == 0:
                continue
            branch = probabilities(math.log(barrier / p["spot"]) / levels, dt, p)
            rows["barrier"].append(barrier)
            rows["levels"].append(levels)
            for key, value in zip(("p_up", "p_middle", "p_down"), branch, strict=True):
                rows[key].append(value)
        curves[str(steps)] = {
            "no_level_below": p["spot"] * math.exp(0.5 * standard),
            "negative_middle_below": p["spot"] * math.exp(p["volatility"] * math.sqrt(dt)),
            **rows,
        }
    cases = []
    for barrier in NEAR_CASES:
        for steps in NEAR_STEPS:
            dt = p["maturity"] / steps
            standard = p["volatility"] * math.sqrt(3 * dt)
            ratio = math.log(barrier / p["spot"]) / standard
            levels = int(ratio + 0.5)
            row = {
                "barrier": barrier,
                "steps": steps,
                "standard_steps_to_barrier": ratio,
                "levels": levels,
            }
            if levels:
                spacing = math.log(barrier / p["spot"]) / levels
                row["p_middle"] = probabilities(spacing, dt, p)[1]
            cases.append(row)
    return {"steps": list(NEAR_STEPS), "curves": curves, "cases": cases}


def build():
    """Return continuous values, dense and doubling tree prices, geometry and limits."""
    p = PARAMETERS
    analytic = up_and_out_call(
        p["spot"],
        p["strike"],
        p["barrier"],
        p["rate"],
        p["dividend_yield"],
        p["volatility"],
        p["maturity"],
    )
    pde = crank_nicolson(p)
    if abs(pde - analytic) >= 1e-5:
        raise ValueError("PDE and continuous barrier formula disagree")

    def outer_analytic(outer_barrier):
        return up_and_out_call(
            p["spot"],
            p["strike"],
            outer_barrier,
            p["rate"],
            p["dividend_yield"],
            p["volatility"],
            p["maturity"],
        )

    dense = {
        key: []
        for key in (
            "binomial_simple",
            "trinomial_simple",
            "interpolated",
            "on_barrier",
            "outer_barrier",
        )
    }
    for steps in DENSE_STEPS:
        for key, value in tree_prices(p, steps).items():
            dense[key].append(value)
    dense["outer_analytic"] = [outer_analytic(level) for level in dense["outer_barrier"]]
    errors = {
        "trinomial_simple": [],
        "barrier_position": [],
        "lattice": [],
        "interpolated": [],
        "on_barrier": [],
    }
    for steps in DOUBLING_STEPS:
        row = tree_prices(p, steps)
        moved = outer_analytic(row["outer_barrier"])
        errors["trinomial_simple"].append(row["trinomial_simple"] - analytic)
        errors["barrier_position"].append(moved - analytic)
        errors["lattice"].append(row["trinomial_simple"] - moved)
        errors["interpolated"].append(row["interpolated"] - analytic)
        errors["on_barrier"].append(row["on_barrier"] - analytic)
    tail = [math.log(abs(e)) for e in errors["on_barrier"][-4:]]
    order = -np.polyfit([math.log(n) for n in DOUBLING_STEPS[-4:]], tail, 1)[0]

    dt = p["maturity"] / HAND_STEPS
    standard = p["volatility"] * math.sqrt(3 * dt)
    ratio = math.log(p["barrier"] / p["spot"]) / standard
    levels = int(ratio + 0.5)
    spacing = math.log(p["barrier"] / p["spot"]) / levels
    branch = probabilities(spacing, dt, p)
    return {
        "section": "27.6",
        "source": "Hull 11e Global Edition pp.656–658, Figures 27.4–27.5; continuous formulas §26.9",
        "units": "stock, strike, barrier and option value in dollars; maturity in years; annual continuous rates and volatility",
        "parameters": p,
        "analytic": {
            "continuous": analytic,
            "pde": {
                "value": pde,
                "intervals_to_barrier": 400,
                "time_steps": 1000,
                "error": pde - analytic,
            },
        },
        "convergence": {"steps": DENSE_STEPS, **dense},
        "errors": {"steps": DOUBLING_STEPS, **errors, "on_barrier_order": order},
        "lattice_example": lattice_example(p),
        "hand_example": {
            "steps": HAND_STEPS,
            "standard_log_spacing": standard,
            "standard_steps_to_barrier": ratio,
            "levels": levels,
            "log_spacing": spacing,
            "p_up": branch[0],
            "p_middle": branch[1],
            "p_down": branch[2],
            "mean": (branch[0] - branch[2]) * spacing,
            "second_moment": (branch[0] + branch[2]) * spacing**2,
        },
        "near_barrier": near_barrier(p),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            raise SystemExit("FAIL: §27.6 independent reference is missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(content, encoding="utf-8")
    print("PASS: §27.6 continuous formula, PDE and forward lattice induction")


if __name__ == "__main__":
    main()
