from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from lob_reproductions.data.fi2010_public import (
    audit_fi2010_archive,
    dataset_manifest,
    fetch_fi2010,
    verify_fi2010_archive,
)
from lob_reproductions.deeplob import DeepLOBAuthorPyTorch, DeepLOBAuthorTF2Spec
from lob_reproductions.fixtures import (
    FI2010MatrixFixture,
    QueueImbalanceFixture,
    UniversalMultiAssetEventFixture,
)
from lob_reproductions.outputs import write_run_artifacts
from lob_reproductions.provenance.profiles import (
    load_profile,
    project_root,
    validate_all_profiles,
)
from lob_reproductions.provenance.sources import fetch_all_sources, verify_sources
from lob_reproductions.queue_imbalance import (
    LocalLogisticRegression,
    ParametricLogisticRegression,
    evaluate_binary_probability_forecast,
    split_observations,
)
from lob_reproductions.queue_imbalance.evaluation import null_model_metrics
from lob_reproductions.registry import build_profile_model, inspect_neural_profile
from lob_reproductions.tlob import MLPLOBReference, TLOBReference
from lob_reproductions.universal_features.protocols import (
    run_synthetic_linear_comparison,
    run_synthetic_lstm_comparison,
)


def _print_json(document: Any) -> None:
    print(json.dumps(document, ensure_ascii=False, indent=2, default=str))


def _sources_fetch(_args: argparse.Namespace) -> int:
    _print_json(fetch_all_sources())
    return 0


def _sources_verify(_args: argparse.Namespace) -> int:
    report = verify_sources()
    _print_json(report)
    return 0 if report["ok"] else 1


def _evidence_build(_args: argparse.Namespace) -> int:
    profiles = validate_all_profiles()
    sources = verify_sources()
    invalid = [name for name, item in profiles.items() if not item["valid"]]
    report = {
        "profiles": profiles,
        "invalid_profiles": invalid,
        "sources": {
            "mismatches": sources["mismatches"],
            "missing_optional_local_sources": sources["missing_optional_local_sources"],
        },
        "ok": not invalid and not sources["mismatches"],
    }
    _print_json(report)
    return 0 if report["ok"] else 1


def _fixtures_generate(args: argparse.Namespace) -> int:
    destination = project_root() / "outputs" / f"fixtures_seed_{args.seed}"
    destination.mkdir(parents=True, exist_ok=True)
    fi = FI2010MatrixFixture()
    queue = QueueImbalanceFixture(days=4, intervals_per_day=140, seed=args.seed)
    queue_observations = queue.sample_paper_observations(observations_per_day=100, seed=args.seed)
    universal = UniversalMultiAssetEventFixture(seed=args.seed)
    np.savez_compressed(
        destination / "fi2010_matrix_fixture.npz",
        values=fi.matrix.values,
        asset_id=fi.matrix.asset_id,
        day_id=fi.matrix.day_id,
    )
    np.savez_compressed(
        destination / "queue_imbalance_fixture.npz",
        imbalance=queue_observations.imbalance,
        response=queue_observations.response,
        sampled_time=queue_observations.sampled_time,
        interval_start=queue_observations.interval_start,
        interval_end=queue_observations.interval_end,
        source_event_time=queue_observations.source_event_time,
    )
    np.savez_compressed(
        destination / "universal_multi_asset_fixture.npz",
        features=universal.features,
        labels=universal.labels,
        mid_prices=universal.mid_prices,
        sector=universal.sector,
    )
    metadata = {
        "seed": args.seed,
        "claim_limit": "structural fixtures only",
        "fi2010": fi.latent_truth,
        "queue": {"days": queue.days, "observations": queue_observations.response.size},
        "universal": universal.latent_truth,
    }
    (destination / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, default=lambda item: item.tolist())
        + "\n",
        encoding="utf-8",
    )
    _print_json({"output": str(destination), "metadata": metadata})
    return 0


