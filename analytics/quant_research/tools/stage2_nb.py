"""Shared generated-code cells for the B5--B8 notebook builders."""

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


def treasury_curve_cell():
    """Load the common Treasury curve panel and preserve the B5 outer-test boundary."""
    return code("""
treasury = qt.load_treasury_snapshot()
rates = treasury.frame.copy()
forecast = qt.make_treasury_forecast_dataset(rates)
b5_split = qt.chronological_split(len(forecast.regression_target), gap=1)

maturity_years = np.array([0.25, 2.0, 5.0, 10.0, 30.0])
curve_yields = rates.loc[:, qt.DEFAULT_TENORS].to_numpy(dtype=float)
curve_dates = rates["date"].to_numpy(dtype="datetime64[ns]")
curve_changes_bp = np.diff(curve_yields, axis=0) * 100.0
change_dates = curve_dates[1:]

train_end_date = forecast.prediction_dates[b5_split.train.max()]
validation_end_date = forecast.prediction_dates[b5_split.validation.max()]
test_start_date = forecast.prediction_dates[b5_split.test.min()]
train_mask = curve_dates <= train_end_date
validation_mask = (curve_dates > train_end_date) & (curve_dates <= validation_end_date)
test_mask = curve_dates >= test_start_date

assert treasury.quality.accepted
assert train_end_date < validation_end_date < test_start_date
assert np.all(np.isfinite(curve_yields))
assert np.all(np.diff(curve_dates).astype("timedelta64[D]") > np.timedelta64(0, "D"))

print("source:", treasury.metadata.source_name)
print("snapshot:", treasury.metadata.start_date, "to", treasury.metadata.end_date)
print("curve rows / tenors:", curve_yields.shape)
print("B5 train / validation end:", train_end_date, validation_end_date)
print("locked outer-test start:", test_start_date)
print("snapshot sha256:", treasury.metadata.snapshot_sha256)
""")


__all__ = ["setup_cell", "treasury_cell", "treasury_curve_cell"]
