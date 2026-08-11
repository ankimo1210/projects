from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[1]
CONTRACT_ROOT = PROJECT_ROOT / "docs" / "contracts"


def _load(name: str) -> dict[str, object]:
    return json.loads((CONTRACT_ROOT / name).read_text(encoding="utf-8"))


def test_b9_preanalysis_is_bound_to_the_reviewed_m6_contract() -> None:
    m6_path = CONTRACT_ROOT / "b9-m6-protocol.json"
    preanalysis = _load("b9-preanalysis-v1.json")
    parent = preanalysis["parent_data"]

    assert preanalysis["schema_version"] == "b9-preanalysis-v1"
    assert preanalysis["status"] == "amended_before_full_candidate_evaluation"
    assert isinstance(parent, dict)
    assert parent["m6_protocol_sha256"] == sha256(m6_path.read_bytes()).hexdigest()
    assert parent["derived_panel_sha256"] == (
        "6c6008c2f28c30299e15e37613cfb0b3b22e8fd283858f5b459227c7e4a412a8"
    )
    assert parent["expected_panel_rows"] == 4631
    assert parent["expected_panel_companies"] == 163


def test_b9_preanalysis_locks_information_set_and_outer_test() -> None:
    contract = _load("b9-preanalysis-v1.json")
    information_set = contract["information_set"]
    splits = contract["splits"]

    assert isinstance(information_set, dict)
    assert information_set["prediction_time"] == "known_at = previous_available_date"
    assert "strictly before known_at" in information_set["feature_timestamp_rule"]
    assert "previous_accession" in information_set["required_row_provenance"]
    assert "previous_acceptance_datetime" in information_set["required_row_provenance"]

    assert isinstance(splits, dict)
    assert splits["outer_time_cutoff"] == "2023-10-23"
    assert splits["outer_test"] == {
        "rule": "target_available_date >= 2023-10-23 and cik % 3 == 0",
        "rows": 413,
        "companies": 38,
        "availability_dates": 183,
    }
    assert splits["development"]["rows"] == 2195
    assert splits["inner_validation"]["time_cutoff"] == "2021-01-01"
    assert splits["inner_validation"]["training_rows"] == 1504
    assert splits["inner_validation"]["validation_rows"] == 691
    assert "may not be used to retune" in splits["outer_test_access"]


def test_b9_preanalysis_keeps_text_in_core_and_foundation_models_advanced() -> None:
    contract = _load("b9-preanalysis-v1.json")
    features = contract["features"]
    models = contract["models"]

    assert isinstance(features, dict)
    assert features["text_core"]["minimum_row_coverage"] == 0.9
    assert "previous_accession only" in features["text_core"]["source"]
    assert "pretrained foundation-model embeddings" in features["advanced_only"]

    assert isinstance(models, dict)
    assert models["mandatory_linear_baselines"] == ["numeric_ridge", "tfidf_ridge"]
    assert set(models["core_learning_families"]) == {
        "numpy_mlp",
        "numpy_lstm",
        "numpy_tcn",
        "numpy_small_self_attention",
        "joint_text_numeric_mlp",
    }
    assert "NumPy" in models["dependency_policy"]
    assert "separate reviewed decision" in models["dependency_policy"]


def test_b9_preanalysis_has_locked_metrics_and_no_model_selected_rule() -> None:
    contract = _load("b9-preanalysis-v1.json")
    evaluation = contract["evaluation"]
    budget = contract["training_budget"]
    search_space = contract["search_space"]

    assert isinstance(evaluation, dict)
    assert evaluation["primary_metric"] == "mae"
    assert evaluation["secondary_metric"] == "median_absolute_error"
    assert evaluation["reference_metric"] == "rmse"
    comparator = evaluation["primary_comparator"]
    assert comparator["selection_partition"] == "inner_validation"
    assert comparator["candidate_baselines"] == [
        "zero",
        "pooled_drift",
        "seasonal",
        "company_mean",
    ]
    assert comparator["tie_break_order"] == comparator["candidate_baselines"]
    assert comparator["freeze_before_outer_access"] is True
    assert "minimum metric value" in evaluation["secondary_guardrail_comparator_rule"]
    assert "do not reselect" in evaluation["outer_uncertainty_comparator"]
    assert "99 percent of the minimum MAE" in evaluation["model_selection_gate"]
    assert evaluation["deep_learning_comparator"] == "tfidf_ridge"
    assert evaluation["failure_result"] == "no_model_selected"
    assert evaluation["bootstrap"] == {
        "unit": "company",
        "replications": 2000,
        "seed": 20260812,
        "interval": "percentile_95",
    }

    assert isinstance(budget, dict)
    assert budget["root_seed"] == 20260811
    assert budget["maximum_training_runs_per_family"] == 12
    assert budget["maximum_trainable_parameters"] == 100000

    assert isinstance(search_space, dict)
    assert search_space["numeric_ridge"]["ridge_lambda"] == [0.01, 0.1, 1.0, 10.0]
    assert search_space["tfidf_ridge"]["maximum_features"] == [5000, 10000]
    assert search_space["tfidf_ridge"]["ngram_maximum"] == [1, 2]
    for family in (
        "numpy_mlp",
        "numpy_lstm",
        "numpy_tcn",
        "numpy_small_self_attention",
        "joint_text_numeric_mlp",
    ):
        assert search_space[family]["seed_offsets"] == [0, 1, 2]


def test_b9_selection_gate_amendment_is_explicit_and_pre_outer() -> None:
    contract = _load("b9-preanalysis-v1.json")
    amendment = contract["amendments"][-1]
    assert amendment["previous_contract_sha256"] == (
        "fbe69fdf3b3bccba7fab70bcbb726d0df61685901cc0322d76fc66be1d7bbd6e"
    )
    assert "before_full_candidate_evaluation" in amendment["stage"]
    assert "no full candidate search" in amendment["observed_before_amendment"][1]
    assert "outer test" in amendment["change"]
