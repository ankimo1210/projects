"""Independent §36.4 budgets, factor moments and caller-specified equity allocation."""

import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad


def _lesson():
    return importlib.import_module("hullkit._business_valuation_lesson")


def _model(**changes):
    return _lesson().BusinessModel(**changes)


def test_quarterly_budget_reduces_loss_carry_and_taxes_only_the_crossing_excess():
    """Catch taxing all profit on the carry-exhaustion quarter or granting loss rebates."""
    lesson = _lesson()
    model = _model(initial_cash=100, initial_loss_carry=30, annual_rate=0)
    cash, carry = 100.0, 30.0
    actual = []
    for revenue in [500, 2000, 3000, 500]:
        result = lesson.business_cash_step(cash, carry, revenue, 1, model)
        actual.append([float(result[k]) for k in ["cash", "loss_carry", "tax", "cashflow"]])
        cash, carry = result["cash"], result["loss_carry"]
    assert np.asarray(actual) == pytest.approx(
        np.array(
            [[55, 75, 0, -45], [100, 30, 0, 45], [178.75, 0, 26.25, 78.75], [133.75, 45, 0, -45]]
        ),
        abs=1e-12,
    )


def test_cash_interest_uses_quarter_units_and_is_subject_to_loss_carry():
    """Catch using annual interest for a quarter, or omitting taxable cash interest."""
    lesson = _lesson()
    model = _model()
    result = lesson.business_cash_step(100, 1, 1250, 1, model)
    gross = 100 * math.expm1(0.05 / 4)
    tax = 0.35 * (gross - 1)
    assert float(result["operating_cashflow"]) == pytest.approx(0, abs=1e-12)
    assert float(result["cash_interest"]) == pytest.approx(gross)
    assert float(result["tax"]) == pytest.approx(tax)
    assert float(result["loss_carry"]) == 0
    assert float(result["cash"]) == pytest.approx(100 + gross - tax)


def test_default_stops_future_cashflows_and_preserves_the_reported_deficit():
    """Catch resurrecting the enterprise after its cash trigger has fired."""
    lesson = _lesson()
    model = _model(annual_rate=0)
    failed = lesson.business_cash_step(12, 0, 0, 1, model)
    assert not bool(failed["alive"])
    assert float(failed["cash"]) == pytest.approx(-63)
    frozen = lesson.business_cash_step(
        failed["cash"], failed["loss_carry"], 5000, 1, model, alive=False
    )
    assert float(frozen["cash"]) == pytest.approx(-63)
    assert [float(frozen[k]) for k in ["cashflow", "tax", "cash_interest"]] == [0, 0, 0]
    assert float(frozen["loss_carry"]) == pytest.approx(75)


def test_zero_volatility_mc_matches_a_literal_four_quarter_cash_budget():
    """Catch tax/cash double counting or missing the terminal enterprise cash."""
    lesson = _lesson()
    model = _model(
        initial_revenue=2000,
        initial_growth=0,
        long_growth=0,
        revenue_volatility=0,
        long_revenue_volatility=0,
        growth_volatility=0,
        initial_cash=100,
        initial_loss_carry=30,
        annual_rate=0,
        horizon_quarters=4,
    )
    result = lesson.simulate_business_value(
        model,
        n_paths=4,
        seed=41,
        substeps_per_quarter=1,
        revenue_timing="start",
        terminal_multiple=2,
        terminal_profit_periods=1,
        record_paths=4,
    )
    assert result["history"]["cash"][:, 0] == pytest.approx(
        [100, 139.75, 169, 198.25, 227.5], abs=1e-11
    )
    assert result["history"]["tax"][1:, 0] == pytest.approx([5.25, 15.75, 15.75, 15.75])
    assert result["cashflow_total"] == pytest.approx(np.full(4, 127.5))
    assert result["terminal_distribution"] == pytest.approx(np.full(4, 317.5))
    assert result["value"] == pytest.approx(317.5)
    assert result["standard_error"] == 0
    assert result["bankruptcy_probability"] == 0


