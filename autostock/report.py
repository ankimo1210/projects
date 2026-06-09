"""
autostock HTML report — a single self-contained report.html summarizing the
research run: best-strategy metrics, the experiment leaderboard (results.tsv),
the charts (reused from plot.py, embedded as base64), the annual Sharpe
breakdown, and the integrity methodology / honest caveats.

Self-contained: no CDN, no JS, no extra deps — opens in any browser.
Regenerable tooling that imports the read-only engine.

Run:
    uv run report.py                  # lockbox withheld
    uv run report.py --reveal-lockbox  # include the lockbox segment
"""

import argparse
import base64
import html
import io
import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

import plot  # noqa: E402
import prepare  # noqa: E402
import strategy  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(__file__), "report.html")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "results.tsv")

CSS = """
:root{--ink:#0f172a;--muted:#64748b;--bg:#f8fafc;--card:#fff;--line:#e2e8f0;
--accent:#2563eb;--pos:#16a34a;--neg:#dc2626}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);line-height:1.5;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px 64px}
header.top{background:var(--ink);color:#fff;padding:36px 0}
h1{margin:0 0 6px;font-size:26px;letter-spacing:-.02em}
.sub{color:#cbd5e1;font-size:14px}
.meta{margin-top:18px;display:flex;flex-wrap:wrap;gap:8px}
.meta span{background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.18);
border-radius:999px;padding:4px 11px;font-size:12px}
h2{font-size:14px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);
margin:42px 0 14px;border-bottom:1px solid var(--line);padding-bottom:8px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 16px;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.card-label{font-size:12px;color:var(--muted)}
.card-value{font-size:24px;font-weight:650;margin:2px 0;
font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.card-note{font-size:11px;color:var(--muted)}
table.grid{width:100%;border-collapse:collapse;background:var(--card);
border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:13px}
.grid th{text-align:left;background:#f1f5f9;color:var(--muted);font-weight:600;
padding:9px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
.grid td{padding:9px 12px;border-top:1px solid var(--line)}
.grid td.num{text-align:right}
.grid tr.keep td:first-child{box-shadow:inset 3px 0 0 var(--pos)}
.grid tr.winner{background:#f0fdf4}
.badge{font-size:11px;padding:2px 8px;border-radius:999px;font-weight:600}
.badge.keep{background:#dcfce7;color:#166534}
.badge.discard{background:#f1f5f9;color:#64748b}
.badge.crash{background:#fee2e2;color:#991b1b}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{border:1px solid var(--line);border-radius:10px;padding:6px 10px;
text-align:center;min-width:62px;background:var(--card)}
.chip-y{font-size:11px;color:var(--muted)}
.chip-v{font-weight:650}
.chip.pos .chip-v{color:var(--pos)}
.chip.neg .chip-v{color:var(--neg)}
.chart{width:100%;border:1px solid var(--line);border-radius:12px;
background:var(--card);padding:10px}
.chart img{width:100%;display:block}
ul.method{padding-left:18px}
ul.method li{margin:7px 0;font-size:14px}
.note{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;
padding:14px 16px;font-size:13px;color:#713f12}
.muted{color:var(--muted)}
footer{margin-top:48px;color:var(--muted);font-size:12px;
border-top:1px solid var(--line);padding-top:16px}
code{background:#f1f5f9;padding:1px 5px;border-radius:5px;font-size:.92em;
font-family:ui-monospace,monospace}
"""


def _fmt(x, nd=3):
    try:
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return html.escape(str(x))


