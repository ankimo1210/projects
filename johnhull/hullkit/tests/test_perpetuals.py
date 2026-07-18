"""Contract arithmetic, funding, and basis feedback for perpetuals."""

import numpy as np
import pytest
from hullkit import perpetuals


def test_linear_inverse_and_quanto_pnl_hand_checks():
    assert perpetuals.position_pnl("linear", 100.0, 110.0, 2.0) == pytest.approx(20.0)
    assert perpetuals.position_pnl("linear", 100.0, 110.0, 2.0, side="short") == pytest.approx(
        -20.0
    )
    assert perpetuals.position_pnl(
        "inverse", 10_000.0, 12_000.0, 100.0, contract_multiplier=1.0
    ) == pytest.approx(100.0 * (1 / 10_000 - 1 / 12_000))
    assert perpetuals.position_pnl(
        "quanto", 100.0, 110.0, 2.0, contract_multiplier=3.0, settlement_fx=0.5
    ) == pytest.approx(30.0)


def test_snapshot_keeps_index_mark_and_last_separate():
    snapshot = perpetuals.MarketSnapshot(100.0, 101.0, 99.0, timestamp=30.0, oracle_timestamp=20.0)
    assert snapshot.oracle_age == 10.0
    assert snapshot.mark_index_basis == pytest.approx(0.01)
    assert snapshot.last_index_dislocation == pytest.approx(-0.01)


def test_funding_clamp_cap_and_zero_sum_ledger():
    policy = perpetuals.FundingPolicy(
        clamp_lower=-0.0005,
        clamp_upper=0.0005,
        absolute_cap=0.005,
    )
    snapshot = perpetuals.MarketSnapshot(100.0, 102.0, 101.0)
    rate = perpetuals.funding_rate(snapshot, policy=policy)
    assert rate == pytest.approx(0.005)  # raw premium is capped
    ledger = perpetuals.matched_funding_ledger(1_000.0, 1_000.0, rate)
    assert ledger.long_cashflow == pytest.approx(-5.0)
    assert ledger.short_cashflow == pytest.approx(5.0)
    assert ledger.conservation_error == pytest.approx(0.0, abs=1e-15)

    # Isolate the premium clamp from the wider absolute cap.
    clamped = perpetuals.funding_rate(
        perpetuals.MarketSnapshot(100.0, 100.2, 100.0),
        policy=policy,
    )
    assert clamped == pytest.approx(0.0015)


def test_funding_settlement_interval_excludes_partial_periods():
    policy = perpetuals.FundingPolicy(interval_hours=8.0)
    assert perpetuals.completed_funding_intervals(7.999, policy=policy) == 0
    assert perpetuals.completed_funding_intervals(8.0, policy=policy) == 1
    assert perpetuals.completed_funding_intervals(24.0, policy=policy) == 3
    assert perpetuals.settled_funding_cashflow(
        1_000.0,
        0.001,
        side="long",
        elapsed_hours=24.0,
        policy=policy,
    ) == pytest.approx(-3.0)


def test_unmatched_funding_is_explicitly_balanced_by_venue():
    ledger = perpetuals.matched_funding_ledger(1_000.0, 800.0, 0.001)
    assert ledger.venue_residual == pytest.approx(0.2)
    assert ledger.conservation_error == pytest.approx(0.0, abs=1e-15)


def test_basis_feedback_is_deterministic_and_funding_reduces_basis():
    index = np.full(6, 100.0)
    path = perpetuals.simulate_basis_feedback(
        index,
        102.0,
        basis_reversion=0.25,
        funding_feedback=1.0,
        policy=perpetuals.FundingPolicy(absolute_cap=0.01),
    )
    again = perpetuals.simulate_basis_feedback(
        index,
        102.0,
        basis_reversion=0.25,
        funding_feedback=1.0,
        policy=perpetuals.FundingPolicy(absolute_cap=0.01),
    )
    np.testing.assert_allclose(path.mark_prices, again.mark_prices)
    assert abs(path.basis[-1]) < abs(path.basis[0])
    assert np.all(np.abs(path.funding_rates) <= 0.01)


def test_invalid_sign_conventions_raise():
    with pytest.raises(ValueError, match="side"):
        perpetuals.position_pnl("linear", 100.0, 101.0, side="buy")
    with pytest.raises(ValueError, match="non-negative"):
        perpetuals.position_pnl("linear", 100.0, 101.0, quantity=-1.0)
