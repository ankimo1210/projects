from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def main() -> None:
    generated_at = datetime.now(UTC).isoformat()
    questions = read_jsonl(ROOT / "data" / "reviewed" / "questions.jsonl")
    status_counts = Counter(str(row["human_review_status"]) for row in questions)
    source_counts = Counter(str(row["source_id"]) for row in questions)
    quality_counts = Counter(str(row["quality_category"]) for row in questions)

    connection = duckdb.connect()

    def query_rows(filename: str) -> list[dict[str, object]]:
        sql = (ROOT / "scripts" / filename).read_text()
        result = connection.execute(sql)
        columns = [description[0] for description in result.description]
        return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]

    summary = query_rows("quality_summary.sql")[0]
    source_rows = query_rows("source_candidate_counts.sql")
    audit_rows = query_rows("audit_checks.sql")
    for row in audit_rows:
        row["check"] = row.pop("check_name")
    total = int(summary["candidate_questions"])
    fetched = int(summary["fetched_sources"])
    screened = int(summary["machine_screened"])
    fact_check = int(summary["fact_check_required"])
    rejected = int(summary["rejected"])
    japanese = int(summary["japanese_candidates"])
    english = int(summary["english_candidates"])
    answered = int(summary["answered_candidates"])
    leaks = int(summary["public_safe_text_leaks"])
    top_source = source_rows[0]
    top_label = str(top_source["source_label"])
    top_count = int(top_source["candidate_count"])
    top_share = top_count / total if total else 0
    profile = {
        "generated_at": generated_at,
        "summary": summary,
        "status_counts": dict(status_counts),
        "quality_counts": dict(quality_counts),
        "source_counts": dict(source_counts),
        "audit_checks": audit_rows,
    }
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "quality_profile.json").write_text(
        json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    source_specs = [
        {
            "id": "summary-sql",
            "label": "Corpus quality summary query",
            "path": "scripts/quality_summary.sql",
            "query": {
                "description": "DuckDB summary of registry, fetch, candidate, review, pattern, and public-safe outputs",
                "language": "sql",
                "executed_at": generated_at,
                "filters": [f"All {total} candidates from explicitly approved public URLs"],
                "metric_definitions": [
                    "Candidate: one question-like text span at one source position",
                    "Machine-screened: passed conservative heading, fragment, and PDF-spacing checks",
                ],
            },
        },
        {
            "id": "source-counts-sql",
            "label": "Official source candidate-count query",
            "path": "scripts/source_candidate_counts.sql",
            "query": {
                "description": "DuckDB source-level counts for the first approved fetch cohort",
                "language": "sql",
                "executed_at": generated_at,
                "filters": ["Registry reviewed on 2026-07-11"],
            },
        },
        {
            "id": "audit-sql",
            "label": "Stable data-quality checks",
            "path": "scripts/audit_checks.sql",
            "query": {
                "description": "DuckDB completeness, uniqueness, extraction, coverage, and leakage checks",
                "language": "sql",
                "executed_at": generated_at,
                "metric_definitions": [
                    "Leak: any non-empty raw_text, normalized_text, or answer_text field"
                ],
            },
        },
    ]
    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": "WSET L3コーパス：データ品質監査",
            "description": "明示承認した公開ソースの収集・抽出・公開安全性を監査",
            "generatedAt": generated_at,
            "cards": [
                {
                    "id": "sources-card",
                    "description": "手動審査済みソース台帳",
                    "dataset": "summary",
                    "sourceId": "summary-sql",
                    "metrics": [{"label": "登録ソース", "field": "registered_sources", "format": "number"}],
                },
                {
                    "id": "fetched-card",
                    "description": "明示承認され取得に成功した公開ソース",
                    "dataset": "summary",
                    "sourceId": "summary-sql",
                    "metrics": [{"label": "取得成功", "field": "fetched_sources", "format": "number"}],
                },
                {
                    "id": "candidates-card",
                    "description": "人手審査前の質問らしいテキスト範囲",
                    "dataset": "summary",
                    "sourceId": "summary-sql",
                    "metrics": [{"label": "候補", "field": "candidate_questions", "format": "number"}],
                },
                {
                    "id": "screened-card",
                    "description": "保守的な機械スクリーニング通過数",
                    "dataset": "summary",
                    "sourceId": "summary-sql",
                    "metrics": [{"label": "機械通過", "field": "machine_screened", "format": "number"}],
                },
                {
                    "id": "leaks-card",
                    "description": "公開安全版に残った第三者本文フィールド",
                    "dataset": "summary",
                    "sourceId": "summary-sql",
                    "metrics": [{"label": "本文漏洩", "field": "public_safe_text_leaks", "format": "number"}],
                },
                {
                    "id": "patterns-card",
                    "description": "独自に作成した抽象問題パターン",
                    "dataset": "summary",
                    "sourceId": "summary-sql",
                    "metrics": [{"label": "独自パターン", "field": "original_patterns", "format": "number"}],
                },
            ],
            "charts": [
                {
                    "id": "source-candidate-chart",
                    "title": "ソース別の質問候補数",
                    "subtitle": f"全{total}候補。未審査の抽出単位を集計",
                    "showDescription": True,
                    "intent": "comparison",
                    "question": "どの公開ソースが候補数を構成しているか",
                    "rationale": f"{len(source_rows)}カテゴリの絶対数比較なので棒グラフを使用",
                    "type": "bar",
                    "dataset": "source_counts",
                    "sourceId": "source-counts-sql",
                    "encodings": {
                        "x": {"field": "source_label", "type": "nominal", "label": "ソース"},
                        "y": {"field": "candidate_count", "type": "quantitative", "aggregate": "none", "format": "number", "label": "候補数"},
                        "tooltip": [
                            {"field": "candidate_count", "type": "quantitative", "label": "候補数"},
                            {"field": "share_of_candidates", "type": "quantitative", "format": "percent", "label": "構成比"},
                            {"field": "fetched", "type": "nominal", "label": "取得成功"},
                        ],
                    },
                    "layout": "full",
                    "maxRows": len(source_rows),
                }
            ],
            "tables": [
                {
                    "id": "audit-table",
                    "title": "主要データ品質チェック",
                    "subtitle": "現在の収集時点。severityはアプリ投入への影響度",
                    "showDescription": True,
                    "dataset": "audit_checks",
                    "defaultSort": {"field": "check", "direction": "asc"},
                    "density": "spacious",
                    "sourceId": "audit-sql",
                    "layout": "full",
                    "columns": [
                        {"field": "check", "label": "チェック", "type": "text"},
                        {"field": "evidence", "label": "証拠", "type": "text"},
                        {"field": "severity", "label": "重要度", "type": "text"},
                        {"field": "confidence", "label": "確信度", "type": "text"},
                    ],
                }
            ],
            "sources": source_specs,
            "blocks": [
                {"id": "title", "type": "markdown", "body": "# WSET L3コーパス：データ品質監査", "layout": "full"},
                {
                    "id": "technical-summary",
                    "type": "markdown",
                    "sourceId": "summary-sql",
                    "layout": "full",
                    "body": f"## 技術サマリー\n\n**公開研究データは{total}件まで拡大したが、人手審査前である。** {fetched}ソースの取得に成功し、英語{english}件、日本語{japanese}件、解答付き{answered}件を構造化した。{screened}件が機械スクリーニングを通過、{fact_check}件は要確認、{rejected}件は見出し・断片として除外候補。public-safe出力の本文漏洩は{leaks}件だった。",
                },
                {"id": "metrics", "type": "metric-strip", "cardIds": ["sources-card", "fetched-card", "candidates-card", "screened-card", "leaks-card", "patterns-card"], "layout": "full"},
                {
                    "id": "finding-source-concentration",
                    "type": "markdown",
                    "sourceId": "source-counts-sql",
                    "layout": "full",
                    "body": f"## 候補の{top_share:.0%}は{top_label}に集中\n\n{top_label}由来が{top_count}/{total}件で、コーパスの形式・分野分布を強く支配している。下図は候補数の所在を示すもので、品質や再利用許諾の比較ではない。",
                },
                {"id": "source-chart", "type": "chart", "chartId": "source-candidate-chart", "layout": "full"},
                {
                    "id": "scope",
                    "type": "markdown",
                    "layout": "full",
                    "body": "## 対象・粒度・指標定義\n\n対象期間は2026年7月11日の取得スナップショット。粒度は `source_id + source_url + source_position` ごとの質問らしいテキスト範囲で、複数行設問の分断や学習到達目標を含みうる。`machine_screened` は保守的な見出し・断片・PDF文字間隔チェックを通った状態で、人による正誤・著作権・自然な日本語の承認を意味しない。",
                },
                {
                    "id": "method",
                    "type": "markdown",
                    "layout": "full",
                    "body": "## 再現可能な監査方法\n\n明示承認した公開URLだけをrobots.txt確認、ドメイン毎6回/分、同時接続1で取得し、HTTP状態・取得時刻・SHA-256を記録した。HTML埋め込みJSON、公開フロントエンドが利用する匿名JSON、HTML本文、PDFを別々に抽出。決定的ID、必須項目、列挙値、信頼度範囲、exact/near重複、public-safe本文除去を自動テストした。詳細計算は `notebooks/03_quality_review.ipynb` に保存している。",
                },
                {
                    "id": "audit-heading",
                    "type": "markdown",
                    "layout": "full",
                    "sourceId": "audit-sql",
                    "body": f"## 系譜と公開安全性は合格、内容品質は未完成\n\n必須系譜とID一意性には欠損がなく、public-safeの本文漏洩は{leaks}件だった。一方、要確認{fact_check}件と人手審査0件はアプリ投入を止める課題である。",
                },
                {"id": "audit", "type": "table", "tableId": "audit-table", "layout": "full"},
                {
                    "id": "limitations",
                    "type": "markdown",
                    "layout": "full",
                    "body": "## 限界・不確実性・頑健性\n\n件数は大きく増えたが、AnkiWebの英語フラッシュカードに集中し、ソース横断の代表標本ではない。品質スコアはレビュー補助であり客観値ではない。フラッシュカードには旧制度・事実誤り・WSET範囲外が含まれる可能性がある。取得成功は再配布許諾を意味せず、第三者本文はprivate exportだけに保持する。有料・登録・会員限定素材にはアクセスしていない。",
                },
                {
                    "id": "next-steps",
                    "type": "markdown",
                    "layout": "full",
                    "sourceId": "summary-sql",
                    "body": f"## 次の推奨作業\n\n1. {screened}件の機械通過候補を優先度順に人手審査する。\n2. 要確認{fact_check}件のPDF・HTML分断を再構成する。\n3. 日本語{japanese}件について、設問と解答・採点基準を関連付ける。\n4. ソース別の事実誤り・旧制度・翻訳品質を検証する。\n5. public-safe漏洩{leaks}件を継続的なblocking testにする。",
                },
                {
                    "id": "questions",
                    "type": "markdown",
                    "layout": "full",
                    "body": "## 次に決めるべき問い\n\n- 日本語問題の最初の対象を、栽培・醸造・主要産地のどこに置くか。\n- 第三者ソースはパターン分析だけに使い、アプリ本文を100%独自作成に固定するか。\n- 人手レビューの合格条件を、事実・WSET範囲・日本語・採点可能性・権利の5軸でどう定義するか。",
                },
            ],
        },
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": "ready",
            "datasets": {
                "summary": [summary],
                "source_counts": source_rows,
                "audit_checks": audit_rows,
            },
        },
        "sources": source_specs,
    }
    (reports / "artifact.json").write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
