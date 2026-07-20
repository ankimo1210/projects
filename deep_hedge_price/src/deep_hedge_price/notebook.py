"""Programmatic construction, execution, and export of the educational notebook."""

from __future__ import annotations

from pathlib import Path


def build_notebook(project_root: str | Path) -> Path:
    """Build the notebook with nbformat so raw JSON is never hand-maintained."""
    import nbformat as nbf

    root = Path(project_root)
    output = root / "notebooks" / "01_deep_hedging_european_call.ipynb"
    output.parent.mkdir(parents=True, exist_ok=True)
    cells = [
        nbf.v4.new_markdown_cell(
            "# Deep Hedging a European Call\n\n"
            "A reproducible Phase 1 demonstration of dynamic hedging under proportional transaction costs. "
            "All reported P&L is discounted, after costs, and includes the initial reporting premium."
        ),
        nbf.v4.new_code_cell(
            "from pathlib import Path\n"
            "import json\nimport numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt\n"
            "from IPython.display import Markdown, display\n"
            "from deep_hedge_price.config import load_config\n"
            "from deep_hedge_price.experiments import load_artifact_manifest\n"
            "from deep_hedge_price.plotting import *\n"
            "from deep_hedge_price.policy import architecture_rows\n"
            "from deep_hedge_price.training import checkpoint_directory, load_policy\n"
            "project_root = Path.cwd()\n"
            "config = load_config(project_root / 'configs' / 'quick.yaml')\n"
            "manifest = load_artifact_manifest(config, project_root)\n"
            "summary_payload = json.loads(manifest['summary_metrics'].read_text())\n"
            "sanity = json.loads(manifest['sanity_checks'].read_text())\n"
            "main_results = pd.read_csv(manifest['main_path_results'])\n"
            "strategy_summary = pd.read_csv(manifest['strategy_summary'], index_col=0)\n"
            "sensitivity = pd.read_csv(manifest['sensitivity_summary'])\n"
            "risk_comparison = pd.read_csv(manifest['risk_objective_summary'])\n"
            "policy_surface = pd.read_csv(manifest['policy_surface'])\n"
            "trade_scatter = pd.read_csv(manifest['trade_scatter'])\n"
            "print(f'Loaded {len(main_results):,} path-strategy rows from config {config.fingerprint()}')"
        ),
        nbf.v4.new_markdown_cell("## Executive summary"),
        nbf.v4.new_code_cell(
            "n = strategy_summary.loc['neural_mse']\n"
            "nh = strategy_summary.loc['no_hedge']\n"
            "reduction = 1 - n['std_discounted_pnl_after_costs_including_premium'] / nh['std_discounted_pnl_after_costs_including_premium']\n"
            "warnings = [name for name, value in sanity.items() if isinstance(value, dict) and not value.get('passed', True)]\n"
            "display(Markdown(f'''- **Out-of-sample comparison:** {config.training.test_paths:,} common paths.\n"
            "- **Dispersion:** neural hedging changed P&L standard deviation by {reduction:.1%} relative to no hedge.\n"
            "- **Tail loss:** neural 99% CVaR loss is {n['cvar_loss_99']:.3f}.\n"
            "- **Sanity checks:** {'all passed' if not warnings else 'warnings: ' + ', '.join(warnings)}.\n\n"
            "Claims below follow the generated metrics; a warning is treated as a limitation, not hidden.'''))"
        ),
        nbf.v4.new_markdown_cell(
            "## Financial setup and sign convention\n\n"
            "Under the physical measure, $S_{t+\\Delta t}=S_t\\exp[(\\mu-\\sigma^2/2)\\Delta t+\\sigma\\sqrt{\\Delta t}Z_t]$. "
            "For a short call, discounted loss excluding premium is\n\n"
            "$$L_T=\\widetilde H-\\sum_t\\delta_t(\\widetilde S_{t+1}-\\widetilde S_t)+"
            "\\sum_t e^{-rt}\\lambda S_t|\\delta_t-\\delta_{t-1}|.$$\n\n"
            "Economic P&L is the Black–Scholes premium minus this loss. The initial position is zero and the specified convention has no terminal liquidation charge."
        ),
        nbf.v4.new_markdown_cell("### Differentiable training path"),
        nbf.v4.new_code_cell("show_figure(training_diagram())"),
        nbf.v4.new_markdown_cell("## Configuration"),
        nbf.v4.new_code_cell(
            "config_rows = []\n"
            "for section, values in config.to_dict().items():\n"
            "    if isinstance(values, dict):\n"
            "        config_rows.extend({'section': section, 'parameter': k, 'value': v} for k, v in values.items())\n"
            "display(pd.DataFrame(config_rows).head(40))"
        ),
        nbf.v4.new_markdown_cell("## Market simulation and payoff"),
        nbf.v4.new_code_cell("show_figure(sample_paths_figure(config))"),
        nbf.v4.new_code_cell("show_figure(payoff_figure(config))"),
        nbf.v4.new_markdown_cell("## Neural-policy architecture"),
        nbf.v4.new_code_cell(
            "model_config = config.with_risk(objective='mse')\n"
            "policy, _ = load_policy(model_config, checkpoint_directory(model_config, project_root) / 'best.pt', device='cpu')\n"
            "display(pd.DataFrame(architecture_rows(policy)))\n"
            "print(f'Total trainable parameters: {policy.parameter_count:,}')"
        ),
        nbf.v4.new_markdown_cell("## End-to-end training history"),
        nbf.v4.new_code_cell(
            "history = pd.read_csv(checkpoint_directory(model_config, project_root) / 'history.csv')\n"
            "show_figure(training_history_figure(history))"
        ),
        nbf.v4.new_markdown_cell("## Main comparison on common test paths"),
        nbf.v4.new_code_cell(
            "comparison_columns = ['mean_discounted_pnl_after_costs_including_premium', 'std_discounted_pnl_after_costs_including_premium', 'rmse_discounted_hedging_error', 'cvar_loss_99', 'average_turnover_shares', 'average_discounted_transaction_cost']\n"
            "display(strategy_summary[comparison_columns].round(4))"
        ),
        nbf.v4.new_markdown_cell("### P&L distributions"),
        nbf.v4.new_code_cell("show_figure(pnl_distribution_figure(main_results))"),
        nbf.v4.new_markdown_cell("### Empirical CDF and lower tail"),
        nbf.v4.new_code_cell("show_figure(ecdf_figure(main_results))"),
        nbf.v4.new_markdown_cell("### VaR and CVaR"),
        nbf.v4.new_code_cell("show_figure(var_cvar_figure(strategy_summary))"),
        nbf.v4.new_markdown_cell("### Turnover and transaction cost"),
        nbf.v4.new_code_cell("show_figure(turnover_cost_figure(strategy_summary))"),
        nbf.v4.new_markdown_cell(
            "## Policy surface\nThe following slice fixes the previous position at 0.5 shares."
        ),
        nbf.v4.new_code_cell("show_figure(policy_heatmap_figure(policy_surface))"),
        nbf.v4.new_markdown_cell("### Neural minus Black–Scholes delta"),
        nbf.v4.new_code_cell("show_figure(policy_heatmap_figure(policy_surface, difference=True))"),
        nbf.v4.new_markdown_cell("### Policy slices at several maturities"),
        nbf.v4.new_code_cell("show_figure(policy_slices_figure(policy_surface))"),
        nbf.v4.new_markdown_cell("### Trade size conditional on prior position and BS target"),
        nbf.v4.new_code_cell("show_figure(trade_scatter_figure(trade_scatter))"),
        nbf.v4.new_markdown_cell("## Transaction-cost sensitivity"),
        nbf.v4.new_code_cell(
            "display(sensitivity.round(4)); show_figure(sensitivity_figure(sensitivity))"
        ),
        nbf.v4.new_markdown_cell("## Risk-objective comparison"),
        nbf.v4.new_code_cell(
            "display(risk_comparison.round(4)); show_figure(risk_objective_figure(risk_comparison))"
        ),
        nbf.v4.new_markdown_cell("## Sanity checks and limitations"),
        nbf.v4.new_code_cell(
            "check_rows = [{'check': k, 'passed': v.get('passed'), 'details': str({x:y for x,y in v.items() if x != 'passed'})} for k,v in sanity.items() if isinstance(v, dict)]\n"
            "display(pd.DataFrame(check_rows))"
        ),
        nbf.v4.new_markdown_cell(
            "Constant-volatility GBM omits jumps, stochastic volatility, liquidity state, and model risk. "
            "Quick-profile tail estimates are intentionally labeled less stable than the full profile. "
            "No claim of superiority is made when its supporting sanity check fails."
        ),
        nbf.v4.new_markdown_cell(
            "## Phase 2 roadmap — Deep Pricing\n\n"
            "Next, build a separately validated Black–Scholes/Monte Carlo label pipeline, then price-and-Greeks surrogates, differential learning, "
            "arbitrage-aware penalties, calibration tests, and inference-speed benchmarks. The executable specification is in `docs/ROADMAP_DEEP_PRICING.md`; "
            "Phase 2 code is deliberately out of scope here."
        ),
    ]
    notebook = nbf.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
    )
    nbf.write(notebook, output)
    return output


def execute_and_export_notebook(project_root: str | Path) -> tuple[Path, Path]:
    """Rebuild, execute top-to-bottom, and export a self-contained HTML notebook."""
    import nbformat
    from nbclient import NotebookClient
    from nbconvert import HTMLExporter
    from nbconvert.writers import FilesWriter

    root = Path(project_root).resolve()
    notebook_path = build_notebook(root)
    notebook = nbformat.read(notebook_path, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=1800,
        kernel_name="python3",
        resources={"metadata": {"path": str(root)}},
    )
    executed = client.execute()
    nbformat.write(executed, notebook_path)
    exporter = HTMLExporter()
    exporter.exclude_input_prompt = True
    exporter.exclude_output_prompt = True
    body, resources = exporter.from_notebook_node(executed)
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    writer = FilesWriter(build_directory=str(reports))
    writer.write(body, resources, notebook_name="01_deep_hedging_european_call")
    html_path = reports / "01_deep_hedging_european_call.html"
    return notebook_path, html_path
