"""Execute the source notebook and export the required offline HTML."""

from __future__ import annotations

import json
import os
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

from .config import Config
from .provenance import PROJECT_ROOT, artifact_dirs, provenance


def execute_notebook(cfg: Config, config_path: str | Path) -> Path:
    paths = artifact_dirs(cfg)
    required = (
        paths["metrics"] / "classical_strategy_summary.csv",
        paths["metrics"] / "lob_strategy_summary.csv",
        paths["metrics"] / "stress_summary.csv",
    )
    if not all(path.exists() for path in required):
        from .experiments import run_all
        from .report import build_reports

        run_all(cfg)
        build_reports(cfg)

    source = PROJECT_ROOT / "notebooks" / "01_optimal_execution_visual_lab.ipynb"
    if not source.exists():
        raise FileNotFoundError(source)
    executed_dir = PROJECT_ROOT / "notebooks" / "_executed"
    executed_dir.mkdir(parents=True, exist_ok=True)
    executed_path = executed_dir / source.name

    notebook = nbformat.read(source, as_version=4)
    notebook.metadata["optimal_execution"] = provenance(cfg, model_parameters=cfg.raw)
    old_config = os.environ.get("OPTIMAL_EXECUTION_CONFIG")
    os.environ["OPTIMAL_EXECUTION_CONFIG"] = str(Path(config_path).resolve())
    try:
        client = NotebookClient(
            notebook,
            timeout=600,
            kernel_name="python3",
            resources={"metadata": {"path": str(PROJECT_ROOT)}},
            allow_errors=False,
        )
        executed = client.execute()
    finally:
        if old_config is None:
            os.environ.pop("OPTIMAL_EXECUTION_CONFIG", None)
        else:
            os.environ["OPTIMAL_EXECUTION_CONFIG"] = old_config
    nbformat.write(executed, executed_path)

    exporter = HTMLExporter(template_name="lab")
    exporter.exclude_input_prompt = True
    exporter.exclude_output_prompt = True
    if hasattr(exporter, "mathjax_url"):
        exporter.mathjax_url = ""
    if hasattr(exporter, "require_js_url"):
        exporter.require_js_url = ""
    body, _ = exporter.from_notebook_node(executed)
    # The lab template includes dormant Mermaid module URLs even when the
    # notebook has no Mermaid cells.  Its script returns before importing in
    # that case; neutralise the fallback strings for strict offline scanning.
    body = body.replace("https://cdnjs.cloudflare.com/", "data:,")
    notebook_provenance = json.dumps(
        provenance(cfg, model_parameters=cfg.raw),
        ensure_ascii=False,
        sort_keys=True,
    )
    body = body.replace(
        "</head>",
        f'<script type="application/json" id="notebook-provenance">{notebook_provenance}</script></head>',
        1,
    )
    output = paths["reports"] / "01_optimal_execution_visual_lab.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    _validate_notebook_html(output)
    return output


def _validate_notebook_html(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if path.stat().st_size < 50_000:
        raise ValueError(f"notebook HTML unexpectedly small: {path}")
    if "Optimal Execution Visual Lab" not in text:
        raise ValueError(f"notebook title missing in {path}")
    if "Traceback (most recent call last)" in text:
        raise ValueError(f"executed notebook contains a traceback: {path}")
    forbidden = ("cdn.plot.ly", "https://cdn.jsdelivr", "https://cdnjs.cloudflare")
    if any(token in text for token in forbidden):
        raise ValueError(f"external CDN reference found in notebook HTML: {path}")
