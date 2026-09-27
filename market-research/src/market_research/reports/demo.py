"""Standalone HTML report for the shared synthetic DemoRun contract."""

from __future__ import annotations

from html import escape
from importlib.resources import files
from math import isfinite

import pandas as pd

from market_research.services import DemoRun

_TOKENS = files(__package__).joinpath("tokens.css").read_text(encoding="utf-8")
_CHART_CSS = """
.chart {width:100%;min-width:640px}
.chart-grid {stroke:var(--grid);stroke-width:1}
.chart-line {fill:none;stroke-width:2.5;stroke-linejoin:round;stroke-linecap:round}
.chart-line.equity {stroke:var(--series-1)}
.chart-line.drawdown {stroke:var(--series-2)}
.chart-dot {opacity:0;transition:opacity .15s}
.chart-dot:hover,.chart-dot:focus {opacity:1}
.chart-dot.equity {fill:var(--series-1)}
.chart-dot.drawdown {fill:var(--series-2)}
.meta-table th {width:32%;text-align:left;white-space:normal}
.meta-table td {text-align:left;white-space:normal;overflow-wrap:anywhere}
"""


def _series_values(run: DemoRun) -> tuple[pd.DatetimeIndex, pd.Series, pd.Series]:
    index = run.prices.index
    equity = run.backtest.equity
    if (
        not isinstance(index, pd.DatetimeIndex)
        or index.tz is None
        or index.empty
        or index.has_duplicates
        or not index.is_monotonic_increasing
        or not index.equals(equity.index)
    ):
        raise ValueError("equity must match a nonempty, ordered, timezone-aware price index")
    for name, series in (
        ("equity", equity),
        ("turnover", run.backtest.turnover),
        ("costs", run.backtest.costs),
    ):
        if not index.equals(series.index):
            raise ValueError(f"{name} must match the price index")
        try:
            values = series.to_numpy(dtype=float)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be finite") from exc
        if not all(isfinite(value) for value in values):
            raise ValueError(f"{name} must be finite")
        if name == "equity" and any(value <= 0 for value in values):
            raise ValueError("equity must be positive")
        if name != "equity" and any(value < 0 for value in values):
            raise ValueError(f"{name} must be nonnegative")
    if not run.prices.columns.size or not run.bars:
        raise ValueError("DemoRun must include assets and price bars")
    peak = equity.cummax().clip(lower=1.0)
    drawdown = equity / peak - 1.0
    return index, equity, drawdown


def _chart(
    index: pd.DatetimeIndex,
    series: pd.Series,
    *,
    label: str,
    kind: str,
) -> str:
    values = [float(value) for value in series]
    low, high = min(values), max(values)
    if low == high:
        pad = max(abs(low) * 0.05, 0.01)
        low -= pad
        high += pad

    def x_at(position: int) -> float:
        return 50.0 + position * 740.0 / max(len(values) - 1, 1)

    def y_at(value: float) -> float:
        return 205.0 - (value - low) * 170.0 / (high - low)

    points = " ".join(f"{x_at(pos):.1f},{y_at(value):.1f}" for pos, value in enumerate(values))
    details = "".join(
        '<circle class="chart-dot '
        f'{kind}" cx="{x_at(pos):.1f}" cy="{y_at(value):.1f}" r="7" '
        'tabindex="0">'
        f"<title>{escape(timestamp.isoformat())}: {value:.4f}</title></circle>"
        for pos, (timestamp, value) in enumerate(zip(index, values, strict=True))
    )
    top = f"{high:.2f}" if kind == "equity" else f"{high:.2%}"
    bottom = f"{low:.2f}" if kind == "equity" else f"{low:.2%}"
    return (
        f'<svg class="chart" viewBox="0 0 840 240" role="img" '
        f'aria-label="{escape(label, quote=True)}">'
        f"<title>{escape(label)}</title>"
        '<line class="chart-grid" x1="50" y1="35" x2="790" y2="35"/>'
        '<line class="chart-grid" x1="50" y1="205" x2="790" y2="205"/>'
        f'<text x="4" y="39">{top}</text><text x="4" y="209">{bottom}</text>'
        f'<polyline class="chart-line {kind}" points="{points}"/>{details}</svg>'
    )


