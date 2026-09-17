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


def split(stock: float | None, fx: float | None) -> str:
    """Stock and FX parts of a JPY P&L, e.g. ``株 +12,000 · FX −3,506``; empty when unknown."""
    if stock is None and fx is None:
        return ""
    return f"株 {jpy(stock, True)} · FX {jpy(fx, True)}"


def usd(value: float | None, rate: float | None, sign: bool = False) -> str:
    """A yen amount in dollars at the day's USD/JPY, e.g. ``$301,257`` / ``−$2,934``."""
    if value is None or not rate:
        return ""
    v = round(float(value) / float(rate))
    text = f"${abs(v):,}"
    if sign:
        return ("+" if v > 0 else "−" if v < 0 else "±") + text
    return ("−" if v < 0 else "") + text


def _joined(*parts: str) -> str:
    return " · ".join(p for p in parts if p)


def after_tax(value: float | None, label: str = "税引後") -> str:
    return "" if value is None else f"{label} {jpy(value, True)}"


def _split_under(row: dict[str, Any], stock: str, fx: str, taxed: str, dollars: str = "") -> str:
    """The dollar figure, the split and the after-tax figure under a cell's value, one per line."""
    lines = [dollars] if dollars else []
    if row.get(stock) is not None or row.get(fx) is not None:
        lines += [f"株 {jpy(row.get(stock), True)}", f"FX {jpy(row.get(fx), True)}"]
    if row.get(taxed) is not None:
        lines.append(after_tax(row[taxed], "税後"))
    return f"<span class='sp'>{'<br>'.join(lines)}</span>" if lines else ""


def _kpi(
    label: str, value: str, sub: str, tone: str = "", sub2: str = "", dollars: str = ""
) -> str:
    in_usd = f'<span class="u">{dollars}</span>' if dollars else ""
    second = f'<span class="s">{sub2}</span>' if sub2 else ""
    return f'<div class="kpi"><span class="k">{_esc(label)}</span><span class="v {tone}">{value}</span>{in_usd}<span class="s">{sub}</span>{second}</div>'


