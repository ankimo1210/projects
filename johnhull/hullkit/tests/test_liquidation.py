"""Margin triggers, oracle shocks, and liquidation cash-flow conservation."""

import pytest
from hullkit import liquidation, perpetuals


def _long_account():
    return liquidation.MarginAccount(
        collateral=10.0,
        quantity=1.0,
        entry_price=100.0,
        initial_margin_rate=0.10,
        maintenance_margin_rate=0.05,
        liquidation_fee_rate=0.01,
    )


def test_bankruptcy_and_liquidation_prices_are_hand_checkable():
    account = _long_account()
    assert liquidation.bankruptcy_price(account) == pytest.approx(90.0)
    expected_liq = (100.0 - 10.0) / (1.0 - 0.05)
    assert liquidation.liquidation_price(account) == pytest.approx(expected_liq)
    assert liquidation.liquidation_triggered(account, expected_liq)
    assert not liquidation.liquidation_triggered(account, expected_liq + 1.0)


def test_short_liquidation_price_is_above_entry():
    account = liquidation.MarginAccount(10.0, -1.0, 100.0)
    assert liquidation.bankruptcy_price(account) == pytest.approx(110.0)
    assert liquidation.liquidation_price(account) > 100.0


def test_oracle_age_dislocation_latency_and_manipulation_are_separate():
    snapshot = perpetuals.MarketSnapshot(
        100.0,
        103.0,
        99.0,
        timestamp=20.0,
        oracle_timestamp=10.0,
    )
    risk = liquidation.assess_oracle_risk(
        snapshot,
        max_age=5.0,
        max_mark_dislocation=0.02,
    )
    assert risk.stale and risk.dislocated and not risk.usable
    shock = liquidation.oracle_shock(snapshot, latency_return=0.10, mark_manipulation=-0.02)
    assert shock.latent_index == pytest.approx(110.0)
    assert shock.shocked_mark == pytest.approx(100.94)
    assert shock.observed_dislocation != pytest.approx(shock.latent_dislocation)


def test_liquidation_waterfall_conserves_cash_and_tracks_fund_adl_social_loss():
    account = _long_account()
    # Equity at 80 is -10. Auction covers 1, insurance 4, ADL 3, social pool 2.
    ledger = liquidation.liquidation_waterfall(
        account,
        80.0,
        insurance_fund=4.0,
        auction_recovery=1.0,
        adl_capacity=3.0,
        social_loss_capacity=10.0,
    )
    assert ledger.account_equity == pytest.approx(-10.0)
    assert ledger.auction_recovery == pytest.approx(1.0)
    assert ledger.insurance_used == pytest.approx(4.0)
    assert ledger.adl_used == pytest.approx(3.0)
    assert ledger.socialized_loss == pytest.approx(2.0)
    assert ledger.insurance_fund_after == pytest.approx(0.0)
    assert ledger.uncovered_loss == pytest.approx(0.0)
    assert ledger.conservation_error == pytest.approx(0.0, abs=1e-12)
    assert ledger.solvent


def test_capacity_shortfall_remains_explicit_and_not_solvent():
    ledger = liquidation.liquidation_waterfall(
        _long_account(),
        80.0,
        insurance_fund=2.0,
        adl_capacity=1.0,
        social_loss_capacity=1.0,
    )
    assert ledger.uncovered_loss == pytest.approx(6.0)
    assert ledger.conservation_error == pytest.approx(0.0, abs=1e-12)
    assert not ledger.solvent


def test_auction_execution_reduces_adverse_impact_vs_forced_sale():
    forced = liquidation.execution_price(100.0, 1.0, method="forced_sale", impact_bps=200)
    auction = liquidation.execution_price(
        100.0,
        1.0,
        method="auction",
        impact_bps=200,
        auction_improvement=0.75,
    )
    assert forced == pytest.approx(98.0)
    assert auction == pytest.approx(99.5)
    assert liquidation.account_equity(_long_account(), auction) > liquidation.account_equity(
        _long_account(), forced
    )


def test_positive_equity_fee_is_credited_to_insurance_fund():
    ledger = liquidation.liquidation_waterfall(_long_account(), 100.0, insurance_fund=5.0)
    assert ledger.liquidation_fee == pytest.approx(1.0)
    assert ledger.trader_return == pytest.approx(9.0)
    assert ledger.insurance_fund_after == pytest.approx(6.0)
    assert ledger.conservation_error == pytest.approx(0.0, abs=1e-12)
