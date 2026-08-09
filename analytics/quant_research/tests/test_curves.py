import numpy as np
import pytest
from quant_textbook import (
    fit_curve,
    leave_one_out_predictions,
    leave_one_out_rmse,
    nelson_siegel_basis,
    polynomial_basis,
    predict_curve,
    rmse,
    truncated_power_cubic_spline_basis,
    weighted_rmse,
)


def test_basis_functions_have_expected_columns_and_stable_zero_limit() -> None:
    maturities = np.array([0.0, 1.0, 3.0])
    polynomial = polynomial_basis(maturities, degree=2)
    np.testing.assert_allclose(polynomial[1], [1.0, 1.0, 1.0])
    spline = truncated_power_cubic_spline_basis(maturities, knots=(1.0, 2.0))
    assert spline.shape == (3, 6)
    assert spline[0, 4] == 0.0
    assert spline[-1, 4] == pytest.approx(8.0)
    nelson_siegel = nelson_siegel_basis(maturities, decay=0.4)
    np.testing.assert_allclose(nelson_siegel[0], [1.0, 1.0, 0.0])


def test_fixed_decay_nelson_siegel_curve_is_recovered_exactly() -> None:
    maturities = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0])
    coefficients = np.array([0.015, -0.012, 0.008])
    yields = nelson_siegel_basis(maturities, decay=0.35) @ coefficients
    model = fit_curve(maturities, yields, basis="nelson_siegel", decay=0.35)

    np.testing.assert_allclose(model.coefficients, coefficients, atol=1e-13)
    np.testing.assert_allclose(model.fitted_values, yields, atol=1e-13)
    assert model.basis == "nelson_siegel"
    assert model.decay == pytest.approx(0.35)
    assert model.diagnostics.rank == 3
    assert model.in_sample_rmse < 1e-13
    new_maturities = np.array([0.75, 4.0, 12.0])
    np.testing.assert_allclose(
        predict_curve(model, new_maturities),
        nelson_siegel_basis(new_maturities, 0.35) @ coefficients,
        atol=1e-13,
    )


def test_polynomial_and_spline_curve_alias_fit_training_data() -> None:
    maturities = np.linspace(0.5, 10.0, 12)
    polynomial_yields = 0.01 + 0.002 * maturities - 0.0001 * maturities**2
    polynomial = fit_curve(maturities, polynomial_yields, basis="polynomial", degree=2)
    np.testing.assert_allclose(polynomial.fitted_yields, polynomial_yields, atol=1e-13)

    spline_yields = polynomial_yields + 0.00003 * np.maximum(maturities - 4.0, 0.0) ** 3
    spline = fit_curve(maturities, spline_yields, basis="spline", knots=(4.0,))
    assert spline.basis == "cubic_spline"
    np.testing.assert_allclose(spline.fitted_yields, spline_yields, atol=1e-12)


def test_spline_leave_one_out_keeps_original_boundary_knots() -> None:
    maturities = np.array([0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0])
    yields = 0.01 + 0.0002 * np.sqrt(maturities)
    error = leave_one_out_rmse(
        maturities,
        yields,
        basis="spline",
        knots=(2.0, 5.0, 10.0, 20.0),
        ridge=1e-5,
    )
    assert np.isfinite(error)


def test_rmse_weighted_rmse_and_leave_one_out_are_consistent() -> None:
    actual = np.array([1.0, 2.0, 4.0])
    predicted = np.array([1.0, 1.0, 2.0])
    weights = np.array([1.0, 2.0, 3.0])
    assert rmse(actual, predicted) == pytest.approx(np.sqrt(5.0 / 3.0))
    assert weighted_rmse(actual, predicted, weights) == pytest.approx(np.sqrt(14.0 / 6.0))

    maturities = np.array([0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0])
    yields = nelson_siegel_basis(maturities, 0.4) @ np.array([0.01, -0.006, 0.003])
    predictions = leave_one_out_predictions(maturities, yields, basis="nelson_siegel", decay=0.4)
    np.testing.assert_allclose(predictions, yields, atol=1e-12)
    assert (
        leave_one_out_rmse(
            maturities, yields, basis="nelson_siegel", decay=0.4, weights=np.arange(1, 9)
        )
        < 1e-12
    )


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: polynomial_basis([1.0], -1), "non-negative"),
        (lambda: nelson_siegel_basis([1.0], 0.0), "strictly positive"),
        (lambda: fit_curve([1.0, 1.0], [0.01, 0.02]), "unique"),
        (lambda: weighted_rmse([1.0], [1.0], [0.0]), "at least one"),
        (lambda: leave_one_out_rmse([1.0, 2.0], [0.01, 0.02]), "at least three"),
        (
            lambda: leave_one_out_rmse(
                [1.0, 2.0, 3.0],
                [0.01, 0.02, 0.03],
                weights=[1.0, 0.0, 1.0],
            ),
            "strictly positive",
        ),
    ],
)
def test_curve_helpers_reject_invalid_inputs(call, message) -> None:
    with pytest.raises(ValueError, match=message):
        call()
