"""Deterministic charts and self-contained HTML research report."""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .curve import ZeroCurve


def create_charts(
    chart_dir: Path,
    selected_curve: ZeroCurve,
    baseline_curve: ZeroCurve,
    advanced_curve: ZeroCurve,
    repricing: pd.DataFrame,
    comparison: dict[str, object],
) -> list[Path]:
    chart_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 120, "axes.grid": True, "grid.alpha": 0.25, "font.size": 9})
    grid = np.linspace(1.0 / 12.0, 30.0, 721)
    paths: list[Path] = []

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.plot(grid, 100 * np.asarray(baseline_curve.zero(grid)), label="Baseline PCHIP", lw=1.5)
    ax.plot(grid, 100 * np.asarray(advanced_curve.zero(grid)), label="Robust smooth spline", lw=2.0)
    ax.set(title="Continuously Compounded Zero Curves", xlabel="Maturity (years)", ylabel="Zero rate (%)")
    ax.legend()
    fig.tight_layout()
    path = chart_dir / "curve.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    ax.plot(grid, 100 * np.asarray(selected_curve.forward(grid)), color="#cc5500", lw=1.8, label="Instantaneous forward")
    ax.plot(grid, 100 * np.asarray(selected_curve.zero(grid)), color="#1f77b4", lw=1.2, alpha=0.8, label="Zero rate")
    ax.axhline(0.0, color="black", lw=0.7)
    ax.set(title="Selected Curve: Forward and Zero Rates", xlabel="Maturity (years)", ylabel="Rate (%)")
    ax.legend()
    fig.tight_layout()
    path = chart_dir / "forward_rate.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(path)

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.3))
    rate_rows = repricing[repricing["instrument_type"] != "bond"]
    for instrument_type, group in rate_rows.groupby("instrument_type"):
        axes[0].scatter(group["maturity_years"], 10_000 * group["residual"], s=20, alpha=0.75, label=instrument_type)
    axes[0].axhline(0.0, color="black", lw=0.7)
    axes[0].set_yscale("symlog", linthresh=5.0)
    axes[0].set(title="Rate-instrument residuals", xlabel="Maturity (years)", ylabel="Model - market (bp)")
    axes[0].legend()
    bonds = repricing[repricing["instrument_type"] == "bond"]
    axes[1].scatter(bonds["maturity_years"], bonds["residual"], s=22, alpha=0.75, color="#2ca02c")
    axes[1].axhline(0.0, color="black", lw=0.7)
    axes[1].set_yscale("symlog", linthresh=0.10)
    axes[1].set(title="Bond residuals", xlabel="Maturity (years)", ylabel="Model - market (price points)")
    fig.tight_layout()
    path = chart_dir / "repricing.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(path)

    labels = ["Train", "Holdout"]
    baseline = [
        comparison["baseline"]["train"]["weighted_normalized_rmse"],
        comparison["baseline"]["holdout"]["weighted_normalized_rmse"],
    ]
    advanced = [
        comparison["advanced"]["train"]["weighted_normalized_rmse"],
        comparison["advanced"]["holdout"]["weighted_normalized_rmse"],
    ]
    x = np.arange(2)
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.bar(x - 0.18, baseline, 0.36, label="Baseline")
    ax.bar(x + 0.18, advanced, 0.36, label="Advanced")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Spread-normalized weighted RMSE")
    ax.set_title("Visible Maturity-block Validation")
    ax.legend()
    fig.tight_layout()
    path = chart_dir / "model_comparison.png"
    fig.savefig(path)
    plt.close(fig)
    paths.append(path)
    return paths


def _image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _mapping_table(mapping: dict[str, object]) -> str:
    rows = []
    for key, value in mapping.items():
        if isinstance(value, float):
            shown = f"{value:.6g}"
        else:
            shown = html.escape(str(value))
        rows.append(f"<tr><th>{html.escape(str(key))}</th><td>{shown}</td></tr>")
    return "<table>" + "".join(rows) + "</table>"


