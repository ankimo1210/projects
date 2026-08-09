import numpy as np
import pandas as pd
import pytest
from quant_textbook import (
    CouponBondUniverse,
    coupon_bond_cashflows,
    fit_bond_price_curve,
    leave_one_bond_out_price_rmse,
    make_synthetic_jgb_universe,
    nelson_siegel_basis,
    predict_bond_prices,
    price_coupon_bond,
    price_coupon_bond_from_yield,
    yield_to_maturity,
)


def test_coupon_bond_cashflows_are_explicit_and_complete() -> None:
    times, cashflows = coupon_bond_cashflows(2.0, 0.02, frequency=2, face_value=100.0)
    np.testing.assert_allclose(times, [0.5, 1.0, 1.5, 2.0])
    np.testing.assert_allclose(cashflows, [1.0, 1.0, 1.0, 101.0])


def test_coupon_bond_price_decreases_when_positive_zero_rates_increase() -> None:
    times, cashflows = coupon_bond_cashflows(10.0, 0.01)
    low_rate_price = price_coupon_bond(times, cashflows, lambda t: np.full_like(t, 0.005))
    high_rate_price = price_coupon_bond(times, cashflows, lambda t: np.full_like(t, 0.02))
    assert high_rate_price < low_rate_price


def test_yield_to_maturity_round_trip() -> None:
    times, cashflows = coupon_bond_cashflows(7.0, 0.015)
    expected_yield = 0.0123
    price = price_coupon_bond_from_yield(times, cashflows, expected_yield)
    solved = yield_to_maturity(price, times, cashflows)
    assert solved == pytest.approx(expected_yield, abs=1e-12)


def test_continuous_yield_round_trip_and_flat_curve_identity() -> None:
    times, cashflows = coupon_bond_cashflows(7.0, 0.015)
    expected_yield = 0.0123
    price = price_coupon_bond_from_yield(
        times,
        cashflows,
        expected_yield,
        compounding="continuous",
    )
    solved = yield_to_maturity(
        price,
        times,
        cashflows,
        compounding="continuous",
    )
    assert solved == pytest.approx(expected_yield, abs=1e-12)

    flat_rate = 0.05
    universe = make_synthetic_jgb_universe(
        maturities=(1.0, 2.0, 5.0),
        coupon_rates=(0.01, 0.02, 0.03),
        zero_curve=lambda t: np.full_like(t, flat_rate),
        seed=3,
    )
    np.testing.assert_allclose(universe.bonds["yield_to_maturity"], flat_rate, atol=1e-12)
    assert set(universe.bonds["yield_compounding"]) == {"continuous"}


def test_yield_solver_brackets_rates_near_the_periodic_lower_bound() -> None:
    times = np.array([1.0])
    cashflows = np.array([100.0])
    expected_yield = -1.9999
    price = price_coupon_bond_from_yield(times, cashflows, expected_yield, frequency=2)
    solved = yield_to_maturity(price, times, cashflows, frequency=2)
    assert solved == pytest.approx(expected_yield, abs=1e-11)


def test_synthetic_jgb_universe_is_deterministic_and_distinguishes_price_from_yield() -> None:
    first = make_synthetic_jgb_universe(seed=17)
    second = make_synthetic_jgb_universe(seed=17)
    pd.testing.assert_frame_equal(first.bonds, second.bonds)
    pd.testing.assert_frame_equal(first.cashflows, second.cashflows)
    assert first.bonds["dirty_price"].gt(0.0).all()
    assert len(first.cashflows) > len(first.bonds)
    difference = np.abs(first.bonds["yield_to_maturity"] - first.bonds["zero_rate_at_maturity"])
    assert (difference > 1e-6).any()


def test_universe_prices_each_bond_from_all_cashflows() -> None:
    def curve(t):
        return 0.002 + 0.001 * np.asarray(t)

    universe = make_synthetic_jgb_universe(
        maturities=(1.0, 2.0),
        coupon_rates=(0.01, 0.02),
        zero_curve=curve,
        seed=5,
    )
    for bond in universe.bonds.itertuples(index=False):
        rows = universe.cashflows.loc[universe.cashflows["bond_id"] == bond.bond_id]
        expected = price_coupon_bond(rows["payment_time"], rows["cashflow"], curve)
        assert bond.dirty_price == pytest.approx(expected)


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: coupon_bond_cashflows(1.1, 0.01, frequency=2), "regular coupon"),
        (lambda: coupon_bond_cashflows(1.0, -0.01), "non-negative"),
        (lambda: price_coupon_bond([1.0], [100.0], None), "callable"),
        (lambda: yield_to_maturity(0.0, [1.0], [100.0]), "strictly positive"),
        (
            lambda: make_synthetic_jgb_universe(maturities=(2.0, 1.0), coupon_rates=(0.01, 0.01)),
            "strictly increasing",
        ),
    ],
)
def test_bond_helpers_reject_invalid_inputs(call, message) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        call()


