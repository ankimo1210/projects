"""Shared 26-section narrative registry and notebook construction utilities.

The executable notebook builders are implemented alongside the final notebook
task; the registry lives here from the outset so the report and notebook cannot
silently diverge in reading order.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter

from rough_volatility.config import load_config


@dataclass(frozen=True)
class Section:
    """One shared report/notebook section."""

    anchor: str
    title: str
    figure_key: str | None = None


SECTIONS: tuple[Section, ...] = (
    Section("executive-summary", "Technical summary"),
    Section("conceptual-map", "From rough paths to option skew and order flow"),
    Section("mathematical-definitions", "Definitions and scaling laws"),
    Section("configuration", "Scope, synthetic data, and configuration"),
    Section(
        "fbm-path-comparison", "Lower H changes local texture, not simply volatility", "fbm_paths"
    ),
    Section("local-zoom", "Roughness remains visible under a local zoom", "fbm_zoom"),
    Section("fgn-increments", "Rough increments alternate sharply", "fgn_increments"),
    Section(
        "increment-acf", "Short-lag increments become anti-persistent below H=1/2", "increment_acf"
    ),
    Section(
        "structure-functions",
        "Structure-function slopes recover the H ordering",
        "structure_scaling",
    ),
    Section("hurst-recovery", "Finite samples disperse H estimates", "hurst_distributions"),
    Section(
        "estimator-bias", "Longer samples reduce, but do not erase, estimator bias", "hurst_bias"
    ),
    Section("ou-versus-fou", "Rough log-volatility differs locally from ordinary OU", "ou_vs_fou"),
    Section(
        "rough-bergomi-paths",
        "Rough Bergomi creates abrupt variance dynamics",
        "model_spot_variance",
    ),
    Section(
        "heston-comparison",
        "The Markovian benchmark responds differently to shared shocks",
        "heston_comparison",
    ),
    Section(
        "terminal-distributions",
        "Model dynamics change return and realized-variance distributions",
        "terminal_distributions",
    ),
    Section("iv-smiles", "Smile shape varies jointly with model and maturity", "iv_smiles"),
    Section(
        "iv-surface",
        "The implied-volatility surface concentrates structure at short maturities",
        "iv_surface",
    ),
    Section("atm-skew-term", "Smaller H produces stronger short-maturity ATM skew", "skew_term"),
    Section(
        "skew-scaling",
        "Finite-maturity skew follows the predicted power-law direction",
        "skew_scaling",
    ),
    Section("hawkes-events", "Near-critical Hawkes flow clusters into bursts", "hawkes_events"),
    Section(
        "order-flow-price",
        "Signed event imbalance creates a clustered synthetic price",
        "hawkes_price",
    ),
    Section(
        "volatility-proxy", "Clustered flow creates a rough-looking RV proxy", "hawkes_intensity"
    ),
    Section("noise-bias", "Noise and sampling choices materially shift estimated H", "noise_bias"),
    Section("establishes", "What the experiments establish"),
    Section("does-not-establish", "What the experiments do not establish"),
    Section("limitations-next-steps", "Limitations, robustness, and next research steps"),
)


_NARRATIVE: dict[str, str] = {
    "executive-summary": "This notebook reproduces the complete synthetic rough-volatility lab. The central result is that clean rough-path scaling, normalized rough Bergomi variance, short-maturity skew, and clustered Hawkes activity can all be demonstrated together—while the noise experiment shows why an estimated $H<1/2$ is not identifying evidence by itself.",
    "conceptual-map": "The evidence chain is **rough paths → rough log-volatility → stochastic-volatility prices → implied-volatility skew**, with Hawkes order flow as a separate pedagogical route to a rough-looking proxy. Arrows organize experiments; they are not causal-identification claims.",
    "mathematical-definitions": r"""The core definitions are

$$\operatorname{Cov}(B_t^H,B_s^H)=\frac12\left(t^{2H}+s^{2H}-|t-s|^{2H}\right),$$

$$S_q(\Delta)=\mathbb E|X_{t+\Delta}-X_t|^q\propto\Delta^{qH},$$

$$V_t=\xi_0(t)\exp\left(\eta\widetilde W_t^H-\frac12\eta^2t^{2H}\right),$$

