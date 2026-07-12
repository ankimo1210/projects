from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from deep_hedge_price.evaluation import summarize_all
from deep_hedge_price.notebook import build_notebook
from deep_hedge_price.report import build_standalone_report
from deep_hedge_price.training import checkpoint_directory


def _report_fixture(tiny_config, root: Path) -> dict[str, Path]:
    data = root / "artifacts" / "data"
    metrics = root / "artifacts" / "metrics"
    data.mkdir(parents=True)
    metrics.mkdir(parents=True)
    rng = np.random.default_rng(2)
    frames = []
    strategies = ["neural_mse", "black_scholes_delta", "black_scholes_band", "no_hedge"]
    for index, strategy in enumerate(strategies):
        pnl = rng.normal(0, 1 + index * 0.4, 200)
        frames.append(
            pd.DataFrame(
                {
                    "path_id": np.arange(200),
                    "strategy": strategy,
                    "discounted_payoff": rng.uniform(0, 10, 200),
                    "net_trading_gain": rng.normal(2, 1, 200),
                    "transaction_cost": 0.02 + index * 0.01,
                    "turnover_shares": 2 + index,
                    "meaningful_trades": 4 + index,
                    "terminal_delta": rng.uniform(0, 1, 200),
                    "discounted_pnl": pnl,
                }
            )
        )
    frame = pd.concat(frames, ignore_index=True)
    frame["gross_trading_gain"] = frame["net_trading_gain"] + frame["transaction_cost"]
    frame["loss_excluding_premium"] = -frame["discounted_pnl"] + 2
    frame["discounted_pnl_before_costs"] = frame["discounted_pnl"] + frame["transaction_cost"]
    main_path = data / "main.csv"
    frame.to_csv(main_path, index=False)
    summary = pd.DataFrame(summarize_all(frame)).T
    strategy_path = data / "summary.csv"
    summary.to_csv(strategy_path)
    sensitivity = pd.DataFrame(
        {
            "transaction_cost_bps": [0, 1, 5, 10, 25],
            "std_discounted_pnl_after_costs_including_premium": [1, 1.01, 1.03, 1.05, 1.1],
            "cvar_loss_99": [2.4, 2.42, 2.45, 2.5, 2.6],
            "average_turnover_shares": [4, 3.8, 3.4, 3.0, 2.5],
            "average_discounted_transaction_cost": [0, 0.01, 0.05, 0.09, 0.15],
            "policy_bs_rmse": [0.1, 0.11, 0.13, 0.15, 0.2],
        }
    )
    sensitivity_path = data / "sensitivity.csv"
    sensitivity.to_csv(sensitivity_path, index=False)
    risk = pd.DataFrame(
        {
            "objective": ["mse", "entropic"],
            "std_discounted_pnl_after_costs_including_premium": [1, 1.05],
            "cvar_loss_99": [2.4, 2.2],
            "average_turnover_shares": [3.4, 3.2],
        }
    )
    risk_path = data / "risk.csv"
    risk.to_csv(risk_path, index=False)
    spots = np.tile(np.linspace(80, 120, 8), 6)
    taus = np.repeat(np.linspace(0.05, 1, 6), 8)
    surface = pd.DataFrame(
        {
            "spot": spots,
            "tau_normalized": taus,
            "neural_delta": np.clip((spots - 80) / 40, 0, 1),
            "difference": np.sin(spots) * 0.02,
        }
    )
    surface_path = data / "surface.csv"
    surface.to_csv(surface_path, index=False)
    sanity_path = metrics / "sanity.json"
    sanity_path.write_text(json.dumps({"check": {"passed": True}}))
    history_dir = checkpoint_directory(tiny_config.with_risk(objective="mse"), root)
    history_dir.mkdir(parents=True)
    pd.DataFrame(
        {
            "epoch": [0, 1, 2],
            "train_objective": [np.nan, 2.0, 1.5],
            "validation_objective": [2.2, 1.9, 1.6],
        }
    ).to_csv(history_dir / "history.csv", index=False)
    return {
        "main_path_results": main_path,
        "strategy_summary": strategy_path,
        "sensitivity_summary": sensitivity_path,
        "risk_objective_summary": risk_path,
        "policy_surface": surface_path,
        "sanity_checks": sanity_path,
    }


def test_html_report_is_self_contained_and_has_expected_sections(tiny_config, tmp_path):
    manifest = _report_fixture(tiny_config, tmp_path)
    output = build_standalone_report(tiny_config, tmp_path, manifest)
    html = output.read_text(encoding="utf-8")
    assert output.exists() and output.stat().st_size > 1_000_000
    assert 'src="https://cdn.plot.ly' not in html
    assert "Plotly.newPlot" in html
    assert html.count('class="plotly-graph-div"') == 8
    assert "setLanguage('ja')" in html
    assert "日本語" in html and "English" in html
    assert "技術サマリー" in html and "リスク目的関数の比較" in html
    for heading in (
        "Technical summary",
        "Main strategy comparison",
        "Transaction costs change trading behavior",
        "Risk-objective comparison",
        "Limitations and uncertainty",
        "Reproduce and extend",
    ):
        assert heading in html


def test_notebook_builder_contains_required_reader_sections(tmp_path):
    import nbformat

    notebook_path = build_notebook(tmp_path)
    notebook = nbformat.read(notebook_path, as_version=4)
    markdown = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "markdown")
    for heading in (
        "Executive summary",
        "Financial setup",
        "Main comparison",
        "Policy surface",
        "Transaction-cost sensitivity",
        "Risk-objective comparison",
        "Phase 2 roadmap",
    ):
        assert heading in markdown
