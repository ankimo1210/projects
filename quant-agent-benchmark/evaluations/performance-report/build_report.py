#!/usr/bin/env python3
"""Build a bounded, source-backed report artifact from the verified final run.

This does not rerun or alter candidates, the evaluator, or session logs.
Run from any directory: python3 evaluations/performance-report/build_report.py
Then use the Data Analytics packaged deliver_portable_artifact.mjs builder.
"""
import csv
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
MATCHED = "analysis/final-review-20260905/matched"
MODELS = ["fable", "opus", "sol", "astra"]
NAMES = {m: m.title() for m in MODELS}
MODEL_IDS = {"astra": "gpt-6-astra", "sol": "gpt-5.6-sol",
             "opus": "claude-opus-5", "fable": "claude-fable-5-1"}
CATEGORIES = [
    ("numerical", "numerical_correctness", "数値精度", 30),
    ("model_quality", "quantitative_model_quality", "モデル品質", 20),
    ("robustness", "hidden_scenario_robustness", "頑健性", 15),
    ("software_engineering", "software_engineering_reproducibility", "ソフトウェア", 15),
    ("data_quality", "data_quality_handling", "データ品質", 10),
    ("report", "report_completeness", "レポート", 5),
    ("completion", "completion_integrity", "完遂", 5),
]
INPUTS = {}
CHECKS = []


def read_json(rel):
    data = (BASE / rel).read_bytes()
    INPUTS[rel] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def read_csv(rel):
    data = (BASE / rel).read_bytes()
    INPUTS[rel] = hashlib.sha256(data).hexdigest()
    return list(csv.DictReader(data.decode("utf-8-sig").splitlines()))


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    CHECKS.append(label)


def close(a, b, label, tol=1e-7):
    check(math.isclose(float(a), float(b), rel_tol=0, abs_tol=tol), label)


def fmt(n, digits=3):
    return f"{n:,.{digits}f}"


summary = read_json("evaluations/combined_summary.json")
check(len(summary) == 4 and {r["model"] for r in summary} == set(MODELS), "4 unique final models")
S = {r["model"]: r for r in summary}
E = {m: read_json(f"evaluations/{m}.json") for m in MODELS}
R = {r["model"]: r for r in read_csv(f"{MATCHED}/runtime_tokens.csv")}
# Work-turn volume with cache reads removed: uncached input + cache creation + output.
# Cache reads are 92-98% of every total and are the cheapest token class at both vendors,
# so the raw total exaggerates the Opus/Fable gap (5.5x) versus this measure (1.2x).
EXCACHE = {m: int(R[m]["uncached_input"]) + int(R[m]["cache_creation_input"]) + int(R[m]["output_total"]) for m in MODELS}
SCORING_SRC = (BASE / "evaluator/scoring.py").read_text(encoding="utf-8")
for weight, metric in [("7.0", "zero_rate_rmse_bps"), ("3.0", "weighted_zero_rate_rmse_bps"),
                       ("4.0", "forward_rate_rmse_bps"), ("4.0", "hidden_instrument_normalized_rmse")]:
    check(f'quantitative_score += {weight} * bounded_score(main_metrics["{metric}"]' in SCORING_SRC,
          f"model quality: {weight} points come from main-curve {metric}")
check('quantitative_score += 1.0 if model_cmp_ok else 0.0' in SCORING_SRC and
      'quantitative_score += 1.0 if sensitivity_ok and main_metrics["forward_roughness"] < 0.002 else 0.0' in SCORING_SRC,
      "model quality: only 2 of 20 points are model-comparison / sensitivity format checks")
check('state.check("data.missing_handling", dq["missing_handling_rate"] >= 0.9' in SCORING_SRC and
      'miss_ok = miss["action"].eq("exclude")' in SCORING_SRC,
      "data quality: missing_quote passes only with action == exclude")
T = read_csv(f"{MATCHED}/user_turns.csv")
AUDIT = read_json(f"{MATCHED}/evaluation_audit.json")
USAGE = read_json(f"{MATCHED}/usage_audit.json")
TESTS = read_json(f"{MATCHED}/pytest_verification.json")
METHOD = read_json("evaluations/methodology.json")
check(AUDIT["original_candidates_unchanged"] is True, "Candidate hashes unchanged during final evaluation")
for phase in ["manifest_before", "manifest_after"]:
    for target, expected in [("input", 12), ("evaluator", 108)]:
        obj = AUDIT[phase][target]
        check(obj["files_verified"] == expected and not obj["mismatches"], f"{phase}: {target} manifest matched")
check(len(T) == 14, "14 human user turns recovered")
check(len([t for t in T if t["selected_work_turn"] == "True"]) == 5, "5 selected work turns across 4 models")
for m in MODELS:
    s, e, r = S[m], E[m], R[m]
    close(s["score"], e["total_score"], f"{m}: summary score")
    close(sum(e["category_scores"].values()), e["total_score"], f"{m}: category sum", .002)
    for short, key, _, maximum in CATEGORIES:
        close(s[short], e["category_scores"][key], f"{m}: {key}")
        check(0 <= s[short] <= maximum, f"{m}: {key} range")
    parts = ["uncached_input", "cache_read_input", "cache_creation_input", "output_nonreasoning", "output_reasoning"]
    check(sum(int(r[k]) for k in parts) == s["total_tokens"], f"{m}: exclusive token parts sum")
    check(int(r["output_nonreasoning"]) + int(r["output_reasoning"]) == s["output_tokens"], f"{m}: reasoning is output subset")
    for field, target in [("total_tokens", "total_tokens"), ("session_total_tokens", "session_total_tokens"), ("work_minutes", "work_time_min")]:
        close(r[field], s[target], f"{m}: runtime summary {field}")
    work = [t for t in T if t["model"] == m and t["selected_work_turn"] == "True"]
    close(sum(float(t["minutes"]) for t in work), s["work_time_min"], f"{m}: work time equals turn sum")
    check(sum(int(t["total_tokens"]) for t in work) == s["total_tokens"], f"{m}: work tokens equal turn sum")
    check(sum(int(t["total_tokens"]) for t in T if t["model"] == m) == s["session_total_tokens"], f"{m}: all session turns reconcile")
    close(s["work_time_min"] + s["between_work_turn_idle_min"], s["work_span_min"], f"{m}: span reconciles")
    check(TESTS[m]["returncode"] == 0 and not TESTS[m]["timed_out"], f"{m}: full pytest success")
    check(f'{s["verified_tests_passed"]} passed' in TESTS[m]["stdout"], f"{m}: test count independently matches log")
    details = e["hidden_tests"]["details"]
    check(len(details) == 41, f"{m}: 41 rubric checks")
    check(sum(bool(v["passed"]) for v in details) == s["hidden_checks_passed"], f"{m}: hidden check count")
    scenarios = e["quantitative_diagnostics"]["hidden_scenarios"]
    check(len(scenarios) == 10 and all(v["valid"] for v in scenarios.values()), f"{m}: 10 valid scenarios")
    if m in ["astra", "sol"]:
        check(USAGE[m]["independent_cumulative_reconciliation"], f"{m}: usage reconciled to cumulative counter")
    else:
        check(USAGE[m]["all_repeated_usage_identical"], f"{m}: repeated usage identical before message dedup")
check(sum(S[m]["verified_tests_passed"] for m in MODELS) == 329, "329 total independent pytest passes")
check(all(S[m]["reported_usd_cost"] is None for m in MODELS), "Cost remains unknown, not zero")
# This is a final-run narrative, not a generic live dashboard: fail loudly if
# later source updates would make its fixed observations stale.
for m, score, tokens in [("astra", 80.103, 3797692), ("sol", 80.438, 8975027),
                         ("opus", 93.431, 59401805), ("fable", 94.473, 10790902)]:
    close(S[m]["score"], score, f"{m}: frozen report score")
    check(S[m]["total_tokens"] == tokens, f"{m}: frozen report token total")
    checks_by_id = {v["id"]: v["passed"] for v in E[m]["hidden_tests"]["details"]}
    check(checks_by_id["math.dv01_finite_difference"] and checks_by_id["math.key_rate_consistency"], f"{m}: risk checks pass")

