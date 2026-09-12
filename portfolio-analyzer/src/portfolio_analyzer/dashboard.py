"""Render the trading-desk style P&L dashboard from a prepared, JSON-serialisable payload.

Layout, top to bottom: headline (NAV, day, window and inception P&L), general data
(allocation, attribution, every position with a 1-year sparkline), then the time series
(account NAV and P&L, per-symbol price and P&L). Python only lays out and embeds the
numbers; the charts are drawn client-side from the ``#data`` block so every point has a
hover readout. Colours come from the claude-report tokens (dark by default, toggle).
"""

from __future__ import annotations

import html
import json
from typing import Any


def _esc(text: Any) -> str:
    return html.escape(str(text), quote=True)


def jpy(value: float | int | None, sign: bool = False) -> str:
    if value is None:
        return "—"
    v = round(float(value))
    text = f"{abs(v):,}"
    if sign:
        return ("+" if v > 0 else "−" if v < 0 else "±") + text
    return ("−" if v < 0 else "") + text


def pct(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{float(value):+.{digits}f}%".replace("-", "−")


def price(value: float | None, cur: str) -> str:
    if value is None:
        return "—"
    v = float(value)
    return f"{v:,.2f}" if cur == "USD" or v < 100 else f"{v:,.1f}"


def cls(value: float | None) -> str:
    if value is None or float(value) == 0:
        return ""
    return "up" if float(value) > 0 else "dn"


def _kpi(label: str, value: str, sub: str, tone: str = "") -> str:
    return f'<div class="kpi"><span class="k">{_esc(label)}</span><span class="v {tone}">{value}</span><span class="s">{sub}</span></div>'


def _positions_table(rows: list[dict[str, Any]]) -> str:
    body = ""
    for r in rows:
        unreal = (
            f"<span class='{cls(r['unreal'])}'>{jpy(r['unreal'], True)}</span> <small>{pct(r['unreal_pct'], 1)}</small>"
            if r.get("unreal") is not None
            else "<small>原価なし</small>"
        )
        body += (
            "<tr>"
            f"<td><b>{_esc(r['sym'])}</b><small>{_esc(r['name'])}</small></td>"
            f"<td><small>{_esc(r['acct'])}</small></td>"
            f"<td class='n'>{jpy(r['qty'])}</td>"
            f"<td class='n'>{price(r['last'], r['cur'])}<small>{_esc(r['cur'])}</small></td>"
            f"<td class='n {cls(r['chg1d'])}'>{pct(r['chg1d'])}</td>"
            f"<td class='n {cls(r['chg1w'])}'>{pct(r['chg1w'], 1)}</td>"
            f"<td class='n {cls(r['chg1m'])}'>{pct(r['chg1m'], 1)}</td>"
            f"<td class='n {cls(r['chg1y'])}'>{pct(r['chg1y'], 1)}</td>"
            f"<td class='spark' data-spark='{_esc(json.dumps(r['spark']))}'></td>"
            f"<td class='n'>{jpy(r['value'])}</td>"
            f"<td class='n'><small>{float(r['weight']):.1f}%</small></td>"
            f"<td class='n {cls(r['day_pnl'])}'>{jpy(r['day_pnl'], True)}</td>"
            f"<td class='n'>{price(r.get('avg_cost'), r['cur']) if r.get('avg_cost') is not None else '—'}</td>"
            f"<td class='n'>{unreal}</td>"
            "</tr>"
        )
    return (
        "<table class='pos'><thead><tr><th>銘柄</th><th>口座</th><th>数量</th><th>終値</th><th>1D</th><th>1W</th><th>1M</th><th>1Y</th>"
        "<th>1年</th><th>評価額 ¥</th><th>比率</th><th>日次損益 ¥</th><th>平均取得</th><th>含み損益 ¥</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _attribution(att: dict[str, Any]) -> str:
    labels = [
        ("unrealized", "含み（保有中）"),
        ("realized", "実現（売却済）"),
        ("dividends", "配当 税引後"),
        ("fees", "費用"),
        ("fx_translation", "為替換算 現金"),
        ("forex", "為替取引"),
    ]
    rows = "".join(
        f"<tr><td>{_esc(lab)}</td><td class='n {cls(att['window'].get(k))}'>{jpy(att['window'].get(k), True)}</td><td class='n {cls(att['incept'].get(k))}'>{jpy(att['incept'].get(k), True)}</td></tr>"
        for k, lab in labels
    )
    rows += f"<tr class='tot'><td>合計＝NAV−入金</td><td class='n {cls(att['window']['total'])}'>{jpy(att['window']['total'], True)}</td><td class='n {cls(att['incept']['total'])}'>{jpy(att['incept']['total'], True)}</td></tr>"
    return f"<div class='sx'><table class='mini'><thead><tr><th>内訳</th><th>期間内</th><th>開設来</th></tr></thead><tbody>{rows}</tbody></table></div>"


def _closed(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    body = "".join(
        f"<tr><td><b>{_esc(r['sym'])}</b></td><td class='wrap'><small>{r['first']} → {r['last']}</small></td><td class='n'><small>{r['trades']}</small></td><td class='n {cls(r['realized'])}'>{jpy(r['realized'], True)}</td></tr>"
        for r in rows
    )
    total = sum(float(r["realized"]) for r in rows)
    body += f"<tr class='tot'><td>合計</td><td></td><td></td><td class='n {cls(total)}'>{jpy(total, True)}</td></tr>"
    return f"<table class='mini'><thead><tr><th>決済済み</th><th>保有期間</th><th>約定</th><th>実現損益 ¥</th></tr></thead><tbody>{body}</tbody></table>"


def render(data: dict[str, Any], tokens_css: str) -> str:
    h = data["headline"]
    fx = data["fx"]
    tape = "".join(
        f"<span class='tk'><b>{_esc(t['sym'])}</b> {price(t['last'], t.get('cur', 'USD'))} <i class='{cls(t['chg_pct'])}'>{pct(t['chg_pct'])}</i></span>"
        for t in data["tape"]
    )
    kpis = "".join(
        [
            _kpi(
                "総資産 NAV ¥",
                jpy(h["nav_total"]),
                f"時価評価 {int(h['quoted_share'] * 100)}% · 残りは残高据え置き",
            ),
            _kpi(
                "日次損益 ¥",
                jpy(h["day_pnl"], True),
                f"時価評価分 {pct(h['day_pnl_pct'])}",
                cls(h["day_pnl"]),
            ),
            _kpi(
                "含み損益 ¥",
                jpy(h["unrealized_known"], True),
                "原価が台帳にある保有",
                cls(h["unrealized_known"]),
            ),
            _kpi(
                f"期間損益 ¥ · {data['window']['days']}日",
                jpy(h["pnl_window"], True),
                f"海外証券口座 {data['window']['start']} 以降・入金控除後",
                cls(h["pnl_window"]),
            ),
            _kpi(
                "開設来損益 ¥",
                jpy(h["pnl_incept"], True),
                f"実現 {jpy(h['realized_cum'], True)} · 配当 {jpy(h['dividends_net'], True)}",
                cls(h["pnl_incept"]),
            ),
            _kpi(
                "資金加重リターン",
                pct(None if h.get("xirr") is None else h["xirr"] * 100),
                f"最大DD（期間内） {pct(None if h.get('max_dd_window') is None else h['max_dd_window'] * 100, 1)}",
                cls(h.get("xirr")),
            ),
        ]
    )
    alloc = "".join(
        f"<div class='seg' style='flex:{max(float(a['pct']), 0.5)}' title='{_esc(a['label'])} {jpy(a['value'])} 円 ({float(a['pct']):.1f}%)'>"
        + (
            f"<span>{_esc(a['label'])}<br>{float(a['pct']):.0f}%</span>"
            if float(a["pct"]) >= 4
            else ""
        )
        + "</div>"
        for a in data["allocation"]
    )
    accounts = "".join(
        f"<tr><td>{_esc(a['name'])}</td><td class='n'>{jpy(a['total'])}</td><td class='n {cls(a['day_pnl'])}'>{jpy(a['day_pnl'], True)}</td><td class='n {cls(a['unrealized'])}'>{jpy(a['unrealized'], True) if a['unrealized'] is not None else '<small>原価なし</small>'}</td></tr>"
        for a in data["accounts"]
    )
    cards = ""
    for key, s in data["series"]["symbols"].items():
        p = next((r for r in data["positions"] if r.get("key", r["sym"]) == key), None)
        if p is None:
            continue
        sym = p["sym"]
        stats = (
            f"<span>数量 <b>{jpy(p['qty'])}</b></span>"
            f"<span>評価 <b>{jpy(p['value'])}</b></span>"
            f"<span>比率 <b>{float(p['weight']):.1f}%</b></span>"
            + (
                f"<span>平均 <b>{price(p['avg_cost'], p['cur'])}</b></span>"
                if p.get("avg_cost") is not None
                else ""
            )
            + f"<span>1M <b class='{cls(p['chg1m'])}'>{pct(p['chg1m'], 1)}</b></span>"
            f"<span>1Y <b class='{cls(p['chg1y'])}'>{pct(p['chg1y'], 1)}</b></span>"
        )
        pnl_now = s["pnl"][-1] if s["pnl"] else None
        cards += (
            f"<div class='card' data-sym='{_esc(key)}'>"
            f"<div class='ch'><b>{_esc(sym)}</b>"
            f"<span class='n'>{price(p['last'], p['cur'])} <small>{_esc(p['cur'])}</small> <i class='{cls(p['chg1d'])}'>{pct(p['chg1d'])}</i></span></div>"
            f"<div class='nm'>{_esc(p['name'])} · {_esc(p['acct'])}</div>"
            f"<div class='stats'>{stats}</div>"
            f"<div class='lab'>株価 · {data['window']['start'][:7]} → {data['as_of'][:7]}<span>▲ 買 ▼ 売 · 破線 平均取得</span></div>"
            f"<svg class='c-price' viewBox='0 0 380 96' role='img' aria-label='{_esc(sym)} の株価'></svg>"
            f"<div class='lab'>{_esc(s['label'])} ¥<span class='{cls(pnl_now)}'>{jpy(pnl_now, True)}</span></div>"
            f"<svg class='c-pnl' viewBox='0 0 380 80' role='img' aria-label='{_esc(sym)} の損益'></svg>"
            "</div>"
        )
    notes = "".join(f"<li>{_esc(n)}</li>" for n in data["notes"])
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

    return rf"""<!doctype html>
<html lang="ja" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="cache-control" content="no-store">
<title>Portfolio · {_esc(data["as_of"])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Zen+Kaku+Gothic+New:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
{tokens_css}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:13px;line-height:1.5;margin:0;padding:0 18px 60px;-webkit-font-smoothing:antialiased;font-feature-settings:"palt" 1}}
.wrap{{max-width:1320px;margin:0 auto}}
.n,.kpi .v,.tk,.stats b,.mini td.n,.pos td.n{{font-family:var(--mono);font-variant-numeric:tabular-nums}}
.up{{color:var(--accent)}}.dn{{color:var(--series-2)}}
small{{color:var(--ink-3);font-size:11px}}
/* top bar */
.top{{position:sticky;top:0;z-index:5;background:var(--ground);border-bottom:1px solid var(--rule);padding:10px 0 8px;display:flex;gap:18px;align-items:baseline;flex-wrap:wrap}}
.top h1{{font-family:var(--serif);font-weight:700;font-size:20px;margin:0;letter-spacing:.01em}}
.top .meta{{font-family:var(--mono);font-size:11px;color:var(--ink-3);display:flex;gap:14px;flex-wrap:wrap}}
.top .meta b{{color:var(--ink-2);font-weight:500}}
.top button{{margin-left:auto;background:var(--surface);color:var(--ink-2);border:1px solid var(--rule);border-radius:999px;padding:3px 11px;font:inherit;font-size:11px;cursor:pointer}}
.tape{{display:flex;gap:6px 18px;flex-wrap:wrap;padding:8px 0 2px;font-size:11.5px;color:var(--ink-2)}}
.tk b{{color:var(--ink);font-weight:600;margin-right:4px}}.tk i{{font-style:normal;margin-left:4px}}
/* headline */
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(196px,1fr));gap:8px;margin:12px 0 0}}
.kpi{{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:11px 14px 12px;min-width:0}}
.kpi .k{{display:block;font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3)}}
.kpi .v{{display:block;font-size:24px;font-weight:600;line-height:1.2;margin-top:6px;letter-spacing:-.01em}}
.kpi .s{{display:block;font-size:11px;color:var(--ink-3);margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
/* general grid */
.grid{{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(340px,1fr);gap:10px;margin-top:10px}}
@media (max-width:900px){{.grid{{grid-template-columns:1fr}}}}
.panel{{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:12px 14px 10px;min-width:0;overflow:hidden}}
.sx{{overflow-x:auto}}
.panel h2{{font-size:12px;font-weight:700;margin:0 0 6px;letter-spacing:.02em;display:flex;justify-content:space-between;align-items:baseline}}
.panel h2 small{{font-weight:400}}
.legend{{display:flex;gap:14px;font-family:var(--mono);font-size:10.5px;color:var(--ink-3)}}
.legend i{{display:inline-block;width:12px;height:2px;vertical-align:middle;margin-right:5px;border-radius:1px}}
.alloc{{display:flex;gap:2px;height:44px;margin:6px 0 10px}}
.seg{{background:var(--surface-2);border-radius:4px;min-width:0;overflow:hidden;font-size:10.5px;line-height:1.25;padding:5px 6px;color:var(--ink-2);font-family:var(--mono)}}
.seg:nth-child(odd){{background:var(--accent-wash)}}
table{{border-collapse:collapse;width:100%;min-width:0}}
th{{font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);font-weight:500;text-align:right;padding:5px 8px;border-bottom:1px solid var(--rule);white-space:nowrap}}
td{{padding:6px 8px;border-bottom:1px solid var(--rule);text-align:right;white-space:nowrap;vertical-align:middle}}
th:first-child,td:first-child{{text-align:left}}
tbody tr:last-child td{{border-bottom:none}}
tr.tot td{{font-weight:700;background:var(--surface-3)}}
.mini{{table-layout:fixed;width:100%}}.mini th:first-child{{width:42%}}
.mini td,.mini th{{padding:4px 8px;font-size:12px;overflow:hidden;text-overflow:ellipsis}}
.mini td:first-child,.mini th:first-child,.mini td.wrap{{white-space:normal;line-height:1.3}}
.tw{{overflow-x:auto;background:var(--surface);border:1px solid var(--rule);border-radius:10px;margin-top:10px}}
.pos{{min-width:1100px;font-size:12.5px}}
.pos td b{{display:block;font-weight:600}}.pos td b+small{{display:block;max-width:220px;overflow:hidden;text-overflow:ellipsis}}
.pos td small{{margin-left:3px}}
.pos td.spark svg{{width:96px;height:26px;display:block}}
/* cards */
.cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px;margin-top:10px}}
.card{{background:var(--surface);border:1px solid var(--rule);border-radius:10px;padding:11px 12px 8px;min-width:0}}
.ch{{display:flex;justify-content:space-between;align-items:baseline;gap:8px}}
.ch b{{font-size:14px;font-weight:700}}.ch i{{font-style:normal;font-family:var(--mono)}}
.nm{{font-size:11px;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.stats{{display:flex;gap:4px 12px;flex-wrap:wrap;font-size:11px;color:var(--ink-3);margin:6px 0 4px}}
.stats b{{color:var(--ink-2);font-weight:500}}
.lab{{display:flex;justify-content:space-between;font-family:var(--mono);font-size:10px;color:var(--ink-3);margin:6px 0 0;letter-spacing:.04em}}
.lab span{{font-family:var(--mono)}}
svg{{display:block;width:100%;height:auto;overflow:visible}}
svg text{{font-family:var(--mono);fill:var(--ink-3);font-size:9.5px}}
.grid1{{stroke:var(--grid);stroke-width:1}}.zero{{stroke:var(--rule-2);stroke-width:1}}
.l1{{stroke:var(--series-1);stroke-width:2;fill:none;stroke-linejoin:round;stroke-linecap:round}}
.l2{{stroke:var(--series-2);stroke-width:1.5;fill:none;stroke-dasharray:3 3}}
.a-up{{fill:var(--accent);opacity:.12}}.a-dn{{fill:var(--series-2);opacity:.14}}
.b-up{{fill:var(--accent)}}.b-dn{{fill:var(--series-2)}}
.buy{{fill:var(--accent)}}.sell{{fill:var(--series-2)}}
.dot{{fill:var(--series-1);stroke:var(--surface);stroke-width:2}}
.xh{{stroke:var(--ink-3);stroke-width:1;stroke-dasharray:2 3;opacity:0}}
.hit{{fill:transparent;cursor:crosshair}}
#tip{{position:fixed;pointer-events:none;opacity:0;transition:opacity .08s;background:var(--ink);color:var(--ground);font-family:var(--mono);font-size:11px;line-height:1.6;padding:7px 10px;border-radius:7px;z-index:99;white-space:pre}}
.err{{background:var(--accent-wash);border:1px solid var(--accent-soft);color:var(--ink);border-radius:8px;padding:9px 12px;margin:10px 0;font-size:12.5px}}
ul.notes{{margin:14px 0 0;padding-left:18px;color:var(--ink-3);font-size:11.5px}}
footer{{margin-top:22px;padding-top:10px;border-top:1px solid var(--rule);font-family:var(--mono);font-size:10.5px;color:var(--ink-3);line-height:1.9}}
h2.sec{{font-family:var(--serif);font-size:15px;font-weight:700;margin:18px 0 0;display:flex;gap:10px;align-items:baseline}}
h2.sec small{{font-family:var(--mono);font-weight:400;letter-spacing:.06em;text-transform:uppercase}}
</style>
</head>
<body>
<div class="wrap">
<div class="top">
  <h1>Portfolio</h1>
  <div class="meta"><span>基準日 <b>{_esc(data["as_of"])}</b></span><span>USD/JPY <b>{float(fx["last"]):.2f}</b> <span class="{cls(fx["chg_pct"])}">{pct(fx["chg_pct"])}</span></span><span>生成 <b>{_esc(data["generated_at"])}</b></span></div>
  <button id="theme" type="button" aria-label="配色を切り替え">配色</button>
</div>
<div class="tape">{tape}</div>

<h2 class="sec">ヘッドライン <small>headline</small></h2>
<div class="kpis">{kpis}</div>

<h2 class="sec">一般データ <small>general</small></h2>
<div class="grid">
  <div class="panel">
    <h2>口座別 <small>評価額 / 日次 / 含み</small></h2>
    <table class="mini"><thead><tr><th>口座</th><th>評価額 ¥</th><th>日次損益 ¥</th><th>含み損益 ¥</th></tr></thead><tbody>{accounts}</tbody></table>
    <h2 style="margin-top:12px">資産配分 <small>総資産比</small></h2>
    <div class="alloc">{alloc}</div>
  </div>
  <div class="panel">{_attribution(data["attribution"])}</div>
</div>
<div class="tw">{_positions_table(data["positions"])}</div>

<h2 class="sec" id="charts-top">時系列 <small>time series · {_esc(data["window"]["start"])} → {_esc(data["as_of"])}</small></h2>
<div class="grid">
  <div class="panel">
    <h2>海外証券口座 NAV と損益 <small>入金は段差、損益 ＝ NAV − 累計入金</small></h2>
    <div class="legend"><span><i style="background:var(--series-1)"></i>NAV ¥</span><span><i style="background:var(--series-2)"></i>累計入金 ¥</span></div>
    <svg id="c-nav" viewBox="0 0 860 220" role="img" aria-label="海外証券口座の NAV と累計入金"></svg>
    <div class="legend" style="margin-top:8px"><span><i style="background:var(--series-1)"></i>損益 ¥（NAV − 累計入金）</span></div>
    <svg id="c-pnl" viewBox="0 0 860 150" role="img" aria-label="海外証券口座の累計損益"></svg>
  </div>
  <div class="panel">
    <h2>日次損益 <small>海外証券口座 · 入金を除いた NAV の日次変化</small></h2>
    <svg id="c-daily" viewBox="0 0 400 220" role="img" aria-label="日次損益の棒グラフ"></svg>
    {_closed(data["closed"])}
  </div>
</div>
<div class="cards" id="charts-end">{cards}</div>

<ul class="notes">{notes}</ul>
<footer>ポジション data/portfolio.private.json · 取引履歴 data/ibkr-transactions.private.csv · 株価/為替 yfinance 終値（USD 建ては USD/JPY で円換算）· スクリプト portfolio-analyzer/scripts/daily_pl_report.py</footer>
</div>
<div id="tip" role="status"></div>
<script id="data" type="application/json">{payload}</script>
<script>
(function(){{
try{{
const root=document.documentElement;
try{{const t=localStorage.getItem("pl-theme");if(t)root.setAttribute("data-theme",t);}}catch(e){{}}
document.getElementById("theme").addEventListener("click",()=>{{const t=root.getAttribute("data-theme")==="dark"?"light":"dark";root.setAttribute("data-theme",t);try{{localStorage.setItem("pl-theme",t);}}catch(e){{}}}});
const D=JSON.parse(document.getElementById("data").textContent);
const NS="http://www.w3.org/2000/svg";
const el=(t,a={{}})=>{{const e=document.createElementNS(NS,t);for(const k in a)e.setAttribute(k,a[k]);return e;}};
const tip=document.getElementById("tip");
const fmt=v=>(v==null?"—":Math.round(v).toLocaleString("ja-JP"));
const sfmt=v=>(v==null?"—":(v>0?"+":v<0?"−":"±")+Math.abs(Math.round(v)).toLocaleString("ja-JP"));
const pfmt=(v,c)=>(v==null?"—":(c==="USD"||v<100?v.toFixed(2):v.toFixed(1)));
const afmt=(v,c)=>(v==null?"":(v>=100?Math.round(v).toLocaleString("ja-JP"):c==="USD"?v.toFixed(0):v.toFixed(1)));
const jd=s=>s.replace(/-/g,"/");
function bindTip(node,fn){{
  node.addEventListener("pointermove",e=>{{tip.textContent=fn(e);tip.style.opacity=1;const w=tip.offsetWidth,h=tip.offsetHeight;let x=e.clientX+14,y=e.clientY-h-12;if(x+w>innerWidth-8)x=e.clientX-w-14;if(y<8)y=e.clientY+18;tip.style.left=x+"px";tip.style.top=y+"px";}});
  node.addEventListener("pointerleave",()=>{{tip.style.opacity=0;}});
}}
function nice(lo,hi,n){{const span=hi-lo||1;const raw=span/n;const p=Math.pow(10,Math.floor(Math.log10(raw)));const m=raw/p;const step=(m<1.5?1:m<3.5?2:m<7.5?5:10)*p;const out=[];for(let v=Math.ceil(lo/step)*step;v<=hi+1e-9;v+=step)out.push(+v.toFixed(10));return out;}}
function yl(v){{const a=Math.abs(v);return a>=1e8?(v/1e8).toFixed(1)+"億":a>=1e4?Math.round(v/1e4)+"万":a>=1?Math.round(v).toString():v.toFixed(2);}}
/* generic line chart: series=[{{v:[],cls:'l1'|'l2'}}], opts: zero, area, ticksX, yfmt, marks */
function lineChart(svg,dates,series,o){{
  const W=+svg.getAttribute("viewBox").split(" ")[2],H=+svg.getAttribute("viewBox").split(" ")[3];
  const M={{l:o.ml||46,r:8,t:8,b:o.ticksX===false?4:18}};const n=dates.length;if(n<2)return;
  let lo=Infinity,hi=-Infinity;series.forEach(s=>s.v.forEach(v=>{{if(v!=null){{lo=Math.min(lo,v);hi=Math.max(hi,v);}}}}));
  if(o.zero){{lo=Math.min(lo,0);hi=Math.max(hi,0);}}
  if(o.extra!=null){{lo=Math.min(lo,o.extra);hi=Math.max(hi,o.extra);}}
  const pad=(hi-lo)*0.08||1;lo-=pad;hi+=pad;
  const x=i=>M.l+i*(W-M.l-M.r)/(n-1),y=v=>H-M.b-(v-lo)/(hi-lo)*(H-M.t-M.b);
  const g=el("g");svg.appendChild(g);
  nice(lo,hi,o.ny||4).forEach(v=>{{g.appendChild(el("line",{{x1:M.l,x2:W-M.r,y1:y(v),y2:y(v),class:"grid1"}}));const t=el("text",{{x:M.l-5,y:y(v)+3,"text-anchor":"end"}});t.textContent=(o.yfmt||yl)(v);g.appendChild(t);}});
  if(o.zero)g.appendChild(el("line",{{x1:M.l,x2:W-M.r,y1:y(0),y2:y(0),class:"zero"}}));
  if(o.ticksX!==false){{let seen="";dates.forEach((d,i)=>{{const m=d.slice(0,7);if(m!==seen){{seen=m;const mm=+m.slice(5);if((mm-1)%(o.mstep||3)===0){{const t=el("text",{{x:x(i),y:H-4,"text-anchor":"middle"}});t.textContent=m.slice(2).replace("-","/");g.appendChild(t);}}}}}});}}
  series.forEach(s=>{{
    const pts=s.v.map((v,i)=>v==null?null:[x(i),y(v)]);
    if(o.area){{let d="",started=false;pts.forEach((p,i)=>{{if(!p)return;d+=(started?"L":"M")+p[0].toFixed(1)+" "+y(0).toFixed(1)+"L"+p[0].toFixed(1)+" "+p[1].toFixed(1);started=true;}});
      /* split positive / negative washes */
      const up=el("path",{{d:pathArea(pts,y(0),true),class:"a-up"}}),dn=el("path",{{d:pathArea(pts,y(0),false),class:"a-dn"}});g.appendChild(up);g.appendChild(dn);}}
    const d=pts.map((p,i)=>p?((i&&pts[i-1])?"L":"M")+p[0].toFixed(1)+" "+p[1].toFixed(1):"").join("");
    g.appendChild(el("path",{{d,class:s.cls||"l1"}}));
    if(s.end!==false){{const li=s.v.length-1;if(s.v[li]!=null)g.appendChild(el("circle",{{cx:x(li),cy:y(s.v[li]),r:3.5,class:"dot"}}));}}
  }});
  if(o.extra!=null){{g.appendChild(el("line",{{x1:M.l,x2:W-M.r,y1:y(o.extra),y2:y(o.extra),class:"l2"}}));}}
  (o.marks||[]).forEach(m=>{{const v=series[0].v[m.i];if(v==null)return;const up=m.qty>0;const cx=x(m.i),cy=y(v)+(up?9:-9);
    g.appendChild(el("path",{{d:up?`M${{cx}} ${{cy-4}}L${{cx-4}} ${{cy+3}}L${{cx+4}} ${{cy+3}}Z`:`M${{cx}} ${{cy+4}}L${{cx-4}} ${{cy-3}}L${{cx+4}} ${{cy-3}}Z`,class:up?"buy":"sell"}}));}});
  const xh=el("line",{{x1:0,x2:0,y1:M.t,y2:H-M.b,class:"xh"}});g.appendChild(xh);
  const hit=el("rect",{{x:M.l,y:M.t,width:W-M.l-M.r,height:H-M.t-M.b,class:"hit"}});g.appendChild(hit);
  bindTip(hit,e=>{{const r=svg.getBoundingClientRect();const px=(e.clientX-r.left)/r.width*W;const i=Math.max(0,Math.min(n-1,Math.round((px-M.l)/(W-M.l-M.r)*(n-1))));xh.setAttribute("x1",x(i));xh.setAttribute("x2",x(i));xh.style.opacity=1;return o.tip(i);}});
  hit.addEventListener("pointerleave",()=>{{xh.style.opacity=0;}});
}}
function pathArea(pts,y0,positive){{let d="";let run=[];const flush=()=>{{if(run.length){{d+="M"+run[0][0].toFixed(1)+" "+y0.toFixed(1)+run.map(p=>"L"+p[0].toFixed(1)+" "+p[1].toFixed(1)).join("")+"L"+run[run.length-1][0].toFixed(1)+" "+y0.toFixed(1)+"Z";}}run=[];}};
  pts.forEach(p=>{{if(!p){{flush();return;}}const side=positive?p[1]<=y0:p[1]>=y0;if(side)run.push(p);else{{if(run.length){{run.push([p[0],y0]);}}flush();}}}});flush();return d;}}
function barChart(svg,dates,v,o){{
  const W=+svg.getAttribute("viewBox").split(" ")[2],H=+svg.getAttribute("viewBox").split(" ")[3];const M={{l:44,r:8,t:8,b:18}};const n=v.length;if(!n)return;
  let a=0;v.forEach(x=>{{if(x!=null)a=Math.max(a,Math.abs(x));}});a=a||1;
  const x=i=>M.l+i*(W-M.l-M.r)/Math.max(n-1,1),y=val=>H-M.b-(val+a)/(2*a)*(H-M.t-M.b);
  const g=el("g");svg.appendChild(g);
  [a,a/2,0,-a/2,-a].forEach(val=>{{g.appendChild(el("line",{{x1:M.l,x2:W-M.r,y1:y(val),y2:y(val),class:val===0?"zero":"grid1"}}));const t=el("text",{{x:M.l-5,y:y(val)+3,"text-anchor":"end"}});t.textContent=yl(val);g.appendChild(t);}});
  let seen="";dates.forEach((d,i)=>{{const m=d.slice(0,7);if(m!==seen){{seen=m;const mm=+m.slice(5);if((mm-1)%3===0){{const t=el("text",{{x:x(i),y:H-4,"text-anchor":"middle"}});t.textContent=m.slice(2).replace("-","/");g.appendChild(t);}}}}}});
  const bw=Math.max((W-M.l-M.r)/n*0.7,1);
  v.forEach((val,i)=>{{if(val==null)return;const r=el("rect",{{x:x(i)-bw/2,y:Math.min(y(0),y(val)),width:bw,height:Math.max(Math.abs(y(val)-y(0)),.5),class:val>=0?"b-up":"b-dn"}});bindTip(r,()=>`${{jd(dates[i])}}\n日次損益 ${{sfmt(val)}} 円`);g.appendChild(r);}});
}}
function spark(td){{const v=JSON.parse(td.getAttribute("data-spark"));if(!v||v.length<2)return;const W=96,H=26;let lo=Math.min(...v),hi=Math.max(...v);const pad=(hi-lo)*0.1||1;lo-=pad;hi+=pad;
  const x=i=>2+i*(W-4)/(v.length-1),y=val=>H-3-(val-lo)/(hi-lo)*(H-6);const svg=el("svg",{{viewBox:`0 0 ${{W}} ${{H}}`}});
  svg.appendChild(el("path",{{d:v.map((val,i)=>(i?"L":"M")+x(i).toFixed(1)+" "+y(val).toFixed(1)).join(""),class:v[v.length-1]>=v[0]?"l1":"l1",style:"stroke-width:1.5"}}));
  svg.appendChild(el("circle",{{cx:x(v.length-1),cy:y(v[v.length-1]),r:2.2,class:"dot",style:"stroke-width:1.5"}}));td.appendChild(svg);}}
/* ---- draw ---- */
const S=D.series,dates=S.dates;
lineChart(document.getElementById("c-nav"),dates,[{{v:S.nav,cls:"l1"}},{{v:S.deposits,cls:"l2",end:false}}],{{ny:4,tip:i=>`${{jd(dates[i])}}\nNAV      ${{fmt(S.nav[i])}} 円\n累計入金  ${{fmt(S.deposits[i])}} 円\n損益      ${{sfmt(S.pnl[i])}} 円`}});
lineChart(document.getElementById("c-pnl"),dates,[{{v:S.pnl,cls:"l1"}}],{{zero:true,area:true,ny:3,tip:i=>`${{jd(dates[i])}}\n損益 ${{sfmt(S.pnl[i])}} 円`}});
barChart(document.getElementById("c-daily"),dates,S.daily_pnl,{{}});
document.querySelectorAll("td.spark").forEach(spark);
document.querySelectorAll(".card").forEach(card=>{{const sym=card.getAttribute("data-sym");const s=S.symbols[sym];if(!s)return;
  const marks=(s.trades||[]).map(t=>({{i:t.i,qty:t.qty}}));
  const name=sym.split("@")[0];
  lineChart(card.querySelector(".c-price"),dates,[{{v:s.price,cls:"l1"}}],{{ml:40,ny:3,extra:s.avg_cost,marks,yfmt:v=>afmt(v,s.cur),tip:i=>{{const t=(s.trades||[]).filter(t=>t.i===i);return `${{jd(dates[i])}}\n${{name}} ${{pfmt(s.price[i],s.cur)}} ${{s.cur}}`+(t.length?"\n"+t.map(t=>(t.qty>0?"買 ":"売 ")+Math.abs(t.qty)+" @ "+pfmt(t.price,s.cur)).join("\n"):"");}}}});
  lineChart(card.querySelector(".c-pnl"),dates,[{{v:s.pnl,cls:"l1"}}],{{ml:40,zero:true,area:true,ny:3,ticksX:false,tip:i=>`${{jd(dates[i])}}\n${{s.label}} ${{sfmt(s.pnl[i])}} 円`}});
}});
  const a=document.getElementById("charts-top"),b=document.getElementById("charts-end");
  if(a&&b){{const y=window.scrollY;document.body.dataset.chartBox=Math.round(a.getBoundingClientRect().top+y)+","+Math.round(b.getBoundingClientRect().bottom+y);}}
}}catch(err){{
  const b=document.createElement("div");b.className="err";
  b.textContent="図の描画に失敗しました（"+err+"）。表の数値は正しく、図だけが欠けています。";
  document.querySelector(".wrap").prepend(b);
  console.error(err);
}}
}})();
</script>
</body>
</html>
"""
