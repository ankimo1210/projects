"""Execute the source notebook and export the required offline HTML."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

from .config import Config
from .provenance import PROJECT_ROOT, artifact_dirs, provenance

# Display ($$...$$) then inline ($...$) LaTeX. The inline pattern is anchored on
# non-'$' boundaries so the greedy display pass never leaves a stray delimiter.
_DISPLAY_MATH = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
_INLINE_MATH = re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL)


def _render_math(markdown: str) -> str:
    """Convert LaTeX math in a markdown cell to inline, self-contained MathML.

    Runs at build time so the exported HTML needs no MathJax/KaTeX, no web
    fonts, and no network — the offline-report invariant. Raises on malformed
    LaTeX so a broken formula fails the build loudly instead of shipping raw
    dollar signs.
    """
    if "$" not in markdown:
        return markdown
    from latex2mathml.converter import convert

    def _display(match: re.Match[str]) -> str:
        return convert(match.group(1).strip(), display="block")

    def _inline(match: re.Match[str]) -> str:
        return convert(match.group(1).strip(), display="inline")

    return _INLINE_MATH.sub(_inline, _DISPLAY_MATH.sub(_display, markdown))


# One entry per localized edition of the visual-lab notebook. The code cells are
# identical across editions (identical figures/data); only markdown and the
# setup caption are translated, so both HTML reports share the same numbers.
NOTEBOOK_LOCALES: dict[str, dict[str, str]] = {
    "en": {
        "source": "01_optimal_execution_visual_lab.ipynb",
        "output": "01_optimal_execution_visual_lab.html",
        "title_token": "Optimal Execution Visual Lab",
    },
    "ja": {
        "source": "01_optimal_execution_visual_lab.ja.ipynb",
        "output": "01_optimal_execution_visual_lab_ja.html",
        "title_token": "最適執行ビジュアルラボ",
    },
}


def _ensure_inputs(cfg: Config) -> None:
    from .report import _artifact_frames

    try:
        _artifact_frames(cfg)
    except (FileNotFoundError, ValueError):
        from .experiments import run_all
        from .report import build_reports

        run_all(cfg)
        build_reports(cfg)


def execute_notebook(cfg: Config, config_path: str | Path, locale: str = "en") -> Path:
    if locale not in NOTEBOOK_LOCALES:
        raise ValueError(
            f"unsupported notebook locale {locale!r}; choose from {sorted(NOTEBOOK_LOCALES)}"
        )
    spec = NOTEBOOK_LOCALES[locale]
    _ensure_inputs(cfg)
    paths = artifact_dirs(cfg)

    source = PROJECT_ROOT / "notebooks" / spec["source"]
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

    # Typeset LaTeX ($…$, $$…$$) to inline MathML for the HTML export only; the
    # saved .ipynb keeps clean LaTeX sources.
    for cell in executed.cells:
        if cell.cell_type == "markdown":
            cell.source = _render_math(cell.source)

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
    output = paths["reports"] / spec["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(body, encoding="utf-8")
    _validate_notebook_html(output, spec["title_token"])
    return output


def execute_notebooks(cfg: Config, config_path: str | Path) -> dict[str, Path]:
    """Execute every localized visual-lab edition; returns {locale: html path}."""
    return {locale: execute_notebook(cfg, config_path, locale) for locale in NOTEBOOK_LOCALES}


def _validate_notebook_html(path: Path, title_token: str) -> None:
    text = path.read_text(encoding="utf-8")
    if path.stat().st_size < 50_000:
        raise ValueError(f"notebook HTML unexpectedly small: {path}")
    if title_token not in text:
        raise ValueError(f"notebook title missing in {path}")
    if "Traceback (most recent call last)" in text:
        raise ValueError(f"executed notebook contains a traceback: {path}")
    forbidden = ("cdn.plot.ly", "https://cdn.jsdelivr", "https://cdnjs.cloudflare")
    if any(token in text for token in forbidden):
        raise ValueError(f"external CDN reference found in notebook HTML: {path}")
