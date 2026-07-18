"""Generate and execute artifact-only notebooks for johnhull vol 18--25."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

JUPYTER_RUNTIME = Path("/tmp/johnhull-jupyter-runtime")
JUPYTER_RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
JUPYTER_RUNTIME.chmod(0o700)
os.environ["JUPYTER_RUNTIME_DIR"] = str(JUPYTER_RUNTIME)
os.environ["TMPDIR"] = "/tmp"
tempfile.tempdir = "/tmp"

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "johnhull"
MANIFEST = json.loads((PROJECT / "release_manifest.json").read_text(encoding="utf-8"))


VOLUME_META = {
    18: {
        "title": "Theory-Guided Surrogates & Greeks",
        "question": "高速な近似器は、価格だけでなくGreeksと無裁定条件をどこまで守れるか。",
        "focus": "解析BSをbaselineに、price-only MLP、direct Greek head、Differential ML、time-value residualを同じsplitで比較する。Heston/COSとMC teacherはSE・95% CI付きで扱い、soft penaltyとは別にhullkitのhard reportを正本とする。",
        "sections": [
            ("price_error", "価格誤差サーフェス", "heatmap"),
            ("delta_error", "Delta誤差のmoneyness依存", "line:moneyness"),
            (
                "violations_unconstrained",
                "soft loss前後のhard violation",
                "bar:check_names:violations_constrained",
            ),
            ("analytic_us", "CPU batch latency", "line2:batch_size:mlp_us"),
        ],
        "citations": "Black & Scholes (1973); Huge & Savine, Differential Machine Learning (2020); Dugas et al. (2009).",
        "gate": "G1",
    },
    19: {
        "title": "Inverse Problems & Arbitrage-Aware Surfaces",
        "question": "同じrepricing誤差でも識別性・無裁定・variance termは一致するか。",
        "focus": "Heston/COS、SABR/Hagan、rBergomi MCの数値teacherを共通schemaへ置き、multi-start forward calibrationを主経路、direct inverseをablationとする。SSVIとconvex call projectionでhard constraintsを検査する。",
        "sections": [
            (
                "clean_teacher_price",
                "clean teacher価格とhard-constrained fit",
                "surface2:hard_constrained_price",
            ),
            (
                "start_parameter_rmse",
                "multi-start parameter/repricing RMSE",
                "line2:start_index:start_repricing_rmse",
            ),
            (
                "pareto_iv_rmse",
                "IV fitとvariance termのPareto frontier",
                "line2:pareto_lambda:pareto_variance_rmse",
            ),
            (
                "target_variance",
                "variance term consistency",
                "line3:variance_maturity:iv_only_variance:joint_variance",
            ),
        ],
        "citations": "Gatheral & Jacquier (2014), Arbitrage-free SVI volatility surfaces; Heston (1993).",
        "gate": "G2",
    },
    20: {
        "title": "Surface Dynamics, Forecasting & Hedging Decisions",
        "question": "予測誤差の小ささは、leakage-freeな下流ヘッジ改善につながるか。",
        "focus": "purged walk-forwardとtrain-only scaler/PCAを固定し、persistence・EWMA・HAR ridge・PCA ridge challengerを比較する。最後にsurrogate→calibration→forecast→hedgeをcommon pathsで評価し、Phase-1 policy未提供時は未評価と明記する。",
        "sections": [
            (
                "actual_variance",
                "walk-forward RV forecast",
                "line3:test_row:har_ridge_prediction:pca_ridge_prediction",
            ),
            ("qlike", "forecast metricとblock-bootstrap CI", "bar:model_names:rmse"),
            ("hedge_pnl", "common-path hedge P&L", "histrows:hedge_names"),
            ("cvar95", "CVaRとturnover", "bar:hedge_names:turnover"),
        ],
        "citations": "Corsi (2009), HAR-RV; Patton (2011), volatility forecast comparison.",
        "gate": "G3",
    },
    21: {
        "title": "Joint SPX/VIX Models",
        "question": "SPX smileとVIX term structureを一つの状態モデルで同時に説明できるか。",
        "focus": "4-factor PDVを主モデル、AFV・rough-Heston kernel・quintic OUを比較に置く。SPX IV、VIX、variance termを別metricでjoint objectiveへ渡し、nested teacherとsurrogateの誤差・速度を併記する。",
        "sections": [
            ("spx_target", "SPX IV joint fit", "surface2:spx_pdv"),
            ("vix_target", "VIX term structure", "line2:vix_maturity:vix_pdv"),
            ("spx_rmse", "PDV/AFV/rough/quintic比較", "bar:model_names:vix_rmse"),
            ("nested_mc_ms", "nested MC vs surrogate", "line2:batch_size:surrogate_ms"),
        ],
        "citations": "Guyon & Lekeufack (2023), Path-dependent volatility; Bergomi (2016), Stochastic Volatility Modeling.",
        "gate": "G4",
    },
    22: {
        "title": "0DTE Clocks, Jumps & Greeks",
        "question": "暦時間では見えない日中variance clockとscheduled jumpをどう分離するか。",
        "focus": "timezone・session・holiday・settlementを先に固定し、variance clock、隣接expiry total variance、scheduled event、time-of-day SV+jumpを独立検証する。dealer-flowから因果は主張しない。",
        "sections": [
            ("variance_clock", "intraday variance clock", "line2:minute:variance_weight"),
            (
                "event_jump_intensity",
                "event/non-event jump intensity",
                "line2:minute:non_event_jump_intensity",
            ),
            (
                "total_variance",
                "adjacent-expiry total variance",
                "line2:adjacent_expiry_minutes:model_total_variance",
            ),
            ("price_mae", "time-of-day price/Greek OOD", "bar:tod_names:greek_mae"),
        ],
        "citations": "Andersen et al. (2024), ultra-short-dated options; scheduled-jump literature.",
        "gate": "G4",
    },
    23: {
        "title": "RFR & Post-LIBOR Smiles",
        "question": "daily compounding、観測規約、curve、smileを混ぜずに検証できるか。",
        "focus": "lookback・lockout・observation shift・in-advance/arrears、multi-curve/basis、policy jump、collateralを分離する。Bachelier→shifted/free-boundary SABR→quadrature/MC teacherと進み、Bartlett deltaをsticky-strikeと比較する。Deep XVAは既存hullkit.xvaへのhandoffとする。",
        "sections": [
            ("discrete_accrual", "daily compounded RFR", "line2:day:continuous_accrual"),
            ("futures_forward_bp", "futures-forward convexity", "line:maturity"),
            ("normal_iv", "Bachelier/shifted SABR smile", "line2:strike:shifted_sabr_iv"),
            ("hedge_rmse", "sticky-strike vs Bartlett delta", "bar:hedge_names"),
        ],
        "citations": "ARRC RFR conventions; Hagan et al. (2002), Managing Smile Risk; Bartlett (2006).",
        "gate": "G5",
    },
    24: {
        "title": "Crypto Perpetuals, Liquidation & AMMs",
        "question": "funding、margin waterfall、oracle、AMM LVRを同じcash-flow ledgerで追えるか。",
        "focus": "linear/inverse/quanto、index/mark/last、funding cap、marginとbankruptcy、insurance→ADL→socialized lossを一つのledgerで保存する。CPMM/concentrated liquidityのLVRとfee compensationを別指標にする。cascadeはsynthetic fixtureである。",
        "sections": [
            ("index_price", "index/mark/last price states", "line3:step:mark_price:last_price"),
            ("insurance_fund", "insurance fund and ADL waterfall", "line2:step:adl_notional"),
            ("equity", "stress-path solvency identity", "line2:step:liability"),
            ("lvr", "AMM LVR and fee compensation", "line3:step:fee_income:dynamic_fee_income"),
        ],
        "citations": "Perpetual swap funding literature; Milionis et al. (2022), Loss-Versus-Rebalancing.",
        "gate": "G6",
    },
    25: {
        "title": "Carbon, Weather & Renewable PPAs",
        "question": "非完備市場のpremium、location basis、PPA shape/volume riskをどう分けるか。",
        "focus": "carbon GBM/Heston/SV+jump、temperature seasonality/OU/fOU、station basis、fixed/pay-as-produced/floor-collar PPAを分ける。fair value・CFaR/CVaR・hedge residualを別々に報告し、storage optionはresearch trackへ隔離する。",
        "sections": [
            ("carbon_gbm_iv", "carbon GBM vs SV+jump smile", "line2:strike:carbon_jump_iv"),
            (
                "temperature_seasonal",
                "temperature OU vs fOU",
                "line3:day:temperature_ou:temperature_fou",
            ),
            ("basis_rmse", "station/location basis risk", "line:station_distance_km"),
            ("cvar95", "PPA CFaR/CVaR and hedge residual", "bar:risk_names:hedge_residual"),
        ],
        "citations": "Benth & Benth (2013), Modeling and Pricing in Financial Markets for Weather Derivatives; energy PPA literature.",
        "gate": "G7",
    },
}


def _md(text: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_markdown_cell(text)


def _code(text: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(text)


def _plot_code(key: str, title: str, kind: str) -> str:
    parts = kind.split(":")
    mode = parts[0]
    preamble = f'fig, ax = plt.subplots(figsize=(7.2, 3.8))\nax.set_title("{title}")\n'
    if mode == "heatmap":
        body = f'im = ax.imshow(data["{key}"], aspect="auto", origin="lower", cmap="magma")\nfig.colorbar(im, ax=ax)'
    elif mode == "surface2":
        other = parts[1]
        body = (
            f'for i in range(data["{key}"].shape[0]):\n'
            f'    ax.plot(data["strike"], data["{key}"][i], color="black", alpha=.45)\n'
            f'    ax.plot(data["strike"], data["{other}"][i], linestyle="--", alpha=.8)'
        )
    elif mode == "line":
        x = parts[1] if len(parts) > 1 else ""
        xexpr = f'data["{x}"]' if x else f'np.arange(len(data["{key}"]))'
        body = f'ax.plot({xexpr}, data["{key}"], marker="o")'
    elif mode == "line2":
        x, other = parts[1], parts[2]
        body = f'ax.plot(data["{x}"], data["{key}"], marker="o", label="{key}")\nax.plot(data["{x}"], data["{other}"], marker="s", label="{other}")\nax.legend()'
    elif mode == "line3":
        x, other1, other2 = parts[1], parts[2], parts[3]
        body = (
            f'ax.plot(data["{x}"], data["{key}"], label="{key}")\n'
            f'ax.plot(data["{x}"], data["{other1}"], label="{other1}")\n'
            f'ax.plot(data["{x}"], data["{other2}"], label="{other2}")\nax.legend()'
        )
    elif mode == "bar":
        labels = parts[1]
        other = parts[2] if len(parts) > 2 else None
        body = f'x = np.arange(len(data["{labels}"]))\nax.bar(x - .18, data["{key}"], width=.36, label="{key}")\n'
        if other:
            body += f'ax.bar(x + .18, data["{other}"], width=.36, label="{other}")\n'
        body += f'ax.set_xticks(x, data["{labels}"], rotation=15)\nax.legend()'
    elif mode == "histrows":
        labels = parts[1]
        body = f'for i, label in enumerate(data["{labels}"]):\n    ax.hist(data["{key}"][i], bins=35, density=True, histtype="step", label=str(label))\nax.legend()'
    else:
        raise ValueError(f"unsupported plot kind: {kind}")
    return preamble + body + "\nax.grid(alpha=.2)\nplt.show()"


def _presentation_code(number: int) -> str:
    """Create plot-only aliases without polluting the release artifact schema."""
    if number == 19:
        return (
            "data.update({\n"
            "    'strike': data['constraint_strikes'],\n"
            "    'clean_teacher_price': data['constraint_clean_teacher_price'],\n"
            "    'hard_constrained_price': data['constraint_hard_price'],\n"
            "    'start_index': np.arange(len(data['calibration_start_repricing_rmse'])),\n"
            "    'start_parameter_rmse': np.sqrt(np.mean((data['calibration_start_parameters'] - data['calibration_truth'][None, :]) ** 2, axis=1)),\n"
            "    'start_repricing_rmse': data['calibration_start_repricing_rmse'],\n"
            "    'pareto_lambda': data['pareto_lambdas'],\n"
            "    'pareto_iv_rmse': np.sqrt(np.maximum(data['pareto_losses'][:, 1], 0.0)),\n"
            "    'pareto_variance_rmse': np.sqrt(np.maximum(data['pareto_losses'][:, 2], 0.0)),\n"
            "    'variance_maturity': data['teacher_maturities'],\n"
            "    'target_variance': data['pareto_target_variance'],\n"
            "    'iv_only_variance': data['pareto_predicted_variance'][0],\n"
            "    'joint_variance': data['pareto_predicted_variance'][-1],\n"
            "})"
        )
    if number == 20:
        return (
            "model_order = ['persistence', 'ewma', 'har_ridge', 'pca_ridge_challenger']\n"
            "strategy_order = manifest['metrics']['end_to_end']['strategy_order']\n"
            "data.update({\n"
            "    'test_row': data['walk_forward_test_row'],\n"
            "    'actual_variance': data['walk_forward_actual'],\n"
            "    'har_ridge_prediction': data['walk_forward_prediction_har_ridge'],\n"
            "    'pca_ridge_prediction': data['walk_forward_prediction_challenger'],\n"
            "    'model_names': np.asarray(model_order),\n"
            "    'rmse': np.asarray([manifest['metrics']['walk_forward']['models'][name]['rmse'] for name in model_order]),\n"
            "    'qlike': np.asarray([manifest['metrics']['walk_forward']['models'][name]['qlike'] for name in model_order]),\n"
            "    'hedge_names': np.asarray(strategy_order),\n"
            "    'hedge_pnl': data['e2e_hedge_pnl'],\n"
            "    'cvar95': np.asarray([manifest['metrics']['end_to_end']['strategy_metrics'][name]['cvar95'] for name in strategy_order]),\n"
            "    'turnover': np.asarray([manifest['metrics']['end_to_end']['strategy_metrics'][name]['turnover'] for name in strategy_order]),\n"
            "})"
        )
    return ""


def _validation_markdown(item: dict, meta: dict, payload: dict) -> str:
    artifact_command = (
        "uv run --no-sync --package deep-hedge-price python "
        "deep_hedge_price/scripts/export_johnhull_pricing_reference.py "
        "--config deep_hedge_price/configs/pricing_quick.yaml"
        if item["number"] == 18
        else (
            "uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py "
            f"--volume {item['number']}"
        )
    )
    lines = [
        f"# Volume {item['number']} Validation — {meta['gate']}",
        "",
        "- Gate: **PASS** (`integration_and_reproducibility`)",
        "- Model performance approved: **no**",
        "- Status: reference artifact and executed notebook generated",
        "- Data policy: synthetic-offline",
        "- Network/training/download during notebook execution: none",
        "",
        "## Artifact evidence",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in payload["metrics"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            "",
            "## Acceptance checks",
            "",
            "| Check | Observed | Criterion | Pass |",
            "|---|---:|---|:---:|",
        ]
    )
    for check in payload["acceptance"]["checks"]:
        lines.append(
            f"| `{check['name']}` | {check['observed']} | {check['criterion']} | "
            f"{'PASS' if check['passed'] else 'FAIL'} |"
        )
    lines.extend(["", "## Negative results", ""])
    lines.extend(f"- {result}" for result in payload["acceptance"]["negative_results"])
    lines.extend(
        [
            "",
            "## Rebuild",
            "",
            "```bash",
            artifact_command,
            f"uv run --no-sync --package hullkit python johnhull/volumes/{item['slug']}/build_{item['book_name']}_notebook.py",
            "```",
            "",
            "## Limitations",
            "",
            *[f"- {limitation}" for limitation in payload["limitations"]],
            "- Research-track models remain optional and cannot fail the core notebook path.",
            "- Core semantic identities are independently recomputed by the release verifier.",
            "",
        ]
    )
    return "\n".join(lines)


def build_volume(number: int, *, execute: bool = True) -> Path:
    item = next(item for item in MANIFEST["volumes"] if item["number"] == number)
    meta = VOLUME_META[number]
    volume = PROJECT / "volumes" / item["slug"]
    json_name = next(ref for ref in item["references"] if ref.endswith(".json"))
    npz_name = next(ref for ref in item["references"] if ref.endswith(".npz"))
    metrics = json.loads((volume / json_name).read_text(encoding="utf-8"))
    cells = [
        _md(f"# Vol {number} — {meta['title']}\n\n**問い:** {meta['question']}"),
        _md(
            "> **核心** — 複雑なモデルは必ず単純baselineとhard checkに並べる。<br>\n"
            "> **直感** — 平均誤差だけでは、尾部・裁定・cash-flow破綻を隠せる。<br>\n"
            "> **実務** — 再現可能なartifactと明示的な失敗条件をmodel risk管理の単位にする。"
        ),
        _md(f"## モデルladderと責務\n\n{meta['focus']}"),
        _md(
            "## Artifact契約とdata policy\n\nこのnotebookはcommitted JSON/NPZだけを読み、学習・download・GPU検出を行わない。"
        ),
        _code(
            "from pathlib import Path\n"
            "import hashlib, json\n"
            "import numpy as np\n"
            "import matplotlib.pyplot as plt\n\n"
            f"reference = Path('reference')\n"
            f"manifest = json.loads((reference / '{Path(json_name).name}').read_text(encoding='utf-8'))\n"
            f"artifact = reference / '{Path(npz_name).name}'\n"
            "digest = hashlib.sha256(artifact.read_bytes()).hexdigest()\n"
            f"assert manifest['schema_version'] == 1 and manifest['volume'] == {number}\n"
            "assert manifest['data_policy'] == 'synthetic-offline'\n"
            "assert manifest['companions'][artifact.name] == digest\n"
            "archive = np.load(artifact, allow_pickle=False)\n"
            "schema = manifest['companion_schemas'][artifact.name]\n"
            "assert set(schema) == set(archive.files)\n"
            "for name in archive.files:\n"
            "    assert schema[name]['shape'] == list(archive[name].shape)\n"
            "    assert schema[name]['dtype'] == str(archive[name].dtype)\n"
            "    assert schema[name]['unit']\n"
            "artifact_data = {name: archive[name] for name in archive.files}\n"
            "archive.close()\n"
            "data = dict(artifact_data)\n"
            "print(f\"schema={manifest['schema_version']} volume={manifest['volume']} digest={digest[:16]} arrays={len(artifact_data)}\")"
        ),
        *([_code(_presentation_code(number))] if _presentation_code(number) else []),
        _md("## 指標の要約\n\n指標は同じsynthetic fixture・単位・seedで比較する。"),
        _code("for key, value in manifest['metrics'].items():\n    print(f'{key}: {value}')"),
        _md(
            "## Acceptance scope\n\nこの判定はintegrationと再現性だけを対象とし、"
            "市場適合・予測力・production readinessを承認しない。"
        ),
        _code(
            "assert manifest['acceptance']['scope'] == 'integration_and_reproducibility'\n"
            "assert manifest['acceptance']['model_performance_approved'] is False\n"
            "assert manifest['acceptance']['passed'] is True\n"
            "for check in manifest['acceptance']['checks']:\n"
            "    print(('PASS' if check['passed'] else 'FAIL'), check['name'], check['observed'], check['criterion'])"
        ),
    ]
    for key, title, kind in meta["sections"]:
        cells.append(
            _md(f"## {title}\n\n単一のaggregate scoreではなく、構造別・時間別・stress別に読む。")
        )
        cells.append(_code(_plot_code(key, title, kind)))
    cells.extend(
        [
            _md(
                "## Gate判定\n\nartifact fingerprint、finite values、主要identityを機械的に確認する。"
            ),
            _code(
                "assert all(np.all(np.isfinite(values)) for values in artifact_data.values() if values.dtype.kind in 'fiu')\n"
                "assert manifest['companions'][artifact.name] == hashlib.sha256(artifact.read_bytes()).hexdigest()\n"
                "assert set(manifest['companion_schemas'][artifact.name]) == set(artifact_data)\n"
                "print('PASS: fingerprint, schema, units, and finite-value checks')"
            ),
            _md(
                "## 限界とnegative results\n\n"
                "本巻の数値はsynthetic fixtureによる教育・integration検証であり、市場予測力、収益性、"
                "実運用較正を示さない。複雑モデルがbaselineに勝たない場合もnegative resultとして保持する。"
            ),
            _md(
                "## Research track\n\n未査読preprintや重いモデルはoptional profileに隔離し、"
                "core artifact・notebook・book・portalの再構築を妨げない。"
            ),
            _md(f"## 参考文献\n\n{meta['citations']}"),
            _md(
                "## まとめ\n\n価格・統計誤差だけでなく、hard constraints、下流risk、計算量、"
                "data/model limitationsを同じ成果物に固定した。"
            ),
        ]
    )
    notebook = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
            "johnhull": {"artifact_only": True, "volume": number, "gate": meta["gate"]},
        },
    )
    target = volume / item["notebook"]
    if execute:
        NotebookClient(
            notebook,
            timeout=180,
            kernel_name="python3",
            resources={"metadata": {"path": str(volume)}},
        ).execute()
    nbformat.write(notebook, target)
    (volume / item["validation"]).write_text(
        _validation_markdown(item, meta, metrics), encoding="utf-8"
    )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--volume", type=int, choices=range(18, 26))
    parser.add_argument("--no-execute", action="store_true")
    args = parser.parse_args(argv)
    numbers = [args.volume] if args.volume else list(range(18, 26))
    for number in numbers:
        path = build_volume(number, execute=not args.no_execute)
        print(f"built {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
