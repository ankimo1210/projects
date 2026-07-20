"""Artifact-only Notebook 02 builder."""

from __future__ import annotations

import json
import os
from pathlib import Path
from textwrap import dedent

REFERENCE_RELATIVE_TO_WORKSPACE = Path(
    "johnhull/volumes/18_ml_surrogates/reference/pricing_metrics.json"
)


def default_pricing_reference(project_root: str | Path) -> Path:
    """Return the tracked johnhull candidate beside the deep pricing project."""
    return Path(project_root).resolve().parent / REFERENCE_RELATIVE_TO_WORKSPACE


def build_pricing_notebook(
    project_root: str | Path,
    reference_metrics_path: str | Path | None = None,
):
    """Build a reader notebook that never trains, downloads, or detects a GPU."""
    import nbformat as nbf

    root = Path(project_root).resolve()
    metrics_path = (
        default_pricing_reference(root)
        if reference_metrics_path is None
        else Path(reference_metrics_path).resolve()
    )
    if not metrics_path.is_file():
        raise FileNotFoundError(f"missing tracked pricing reference: {metrics_path}")
    relative = Path(os.path.relpath(metrics_path, root))

    def code(source: str) -> str:
        return dedent(source).strip()

    relative_literal = json.dumps(str(relative))
    cells = [
        nbf.v4.new_markdown_cell(
            "# Neural Pricing Surrogates & Greeks\n\n"
            "Phase 2 reads the committed johnhull JSON/NPZ reference only; this notebook "
            "never starts training."
        ),
        nbf.v4.new_markdown_cell("## Data policy and artifact fingerprint"),
        nbf.v4.new_code_cell(
            code(
                f"""
                import hashlib
                import json
                from pathlib import Path

                import numpy as np

                root = Path.cwd()
                metrics_path = (
                    root / {relative_literal}
                ).resolve()
                reference = json.loads(metrics_path.read_text(encoding="utf-8"))
                companion_name = "pricing_slices.npz"
                arrays_path = metrics_path.parent / companion_name
                expected_sha256 = reference["companions"][companion_name]
                actual_sha256 = hashlib.sha256(arrays_path.read_bytes()).hexdigest()
                if actual_sha256 != expected_sha256:
                    raise ValueError("pricing_slices.npz hash does not match pricing_metrics.json")
                with np.load(arrays_path, allow_pickle=False) as payload:
                    slices = {{name: payload[name] for name in payload.files}}
                expected_arrays = set(reference["companion_schemas"][companion_name])
                if set(slices) != expected_arrays:
                    raise ValueError("pricing_slices.npz arrays do not match the committed schema")
                metrics = reference["metrics"]
                reference["engine_evidence"]["dataset_split_fingerprints"]
                """
            )
        ),
        nbf.v4.new_markdown_cell(
            "## Dimensionless Black–Scholes reference\n\n"
            "Inputs are `x = S/K`, `τ = T`, `r`, `q`, and `σ`; output is `C/K`."
        ),
        nbf.v4.new_code_cell(
            code(
                """
                {
                    "moneyness_range": (slices["moneyness"].min(), slices["moneyness"].max()),
                    "maturity_range": (slices["maturity"].min(), slices["maturity"].max()),
                }
                """
            )
        ),
        nbf.v4.new_markdown_cell("## Split and OOD audit"),
        nbf.v4.new_code_cell(
            code(
                """
                {
                    "split_overlap_count": metrics["split_overlap_count"],
                    "fingerprints": reference["engine_evidence"]["dataset_split_fingerprints"],
                    "ood_claim": reference["limitations"][1],
                }
                """
            )
        ),
        nbf.v4.new_markdown_cell("## Neural price and Greek diagnostics"),
        nbf.v4.new_code_cell(
            code(
                """
                {
                    "price_mae_normalized": metrics["price_mae_normalized"],
                    "delta_mae": metrics["delta_mae"],
                    "slice_price_error_max": slices["price_error"].max(),
                    "slice_delta_error_mean": slices["delta_error"].mean(),
                    "slice_gamma_error_mean": slices["gamma_error"].mean(),
                }
                """
            )
        ),
        nbf.v4.new_markdown_cell(
            "## Differential ML and residual correction\n\nLoss weights are checkpointed. A negative result retains the simpler price-only baseline."
        ),
        nbf.v4.new_code_cell(
            code(
                """
                {
                    "dml_improved_a_greek_without_price_degradation": metrics[
                        "dml_improved_a_greek_without_price_degradation"
                    ],
                    "heston_raw_price_mae": metrics["heston_raw_price_mae"],
                    "heston_bsm_residual_mae": metrics["heston_bsm_residual_mae"],
                }
                """
            )
        ),
        nbf.v4.new_markdown_cell("## Hard arbitrage diagnostics"),
        nbf.v4.new_code_cell(
            code(
                """
                {
                    "hard_violation_rate": metrics["hard_violation_rate"],
                    "acceptance": reference["engine_evidence"]["acceptance"],
                    "violations": dict(
                        zip(
                            slices["check_names"].tolist(),
                            slices["violations_constrained"].tolist(),
                            strict=True,
                        )
                    ),
                }
                """
            )
        ),
        nbf.v4.new_markdown_cell(
            "## Heston/COS and Monte Carlo teacher uncertainty\n\nTeacher discrepancies must be interpreted beside standard errors and confidence intervals."
        ),
        nbf.v4.new_code_cell(
            code(
                """
                {
                    "teacher_ci_coverage_20_seeds": metrics.get(
                        "teacher_ci_coverage_20_seeds_by_estimand",
                        {"price": metrics["teacher_ci_coverage_20_seeds"]},
                    ),
                    "teacher_se_ratio_4x_paths": metrics.get(
                        "teacher_se_ratio_4x_paths_by_estimand",
                        {"price": metrics["teacher_se_ratio_4x_paths"]},
                    ),
                }
                """
            )
        ),
        nbf.v4.new_markdown_cell("## Calibration and CPU break-even"),
        nbf.v4.new_code_cell(
            code(
                """
                {
                    "batch_size": slices["batch_size"],
                    "analytic_us": slices["analytic_us"],
                    "mlp_us": slices["mlp_us"],
                    "break_even_batch": metrics["break_even_batch"],
                    "calibration_note": "The committed quick reference does not claim calibration coverage.",
                }
                """
            )
        ),
        nbf.v4.new_markdown_cell(
            "## Limitations / negative results / research track\n\nSynthetic accuracy is not market predictive power. Failed acceptance checks remain visible in the report."
        ),
        nbf.v4.new_code_cell('reference["limitations"]'),
    ]
    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
    )
    output = root / "notebooks" / "02_neural_pricing_surrogate.ipynb"
    output.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, output)
    return output


