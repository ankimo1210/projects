from __future__ import annotations

import json
import math
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow
import scipy
import sklearn
import torch
import yaml

from lob_reproductions.provenance.profiles import project_root
from lob_reproductions.provenance.sources import source_manifests
from lob_reproductions.universal_features.assumptions import serialized_assumptions


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, np.ndarray):
        return _sanitize(value.tolist())
    if isinstance(value, np.generic):
        return _sanitize(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, Path):
        return str(value)
    return value


def _write_json(path: Path, document: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(_sanitize(document), handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def environment_manifest() -> dict[str, Any]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "pyarrow": pyarrow.__version__,
        "scipy": scipy.__version__,
        "scikit_learn": sklearn.__version__,
        "torch": torch.__version__,
        "torch_cuda_available": torch.cuda.is_available(),
        "timezone": "UTC",
    }


def git_state() -> dict[str, Any]:
    workspace = project_root().parent
    commands = {
        "head": ["git", "rev-parse", "HEAD"],
        "status": ["git", "status", "--short", "--untracked-files=all"],
    }
    result: dict[str, Any] = {"workspace": str(workspace)}
    for name, command in commands.items():
        completed = subprocess.run(
            command,
            cwd=workspace,
            text=True,
            capture_output=True,
            check=False,
        )
        result[name] = {
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    return result


def create_run_directory(profile_name: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    base = project_root() / "outputs" / f"{timestamp}_{profile_name}"
    candidate = base
    suffix = 1
    while candidate.exists():
        candidate = Path(f"{base}_{suffix}")
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def write_run_artifacts(
    *,
    profile: dict[str, Any],
    metrics: dict[str, Any],
    predictions: pd.DataFrame,
    shape_trace: list[dict[str, Any]],
    parameter_count: dict[str, Any],
    warnings: list[dict[str, Any]],
    report_header: str = "STRUCTURAL REPRODUCTION ON SYNTHETIC DATA",
    actual_dataset_profile: str | None = None,
) -> Path:
    output = create_run_directory(profile["implementation_profile"])
    with (output / "frozen_config.yaml").open("w", encoding="utf-8") as handle:
        yaml.safe_dump(profile, handle, sort_keys=False, allow_unicode=True)

    manifests = [document for _, document in source_manifests()]
    _write_json(
        output / "source_manifest.json",
        {
            "paper_id": profile["paper_id"],
            "implementation_profile": profile["implementation_profile"],
            "fidelity_class": profile["fidelity_class"],
            "paper_version": profile["paper_version"],
            "source_code_commit": profile["source_code_commit"],
            "dataset_profile": actual_dataset_profile or profile["dataset_profile"],
            "random_seed": profile["random_seed"],
            "sources": manifests,
        },
    )
    _write_json(output / "environment.json", environment_manifest())
    _write_json(output / "git_state.json", git_state())
    _write_json(output / "metrics.json", metrics)
    predictions.to_parquet(output / "predictions.parquet", index=False)
    _write_json(output / "shape_trace.json", shape_trace)
    _write_json(output / "parameter_count.json", parameter_count)

    assumption_ids = [
        evidence["locator"]
        for evidence in profile.get("provenance", {}).values()
        if evidence.get("source_type") == "ASSUMPTION"
    ]
    assumptions = {
        "profile_assumption_ids": sorted(set(assumption_ids)),
        "unresolved_material_fields": profile.get("unresolved_material_fields", []),
        "sirignano_cont_catalog": (
            serialized_assumptions() if profile["paper_id"] == "sirignano_cont_2019" else []
        ),
    }
    _write_json(output / "assumptions.json", assumptions)
    _write_json(output / "warnings.json", warnings)

    report = [
        f"# {report_header}",
        "",
        f"- paper_id: `{profile['paper_id']}`",
        f"- implementation_profile: `{profile['implementation_profile']}`",
        f"- fidelity_class: `{profile['fidelity_class']}`",
        f"- paper_version: `{profile['paper_version']}`",
        f"- source_code_commit: `{profile['source_code_commit']}`",
        f"- dataset_profile: `{actual_dataset_profile or profile['dataset_profile']}`",
        f"- random_seed: `{profile['random_seed']}`",
        "",
        "This output verifies structure/protocol on a deterministic synthetic fixture.",
        "It is not a numerical replication of paper-reported market-data results.",
        "",
        "## Metrics",
        "",
        "```json",
        json.dumps(_sanitize(metrics), ensure_ascii=False, indent=2),
        "```",
        "",
        "## Warnings",
        "",
    ]
    report.extend(f"- {item.get('message', item)}" for item in warnings)
    (output / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return output
