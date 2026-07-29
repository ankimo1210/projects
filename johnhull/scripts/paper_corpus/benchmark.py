"""Tracked extractor bake-off evidence and fail-closed selection rules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .gold import GOLD_ROOT

DEFAULT_BAKEOFF_OUTPUT = GOLD_ROOT / "extractor_bakeoff.json"

EXTRACTORS = (
    {
        "extractor_id": "pymupdf4llm-1.28.0",
        "name": "PyMuPDF4LLM",
        "version": "1.28.0",
        "mode": "page_chunks",
        "execution_status": "completed",
        "runtime_seconds_hw_p6": 0.775,
        "license_gate": {
            "status": "review",
            "reason": "PyMuPDF is offered under AGPL or a commercial license.",
        },
        "operational_notes": ["Fast baseline; formula transcription was not usable."],
    },
    {
        "extractor_id": "docling-2.114.0",
        "name": "Docling",
        "version": "2.114.0",
        "mode": "standard_pipeline",
        "execution_status": "completed",
        "runtime_seconds_hw_p6": None,
        "license_gate": {"status": "pass", "reason": "MIT-licensed package."},
        "operational_notes": [
            "Produced structured formulas and tables with semantic and numeric errors."
        ],
    },
    {
        "extractor_id": "marker-2.0.0",
        "name": "Marker",
        "version": "2.0.0",
        "mode": "balanced_and_fast",
        "execution_status": "partial",
        "runtime_seconds_hw_p6": 0.264,
        "license_gate": {
            "status": "review",
            "reason": "Code is Apache-2.0; model weights impose additional commercial terms.",
        },
        "operational_notes": [
            "Balanced mode required Docker through Surya vLLM in this WSL environment.",
            "CPU LLM mode required an unavailable llama-server.",
            "Fast mode completed but emitted no equation transcription.",
        ],
    },
    {
        "extractor_id": "mineru-3.4.4-pipeline",
        "name": "MinerU",
        "version": "3.4.4",
        "mode": "pipeline",
        "execution_status": "completed",
        "runtime_seconds_hw_p6": None,
        "license_gate": {
            "status": "review",
            "reason": (
                "Custom open-source license adds service attribution and commercial-scale "
                "thresholds to the Apache-2.0 base."
            ),
        },
        "operational_notes": [
            "Pipeline mode completed locally on the representative and 88-page gold sets.",
            "Hybrid VLM was unavailable because the RTX 5080 requires CUDA 12.9 or newer.",
            "Pipeline output remains auto/unverified until a separate assertion verifies it.",
        ],
    },
)

CASES = (
    {
        "case_id": "hw-p6-vasicek-b",
        "metric": "formula_exact_match",
        "expected": r"B(t,T)=\frac{1-e^{-a(T-t)}}{a}",
        "results": {
            "pymupdf4llm-1.28.0": "fail",
            "docling-2.114.0": "fail",
            "marker-2.0.0": "missing",
            "mineru-3.4.4-pipeline": "pass",
        },
    },
    {
        "case_id": "hw-p6-mean-reversion-equation-15",
        "metric": "formula_exact_match",
        "expected": (
            r"a(t)=-\frac{\partial^2 B(0,t)/\partial t^2}"
            r"{\partial B(0,t)/\partial t}"
        ),
        "results": {
            "pymupdf4llm-1.28.0": "fail",
            "docling-2.114.0": "fail",
            "marker-2.0.0": "missing",
            "mineru-3.4.4-pipeline": "fail",
        },
    },
    {
        "case_id": "hw-p17-table4-critical-cells",
        "metric": "numeric_cell_exact_match",
        "expected": {"Ext Vas|1.02": 0.35, "Two-factor CIR|1.02": 0.34},
        "results": {
            "pymupdf4llm-1.28.0": "not_run",
            "docling-2.114.0": "fail",
            "marker-2.0.0": "not_run",
            "mineru-3.4.4-pipeline": "pass",
        },
    },
    {
        "case_id": "hw-p17-table3-and-table4-other-cells",
        "metric": "numeric_cell_exact_match",
        "expected": {"Table 3 source value": 1.32, "Table 4 source value": 0.86},
        "results": {
            "pymupdf4llm-1.28.0": "not_run",
            "docling-2.114.0": "not_scored",
            "marker-2.0.0": "not_run",
            "mineru-3.4.4-pipeline": "fail",
        },
    },
)


def build_bakeoff() -> dict[str, Any]:
    """Build the deterministic, reviewed bake-off record."""

    return {
        "bakeoff_version": "1.0.0",
        "reviewed_at": "2026-07-23",
        "reviewer": "codex-visual-semantic-audit-2026-07-23",
        "environment": {
            "platform": "WSL2 Linux",
            "gpu": "NVIDIA GeForce RTX 5080",
            "constraint_notes": [
                "Docker was unavailable to Marker balanced mode.",
                "Installed CUDA support could not execute MinerU hybrid VLM on SM 12.0.",
            ],
        },
        "gold_scope": {
            "paper_id": "1990-hull-white-interest-rate-derivative-securities",
            "source_pages": [6, 17],
            "evidence": "gold_assertions.jsonl and visually reviewed source-page renders",
        },
        "extractors": list(EXTRACTORS),
        "cases": list(CASES),
        "selection": {
            "extractor_id": "mineru-3.4.4-pipeline",
            "status": "accepted_with_controls",
            "reason": (
                "Best available local structured layout, equation, and table candidate output; "
                "the benchmark also proves it is not semantically reliable on its own."
            ),
            "dependency_policy": "optional pinned uvx tool; not a production dependency",
            "required_controls": [
                "Retain source crops for every equation, table, and figure.",
                "Mark extractor output auto or unverified, never verified by extraction alone.",
                "Apply only independent, reviewed assertions as verified overrides.",
                "Fail P0 release gates when a required formula or numeric cell is unverified.",
                "Record extractor version and source PDF SHA-256 in every derived record.",
            ],
        },
        "metric_coverage": {
            "text_edit_distance": "deferred_until_independent_text_transcripts",
            "formula_token_error": "represented_by_exact_match_regressions",
            "formula_cdm": "deferred_until_rendered_formula_gold",
            "table_teds": "deferred_until_independent_structural_table_gold",
            "numeric_accuracy": "represented_by_independently_verified_cells",
            "reading_order": "visual_overlay_audit_only",
            "runtime": "partial",
            "memory": "not_measured",
            "reproducibility": "versions_and_modes_pinned; full_determinism_gate_pending",
            "licensing": "recorded_per_extractor",
        },
        "limitations": [
            "This small bake-off selects a backend; it is not the release quality score.",
            "Metrics without independent gold labels remain explicitly deferred.",
            "No aggregate pass is inferred from layout-region counts or extractor agreement.",
        ],
    }


def render_bakeoff(value: dict[str, Any] | None = None) -> str:
    """Serialize the bake-off deterministically."""

    return json.dumps(value or build_bakeoff(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def validate_bakeoff(value: dict[str, Any]) -> None:
    """Validate candidate coverage and the fail-closed selection contract."""

    ids = {item["extractor_id"] for item in value["extractors"]}
    required = {
        "pymupdf4llm-1.28.0",
        "docling-2.114.0",
        "marker-2.0.0",
        "mineru-3.4.4-pipeline",
    }
    if ids != required:
        raise ValueError("bake-off must cover all four candidate extractors exactly once")
    if value["selection"]["extractor_id"] not in ids:
        raise ValueError("selected extractor must be one of the benchmark candidates")
    controls = " ".join(value["selection"]["required_controls"]).lower()
    if "never verified" not in controls or "source crops" not in controls:
        raise ValueError("selection must remain fail-closed and retain source crops")
    for case in value["cases"]:
        if set(case["results"]) != ids:
            raise ValueError(f"incomplete extractor results for {case['case_id']}")
    metrics = value["metric_coverage"]
    if any(not status for status in metrics.values()):
        raise ValueError("every planned metric must state its measured or deferred status")


def read_bakeoff(path: Path = DEFAULT_BAKEOFF_OUTPUT) -> dict[str, Any]:
    """Read the tracked bake-off JSON."""

    return json.loads(path.read_text(encoding="utf-8"))
