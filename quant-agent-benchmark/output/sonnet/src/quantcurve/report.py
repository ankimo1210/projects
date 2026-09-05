"""Self-contained HTML research report (no external assets or network calls)."""

from __future__ import annotations

import base64
import html
from pathlib import Path

_CSS = """
:root {
  --bg: #f7f8fa; --panel: #ffffff; --ink: #1c2430; --muted: #5c6673;
  --border: #e2e6ec; --accent: #5b7ea6; --accent-2: #c65d3b; --good: #3f8f5f; --warn: #b9862d;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  line-height: 1.55; }
.wrap { max-width: 980px; margin: 0 auto; padding: 2.5rem 1.5rem 5rem; }
header.hero { padding: 2.2rem 0 1.4rem; border-bottom: 1px solid var(--border); margin-bottom: 2rem; }
header.hero h1 { font-size: 1.7rem; margin: 0 0 0.35rem; }
header.hero p.meta { color: var(--muted); margin: 0; font-size: 0.92rem; }
h2.section-title { font-size: 1.2rem; margin: 2.6rem 0 1rem; padding-top: 0.4rem;
  border-top: 1px solid var(--border); }
h3 { font-size: 1.0rem; margin: 1.4rem 0 0.6rem; }
p { color: #333d49; }
.panel { background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
  padding: 1.1rem 1.3rem; margin: 0.9rem 0; }
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.8rem; margin: 1rem 0; }
.kpi { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 0.9rem 1rem; }
.kpi .label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
.kpi .value { font-size: 1.35rem; font-weight: 600; margin-top: 0.15rem; }
.kpi .value.good { color: var(--good); }
.kpi .value.warn { color: var(--warn); }
table { width: 100%; border-collapse: collapse; font-size: 0.86rem; margin: 0.6rem 0 1.2rem; }
th, td { text-align: left; padding: 0.42rem 0.6rem; border-bottom: 1px solid var(--border); }
th { color: var(--muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.03em; }
tr:last-child td { border-bottom: none; }
code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.85em; }
.badge { display: inline-block; padding: 0.12rem 0.55rem; border-radius: 999px; font-size: 0.72rem;
  font-weight: 600; }
.badge.selected { background: #e4efe8; color: var(--good); }
.badge.other { background: #eceef1; color: var(--muted); }
figure { margin: 0.6rem 0 1.4rem; }
figure img { width: 100%; border-radius: 8px; border: 1px solid var(--border); display: block; }
figcaption { font-size: 0.8rem; color: var(--muted); margin-top: 0.4rem; }
ul.tight li { margin-bottom: 0.35rem; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1.4rem; }
@media (max-width: 720px) { .two-col { grid-template-columns: 1fr; } }
footer.note { color: var(--muted); font-size: 0.8rem; margin-top: 3rem; padding-top: 1rem;
  border-top: 1px solid var(--border); }
"""


def _img(b64: str) -> str:
    return f'<img src="data:image/png;base64,{b64}" alt="chart">'


def _fmt(x, digits=4, suffix="") -> str:
    if x is None:
        return "n/a"
    try:
        if isinstance(x, float) and (x != x):
            return "n/a"
        return f"{x:.{digits}f}{suffix}"
    except Exception:
        return html.escape(str(x))


def _kpi(label: str, value: str, cls: str = "") -> str:
    return f'<div class="kpi"><div class="label">{html.escape(label)}</div><div class="value {cls}">{value}</div></div>'