def test_revenue_accounting_time_is_explicit_and_changes_the_budget():
    """Catch silently replacing start-of-period revenue with the future endpoint."""
    lesson = _lesson()
    model = _model(
        initial_revenue=100,
        initial_growth=math.log(2),
        long_growth=math.log(2),
        revenue_volatility=0,
        long_revenue_volatility=0,
        growth_volatility=0,
        initial_cash=10,
        initial_loss_carry=0,
        annual_rate=0,
        tax_rate=0,
        cogs_fraction=0,
        other_variable_fraction=0,
        fixed_cost=0,
        horizon_quarters=2,
    )
    common = dict(
        n_paths=2,
        seed=12,
        substeps_per_quarter=1,
        terminal_multiple=0,
        terminal_profit_periods=1,
    )
    start = lesson.simulate_business_value(model, revenue_timing="start", **common)
    end = lesson.simulate_business_value(model, revenue_timing="end", **common)
    assert start["value"] == pytest.approx(310)
    assert end["value"] == pytest.approx(610)
    assert start["revenue"] == pytest.approx(np.full(2, 400))
    assert end["revenue"] == pytest.approx(np.full(2, 400))


@pytest.mark.parametrize("kappa", [0.0, 0.4])
def test_factor_step_matches_independent_lognormal_and_ou_moments(kappa):
    """Catch double sqrt(dt) in OU noise and the wrong revenue/growth Q drift."""
    lesson = _lesson()
    model = _model(
        growth_reversion=kappa,
        volatility_reversion=0,
        growth_volatility_reversion=0,
        growth_risk_price=0.3,
        revenue_risk_price=0.2,
    )
    draws = np.random.default_rng(47019).standard_normal((120000, 2))
    dt = 0.25
    result = lesson.business_factor_step(356, 0.11, 0, dt, draws[:, 0], draws[:, 1], model)
    log_return = np.log(result["revenue"] / 356)
    log_mean = (0.11 - 0.2 * 0.1 - 0.1**2 / 2) * dt
    log_var = 0.1**2 * dt
    assert log_return.mean() == pytest.approx(log_mean, abs=6 * math.sqrt(log_var / len(draws)))
    assert log_return.var(ddof=1) == pytest.approx(
        log_var, abs=6 * log_var * math.sqrt(2 / (len(draws) - 1))
    )
    expected_mu = (
        0.11 - 0.3 * 0.03 * dt
        if kappa == 0
        else 0.015
        + (0.11 - 0.015) * math.exp(-kappa * dt)
        - 0.3 * 0.03 * (1 - math.exp(-kappa * dt)) / kappa
    )
    variance = quad(lambda u: 0.03**2 * math.exp(-2 * kappa * (dt - u)), 0, dt)[0]
    assert result["growth"].mean() == pytest.approx(
        expected_mu, abs=6 * math.sqrt(variance / len(draws))
    )
    assert result["growth"].var(ddof=1) == pytest.approx(
        variance, abs=6 * variance * math.sqrt(2 / (len(draws) - 1))
    )
    expected_revenue = 356 * math.exp((0.11 - 0.2 * 0.1) * dt)
    revenue_sd = expected_revenue * math.sqrt(math.expm1(log_var))
    assert result["revenue"].mean() == pytest.approx(
        expected_revenue, abs=6 * revenue_sd / math.sqrt(len(draws))
    )


def test_source_volatility_decay_and_deterministic_growth_are_in_quarters():
    """Catch swapped sigma/eta targets or a missing growth mean-reversion term."""
    lesson = _lesson()
    model = _model()
    result = lesson.business_factor_step(356, 0.11, 10, 1, 0, 0, model)
    sigma = 0.05 + 0.05 * math.exp(-0.7)
    eta = 0.03 * math.exp(-0.7)
    assert result["revenue_volatility"] == pytest.approx(sigma)
    assert result["growth_volatility"] == pytest.approx(eta)
    assert float(result["growth"]) == pytest.approx(0.015 + 0.095 * math.exp(-0.07))
    assert float(result["revenue"]) == pytest.approx(
        356 * math.exp(0.11 - 0.01 * sigma - sigma**2 / 2)
    )


