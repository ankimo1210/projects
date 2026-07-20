from __future__ import annotations

import html
import io
import math
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd

matplotlib.use("Agg")
from matplotlib import font_manager, pyplot as plt  # noqa: I001

from jhrmbs.artifacts import read_table
from jhrmbs.cashflow_service import create_issue_cashflow
from jhrmbs.config import AppConfig
from jhrmbs.forecast import fixed_psj_forecast, forecast_issue
from jhrmbs.models.training import resolve_run_directory
from jhrmbs.paths import DataPaths
from jhrmbs.util import atomic_write_bytes, atomic_write_json, read_json, utc_now

BLUE = "#1f5a94"
GOLD = "#d49a24"
INK = "#172033"
GRID = "#d8dee9"


def _configure_cjk_font() -> None:
    for family in (
        "Noto Sans CJK JP",
        "Droid Sans Fallback",
        "Yu Gothic",
        "MS Gothic",
    ):
        try:
            font_manager.findfont(family, fallback_to_default=False)
        except ValueError:
            continue
        matplotlib.rcParams["font.family"] = ["DejaVu Sans", family]
        return


_configure_cjk_font()


def _svg() -> str:
    buffer = io.StringIO()
    plt.savefig(buffer, format="svg", bbox_inches="tight", metadata={"Date": None})
    plt.close()
    value = buffer.getvalue()
    return value[value.find("<svg") :]


def _prepayment_chart(
    history: pd.DataFrame,
    model_forecast: pd.DataFrame,
    psj_forecast: pd.DataFrame,
) -> str:
    plt.figure(figsize=(9.2, 4.5))
    recent = history[history["voluntary_cpr_pct"].notna()].tail(36)
    forecast_end = pd.Timestamp(model_forecast["payment_month"].min()) + pd.DateOffset(months=59)
    model_view = model_forecast[model_forecast["payment_month"] <= forecast_end]
    psj_view = psj_forecast[psj_forecast["payment_month"] <= forecast_end]
    plt.plot(
        recent["payment_month"],
        recent["voluntary_cpr_pct"],
        color=INK,
        linewidth=1.8,
        label="公表 CPR（実績）",
    )
    plt.plot(
        model_view["payment_month"],
        model_view["predicted_cpr_pct"],
        color=BLUE,
        linewidth=2.2,
        label="fractional logit",
    )
    plt.plot(
        psj_view["payment_month"],
        psj_view["predicted_cpr_pct"],
        color=GOLD,
        linewidth=2.0,
        linestyle="--",
        label="固定 PSJ",
    )
    plt.ylabel("CPR（% / 年）")
    plt.xlabel("支払月")
    plt.title("任意期限前償還率：直近実績と今後5年のシナリオ")
    plt.grid(axis="y", color=GRID, linewidth=0.7)
    plt.legend(frameon=False, ncol=3, fontsize=9)
    plt.tight_layout()
    return _svg()


