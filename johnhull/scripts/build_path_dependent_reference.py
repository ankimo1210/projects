"""Independent §27.5 reference: printed Figure 27.3 and exact path enumeration.

No hullkit imports. The exact small trees enumerate the full, non-recombining
path history, rather than interpolating a representative average state.
"""

import argparse
import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs/validation/section-27-5/reference.json"
PARAMETERS = {
    "spot": 50.0,
    "strike": 50.0,
    "rate": 0.10,
    "volatility": 0.40,
    "maturity": 1.0,
    "dividend_yield": 0.0,
}
FIGURE_27_3 = {
    "X": {
        "stock": 50.00,
        "averages": [46.65, 49.04, 51.44, 53.83],
        "values": [5.642, 5.923, 6.206, 6.492],
    },
    "Y": {
        "stock": 54.68,
        "averages": [47.99, 51.12, 54.26, 57.39],
        "values": [7.575, 8.101, 8.635, 9.178],
    },
    "Z": {
        "stock": 45.72,
        "averages": [43.88, 46.75, 49.61, 52.48],
        "values": [3.430, 3.750, 4.079, 4.416],
    },
}
PRINTED = {
    "x_average": 51.44,
    "x_value": 6.206,
    "coarse": {"steps": 20, "average_points": 4, "european": 7.17, "american": 7.77},
    "fine": {"steps": 60, "average_points": 100, "european": 5.58, "american": 6.17},
    "continuous_average_analytic_approximation": 5.62,
}


def linear_interpolation(xs, ys, target):
    """Compute a printed node value with elementary linear interpolation."""
    for index in range(len(xs) - 1):
        if xs[index] <= target <= xs[index + 1]:
            weight = (target - xs[index]) / (xs[index + 1] - xs[index])
            return ys[index] * (1 - weight) + ys[index + 1] * weight
    raise ValueError("target outside representative average grid")


def exact_nonrecombining_tree(steps, *, american):
    """Price every distinct stock path directly, retaining its running sum."""
    p = PARAMETERS
    dt = p["maturity"] / steps
    up = math.exp(p["volatility"] * math.sqrt(dt))
    down = 1 / up
    probability = (math.exp((p["rate"] - p["dividend_yield"]) * dt) - down) / (up - down)
    discount = math.exp(-p["rate"] * dt)

    def visit(time, stock, running_sum):
        exercise = max(running_sum / (time + 1) - p["strike"], 0.0)
        if time == steps:
            return exercise
        up_stock, down_stock = stock * up, stock * down
        continuation = discount * (
            probability * visit(time + 1, up_stock, running_sum + up_stock)
            + (1 - probability) * visit(time + 1, down_stock, running_sum + down_stock)
        )
        return max(continuation, exercise) if american else continuation

    return visit(0, p["spot"], p["spot"])


def build():
    """Return Figure 27.3 interpolation, original price pins and exact trees."""
    x = PRINTED["x_average"]
    y_average = (5 * x + FIGURE_27_3["Y"]["stock"]) / 6
    z_average = (5 * x + FIGURE_27_3["Z"]["stock"]) / 6
    up_value = linear_interpolation(
        FIGURE_27_3["Y"]["averages"], FIGURE_27_3["Y"]["values"], y_average
    )
    down_value = linear_interpolation(
        FIGURE_27_3["Z"]["averages"], FIGURE_27_3["Z"]["values"], z_average
    )
    dt = PARAMETERS["maturity"] / PRINTED["coarse"]["steps"]
    u = math.exp(PARAMETERS["volatility"] * math.sqrt(dt))
    d = 1 / u
    up_probability = (math.exp(PARAMETERS["rate"] * dt) - d) / (u - d)
    x_value = math.exp(-PARAMETERS["rate"] * dt) * (
        up_probability * up_value + (1 - up_probability) * down_value
    )
    if (
        abs(y_average - 51.98) >= 0.005
        or abs(z_average - 50.49) >= 0.005
        or abs(up_value - 8.247) >= 0.002
        or abs(down_value - 4.182) >= 0.002
        or abs(x_value - PRINTED["x_value"]) >= 0.002
    ):
        raise ValueError("Figure 27.3 printed interpolation does not reconcile")
    exact = [
        {
            "steps": steps,
            "european": exact_nonrecombining_tree(steps, american=False),
            "american": exact_nonrecombining_tree(steps, american=True),
        }
        for steps in (4, 6, 8, 10, 12)
    ]
    return {
        "section": "27.5",
        "source": "Hull 11e Global Edition pp.653–656, Figure 27.3 and Example 26.3",
        "units": "stock, strike, average and option value in dollars; maturity in years; annual continuous rates and volatility",
        "parameters": PARAMETERS,
        "figure_27_3": FIGURE_27_3,
        "printed": PRINTED,
        "interpolation": {
            "up_average": y_average,
            "down_average": z_average,
            "up_value": up_value,
            "down_value": down_value,
            "up_probability": up_probability,
            "x_value": x_value,
        },
        "exact_small_trees": exact,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            raise SystemExit("FAIL: §27.5 independent reference is missing or stale")
    else:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(content, encoding="utf-8")
    print("PASS: §27.5 printed interpolation and exact non-recombining trees")


if __name__ == "__main__":
    main()