and $|\mathrm{ATM\ skew}(T)|\propto T^{H-1/2}$.""",
    "configuration": "All rows below are synthetic and generated locally from the resolved YAML profile. Monte Carlo path counts, maturity grids, Hurst replications, and event-process horizons are explicit so comparisons can be audited.",
    "fbm-path-comparison": "At a matched horizon scale, lower $H$ changes local regularity rather than merely increasing unconditional amplitude.",
    "local-zoom": "A local window isolates texture from the broad range of a path. The rough path continues to oscillate more sharply after zooming.",
    "fgn-increments": "Fractional Gaussian-noise increments make the fine-scale alternation visible directly.",
    "increment-acf": "For $H<1/2$, short-lag increments are anti-persistent even when process levels can look persistent.",
    "structure-functions": "The second-order log–log slope estimates $2H$. Only bounded log-spaced lags are used to avoid the noisiest long-lag tail.",
    "hurst-recovery": "Estimator distributions remain dispersed in finite samples, including on perfectly clean synthetic fBM.",
    "estimator-bias": "Bias and RMSE depend on the estimator, true $H$, and sample length. This is the clean-data baseline for the later noise study.",
    "ou-versus-fou": "Ordinary and fractional OU log-volatility are matched in broad scale but differ sharply in local regularity. The fOU Euler path is visualization-grade, not an exact stationary sampler.",
    "rough-bergomi-paths": r"The exact-grid joint-Gaussian Volterra operator preserves $\mathbb E[V_t]=\xi_0(t)$ up to Monte Carlo error and produces abrupt variance paths.",
    "heston-comparison": "Both models reuse the same standardized spot-driver normals. Remaining differences therefore reflect dynamics rather than a lucky shock draw; parameter matching is broad, not calibrated equivalence.",
    "terminal-distributions": "Terminal returns and realized variance summarize consequences of the path dynamics on common density scales.",
    "iv-smiles": "Short-maturity wings have the largest Monte Carlo uncertainty. Error bars should be read before interpreting visual differences.",
    "iv-surface": "The heatmap view exposes where smile curvature and skew concentrate across log-moneyness and maturity.",
    "atm-skew-term": "Weighted local-quadratic fits estimate the ATM derivative and propagate IV uncertainty.",
    "skew-scaling": "The fitted finite-maturity exponent is compared with $H-1/2$ as a directional diagnostic, not an exact asymptotic proof.",
    "hawkes-events": "Rate-matched Poisson, stable, and near-critical Hawkes scenarios separate unconditional activity from self-exciting clustering.",
    "order-flow-price": "Signed order imbalance creates a simple synthetic price. It is deliberately pedagogical rather than a structural impact model.",
    "volatility-proxy": "Intensity bursts and rolling squared returns form a rough-looking proxy. Its effective H is labeled as an empirical diagnostic only.",
    "noise-bias": "The same latent paths yield different H estimates after changing observation noise, sampling stride, and preprocessing.",
    "establishes": "The experiments establish numerical scaling on clean simulations, forward-variance normalization, common-random-number model comparisons, finite-maturity skew direction, and the sufficiency of self-excitation for clustered proxies.",
    "does-not-establish": "They do not identify a fractional real-world data-generating process, calibrate either volatility model, derive rough Heston from Hawkes flow, or prove asymptotic skew exactly.",
    "limitations-next-steps": "Next steps should emphasize robustness: calibrated forward variance, hybrid/FFT convergence checks, variance reduction for short-wing IV, noise-robust H estimators, and seasonality-aware Hawkes estimation. Further questions include sensitivity to leverage, vol-of-vol, grid design, and asynchronous sampling.",
}

_STATIC_FIGURES: dict[str, tuple[str, ...]] = {
    "fbm_paths": ("fbm_paths",),
    "fbm_zoom": ("fbm_zoom",),
    "fgn_increments": ("fgn_increments",),
    "increment_acf": ("increment_acf",),
    "structure_scaling": ("structure_scaling",),
    "hurst_distributions": ("hurst_distributions",),
    "hurst_bias": ("hurst_bias",),
    "ou_vs_fou": ("ou_vs_fou", "ou_volatility"),
    "model_spot_variance": ("model_spot", "model_variance"),
    "heston_comparison": ("model_spot",),
    "terminal_distributions": ("terminal_returns", "realized_variance"),
    "iv_smiles": ("iv_smiles",),
    "iv_surface": ("iv_surface",),
    "skew_term": ("skew_term",),
    "skew_scaling": ("skew_scaling",),
    "hawkes_events": ("hawkes_events",),
    "hawkes_price": ("hawkes_price_rv",),
    "hawkes_intensity": ("hawkes_intensity", "hawkes_counts"),
    "noise_bias": ("noise_bias",),
}


def _initial_cell(project_root: Path, config_path: Path) -> str:
    try:
        config_reference = config_path.relative_to(project_root)
        config_expression = f"project_root / Path({str(config_reference)!r})"
    except ValueError:
        config_expression = f"Path({str(config_path)!r})"
    return f"""from pathlib import Path
import json
import numpy as np
import pandas as pd
from IPython.display import Image, Markdown, display

