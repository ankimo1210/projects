"""Shared generated-code cells for the B5--B6 notebook builders."""

from __future__ import annotations

from nbkit import code


def setup_cell(notebook_id: int):
    """Return deterministic imports and RNG routing for one generated notebook."""
    return code(f"""
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

import quant_textbook as qt

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = {notebook_id}


def task_rng(task_id, *coordinates):
    entropy = [
        RANDOM_SEED,
        NOTEBOOK_ID,
        int(task_id),
        *(int(coordinate) for coordinate in coordinates),
    ]
    return np.random.default_rng(np.random.SeedSequence(entropy))
""")


def treasury_cell():
    """Load the bundled official snapshot and build the common prediction table."""
    return code("""
treasury = qt.load_treasury_snapshot()
rates = treasury.frame.copy()
forecast = qt.make_treasury_forecast_dataset(rates)

assert treasury.quality.accepted
assert np.all(forecast.target_dates > forecast.prediction_dates)
assert np.all(np.isfinite(forecast.features))
crosses_methodology_break = (
    (forecast.prediction_dates < qt.TREASURY_METHOD_BREAK.to_datetime64())
    & (forecast.target_dates >= qt.TREASURY_METHOD_BREAK.to_datetime64())
)
assert not np.any(crosses_methodology_break)

print("source:", treasury.metadata.source_name)
print("snapshot:", treasury.metadata.start_date, "to", treasury.metadata.end_date)
print("rows / forecast rows:", len(rates), len(forecast.regression_target))
print("methodology-crossing targets retained:", int(crosses_methodology_break.sum()))
print("snapshot sha256:", treasury.metadata.snapshot_sha256)
""")


__all__ = ["setup_cell", "treasury_cell"]