def execute_pricing_notebook(
    project_root: str | Path,
    reference_metrics_path: str | Path | None = None,
):
    """Execute Notebook 02 against the tracked JSON/NPZ and export local HTML."""
    from tempfile import TemporaryDirectory

    import nbformat
    from jupyter_client import KernelManager
    from nbclient import NotebookClient
    from nbconvert import HTMLExporter
    from nbconvert.writers import FilesWriter

    root = Path(project_root).resolve()
    notebook_path = build_pricing_notebook(root, reference_metrics_path)
    notebook = nbformat.read(notebook_path, as_version=4)
    # On WSL, jupyter_core can otherwise inherit Windows' TEMP directory and
    # reject its connection file because NTFS cannot expose mode 0o600.
    with TemporaryDirectory(prefix="pricing-kernel-", dir="/tmp") as runtime_dir:
        kernel_manager = KernelManager(
            kernel_name="python3",
            connection_file=str(Path(runtime_dir) / "kernel.json"),
        )
        executed = NotebookClient(
            notebook,
            km=kernel_manager,
            timeout=300,
            kernel_name="python3",
            resources={"metadata": {"path": str(root)}},
        ).execute(cleanup_kc=True)
    nbformat.write(executed, notebook_path)
    exporter = HTMLExporter()
    exporter.exclude_input_prompt = True
    exporter.exclude_output_prompt = True
    exporter.mathjax_url = ""
    exporter.require_js_url = ""
    exporter.jupyter_widgets_base_url = ""
    body, resources = exporter.from_notebook_node(executed)
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    FilesWriter(build_directory=str(reports)).write(
        body, resources, notebook_name="02_neural_pricing_surrogate"
    )
    return notebook_path, reports / "02_neural_pricing_surrogate.html"