def build_html_report(
    report_path: Path,
    valuation_date: str,
    comparison: dict[str, object],
    sensitivity: dict[str, object],
    validation: dict[str, object],
    cleaning: pd.DataFrame,
    repricing: pd.DataFrame,
    chart_paths: list[Path],
    config_summary: dict[str, object],
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    action_counts = cleaning["action"].value_counts().to_dict()
    selected = str(comparison["selected_model"])
    baseline_holdout = float(comparison["baseline"]["holdout"]["weighted_normalized_rmse"])
    advanced_holdout = float(comparison["advanced"]["holdout"]["weighted_normalized_rmse"])
    improvement = 100.0 * (baseline_holdout - advanced_holdout) / max(baseline_holdout, 1e-12)
    if improvement >= 0:
        holdout_comparison = f"improved by {improvement:.2f}%"
    else:
        holdout_comparison = f"worsened by {abs(improvement):.2f}%"
    worst = repricing.assign(abs_standardized=lambda x: x["standardized_residual"].abs()).nlargest(8, "abs_standardized")
    worst_rows = "".join(
        f"<tr><td>{html.escape(str(r.instrument_id))}</td><td>{html.escape(str(r.instrument_type))}</td>"
        f"<td>{r.maturity_years:.3f}</td><td>{r.residual:.6g}</td><td>{r.weight:.4f}</td></tr>"
        for r in worst.itertuples()
    )
    images = "".join(
        f"<figure><img src=\"{_image_data_uri(path)}\" alt=\"{html.escape(path.stem)}\"><figcaption>{html.escape(path.stem.replace('_', ' ').title())}</figcaption></figure>"
        for path in chart_paths
    )
    sensitivity_json = html.escape(json.dumps(sensitivity, indent=2, sort_keys=True))
    validation_json = html.escape(json.dumps(validation, indent=2, sort_keys=True))
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zero-Curve Research Report</title>
<style>
body{{font-family:Arial,sans-serif;max-width:1050px;margin:28px auto;padding:0 22px;color:#1f2933;line-height:1.48}}
h1,h2{{color:#123b5d}} .callout{{background:#eef6fb;border-left:5px solid #2779a7;padding:12px 16px}}
table{{border-collapse:collapse;width:100%;margin:10px 0 20px}}th,td{{border:1px solid #cad4dc;padding:7px;text-align:left}}th{{background:#edf2f5}}
.charts{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}figure{{margin:0}}img{{width:100%;border:1px solid #d4dce2}}figcaption{{text-align:center;color:#52606d}}
pre{{background:#f5f7f8;padding:12px;overflow:auto;font-size:12px}}code{{font-family:Menlo,monospace}} .small{{font-size:0.9em;color:#52606d}}
@media(max-width:760px){{.charts{{grid-template-columns:1fr}}}}
</style></head><body>
<h1>USD Zero-Curve Research Report</h1>
<p class="small">Valuation date: {html.escape(valuation_date)}. Rates are continuously compounded annual decimals unless shown as percent or basis points.</p>

<h2>Executive summary</h2>
<div class="callout"><strong>Selected model: {html.escape(selected)}.</strong> The advanced model's visible holdout spread-normalized RMSE {holdout_comparison} versus the baseline. Selection required at least a 2% holdout improvement plus numerical guardrails; complexity alone was not sufficient. {html.escape(str(comparison['selection_rationale']))}</div>

<h2>Methodology</h2>
<p>The baseline converts each usable deposit, OIS swap, or bond to a standalone flat continuously compounded yield, aggregates yields by half-year maturity bucket using liquidity/spread weights, and applies shape-preserving PCHIP interpolation. The advanced estimator fits natural-cubic zero-rate knots directly to all documented instrument pricing equations. Its objective uses bid/ask-derived residual scales, liquidity weights, an integrated zero-curve curvature penalty, and iterative Huber residual weights. Discount factors are <code>exp(-z(T)T)</code>, which guarantees positivity without imposing monotonicity and therefore permits negative rates.</p>
{_mapping_table(config_summary)}
<p>The visible holdout is assigned by deterministic half-year maturity blocks. All instruments in a block are kept together, preventing same-maturity duplicates or near duplicates from leaking between train and holdout samples.</p>

<h2>Data-quality findings</h2>
{_mapping_table({str(k): int(v) for k, v in action_counts.items()})}
<p>Every input row appears in <code>outputs/diagnostics/cleaning.csv</code>. Unit conversions, midpoint substitutions, bid/ask inversions, stale observations, duplicates, low-liquidity rows, exclusions, and robust outlier weights are explicit. No problematic row was silently removed.</p>

<h2>Baseline-versus-advanced model comparison</h2>
<table><tr><th>Model</th><th>Train normalized RMSE</th><th>Holdout normalized RMSE</th></tr>
<tr><td>Baseline</td><td>{comparison['baseline']['train']['weighted_normalized_rmse']:.6g}</td><td>{baseline_holdout:.6g}</td></tr>
<tr><td>Advanced</td><td>{comparison['advanced']['train']['weighted_normalized_rmse']:.6g}</td><td>{advanced_holdout:.6g}</td></tr></table>

<h2>Sensitivity analysis</h2>
<p>Checks cover smoothing strength, robust threshold, deterministic 10% observation removal, and removal of liquidity/spread weighting. Curve deltas are computed on a dense 0–30Y grid against the final advanced fit.</p>
<pre>{sensitivity_json}</pre>

<h2>Validation and repricing</h2>
<pre>{validation_json}</pre>
<table><tr><th>Instrument</th><th>Type</th><th>Maturity</th><th>Residual</th><th>Final weight</th></tr>{worst_rows}</table>

<h2>Key charts</h2><div class="charts">{images}</div>

<h2>Limitations</h2>
<ul><li>Cash-flow dates use the authoritative year fractions and regular schedules because calendar/holiday rules and instrument effective dates are not supplied.</li>
<li>Flat-zero extrapolation outside the fitted domain is stable but makes long-end forward-rate risk dependent on the final knot.</li>
<li>Visible holdout errors remain in-sample research evidence from one valuation date; they are not a multi-date backtest.</li>
<li>Robust downweighting protects the curve but does not prove that a flagged quote is erroneous; the audit should be reviewed by a market-data owner.</li></ul>

<h2>Recommended next steps</h2>
<ol><li>Add instrument effective dates, business-day calendars, payment dates, and accrued interest for production valuation.</li>
<li>Backtest knot and smoothing choices over multiple dates and stressed negative-rate regimes.</li>
<li>Reconcile corrected units and stale/outlier flags against source-system metadata before trading or valuation use.</li>
<li>Validate portfolio-level hedge P&amp;L against realized curve moves and instrument-specific spread risk.</li></ol>
</body></html>"""
    report_path.write_text(document, encoding="utf-8")
