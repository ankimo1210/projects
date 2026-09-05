"""Self-contained local HTML reporting for a curve run."""

from __future__ import annotations

import base64
import html
from pathlib import Path

import numpy as np
import pandas as pd


def _image_data(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _metric_line(name: str, metrics: dict[str, object]) -> str:
    return (
        f"<tr><td>{html.escape(name)}</td><td>{metrics['n']}</td>"
        f"<td>{float(metrics['weighted_normalized_rmse']):.4f}</td>"
        f"<td>{float(metrics['median_abs_standardized_error']):.4f}</td></tr>"
    )


def render_report(
    path: Path,
    valuation_date: str,
    raw: pd.DataFrame,
    audit: pd.DataFrame,
    comparison: dict[str, object],
    sensitivity: dict[str, object],
    repricing: pd.DataFrame,
    risk: pd.DataFrame,
    chart_paths: list[Path],
) -> None:
    """Create an intentionally dependency-free report that opens locally."""
    actions = audit["action"].value_counts().to_dict()
    selected = str(comparison["selected_model"])
    baseline = comparison["baseline"]
    advanced = comparison["advanced"]
    assert isinstance(baseline, dict) and isinstance(advanced, dict)
    base_train, base_hold = baseline["train"], baseline["holdout"]
    adv_train, adv_hold = advanced["train"], advanced["holdout"]
    assert all(isinstance(x, dict) for x in (base_train, base_hold, adv_train, adv_hold))
    residual_summary = repricing.groupby("instrument_type")["residual"].agg(["count", "mean", "std", "max", "min"]).round(8).to_html(classes="compact", border=0)
    risk_gap = float(np.max(np.abs(risk["key_sum_minus_dv01"]))) if len(risk) else float("nan")
    sensitivity_rows = "".join(
        f"<tr><td>{html.escape(str(item['name']))}</td><td>{int(item.get('observations_removed', 0))}</td>"
        f"<td>{float(item['max_zero_rate_change_bp']):.3f}</td></tr>"
        for item in sensitivity["checks"]
    )
    images = "".join(
        f'<figure><img src="{_image_data(image)}" alt="{html.escape(image.stem)}"><figcaption>{html.escape(image.stem.replace("_", " ").title())}</figcaption></figure>'
        for image in chart_paths
    )
    weak_points = [
        "Visible market data contain only one valuation-date cross-section; no independent time-series backtest is available.",
        "The 30Y endpoint is constrained by sparse liquid evidence, so forward rates near the boundary remain extrapolation-sensitive.",
        "The model uses synthetic ACT/365F maturity fractions and simplified stub handling; production systems need full calendar, holiday, and settlement engines.",
    ]
    html_text = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>QuantCurve research report</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:1100px;margin:32px auto;padding:0 20px;color:#1f2933;line-height:1.5}}
h1,h2{{color:#12395b}} .note{{background:#edf6fb;padding:14px;border-left:4px solid #246b99}}
table{{border-collapse:collapse;width:100%;margin:12px 0}} th,td{{border:1px solid #d9e2ec;padding:7px;text-align:left}} th{{background:#f0f4f8}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:14px}} figure{{margin:0;border:1px solid #d9e2ec;padding:8px}} img{{width:100%;height:auto}} figcaption{{font-size:.9em;color:#52606d}}
code{{background:#f0f4f8;padding:2px 4px}} .small{{font-size:.92em;color:#52606d}}
</style></head><body>
<h1>USD continuously compounded zero-curve research report</h1>
<p class="small">Valuation date: {html.escape(valuation_date)} · Deterministic workflow · Rates reported as annual decimals unless stated otherwise.</p>
<h2>Executive summary</h2>
<div class="note"><strong>Selected model: {html.escape(selected)}.</strong> {html.escape(str(comparison['selection_rationale']))}
The curve is fitted in log-discount-factor space, which preserves strictly positive discount factors while allowing negative zero and forward rates.</div>
<p>Of {len(raw)} supplied observations, {len(audit) - int(actions.get('exclude', 0))} were usable after validation. The audit recorded {int(actions.get('correct', 0))} corrections, {int(actions.get('downweight', 0))} downweights, and {int(actions.get('exclude', 0))} exclusions.</p>
<h2>Methodology</h2>
<p>The baseline is a piecewise-linear log-discount curve. The advanced estimator uses a natural cubic log-discount spline and penalises changes in implied instantaneous forwards. Both price deposits by their documented simple-rate identity, OIS swaps by fixed-leg annuity equality, and bonds from level coupon cash flows plus principal. Quote residuals are scaled by type-specific floors and bid/ask-liquidity quality weights. The advanced fit applies three deterministic Huber-style IRLS rounds. Regularisation is selected as the smoothest tested strength within 1% of the best advanced holdout error.</p>
<p>Validation is maturity-aware: every fifth ordered maturity bucket is held out as a complete group, preventing same-maturity observations from crossing train and validation sets. It measures interpolation performance rather than claiming a random-sample result.</p>
<h2>Data-quality findings</h2>
<p>Schema, timestamp, unit, range, bid/ask, missing-quote, and duplicate checks are performed before calibration. Rate quotes are converted from percentage points to decimals; bond prices remain points per 100. Quotes outside a valid bid/ask interval are replaced with its midpoint and the decision is retained in <code>cleaning.csv</code>. Stale quotes are retained only with reduced quality weight; duplicates retain the fresher observation.</p>
<table><tr><th>Action</th><th>Count</th></tr>{''.join(f'<tr><td>{html.escape(str(k))}</td><td>{int(v)}</td></tr>' for k,v in sorted(actions.items()))}</table>
<h2>Baseline versus advanced validation</h2>
<table><tr><th>Model / sample</th><th>N</th><th>Weighted normalized RMSE</th><th>Median absolute standardized error</th></tr>
{_metric_line('Baseline / train', base_train)}{_metric_line('Baseline / holdout', base_hold)}{_metric_line('Advanced / train', adv_train)}{_metric_line('Advanced / holdout', adv_hold)}</table>
<p>Holdout maturity buckets: {', '.join(f'{float(x):g}Y' for x in comparison['holdout_maturity_years'])}.</p>
<h2>Curve and repricing diagnostics</h2><div class="grid">{images}</div>
<h3>Residual summary</h3>{residual_summary}
<h2>Sensitivity analysis and risk checks</h2>
<p>All sensitivities use a central ±1 bp zero-rate shift. Key-rate bumps are triangular/linear partition-of-unity shapes around 2Y, 5Y, 10Y, and 30Y; therefore their sum represents the parallel shift at all cash-flow dates. The maximum finite-difference key-sum gap is {risk_gap:.6g} currency units.</p>
<table><tr><th>Refit check</th><th>Observations removed</th><th>Maximum zero-rate change (bp)</th></tr>{sensitivity_rows}</table>
<h2>Limitations, model risk, and recommended next steps</h2>
<ul>{''.join(f'<li>{html.escape(item)}</li>' for item in weak_points)}</ul>
<p>Recommended next steps: independently validate instrument calendars and payment schedules, add historical cross-validation and stressed bid/ask scenarios, then apply governance limits to long-end forward and key-rate risk before using the curve for trading or valuation.</p>
</body></html>"""
    path.write_text(html_text, encoding="utf-8")
