#!/usr/bin/env python3
"""Build the portable technical report artifact for paper conversion QA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

TITLE = "LOB論文コーパス変換・検索頑健性QA"
GENERATED_AT = "2026-07-23T00:00:00+09:00"


def source_records() -> list[dict[str, Any]]:
    return [
        {
            "id": "conversion_results",
            "label": "Paper conversion audit results",
            "path": "reports/paper_conversion_qa/conversion_results.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_json_auto('reports/paper_conversion_qa/conversion_results.json', format = 'auto');",
                "description": "Compares source-PDF and converted-document tokens on every page and audits structures, hashes, images, formulas, and chunk limits.",
                "tables_used": [
                    "sources/papers/*.pdf",
                    "corpus/papers/*/document.json",
                    "corpus/papers/*/chunks.jsonl",
                    "corpus/papers/*/formulas.jsonl",
                ],
                "metric_definitions": [
                    "Page token recall: multiset overlap between normalized pdftotext tokens and converted page tokens divided by source token count.",
                    "P10: linearly interpolated tenth percentile across all 449 source pages.",
                ],
            },
        },
        {
            "id": "robustness_results",
            "label": "Paper retrieval robustness results",
            "path": "reports/paper_conversion_qa/robustness_results.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_json_auto('reports/paper_conversion_qa/robustness_results.json', format = 'auto');",
                "description": "Evaluates canonical, strong English paraphrase, and Japanese questions over the committed chunks.",
                "tables_used": [
                    "corpus/papers/*/chunks.jsonl",
                    "manifests/paper_retrieval_gold.json",
                    "manifests/paper_retrieval_robustness.json",
                ],
                "metric_definitions": [
                    "Exact evidence Recall@5: fraction of questions with an answer page in the first five chunks, upgraded to full formula-marker retrieval when formula IDs are specified.",
                    "Full formula Recall@5: fraction of formula-bearing questions for which every expected formula marker appears in the first five chunks.",
                ],
            },
        },
        {
            "id": "visual_checks",
            "label": "Rendered PDF visual checks",
            "path": "manifests/paper_conversion_visual_checks.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_json_auto('manifests/paper_conversion_visual_checks.json', format = 'auto');",
                "description": "Visual review of all pages below 0.80 token recall and the one page that previously crossed the hard chunk boundary.",
                "tables_used": ["sources/papers/*.pdf", "corpus/papers/*"],
            },
        },
        {
            "id": "corpus_index",
            "label": "Converted paper corpus index",
            "path": "corpus/papers/_index.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_json_auto('corpus/papers/_index.json', format = 'auto');",
                "description": "Versioned corpus inventory and PDF/hash/page/chunk/formula provenance.",
                "tables_used": ["corpus/papers/_index.json"],
            },
        },
    ]


def query_set_rows(robustness: dict[str, Any]) -> list[dict[str, Any]]:
    canonical = robustness["canonical"]["metrics"]["overall"]
    paraphrase = robustness["variants"]["strong_english_paraphrase"]["metrics"]["overall"]
    japanese = robustness["variants"]["japanese"]["metrics"]["overall"]
    return [
        {
            "query_set": "Canonical English",
            "queries": 66,
            "paper_recall_at_3": canonical["paper_recall_at_3"],
            "page_recall_at_5": canonical["page_recall_at_5"],
            "exact_evidence_recall_at_5": canonical["exact_evidence_recall_at_5"],
            "page_mrr": canonical["page_mrr"],
            "assessment": "PASS",
        },
        {
            "query_set": "Strong English paraphrase",
            "queries": 66,
            "paper_recall_at_3": paraphrase["paper_recall_at_3"],
            "page_recall_at_5": paraphrase["page_recall_at_5"],
            "exact_evidence_recall_at_5": paraphrase["exact_evidence_recall_at_5"],
            "page_mrr": paraphrase["page_mrr"],
            "assessment": "FAIL",
        },
        {
            "query_set": "Japanese (raw lexical)",
            "queries": 66,
            "paper_recall_at_3": japanese["paper_recall_at_3"],
            "page_recall_at_5": japanese["page_recall_at_5"],
            "exact_evidence_recall_at_5": japanese["exact_evidence_recall_at_5"],
            "page_mrr": japanese["page_mrr"],
            "assessment": "DIAGNOSTIC",
        },
    ]


def integrity_rows(conversion: dict[str, Any]) -> list[dict[str, Any]]:
    actuals = conversion["threshold_actuals"]
    thresholds = conversion["thresholds"]
    labels = {
        "page_token_recall_median": "Page token recall median",
        "page_token_recall_p10": "Page token recall P10",
        "page_token_recall_min": "Page token recall minimum",
        "page_count_mismatches": "PDF page count mismatches",
        "empty_converted_pages": "Empty converted pages",
        "oversized_chunks": "Chunks above 512 tokens",
        "missing_picture_files": "Missing picture files",
        "missing_formula_crop_files": "Missing formula crops",
        "unverified_or_fallback_formulas": "Unverified/fallback formulas",
    }
    rows = []
    for metric, label in labels.items():
        minimum_metric = metric.startswith("page_token_recall")
        comparator = ">=" if minimum_metric else "<="
        threshold = thresholds[metric]
        value = actuals[metric]
        passed = value >= threshold if minimum_metric else value <= threshold
        rows.append(
            {
                "check": label,
                "actual": value,
                "threshold": f"{comparator} {threshold}",
                "status": "PASS" if passed else "FAIL",
            }
        )
    return rows


def build_artifact(conversion: dict[str, Any], robustness: dict[str, Any]) -> dict[str, Any]:
    summary = conversion["summary"]
    canonical = robustness["canonical"]["metrics"]
    paraphrase = robustness["variants"]["strong_english_paraphrase"]["metrics"]
    japanese = robustness["variants"]["japanese"]["metrics"]
    query_rows = query_set_rows(robustness)
    visual_rows = [
        {
            "paper_id": check["paper_id"],
            "page": check["page"],
            "reason": check["reason"],
            "status": check["status"],
            "finding": check["finding"],
        }
        for check in conversion["visual_checks"]["checks"]
    ]
    summary_row = {
        "median_page_recall": summary["token_recall_median"],
        "p10_page_recall": summary["token_recall_p10"],
        "canonical_evidence_r5": canonical["overall"]["exact_evidence_recall_at_5"],
        "paraphrase_page_r5": paraphrase["overall"]["page_recall_at_5"],
        "japanese_page_r5": japanese["overall"]["page_recall_at_5"],
        "max_chunk_tokens": max(paper["max_chunk_tokens"] for paper in conversion["papers"]),
    }
    sources = source_records()
    return {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": TITLE,
            "description": "22論文449ページの変換忠実度と検索頑健性を分離して検証する技術監査",
            "generatedAt": GENERATED_AT,
            "cards": [
                {
                    "id": "median_recall",
                    "description": "全449ページにおける原PDF tokenの再現率中央値。",
                    "dataset": "summary",
                    "sourceId": "conversion_results",
                    "metrics": [
                        {
                            "label": "ページ再現率 中央値",
                            "field": "median_page_recall",
                            "format": "percent",
                        }
                    ],
                },
                {
                    "id": "p10_recall",
                    "description": "ページ再現率の下位10%点。",
                    "dataset": "summary",
                    "sourceId": "conversion_results",
                    "metrics": [
                        {
                            "label": "ページ再現率 P10",
                            "field": "p10_page_recall",
                            "format": "percent",
                        }
                    ],
                },
                {
                    "id": "canonical_evidence",
                    "description": "正解ページまたは指定formula markerが上位5件に揃ったcanonical質問の割合。",
                    "dataset": "summary",
                    "sourceId": "robustness_results",
                    "metrics": [
                        {
                            "label": "Canonical exact evidence R@5",
                            "field": "canonical_evidence_r5",
                            "format": "percent",
                        }
                    ],
                },
                {
                    "id": "paraphrase_recall",
                    "description": "強い英語言い換え66問の正解ページRecall@5。",
                    "dataset": "summary",
                    "sourceId": "robustness_results",
                    "metrics": [
                        {
                            "label": "Paraphrase page R@5",
                            "field": "paraphrase_page_r5",
                            "format": "percent",
                        }
                    ],
                },
                {
                    "id": "japanese_recall",
                    "description": "英語コーパスを未翻訳の語彙BM25で検索した日本語66問の診断値。",
                    "dataset": "summary",
                    "sourceId": "robustness_results",
                    "metrics": [
                        {
                            "label": "Japanese page R@5",
                            "field": "japanese_page_r5",
                            "format": "percent",
                        }
                    ],
                },
                {
                    "id": "chunk_limit",
                    "description": "修復後の全1,320 chunksにおける最大token数。",
                    "dataset": "summary",
                    "sourceId": "conversion_results",
                    "metrics": [
                        {
                            "label": "最大chunk tokens",
                            "field": "max_chunk_tokens",
                            "format": "number",
                        }
                    ],
                },
            ],
            "charts": [
                {
                    "id": "query_set_page_recall",
                    "title": "質問形式別の正解ページRecall@5",
                    "subtitle": "各66問。Canonical、強い英語言い換え、日本語の未翻訳語彙検索を比較。0起点。",
                    "type": "bar",
                    "dataset": "query_sets",
                    "sourceId": "robustness_results",
                    "encodings": {
                        "x": {"field": "query_set", "type": "nominal", "label": "質問形式"},
                        "y": {
                            "field": "page_recall_at_5",
                            "type": "quantitative",
                            "label": "正解ページ Recall@5",
                            "format": "percent",
                        },
                    },
                    "yAxisTitle": "正解ページ Recall@5",
                    "valueFormat": "percent",
                    "layout": "full",
                }
            ],
            "tables": [
                {
                    "id": "query_set_metrics",
                    "title": "質問形式別の検索指標",
                    "subtitle": "各66問。exact evidenceは式指定問では全formula markerの取得を要求。",
                    "dataset": "query_sets",
                    "sourceId": "robustness_results",
                    "columns": [
                        {"field": "query_set", "label": "質問形式", "type": "text"},
                        {"field": "queries", "label": "質問数", "format": "number"},
                        {"field": "paper_recall_at_3", "label": "論文 R@3", "format": "percent"},
                        {"field": "page_recall_at_5", "label": "ページ R@5", "format": "percent"},
                        {
                            "field": "exact_evidence_recall_at_5",
                            "label": "Exact evidence R@5",
                            "format": "percent",
                        },
                        {"field": "page_mrr", "label": "ページ MRR", "format": "number"},
                        {"field": "assessment", "label": "判定", "type": "text"},
                    ],
                },
                {
                    "id": "conversion_gates",
                    "title": "変換品質ゲート",
                    "subtitle": "原PDF、構造化文書、画像、数式、chunk境界を全件検査。",
                    "dataset": "conversion_gates",
                    "sourceId": "conversion_results",
                    "columns": [
                        {"field": "check", "label": "検査", "type": "text"},
                        {"field": "actual", "label": "実測", "format": "number"},
                        {"field": "threshold", "label": "基準", "type": "text"},
                        {"field": "status", "label": "判定", "type": "text"},
                    ],
                },
                {
                    "id": "paper_quality",
                    "title": "論文別の変換品質",
                    "subtitle": "22本。ページtoken再現率、構造要素数、最大chunk長。",
                    "dataset": "papers",
                    "sourceId": "conversion_results",
                    "defaultSort": {"field": "token_recall_min", "direction": "asc"},
                    "columns": [
                        {"field": "paper_id", "label": "論文", "type": "text"},
                        {"field": "page_count", "label": "pages", "format": "number"},
                        {"field": "token_recall_median", "label": "median", "format": "percent"},
                        {"field": "token_recall_p10", "label": "P10", "format": "percent"},
                        {"field": "token_recall_min", "label": "min", "format": "percent"},
                        {"field": "pages_below_0_90", "label": "<90% pages", "format": "number"},
                        {"field": "tables", "label": "tables", "format": "number"},
                        {"field": "pictures", "label": "pictures", "format": "number"},
                        {"field": "formulas", "label": "formulas", "format": "number"},
                        {"field": "chunks", "label": "chunks", "format": "number"},
                        {"field": "max_chunk_tokens", "label": "max tokens", "format": "number"},
                    ],
                },
                {
                    "id": "low_pages",
                    "title": "token再現率が低いページ",
                    "subtitle": "下位20ページ。数式・複雑表・画像ページが中心。",
                    "dataset": "low_pages",
                    "sourceId": "conversion_results",
                    "defaultSort": {"field": "token_recall", "direction": "asc"},
                    "columns": [
                        {"field": "paper_id", "label": "論文", "type": "text"},
                        {"field": "page", "label": "page", "format": "number"},
                        {"field": "token_recall", "label": "recall", "format": "percent"},
                        {"field": "token_precision", "label": "precision", "format": "percent"},
                        {
                            "field": "source_token_count",
                            "label": "source tokens",
                            "format": "number",
                        },
                        {
                            "field": "converted_token_count",
                            "label": "converted tokens",
                            "format": "number",
                        },
                        {"field": "table_count", "label": "tables", "format": "number"},
                    ],
                },
                {
                    "id": "visual_review",
                    "title": "原PDFレンダリングとの目視確認",
                    "subtitle": "自動検査の下位ページ5件と修復対象1件。",
                    "dataset": "visual_checks",
                    "sourceId": "visual_checks",
                    "columns": [
                        {"field": "paper_id", "label": "論文", "type": "text"},
                        {"field": "page", "label": "page", "format": "number"},
                        {"field": "reason", "label": "選定理由", "type": "text"},
                        {"field": "status", "label": "判定", "type": "text"},
                        {"field": "finding", "label": "確認結果", "type": "text"},
                    ],
                },
            ],
            "sources": [
                {"id": source["id"], "label": source["label"], "path": source["path"]}
                for source in sources
            ],
            "blocks": [
                {"id": "title", "type": "markdown", "body": f"# {TITLE}"},
                {
                    "id": "technical_summary",
                    "type": "markdown",
                    "body": (
                        "## 技術サマリー\n\n"
                        "**変換コーパスはAI読解・検索の基盤として合格。ただし、現行の語彙検索をそのまま本番RAGに使うのは不十分。** "
                        f"22論文449ページのtoken再現率は中央値{summary['token_recall_median']:.2%}、P10 "
                        f"{summary['token_recall_p10']:.2%}で、空ページ、原本hash不一致、512-token超過、欠落画像・数式cropは0。"
                        f"一方、正解ページRecall@5はcanonical質問で100%から強い英語言い換えで{paraphrase['overall']['page_recall_at_5']:.2%}、"
                        f"日本語の未翻訳語彙検索で{japanese['overall']['page_recall_at_5']:.2%}へ低下した。"
                    ),
                },
                {
                    "id": "metrics",
                    "type": "metric-strip",
                    "cardIds": [
                        "median_recall",
                        "p10_recall",
                        "canonical_evidence",
                        "paraphrase_recall",
                        "japanese_recall",
                        "chunk_limit",
                    ],
                },
                {
                    "id": "conversion_findings",
                    "type": "markdown",
                    "sourceId": "conversion_results",
                    "body": (
                        "## 本文・構造・数式の変換は全品質ゲートを通過\n\n"
                        f"全{summary['page_count']}ページに変換textがあり、ページtoken再現率の平均は{summary['token_recall_mean']:.2%}。"
                        f"134表、135図、424 formula recordsを追跡できる。低スコア5ページは数式密集、複雑表、図だけのページで、"
                        "原PDFレンダリングとの目視確認では欠落ではなく表現形式の差と判断した。"
                    ),
                },
                {"id": "conversion_gate_table", "type": "table", "tableId": "conversion_gates"},
                {"id": "paper_table", "type": "table", "tableId": "paper_quality"},
                {
                    "id": "retrieval_findings",
                    "type": "markdown",
                    "sourceId": "robustness_results",
                    "body": (
                        "## 強い言い換えで語彙検索の順位品質が崩れる\n\n"
                        f"強い英語言い換え66問では論文Recall@3が{paraphrase['overall']['paper_recall_at_3']:.2%}、正解ページRecall@5が"
                        f"{paraphrase['overall']['page_recall_at_5']:.2%}となり、事前基準90%/80%を下回った。"
                        f"日本語66問は英字のモデル名・略語だけで偶発的に検索できるケースを含み、正解ページRecall@5は"
                        f"{japanese['overall']['page_recall_at_5']:.2%}。多言語対応を示す値ではない。"
                    ),
                },
                {
                    "id": "query_chart",
                    "type": "chart",
                    "chartId": "query_set_page_recall",
                    "layout": "full",
                },
                {"id": "query_table", "type": "table", "tableId": "query_set_metrics"},
                {
                    "id": "evidence_findings",
                    "type": "markdown",
                    "sourceId": "robustness_results",
                    "body": (
                        "## ページhitと回答に必要な正確な式の取得は同じではない\n\n"
                        f"Canonical 66問のexact evidence Recall@5は{canonical['overall']['exact_evidence_recall_at_5']:.2%}。"
                        f"formula IDを指定した23問では、期待する式markerがすべて上位5件に入る割合は"
                        f"{canonical['formula_evidence']['full_formula_recall_at_5']:.2%}だった。"
                        "したがって、ページhit 100%だけから生成回答のfaithfulnessを主張してはいけない。"
                    ),
                },
                {
                    "id": "scope",
                    "type": "markdown",
                    "body": (
                        "## 対象・データ・指標定義\n\n"
                        "対象はDocling 2.114.0で変換した全22論文。token再現率は原PDFの埋め込みtext layerをpdftotextでページ単位に抽出し、"
                        "Unicode正規化・小文字化・行末hyphen結合後のmultiset overlapを測る。検索は1,320 chunksに対する既存のfield-aware BM25。"
                        "質問集合はcanonical 66問、同じ正解を持つ強い英語言い換え66問、日本語66問である。"
                    ),
                },
                {
                    "id": "methodology",
                    "type": "markdown",
                    "body": (
                        "## 方法と検証設計\n\n"
                        "変換監査はPDF hash・ページ数・JSON構造・ページtext・表・画像・formula crop・chunk token上限を全件検査した。"
                        "自動検査の下位5ページと、修復前に512 tokenを超えた表ページを原PDFのPNGへrenderして確認した。"
                        "検索頑健性はcanonical goldを変更せず質問文だけを置換し、paper/page/exact-evidence順位を同じコードで再計算した。"
                    ),
                },
                {"id": "low_page_table", "type": "table", "tableId": "low_pages"},
                {"id": "visual_table", "type": "table", "tableId": "visual_review"},
                {
                    "id": "limitations",
                    "type": "markdown",
                    "body": (
                        "## 制約・不確実性\n\n"
                        "- token overlapは語順、意味、表のセル結合、数式記号の等価性を評価しない。\n"
                        "- 135図は画像として保存されるがmachine annotationは0で、16図はcaptionもない。text-only RAGは曲線上の値を読めない。\n"
                        "- 191式は一次資料の逐語照合ではなくsemantic high confidence。引用時はformula recordのnoteと原式cropを確認する。\n"
                        "- 言い換え・日本語variantと目視判定は単一レビュアーで、独立評価ではない。\n"
                        "- exact evidenceは取得文脈の存在を測り、生成回答そのものの正誤・引用整合性は未評価。"
                    ),
                },
                {
                    "id": "next_steps",
                    "type": "markdown",
                    "body": (
                        "## 推奨する次の作業\n\n"
                        "1. multilingual embeddingとBM25のhybrid retrievalを別holdoutで比較する。\n"
                        "2. top chunkから隣接chunkと同一ページのformula markerを展開し、exact evidence Recall@5を改善する。\n"
                        "3. 66問すべてにsource-backed reference answerとclaim-level citation判定を追加する。\n"
                        "4. captionなし16図と重要plotを優先し、multimodal captionまたは構造化chart dataを追加する。"
                    ),
                },
                {
                    "id": "further_questions",
                    "type": "markdown",
                    "body": (
                        "## 追加で答えるべき問い\n\n"
                        "- hybrid検索の改善は未知の質問にも一般化するか。\n"
                        "- 同一ページ展開でcontext量が増えたとき、回答のprecisionは落ちないか。\n"
                        "- 図の数値化はどの論文・図から着手すると回答可能性を最も改善するか。"
                    ),
                },
                {
                    "id": "source_notes",
                    "type": "markdown",
                    "body": (
                        "## ソース注記\n\n"
                        "チャートmap: 検索頑健性セクションで質問形式ごとの正解ページRecall@5を比較する単一系列barを使用。"
                        "各集合66問で同じ分母を持ち、絶対割合比較なので0起点とした。論文別品質と監査下位ページはexact lookupが目的のためtableを使用した。"
                    ),
                },
            ],
        },
        "snapshot": {
            "version": 1,
            "generatedAt": GENERATED_AT,
            "status": "ready",
            "datasets": {
                "summary": [summary_row],
                "query_sets": query_rows,
                "conversion_gates": integrity_rows(conversion),
                "papers": conversion["papers"],
                "low_pages": conversion["lowest_recall_pages"],
                "visual_checks": visual_rows,
            },
        },
        "sources": sources,
    }


def parse_args() -> argparse.Namespace:
    project_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--conversion",
        type=Path,
        default=project_dir / "reports/paper_conversion_qa/conversion_results.json",
    )
    parser.add_argument(
        "--robustness",
        type=Path,
        default=project_dir / "reports/paper_conversion_qa/robustness_results.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_dir / "reports/paper_conversion_qa/artifact.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    conversion = json.loads(args.conversion.read_text(encoding="utf-8"))
    robustness = json.loads(args.robustness.read_text(encoding="utf-8"))
    artifact = build_artifact(conversion, robustness)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