def render_demo_report(run: DemoRun) -> str:
    """Render an existing DemoRun as deterministic, self-contained offline HTML.

    The caller may write the returned UTF-8 string to a .html file. This
    reports the stored run; it does not fetch data or rerun the strategy.
    """
    if not isinstance(run, DemoRun):
        raise TypeError("render_demo_report requires a DemoRun")
    index, equity, drawdown = _series_values(run)
    assets = ", ".join(sorted(str(asset) for asset in run.prices.columns))
    providers = ", ".join(sorted({str(bar.provider) for bar in run.bars}))
    adjustments = ", ".join(sorted({str(bar.adjustment) for bar in run.bars}))
    revisions = ", ".join(sorted({str(bar.revision_id) for bar in run.bars}))
    warning_count = sum(bar.quality != "ok" for bar in run.bars)
    turnover = float(run.backtest.turnover.sum())
    costs = float(run.backtest.costs.sum())
    rate = f"{costs / turnover * 10_000:.2f} bps" if turnover else "算定不可（回転なし）"
    total_return = (float(equity.iloc[-1]) - 1.0) * 100.0
    max_drawdown = float(drawdown.min()) * 100.0
    metadata = (
        ("run ID", run.run_id),
        ("入力 SHA-256", run.input_hash),
        ("種別", run.mode),
        ("対象", assets),
        ("価格出典", providers),
        ("調整方式", adjustments),
        ("revision", revisions),
        ("基準通貨", run.backtest.base_currency),
        ("判断時刻の範囲", f"{index[0].isoformat()} – {index[-1].isoformat()}"),
        ("価格品質", f"{len(run.bars)} 本のうち注意・除外 {warning_count} 本"),
    )
    metadata_rows = "".join(
        f'<tr><th scope="row">{escape(key)}</th><td>{escape(str(value))}</td></tr>'
        for key, value in metadata
    )
    observation_rows = "".join(
        "<tr>"
        f"<td>{escape(timestamp.isoformat())}</td>"
        f'<td class="num">{float(value):.4f}</td>'
        f'<td class="num">{float(depth):.2%}</td>'
        "</tr>"
        for timestamp, value, depth in zip(index, equity, drawdown, strict=True)
    )
    equity_chart = _chart(index, equity, label="累積資産の推移", kind="equity")
    drawdown_chart = _chart(index, drawdown, label="ドローダウンの推移", kind="drawdown")
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>合成デモ研究レポート</title>
<style>
{_TOKENS}
{_CHART_CSS}
</style>
</head>
<body>
<div class="wrap">
<header class="mast">
  <div class="eyebrow"><span>市場研究</span><span>合成データ</span><b>run {escape(str(run.run_id))}</b></div>
  <h1>合成デモの評価<span class="sub">同じ run の累積資産とドローダウン</span></h1>
  <p class="lede">これは架空の価格と戦略による研究用の結果です。意思決定時点の目標ウェイトを
  <strong>1期遅れ</strong>で評価し、費用をリターンから控除しています。</p>
  <div class="strip">
    <div><span class="k">累積リターン</span><span class="v a">{total_return:+.2f}%</span>
      <span class="n">開始時の資産を 1 とした終点</span></div>
    <div><span class="k">最大ドローダウン</span><span class="v b">{max_drawdown:.2f}%</span>
      <span class="n">開始時 1 を含む過去最高値からの下落</span></div>
    <div><span class="k">判断時点</span><span class="v">{len(index)}</span>
      <span class="n">タイムゾーン付き価格観測</span></div>
    <div><span class="k">平均費用率</span><span class="v">{rate}</span>
      <span class="n">費用合計 ÷ 回転合計。手数料とスリッページの合算</span></div>
  </div>
</header>
<section>
  <div class="head"><span class="step">01</span><h2>累積資産と下落</h2></div>
  <div class="col"><p>費用控除後の資産指数です。各点の詳細はグラフ上にカーソルを置くか、下の表で確認できます。</p></div>
  <figure>
    <p class="figtitle">累積資産</p><p class="figsub">開始時 1、評価時点ごとの終値ベース</p>
    <div class="scroll">{equity_chart}</div>
    <figcaption><b>Fig 1</b>終点 {float(equity.iloc[-1]):.4f}。現実の約定価格は表していません。</figcaption>
  </figure>
  <figure>
    <p class="figtitle">ドローダウン</p><p class="figsub">過去最高値からの下落率、単位 %</p>
    <div class="scroll">{drawdown_chart}</div>
    <figcaption><b>Fig 2</b>最大下落 {max_drawdown:.2f}%。初期資産 1 を最高値の基準に含めます。</figcaption>
  </figure>
  <div class="tw"><table>
    <caption>各判断時点の資産指数とドローダウン</caption>
    <thead><tr><th>判断時刻</th><th>資産指数</th><th>ドローダウン</th></tr></thead>
    <tbody>{observation_rows}</tbody>
  </table></div>
</section>
<section>
  <div class="head"><span class="step">02</span><h2>出典と計算条件</h2></div>
  <div class="tw"><table class="meta-table"><tbody>{metadata_rows}</tbody></table></div>
  <div class="note"><span class="lab">読み方の注意</span>
    <p>費用率は保存された費用と回転額から計算した加重平均です。費用控除分の単純合計は
    {costs * 100:.3f} パーセントポイントで、複利の成績差ではありません。</p></div>
</section>
<section>
  <div class="head"><span class="step">03</span><h2>使えない範囲</h2></div>
  <ul>
    <li>合成データの結果であり、実市場での成績予測や投資助言ではありません。</li>
    <li>1期遅れの close-to-close 研究近似です。実際の翌営業日寄付や板上の約定は再現しません。</li>
    <li>基準通貨以外への FX 換算、実口座の損益・税金は含みません。</li>
  </ul>
</section>
<footer>market-research / synthetic-demo<br>入力 SHA-256: {escape(str(run.input_hash))}</footer>
</div>
</body>
</html>
"""