def test_deterministic_ou_revenue_refines_toward_an_independent_integrated_drift():
    """Catch freezing the initial growth for the whole business path."""
    lesson = _lesson()
    model = _model(
        initial_revenue=100,
        initial_growth=0.12,
        long_growth=0.03,
        growth_reversion=0.7,
        revenue_volatility=0,
        long_revenue_volatility=0,
        growth_volatility=0,
        initial_cash=1000,
        initial_loss_carry=0,
        annual_rate=0,
        tax_rate=0,
        cogs_fraction=0,
        other_variable_fraction=0,
        fixed_cost=0,
        horizon_quarters=4,
    )
    true_integral = quad(lambda t: 0.03 + 0.09 * math.exp(-0.7 * t), 0, 4)[0]
    true_revenue = 100 * math.exp(true_integral)
    errors = []
    for subdivisions in [1, 4, 16]:
        result = lesson.simulate_business_value(
            model,
            n_paths=2,
            seed=513,
            substeps_per_quarter=subdivisions,
            revenue_timing="end",
            terminal_multiple=0,
            terminal_profit_periods=1,
        )
        errors.append(abs(result["revenue"][0] - true_revenue))
    assert errors[1] < 0.3 * errors[0]
    assert errors[2] < 0.3 * errors[1]


def test_retained_cash_and_terminal_profit_are_discounted_once():
    """Catch quarterly annualization mistakes and double-discounting retained cash."""
    lesson = _lesson()
    cash_only = _model(
        initial_revenue=1250,
        initial_growth=0,
        long_growth=0,
        revenue_volatility=0,
        long_revenue_volatility=0,
        growth_volatility=0,
        initial_cash=100,
        initial_loss_carry=0,
        tax_rate=0,
        annual_rate=0.08,
        horizon_quarters=4,
    )
    common = dict(n_paths=2, seed=5, substeps_per_quarter=4, revenue_timing="start")
    cash = lesson.simulate_business_value(
        cash_only, terminal_multiple=0, terminal_profit_periods=1, **common
    )
    assert cash["value"] == pytest.approx(100, abs=1e-11)
    profit_model = _model(
        initial_revenue=2000,
        initial_growth=0,
        long_growth=0,
        revenue_volatility=0,
        long_revenue_volatility=0,
        growth_volatility=0,
        initial_cash=100,
        initial_loss_carry=0,
        tax_rate=0,
        annual_rate=0,
        horizon_quarters=1,
    )
    one = lesson.simulate_business_value(
        profit_model, terminal_multiple=10, terminal_profit_periods=1, **common
    )
    annual = lesson.simulate_business_value(
        profit_model, terminal_multiple=10, terminal_profit_periods=4, **common
    )
    assert annual["value"] - one["value"] == pytest.approx(3 * 10 * 45)


def test_seeded_joint_mc_matches_known_one_year_revenue_and_pair_standard_error():
    """Catch volatility time scaling, ignored seed, or counting antithetic paths twice."""
    lesson = _lesson()
    model = _model(
        initial_growth=0.07,
        long_growth=0.07,
        growth_volatility=0,
        revenue_volatility=0.2,
        long_revenue_volatility=0.2,
        revenue_risk_price=0.15,
        cogs_fraction=0,
        other_variable_fraction=0,
        fixed_cost=0,
        tax_rate=0,
        initial_cash=1000,
        annual_rate=0,
        horizon_quarters=4,
    )
    results = []
    for subdivisions in [1, 4]:
        result = lesson.simulate_business_value(
            model,
            n_paths=20000,
            seed=73017,
            substeps_per_quarter=subdivisions,
            revenue_timing="end",
            terminal_multiple=0,
            terminal_profit_periods=1,
        )
        half = len(result["revenue"]) // 2
        paired_revenue = (result["revenue"][:half] + result["revenue"][half:]) / 2
        expected = 356 * math.exp((0.07 - 0.15 * 0.2) * 4)
        revenue_se = paired_revenue.std(ddof=1) / math.sqrt(half)
        assert result["revenue"].mean() == pytest.approx(expected, abs=6 * revenue_se)
        paired_value = (result["path_pv"][:half] + result["path_pv"][half:]) / 2
        assert result["standard_error"] == pytest.approx(paired_value.std(ddof=1) / math.sqrt(half))
        assert result["independent_samples"] == half
        results.append(result)
    duplicate = lesson.simulate_business_value(
        model,
        n_paths=20000,
        seed=73017,
        substeps_per_quarter=1,
        revenue_timing="end",
        terminal_multiple=0,
        terminal_profit_periods=1,
    )
    assert np.array_equal(duplicate["path_pv"], results[0]["path_pv"])


