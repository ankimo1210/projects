from __future__ import annotations

import argparse
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "01_mvp_walkthrough.ipynb"
RUNTIME_DIRECTORY = WORKSPACE_ROOT / "_scratch" / "jhrmbs-jupyter-runtime"
RUNTIME_DIRECTORY.mkdir(parents=True, exist_ok=True, mode=0o700)
RUNTIME_DIRECTORY.chmod(0o700)
os.environ["JUPYTER_RUNTIME_DIR"] = str(RUNTIME_DIRECTORY)
os.environ["TMPDIR"] = str(RUNTIME_DIRECTORY)

import nbformat  # noqa: E402
from nbclient import NotebookClient  # noqa: E402


def build_notebook() -> nbformat.NotebookNode:
    cells = [
        nbformat.v4.new_markdown_cell(
            """# JHRMBS public-data MVP walkthrough

この Notebook は、CLI で作成済みの immutable artifact を読み、データ品質、回号月次 CPR、
時系列・vintage OOS、将来 cashflow と WAL を検証します。取得・変換・学習ロジックは
`jhrmbs` package にあり、Notebook 内に複製しません。

単位は `_pct` が百分率、SMM/Factor は小数、金額は JPY です。モデル特徴量は原則1か月 lag です。"""
        ),
        nbformat.v4.new_code_cell(
            """from pathlib import Path
import json
import matplotlib.pyplot as plt
import pandas as pd

from jhrmbs.artifacts import read_table
from jhrmbs.cashflow_service import create_issue_cashflow
from jhrmbs.config import load_config
from jhrmbs.forecast import fixed_psj_forecast, forecast_issue
from jhrmbs.models.training import resolve_run_directory
from jhrmbs.paths import DataPaths

WORKSPACE_ROOT = Path.cwd()
CONFIG_PATH = WORKSPACE_ROOT / "JHRMBS" / "config" / "default.yml"
config = load_config(CONFIG_PATH)
paths = DataPaths(config.data_root)
print(f"data root: {config.data_root}")"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 1. Data contract and quality

panel の grain、必須値、Factor の範囲・単調性、reconciliation を確認します。critical finding が
あれば `build-dataset` 自体が失敗します。reconciliation は異なる減少概念の診断で、完全一致は
要求しません。"""
        ),
        nbformat.v4.new_code_cell(
            """panel = read_table(paths.processed / "issue_month_panel.parquet")
issues = read_table(paths.processed / "issues.parquet")
features = read_table(paths.features / "model_features.parquet")
quality = json.loads((paths.processed / "data_quality_report.json").read_text(encoding="utf-8"))

coverage = pd.DataFrame({
    "metric": ["rows", "issues", "observed rows", "first month", "last observed month", "critical findings"],
    "value": [
        len(panel), panel["issue_id"].nunique(), int(panel["is_observed"].sum()),
        panel["payment_month"].min().date(),
        panel.loc[panel["is_observed"], "payment_month"].max().date(),
        quality["panel"]["critical_count"],
    ],
})
coverage"""
        ),
        nbformat.v4.new_code_cell(
            """finding_columns = ["severity", "check", "failed_count", "failed_rate", "message"]
findings = pd.DataFrame(quality["panel"]["findings"])
findings[finding_columns] if not findings.empty else pd.DataFrame(columns=finding_columns)"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 2. Observed prepayment panel

将来予定行を除き、公表 CPR の分布と vintage 差を確認します。これは borrower-level 分布ではなく、
回号プール月次の分布です。"""
        ),
        nbformat.v4.new_code_cell(
            """observed = panel[panel["voluntary_cpr_pct"].notna()].copy()
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].hist(observed["voluntary_cpr_pct"], bins=35, color="#1f5a94", alpha=0.85)
axes[0].set(title="Published voluntary CPR", xlabel="CPR (% / year)", ylabel="Issue-month count")
vintage = observed.groupby("vintage_year")["voluntary_cpr_pct"].median()
axes[1].plot(vintage.index, vintage.values, marker="o", color="#d49a24")
axes[1].set(title="Median CPR by vintage", xlabel="Issue vintage", ylabel="Median CPR (%)")
for axis in axes:
    axis.grid(axis="y", alpha=0.25)
plt.tight_layout();"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 3. Out-of-sample comparison

固定 PSJ、seasoning、金利 proxy 付き、full model を、暦月 holdout と最新 vintage holdout で
比較します。主指標は前月残高加重 RMSE（CPR percentage point）です。"""
        ),
        nbformat.v4.new_code_cell(
            """run_directory = resolve_run_directory(config)
metrics = read_table(run_directory / "metrics.parquet")
display_columns = [
    "split", "model", "train_rows", "test_rows", "rate_proxy_share",
    "weighted_rmse_cpr_pct", "weighted_mae_cpr_pct",
    "cashflow_cumulative_principal_mae_pct", "truncated_wal_mae_years",
]
metrics[display_columns].sort_values(["split", "weighted_rmse_cpr_pct"])"""
        ),
        nbformat.v4.new_code_cell(
            """pivot = metrics.pivot(index="model", columns="split", values="weighted_rmse_cpr_pct")
pivot.plot.bar(figsize=(9, 4), color=["#1f5a94", "#d49a24"])
plt.ylabel("Weighted RMSE (CPR percentage point)")
plt.xlabel("Model")
plt.title("OOS error by split")
plt.grid(axis="y", alpha=0.25)
plt.xticks(rotation=0)
plt.tight_layout();"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 4. Issue forecast and cashflow

直近実績より後に JHF 予定 Factor がある通常回号を自動選択します。モデル将来予測は直近の外部
状態を固定し、予定 Factor path だけを既知 schedule として使います。固定 PSJ と WAL を比較します。"""
        ),
        nbformat.v4.new_code_cell(
            """observed_end = (
    panel[panel["is_observed"]].groupby("issue_id")["payment_month"].max().rename("observed_end")
)
candidates = panel.join(observed_end, on="issue_id")
candidates = candidates[
    (candidates["series_type"] == "monthly") &
    (candidates["payment_month"] > candidates["observed_end"])
]
future_counts = candidates.groupby("issue_id").size().sort_values(ascending=False)
issue_id = str(future_counts.index[0])
model_forecast = forecast_issue(config, issue_id, model_name="champion", save=False)
psj_forecast = fixed_psj_forecast(config, issue_id, terminal_cpr_pct=6.0)
selected_model_name = str(model_forecast["model_name"].iloc[0])
issue_id, selected_model_name, len(model_forecast), model_forecast["payment_month"].max().date()"""
        ),
        nbformat.v4.new_code_cell(
            """history = panel[(panel["issue_id"] == issue_id) & panel["voluntary_cpr_pct"].notna()].tail(48)
plt.figure(figsize=(11, 4.5))
plt.plot(history["payment_month"], history["voluntary_cpr_pct"], color="#172033", label="Published CPR")
plt.plot(model_forecast["payment_month"], model_forecast["predicted_cpr_pct"], color="#1f5a94", label=selected_model_name)
plt.plot(psj_forecast["payment_month"], psj_forecast["predicted_cpr_pct"], "--", color="#d49a24", label="Fixed PSJ 6%")
plt.ylabel("CPR (% / year)")
plt.xlabel("Payment month")
plt.title(f"{issue_id}: historical and forecast voluntary prepayment")
plt.grid(axis="y", alpha=0.25)
plt.legend(frameon=False)
plt.tight_layout();"""
        ),
        nbformat.v4.new_code_cell(
            """model_cf, model_risk = create_issue_cashflow(config, issue_id, scenario="model", save=False)
psj_cf, psj_risk = create_issue_cashflow(config, issue_id, scenario="psj", save=False)
pd.DataFrame([
    {"scenario": selected_model_name, **model_risk},
    {"scenario": "fixed_psj_6pct", **psj_risk},
])[[
    "scenario", "wal_years", "dirty_price_per_100", "macaulay_duration_years",
    "effective_duration_years", "convexity", "annual_effective_yield_pct",
]]"""
        ),
        nbformat.v4.new_markdown_cell(
            """## 5. Interpretation guardrails

- OOS 順位が split 間で逆転する場合、最良 model を確定せず regime / vintage 安定性を追加検証する。
- `rate_proxy_share` が高い期間の rate coefficient は借換効果と因果解釈しない。
- truncated WAL error と将来全期間 WAL は別指標である。
- clean-up call、回収月と支払月の lag、個別借換費用、OAS は MVP の外部仮定である。
"""
        ),
    ]
    return nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    notebook = build_notebook()
    if args.execute:
        NotebookClient(notebook, timeout=180, kernel_name="python3").execute(
            cwd=str(WORKSPACE_ROOT)
        )
    NOTEBOOK_PATH.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, NOTEBOOK_PATH)
    print(NOTEBOOK_PATH)


if __name__ == "__main__":
    main()
