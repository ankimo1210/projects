"""Controlled synthetic quote-DML protocol, grouped inputs and offline experiment.

The default replay path never imports a learner or torch. Learning is an
explicit offline action; every market is calibrated once for its eight rows.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from hullkit import _quote_dml_teachers as teacher

HERE = Path(__file__).resolve().parent


def load_protocol(path=HERE / "protocol.json"):
    """Read the frozen schema, quote units, supported curve and fit design."""
    config = json.loads(Path(path).read_text())
    curve, training = config["curve"], config["training"]
    if (
        config["schema_version"] != 1
        or curve["quote_unit"] != "rate_decimal"
        or curve["interpolation"] != "zero_linear"
        or curve["quote_kinds"] != list(teacher.QUOTE_KINDS)
        or curve["quote_times"] != [list(times) for times in teacher.QUOTE_TIMES]
        or curve["pillar_times"] != [0.5, 1, 2, 3, 5]
        or len(training["modes"]) * len(training["sizes"]) * len(training["seeds"]) != 30
    ):
        raise ValueError("unsupported protocol schema, curve, units or fit design")
    return config


def make_dataset(protocol, split):
    """Draw disjoint market groups without silently replacing failed curves.

    Rate gradients are per annual decimal quote unit; rows are price payout
    one. Group IDs include the split, allowing market-cluster uncertainty.
    """
    split_id = {"train": 0, "validation": 1, "test": 2}[split]
    sampling, curve, contract = protocol["sampling"], protocol["curve"], protocol["contract"]
    markets, count = sampling["markets"][split], sampling["contracts_per_market"]
    rng = np.random.default_rng(np.random.SeedSequence([sampling["seed"], split_id]))
    n = markets * count
    data = {
        key: np.full(shape, np.nan)
        for key, shape in {
            "x_quote": (n, 7),
            "x_theta": (n, 7),
            "price": (n,),
            "g_quote": (n, 6),
            "g_theta": (n, 6),
            "A": (n, 5, 5),
            "a_quote": (n, 5),
            "discount": (n,),
            "integrated_rate": (n,),
            "rank": (n,),
            "amplification": (n,),
            "iterations": (n,),
            "scaled_residual": (n,),
        }.items()
    }
    data["market_id"] = np.repeat(split_id * 100000 + np.arange(markets), count)
    data["contract_id"] = np.tile(np.arange(count), markets)
    data["failure_reason"] = np.full(n, "", dtype="U512")
    data["calibration_count"] = np.array(markets)
    for index in range(markets):
        rows = slice(index * count, (index + 1) * count)
        q = np.asarray(curve["base_quotes"]) + rng.uniform(
            -curve["halfwidth"], curve["halfwidth"], 5
        )
        if split == "test":
            terms = np.asarray(sampling["test_contracts"], dtype=float)
        else:
            spot = rng.uniform(*contract["spot_bounds"], count)
            maturity = np.exp(rng.uniform(*np.log(contract["maturity_bounds"]), count))
            terms = np.column_stack([spot, maturity])
        data["x_quote"][rows] = np.column_stack([np.tile(q, (count, 1)), terms])
        try:
            market = teacher.prepare_market(q)
            calibration = market.calibration
            data["x_theta"][rows] = np.column_stack([np.tile(calibration.zeros, (count, 1)), terms])
            data["A"][rows] = market.dz_dq
            data["rank"][rows] = np.linalg.matrix_rank(calibration.jacobian)
            data["amplification"][rows] = calibration.amplification
            data["iterations"][rows] = calibration.iterations
            data["scaled_residual"][rows] = calibration.scaled_residual_norm
            for offset, (spot, maturity) in enumerate(terms):
                exact = teacher.analytic(
                    market, spot, maturity, strike=contract["strike"], sigma=contract["sigma"]
                )
                for key in (
                    "price",
                    "g_quote",
                    "g_theta",
                    "a_quote",
                    "discount",
                    "integrated_rate",
                ):
                    data[key][index * count + offset] = exact[key]
        except (ValueError, RuntimeError, np.linalg.LinAlgError) as error:
            data["failure_reason"][rows] = f"{type(error).__name__}: {error}"
    return data