def _cashflow_chart(model: pd.DataFrame, psj: pd.DataFrame) -> str:
    def annual(frame: pd.DataFrame) -> pd.Series:
        year = pd.to_datetime(frame["payment_date"]).dt.year
        return frame.groupby(year)["total_principal"].sum() / 100_000_000.0

    model_annual = annual(model)
    psj_annual = annual(psj)
    years = sorted(set(model_annual.index) | set(psj_annual.index))
    x = list(range(len(years)))
    width = 0.38
    plt.figure(figsize=(9.2, 4.5))
    plt.bar(
        [value - width / 2 for value in x],
        [float(model_annual.get(year, 0.0)) for year in years],
        width=width,
        color=BLUE,
        label="fractional logit",
    )
    plt.bar(
        [value + width / 2 for value in x],
        [float(psj_annual.get(year, 0.0)) for year in years],
        width=width,
        color=GOLD,
        label="固定 PSJ",
    )
    step = max(len(years) // 10, 1)
    shown = x[::step]
    plt.xticks(shown, [str(years[value]) for value in shown], rotation=45)
    plt.ylabel("年間元本（億円）")
    plt.xlabel("支払年")
    plt.title("予測元本キャッシュフロー")
    plt.grid(axis="y", color=GRID, linewidth=0.7)
    plt.legend(frameon=False)
    plt.tight_layout()
    return _svg()


def _format_number(value: object, decimals: int = 2) -> str:
    if value is None:
        return "—"
    try:
        number = float(str(value))
    except ValueError:
        return "—"
    if not math.isfinite(number):
        return "—"
    return f"{number:,.{decimals}f}"


def _summary_table(model: dict[str, Any], psj: dict[str, Any]) -> str:
    rows = (
        ("WAL（年）", "wal_years", 2),
        ("Dirty price / 100", "dirty_price_per_100", 3),
        ("Effective duration（年）", "effective_duration_years", 3),
        ("Convexity", "convexity", 2),
        ("元本合計（億円）", "total_principal_jpy", 2),
        ("利息合計（億円）", "total_interest_jpy", 2),
    )
    body: list[str] = []
    for label, key, decimals in rows:
        divisor = 100_000_000.0 if key.endswith("_jpy") else 1.0
        body.append(
            "<tr>"
            f"<th>{html.escape(label)}</th>"
            f"<td>{_format_number(float(model[key]) / divisor, decimals)}</td>"
            f"<td>{_format_number(float(psj[key]) / divisor, decimals)}</td>"
            "</tr>"
        )
    return "".join(body)


def _metrics_table(metrics: pd.DataFrame, model_name: str) -> str:
    selected = metrics[metrics["model"].isin(["fixed_psj", model_name])].copy()
    if selected.empty:
        return "<p>評価結果を取得できませんでした。</p>"
    selected = selected[
        [
            "split",
            "model",
            "weighted_rmse_cpr_pct",
            "weighted_mae_cpr_pct",
            "cashflow_cumulative_principal_mae_pct",
            "truncated_wal_mae_years",
        ]
    ].rename(
        columns={
            "split": "分割",
            "model": "モデル",
            "weighted_rmse_cpr_pct": "加重 RMSE (CPR pt)",
            "weighted_mae_cpr_pct": "加重 MAE (CPR pt)",
            "cashflow_cumulative_principal_mae_pct": "累積元本誤差 (%)",
            "truncated_wal_mae_years": "観測窓 WAL 誤差 (年)",
        }
    )
    rendered = selected.to_html(
        index=False,
        border=0,
        classes=["metric-table"],
        float_format=lambda value: f"{value:.3f}",
    )
    return rendered


def generate_issue_report(
    config: AppConfig,
    issue_id: str,
    *,
    model_name: str = "champion",
    run_id: str | None = None,
    psj_terminal_cpr_pct: float = 6.0,
    valuation_yield_pct: float | None = None,
    cleanup_call: bool = False,
) -> Path:
    paths = DataPaths(config.data_root)
    panel = read_table(paths.processed / "issue_month_panel.parquet")
    issues = read_table(paths.processed / "issues.parquet")
    issue_history = panel[panel["issue_id"] == issue_id].sort_values("payment_month")
    issue_record = issues[issues["issue_id"] == issue_id]
    if issue_history.empty or issue_record.empty:
        raise ValueError(f"unknown issue: {issue_id}")

    model_forecast = forecast_issue(
        config, issue_id, model_name=model_name, run_id=run_id, save=True
    )
    selected_model_name = str(model_forecast["model_name"].iloc[0])
    psj_forecast = fixed_psj_forecast(config, issue_id, terminal_cpr_pct=psj_terminal_cpr_pct)
    model_cashflow, model_summary = create_issue_cashflow(
        config,
        issue_id,
        scenario="model",
        model_name=model_name,
        run_id=run_id,
        valuation_yield_pct=valuation_yield_pct,
        cleanup_call=cleanup_call,
        save=True,
    )
    psj_cashflow, psj_summary = create_issue_cashflow(
        config,
        issue_id,
        scenario="psj",
        psj_terminal_cpr_pct=psj_terminal_cpr_pct,
        valuation_yield_pct=valuation_yield_pct,
        cleanup_call=cleanup_call,
        save=True,
    )
    run_directory = resolve_run_directory(config, run_id)
    metrics = read_table(run_directory / "metrics.parquet")
    quality = read_json(paths.processed / "data_quality_report.json", {})
    panel_quality = quality.get("panel", {}) if isinstance(quality, dict) else {}
    feature_quality = quality.get("features", {}) if isinstance(quality, dict) else {}
    rate_missing = (
        feature_quality.get("rate_feature_missing_rate", float("nan"))
        if isinstance(feature_quality, dict)
        else float("nan")
    )

    current = issue_history[issue_history["actual_factor"].notna()].iloc[-1]
    issue = issue_record.iloc[0]
    prepayment_svg = _prepayment_chart(issue_history, model_forecast, psj_forecast)
    cashflow_svg = _cashflow_chart(model_cashflow, psj_cashflow)
    sources = {source.id: source.url for source in config.sources}
    rate_note = (
        "設定された同一定義の住宅ローン金利系列を使用"
        if not bool(model_forecast["rate_feature_is_proxy"].iloc[0])
        else "過去の機械可読な公式フラット35系列がないため WAC−JGB 10年を proxy として使用"
    )
    title = f"{issue_id} 回号別期限前償還・キャッシュフローレポート"
    generated_at = utc_now()
    report_html = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{--ink:{INK};--blue:{BLUE};--gold:{GOLD};--paper:#fff;--muted:#5f6b7a;--line:#d8dee9;}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans JP",sans-serif;color:var(--ink);margin:0;background:#f4f6f9;line-height:1.62;}}
main{{max-width:1080px;margin:28px auto;padding:42px 52px;background:var(--paper);box-shadow:0 4px 24px #17203318;}}
h1{{font-size:2rem;line-height:1.25;margin:0 0 6px;border-bottom:4px solid var(--blue);padding-bottom:14px;}}
h2{{font-size:1.35rem;margin-top:42px;border-left:5px solid var(--gold);padding-left:12px;}}
h3{{font-size:1.05rem;margin-top:26px;}} .meta,.note{{color:var(--muted);font-size:.92rem;}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:22px 0;}}
.card{{border:1px solid var(--line);border-top:4px solid var(--blue);padding:13px;border-radius:4px;}}
.card span{{display:block;color:var(--muted);font-size:.8rem;}} .card strong{{font-size:1.25rem;}}
.chart{{border:1px solid var(--line);padding:12px;margin:16px 0;background:#fff;overflow-x:auto;}}
.chart svg{{width:100%;height:auto;}} table{{border-collapse:collapse;width:100%;font-size:.9rem;}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;}} th:first-child,td:first-child{{text-align:left;}}
thead th{{background:#eef3f8;}} .callout{{background:#eef5fb;border-left:5px solid var(--blue);padding:14px 18px;}}
code{{background:#f2f4f7;padding:2px 5px;}} a{{color:var(--blue);}} ul{{padding-left:22px;}}
@media(max-width:760px){{main{{margin:0;padding:24px 18px}}.cards{{grid-template-columns:repeat(2,1fr)}}}}
@media print{{body{{background:#fff}}main{{box-shadow:none;margin:0;max-width:none}}}}
</style></head><body><main>
<h1>{html.escape(title)}</h1>
<p class="meta">生成日時 {generated_at:%Y-%m-%d %H:%M UTC} / model run <code>{html.escape(run_directory.name)}</code></p>

<h2>Technical summary</h2>
<p class="callout">JHF 公開プールデータから推定した <strong>{html.escape(selected_model_name)}</strong> モデルと、
終端 CPR {psj_terminal_cpr_pct:.1f}% の固定 PSJ を比較する。既定の <code>champion</code> は
両 OOS split の平均順位で run ごとに選択する。評価利回りは年率
{float(model_summary["annual_effective_yield_pct"]):.2f}%（年複利）、価格は経過利息控除前の dirty price。
本結果は公開データのみを用いた調査用 MVP であり、売買価格・公式評価ではない。</p>
<div class="cards">
<div class="card"><span>直近実績月</span><strong>{pd.Timestamp(current["payment_month"]):%Y-%m}</strong></div>
<div class="card"><span>実績 Factor</span><strong>{float(current["actual_factor"]):.5f}</strong></div>
<div class="card"><span>WAC</span><strong>{_format_number(current["wac_pct"])}%</strong></div>
<div class="card"><span>モデル WAL</span><strong>{float(model_summary["wal_years"]):.2f} 年</strong></div>
</div>

<h2>回号と計算前提</h2>
<table><tbody>
<tr><th>回号名</th><td>{html.escape(str(issue["issue_name"]))}</td></tr>
<tr><th>発行日</th><td>{pd.Timestamp(issue["issue_date"]):%Y-%m-%d}</td></tr>
<tr><th>発行額面</th><td>{float(issue["face_amount_jpy"]) / 100_000_000:,.2f} 億円</td></tr>
<tr><th>表面利率</th><td>{float(issue["coupon_pct"]):.3f}%</td></tr>
<tr><th>金利特徴量</th><td>{html.escape(rate_note)}</td></tr>
<tr><th>clean-up call</th><td>{"残高10%以下で仮定" if cleanup_call else "仮定しない"}</td></tr>
</tbody></table>

<h2>期限前償還の実績と予測</h2>
<p>CPR は年率、モデル内部では <code>SMM = 1-(1-CPR)^(1/12)</code> に変換する。
標準 PSJ は WALA 0か月で 0%、60か月で指定終端 CPR に達し、以降一定とした。</p>
<div class="chart">{prepayment_svg}</div>
<p class="note">実績は JHF 公表の「任意期限前償還率」。Factor から逆算する総減少には長期延滞・その他解約等が含まれ得るため、同一概念とは扱わない。</p>

<h2>キャッシュフローとリスク</h2>
<div class="chart">{cashflow_svg}</div>
<table><thead><tr><th>指標</th><th>{html.escape(selected_model_name)}</th><th>固定 PSJ</th></tr></thead>
<tbody>{_summary_table(model_summary, psj_summary)}</tbody></table>
<p class="note">予定元本は連続する JHF 当初予定 Factor の比率、任意期限前償還は予定元本控除後残高 × SMM、利息は月初残高 × coupon / 12。</p>

<h2>Out-of-sample 評価</h2>
<p>暦月 holdout と最新 vintage holdout の双方で再推定した。CPR 誤差は残高加重指標を主指標とし、累積元本と観測窓内 truncated WAL も確認する。</p>
{_metrics_table(metrics, selected_model_name)}

<h2>データ品質</h2>
<table><tbody>
<tr><th>panel 行数</th><td>{int(panel_quality.get("row_count", len(panel))):,}</td></tr>
<tr><th>回号数</th><td>{int(panel_quality.get("issue_count", panel["issue_id"].nunique())):,}</td></tr>
<tr><th>critical finding</th><td>{int(panel_quality.get("critical_count", 0))}</td></tr>
<tr><th>最新実績支払月</th><td>{html.escape(str(panel_quality.get("latest_observed_payment_month", "—")))}</td></tr>
<tr><th>金利特徴量の欠損率</th><td>{float(rate_missing):.2%}</td></tr>
</tbody></table>

<h2>データ品質・限界・頑健性</h2>
<ul>
<li>プール状態と公開マクロ特徴量は予測月より1か月ラグを置き、同月 CPR・Factor の混入を防いだ。</li>
<li>{html.escape(rate_note)}。これは借換え住宅ローン金利そのものではない。</li>
<li>プールレベル公開値から個別債務者の competing risk、借換費用、属性別 heterogeneity は識別できない。</li>
<li>回収月と MBS 支払月のラグ、差替え、端数処理、clean-up call の実際の条件は商品資料で別途確認が必要。</li>
<li>Duration・Convexity は期限前償還パスを固定した平行利回りシフト。OAS や金利連動 CPR ではない。</li>
</ul>

<h2>次の検証</h2>
<ol><li>公式フラット35金利の機械可読な履歴を補完し、proxy 使用率と係数安定性を再評価する。</li>
<li>GAM / mixed effects / gradient boosting を同じ OOS 契約で比較する。</li>
<li>商品要項に基づく支払ラグ、clean-up 条件、経過利息を明示し、金利パス別 OAS へ拡張する。</li></ol>

<h2>出典</h2><ul>
<li><a href="{html.escape(sources.get("jhf_monthly", ""))}">住宅金融支援機構：ファクター等毎月開示情報</a></li>
<li><a href="https://www.jsda.or.jp/shiryoshitsu/toukei/psj/index.html">日本証券業協会：標準期限前償還モデル（PSJモデル）</a></li>
<li><a href="{html.escape(sources.get("mof_jgb", ""))}">財務省：国債金利情報 CSV</a></li>
<li><a href="{html.escape(sources.get("flat35_current", ""))}">住宅金融支援機構：フラット35 現行金利</a></li>
<li><a href="{html.escape(sources.get("mlit_housing_starts", ""))}">国土交通省：住宅着工統計</a></li>
<li><a href="{html.escape(sources.get("boj_m3", ""))}">日本銀行：時系列統計データ検索サイト API</a></li>
</ul>
<p class="meta">Generated by JHRMBS 0.1.0. 入力ファイルの hash と加工履歴は raw manifest / processed lineage に保存。</p>
</main></body></html>"""
    output_directory = paths.reports / issue_id
    output_path = output_directory / f"{run_directory.name}_{selected_model_name}.html"
    atomic_write_bytes(output_path, report_html.encode("utf-8"))
    atomic_write_json(
        output_path.with_suffix(".json"),
        {
            "generated_at": generated_at.isoformat(),
            "issue_id": issue_id,
            "requested_model_name": model_name,
            "model_name": selected_model_name,
            "run_id": run_directory.name,
            "report_path": str(output_path),
            "charts": {
                "prepayment": "published historical CPR, fitted model forecast, fixed PSJ",
                "annual_principal": "annual projected principal under fitted model and fixed PSJ",
            },
            "model_summary": model_summary,
            "psj_summary": psj_summary,
        },
    )
    return output_path