def _fig_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def _cards_html(m):
    cards = [
        ("OOS test Sharpe", _fmt(m["sharpe"]), "headline metric — higher is better"),
        ("Train Sharpe", _fmt(m["train_sharpe"]), "in-sample; large gap vs test = overfit"),
        ("Ann. return", _fmt(m["ann_return"]), "test period, annualized"),
        ("Ann. vol", _fmt(m["ann_vol"]), "test period, annualized"),
        ("Max drawdown", _fmt(m["max_drawdown"]), "test period"),
        ("Turnover", _fmt(m["turnover"]), "avg daily, test period"),
        ("Rolling Sharpe (mean)", _fmt(m["roll_sharpe_mean"]),
         f"{prepare.ROLL_WINDOW}d windows in test"),
        ("Rolling Sharpe (min)", _fmt(m["roll_sharpe_min"]), "worst window = fragility"),
        ("Rolling Sharpe (pos %)", _fmt(m["roll_sharpe_pos_frac"]), "share of windows > 0"),
    ]
    if "lockbox_sharpe" in m:
        cards.insert(2, ("Lockbox Sharpe", _fmt(m["lockbox_sharpe"]),
                         "withheld holdout — revealed"))
    items = "".join(
        f'<div class="card"><div class="card-label">{html.escape(lbl)}</div>'
        f'<div class="card-value">{html.escape(val)}</div>'
        f'<div class="card-note">{html.escape(note)}</div></div>'
        for lbl, val, note in cards
    )
    return f'<div class="cards">{items}</div>'


def _leaderboard_html():
    import pandas as pd

    if not os.path.exists(RESULTS_PATH):
        return ('<p class="muted">No <code>results.tsv</code> yet — run experiments '
                "to populate the leaderboard.</p>")
    df = pd.read_csv(RESULTS_PATH, sep="\t")
    best = df["sharpe"].max()
    body = []
    for _, r in df.iterrows():
        status = str(r["status"])
        win = " winner" if float(r["sharpe"]) == best else ""
        body.append(
            f'<tr class="{status}{win}">'
            f'<td class="mono">{html.escape(str(r["commit"]))}</td>'
            f'<td class="num mono">{_fmt(r["sharpe"])}</td>'
            f'<td class="num mono">{_fmt(r["train_sharpe"])}</td>'
            f'<td class="num mono">{_fmt(r["max_dd"])}</td>'
            f'<td class="num mono">{_fmt(r["turnover"])}</td>'
            f'<td><span class="badge {status}">{html.escape(status)}</span></td>'
            f'<td>{html.escape(str(r["description"]))}</td></tr>'
        )
    head = ("<tr><th>commit</th><th>OOS Sharpe</th><th>train</th><th>max DD</th>"
            "<th>turnover</th><th>status</th><th>description</th></tr>")
    return (f'<table class="grid"><thead>{head}</thead>'
            f'<tbody>{"".join(body)}</tbody></table>')


def _annual_html(m):
    chips = []
    for y in sorted(m["annual_sharpe"]):
        v = m["annual_sharpe"][y]
        sign = "pos" if v >= 0 else "neg"
        chips.append(f'<div class="chip {sign}"><div class="chip-y">{y}</div>'
                     f'<div class="chip-v mono">{_fmt(v, 2)}</div></div>')
    return f'<div class="chips">{"".join(chips)}</div>'


def _winner_desc():
    import pandas as pd

    if not os.path.exists(RESULTS_PATH):
        return "current strategy.py"
    df = pd.read_csv(RESULTS_PATH, sep="\t")
    return str(df.loc[df["sharpe"].idxmax(), "description"])


