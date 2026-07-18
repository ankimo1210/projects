from __future__ import annotations

import json
from dataclasses import replace

from deep_hedge_price.pricing_ablation import (
    PricingAblationProtocol,
    run_pricing_ablation,
)
from deep_hedge_price.pricing_config import PricingConfig, pricing_run_directory
from deep_hedge_price.pricing_data import generate_black_scholes_dataset


def _config():
    base = PricingConfig()
    return replace(
        base,
        profile="ablation-test",
        data=replace(
            base.data,
            train_size=128,
            validation_size=64,
            test_size=64,
            ood_size=32,
        ),
        model=replace(base.model, activation="tanh"),
        training=replace(base.training, learning_rate=0.003),
        output=replace(base.output, namespace="ablation-test"),
    )


def _protocol():
    return PricingAblationProtocol(
        model_seeds=(11, 22, 33),
        train_rows=96,
        validation_rows=48,
        test_rows=48,
        epochs=2,
        batch_size=48,
        hidden_layers=1,
        hidden_units=8,
        positive_penalty_weight=0.2,
    )


def test_ablation_uses_one_fixed_split_three_seeds_and_hard_reports(tmp_path):
    config = _config()
    manifest, _ = generate_black_scholes_dataset(config, pricing_run_directory(config, tmp_path))
    output, result = run_pricing_ablation(
        config,
        manifest,
        tmp_path / "reports" / "pricing_ablation_test.json",
        protocol=_protocol(),
    )

    assert output.exists()
    assert result["artifact_kind"] == "pricing_quick_ablation"
    assert result["dataset"]["same_fixed_split_for_every_variant_and_model_seed"] is True
    assert result["protocol"]["model_seeds"] == [11, 22, 33]
    assert result["protocol"]["analytic_delta_embedded_in_model_or_inference"] is False
    assert set(result["variants"]) == {
        "price_only",
        "direct_multi_task",
        "differential_ml",
    }
    protocol_ids = {variant["data_protocol_id"] for variant in result["variants"].values()}
    protocol_ids.update(
        result["penalty_ablation"][name]["data_protocol_id"] for name in ("zero", "positive")
    )
    assert protocol_ids == {result["dataset"]["data_protocol_id"]}
    for variant in result["variants"].values():
        assert len(variant["seed_runs"]) == 3
        assert variant["aggregate"]["test"]["price_mae"]["standard_deviation_population"] >= 0
        for run in variant["seed_runs"]:
            checks = run["hard_validation"]["checks"]
            assert {check["name"] for check in checks} == {
                "price_bounds",
                "put_call_parity",
                "strike_monotonicity",
                "strike_convexity",
                "calendar_monotonicity",
                "spot_monotonicity",
                "nonnegative_gamma",
                "greek_consistency",
            }
            assert all(
                {"n_checked", "n_violations", "max_violation", "tolerance"} <= check.keys()
                for check in checks
            )
    assert result["penalty_ablation"]["zero"]["weight"] == 0.0
    assert result["penalty_ablation"]["positive"]["weight"] == 0.2
    assert len(result["penalty_ablation"]["positive"]["seed_runs"]) == 3
    assert not list(tmp_path.rglob("*.pt"))
    assert json.loads(output.read_text(encoding="utf-8")) == result


def test_ablation_json_is_byte_stable(tmp_path, monkeypatch):
    config = _config()
    manifest, _ = generate_black_scholes_dataset(config, pricing_run_directory(config, tmp_path))
    protocol = replace(
        _protocol(),
        train_rows=48,
        validation_rows=24,
        test_rows=24,
        epochs=1,
        batch_size=48,
    )

    def hard_report(_model, _device):
        return {
            "arbitrage_free": True,
            "checks": [
                {
                    "name": "price_bounds",
                    "n_checked": 1,
                    "n_violations": 0,
                    "violation_rate": 0.0,
                    "max_violation": 0.0,
                    "tolerance": 1e-6,
                    "passed": True,
                }
            ],
        }

    monkeypatch.setattr("deep_hedge_price.pricing_ablation._hard_report", hard_report)
    output = tmp_path / "reports" / "stable.json"
    run_pricing_ablation(config, manifest, output, protocol=protocol)
    first = output.read_bytes()
    run_pricing_ablation(config, manifest, output, protocol=protocol)
    assert output.read_bytes() == first


def test_ablation_protocol_rejects_anything_other_than_three_distinct_seeds():
    protocol = replace(_protocol(), model_seeds=(1, 1, 2))
    try:
        protocol.validate()
    except ValueError as error:
        assert "exactly three distinct" in str(error)
    else:  # pragma: no cover
        raise AssertionError("duplicate model seeds must be rejected")