# The installed portable validator requires SQL for numerical widgets, even
# though file-only provenance is documented. Use real, executed SQL reductions
# over the reviewed evidence, preserving the original files and recovery code.
# These queries calculate the report's scores, selected-turn totals, ratios,
# scenario matrix and test-count reconciliation; they are not dummy SQL.
DB = sqlite3.connect(":memory:")
DB.row_factory = sqlite3.Row
DB.execute("CREATE TABLE raw_evaluations (model TEXT PRIMARY KEY, document TEXT)")
DB.executemany("INSERT INTO raw_evaluations VALUES (?, ?)", [(m, json.dumps(E[m])) for m in MODELS])
DB.execute("CREATE TABLE raw_pytest (model TEXT PRIMARY KEY, document TEXT)")
DB.executemany("INSERT INTO raw_pytest VALUES (?, ?)", [(m, json.dumps(TESTS[m])) for m in MODELS])
turn_fields = list(T[0])
DB.execute("CREATE TABLE raw_user_turns (" + ",".join('"' + k + '" TEXT' for k in turn_fields) + ")")
DB.executemany("INSERT INTO raw_user_turns VALUES (" + ",".join("?" for _ in turn_fields) + ")", [[t[k] for k in turn_fields] for t in T])
QUERIES = {
"scores": """SELECT e.model, json_extract(e.document, '$.total_score') AS score,
       c.key AS category, CAST(c.value AS REAL) AS category_score,
       CASE c.key WHEN 'numerical_correctness' THEN 30
         WHEN 'quantitative_model_quality' THEN 20
         WHEN 'hidden_scenario_robustness' THEN 15
         WHEN 'software_engineering_reproducibility' THEN 15
         WHEN 'data_quality_handling' THEN 10 ELSE 5 END AS category_maximum,
       CAST(c.value AS REAL) / CASE c.key WHEN 'numerical_correctness' THEN 30
         WHEN 'quantitative_model_quality' THEN 20
         WHEN 'hidden_scenario_robustness' THEN 15
         WHEN 'software_engineering_reproducibility' THEN 15
         WHEN 'data_quality_handling' THEN 10 ELSE 5 END AS attainment
FROM main.raw_evaluations e, json_each(e.document, '$.category_scores') c
ORDER BY score DESC, category;""",
"precision": """WITH diagnostic_rows AS (
  SELECT model, 'main' AS scope, json_extract(document, '$.quantitative_diagnostics') AS metrics
  FROM main.raw_evaluations
  UNION ALL
  SELECT e.model, s.key, s.value
  FROM main.raw_evaluations e, json_each(e.document, '$.quantitative_diagnostics.hidden_scenarios') s
)
SELECT model, scope, metrics,
       json_extract(metrics, '$.zero_rate_rmse_bps') AS zero_rmse_bps,
       json_extract(metrics, '$.forward_rate_rmse_bps') AS forward_rmse_bps,
       100.0 * json_extract(metrics, '$.dv01_median_relative_error') AS dv01_relative_error_percent,
       RANK() OVER (PARTITION BY scope ORDER BY json_extract(metrics, '$.zero_rate_rmse_bps')) AS zero_error_rank
FROM diagnostic_rows ORDER BY scope, zero_error_rank;""",
"usage": """SELECT model,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(minutes AS REAL) ELSE 0 END) AS work_minutes,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(api_responses AS INTEGER) ELSE 0 END) AS work_api_responses,
 SUM(CAST(api_responses AS INTEGER)) AS session_api_responses,
 SUM(CAST(total_tokens AS INTEGER)) AS session_total_tokens,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(uncached_input AS INTEGER) ELSE 0 END) AS uncached_input,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(cache_read_input AS INTEGER) ELSE 0 END) AS cache_read_input,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(cache_creation_input AS INTEGER) ELSE 0 END) AS cache_creation_input,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(uncached_input AS INTEGER) + CAST(cache_read_input AS INTEGER) + CAST(cache_creation_input AS INTEGER) ELSE 0 END) AS input_total,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(output_nonreasoning AS INTEGER) ELSE 0 END) AS output_nonreasoning,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(output_reasoning AS INTEGER) ELSE 0 END) AS output_reasoning,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(output_nonreasoning AS INTEGER) + CAST(output_reasoning AS INTEGER) ELSE 0 END) AS output_total,
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(uncached_input AS INTEGER) + CAST(cache_read_input AS INTEGER) + CAST(cache_creation_input AS INTEGER) + CAST(output_nonreasoning AS INTEGER) + CAST(output_reasoning AS INTEGER) ELSE 0 END) AS total_tokens,
 1.0 * SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(output_total AS INTEGER) ELSE 0 END) /
 SUM(CASE WHEN selected_work_turn = 'True' THEN CAST(api_responses AS INTEGER) ELSE 0 END) AS output_per_api
FROM main.raw_user_turns GROUP BY model ORDER BY total_tokens;""",
"qa": """WITH pytest_counts AS (
 SELECT p.model, CAST(trim(substr(json_extract(p.document, '$.stdout'),
   instr(json_extract(p.document, '$.stdout'), ' passed') - 3, 3)) AS INTEGER) AS pytest_passed,
   json_extract(p.document, '$.returncode') AS pytest_exit_code
 FROM main.raw_pytest p
)
SELECT e.model, p.pytest_passed, p.pytest_exit_code,
 SUM(CASE WHEN json_extract(c.value, '$.passed') = 1 THEN 1 ELSE 0 END) AS hidden_passed,
 COUNT(*) AS hidden_checks,
 (SELECT COUNT(*) FROM json_each(e.document, '$.quantitative_diagnostics.hidden_scenarios') s WHERE json_extract(s.value, '$.valid') = 1) AS valid_scenarios
FROM main.raw_evaluations e JOIN pytest_counts p ON p.model = e.model,
 json_each(e.document, '$.hidden_tests.details') c
GROUP BY e.model ORDER BY e.model;"""
}
# The present test totals are 2–3 digits; validate the parser against the
# independently recorded count and reject unknown formats instead of guessing.
SQL_ROWS = {sid: [dict(row) for row in DB.execute(sql)] for sid, sql in QUERIES.items()}
for row in SQL_ROWS["scores"]:
    close(row["category_score"], E[row["model"]]["category_scores"][row["category"]], "SQL category score reconciles")
    close(row["attainment"], row["category_score"] / row["category_maximum"], "SQL attainment reconciles")
    S[row["model"]]["score"] = row["score"]
    for short, key, _, _ in CATEGORIES:
        if key == row["category"]:
            S[row["model"]][short] = row["category_score"]
for row in SQL_ROWS["usage"]:
    for key, value in row.items():
        if key not in ["model", "output_per_api"]:
            close(value, R[row["model"]][key], f'SQL {row["model"]} {key} reconciles')
            R[row["model"]][key] = value
    S[row["model"]]["total_tokens"] = row["total_tokens"]
    S[row["model"]]["work_time_min"] = row["work_minutes"]
for row in SQL_ROWS["qa"]:
    check(row["pytest_passed"] == S[row["model"]]["verified_tests_passed"], "SQL pytest count reconciles")
    check(row["hidden_passed"] == S[row["model"]]["hidden_checks_passed"], "SQL hidden checks reconcile")
    check(row["valid_scenarios"] == 10 and row["hidden_checks"] == 41, "SQL scenario/check population reconciles")
    S[row["model"]]["verified_tests_passed"] = row["pytest_passed"]
    S[row["model"]]["hidden_checks_passed"] = row["hidden_passed"]
(HERE / "report_queries.sql").write_text("\n\n".join(f"-- {sid}\n{sql}" for sid, sql in QUERIES.items()) + "\n", encoding="utf-8")

generated = datetime.now(timezone.utc).isoformat()
DATA = {}
BLOCKS = []
CHARTS = []
TABLES = []
CARDS = []
SOURCES = []


def source(sid, label, path, files, definitions, description):
    SOURCES.append({"id": sid, "label": label, "path": path, "query": {
        "engine": "local-file", "description": description,
        "executed_at": METHOD["generated_utc"], "tables_used": files,
        "filters": ["2026年9月5日に完了した4モデルの各1実行。最終提出物のみ。"],
        "metric_definitions": definitions}})
    if sid in QUERIES:
        SOURCES[-1]["query"].update({"engine": "SQLite (in-memory)", "language": "sql", "sql": QUERIES[sid],
            "executed_at": generated,
            "description": description + " レポートの数値は、記載の元ファイルを読み込んだSQLite一時テーブルで独立に集計・照合。元ログの回復は記載のPython処理による。",
            "tables_used": files + ["main.raw_evaluations", "main.raw_user_turns", "main.raw_pytest",
                                     "evaluations/performance-report/build_report.py", "evaluations/performance-report/report_queries.sql"]})


