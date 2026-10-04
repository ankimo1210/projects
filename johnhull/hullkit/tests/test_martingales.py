"""Conditional ratio means preserve measure, sign and raw-input validity."""

import importlib

import numpy as np
import pytest


def api():
    return importlib.import_module("hullkit._martingales")


def test_signed_numeraire_cancels_ito_drift_but_wrong_measure_does_not():
    m = api()
    assert m.numeraire_drifts(0.04, 0.3, -0.2) == pytest.approx((-0.02, 0.08))
    assert m.ratio_drift(-0.02, 0.08, 0.3, -0.2) == pytest.approx(0, abs=1e-15)
    assert m.ratio_drift(0.04, 0.04, 0.3, -0.2) == pytest.approx(0.1)
    assert m.ratio_conditional_mean(0.7, 0.04, 0.04, 0.3, -0.2, 1.25) == pytest.approx(
        0.7932039171467784
    )


@pytest.mark.parametrize("sg", [-0.2, 0, 0.15, 0.3])
def test_conditional_values_at_multiple_observation_times_and_states(sg):
    m = api()
    mf, mg = m.numeraire_drifts(0.04, 0.3, sg)
    values = np.array([0.5, 1.25, 2])
    horizons = np.array([1.5, 1.2, 0.8])[:, None]
    assert m.ratio_conditional_mean(values, mf, mg, 0.3, sg, horizons) == pytest.approx(
        np.broadcast_to(values, (3, 3)), abs=1e-14
    )


def test_zero_horizon_and_identical_assets_keep_observed_ratio():
    m = api()
    assert m.ratio_conditional_mean(1.25, 0.12, -0.03, -0.2, 0.4, 0) == 1.25
    assert m.ratio_conditional_mean(1, 0.04, 0.04, 0.3, 0.3, 2) == 1


def test_batch_shapes_scalar_types_and_valid_empty_batches():
    m = api()
    assert isinstance(m.ratio_drift(0.04, 0.04, 0.3, 0.15), float)
    assert m.ratio_drift(np.array([0.04, 0.08])[:, None], 0.04, [0.3, -0.3], 0.15).shape == (2, 2)
    assert m.ratio_conditional_mean(np.empty((0, 3)), 0.04, 0.04, 0.3, 0.15, 1).shape == (0, 3)
    assert m.ratio_conditional_mean(
        np.array([0.7], dtype=object), 0.04, 0.04, 0.3, -0.2, 1.25
    ) == pytest.approx([0.7932039171467784])


@pytest.mark.parametrize("value,horizon", [(0, 1), (-1, 1), (1, -1)])
@pytest.mark.parametrize("empty", [False, True])
def test_bad_settings_rejected_before_empty_broadcast(value, horizon, empty):
    with pytest.raises(ValueError):
        api().ratio_conditional_mean(
            value, np.empty(0) if empty else 0.04, 0.04, 0.3, 0.15, horizon
        )


@pytest.mark.parametrize(
    "bad",
    [
        complex(0.3, 0),
        np.array([np.complex128(0.3)], dtype=object),
        float("nan"),
        float("inf"),
        10**500,
    ],
)
def test_nonreal_nonfinite_and_unrepresentable_inputs_rejected(bad):
    m = api()
    with pytest.raises(ValueError):
        m.ratio_drift(0.04, 0.04, bad, 0.15)
    with pytest.raises(ValueError):
        m.ratio_conditional_mean(1.25, 0.04, 0.04, 0.3, 0.15, bad)
    with pytest.raises(ValueError):
        m.numeraire_drifts(bad, 0.3, 0.15)


def test_incompatible_shapes_rejected():
    with pytest.raises(ValueError):
        api().ratio_drift([0.04, 0.05], [0.04, 0.05, 0.06], 0.3, 0.15)


@pytest.mark.parametrize(
    "call",
    [
        lambda m: m.ratio_drift(1e308, -1e308, 0.3, 0.15),
        lambda m: m.numeraire_drifts(0.04, 1e308, 1e308),
        lambda m: m.ratio_conditional_mean(1, 1e3, 0, 0, 0, 1),
        lambda m: m.ratio_conditional_mean(1, -1e3, 0, 0, 0, 1),
    ],
)
def test_overflow_and_loss_of_positive_mean_rejected(call):
    with pytest.raises(ValueError):
        call(api())


@pytest.mark.parametrize(
    "bad",
    [
        np.datetime64("2026-10-04"),
        np.datetime64("NaT"),
        np.timedelta64(365, "D"),
        np.timedelta64("NaT"),
        np.array(["2026-10-04"], dtype="datetime64[D]"),
        np.array([365], dtype="timedelta64[D]"),
        np.array([0.04, np.datetime64("NaT")], dtype=object),
        np.array([0.04, np.timedelta64(365, "D")], dtype=object),
        np.empty(0, dtype="datetime64[D]"),
        np.empty(0, dtype="timedelta64[D]"),
    ],
)
@pytest.mark.parametrize("entry", ["ratio_drift", "numeraire_drifts", "ratio_conditional_mean"])
@pytest.mark.parametrize("empty", [False, True])
def test_temporal_inputs_rejected_before_float_conversion(bad, entry, empty):
    m = api()
    other = np.empty((0, 1)) if empty else 0.04
    with pytest.raises(ValueError):
        if entry == "ratio_drift":
            m.ratio_drift(other, 0.04, bad, 0.15)
        elif entry == "numeraire_drifts":
            m.numeraire_drifts(bad, other, 0.15)
        else:
            m.ratio_conditional_mean(1, other, 0.04, 0.3, -0.2, bad)