def _positions_table(rows: list[dict[str, Any]], rate: float | None) -> str:
    body = ""
    for r in rows:
        unreal = (
            f"<span class='{cls(r['unreal'])}'>{jpy(r['unreal'], True)}</span> <small>{pct(r['unreal_pct'], 1)}</small>"
            f"{_split_under(r, 'unreal_stock', 'unreal_fx', 'unreal_after_tax', usd(r['unreal'], rate, True))}"
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
            f"<td class='spark' data-piece='spark:{_esc(r.get('key', r['sym']))}' data-spark='{_esc(json.dumps(r['spark']))}'></td>"
            f"<td class='n'>{jpy(r['value'])}<span class='sp'>{usd(r['value'], rate)}</span></td>"
            f"<td class='n'><small>{float(r['weight']):.1f}%</small></td>"
            f"<td class='n {cls(r['day_pnl'])}'>{jpy(r['day_pnl'], True)}{_split_under(r, 'day_stock', 'day_fx', 'day_after_tax', usd(r['day_pnl'], rate, True))}</td>"
            f"<td class='n'>{price(r.get('avg_cost'), r['cur']) if r.get('avg_cost') is not None else '—'}</td>"
            f"<td class='n'>{unreal}</td>"
            "</tr>"
        )
    return (
        "<table class='pos'><thead><tr><th>銘柄</th><th>口座</th><th>数量</th><th>終値</th><th>1D</th><th>1W</th><th>1M</th><th>1Y</th>"
        "<th>1年</th><th>評価額 ¥</th><th>比率</th><th>日次損益 ¥</th><th>平均取得</th><th>含み損益 ¥</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def _attribution(att: dict[str, Any], names: dict[str, str] | None = None) -> str:
    """The P&L buckets over the window and since inception, then each account's total."""
    names = names or {}
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
    for acc, a in (att.get("accounts") or {}).items():
        w, i = a["window"].get("total"), a["incept"].get("total")
        rows += f"<tr><td>{_esc(names.get(acc, acc))}</td><td class='n {cls(w)}'>{jpy(w, True)}</td><td class='n {cls(i)}'>{jpy(i, True)}</td></tr>"
    return f"<div class='sx'><table class='mini'><thead><tr><th>内訳 <small>全口座 · 下段は口座別</small></th><th>期間内</th><th>開設来</th></tr></thead><tbody>{rows}</tbody></table></div>"


def _ratio(value: float | None, digits: int = 1) -> str:
    """A fraction as an unsigned percentage: 0.323 → 32.3%."""
    return "—" if value is None else f"{float(value) * 100:.{digits}f}%"


def _delta(cur: float | None, prev: float | None, unit: str = "pt", digits: int = 1) -> str:
    """The change since the previous report as a small tag; empty when either side is unknown."""
    if cur is None or prev is None:
        return ""
    d = (float(cur) - float(prev)) * (100 if unit == "pt" else 1)
    text = f"{d:+.{digits}f}".replace("-", "−")
    return f"<small class='{cls(d)}'>前日比 {text}{unit if unit == 'pt' else ''}</small>"


def _limit_value(metric: str, value: float | None) -> str:
    if value is None:
        return "—"
    # whole words: "largest_foreign_country_ratio" contains "count" but is a share
    words = set(metric.split("_"))
    return f"{float(value):.1f}" if words & {"effective", "count"} else _ratio(value)


def _share_rows(rows: list[dict[str, Any]], key: str = "pct", limit: int = 8) -> str:
    """Label, a bar in proportion to the share, and the share itself."""
    out = ""
    for r in rows[:limit]:
        p = r.get(key)
        width = 0.0 if p is None else max(float(p) * 100, 0.0)
        out += (
            f"<tr><td>{_esc(r['label'])}</td><td class='b'><div class='bar' style='width:{width:.0f}%'></div></td>"
            f"<td class='n'>{_ratio(p)}</td></tr>"
        )
    return out


def _stress_rows(rows: list[dict[str, Any]], note) -> str:
    """Label, a bar in proportion to the worst impact (red when a loss), impact and note."""
    peak = max((abs(float(r["impact_pct"] or 0)) for r in rows), default=0.0)
    out = ""
    for r in rows:
        p = float(r["impact_pct"] or 0)
        width = 0.0 if not peak else abs(p) / peak * 100
        out += (
            f"<tr><td>{_esc(r['label'])}<small> {_esc(note(r))}</small></td>"
            f"<td class='b'><div class='bar {'neg' if p < 0 else ''}' style='width:{width:.0f}%'></div></td>"
            f"<td class='n {cls(p)}'>{pct(p * 100, 1)}<span class='sp'>{jpy(r['impact_jpy'], True)}</span></td></tr>"
        )
    return out


def _risk(risk: dict[str, Any] | None) -> str:
    """The risk section: limits, look-through exposures, statistics, contributions and stress."""
    if not risk:
        return ""
    s, c, x, rc, st = (
        risk["stats"],
        risk["concentration"],
        risk["exposures"],
        risk["contributions"],
        risk["stress"],
    )
    prev = s.get("prev") or {}
    beta = s.get("beta") or {}
    chips = ""
    for lim in risk.get("policy") or []:
        breach = lim["status"] == "breach"
        chips += (
            f"<span class='lim {lim['status']}' title='{_esc(lim.get('note') or '')}'>"
            f"{'超過 ' if breach else ''}{_esc(lim['label'])} · {_limit_value(lim['metric'], lim['value'])}"
            f" / {_esc(lim['operator'])} {_limit_value(lim['metric'], lim['threshold'])}</span>"
        )
    breaches = risk.get("policy_breaches") or 0
    exposures = "".join(
        f"<div><h3>{title}</h3><table class='mini'><tbody>{_share_rows(x[key])}</tbody></table></div>"
        for key, title in (
            ("asset_class", "資産クラス"),
            ("currency", "通貨"),
            ("region", "国・地域"),
            ("sector", "セクター"),
        )
    )
    issuers = "".join(
        f"<tr><td>{_esc(r['label'])}<small> {_esc(r.get('country') or '')}</small></td>"
        f"<td class='wrap'><small>{_esc(' · '.join(r['via']))}</small></td><td class='n'>{_ratio(r['pct'])}</td></tr>"
        for r in x["issuers"][:10]
    )
    coverage = (x.get("coverage") or {}).get("issuer")
    worst = s.get("worst_day") or {}
    stat_rows = [
        (
            "年率ボラティリティ",
            _ratio(s["vol_annual"]),
            _delta(s["vol_annual"], prev.get("vol_annual")),
        ),
        (
            "VaR 1日 95%",
            f"{jpy(s['var_1d_95_jpy'])} <small>{_ratio(s['var_1d_95'], 2)}</small>",
            _delta(s["var_1d_95"], prev.get("var_1d_95"), digits=2),
        ),
        (
            "VaR 1日 99%",
            f"{jpy(s['var_1d_99_jpy'])} <small>{_ratio(s['var_1d_99'], 2)}</small>",
            "",
        ),
        (
            "ES 97.5%",
            f"{jpy(s['es_1d_975_jpy'])} <small>{_ratio(s['es_1d_975'], 2)}</small>",
            _delta(s["es_1d_975"], prev.get("es_1d_975"), digits=2),
        ),
        (
            "VaR 20日 95% <small>√20 換算</small>",
            f"{jpy(s['var_20d_95_jpy'])} <small>{_ratio(s['var_20d_95'])}</small>",
            "",
        ),
        (
            "最悪日 <small>窓内</small>",
            f"{jpy(worst.get('pnl_jpy'), True)} <small>{_esc(worst.get('date') or '—')} · {pct(None if worst.get('pct') is None else worst['pct'] * 100)}</small>",
            "",
        ),
        (
            "ベータ TOPIX",
            "—" if beta.get("topix") is None else f"{beta['topix']:.2f}",
            _delta(beta.get("topix"), prev.get("beta_topix"), unit="", digits=2),
        ),
        (
            "ベータ S&amp;P 500 <small>現地通貨</small>",
            "—" if beta.get("sp500") is None else f"{beta['sp500']:.2f}",
            _delta(beta.get("sp500"), prev.get("beta_sp500"), unit="", digits=2),
        ),
        (
            "ベータ USD/JPY",
            "—" if beta.get("usdjpy") is None else f"{beta['usdjpy']:.2f}",
            _delta(beta.get("usdjpy"), prev.get("beta_usdjpy"), unit="", digits=2),
        ),
        (
            "外貨エクスポージャー",
            _ratio(c["foreign_currency_ratio"]),
            _delta(c["foreign_currency_ratio"], prev.get("foreign_currency_ratio")),
        ),
        (
            "最大ルックスルー銘柄",
            f"{_esc(c.get('largest_issuer') or '—')} <small>{_ratio(c['largest_issuer_lookthrough_ratio'])}</small>",
            _delta(
                c["largest_issuer_lookthrough_ratio"], prev.get("largest_issuer_lookthrough_ratio")
            ),
        ),
        (
            "最大セクター",
            f"{_esc(c.get('max_sector') or '—')} <small>{_ratio(c['max_sector_ratio'])}</small>",
            _delta(c["max_sector_ratio"], prev.get("max_sector_ratio")),
        ),
        (
            "実効数 <small>銘柄 · セクター · 通貨 · 国・地域</small>",
            " · ".join(
                "—" if c.get(k) is None else f"{c[k]:.1f}"
                for k in (
                    "effective_positions",
                    "effective_sectors",
                    "effective_currencies",
                    "effective_countries",
                )
            ),
            "",
        ),
    ]
    stats = "".join(
        f"<tr><td>{label}</td><td class='n'>{value}{f'<span class=sp>{tag}</span>' if tag else ''}</td></tr>"
        for label, value, tag in stat_rows
    )
    positions = "".join(
        f"<tr><td>{_esc(p['sym'])}</td><td class='n'>{_ratio(p['weight'])}</td>"
        f"<td class='n'><b>{_ratio(p['risk_share'])}</b></td><td class='n'>{_ratio(p.get('vol_annual'))}</td></tr>"
        for p in rc["positions"][:8]
    )
    buckets = "".join(
        f"<div><h3>{title}</h3><table class='mini'><thead><tr><th>{title}</th><th>比率</th><th>寄与</th></tr></thead><tbody>"
        + "".join(
            f"<tr><td>{_esc(r['label'])}</td><td class='n'>{_ratio(r.get('weight'))}</td><td class='n'>{_ratio(r['risk_share'])}</td></tr>"
            for r in rc[key][:6]
        )
        + "</tbody></table></div>"
        for key, title in (("currency", "通貨"), ("sector", "セクター"), ("region", "国・地域"))
    )
    scenarios = st["scenarios"]
    shown = scenarios[:8] + [r for r in scenarios[8:] if r["kind"] == "historical"]
    kinds = {"historical": "過去局面の換算", "compound": "複合", "hypothetical": "単一"}
    return f"""
<h2 class="sec" id="risk">リスク <small>risk · ルックスルー · 直近 {
        int(s.get("window_days") or 0)
    } 営業日 · 現在ウェイト</small></h2>
<div class="rgrid">
  <div class="panel wide">
    <h2>限度 <small>{
        "超過 " + str(breaches) + " 件" if breaches else "超過なし"
    } · 参照ファイルのポリシー（draft）</small></h2>
    <div>{chips}</div>
  </div>
  <div class="panel wide">
    <h2>エクスポージャー <small>ルックスルー後 · 総資産比 · DC は月次レポートの構成比で按分（推定）</small></h2>
    <div class="xg">{exposures}</div>
  </div>
  <div class="panel">
    <h2>ルックスルー上位銘柄 <small>直接保有 ＋ ETF 経由 · 発行体カバー率 {
        _ratio(coverage, 0)
    }</small></h2>
    <div class="sx"><table class="mini"><thead><tr><th>発行体</th><th>経由</th><th>比率</th></tr></thead><tbody>{
        issuers
    }</tbody></table></div>
  </div>
  <div class="panel">
    <h2>リスク量 <small>過去シミュレーション · 前日比は前回レポート比</small></h2>
    <div class="sx"><table class="mini rs"><tbody>{stats}</tbody></table></div>
  </div>
  <div class="panel wide">
    <h2>リスク寄与 <small>分散への寄与 w·Σw / σ² · 合計 100% · 通貨・セクター・国へはルックスルー比率で按分</small></h2>
    <div class="xg"><div><h3>銘柄</h3><table class="mini"><thead><tr><th>銘柄</th><th>比率</th><th>寄与</th><th>ボラ</th></tr></thead><tbody>{
        positions
    }</tbody></table></div>{buckets}</div>
  </div>
  <div class="panel wide">
    <h2>ストレス <small>ファクター換算のシナリオ · 実測リプレイの局面</small></h2>
    <div class="xg2"><div><h3>シナリオ <small>参照ファイル · 損失の大きい順 · 過去局面の換算は全件</small></h3>
    <table class="mini"><thead><tr><th>シナリオ</th><th></th><th>影響</th></tr></thead><tbody>{
        _stress_rows(shown, lambda r: kinds.get(r["kind"], r["kind"]))
    }</tbody></table></div>
    <div><h3>過去局面のリプレイ <small>開始前日の終値 → 終了日の終値 · 現在の保有で</small></h3>
    <table class="mini"><thead><tr><th>局面</th><th></th><th>影響</th></tr></thead><tbody>{
        _stress_rows(
            st["episodes"],
            lambda r: f"{r['start']} → {r['end']} · カバー率 {_ratio(r.get('coverage'), 0)}",
        )
    }</tbody></table></div></div>
  </div>
</div>"""


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


# Chart sizes (viewBox) on screen, where they scale with the page, and when the
# page is captured for the mail, where each is drawn at the mail column's width.
SCREEN_SIZES = {
    "nav": (860, 220),
    "pnl": (860, 150),
    "daily": (400, 220),
    "price": (380, 96),
    "pnlc": (380, 80),
}
CAPTURE_SIZES = {
    "nav": (540, 190),
    "pnl": (540, 130),
    "daily": (540, 150),
    "price": (520, 120),
    "pnlc": (520, 84),
}
CAPTURE_CSS = (
    ".grid,.cards{grid-template-columns:1fr!important}.panel{overflow:visible}"
    "svg[data-piece]{width:auto!important;height:auto!important;max-width:none!important;margin:14px 0}"
    "td.spark{padding:12px 14px!important}"
)


def _viewbox(kind: str, capture: bool, quote: str = '"') -> str:
    """A chart's viewBox, plus a fixed width and height when the page is captured."""
    w, h = (CAPTURE_SIZES if capture else SCREEN_SIZES)[kind]
    q = quote
    fixed = f" width={q}{w}{q} height={q}{h}{q}" if capture else ""
    return f"viewBox={q}0 0 {w} {h}{q}{fixed}"


def _freshness(data: dict[str, Any]) -> str:
    notes = [str(n) for n in data.get("notes", []) if str(n).startswith("基準日より前の終値:")]
    if not notes:
        return ""
    return (
        '<div class="err freshness" role="note"><b>価格の更新状況</b><br>'
        + "<br>".join(_esc(n) for n in notes)
        + "</div>"
    )


def _overview(data: dict[str, Any]) -> str:
    """Compact overview of the same series and risk payload used in the details."""
    risk = data.get("risk")
    metrics = '<p class="overview-note">リスク指標は未取得</p>'
    if risk:
        stats = risk.get("stats") or {}
        concentration = risk.get("concentration") or {}
        breaches = risk.get("policy_breaches")
        tiles = [
            (
                "年率ボラティリティ",
                _ratio(stats.get("vol_annual")),
                "現在ウェイト・過去の値動きから推定",
            ),
            (
                "VaR 1日 95%",
                jpy(stats.get("var_1d_95_jpy")) + " 円",
                "過去シミュレーション・損失額の目安",
            ),
            (
                "外貨比率",
                _ratio(concentration.get("foreign_currency_ratio")),
                "ルックスルー後・総資産比",
            ),
            (
                "限度",
                "未取得" if breaches is None else f"超過 {int(breaches)} 件",
                "設定済みポリシー（draft）",
            ),
        ]
        cards = "".join(
            f'<a class="overview-metric" href="#risk"><span>{_esc(label)}</span><b>{_esc(value)}</b><small>{_esc(note)}</small></a>'
            for label, value, note in tiles
        )
        contributors = sorted(
            [
                r
                for r in (risk.get("contributions") or {}).get("positions", [])
                if r.get("risk_share") is not None
            ],
            key=lambda r: r["risk_share"],
            reverse=True,
        )[:2]
        leaders = (
            " · ".join(f"{_esc(r['sym'])} {_ratio(r['risk_share'])}" for r in contributors)
            or "未取得"
        )
        metrics = f'<div class="overview-metrics">{cards}</div><p class="overview-note">リスク寄与上位：<b>{leaders}</b> <small>分散への寄与率・保有比率とは異なる</small> <a href="#risk">リスク詳細へ →</a></p>'
    return f"""
<div class="grid overview-charts">
  <div class="panel">
    <h2>NAV と累計入金 <small>全口座 · {_esc(data["window"]["start"])} → {_esc(data["as_of"])}</small></h2>
    <div class="legend"><span><i style="background:var(--series-1)"></i>NAV ¥</span><span><i style="background:var(--series-2)"></i>累計入金 ¥</span></div>
    <svg id="overview-nav" viewBox="0 0 860 220" role="img" aria-label="主要時系列：全口座NAVと累計入金"></svg>
    <a class="overview-link" href="#charts-top">詳細時系列へ →</a>
  </div>
  <div class="panel">
    <h2>累計PL <small>NAV − 累計入金 · 入金の影響を除く</small></h2>
    <div class="legend"><span><i style="background:var(--series-1)"></i>損益 ¥</span></div>
    <svg id="overview-pnl" viewBox="0 0 860 220" role="img" aria-label="主要時系列：全口座の累計PL"></svg>
    <a class="overview-link" href="#charts-top">日次PL・銘柄別の推移へ →</a>
  </div>
</div>
<div class="panel overview-risk"><h2>主要リスク <small>詳細と同じ計算値</small></h2>{metrics}</div>
"""


def render(data: dict[str, Any], tokens_css: str, capture: bool = False) -> str:
    """The dashboard page. ``capture`` lays it out for cutting the charts out into the mail."""
    h = data["headline"]
    fx = data["fx"]
    tape = "".join(
        f"<span class='tk'><b>{_esc(t['sym'])}</b> {price(t['last'], t.get('cur', 'USD'))} <i class='{cls(t['chg_pct'])}'>{pct(t['chg_pct'])}</i></span>"
        for t in data["tape"]
    )
    rate = data["fx"]["last"]
    kpis = "".join(
        [
            _kpi(
                "総資産 NAV ¥",
                jpy(h["nav_total"]),
                f"時価評価 {int(h['quoted_share'] * 100)}% · 残りは残高据え置き",
                sub2=_joined(
                    "" if h.get("nav_after_tax") is None else f"税引後 {jpy(h['nav_after_tax'])}",
                    usd(h.get("nav_after_tax"), rate),
                ),
                dollars=usd(h["nav_total"], rate),
            ),
            _kpi(
                "日次損益 ¥",
                jpy(h["day_pnl"], True),
                " · ".join(
                    t
                    for t in (pct(h["day_pnl_pct"]), split(h.get("day_stock"), h.get("day_fx")))
                    if t
                ),
                cls(h["day_pnl"]),
                sub2=_joined(
                    after_tax(h.get("day_after_tax")), usd(h.get("day_after_tax"), rate, True)
                ),
                dollars=usd(h["day_pnl"], rate, True),
            ),
            _kpi(
                "含み損益 ¥",
                jpy(h["unrealized_known"], True),
                split(h.get("unreal_stock"), h.get("unreal_fx")) or "原価が台帳にある保有",
                cls(h["unrealized_known"]),
                sub2=_joined(
                    after_tax(h.get("unreal_after_tax")), usd(h.get("unreal_after_tax"), rate, True)
                ),
                dollars=usd(h["unrealized_known"], rate, True),
            ),
            _kpi(
                f"期間損益 ¥ · {data['window']['days']}日",
                jpy(h["pnl_window"], True),
                f"全口座 {data['window']['start']} 以降・入金控除後",
                cls(h["pnl_window"]),
                dollars=usd(h["pnl_window"], rate, True),
            ),
            _kpi(
                "開設来損益 ¥",
                jpy(h["pnl_incept"], True),
                f"実現 {jpy(h['realized_cum'], True)} · 配当 {jpy(h['dividends_net'], True)}",
                cls(h["pnl_incept"]),
                dollars=usd(h["pnl_incept"], rate, True),
            ),
            _kpi(
                "資金加重リターン",
                pct(None if h.get("xirr") is None else h["xirr"] * 100),
                f"{h.get('xirr_scope') or '—'} · 最大DD（期間内） {pct(None if h.get('max_dd_window') is None else h['max_dd_window'] * 100, 1)}",
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
        f"<tr><td>{_esc(a['name'])}</td><td class='n'>{jpy(a['total'])}<span class='sp'>{usd(a['total'], rate)}</span></td>"
        f"<td class='n {cls(a['day_pnl'])}'>{jpy(a['day_pnl'], True)}{_split_under(a, 'day_stock', 'day_fx', 'day_after_tax', usd(a['day_pnl'], rate, True))}</td>"
        f"<td class='n {cls(a['unrealized'])}'>"
        f"{jpy(a['unrealized'], True) + _split_under(a, 'unreal_stock', 'unreal_fx', 'unreal_after_tax', usd(a['unrealized'], rate, True)) if a['unrealized'] is not None else '<small>原価なし</small>'}</td></tr>"
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
            f"<svg class='c-price' {_viewbox('price', capture, "'")} data-piece='price:{_esc(key)}' role='img' aria-label='{_esc(sym)} の株価'></svg>"
            f"<div class='lab'>{_esc(s['label'])} ¥<span class='{cls(pnl_now)}'>{jpy(pnl_now, True)}</span></div>"
            f"<svg class='c-pnl' {_viewbox('pnlc', capture, "'")} data-piece='pnlc:{_esc(key)}' role='img' aria-label='{_esc(sym)} の損益'></svg>"
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
.kpi .u{{display:block;font-family:var(--mono);font-size:12px;color:var(--ink-3);margin-top:2px}}
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
.sp{{display:block;font-size:10.5px;line-height:1.35;color:var(--ink-3);margin-top:2px}}
.pos td.spark svg{{width:96px;max-width:none;height:26px;display:block}}
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
.overview-risk{{margin-top:10px}}
.overview-metrics{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:10px}}
.overview-metric{{display:flex;flex-direction:column;gap:5px;padding:10px;border:1px solid var(--rule);border-radius:8px;color:var(--ink);text-decoration:none}}
.overview-metric span,.overview-metric small,.overview-note{{font-size:11px;color:var(--ink-3)}}
.overview-metric b{{font-family:var(--mono);font-size:22px;font-weight:500;overflow-wrap:anywhere}}
.overview-metric:hover,.overview-metric:focus-visible{{border-color:var(--accent)}}
.overview-link,.overview-note a{{font-size:11px;color:var(--accent)}}
.overview-note{{margin:12px 0 0;line-height:1.8}}.overview-note b{{color:var(--ink)}}
.overview-charts{{grid-template-columns:repeat(2,minmax(0,1fr))}}
.overview-charts svg{{display:block;width:100%;height:auto}}
@media(max-width:650px){{.overview-metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}.overview-charts{{grid-template-columns:1fr}}}}
/* risk */
.rgrid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}}
.rgrid .wide{{grid-column:1/-1}}
.xg{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:4px 18px}}
.xg2{{display:grid;grid-template-columns:1fr 1fr;gap:4px 18px}}
@media (max-width:900px){{.rgrid,.xg2{{grid-template-columns:1fr}}}}
.panel h3{{font-family:var(--mono);font-size:10px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);margin:10px 0 2px}}
.lim{{display:inline-block;border-radius:999px;padding:2px 9px;margin:2px 4px 2px 0;font-size:11px;border:1px solid var(--rule);color:var(--ink-2)}}
.lim.breach{{border-color:var(--series-2);color:var(--series-2);font-weight:700}}
.lim.na{{opacity:.55}}
.bar{{height:8px;background:var(--accent);border-radius:2px;min-width:1px}}.bar.neg{{background:var(--series-2)}}
.mini td.b{{width:34%;padding-left:0}}
.mini.rs td:first-child{{width:50%}}
{CAPTURE_CSS if capture else ""}
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

