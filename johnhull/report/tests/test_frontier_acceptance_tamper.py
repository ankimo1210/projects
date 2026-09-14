"""Tampering contract for the frontier acceptance gate.

The gate is only worth its PASS if it recomputes from the committed arrays
instead of trusting stored scalars. Each case below alters one committed
array or metric of a released volume and asserts that exactly the named
check flips to FAIL. A tamper that leaves the gate green is a check that is
reading its own answer back (the 2026-09-14 audit found that zeroing vol 28's
``cds_bootstrap_hazard`` or ``cds_survival`` and vol 27's ``gpd_losses`` all
kept 17/17 and 14/14 PASS).
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

import numpy as np
import pytest

from johnhull.scripts.frontier_acceptance import evaluate_acceptance

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = json.loads((ROOT / "johnhull/release_manifest.json").read_text(encoding="utf-8"))


@cache
def _load(volume: int) -> tuple[dict, dict]:
    item = next(entry for entry in MANIFEST["volumes"] if entry["number"] == volume)
    folder = ROOT / "johnhull/volumes" / item["slug"]
    json_name = next(ref for ref in item["references"] if ref.endswith(".json"))
    npz_name = next(ref for ref in item["references"] if ref.endswith(".npz"))
    metrics = json.loads((folder / json_name).read_text(encoding="utf-8"))["metrics"]
    with np.load(folder / npz_name, allow_pickle=False) as stored:
        arrays = {name: stored[name].copy() for name in stored.files}
    return metrics, arrays


def _failed(volume: int, metrics: dict, arrays: dict) -> set[str]:
    record = evaluate_acceptance(volume, metrics, arrays)
    return {check["name"] for check in record["checks"] if not check["passed"]}


def _scale_array(name: str, factor: float):
    def tamper(metrics, arrays):
        arrays[name] = arrays[name] * factor

    return tamper


def _set_array_value(name: str, index, value: float):
    def tamper(metrics, arrays):
        arrays[name] = arrays[name].copy()
        arrays[name][index] = value

    return tamper


def _scale_metric(name: str, factor: float):
    def tamper(metrics, arrays):
        metrics[name] = metrics[name] * factor

    return tamper


def _flip_flag(name: str, index: int):
    def tamper(metrics, arrays):
        arrays[name] = arrays[name].copy()
        arrays[name][index] = 1.0 - arrays[name][index]

    return tamper


CASES = {
    23: [
        ("daily_rate", _scale_array("daily_rate", 1.001), "daily_compounding_handcheck"),
        (
            "discrete_accrual",
            _scale_array("discrete_accrual", 1.001),
            "daily_compounding_handcheck",
        ),
        (
            "convention_accumulation",
            _set_array_value("convention_accumulation", 0, 1.0),
            "daily_compounding_handcheck",
        ),
        ("continuous_accrual", _scale_array("continuous_accrual", 1.001), "continuous_limit"),
        (
            "bachelier_price",
            _scale_array("bachelier_price", 1.001),
            "bachelier_quadrature_handcheck",
        ),
        (
            "quadrature_price",
            _scale_array("quadrature_price", 1.001),
            "bachelier_quadrature_handcheck",
        ),
        (
            "bachelier_normal_vol",
            _scale_metric("bachelier_normal_vol", 1.01),
            "bachelier_quadrature_handcheck",
        ),
    ],
    24: [
        # The matched ledger nets to a zero venue leg and the underwater account
        # has zero fee/trader return and an exhausted insurance fund, so the
        # tampers below move the non-zero legs.
        (
            "funding_long_cashflow",
            _scale_array("funding_long_cashflow", 1.001),
            "funding_cap_interval",
        ),
        (
            "funding_settled_intervals",
            _set_array_value("funding_settled_intervals", -1, 9),
            "funding_cap_interval",
        ),
        (
            "liquidation_method_equity",
            _scale_array("liquidation_method_equity", 1.001),
            "liquidation_method_waterfalls",
        ),
        (
            "liquidation_method_socialized_loss",
            _scale_array("liquidation_method_socialized_loss", 1.001),
            "liquidation_method_waterfalls",
        ),
        (
            "liquidation_method_insurance_before",
            _scale_array("liquidation_method_insurance_before", 1.001),
            "insurance_identity",
        ),
        ("adl_notional", _scale_array("adl_notional", 1.001), "stress_waterfall"),
        ("rebalanced_value", _scale_array("rebalanced_value", 1.001), "amm_identity"),
        ("lvr", _scale_array("lvr", 1.001), "amm_identity"),
        ("fee_income", _scale_array("fee_income", 1.001), "amm_lvr_fee_variants"),
        ("fixed_fee_net_lvr", _scale_array("fixed_fee_net_lvr", 1.001), "amm_lvr_fee_variants"),
        (
            "dynamic_fee_compensation",
            _scale_metric("dynamic_fee_compensation", 1.001),
            "amm_lvr_fee_variants",
        ),
    ],
    25: [
        (
            "weather_premium",
            _set_array_value("weather_premium", slice(None), 1.0),
            "market_completeness",
        ),
        (
            "carbon_black76_price",
            _scale_array("carbon_black76_price", 1.001),
            "carbon_model_ladder",
        ),
        ("carbon_gbm_price", _scale_array("carbon_gbm_price", 1.1), "carbon_model_ladder"),
        (
            "carbon_black76_volatility",
            _scale_metric("carbon_black76_volatility", 1.01),
            "carbon_model_ladder",
        ),
        ("ppa_fixed", _scale_array("ppa_fixed", 1.001), "ppa_risk_decomposition"),
        (
            "hedge_ratio_residual",
            _scale_array("hedge_ratio_residual", 1.001),
            "ppa_risk_decomposition",
        ),
        (
            "ppa_merchant_cash_flow_samples",
            _scale_array("ppa_merchant_cash_flow_samples", 1.001),
            "ppa_risk_decomposition",
        ),
        (
            "ppa_hedged_cash_flow_samples",
            _scale_array("ppa_hedged_cash_flow_samples", 1.001),
            "ppa_cashflow_risk",
        ),
        ("cvar95", _scale_array("cvar95", 1.001), "ppa_cashflow_risk"),
        ("hedge_residual", _scale_array("hedge_residual", 1.001), "ppa_cashflow_risk"),
    ],
    27: [
        (
            "kupiec_size_reject_flags",
            _flip_flag("kupiec_size_reject_flags", 0),
            "kupiec_size_flags_match_recomputation",
        ),
        ("garch_returns", _scale_array("garch_returns", 1.001), "fhs_coverage_improvement"),
        # FHS rescales z = r/sigma by sigma_t, so a uniform sigma scale cancels;
        # move a single day's sigma instead.
        (
            "conditional_sigma",
            _set_array_value("conditional_sigma", -1, 0.05),
            "fhs_coverage_improvement",
        ),
        ("hs_var_forecast", _scale_array("hs_var_forecast", 1.001), "fhs_coverage_improvement"),
        ("gpd_losses", _scale_array("gpd_losses", 1.01), "gpd_parameter_recovery"),
        ("gpd_beta_hat", _scale_metric("gpd_beta_hat", 1.02), "gpd_parameter_recovery"),
        ("evt_var", _scale_metric("evt_var", 1.001), "evt_var_es_identity"),
        ("evt_var_ladder", _scale_array("evt_var_ladder", 1.001), "evt_var_es_identity"),
        (
            "alloc_component_var",
            _scale_array("alloc_component_var", 1.001),
            "euler_additivity_normal",
        ),
        ("alloc_normal_var", _scale_metric("alloc_normal_var", 1.001), "euler_additivity_normal"),
        ("alloc_vols", _scale_array("alloc_vols", 1.001), "euler_additivity_normal"),
        ("book_delta", _scale_array("book_delta", 1.001), "cross_asset_factor_mapping"),
        (
            "position_full_pnl",
            _scale_array("position_full_pnl", 1.001),
            "cross_asset_factor_mapping",
        ),
        ("es_components", _scale_array("es_components", 1.001), "euler_es_additivity_sim"),
    ],
    28: [
        ("cds_survival", _scale_array("cds_survival", 0.999), "cds_par_spread_hull_pin"),
        ("cds_payoff_pv", _scale_array("cds_payoff_pv", 1.001), "cds_par_spread_hull_pin"),
        (
            "cds_bootstrap_hazard",
            _scale_array("cds_bootstrap_hazard", 1.01),
            "cds_bootstrap_round_trip",
        ),
        (
            "fixed_coupon_duration",
            _scale_metric("fixed_coupon_duration", 1.001),
            "fixed_coupon_price_identity",
        ),
        (
            "fixed_coupon_hazard",
            _scale_metric("fixed_coupon_hazard", 1.01),
            "fixed_coupon_price_identity",
        ),
        ("option_curve_hazard", _scale_array("option_curve_hazard", 1.01), "cds_option_parity"),
        ("payer_value", _scale_array("payer_value", 1.001), "cds_option_parity"),
        (
            "capital_structure_expected_loss",
            _scale_array("capital_structure_expected_loss", 1.001),
            "capital_structure_loss_conservation",
        ),
        (
            "portfolio_expected_loss",
            _scale_metric("portfolio_expected_loss", 1.001),
            "capital_structure_loss_conservation",
        ),
        (
            "kth_conditional_cumulative_prob",
            _scale_array("kth_conditional_cumulative_prob", 1.001),
            "kth_to_default_hull_pin_and_ordering",
        ),
        ("kth_rho", _scale_metric("kth_rho", 1.05), "kth_to_default_hull_pin_and_ordering"),
        (
            "base_correlation",
            _scale_array("base_correlation", 1.01),
            "base_correlation_curve_shape",
        ),
        ("el_curve_value", _scale_array("el_curve_value", 1.001), "base_correlation_curve_shape"),
        (
            "tranche_expected_loss",
            _scale_array("tranche_expected_loss", 1.001),
            "base_correlation_curve_shape",
        ),
        (
            "gaussian_mezz_spread",
            _scale_metric("gaussian_mezz_spread", 1.001),
            "double_t_gaussian_limit",
        ),
        (
            "cva_default_prob",
            _scale_array("cva_default_prob", 1.001),
            "netting_collateral_and_cva_special_case",
        ),
        (
            "cva_hazard",
            _scale_metric("cva_hazard", 1.01),
            "netting_collateral_and_cva_special_case",
        ),
    ],
}

# A tampered input can legitimately break more than one check when the checks
# share it (the CDS legs feed both the par spread and the MTM identity; the
# vol 24 funding and waterfall legs feed the cash-flow conservation roll-up).
DEPENDENT_FAILURES = {
    "daily_compounding_handcheck": {"continuous_limit"},
    "funding_cap_interval": {"cashflow_conservation"},
    "liquidation_method_waterfalls": {"cashflow_conservation", "stress_waterfall"},
    "insurance_identity": {"solvency_identity", "stress_waterfall"},
    "amm_identity": {"amm_lvr_fee_variants"},
    "ppa_risk_decomposition": {"ppa_cashflow_risk"},
    "ppa_cashflow_risk": {"ppa_risk_decomposition"},
    "fhs_coverage_improvement": {"fhs_constant_vol_identity"},
    "gpd_parameter_recovery": {"evt_var_es_identity"},
    "euler_additivity_normal": {"marginal_fd_consistency", "desk_report_reproducible"},
    "cross_asset_factor_mapping": {"pnl_explain_taylor_ordering"},
    "euler_es_additivity_sim": {"desk_report_reproducible"},
    "cds_par_spread_hull_pin": {"cds_mtm_identity"},
    "base_correlation_curve_shape": {"implied_correlation_reprices_quotes"},
}

FLAT_CASES = [(volume, *case) for volume, cases in CASES.items() for case in cases]


@pytest.mark.parametrize("volume", sorted(CASES))
def test_committed_gate_passes(volume):
    metrics, arrays = _load(volume)
    assert _failed(volume, dict(metrics), dict(arrays)) == set()


@pytest.mark.parametrize(
    ("volume", "label", "tamper", "check"),
    FLAT_CASES,
    ids=[f"vol{volume}-{label}" for volume, label, _, _ in FLAT_CASES],
)
def test_tamper_flips_exactly_the_recomputing_check(volume, label, tamper, check):
    metrics, arrays = _load(volume)
    metrics, arrays = dict(metrics), dict(arrays)
    tamper(metrics, arrays)
    failed = _failed(volume, metrics, arrays)
    assert check in failed, f"vol {volume} {label}: {check} still passes after tampering"
    assert failed <= {check, *DEPENDENT_FAILURES.get(check, set())}, (
        f"vol {volume} {label}: {failed}"
    )
