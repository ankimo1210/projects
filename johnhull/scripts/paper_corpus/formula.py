"""Deterministic LaTeX representation and reviewed-formula rendering checks."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def compile_to_mathml(latex: str) -> tuple[str, str | None, str | None]:
    """Compile LaTeX to well-formed MathML and return status, hash, and error."""

    try:
        from latex2mathml.converter import convert

        mathml = convert(latex)
        ET.fromstring(mathml)
    except Exception as exc:  # converters expose several parser exception types
        return "failed", None, f"{type(exc).__name__}: {exc}"
    digest = hashlib.sha256(mathml.encode("utf-8")).hexdigest()
    return "passed", digest, None


def render_reviewed_formula(
    latex: str,
    output_dir: Path,
    equation_id: str,
) -> str:
    """Render a reviewed, MathText-compatible formula to a deterministic PNG."""

    import matplotlib as mpl
    from matplotlib.figure import Figure

    safe_id = equation_id.replace(":", "-")
    relative = Path("assets") / "formula-renders" / f"{safe_id}.png"
    destination = output_dir / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    with mpl.rc_context(
        {
            "font.family": "DejaVu Sans",
            "mathtext.fontset": "dejavusans",
            "savefig.transparent": True,
        }
    ):
        figure = Figure(figsize=(12, 1.4), dpi=144)
        figure.text(0.01, 0.5, f"${latex}$", va="center", fontsize=18)
        figure.savefig(
            destination,
            format="png",
            dpi=144,
            bbox_inches="tight",
            pad_inches=0.08,
            transparent=True,
            metadata={"Software": "matplotlib formula gate"},
        )
    if not destination.is_file() or destination.stat().st_size == 0:
        raise RuntimeError(f"formula render is missing: {destination}")
    return relative.as_posix()


def validate_equation_record(
    record: dict[str, Any],
    *,
    output_dir: Path,
) -> dict[str, Any]:
    """Attach compile evidence and render independently reviewed formulas."""

    latex = str(record.get("latex") or "")
    compile_status, mathml_sha256, error = compile_to_mathml(latex)
    record["latex_compile_status"] = compile_status
    record["mathml_sha256"] = mathml_sha256
    record["latex_compile_error"] = error
    if record["verification_status"] == "verified" and compile_status == "passed":
        record["representation_status"] = "latex_and_source_image"
        try:
            record["render_asset"] = render_reviewed_formula(
                latex, output_dir, str(record["equation_id"])
            )
        except Exception as exc:  # renderer exceptions are part of quality evidence
            record["render_validation_status"] = "failed"
            record["render_validation_error"] = f"{type(exc).__name__}: {exc}"
        else:
            record["render_validation_status"] = "passed"
            record["render_validation_error"] = None
            record["source_comparison_status"] = "manual_review_pass"
    elif compile_status == "passed":
        record["representation_status"] = "latex_and_source_image"
        record["render_validation_status"] = "not_required_unverified"
        record["render_validation_error"] = None
        record["source_comparison_status"] = "not_reviewed"
    else:
        if record["verification_status"] == "verified":
            record["representation_status"] = "failed"
            record["render_validation_status"] = "failed"
            record["render_validation_error"] = error
            record["source_comparison_status"] = "not_reviewed"
        else:
            record["latex_candidate"] = record["latex"]
            record["latex"] = None
            record["latex_candidate_compile_status"] = "failed"
            record["representation_status"] = "source_image_fallback"
            record["render_validation_status"] = "source_image_fallback"
            record["render_validation_error"] = error
            record["source_comparison_status"] = "not_reviewed"
    return record