{_freshness(data)}
<h2 class="sec">ヘッドライン <small>headline</small></h2>
<div class="kpis">{kpis}</div>

<h2 class="sec" id="general">一般データ <small>general</small></h2>
{_overview(data) if not capture else ""}
<div class="grid">
  <div class="panel">
    <h2>口座別 <small>評価額 / 日次 / 含み</small></h2>
    <table class="mini"><thead><tr><th>口座</th><th>評価額 ¥</th><th>日次損益 ¥</th><th>含み損益 ¥</th></tr></thead><tbody>{accounts}</tbody></table>
    <h2 style="margin-top:12px">資産配分 <small>総資産比</small></h2>
    <div class="alloc">{alloc}</div>
  </div>
  <div class="panel">{_attribution(data["attribution"], {a["id"]: a["name"] for a in data["accounts"]})}</div>
</div>
{_risk(data.get("risk"))}
<div class="tw">{_positions_table(data["positions"], data["fx"]["last"])}</div>

<h2 class="sec" id="charts-top">時系列 <small>time series · {_esc(data["window"]["start"])} → {_esc(data["as_of"])}</small></h2>
<div class="grid">
  <div class="panel">
    <h2>全口座 NAV と損益 <small>3 口座の合計 · 入金は段差、損益 ＝ NAV − 累計入金</small></h2>
    <div class="legend"><span><i style="background:var(--series-1)"></i>NAV ¥</span><span><i style="background:var(--series-2)"></i>累計入金 ¥</span></div>
    <svg id="c-nav" {_viewbox("nav", capture)} data-piece="nav" role="img" aria-label="全口座の NAV と累計入金"></svg>
    <div class="legend" style="margin-top:8px"><span><i style="background:var(--series-1)"></i>損益 ¥（NAV − 累計入金）</span></div>
    <svg id="c-pnl" {_viewbox("pnl", capture)} data-piece="pnl" role="img" aria-label="全口座の累計損益"></svg>
  </div>
  <div class="panel">
    <h2>日次損益 <small>全口座 · 入金を除いた NAV の日次変化</small></h2>
    <svg id="c-daily" {_viewbox("daily", capture)} data-piece="daily" role="img" aria-label="日次損益の棒グラフ"></svg>
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
function yl(v){{const a=Math.abs(v);return a>=1e8?(v/1e8).toFixed(1)+"億":a>=1e4?Math.round(v/1e4)+"万":a>=1?Math.round(v).toString():a===0?"0":v.toFixed(2);}}
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
function drawOverview(){{
const ovNav=document.getElementById("overview-nav"),ovPnl=document.getElementById("overview-pnl");
for(const svg of [ovNav,ovPnl]){{if(svg){{svg.replaceChildren();svg.setAttribute("viewBox",`0 0 ${{Math.max(280,Math.round(svg.clientWidth))}} 220`);}}}}
if(ovNav)lineChart(ovNav,dates,[{{v:S.nav,cls:"l1"}},{{v:S.deposits,cls:"l2",end:false}}],{{ny:4,tip:i=>`${{jd(dates[i])}}\nNAV ${{fmt(S.nav[i])}} 円\n累計入金 ${{fmt(S.deposits[i])}} 円`}});
if(ovPnl)lineChart(ovPnl,dates,[{{v:S.pnl,cls:"l1"}}],{{zero:true,area:true,ny:3,tip:i=>`${{jd(dates[i])}}\n損益 ${{sfmt(S.pnl[i])}} 円`}});

}}
drawOverview();
window.addEventListener("resize",drawOverview);
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
  /* every drawn chart's box, for cutting them out of a screenshot into the mail */
  const pieces={{}};document.querySelectorAll("[data-piece]").forEach(n=>{{const s=n.tagName.toLowerCase()==="svg"?n:n.querySelector("svg");if(!s)return;const r=s.getBoundingClientRect();pieces[n.getAttribute("data-piece")]=[Math.round(r.left+window.scrollX),Math.round(r.top+window.scrollY),Math.round(r.width),Math.round(r.height)];}});
  document.body.dataset.pieces=JSON.stringify(pieces);
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