def _exact_nelson_siegel_universe(*, price_noise_std: float = 0.0, seed: int = 7):
    coefficients = np.array([0.012, -0.008, 0.018])
    decay = 0.37

    def zero_curve(maturities):
        return nelson_siegel_basis(maturities, decay) @ coefficients

    universe = make_synthetic_jgb_universe(
        maturities=(0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 30.0),
        coupon_rates=(0.002, 0.003, 0.004, 0.005, 0.007, 0.009, 0.011, 0.013, 0.014, 0.015),
        zero_curve=zero_curve,
        price_noise_std=price_noise_std,
        seed=seed,
    )
    return universe, coefficients, decay


def test_bond_price_curve_exactly_recovers_synthetic_nelson_siegel_curve() -> None:
    universe, expected_coefficients, decay = _exact_nelson_siegel_universe()

    model = fit_bond_price_curve(universe, decay=decay)

    np.testing.assert_allclose(model.coefficients, expected_coefficients, atol=1e-12)
    np.testing.assert_allclose(model.fitted_prices, universe.bonds["dirty_price"], atol=1e-11)
    np.testing.assert_allclose(predict_bond_prices(model, universe), model.fitted_prices)
    test_maturities = np.array([0.25, 4.0, 12.0, 25.0])
    np.testing.assert_allclose(
        model.predict_zero_rates(test_maturities),
        nelson_siegel_basis(test_maturities, decay) @ expected_coefficients,
        atol=1e-12,
    )
    assert model.basis == "nelson_siegel"
    assert model.decay == decay
    assert model.diagnostics.rank == 3
    assert np.isfinite(model.diagnostics.condition_number)
    assert model.diagnostics.rmse < 1e-11
    assert model.diagnostics.weighted_rmse < 1e-11
    assert model.diagnostics.success
    assert model.diagnostics.nfev > 0


def test_noisy_weighted_price_fit_and_leave_one_bond_out_score_are_deterministic() -> None:
    universe, _, decay = _exact_nelson_siegel_universe(price_noise_std=0.02, seed=13)
    weights = np.linspace(0.5, 2.0, len(universe.bonds))

    first = fit_bond_price_curve(universe, decay=decay, weights=weights, ridge=1e-8)
    second = fit_bond_price_curve(universe, decay=decay, weights=weights, ridge=1e-8)
    np.testing.assert_allclose(first.coefficients, second.coefficients, rtol=0.0, atol=0.0)
    expected_weighted_rmse = np.sqrt(
        np.average((first.observed_prices - first.fitted_prices) ** 2, weights=weights)
    )
    assert first.diagnostics.weighted_rmse == pytest.approx(expected_weighted_rmse)
    assert first.diagnostics.success

    first_loo = leave_one_bond_out_price_rmse(
        universe,
        decay=decay,
        weights=weights,
        ridge=1e-8,
    )
    second_loo = leave_one_bond_out_price_rmse(
        universe,
        decay=decay,
        weights=weights,
        ridge=1e-8,
    )
    assert first_loo == pytest.approx(second_loo, rel=0.0, abs=0.0)
    assert np.isfinite(first_loo)
    assert first_loo > 0.0


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (lambda universe: fit_bond_price_curve(universe, weights=[1.0]), "one value per bond"),
        (
            lambda universe: fit_bond_price_curve(
                universe, weights=np.r_[np.ones(len(universe.bonds) - 1), 0.0]
            ),
            "strictly positive",
        ),
        (lambda universe: fit_bond_price_curve(universe, ridge=-1.0), "non-negative"),
        (lambda universe: fit_bond_price_curve(universe, initial=[0.01]), "3 coefficients"),
        (lambda universe: fit_bond_price_curve(universe, max_nfev=0), "strictly positive"),
        (
            lambda universe: fit_bond_price_curve(
                CouponBondUniverse(
                    bonds=universe.bonds.drop(columns="dirty_price"),
                    cashflows=universe.cashflows,
                )
            ),
            "missing required columns",
        ),
        (
            lambda universe: fit_bond_price_curve(
                CouponBondUniverse(
                    bonds=universe.bonds,
                    cashflows=universe.cashflows.assign(bond_id="UNKNOWN"),
                )
            ),
            "unknown bond_id",
        ),
    ],
)
def test_bond_price_curve_rejects_invalid_inputs(operation, message) -> None:
    universe, _, _ = _exact_nelson_siegel_universe()
    with pytest.raises((TypeError, ValueError), match=message):
        operation(universe)
