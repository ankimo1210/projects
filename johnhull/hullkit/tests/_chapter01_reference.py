"""Independent Ch1 cash-account references; no hullkit imports."""

import math
from decimal import Decimal


def build():
    """Compute all printed values and each plotted ordinate by separate cash legs."""
    cash = Decimal("1000000") * Decimal("1.223")
    carry = Decimal("60") * Decimal("1.05")
    values = {
        "1.3": dict(
            delivery=cash,
            gain_high=Decimal("1000000") * Decimal("1.3") - cash,
            loss_low=Decimal("1000000") * Decimal("1.2") - cash,
            unit_high=Decimal("1.3") - Decimal("1.223"),
            unit_low=Decimal("1.2") - Decimal("1.223"),
            fair=carry,
            carry_gain=Decimal("67") - carry,
            interest=carry - Decimal("60"),
            reverse_gain=carry - Decimal("58"),
        ),
        "1.5": dict(
            call_cost=Decimal("20.30") * 100,
            call_payoff=(Decimal(400) - 340) * 100,
            call_profit=(Decimal(400) - 340 - Decimal("20.30")) * 100,
            put_premium=Decimal("12.70") * 100,
            put_payment=(Decimal(290) - 250) * 100,
            put_loss=(Decimal(290) - 250 - Decimal("12.70")) * 100,
        ),
        "1.7": dict(
            import_fixed=Decimal("10000000") * Decimal("1.2225"),
            export_fixed=Decimal("30000000") * Decimal("1.222"),
            import_low=Decimal("10000000") * Decimal("1.2"),
            import_high=Decimal("10000000") * Decimal("1.3"),
            cost_contract=Decimal(100),
            cost_total=Decimal(1000),
            floor=Decimal(1000) * Decimal("27.5"),
            floor_after_cost=Decimal(1000) * (Decimal("27.5") - 1),
        ),
        "1.8": dict(
            spot_outlay=Decimal(250000) * Decimal("1.222"),
            margin=Decimal(4) * 5000,
            spot_high=Decimal(250000) * (Decimal("1.3") - Decimal("1.222")),
            future_high=Decimal(250000) * (Decimal("1.3") - Decimal("1.2223")),
            spot_low=Decimal(250000) * (Decimal("1.2") - Decimal("1.222")),
            future_low=Decimal(250000) * (Decimal("1.2") - Decimal("1.2223")),
            stock_high=Decimal(100) * (27 - 20),
            stock_low=Decimal(100) * (15 - 20),
            call_unit=Decimal(27) - Decimal("22.5"),
            call_payoff=Decimal(2000) * (Decimal(27) - Decimal("22.5")),
            call_high=Decimal(2000) * (Decimal(27) - Decimal("22.5") - 1),
            call_low=-Decimal(2000),
            ratio=Decimal(10),
        ),
        "1.9": dict(arbitrage=Decimal(100) * (Decimal(100) * Decimal("1.23") - 120)),
    }
    values = {sid: {k: float(v) for k, v in row.items()} for sid, row in values.items()}
    grid = {
        "intro_forward": [0, 1.2, 1.223, 1.3, 2],
        "intro_options": [0, 250, 290, 340, 400, 500],
        "intro_protection": [0, 20, 27.5, 28, 40],
        "intro_speculation": [0, 15, 20, 22.5, 27, 30],
    }
    formulas = {
        "intro_forward": {
            "long": lambda s: Decimal(1000000) * s - cash,
            "short": lambda s: cash - Decimal(1000000) * s,
        },
        "intro_options": {
            "long_call": lambda s: (s - 340 if s > 340 else Decimal(0)) * 100 - Decimal("2030"),
            "short_put": lambda s: Decimal("1270") - (290 - s if s < 290 else Decimal(0)) * 100,
        },
        "intro_protection": {
            "unhedged": lambda s: Decimal(1000) * s,
            "insured_after_cost": lambda s: (
                Decimal(1000) * s
                + (Decimal("27.5") - s if s < Decimal("27.5") else Decimal(0)) * 1000
                - Decimal(1000)
            ),
        },
        "intro_speculation": {
            "stock": lambda s: (s - 20) * 100,
            "call": lambda s: (
                (s - Decimal("22.5") if s > Decimal("22.5") else Decimal(0)) * 2000 - Decimal(2000)
            ),
        },
    }
    figures = {
        k: [
            dict(role=role, x=grid[k], y=[float(fn(Decimal(str(s)))) for s in grid[k]])
            for role, fn in rows.items()
        ]
        for k, rows in formulas.items()
    }
    return dict(
        status="PASS",
        chapter=1,
        printed_value_count=sum(map(len, values.values())),
        values=values,
        figures=figures,
    )


def compare(actual, reference):
    """Reject missing/extra keys, role changes and economically material errors."""
    if set(actual) != set(reference):
        raise ValueError("reference key coverage differs")
    largest = 0.0
    for key, expected in reference.items():
        value = actual[key]
        if isinstance(expected, dict):
            error = compare(value, expected)
        elif isinstance(expected, list):
            if len(value) != len(expected):
                raise ValueError("series shape differs")
            error = 0.0
            for x, y in zip(value, expected, strict=True):
                delta = compare(x, y) if isinstance(y, dict) else abs(float(x) - float(y))
                if not math.isfinite(delta):
                    raise ValueError("nonfinite displayed value")
                error = max(error, delta)
        elif isinstance(expected, str):
            if value != expected:
                raise ValueError("role differs")
            error = 0.0
        else:
            error = abs(float(value) - float(expected))
        if not math.isfinite(error) or error > 1e-7:
            raise ValueError("cash/series differs: " + key)
        largest = max(largest, error)
    return largest