source("scores", "最終自動採点・カテゴリ別集計", "evaluations/combined_summary.json",
       ["evaluations/combined_summary.json"] + [f"evaluations/{m}.json" for m in MODELS] + ["evaluator/scoring.py"],
       ["総得点は7カテゴリの和、満点100。表示は小数第3位。配点・閾値は元のまま。",
        "数値30、モデル品質20、頑健性15、ソフトウェア15、データ品質10、レポート5、完遂5。",
        "カテゴリ達成率=カテゴリ得点/カテゴリ満点。グラフでは0〜1、表示は%。",
        "Fableとの差=Fableのカテゴリ得点−比較モデルの同カテゴリ得点。",
        "モデル品質20点=主カーブのゼロRMSE 7＋重み付きゼロRMSE 3＋フォワードRMSE 4＋非公開商品RMSE 4＋比較JSON 1＋感度JSON 1（scoring.py）。",
        "データ品質のmissing_handlingは欠損クォート4件をaction=excludeにした比率≥0.9で合格。中値復元（correct/downweight）は不合格扱い。"],
       "ユーザー提示スクリプトを基にした最終再採点。リスク表の任意列の衝突のみ互換処理し、手動加点はしていない。")
source("precision", "正解カーブ・非公開商品・隠しシナリオ診断", "evaluations/fable.json",
       [f"evaluations/{m}.json" for m in MODELS] + ["evaluator/scoring.py"],
       ["ゼロ金利RMSE=1e4×sqrt(mean((推定ゼロ金利−正解)^2))、単位bp。1bp=0.01%。",
        "重み付きゼロRMSEは重み1/sqrt(0.15+満期年)。フォワードは推定z(T)×Tの数値微分で比較。",
        "短期は満期2年以下、長期は15年以上。主診断は本データ、s01〜s10は別の隠しシナリオ。",
        "非公開商品RMSEは金利誤差をbp、債券価格誤差を0.1価格単位に換算してプール。単一のbpではない。",
        "DV01相対誤差は照合できた各モデルの対象商品集合の中央値。対象数は異なる。",
        "公開クォート再現=観測クォートの再現誤差をbid/ask幅で正規化したRMSE（bid_ask_normalized_pricing_rmse）。無次元。",
        "隠しシナリオのフォワードRMSEは各シナリオの正解フォワードとの比較、単位bp。"],
       "最終評価JSONから診断値を抽出。主診断と隠し10シナリオの平均を混同しない。")
source("usage", "監査済み作業時間・トークン・ターン集計", f"{MATCHED}/runtime_tokens.csv",
       [f"{MATCHED}/runtime_tokens.csv", f"{MATCHED}/user_turns.csv", f"{MATCHED}/usage_audit.json",
        "analysis/session-tokens-20260905/recover_tokens.py", "analysis/final-review-20260905/recheck_final.py"],
       ["作業時間=選択した本実行/再開ユーザーターンの開始〜終了の和（分）。ツール・自動要約待ちを含む。",
        "Astra T4、Sol T2、Opus T1+T2、Fable T1。準備・確認・出力先対応・終了後依頼・ターン間待機は除外。",
        "経過時間=最初の作業開始〜最後の作業終了。Opusのみ再開待ち78.332933分を含む。",
        "総トークン=未キャッシュ入力+キャッシュ読み込み+キャッシュ作成+通常出力+推論出力。",
        "推論は出力の内数。セッション総量は本実行以外のユーザーターンも含む。",
        "キャッシュ読取を除く=未キャッシュ入力+キャッシュ作成+出力総量。両事業者でキャッシュ読取は最も安価なトークン区分であり、料金の代理ではないが総量より歪みが小さい。",
        "Codexはresponse_idで重複排除したusageを累積カウンタと照合。Claudeはmessage.idで一意化しrequestIdも照合。",
        "出力/API=本実行出力総量/一意な本実行API応答数。キャッシュ読取比率=キャッシュ読取/入力総量。異種トークナイザの単純比較には限界。"],
       "集計済みログを利用。過去の未完了Opus集計を使わず再開分を含める。思考本文・会話本文は収録しない。")
source("qa", "再評価の環境・テスト・入力保全監査", f"{MATCHED}/evaluation_audit.json",
       [f"{MATCHED}/evaluation_audit.json", f"{MATCHED}/pytest_verification.json", "evaluations/methodology.json", "evaluations/README.md",
        "evaluations/combined_summary.json"] + [f"evaluations/{m}.json" for m in MODELS],
       ["pytestは各候補の全テストを隔離コピーで実行。候補が書いたテストであり、モデル間で同一テスト集ではない。",
        "採点チェック41件と隠しシナリオ10件、pytest件数は別の母集団。",
        "マニフェストは公開入力12、評価側108ファイル。検証対象候補ハッシュは採点前後で一致。"],
       "記録された数値ライブラリに合わせた隔離環境で再確認。旧環境との得点一致も既存監査で確認。")
source("limits", "採点器の限界・仕様の確認記録", "evaluations/README.md",
       ["evaluations/README.md", "evaluations/methodology.json", "evaluator/scoring.py",
        "input/market_data/CONVENTIONS.md", "tools/generate_benchmark.py"],
       ["警告ヒットと実際の禁止行為を区別する。生得点を保持し、仮想的な補正スコアは計算しない。"],
       "日本語章見出し・自己パスの静的スキャン・JSON形式依存・端数期間の支払規則の比較。")
source("profiles", "候補の実装と自己申告", "results/fable/benchmark_summary.json",
       [f'{S[m]["candidate_path"]}/benchmark_summary.json' for m in MODELS] +
       [f'{S[m]["candidate_path"]}/README.md' for m in MODELS] +
       [S[m]["candidate_path"] for m in MODELS],
       ["修正反復回数は候補の自己申告で、共通のログ分類で検証した回数ではない。",
        "実装上の設計と観測誤差は区別する。アブレーション未実施のため原因ごとの寄与は未推定。"],
       "前段のコードレビューで確認した手法の要約。得点差の因果的な説明は仮説として扱う。")


def md(ident, body, sid=None):
    b = {"id": ident, "type": "markdown", "body": body.strip(), "layout": "full"}
    if sid:
        b["sourceId"] = sid
    BLOCKS.append(b)


def chart(ident, title, subtitle, dataset, sid, x, y, kind="bar", color=None, unit=None, fmtval="number", horizontal=False,
          show_description=False):
    enc = {"x": {"field": x, "type": "nominal", "label": {"model": "モデル", "category": "カテゴリ", "scenario": "シナリオ"}.get(x, x)},
           "y": {("fields" if isinstance(y, list) else "field"): y, "type": "quantitative", "label": unit or title}}
    if color:
        enc["color"] = {"field": color, "type": "nominal"}
    c = {"id": ident, "title": title, "subtitle": subtitle, "type": kind,
         "dataset": dataset, "sourceId": sid, "encodings": enc, "layout": "full",
         "valueFormat": fmtval, "labels": {"values": "all"},
         "palette": {"kind": "sequential" if kind == "heatmap" else "identity", "name": "blue"},
         "settings": {"sort": "none", "showValues": True},
         "surface": {"surface": "card", "showControls": False, "interactiveLegend": False}}
    if unit:
        c["unit"] = unit
    if show_description:
        # Heatmap subtitles carry the reading direction (dark = good vs dark = bad); keep them visible.
        c["showDescription"] = True
    if horizontal:
        c["settings"]["orientation"] = "horizontal"
    if kind in ["stackedBar", "horizontalStackedBar"]:
        c["settings"]["groupMode"] = "stacked"
        c["legend"] = {"position": "bottom", "sort": "spec"}
    CHARTS.append(c)
    BLOCKS.append({"id": ident + "-block", "type": "chart", "chartId": ident, "layout": "full"})