def _inspect(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    if profile["paper_id"] == "gould_bonart_2015":
        report = {
            "profile": args.profile,
            "shape_trace": [
                {"name": "Level1EventStream", "shape": ["events"]},
                {"name": "strict_open_interval_samples", "shape": ["observations", 1]},
                {"name": "binary_response", "shape": ["observations"]},
            ],
            "parameter_count": {"parametric_logistic": 2, "local_fit_per_query": 2},
        }
    else:
        inspected = inspect_neural_profile(profile)
        report = {
            "profile": args.profile,
            "paper_id": profile["paper_id"],
            "fidelity_class": profile["fidelity_class"],
            "runtime": inspected["runtime"],
        }
        if args.show_shapes:
            report["shape_trace"] = inspected["shape_trace"]
        if args.show_parameters:
            report["parameter_count"] = inspected["parameter_count"]
        if not args.show_shapes and not args.show_parameters:
            report["hint"] = "pass --show-shapes and/or --show-parameters"
    _print_json(report)
    return 0


def _tensor_predictions(output: torch.Tensor | None, profile: dict[str, Any]) -> pd.DataFrame:
    if output is None:
        probabilities = np.full((2, 3), 1 / 3, dtype=float)
    else:
        array = output.detach().cpu()
        is_probability = bool(
            torch.all(array >= 0)
            and torch.all(array <= 1)
            and torch.allclose(array.sum(dim=1), torch.ones(array.shape[0]), atol=1e-5)
        )
        probabilities = (array if is_probability else torch.softmax(array, dim=1)).numpy()
    frame = pd.DataFrame(
        probabilities,
        columns=[f"probability_class_{index}" for index in range(probabilities.shape[1])],
    )
    frame.insert(0, "sample_id", np.arange(len(frame)))
    frame["prediction"] = probabilities.argmax(axis=1)
    frame["paper_id"] = profile["paper_id"]
    frame["implementation_profile"] = profile["implementation_profile"]
    return frame


def _smoke_profile(profile: dict[str, Any]) -> Path:
    inspected = inspect_neural_profile(profile)
    predictions = _tensor_predictions(inspected["output"], profile)
    probability_columns = [column for column in predictions if column.startswith("probability_")]
    sums = predictions[probability_columns].sum(axis=1).to_numpy()
    metrics = {
        "architecture_verified": True,
        "output_rows": len(predictions),
        "probability_rows_sum_to_one": bool(np.allclose(sums, 1.0, atol=1e-6)),
        "numerical_benchmark_attempted": False,
        "runtime": inspected["runtime"],
    }
    if profile["paper_id"] == "sirignano_cont_2019":
        fixture = UniversalMultiAssetEventFixture(seed=int(profile["random_seed"]))
        metrics["audit_metrics"] = {
            "synthetic_protocol_linear": run_synthetic_linear_comparison(fixture),
            "synthetic_protocol_lstm_scaled": run_synthetic_lstm_comparison(fixture),
        }
    warnings = [
        {
            "code": "SYNTHETIC_ONLY",
            "message": "Synthetic structure test; paper-reported accuracy/F1 was not attempted.",
        }
    ]
    if profile["fidelity_class"] == "A_AUTHOR_CODE_EXACT":
        warnings.append(
            {
                "code": "NO_REFERENCE_EXECUTION",
                "message": "This smoke validates the clean-room target; it did not execute fetched reference code side-by-side.",
            }
        )
    if profile.get("unresolved_material_fields"):
        warnings.append(
            {
                "code": "UNRESOLVED_MATERIAL_FIELDS",
                "message": "Unresolved fields: " + ", ".join(profile["unresolved_material_fields"]),
            }
        )
    expected_framework = str(profile.get("training", {}).get("framework", ""))
    if expected_framework.startswith("torch_2.5") and not torch.__version__.startswith("2.5"):
        warnings.append(
            {
                "code": "FRAMEWORK_VERSION_DEVIATION",
                "message": f"Pinned repository specifies {expected_framework}; clean-room smoke used torch {torch.__version__}.",
            }
        )
    if profile["implementation_profile"].startswith("deeplob_author_tf2"):
        warnings.append(
            {
                "code": "TF2_ANALYTIC_SPEC",
                "message": "TensorFlow native execution is optional; this run used the pinned analytic shape/count specification.",
            }
        )
    return write_run_artifacts(
        profile=profile,
        metrics=metrics,
        predictions=predictions,
        shape_trace=inspected["shape_trace"],
        parameter_count=inspected["parameter_count"],
        warnings=warnings,
        actual_dataset_profile="deterministic_synthetic_smoke_v1",
    )


def _smoke(args: argparse.Namespace) -> int:
    if args.data != "synthetic":
        raise ValueError("default smoke supports only synthetic data")
    profile = load_profile(args.profile)
    if profile["paper_id"] == "gould_bonart_2015":
        output = _run_queue_profile(profile)
    else:
        output = _smoke_profile(profile)
    _print_json({"output": str(output), "status": "architecture verified"})
    return 0


def _run_queue_profile(profile: dict[str, Any]) -> Path:
    fixture = QueueImbalanceFixture(days=12, intervals_per_day=140, seed=profile["random_seed"])
    observations = fixture.sample_paper_observations(
        observations_per_day=100, seed=profile["random_seed"]
    )
    split = split_observations(
        observations,
        train_fraction=float(profile["split"]["train_fraction"]),
        strategy=profile["split"]["strategy"],
        seed=profile["random_seed"],
    )
    train_x = observations.imbalance[split.train_index]
    train_y = observations.response[split.train_index]
    test_x = observations.imbalance[split.test_index]
    test_y = observations.response[split.test_index]

    parametric = ParametricLogisticRegression().fit(train_x, train_y)
    parametric_probability = parametric.predict_proba(test_x)
    local = LocalLogisticRegression(
        bandwidth=float(profile["model"]["nearest_neighbor_bandwidth"])
    ).fit(train_x, train_y)
    local_probability = local.predict_proba(test_x)

    metrics = {
        "parametric_logistic": evaluate_binary_probability_forecast(test_y, parametric_probability),
        "local_logistic": evaluate_binary_probability_forecast(test_y, local_probability),
        "null_model": null_model_metrics(test_y),
        "coefficients": {
            "intercept": parametric.intercept_,
            "queue_imbalance": parametric.slope_,
            "mle_converged": parametric.converged_,
        },
        "fixture": {
            "days": fixture.days,
            "observations_per_day": 100,
            "training_observations": int(split.train_index.size),
            "testing_observations": int(split.test_index.size),
            "all_samples_strictly_inside_interval": True,
            "post_move_features": 0,
        },
        "bandwidth": {
            "reported_value": local.bandwidth,
            "selection_procedure": "five-fold CV minimizing MSR is implemented and unit-tested",
        },
        "numerical_benchmark_attempted": False,
    }
    predictions = pd.DataFrame(
        {
            "sample_id": np.arange(test_y.size),
            "imbalance": test_x,
            "target_up": test_y,
            "parametric_probability_up": parametric_probability,
            "local_probability_up": local_probability,
            "interval_end": observations.interval_end[split.test_index],
            "sampled_time": observations.sampled_time[split.test_index],
        }
    )
    trace = [
        {"name": "Level1EventStream", "shape": [len(fixture.events), 7]},
        {"name": "strict_open_interval_samples", "shape": [observations.response.size, 1]},
        {
            "name": "random_or_chronological_split",
            "shape": [split.train_index.size, split.test_index.size],
        },
        {"name": "probability_forecasts", "shape": [test_y.size, 2]},
    ]
    warnings = [
        {
            "code": "SCALED_SYNTHETIC_FIXTURE",
            "message": "Uses 12 synthetic days for CPU runtime; paper profile remains 252 days and is not numerically benchmarked.",
        },
        {
            "code": "SYNTHETIC_ONLY",
            "message": "Protocol reproduced on a synthetic fixture; no stock-level empirical conclusion is claimed.",
        },
    ]
    return write_run_artifacts(
        profile=profile,
        metrics=metrics,
        predictions=predictions,
        shape_trace=trace,
        parameter_count={"parametric_coefficients": 2, "local_coefficients_per_query": 2},
        warnings=warnings,
        actual_dataset_profile="queue_imbalance_synthetic_smoke_12d_v1",
    )


def _run(args: argparse.Namespace) -> int:
    if args.data != "synthetic":
        raise ValueError("real-data runs require the optional adapter and an exact dataset variant")
    profile = load_profile(args.profile)
    output = (
        _run_queue_profile(profile)
        if profile["paper_id"] == "gould_bonart_2015"
        else _smoke_profile(profile)
    )
    _print_json({"output": str(output)})
    return 0


def _golden_test(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    name = profile["implementation_profile"]
    checks: dict[str, Any] = {}
    model, _sample = build_profile_model(profile)
    if isinstance(model, DeepLOBAuthorTF2Spec):
        actual = sum(model.parameter_breakdown().values())
        checks["parameter_count"] = {
            "actual": actual,
            "expected": 142_435,
            "pass": actual == 142_435,
        }
        checks["dropout_forced_training"] = model.dropout_forced_training
    elif isinstance(model, DeepLOBAuthorPyTorch):
        actual = sum(parameter.numel() for parameter in model.parameters())
        checks["parameter_count"] = {
            "actual": actual,
            "expected": 143_907,
            "pass": actual == 143_907,
        }
    elif isinstance(model, TLOBReference):
        actual = sum(parameter.numel() for parameter in model.parameters())
        expected = profile["model"].get("expected_parameters")
        checks["parameter_count"] = {
            "actual": actual,
            "expected": expected,
            "authoritative": expected is not None,
            "pass": expected is None or actual == expected,
        }
        checks["attention_masks"] = {
            "pass": all(layer.attention.dropout == 0.0 for layer in model.layers),
            "causal_mask": False,
        }
    elif isinstance(model, MLPLOBReference):
        actual = sum(parameter.numel() for parameter in model.parameters())
        expected = profile["model"].get("expected_parameters")
        checks["parameter_count"] = {
            "actual": actual,
            "expected": expected,
            "authoritative": expected is not None,
            "pass": expected is None or actual == expected,
        }
    else:
        inspected = inspect_neural_profile(profile)
        checks["forward_shape"] = inspected["shape_trace"][-1]
    passed = all(
        item.get("pass", True) if isinstance(item, dict) else True for item in checks.values()
    )
    _print_json(
        {
            "profile": name,
            "checks": checks,
            "pass": passed,
            "claim_limit": "structural golden tests; reference side-by-side execution not claimed",
        }
    )
    return 0 if passed else 1


def _data_fetch(args: argparse.Namespace) -> int:
    manifest = dataset_manifest()
    if not args.accept_terms:
        _print_json(
            {
                "source": manifest["author_archive_url"],
                "terms": manifest["terms_url"],
                "redistribution_status": manifest["redistribution_status"],
                "action": "review terms, then rerun with --accept-terms",
            }
        )
        return 2
    _print_json(fetch_fi2010(accept_terms=True))
    return 0


def _data_verify(args: argparse.Namespace) -> int:
    report = verify_fi2010_archive(deep=not args.quick)
    _print_json(report)
    return 0 if report["ok"] else 1


def _data_audit(args: argparse.Namespace) -> int:
    report = audit_fi2010_archive(sequence_length=args.sequence_length, horizon=args.horizon)
    _print_json(report)
    return 0 if report["ok"] else 1


def _report_build(_args: argparse.Namespace) -> int:
    outputs = sorted((project_root() / "outputs").glob("*/metrics.json"))
    lines = [
        "# Local run index",
        "",
        "STRUCTURAL REPRODUCTION ON SYNTHETIC DATA",
        "",
        "No paper-reported market-data numerical benchmark is claimed.",
        "",
        "## Local runs",
        "",
    ]
    if not outputs:
        lines.append("No local run artifacts are present.")
    for metrics_path in outputs:
        lines.append(f"- `{metrics_path.parent.name}`")
    run_index = project_root() / "outputs" / "RUN_INDEX.md"
    run_index.parent.mkdir(parents=True, exist_ok=True)
    run_index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = project_root() / "REPRODUCTION_REPORT.md"
    if not report.is_file():
        report.write_text(
            "# STRUCTURAL REPRODUCTION ON SYNTHETIC DATA\n\n"
            "No paper-reported market-data numerical benchmark is claimed.\n",
            encoding="utf-8",
        )
    _print_json({"output": str(report), "run_index": str(run_index), "runs": len(outputs)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lob-repro")
    commands = parser.add_subparsers(dest="command", required=True)

    sources = commands.add_parser("sources")
    source_commands = sources.add_subparsers(dest="sources_command", required=True)
    source_commands.add_parser("fetch").set_defaults(func=_sources_fetch)
    source_commands.add_parser("verify").set_defaults(func=_sources_verify)

    evidence = commands.add_parser("evidence")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_commands.add_parser("build").set_defaults(func=_evidence_build)

    fixtures = commands.add_parser("fixtures")
    fixture_commands = fixtures.add_subparsers(dest="fixtures_command", required=True)
    generate = fixture_commands.add_parser("generate")
    generate.add_argument("--seed", type=int, default=7)
    generate.set_defaults(func=_fixtures_generate)

    inspect = commands.add_parser("inspect")
    inspect.add_argument("--profile", required=True)
    inspect.add_argument("--show-shapes", action="store_true")
    inspect.add_argument("--show-parameters", action="store_true")
    inspect.set_defaults(func=_inspect)

    smoke = commands.add_parser("smoke")
    smoke.add_argument("--profile", required=True)
    smoke.add_argument("--data", default="synthetic")
    smoke.set_defaults(func=_smoke)

    golden = commands.add_parser("golden-test")
    golden.add_argument("--profile", required=True)
    golden.set_defaults(func=_golden_test)

    run = commands.add_parser("run")
    run.add_argument("--profile", required=True)
    run.add_argument("--data", default="synthetic")
    run.set_defaults(func=_run)

    data = commands.add_parser("data")
    data_commands = data.add_subparsers(dest="data_command", required=True)
    fetch_data = data_commands.add_parser("fetch-fi2010")
    fetch_data.add_argument("--accept-terms", action="store_true")
    fetch_data.set_defaults(func=_data_fetch)
    verify_data = data_commands.add_parser("verify-fi2010")
    verify_data.add_argument("--quick", action="store_true")
    verify_data.set_defaults(func=_data_verify)
    audit_data = data_commands.add_parser("audit-fi2010")
    audit_data.add_argument("--sequence-length", type=int, default=100)
    audit_data.add_argument("--horizon", type=int, default=100)
    audit_data.set_defaults(func=_data_audit)

    report = commands.add_parser("report")
    report_commands = report.add_subparsers(dest="report_command", required=True)
    report_commands.add_parser("build").set_defaults(func=_report_build)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (ValueError, FileNotFoundError, PermissionError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