def _table(rows: list[dict], columns: list[tuple]) -> str:
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(row.get(key, '')))}</td>" for key, _ in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def render_report(ctx: dict, chart_files: dict[str, Path], out_path: Path) -> None:
    charts_b64 = {name: base64.b64encode(Path(p).read_bytes()).decode("ascii") for name, p in chart_files.items()}

    selected = ctx["model_selected"]
    base = ctx["comparison"]["baseline"]
    adv = ctx["comparison"]["advanced"]

    cleaning_rows = [
        {"Action": r["action"], "Count": r["count"]}
        for r in ctx["cleaning_summary_by_action"]
    ]
    cleaning_examples_rows = [
        {
            "obs_id": r["obs_id"], "instrument_id": r["instrument_id"], "action": r["action"],
            "reason": r["reason"],
        }
        for r in ctx["cleaning_examples"]
    ]

    sens = ctx["sensitivity"]
    bump = sens["bump_size_convergence"]
    leave_out = sens["leave_worst_out_refit"]
    neg_stress = sens["negative_rate_stress"]

    html_doc = f"""
<title>Zero-Curve Research Report</title>
<style>{_CSS}</style>
<div class="wrap">

<header class="hero">
  <h1>USD Zero-Curve Construction &amp; Validation</h1>
  <p class="meta">Valuation date {html.escape(ctx['valuation_date'])} &middot; generated {html.escape(ctx['generated_at'])}
  &middot; source: <code>{html.escape(ctx['market_data_name'])}</code></p>
</header>

<h2 class="section-title">1. Executive summary</h2>
<div class="kpi-grid">
  {_kpi("Observations", str(ctx['n_observations']))}
  {_kpi("Usable instruments", str(ctx['n_usable']))}
  {_kpi("Excluded", str(ctx['n_excluded']), 'warn' if ctx['n_excluded'] else '')}
  {_kpi("Model selected", selected.title(), 'good')}
  {_kpi("Baseline holdout wRMSE", _fmt(base['holdout_weighted_rmse'], 3))}
  {_kpi("Advanced holdout wRMSE", _fmt(adv['holdout_weighted_rmse'], 3))}
</div>
<p>{ctx['executive_summary']}</p>

<h2 class="section-title">2. Methodology</h2>
<p>{ctx['methodology_intro']}</p>
<div class="two-col">
  <div class="panel">
    <h3>Baseline model</h3>
    <p>{ctx['methodology_baseline']}</p>
  </div>
  <div class="panel">
    <h3>Advanced model</h3>
    <p>{ctx['methodology_advanced']}</p>
  </div>
</div>
<h3>Holdout methodology</h3>
<p>{ctx['holdout_methodology']}</p>

<h2 class="section-title">3. Data-quality findings</h2>
<p>{ctx['data_quality_intro']}</p>
{_table(cleaning_rows, [("Action", "Action"), ("Count", "Count")])}
<h3>Illustrative examples</h3>
{_table(cleaning_examples_rows, [("obs_id", "Obs ID"), ("instrument_id", "Instrument"), ("action", "Action"), ("reason", "Reason")])}

<h2 class="section-title">4. Baseline vs. advanced comparison</h2>
<figure>{_img(charts_b64['comparison'])}<figcaption>Left: weighted RMSE by model and split. Right: advanced-model holdout RMSE across the regularisation-strength grid searched during model selection.</figcaption></figure>
{_table([
    {"Model": "Baseline", "Train wRMSE": _fmt(base['train_weighted_rmse'],3), "Holdout wRMSE": _fmt(base['holdout_weighted_rmse'],3), "Selected": "yes" if selected=="baseline" else ""},
    {"Model": "Advanced", "Train wRMSE": _fmt(adv['train_weighted_rmse'],3), "Holdout wRMSE": _fmt(adv['holdout_weighted_rmse'],3), "Selected": "yes" if selected=="advanced" else ""},
], [("Model","Model"), ("Train wRMSE","Train wRMSE"), ("Holdout wRMSE","Holdout wRMSE"), ("Selected","Selected")])}
<p><strong>Selection rationale:</strong> {ctx['comparison']['selection_rationale']}</p>

<h2 class="section-title">5. Sensitivity analysis</h2>
<div class="two-col">
  <div class="panel">
    <h3>Finite-difference bump-size convergence</h3>
    <p>DV01 is defined as the PV move for a 1bp bump, so raw finite-difference values scale linearly with
    whatever bump size is used; each is rescaled to a common per-1bp basis before comparing. Mean |DV01|
    across a representative instrument sample, rescaled to per-1bp, at 10bp / 1bp / 0.1bp bump sizes:
    {_fmt(bump['mean_abs_dv01_by_bump_per_1bp']['bump_0.001'],2)} / {_fmt(bump['mean_abs_dv01_by_bump_per_1bp']['bump_0.0001'],2)} /
    {_fmt(bump['mean_abs_dv01_by_bump_per_1bp']['bump_1e-05'],2)} (USD/points per bp). Relative deviation vs. the 1bp
    reference: {_fmt(bump['relative_diff_10bp_vs_1bp']*100,2)}% (10bp), {_fmt(bump['relative_diff_0p1bp_vs_1bp']*100,2)}% (0.1bp).
    DV01 is stable across step sizes: <strong>{bump['stable']}</strong>.</p>
  </div>
  <div class="panel">
    <h3>Leave-worst-out refit</h3>
    <p>Removing the single largest-residual training instrument (<code>{html.escape(str(leave_out['removed_instrument_id']))}</code>)
    and refitting the baseline shifts the 2Y/5Y/10Y/30Y zero rates by at most
    <strong>{_fmt(leave_out['max_zero_rate_shift_bp'],2)} bp</strong> &mdash; curve is not overly sensitive to any single quote:
    <strong>{leave_out['stable']}</strong>.</p>
  </div>
</div>
<div class="panel">
  <h3>Negative-rate stress test</h3>
  <p>All deposit/swap quotes were parallel-shocked down by 3.00 percentage points and the baseline curve refit
  from scratch (requirement: negative zero/forward rates must be supported without discount factors falling to
  or below zero). Result: minimum zero rate on the output grid = <strong>{_fmt(neg_stress['min_zero_rate']*100,2)}%</strong>
  ({_fmt(neg_stress['fraction_of_grid_negative']*100,1)}% of the grid negative), minimum discount factor =
  <strong>{_fmt(neg_stress['min_discount_factor'],6)}</strong> (always &gt; 0: <strong>{neg_stress['all_discount_factors_positive']}</strong>).</p>
</div>

<h2 class="section-title">6. Validation &amp; repricing</h2>
<figure>{_img(charts_b64['repricing'])}<figcaption>Repricing residual (market minus model) by maturity and instrument type, for the selected model. Triangles are visible-holdout instruments (never used to calibrate this curve); circles are training instruments.</figcaption></figure>
<p>{ctx['validation_narrative']}</p>

<h2 class="section-title">7. Curves &amp; risk</h2>
<figure>{_img(charts_b64['curve'])}<figcaption>Fitted zero rate and discount factor, baseline vs. advanced, from the front end to 30Y.</figcaption></figure>
<figure>{_img(charts_b64['forward'])}<figcaption>Instantaneous forward rate: the baseline's piecewise-linear zero rate produces a kinked forward curve; the advanced spline is smooth by construction.</figcaption></figure>
<div class="kpi-grid">
  {_kpi("Instruments with computed risk", str(ctx['risk_summary']['n_instruments']))}
  {_kpi("Sum of DV01 (USD)", _fmt(ctx['risk_summary']['sum_dv01'], 2))}
  {_kpi("Sum of key-rate DV01s (USD)", _fmt(ctx['risk_summary']['sum_key_rates'], 2))}
  {_kpi("Parallel vs. key-rate sum gap", _fmt(ctx['risk_summary']['reconciliation_gap_pct'], 6, '%'))}
</div>

<h2 class="section-title">8. Limitations</h2>
<ul class="tight">
{''.join(f'<li>{html.escape(item)}</li>' for item in ctx['limitations'])}
</ul>

<h2 class="section-title">9. Recommended next steps</h2>
<ul class="tight">
{''.join(f'<li>{html.escape(item)}</li>' for item in ctx['next_steps'])}
</ul>

<footer class="note">Generated by <code>quantcurve</code> {html.escape(ctx.get('version',''))}. This report and all
referenced diagnostics are reproduced deterministically by <code>quantcurve.cli run</code>; see README.md.</footer>
</div>
"""
    out_path.write_text(html_doc, encoding="utf-8")