def table(ident, title, subtitle, rows, sid, columns, sort, density="spacious"):
    if sid in ["limits", "profiles"]:
        # These are qualitative file-backed review notes, not SQL measures.
        # Keep them in sourced narrative blocks instead of misrepresenting them
        # as query output merely to satisfy the native table SQL requirement.
        text = f"### {title}\n\n{subtitle}\n\n"
        for row in rows:
            text += "- " + " · ".join(f"{label}：{row[field]}" for field, label, _ in columns) + "\n"
        md(ident + "-notes", text, sid)
        return
    DATA[ident] = rows
    # Audit-style lookup tables with 7+ columns overflow the 768px reader column at spacious density.
    TABLES.append({"id": ident, "title": title, "subtitle": subtitle, "dataset": ident,
                   "sourceId": sid, "layout": "full", "density": density,
                   "defaultSort": {"field": sort[0], "direction": sort[1]},
                   "columns": [{"field": f, "label": lab, "type": "text" if typ == "text" else "number"}
                               for f, lab, typ in columns]})
    BLOCKS.append({"id": ident + "-block", "type": "table", "tableId": ident, "layout": "full"})


TITLE = "コーディングエージェント性能評価"
md("title", f"# {TITLE}\n\n量的リサーチ・ベンチマーク最終レポート · 2026年9月5日 · 時刻は日本標準時（JST）\n\n対象：Astra / Sol / Opus / Fable。完了済み提出物の自動採点、ログから回復した使用量、独立したテスト再実行を統合。")
md("executive-summary", """
## Executive Summary

- **今回の総合得点はFableが最高。** 94.473/100点で、Opusの93.431点を1.042点上回った。全4モデルが10/10の隠しシナリオで有効なカーブを生成し、独立したpytest再実行は合計329件すべて合格した。
- **精度・時間・トークンで、優位なモデルは異なる。** Solは34.6分で最短、Astraは3.80Mトークンで最少。Fableは55.9分・10.79M、Opusは再開を含め124.2分・59.40Mだった。ただし総量の92〜98%はキャッシュ読取で、それを除くとAstra 0.22M、Sol 0.23M、Fable 1.05M、Opus 1.29M。OpusとFableの差は5.5倍ではなく1.2倍で、トークン量は料金でもない。
- **GPT側の点差は、未完遂ではなく主カーブとストレス条件の精度にある。** Fableとの差は、数値精度・モデル品質・頑健性の計65点部分でAstraが10.687点、Solが15.035点。ただし「モデル品質」20点のうち18点は数値精度と同じ主カーブの誤差を再採点したもので、独立した証拠ではない。Astraには日本語レポートの機械判定による不利もある。
- **これは1回ずつの観測結果であり、普遍的な能力順位ではない。** 採点形式や支払日仕様に加え、欠損クォートの採点規則は4モデル全員が同じ理由で失点している。精度重視ではストレス条件に強いFableと主データで最も正確なOpusの両方を再検証候補とし、速度重視のSol・処理量重視のAstraも用途別に残すのが妥当。
""")

# A concise metric strip follows (never precedes) the executive summary.
DATA["headlines"] = [{"best_score": S["fable"]["score"], "score_lead": S["fable"]["score"] - S["opus"]["score"],
                      "fastest_min": S["sol"]["work_time_min"], "fewest_tokens": S["astra"]["total_tokens"]}]
for cid, label, field, sid, description in [
    ("score-kpi", "Fable · 最高得点 /100", "best_score", "scores", "今回の単一実行における自動採点。"),
    ("time-kpi", "Sol · 最短作業時間（分）", "fastest_min", "usage", "選択した本実行ターンの壁時計時間。"),
    ("tokens-kpi", "Astra · 最少処理トークン", "fewest_tokens", "usage", "キャッシュ入力を含む処理総量。料金換算なし。")]:
    metrics = [{"label": label, "field": field, "format": "number"}]  # exact tokens, same as the tables
    if field == "best_score":
        metrics.append({"label": "Opusとの差（点）", "field": "score_lead", "format": "number", "signed": True})
    CARDS.append({"id": cid, "dataset": "headlines", "sourceId": sid, "description": description, "metrics": metrics})
BLOCKS.append({"id": "headline-strip", "type": "metric-strip", "cardIds": [c["id"] for c in CARDS]})

md("overall", """
## 1. Fableが総合首位、Opusが僅差で続く

生の自動採点ではFable、Opus、Sol、Astraの順だった。FableとOpusの差は1.042点、SolとAstraの差は0.335点と小さい。後述の形式依存の減点があるため、この微差から安定した順位までは判断できない。

採点は100点満点の7カテゴリ。時間・トークンは得点に混ぜず別軸で示す。リスク表の任意列の衝突を避ける互換処理だけを適用し、計算式・配点・閾値は変更していない。誤検知を手作業で加点補正した値ではない。
""", "scores")
DATA["ranking"] = [{"model": NAMES[m], "score": S[m]["score"], "rank": S[m]["rank"],
                    "core_score": sum(S[m][c[0]] for c in CATEGORIES[:3]), "max_score": 100,
                    "candidate": S[m]["candidate_path"]} for m in MODELS]
chart("score-ranking", "モデル別総合得点", "100点満点・各1実行。点数は高いほど良い。", "ranking", "scores", "model", "score", unit="点", horizontal=True)
# Lookup tables put metrics in rows and models in columns: the shared reader clips anything wider than 768px.
table("category-scores", "カテゴリ別得点", "小数第3位までの正確な値。行=カテゴリ（満点付き）、列=モデル。",
      [{"metric": f"{i + 1}. {label} /{maximum}", **{NAMES[m]: fmt(S[m][short]) for m in MODELS}}
       for i, (short, _, label, maximum) in enumerate(CATEGORIES)] + [{"metric": f"{len(CATEGORIES) + 1}. 総合 /100", **{NAMES[m]: fmt(S[m]["score"]) for m in MODELS}}],
      "scores", [("metric", "カテゴリ", "text")] + [(NAMES[m], NAMES[m], "text") for m in MODELS], ("metric", "asc"))
DATA["category-attainment"] = [{"category": f"{label} /{maximum}", "maximum": maximum,
                                **{NAMES[m]: S[m][short] / maximum for m in MODELS}}
                               for short, _, label, maximum in CATEGORIES]
chart("category-matrix", "カテゴリ別の満点に対する達成率", "各セル=得点÷カテゴリ満点。濃いほど達成率が高い。総合点への寄与は配点で異なる。",
      "category-attainment", "scores", "category", [NAMES[m] for m in MODELS], kind="heatmap", fmtval="percent",
      show_description=True)

gap_rows = []
for short, _, label, maximum in CATEGORIES:
    gap_rows.append({"category": label, "max": maximum,
                     "vs_astra": fmt(S["fable"][short] - S["astra"][short]),
                     "vs_sol": fmt(S["fable"][short] - S["sol"][short])})
md("gap", """
## 2. GPT側の差は、完遂よりも数値・モデル品質に集中

全モデルの完遂点は5/5。FableとAstraの総得点差14.370点のうち、数値精度・モデル品質・頑健性で10.687点を占める。残りにはレポート点差3.111点とデータ品質差0.572点がある。

FableとSolは、同じ中核3カテゴリで15.035点の差がある一方、ソフトウェアではSolが1点上回るため、総差は14.035点になる。したがって、追加テストの件数だけを増やすより、価格付け規約・カーブ表現・ホールドアウト設計の再検証が優先される。

ただし「数値精度」と「モデル品質」は独立した2つの証拠ではない。採点器のモデル品質20点は、主データのゼロRMSE 7点・重み付きゼロRMSE 3点・フォワードRMSE 4点・非公開商品RMSE 4点の計18点と、モデル比較JSON・感度分析JSONの形式チェック各1点で構成される。つまり中核3カテゴリの実態は「主カーブ精度（数値精度30＋モデル品質18）」と「隠しシナリオ精度（頑健性15）」の2本で、Solのモデル品質10.218/20を「モデル選択の進め方が劣る」と読むことはできない。
""", "scores")
table("score-gaps", "Fableとのカテゴリ別得点差", "正の値はFableが上回る点数、負の値は比較相手が上回る点数。",
      gap_rows, "scores", [("category", "カテゴリ", "text"), ("max", "満点", "number"),
      ("vs_astra", "Fable − Astra（点）", "text"), ("vs_sol", "Fable − Sol（点）", "text")], ("max", "desc"))