from rough_volatility.config import load_config
from rough_volatility.experiments import load_artifact_manifest, run_all
from rough_volatility.plotting import CHART_CONTRACTS, generate_static_figures

project_root = Path.cwd().resolve()
config_path = {config_expression}
config = load_config(config_path)
np.random.seed(config.seed)
try:
    manifest = load_artifact_manifest(config, project_root)
except (FileNotFoundError, ValueError):
    manifest = run_all(config, project_root, force=False)

figure_dir = project_root / config.output.artifacts_dir / 'figures'
if not all((figure_dir / f'{{name}}.png').exists() for name in CHART_CONTRACTS):
    generate_static_figures(config, project_root, manifest)

validation = json.loads(manifest['validation_checks'].read_text(encoding='utf-8'))
skew_power = pd.read_csv(manifest['skew_power_law'])
hurst_summary = pd.read_csv(manifest['hurst_summary'])
hawkes_summary = pd.read_csv(manifest['hawkes_summary'])
print(f"profile={{config.profile}} seed={{config.seed}} fingerprint={{config.fingerprint()}}")
print(f"validation_all_passed={{validation['checks']['all_passed']}}")
"""


def _figure_cell(names: tuple[str, ...]) -> str:
    quoted = repr(list(names))
    return f"""for figure_name in {quoted}:
    path = figure_dir / f"{{figure_name}}.png"
    display(Image(filename=str(path)))
"""


def _table_cell(anchor: str) -> str | None:
    cells = {
        "executive-summary": "display(skew_power[['h', 'beta', 'theoretical_beta', 'h_implied', 'r_squared', 'ok']])",
        "configuration": "display(pd.json_normalize(config.to_dict(), sep='.').T.rename(columns={0: 'resolved value'}))",
        "hurst-recovery": "display(hurst_summary[['true_h', 'sample_size', 'estimator', 'mean_h_hat', 'bias', 'rmse', 'coverage']])",
        "atm-skew-term": "display(skew_power[['h', 'beta', 'beta_se', 'theoretical_beta', 'beta_error', 'r_squared']])",
        "hawkes-events": "display(hawkes_summary[['scenario', 'branching_ratio', 'event_count', 'expected_event_count', 'truncated']])",
        "establishes": "display(pd.DataFrame(validation['checks']).T)",
    }
    return cells.get(anchor)


def build_notebook(root: str | Path, config_path: str | Path) -> Path:
    """Build the 26-section notebook without executing it."""
    project_root = Path(root).resolve()
    resolved_config = Path(config_path)
    if not resolved_config.is_absolute():
        resolved_config = (project_root / resolved_config).resolve()
    config = load_config(resolved_config)
    output = project_root / config.output.notebook_path
    output.parent.mkdir(parents=True, exist_ok=True)

    cells = [nbformat.v4.new_code_cell(_initial_cell(project_root, resolved_config))]
    for index, section in enumerate(SECTIONS, start=1):
        markdown = (
            f'<a id="{section.anchor}"></a>\n\n'
            f"## {index}. {section.title}\n\n"
            f"{_NARRATIVE[section.anchor]}"
        )
        cells.append(nbformat.v4.new_markdown_cell(markdown))
        table_cell = _table_cell(section.anchor)
        if table_cell is not None:
            cells.append(nbformat.v4.new_code_cell(table_cell))
        if section.figure_key is not None:
            cells.append(
                nbformat.v4.new_code_cell(_figure_cell(_STATIC_FIGURES[section.figure_key]))
            )
    notebook = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
            "rough_volatility": {
                "profile": config.profile,
                "seed": config.seed,
                "fingerprint": config.fingerprint(),
                "section_count": len(SECTIONS),
            },
        },
    )
    nbformat.write(notebook, output)
    return output


def execute_and_export_notebook(
    root: str | Path,
    config_path: str | Path,
    *,
    timeout: int = 1800,
) -> tuple[Path, Path]:
    """Build, execute in-place, and export the notebook to HTML."""
    project_root = Path(root).resolve()
    notebook_path = build_notebook(project_root, config_path)
    notebook = nbformat.read(notebook_path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(project_root)}},
        allow_errors=False,
    )
    executed = client.execute()
    nbformat.write(executed, notebook_path)

    config = load_config(config_path)
    exporter = HTMLExporter()
    exporter.exclude_input_prompt = True
    exporter.exclude_output_prompt = True
    body, _ = exporter.from_notebook_node(
        executed, resources={"metadata": {"path": str(project_root)}}
    )
    html_path = project_root / config.output.reports_dir / f"{notebook_path.stem}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(body, encoding="utf-8")
    return notebook_path, html_path
