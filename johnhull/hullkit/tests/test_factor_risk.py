"""Factor signs, annual excess returns and final-axis batches are contract boundaries."""

import importlib

import numpy as np
import pytest


def api():
    return importlib.import_module("hullkit.factor_risk")


def test_example_is_excess_return_and_rate_is_added_once():
    m = api()
    np.testing.assert_allclose(
        m.factor_contributions([0.2, -0.1, 0.4], [0.05, 0.1, 0.15]), [0.01, -0.01, 0.06]
    )
    assert m.factor_excess_return([0.2, -0.1, 0.4], [0.05, 0.1, 0.15]) == pytest.approx(0.06)
    assert m.factor_required_return(0.04, [0.2, -0.1, 0.4], [0.05, 0.1, 0.15]) == pytest.approx(
        0.10
    )
    assert isinstance(m.factor_excess_return([0.2], [0.3]), float)


def test_signed_loading_and_zero_price_preserve_lower_risk_premium():
    m = api()
    assert m.factor_excess_return([0.2, -0.1, 0.4, 0], [-0.05, 0.1, 0.15, 9]) == pytest.approx(0.04)
    assert m.factor_required_return(-0.02, [0, 0], [20, -30]) == pytest.approx(-0.02)
    assert m.factor_excess_return([1, 2], [0, 0]) == 0


def test_final_factor_axis_and_leading_batches_broadcast():
    m = api()
    lam = np.array([[0.2, -0.1, 0.4], [0, 0, 0]])
    s = np.array([[[0.05, 0.1, 0.15]], [[-0.05, 0.1, -0.15]]])
    np.testing.assert_allclose(m.factor_excess_return(lam, s), [[0.06, 0], [-0.08, 0]])
    np.testing.assert_allclose(
        m.factor_required_return([0.04, -0.02], lam, s), [[0.10, -0.02], [-0.04, -0.02]]
    )
    assert m.factor_contributions(lam, s).shape == (2, 2, 3)


@pytest.mark.parametrize(
    "lam,s",
    [
        (0.2, [0.1]),
        ([0.2], 0.1),
        ([], []),
        ([0.2], [0.1, 0.3]),
        ([[0.1, 0.2], [0.3, 0.4]], np.zeros((3, 2))),
    ],
)
@pytest.mark.parametrize(
    "name", ["factor_contributions", "factor_excess_return", "factor_required_return"]
)
def test_rejects_scalar_empty_mismatched_factor_or_batch_axes(name, lam, s):
    fn = getattr(api(), name)
    with pytest.raises(ValueError):
        fn(0.04, lam, s) if name == "factor_required_return" else fn(lam, s)


@pytest.mark.parametrize(
    "bad", [[np.nan], [np.inf], [1 + 0j], np.array([np.complex64(1j)], dtype=object), [10**400]]
)
@pytest.mark.parametrize("position", [0, 1])
def test_invalid_inputs_are_checked_before_empty_batch_broadcast(bad, position):
    args = [np.empty((0, 1)), [0.2]]
    args[position] = bad
    with pytest.raises(ValueError):
        api().factor_excess_return(*args)


def test_valid_empty_batch_and_real_object_arrays():
    m = api()
    assert m.factor_excess_return(np.empty((0, 2)), [0.1, 0.2]).shape == (0,)
    assert m.factor_required_return(0.04, np.empty((0, 2)), [0.1, 0.2]).shape == (0,)
    np.testing.assert_allclose(
        m.factor_contributions(np.array([0.2, -0.1], dtype=object), [0.1, 0.2]), [0.02, -0.02]
    )


@pytest.mark.parametrize("bad", [np.nan, complex(0.04), 10**400])
def test_invalid_rate_rejected_alongside_empty_batch(bad):
    with pytest.raises(ValueError):
        api().factor_required_return(bad, np.empty((0, 1)), [0.2])


def test_rejects_rate_shape_conflicting_with_reduced_batch():
    with pytest.raises(ValueError):
        api().factor_required_return([0.01, 0.02, 0.03], [[0.2, 0.1], [0.3, 0.2]], [0.1, 0.2])


def test_unrepresentable_product_sum_and_total_return_are_rejected():
    m = api()
    for fn, args in [
        (m.factor_contributions, ([1e308], [2])),
        (m.factor_excess_return, ([1, 1], [1e308, 1e308])),
        (m.factor_required_return, (1e308, [1], [1e308])),
    ]:
        with pytest.raises(ValueError):
            fn(*args)