D = {row["model"]: json.loads(row["metrics"]) for row in SQL_ROWS["precision"] if row["scope"] == "main"}
md("precision", """
## 3. Solは短期、Astraは長期の誤差が目立つ

本データの正解カーブとの比較では、OpusとFableのゼロ金利RMSEは約1.1bp、AstraとSolは約5〜6bpだった。フォワード金利でも前者が約13〜15bp、後者が約31〜33bpとなっている。これは提出完了の判定ではなく、数値再現の差を示す。

年限別にみるとSolは2年以下が20.223bp、Astraは15年以上が6.202bp。誤差の位置が違うため、「GPTモデルに一律の弱点がある」とまとめるより、モデル別の設計判断を調べる方が有用である。
""", "precision")
DATA["zero-errors"] = [{"model": NAMES[m], "zero_rmse": D[m]["zero_rate_rmse_bps"],
                        "forward_rmse": D[m]["forward_rate_rmse_bps"],
                        "short_rmse": D[m]["short_end_zero_rmse_bps"], "long_rmse": D[m]["long_end_zero_rmse_bps"]}
                       for m in sorted(MODELS, key=lambda m: D[m]["zero_rate_rmse_bps"])]
chart("zero-error-chart", "本データのゼロ金利RMSE", "単位bp。小さいほど良い。1bpは0.01パーセントポイント。", "zero-errors", "precision", "model", "zero_rmse", unit="bp", horizontal=True)
ACCURACY_ROWS = [("zero_rate_rmse_bps", "ゼロ金利RMSE（bp）"), ("weighted_zero_rate_rmse_bps", "重み付きゼロRMSE（bp）"),
                 ("forward_rate_rmse_bps", "フォワードRMSE（bp）"), ("short_end_zero_rmse_bps", "短期 ≤2Y ゼロRMSE（bp）"),
                 ("long_end_zero_rmse_bps", "長期 ≥15Y ゼロRMSE（bp）"), ("hidden_instrument_normalized_rmse", "非公開商品RMSE（正規化）")]
table("accuracy-detail", "本データの精度診断", "RMSEは小さいほど良い。行=指標、列=モデル。非公開商品は混合正規化単位であり、単純なbpではない。",
      [{"metric": f"{i + 1}. {label}", **{NAMES[m]: fmt(D[m][key]) for m in MODELS}} for i, (key, label) in enumerate(ACCURACY_ROWS)],
      "precision", [("metric", "指標", "text")] + [(NAMES[m], NAMES[m], "text") for m in MODELS], ("metric", "asc"))
md("risk-readout", """
### リスク計算は全モデルでチェックを通過

公開クォートそのものの再現では、bid/ask幅で正規化した誤差がOpus 5.4・Fable 5.1に対しAstra 17.7・Sol 63.6で、Solは入力クォートの再現から既に外れている。DV01有限差分とキーレート合計の整合性チェックは全モデルが合格した。ただし、照合できた商品数がモデル間で異なるため、下記の相対誤差だけでリスク計算の優劣を順位付けしない。非公開商品の価格誤差チェック（正規化RMSE < 3）はAstra・Solが不合格、Opus・Fableが合格だった。
""", "precision")
table("risk-detail", "公開クォートの再現とDV01の照合", "公開クォート再現=観測クォートの再現誤差÷bid/ask幅のRMSE（無次元、小さいほど良い）。DV01は相対誤差の中央値で、対象商品集合が異なる点に注意。",
      [{"model": NAMES[m], "n": D[m]["risk_instruments_checked"],
        "bidask": fmt(D[m]["bid_ask_normalized_pricing_rmse"]),
        "dv01": f'{D[m]["dv01_median_relative_error"] * 100:.4f}%',
        "key": f'{D[m]["key_rate_sum_median_relative_error"]:.3e}'} for m in MODELS], "precision",
      [("model", "モデル", "text"), ("bidask", "公開クォート再現（bid/ask幅比）", "text"), ("n", "照合商品数", "number"), ("dv01", "DV01相対誤差", "text"),
       ("key", "キーレート合計相対誤差", "text")], ("model", "asc"))

md("scenarios", """
## 4. 隠しシナリオでも精度差は残る

全モデルが10/10で有効なカーブを返したが、これは全ケースで精度が十分だったという意味ではない。Fableのゼロ金利RMSEは9/10シナリオで最小、残るs10ではOpusが最小だった。これら10条件は同一実装に対するストレス検証であり、独立した10回のモデル実行ではない。

また、ゼロ金利だけでは見えない弱点がある。Opusはs09のフォワードRMSEが70.314bpまで増え、同条件のFableは18.952bpだった。本データでのOpusの高精度を、すべてのストレス条件へ一般化しないことが重要である。
""", "precision")
# Models as rows, scenarios as columns: the shared card renderer fixes the heatmap
# height, and a 10-row matrix overflowed into an internal scroll that hid s01.
SCENARIOS = sorted(D["fable"]["hidden_scenarios"])
DATA["scenario-zero"] = [{"model": NAMES[m], "valid_scenarios": 10,
                          **{s: D[m]["hidden_scenarios"][s]["zero_rate_rmse_bps"] for s in SCENARIOS}} for m in MODELS]
chart("scenario-matrix", "隠し10シナリオのゼロ金利RMSE", "単位bp。行=モデル、列=隠しシナリオs01〜s10。濃いほど誤差が大きい（前の達成率図とは良否の向きが逆）。",
      "scenario-zero", "precision", "model", SCENARIOS, kind="heatmap", unit="bp", show_description=True)
DATA["scenario-forward"] = [{"scenario": sid, **{NAMES[m]: fmt(D[m]["hidden_scenarios"][sid]["forward_rate_rmse_bps"]) for m in MODELS},
                             "lowest": NAMES[min(MODELS, key=lambda m: D[m]["hidden_scenarios"][sid]["forward_rate_rmse_bps"])]} for sid in SCENARIOS]
table("scenario-forward", "隠し10シナリオのフォワード金利RMSE", "単位bp、小さいほど良い。ゼロ金利図では見えないOpusのs09（70.314bp）を含む。最小列=そのシナリオで誤差が最小のモデル。",
      DATA["scenario-forward"], "precision",
      [("scenario", "シナリオ", "text")] + [(NAMES[m], NAMES[m], "text") for m in MODELS] + [("lowest", "最小", "text")], ("scenario", "asc"))
opus_worst = max(SCENARIOS, key=lambda sid: D["opus"]["hidden_scenarios"][sid]["forward_rate_rmse_bps"])
check(opus_worst == "s09" and
      abs(D["opus"]["hidden_scenarios"]["s09"]["forward_rate_rmse_bps"] - 70.314) < 5e-4 and
      abs(D["fable"]["hidden_scenarios"]["s09"]["forward_rate_rmse_bps"] - 18.952) < 5e-4, "Opus s09 forward RMSE is its worst scenario")
wins = {m: 0 for m in MODELS}
for s in D["fable"]["hidden_scenarios"]:
    wins[min(MODELS, key=lambda m: D[m]["hidden_scenarios"][s]["zero_rate_rmse_bps"])] += 1
check(wins == {"fable": 9, "opus": 1, "sol": 0, "astra": 0}, "Per-scenario minimum count verifies 9 Fable / 1 Opus")

md("time", """
## 5. 最短はSol。Opusの再開待ちは作業時間と分ける

作業ターンの合計はSol 34.6分、Astra 52.0分、Fable 55.9分、Opus 124.2分。FableはOpusより作業時間が55.0%短く、今回の観測では総合点も高かった。ただし、計算機の競合・ツール待ち・自動要約を含むため、モデルの純粋な推論速度ではない。

Opusは途中で止まった後に再開している。69.8818分＋54.3365分が作業合計で、再開待ち78.3329分を含む最初から最後までは202.5513分。以前の69.9分という値は途中時点であり、本レポートでは最終値に置き換えている。
""", "usage")
DATA["work-time"] = [{"model": NAMES[m], "minutes": S[m]["work_time_min"], "span_minutes": S[m]["work_span_min"],
                      "idle_minutes": S[m]["between_work_turn_idle_min"], "work_turns": R[m]["work_turns"]}
                     for m in sorted(MODELS, key=lambda m: S[m]["work_time_min"])]
