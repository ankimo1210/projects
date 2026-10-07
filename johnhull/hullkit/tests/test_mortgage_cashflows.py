"""§33.3 has tranche sizes, but no pool, prepayment or market-price inputs."""

import importlib
import math

import numpy as np
import pytest


def model():
    return importlib.import_module("hullkit._mortgage_cashflows")


def test_thirty_year_no_prepayment_amortization_against_closed_form():
    m = model()
    L = 800.0
    r = 0.06 / 12
    n = 360
    row = m.mortgage_cashflows(L, 0.06, np.full((1, n), 0.05))
    payment = L * r / (1 - (1 + r) ** -n)
    i = np.arange(n + 1)
    balance = L * (1 + r) ** i - payment * ((1 + r) ** i - 1) / r
    balance[-1] = 0
    assert row["balances"][0] == pytest.approx(balance, abs=2e-10)
    assert row["interest"][0] + row["principal"][0] == pytest.approx(np.full(n, payment), abs=2e-10)
    assert row["principal"].sum() == pytest.approx(L, abs=1e-11)
    value = m.mortgage_value(row, np.full((1, n), 0.05))
    q = math.exp(-0.05 / 12)
    assert value["pass_through"] == pytest.approx(payment * q * (1 - q**n) / (1 - q), abs=2e-10)


@pytest.mark.parametrize("tranches", [[400, 300, 100], [100, 200, 500]])
def test_original_eight_hundred_principal_two_sequential_cmo_allocations(tranches):
    m = model()
    principal = np.array([[100, 150, 300, 250.0]])
    row = m.sequential_cmo_principal(principal, tranches)
    assert row["cashflows"].sum(axis=2) == pytest.approx(principal, abs=1e-12)
    assert row["cashflows"].sum(axis=1)[0] == pytest.approx(tranches, abs=1e-12)
    assert row["balances"][0, -1] == pytest.approx([0, 0, 0], abs=1e-12)
    assert row["cashflows"][0, 0, 0] == pytest.approx(100)


def test_faster_prepayment_lowers_io_and_raises_po_under_fixed_curve():
    m = model()
    rates = np.full((1, 360), 0.05)
    slow = m.mortgage_cashflows(800, 0.06, rates)
    fast = m.mortgage_cashflows(800, 0.06, rates, prepayment=0.03)
    a = m.mortgage_value(slow, rates)
    b = m.mortgage_value(fast, rates)
    assert b["IO"] < a["IO"]
    assert b["PO"] > a["PO"]
    assert fast["principal"].sum() == pytest.approx(800, abs=1e-10)
    assert fast["balances"][0, -1] == pytest.approx(0, abs=1e-12)
    assert b["pass_through"] == pytest.approx(b["IO"] + b["PO"], abs=1e-12)


def test_history_adapted_prepayment_never_reads_future_rates():
    m = model()
    rates = np.full((2, 24), 0.04)
    rates[1, :12] = 0.02

    def prepay(month, balance, history):
        return np.where(history.mean(axis=1) < 0.03, 0.1, 0)

    a = m.mortgage_cashflows(100, 0.06, rates, prepayment=prepay)
    changed = rates.copy()
    changed[:, 12:] = 0.15
    b = m.mortgage_cashflows(100, 0.06, changed, prepayment=prepay)
    assert a["principal"][:, :12] == pytest.approx(b["principal"][:, :12], abs=1e-12)
    assert a["balances"][1, 12] < a["balances"][0, 12]


def test_fixed_cashflow_oas_inverse_and_gaussian_discount_mc_independent_expectation():
    m = model()
    n = 60
    samples = 8192
    rng = np.random.default_rng(3332026)
    rates = rng.normal(0.05, 0.01, (samples, n))
    row = m.mortgage_cashflows(100, 0.06, rates)
    spread = 0.003
    pv = m.mortgage_value(row, rates, spread)
    q = 0.06 / 12
    payment = 100 * q / (1 - (1 + q) ** -n)
    k = np.arange(1, n + 1)
    expected = payment * np.exp(-(0.05 + spread) * k / 12 + 0.5 * k * (0.01 / 12) ** 2).sum()
    assert abs(pv["pass_through"] - expected) < 5 * pv["standard_error"]
    solved = m.mortgage_oas(row, rates, pv["pass_through"])
    assert solved["spread"] == pytest.approx(spread, abs=1e-12)
    assert m.mortgage_value(row, rates, spread + 0.001)["pass_through"] < pv["pass_through"]


def test_zero_coupon_and_full_prepayment_boundary_servicing_and_domain():
    m = model()
    rates = np.zeros((1, 12))
    row = m.mortgage_cashflows(120, 0, rates, prepayment=1.0)
    assert row["principal"][0, 0] == pytest.approx(120)
    assert row["principal"][0, 1:] == pytest.approx(np.zeros(11))
    assert row["interest"].sum() == pytest.approx(0)
    serviced = m.mortgage_cashflows(100, 0.06, rates, servicing_rate=0.005)
    gross = m.mortgage_cashflows(100, 0.06, rates)
    assert np.all(serviced["interest"] <= gross["interest"])
    assert serviced["principal"] == pytest.approx(gross["principal"], abs=1e-12)
    with pytest.raises(ValueError):
        m.mortgage_cashflows(100, 0.06, rates, prepayment=1.1)
    with pytest.raises(ValueError):
        m.mortgage_oas(row, rates, 0)