def build_report(prices, reveal_lockbox=False, generated=None):
    """Return a self-contained HTML report string for the current strategy."""
    weights = strategy.generate_weights(prices)
    m = prepare.evaluate(weights, prices, reveal_lockbox=reveal_lockbox)

    fig = plot.build_figure(prices, reveal_lockbox=reveal_lockbox)
    img_b64 = _fig_base64(fig)
    plt.close(fig)

    generated = generated or datetime.now().strftime("%Y-%m-%d %H:%M")
    meta = [
        f"Universe: {', '.join(prepare.UNIVERSE)}",
        f"Cost: {prepare.COST_BPS:g} bps/turnover",
        f"Gross ≤ {prepare.MAX_GROSS:g}, name ≤ {prepare.MAX_NAME:g}",
        f"Train: {prepare.START_DATE} .. {prepare.TRAIN_END}",
        f"Test: {prepare.TEST_START} .. {prepare.TEST_END}",
        f"Lockbox: {prepare.LOCKBOX_START} → ({'revealed' if reveal_lockbox else 'withheld'})",
        f"Generated: {generated}",
    ]
    meta_html = "".join(f"<span>{html.escape(s)}</span>" for s in meta)

    method = [
        "<b>1-day execution lag</b> — weights decided at the close of day <code>t</code> "
        "are held from <code>t+1</code>, so a signal built from day-<code>t</code> data "
        "cannot capture day-<code>t</code>'s return (no same-day-close lookahead).",
        f"<b>Transaction costs</b> — {prepare.COST_BPS:g} bps charged on turnover "
        "(Σ|Δw|); churn is penalized automatically.",
        f"<b>Leverage caps</b> — gross Σ|w| ≤ {prepare.MAX_GROSS:g}, per-name "
        f"|w| ≤ {prepare.MAX_NAME:g}; enforced by the engine, not the strategy.",
        "<b>Missing-asset handling</b> — pre-IPO names (e.g. META before 2012-05) get "
        "weight 0 and the rest renormalize; blocks NaN-mediated lookahead.",
        "<b>Held-out segments</b> — the headline Sharpe is measured only on the "
        f"out-of-sample <b>test</b> window ({prepare.TEST_START}..{prepare.TEST_END}); the "
        f"<b>lockbox</b> ({prepare.LOCKBOX_START}→) is withheld until an explicit reveal.",
        "<b>Read-only metric</b> — <code>prepare.py</code> is never edited by the loop; "
        "the agent only edits <code>strategy.py</code>'s <code>generate_weights</code>.",
    ]
    method_html = "".join(f"<li>{s}</li>" for s in method)

    caveats = [
        "The Magnificent-7 is a hand-picked set of <b>survivors</b>, so absolute Sharpe "
        "levels are optimistic — this is not deployable alpha.",
        "A high test Sharpe with a large <b>train→test gap</b> or a deeply negative "
        "worst rolling window is fragile/regime-fit; read the rolling and annual panels.",
        "The lockbox <b>bounds</b> multiple-testing overfit accumulated across many "
        "experiments, but does not eliminate it.",
        "The point of the demo is the <b>autonomous search loop + cheat-proof metric</b>, "
        "ported from Karpathy's autoresearch.",
    ]
    caveats_html = "".join(f"<li>{c}</li>" for c in caveats)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>autostock — research report</title>
<style>{CSS}</style></head>
<body>
<header class="top"><div class="wrap">
<h1>autostock — research report</h1>
<div class="sub">Autonomous Mag-7 strategy search (autoresearch port) · metric = out-of-sample test Sharpe</div>
<div class="meta">{meta_html}</div>
</div></header>
<div class="wrap">
<h2>Best strategy — {html.escape(_winner_desc())}</h2>
{_cards_html(m)}
<h2>Charts</h2>
<div class="chart"><img alt="autostock charts" src="data:image/png;base64,{img_b64}"></div>
<h2>Experiment leaderboard</h2>
{_leaderboard_html()}
<h2>Annual Sharpe (visible window)</h2>
{_annual_html(m)}
<h2>Methodology &amp; integrity</h2>
<ul class="method">{method_html}</ul>
<h2>Caveats (read honestly)</h2>
<div class="note"><ul class="method">{caveats_html}</ul></div>
<footer>Generated by <code>uv run report.py</code> · regenerate anytime ·
charts reuse <code>plot.build_figure</code> · metric defined in read-only <code>prepare.py</code>.</footer>
</div></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reveal-lockbox", action="store_true")
    args = ap.parse_args()

    prices = prepare.load_prices()
    out = build_report(prices, reveal_lockbox=args.reveal_lockbox)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"wrote {OUT_PATH}  ({len(out):,} bytes)")


if __name__ == "__main__":
    main()