chart("execution-time", "本実行・再開の作業時間", "単位分。準備・後続依頼・ターン間の待機を除外。ツールと要約待ちは含む。", "work-time", "usage", "model", "minutes", unit="分", horizontal=True)
table("time-detail", "ログ計測と自己申告の時間", "比較の基準はログ作業時間。自己申告の時間は境界が異なるため別列。",
      [{"model": NAMES[m], "work": fmt(S[m]["work_time_min"], 2), "idle": fmt(S[m]["between_work_turn_idle_min"], 2),
        "span": fmt(S[m]["work_span_min"], 2), "reported": fmt(S[m]["wall_time_sec"] / 60, 2)} for m in MODELS], "usage",
      [("model", "モデル", "text"), ("work", "作業合計（分）", "text"), ("idle", "再開待ち（分）", "text"),
       ("span", "開始→終了（分）", "text"), ("reported", "自己申告（分）", "text")], ("model", "asc"))
table("selected-turns", "本実行に含めたターン", "2026年9月5日・JST、秒まで表示（ログはミリ秒まで保持）。API=そのターンの一意なAPI応答数。",
      [{"start_sort": t["start_jst"], "model": f'{NAMES[t["model"]]} T{int(t["turn_number"])}',
        "start": t["start_jst"][11:19], "end": t["end_jst"][11:19], "minutes": fmt(float(t["minutes"]), 2),
        "api": int(t["api_responses"]), "tokens": f'{int(t["total_tokens"]):,}'} for t in T if t["selected_work_turn"] == "True"],
      "usage", [("model", "モデル・ターン", "text"), ("start", "開始", "text"), ("end", "終了", "text"),
      ("minutes", "分", "text"), ("api", "API", "number"), ("tokens", "トークン", "text")], ("start", "asc"))

md("tokens", """
## 6. 総トークンの大半はキャッシュ入力

本実行の総量はAstra 3.80M、Sol 8.98M、Fable 10.79M、Opus 59.40M。OpusはFableの約5.50倍を処理した。しかし総量の92〜98%はキャッシュ読取で、これを除いた「通常入力＋キャッシュ作成＋出力」はAstra 215,612、Sol 229,299、Fable 1,051,441、Opus 1,285,431。この尺度ではOpusとFableの差は1.22倍に縮まり、Claude系2モデルがGPT系2モデルの約5倍という構図になる。どちらの値も「生成した文章量」「消費料金」や「推論の深さ」とは読み替えられない。

集計では、通常入力・キャッシュ読み込み・キャッシュ作成・通常出力・推論出力を排他的に足している。推論出力を出力総量へもう一度加えることはしない。API事業者間でトークナイザやキャッシュ計測が異なり、課金額・エネルギー・割当消費率は未測定である。
""", "usage")
DATA["token-composition"] = [{"model": NAMES[m], "part": label, "tokens": int(R[m][field]),
                              "work_total": S[m]["total_tokens"], "session_total": S[m]["session_total_tokens"]}
                             for m in sorted(MODELS, key=lambda m: S[m]["total_tokens"])
                             for label, field in [("入力（キャッシュ含む）", "input_total"), ("出力（推論含む）", "output_total")]]
chart("token-volume", "本実行の入力・出力トークン", "M=100万トークン。入力内のキャッシュ詳細は下表。総量の比較は料金の比較ではない。",
      "token-composition", "usage", "model", "tokens", kind="horizontalStackedBar", color="part", unit="tokens", fmtval="compact")
table("input-token-detail", "入力・出力の排他的な内訳", "通常入力・キャッシュ読取・キャッシュ作成・出力総量の和が本実行総量。キャッシュ読取を除く総量=通常入力＋キャッシュ作成＋出力総量。料金換算はしていない。",
      [{"metric": f"{i + 1}. {label}", **{NAMES[m]: f'{int(value(m)):,}' for m in MODELS}} for i, (label, value) in enumerate([
          ("通常入力", lambda m: R[m]["uncached_input"]), ("キャッシュ読取", lambda m: R[m]["cache_read_input"]),
          ("キャッシュ作成", lambda m: R[m]["cache_creation_input"]), ("出力総量（推論含む）", lambda m: R[m]["output_total"]),
          ("本実行総量", lambda m: S[m]["total_tokens"]), ("キャッシュ読取を除く総量", lambda m: EXCACHE[m])])], "usage",
      [("metric", "指標", "text")] + [(NAMES[m], NAMES[m], "text") for m in MODELS], ("metric", "asc"))
for m in MODELS:
    close(EXCACHE[m] + int(R[m]["cache_read_input"]), S[m]["total_tokens"], f"{m}: cache-excluded volume + cache reads = total", tol=0.5)
check(abs(EXCACHE["opus"] / EXCACHE["fable"] - 1.22) < 5e-3 and abs(S["opus"]["total_tokens"] / S["fable"]["total_tokens"] - 5.50) < 5e-3,
      "Opus/Fable ratio: 5.50x total vs 1.22x cache-excluded")
DATA["output-composition"] = [{"model": NAMES[m], "part": label, "tokens": int(R[m][field]),
                               "output_total": int(R[m]["output_total"]), "api_responses": int(R[m]["work_api_responses"])}
                              for m in sorted(MODELS, key=lambda m: S[m]["output_tokens"])
                              for label, field in [("通常出力", "output_nonreasoning"), ("推論出力", "output_reasoning")]]
md("output", """
### 出力だけを分けると、作業の進め方の違いが見える

Opusは275回のAPI応答と415.6k出力トークン、Fableは41回と277.3k。Astraは40回と83.2k、Solは72回と74.0kだった。Fableは比較的少ない応答回数で多くの出力を返し、Opusは多くの応答を重ねた。ただし、これは記録された応答の粒度であり、ツール呼出し数や内部の思考ステップ数ではない。

以下の推論量はログに明示された数値だけを使う。推論本文は収録しない。出力/APIもシステム間の応答境界に依存する観測指標で、単独の品質指標ではない。
""", "usage")
chart("output-volume", "通常出力と推論出力", "k=千トークン。2区分の和が出力総量。推論は出力に含まれる。", "output-composition", "usage", "model", "tokens",
      kind="horizontalStackedBar", color="part", unit="tokens", fmtval="compact")
table("work-patterns", "本実行の応答粒度と出力構成", "推論比率=推論出力÷出力総量。出力/API=出力総量÷API応答数。入力キャッシュ読取比率=キャッシュ読取÷入力総量。",
      [{"metric": f"{i + 1}. {label}", **{NAMES[m]: value(m) for m in MODELS}} for i, (label, value) in enumerate([
          ("API応答数", lambda m: f'{int(R[m]["work_api_responses"]):,}'),
          ("通常出力", lambda m: f'{int(R[m]["output_nonreasoning"]):,}'),
          ("推論出力", lambda m: f'{int(R[m]["output_reasoning"]):,}'),
          ("推論比率", lambda m: f'{int(R[m]["output_reasoning"]) / int(R[m]["output_total"]) * 100:.1f}%'),
          ("出力/API", lambda m: f'{int(R[m]["output_total"]) / int(R[m]["work_api_responses"]):,.0f}'),
          ("入力キャッシュ読取比率", lambda m: f'{int(R[m]["cache_read_input"]) / int(R[m]["input_total"]) * 100:.1f}%')])], "usage",
      [("metric", "指標", "text")] + [(NAMES[m], NAMES[m], "text") for m in MODELS], ("metric", "asc"))
table("sessions", "セッション名と集計範囲", "本実行以外の準備・確認・後続依頼を含むと、AstraとSolの総量が増える。",
      [{"model": NAMES[m], "session": R[m]["session_name"], "turns": len([t for t in T if t["model"] == m]),
        "selected": R[m]["work_turns"], "total": f'{S[m]["session_total_tokens"]:,}',
        "excluded": f'{S[m]["session_total_tokens"] - S[m]["total_tokens"]:,}'} for m in MODELS], "usage",
      [("model", "モデル", "text"), ("session", "セッション名", "text"), ("turns", "全ターン数", "number"),
       ("selected", "本実行ターン", "text"), ("total", "全セッショントークン", "text"),
       ("excluded", "本実行以外", "text")], ("model", "asc"))
SOL_TURN_END = datetime.fromisoformat("2026-09-05T10:56:32.554+09:00")
sol_files = [f for f in (BASE / "output/sol").rglob("*") if f.is_file()
             and not any(part in {"__pycache__", ".pytest_cache", ".venv", ".git"} for part in f.parts)]
sol_after = sorted(f.relative_to(BASE).as_posix() for f in sol_files
                   if datetime.fromtimestamp(f.stat().st_mtime, tz=timezone(timedelta(hours=9))) > SOL_TURN_END)
