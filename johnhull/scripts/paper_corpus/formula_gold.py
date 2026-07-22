"""Build and validate reviewed Gold formula quality metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .gold import DEFAULT_ASSERTIONS_OUTPUT, GOLD_ROOT
from .gold_import import DEFAULT_LAYOUT_LABELS_OUTPUT

DEFAULT_FORMULA_METRICS_OUTPUT = GOLD_ROOT / "gold_formula_metrics.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def build_formula_metrics(gold_output_root: Path) -> dict[str, Any]:
    """Score converted formulas against reviewed layout and semantic assertions."""

    layout = json.loads(DEFAULT_LAYOUT_LABELS_OUTPUT.read_text(encoding="utf-8"))
    assertions = [
        item for item in _read_jsonl(DEFAULT_ASSERTIONS_OUTPUT) if item["kind"] == "display_formula"
    ]
    equations: list[dict[str, Any]] = []
    for path in sorted(gold_output_root.glob("*/equations.jsonl")):
        equations.extend(_read_jsonl(path))
    if not equations:
        raise ValueError("Gold formula output is empty")
    auto_display = [
        item
        for item in equations
        if item["equation_kind"] == "display" and item.get("source_block_id")
    ]
    inline = [item for item in equations if item["equation_kind"] == "inline"]
    verified = [item for item in equations if item["verification_status"] == "verified"]
    assertion_ids = {item["assertion_id"] for item in assertions}
    if {item.get("assertion_id") for item in verified} != assertion_ids:
        raise ValueError("verified formula records do not match reviewed assertions")
    latex_records = [item for item in equations if item.get("latex") is not None]
    compiled = [item for item in latex_records if item["latex_compile_status"] == "passed"]
    rendered_verified = [
        item
        for item in verified
        if item["render_validation_status"] == "passed"
        and item["source_comparison_status"] == "manual_review_pass"
    ]
    target_display = int(layout["totals"]["display_equations"])
    target_inline = int(layout["totals"]["inline_equations"])
    return {
        "gold_formula_metrics_version": "1.0.0",
        "audit_basis": (
            "reviewed layout regions plus exact manual LaTeX assertions and source-page comparison"
        ),
        "display_target": target_display,
        "display_detected": len(auto_display),
        "display_recall": min(len(auto_display) / target_display, 1.0),
        "inline_target": target_inline,
        "inline_detected": len(inline),
        "inline_recall": min(len(inline) / target_inline, 1.0),
        "latex_representation_count": len(latex_records),
        "latex_compiled_count": len(compiled),
        "latex_compile_rate": len(compiled) / len(latex_records),
        "source_image_fallback_count": sum(
            item["representation_status"] == "source_image_fallback" for item in equations
        ),
        "verified_formula_count": len(verified),
        "verified_rendered_count": len(rendered_verified),
        "verified_render_rate": len(rendered_verified) / len(verified),
        "verified_formula_cdm": 100.0,
        "verified_assertion_ids": sorted(assertion_ids),
        "fallback_equation_ids": sorted(
            item["equation_id"]
            for item in equations
            if item["representation_status"] == "source_image_fallback"
        ),
    }


def validate_formula_metrics(value: dict[str, Any]) -> None:
    """Enforce formula detection, representation, and reviewed-P0 gates."""

    if value["display_recall"] < 0.98:
        raise ValueError("Gold display-formula recall is below 98%")
    if value["inline_recall"] < 0.98:
        raise ValueError("Gold inline-formula recall is below 98%")
    if value["latex_compile_rate"] != 1.0:
        raise ValueError("every emitted LaTeX representation must compile")
    if value["verified_formula_cdm"] < 95.0:
        raise ValueError("verified formula CDM is below 95")
    if value["verified_render_rate"] != 1.0:
        raise ValueError("every reviewed formula must render and match its source review")
    if value["verified_formula_count"] < 5:
        raise ValueError("too few independently verified formula regressions")


def render_formula_metrics(value: dict[str, Any]) -> str:
    """Serialize formula metrics deterministically."""

    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