def test_initial_or_subsequent_bankruptcy_has_no_terminal_value_or_later_cashflows():
    """Catch terminal EBITDA being paid on defaulted paths or default-time reset."""
    lesson = _lesson()
    bankrupt = _model(
        initial_cash=12,
        initial_revenue=0,
        initial_loss_carry=0,
        revenue_volatility=0,
        long_revenue_volatility=0,
        growth_volatility=0,
        annual_rate=0,
        horizon_quarters=3,
    )
    result = lesson.simulate_business_value(
        bankrupt,
        n_paths=2,
        seed=12,
        substeps_per_quarter=1,
        revenue_timing="start",
        terminal_multiple=10,
        terminal_profit_periods=4,
        record_paths=2,
    )
    assert result["value"] == 0
    assert result["default_time"] == pytest.approx([1, 1])
    assert result["bankruptcy_probability"] == 1
    assert result["history"]["cashflow"][2:] == pytest.approx(np.zeros((2, 2)))
    assert result["terminal_distribution"] == pytest.approx([0, 0])
    initial = _model(initial_cash=0, horizon_quarters=1)
    result0 = lesson.simulate_business_value(
        initial,
        n_paths=2,
        seed=12,
        substeps_per_quarter=1,
        revenue_timing="start",
        terminal_multiple=10,
        terminal_profit_periods=4,
    )
    assert result0["value"] == 0
    assert result0["default_time"] == pytest.approx([0, 0])


def test_capitalization_accounts_for_dated_exercise_receipts_debt_and_new_shares():
    """Catch missing conversion dilution, exercise proceeds, or debt-service discounting."""
    lesson = _lesson()
    events = [
        lesson.CapitalEvent(
            time_quarters=1,
            option_shares=10,
            option_strike=2,
            conversion_shares=5,
            after_tax_coupon=2,
            principal_payment=10,
        )
    ]
    result = lesson.capitalized_equity(
        [1000, 2000],
        [True, False],
        initial_shares=100,
        events=events,
        annual_rate=0.08,
        horizon_quarters=4,
    )
    expected_terminal = 1000 + 8 * math.exp(0.02 * 3)
    assert result["shares"] == pytest.approx(115)
    assert result["exercise_proceeds"] == pytest.approx(20)
    assert result["debt_service"] == pytest.approx(12)
    assert result["equity_terminal"] == pytest.approx([expected_terminal, 0])
    assert result["per_share_path_pv"] == pytest.approx(
        [expected_terminal * math.exp(-0.08) / 115, 0]
    )
    with pytest.raises(ValueError, match="horizon"):
        lesson.capitalized_equity(
            [1000],
            [True],
            initial_shares=100,
            events=[lesson.CapitalEvent(time_quarters=5)],
            annual_rate=0,
            horizon_quarters=4,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"revenue_volatility": -0.1},
        {"growth_reversion": -0.1},
        {"initial_loss_carry": -1},
        {"tax_rate": 1.1},
        {"annual_rate": math.nan},
        {"horizon_quarters": 1.5},
    ],
)
def test_invalid_business_states_and_units_are_rejected(changes):
    """Catch nonfinite parameters or negative risk/stock states entering simulation."""
    with pytest.raises(ValueError):
        _model(**changes)


def test_invalid_simulation_controls_and_factor_shapes_are_rejected():
    lesson = _lesson()
    model = _model(horizon_quarters=1)
    common = dict(
        seed=1,
        substeps_per_quarter=1,
        revenue_timing="start",
        terminal_multiple=10,
        terminal_profit_periods=4,
    )
    with pytest.raises(ValueError, match="even"):
        lesson.simulate_business_value(model, n_paths=3, **common)
    with pytest.raises(ValueError, match="timing"):
        lesson.simulate_business_value(model, n_paths=4, **(common | {"revenue_timing": "future"}))
    with pytest.raises(ValueError):
        lesson.business_factor_step(356, 0.11, 0, 0, 0, 0, model)
    with pytest.raises(ValueError):
        lesson.business_factor_step([356, 400], 0.11, 0, 1, [0, 0, 0], 0, model)