check(sol_after == ["output/sol/benchmark_summary.json"],
      "Sol: only the self-report summary changed after the counted work turn; scored code and outputs did not")
md("scope-note", "Astraでは準備・モデル名確認・終了後表示、Solではそれらに加えて出力先確認と修正依頼のターンを本実行から除外している。したがって作業時間は「完全な引き渡し対応時間」ではない。除外が採点対象を変えていないことは更新時刻で確認した：Solの本実行ターン終了（10:56:32）以降に変更されたファイルは自己申告の `benchmark_summary.json`（11:30:37）だけで、採点対象のコード・カーブ・診断出力は10:54:21のまま不変である。Solの実際の成果物は `output/sol` にあり、`results/sol` が空であることを未完遂と誤判定していない。")

md("profiles-heading", """
## 7. 手法の違いは確認できるが、因果関係は追加検証が必要

以下は実装レビューと候補の自己申告を、観測された精度差と照合したもの。原因ごとの寄与を測る変更実験は未実施である。「この設計だから何点失った」とはまだ言えない。
""")
md("profile-astra", """
### Astra — 少ない処理量で一式を実装、長期の誤差が課題

ゼロ金利をlog1p年限上の自然3次スプラインで表す高度モデルと、Nelson–Siegel基準モデルを比較。重み付きHuber損失と年限グループの検証で平滑化を選び、高度モデルを採用した。キャッシュを含む処理総量は今回最少だった。

長期の誤差が目立つ一方、日本語のレポート本文にも必要な内容が見られる。長期の平滑化・価格付け規約が誤差に寄与した可能性と、英語キーワード判定による減点は分けて検証する必要がある。
""")
md("profile-sol", """
### Sol — 最短でソフトウェア満点、短期カーブの選択が再検証点

基準モデルは商品ごとの一定利回りを0.5年の満期バケットで集約し、PCHIP補間と平滑化を用いる。高度なゼロ金利スプラインも試したが、ホールドアウトで基準モデルが有利だったため基準モデルを採用した。

短期の細かな年限構造をバケット集約が弱めた可能性はある。ただし、高度モデルを選び直せば改善するとは限らない。共通の価格付け規約の下で、バケット幅と検証分割を1つずつ変える実験が必要である。
""")
md("profile-opus", """
### Opus — 高い主データ精度と多い検証、長い作業時間

瞬間フォワード金利の3次スプラインに、年限依存の曲率ペナルティ、HuberからTukeyへ移るロバスト反復、商品種別ごとの残差スケールを組み合わせた。年限ブロック検証に安定性条件も加えて高度モデルを選んだ。

主データのゼロ・フォワード誤差は今回最小だが、再開を含む時間とトークンは最大。自作テストの範囲も広い一方、s09のフォワード誤差は例外的に大きい。追加の反復量が常に追加の汎化精度へ結びついたとは言えない。
""")
md("profile-fable", """
### Fable — 高いストレス精度と比較的少ない応答回数

瞬間フォワード金利の3次Bスプラインを積分して価格付けし、年限依存のペナルティとグループ化した交差検証を用いた。ロバスト処理では、年限上で一貫した観測群を単純に外れ値として消さない工夫がある。

総合点と隠しシナリオの精度は今回良好だった。ただし、感度分析のJSON構造や自己パスの静的チェックで不合格が残る。少ないAPI応答回数を、少ない内部作業や常に優れた効率と同一視しない。
""")
table("model-metadata", "実行モデルと自己申告の修正回数", "モデルIDは記録値。修正回数は候補ごとの自己申告であり、共通定義による計測値ではない。",
      [{"model": NAMES[m], "model_id": MODEL_IDS[m], "effort": "xhigh", "iterations": S[m]["corrective_iterations"],
        "path": S[m]["candidate_path"]} for m in MODELS], "profiles",
      [("model", "モデル", "text"), ("model_id", "記録されたモデルID", "text"), ("effort", "推論設定", "text"),
       ("iterations", "修正回数（自己申告）", "number"), ("path", "提出先", "text")], ("model", "asc"))

md("test-heading", """
## 8. 再現性の検証は合格。ただし自作テスト数は性能点ではない

記録された数値ライブラリに合わせた隔離環境で全候補のpytestを再実行し、Astra 45件、Sol 20件、Opus 204件、Fable 60件がすべて合格した。これは各モデルが自分で書いた異なるテスト群であり、件数が多いほど未見データに強いとは限らない。

元の採点器のunittest探索ではAstra・Sol・Fableは各7件のみが対象だった。下表は全pytestと41件の採点チェックを分離している。Solは採点チェックの合格数が最多だが、連続値の数値得点が低いため総合首位ではない。
""")
table("test-results", "再実行テストと採点チェック", "pytest、採点チェック、隠しシナリオは別々の評価単位。",
      [{"model": NAMES[m], "pytest": S[m]["verified_tests_passed"], "pytest_fail": S[m]["verified_tests_failed"],
        "checks": f'{S[m]["hidden_checks_passed"]} / 41', "fails": S[m]["hidden_checks_failed"], "valid": "10 / 10"} for m in MODELS],
      "qa", [("model", "モデル", "text"), ("pytest", "pytest合格", "number"), ("pytest_fail", "pytest失敗", "number"),
       ("checks", "採点チェック合格", "text"), ("fails", "採点チェック不合格", "number"), ("valid", "有効シナリオ", "text")], ("model", "asc"))
md("integrity", """
### 検証環境と保全

Python 3.12.11 / NumPy 2.5.2 / pandas 2.3.3 / SciPy 1.18.1 / Matplotlib 3.11.1で再検証した。旧共有環境で発生したAstra・Fableの数値警告によるテスト失敗は、記録された版をそろえると解消。4モデルの自動採点は旧環境と小数第3位まで一致した。

公開入力12ファイル、評価側108ファイルのマニフェストは採点前後で一致。検証対象の候補コード・成果物ハッシュも不変だった。互換処理4テスト、使用量回復8テスト、実行後にも適用できる評価側12テストを既存の最終確認で通過している。実行前専用の「resultsが空」という検査は、提出後の検証対象から明示的に除外した。
""", "qa")

md("rubric", """
## 9. 採点の弱点を、候補モデルの弱点と混同しない

最終スコアは追跡可能な生得点として保持する。ただし下記の仕様依存・誤検知があるため、人が内容を再審査する前に補正点や真の順位を計算することは避けた。とくにAstraの日本語レポート点差は、数値精度の差とは別の論点である。また、4モデルが同一の理由で落とした欠損クォートのチェック（各1.0点）と、「モデル品質」の18/20点が数値精度と同じ誤差であることは、順位ではなくカテゴリの読み方に影響する。
""", "limits")
labels = read_csv("evaluator/ground_truth/corruption_labels.csv")
missing_ids = {r["obs_id"] for r in labels if r["issue"] == "missing_quote"}
check(len(missing_ids) == 4, "4 labeled missing-quote observations")
for m in MODELS:
    cleaning = read_csv(f'{S[m]["candidate_path"]}/outputs/diagnostics/cleaning.csv')
    acts = {r["obs_id"]: r["action"].lower() for r in cleaning if r["obs_id"] in missing_ids}
    check(len(acts) == 4 and all(a in {"correct", "downweight"} for a in acts.values()),
          f"{m}: all 4 missing quotes reconstructed (correct/downweight), none excluded")
    close(D[m].get("data_quality", {}).get("missing_handling_rate", 0.0), 0.0, f"{m}: missing_handling_rate is 0")
limitations = [
    {"priority": 1, "issue": "端数期間の支払規則", "models": "全モデル", "finding": "公開文書の満期・元本償還規則と、生成器のround(T×頻度)による支払時点が一部整合しない。", "impact": "価格誤差の一部が規約選択に依存する可能性。寄与は未推定。"},
    {"priority": 2, "issue": "「モデル品質」の中身", "models": "採点器", "finding": "モデル品質20点のうち18点は数値精度と同じ主カーブのRMSE（ゼロ7・重み付き3・フォワード4・非公開商品4）。形式チェックは2点。", "impact": "数値精度とモデル品質は同じ誤差の二重採点で、独立した証拠ではない。カテゴリ名からモデル選択の質を読み取らない。"},
    {"priority": 3, "issue": "英語キーワードによる章判定", "models": "Astra", "finding": "日本語見出しがあるが2/9概念しか認識されず、レポート1.889/5。", "impact": "満点との3.111点差を内容不足だけで説明できない。自動で満点には補正しない。"},
    {"priority": 4, "issue": "欠損クォートの採点規則", "models": "全モデル", "finding": "採点器は欠損クォート4件をaction=excludeにした場合だけ合格とする。4モデルとも二者間bid/askの中値で復元して採用（correct/downweight）し、全員が0/4で不合格、データ品質から各1.0点減。", "impact": "4モデル同一の失点は実装の弱点ではなく採点規則の選択。中値復元は妥当な処理であり、次回は仕様で扱いを固定する。"},
    {"priority": 5, "issue": "自分の出力パスの静的スキャン", "models": "Astra / Opus / Fable", "finding": "Astra30件、Opus1件、Fable1件はいずれも各自のパス。", "impact": "これらの警告は他モデル出力の閲覧証拠ではない。完全な隔離の証明でもない。"},
    {"priority": 6, "issue": "比較結果のキー名", "models": "Astra / Opus", "finding": "model_selected と、採点器の selected_model が不一致。", "impact": "情報の存在とスキーマ準拠が混ざる。事前にスキーマ固定が必要。"},
    {"priority": 7, "issue": "感度分析のJSON構造", "models": "Fable", "finding": "checksリストに結果があるが、トップレベル3キー以上という判定で不合格。", "impact": "チェック不合格だけで感度分析の欠落とは判断できない。"},
    {"priority": 8, "issue": "個人環境への絶対パス", "models": "Opus", "finding": "tests/test_cli.py に公開入力への固定絶対パスがある。", "impact": "移植性の課題。許可された公開入力への参照を情報漏洩と混同しない。"},
    {"priority": 9, "issue": "リスク表の任意列結合", "models": "採点器", "finding": "任意メタデータ列が正解表と衝突して停止。別ラッパーで必須列に限定。", "impact": "実行互換性を回復。元の配点・計算式・閾値は保持。"},
]
table("rubric-limitations", "解釈に影響する採点上の論点", "数値誤差、形式違反、誤検知を分けて評価する。",
      limitations, "limits", [("priority", "優先", "number"), ("issue", "論点", "text"), ("models", "対象", "text"),
      ("finding", "確認した事実", "text"), ("impact", "解釈への影響", "text")], ("priority", "asc"))
md("schedules", """
### 支払規則の違いは、有力な仮説だが未検証

公開文書では満期年を正とし、債券元本を満期に返す。一方、生成器・採点器は `round(T × frequency)` から支払列を作るため、端数満期では最後の支払時点が満期Tと一致しない場合がある。

Astraは端数期間を日数比例で扱い、Solは満期までの通常クーポンと満期元本を分け、Opusは満期から逆算した支払列を用い、Fableは観測への適合から規則を選んだ。これらの差が価格誤差に寄与した可能性はあるが、Opus・Fableだけが「明確に記載された正しい仕様を実装した」とは言えない。まず共通規約を定め、規約だけを入れ替える対照実験が必要である。
""")

md("next-steps", """
## 10. 次回は採点器を固定し、同じ条件で反復する

1. **仕様と採点スキーマを先に固定する。** 端数期間、元本償還日、欠損クォートの扱い（除外かbid/ask中値復元か）、比較JSON、感度JSON、レポートの言語非依存判定を明文化する。「モデル品質」は主カーブ精度と分離し、検証設計そのものを採点する項目に改める。自己パスの誤検知を修正し、新旧ルーブリックを別バージョンで保存する。
2. **共通の運用条件で複数回走らせる。** 入力・依存関係・プロンプト・ツール権限・推論設定・時間上限・中断時の扱いを統一する。乱数を変えた反復で中央値とばらつきを報告し、今回の単発結果と混ぜない。
3. **原因を切り分ける小さな実験を行う。** 支払規約だけを統一し、次にSolのバケット幅、Astraの長期平滑化、両者の検証分割を1要因ずつ比較する。改善幅を測るまでは原因別の失点を断定しない。
4. **目的別に選ぶ。** 精度重視ではFable（隠しシナリオで9/10最小）とOpus（主データで最小誤差）を再検証し、どの精度を優先するかを先に決める。時間制約ではSol、処理量制約ではAstraを候補として残し、必要な精度の下限を別途設定する。処理量はキャッシュ読取を除いた値で比較し、料金の意思決定には実請求データを追加する。

これらは次回への提案であり、このレポート作成で候補実装の修正や追加のモデル実行は行っていない。
""")
md("open-questions", """
## 判断前に残る問い

- どの精度水準なら実務用途として許容できるか。短期、長期、価格再現、DV01のどれを必須条件にするか。
- 「速さ」は作業ターン時間か、途中停止と引き渡し対応を含む完了までの時間か。
- キャッシュ割引と実際の契約条件を含む請求額はいくらか。現時点では未測定で、ゼロではない。
- 採点器の形式依存を除き、複数実行で比較したとき、今回の1点前後の順位差は残るか。
""")
md("caveats", """
## 前提と利用上の注意

本レポートの評価は **「留保付きで共有可能」**。対象4モデルはそれぞれ1回の実行で、信頼区間や統計的有意差は推定していない。モデルID・推論設定はログや候補記録の値であり、モデルファミリー全体の性能を表さない。合成データのベンチマークであり、実市場での運用成績も示していない。

時間は壁時計、トークンはキャッシュの反復入力を含むログ上の処理量（キャッシュ読取を除いた値も併記）。API応答数・自作テスト件数・自己申告の修正回数は定義が異なるため、それだけで「仕事の上手さ」を判定しない。数値精度に差があることと、その原因が特定できたことは別である。

図表のデータ出典から、参照ファイルと計算定義を確認できる。このHTMLは最終確認済みデータの固定スナップショットで、ライブ更新や外部接続は行わない。
""")

# Validate every field reference and the canonical artifact's portable bounds.
for t in TABLES:
    check(t["defaultSort"]["field"] in {c["field"] for c in t["columns"]}, f'{t["id"]}: declared sort field')
    for row in DATA[t["dataset"]]:
        check(all(c["field"] in row for c in t["columns"]), f'{t["id"]}: complete row')
for c in CHARTS:
    enc = c["encodings"]
    fields = [enc["x"]["field"]] + ([enc["y"]["field"]] if "field" in enc["y"] else enc["y"]["fields"])
    if "color" in enc:
        fields.append(enc["color"]["field"])
    check(all(all(f in row for f in fields) for row in DATA[c["dataset"]]), f'{c["id"]}: complete chart fields')
check(len(DATA) <= 50 and max(map(len, DATA.values())) <= 2000, "Dataset size bounds")
artifact = {"surface": "report", "manifest": {"version": 1, "surface": "report", "title": TITLE,
            "description": "4モデルの最終スコア・数値精度・実行時間・トークン・再現性・評価上の限界を統合。",
            "generatedAt": generated, "blocks": BLOCKS, "cards": CARDS, "charts": CHARTS, "tables": TABLES, "sources": SOURCES},
            "snapshot": {"version": 1, "generatedAt": generated, "status": "ready", "datasets": DATA}}
serialized = json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False)
check(len(serialized.encode()) < 3_000_000, "Artifact under 3MB")
check("/Users/" not in serialized and "../" not in serialized, "Portable payload excludes absolute and parent-traversing paths")
check(len({b["id"] for b in BLOCKS}) == len(BLOCKS), "Unique block IDs")
check(all(INPUTS[p] == hashlib.sha256((BASE / p).read_bytes()).hexdigest() for p in INPUTS), "Read-only sources unchanged during report generation")
(HERE / "artifact.json").write_text(serialized + "\n", encoding="utf-8")
(HERE / "validation.json").write_text(json.dumps({"status": "passed", "generated_at": generated,
    "checks_passed": len(CHECKS), "checks": CHECKS, "source_sha256": INPUTS,
    "rows": {k: len(v) for k, v in DATA.items()}, "model_runs": 4, "charts": len(CHARTS),
    "tables": len(TABLES), "blocks": len(BLOCKS), "caveats": ["single run per model", "raw rubric limitations", "cost unknown"]},
    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "passed", "checks": len(CHECKS), "charts": len(CHARTS), "tables": len(TABLES),
                  "blocks": len(BLOCKS), "artifact_bytes": len(serialized.encode()), "output": str(HERE / "artifact.json")}, ensure_ascii=False))
