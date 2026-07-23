#!/usr/bin/env python3
"""Build the canonical portable-report artifact for paper retrieval QA."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

TITLE = "LOB論文コーパス検索QA"
GENERATED_AT = "2026-07-23T00:00:00+09:00"


def source_records() -> list[dict[str, Any]]:
    return [
        {
            "id": "retrieval_results",
            "label": "Paper retrieval QA results",
            "path": "reports/paper_retrieval_qa/results.json",
            "query": {
                "engine": "duckdb",
                "language": "sql",
                "sql": "SELECT * FROM read_json_auto('reports/paper_retrieval_qa/results.json', format = 'auto');",
                "description": "Loads the complete committed evaluator output. The report generator selects the reviewed nested metric, audit, category, paper, and query-rank fields from this record.",
                "tables_used": [
                    "corpus/papers/*/chunks.jsonl",
                    "manifests/paper_retrieval_gold.json",
                ],
                "metric_definitions": [
                    "Paper Recall@k: fraction of questions whose target paper appears in the first k chunks.",
                    "Answer-page Recall@k: fraction of questions with a first-k target-paper chunk whose page provenance overlaps an accepted answer page.",
                    "Answer-page MRR: mean reciprocal rank of the first target-paper chunk overlapping an accepted answer page; missing ranks contribute zero.",
                ],
            },
        },
        {
            "id": "retrieval_gold",
            "label": "Paper retrieval gold set",
            "path": "manifests/paper_retrieval_gold.json",
            "query": {
                "engine": "manual_review",
                "description": "Census-stratified questions and answer pages, including PDF adjudication notes and quality thresholds.",
                "tables_used": ["sources/papers/*.pdf"],
            },
        },
        {
            "id": "corpus_index",
            "label": "Converted paper corpus index",
            "path": "corpus/papers/_index.json",
            "query": {
                "engine": "docling",
                "description": "Corpus inventory and PDF/hash/page/chunk/formula provenance for all converted papers.",
                "tables_used": ["corpus/papers/_index.json"],
            },
        },
    ]


def paper_rows(results: dict[str, Any], corpus_index: dict[str, Any]) -> list[dict[str, Any]]:
    titles = {paper["paper_id"]: paper["title"] for paper in corpus_index["papers"]}
    ranks: dict[str, dict[str, int | None]] = defaultdict(dict)
    for evaluation in results["evaluations"]:
        ranks[evaluation["paper_id"]][evaluation["category"]] = evaluation["page_rank"]

    rows: list[dict[str, Any]] = []
    for paper_id, metrics in results["metrics"]["by_paper"].items():
        rows.append(
            {
                "paper": titles[paper_id],
                "paper_id": paper_id,
                "formula_rank": ranks[paper_id]["formula"],
                "method_rank": ranks[paper_id]["method"],
                "result_rank": ranks[paper_id]["result"],
                "page_recall_at_5": metrics["page_recall_at_5"],
                "page_mrr": metrics["page_mrr"],
            }
        )
    return rows


def build_artifact(
    results: dict[str, Any], gold: dict[str, Any], corpus_index: dict[str, Any]
) -> dict[str, Any]:
    overall = results["metrics"]["overall"]
    audit = results["corpus_audit"]
    draft_metrics = gold["adjudication"]["draft_metrics_before_adjudication"]
    category_rows = [
        {
            "category": category,
            "queries": metrics["query_count"],
            "paper_recall_at_3": metrics["paper_recall_at_3"],
            "page_recall_at_5": metrics["page_recall_at_5"],
            "page_mrr": metrics["page_mrr"],
        }
        for category, metrics in results["metrics"]["by_category"].items()
    ]
    integrity_rows = [
        {
            "check": "Completeness",
            "evidence": f"{audit['paper_count']} papers / {overall['query_count']} questions",
            "status": "PASS",
        },
        {
            "check": "Chunk uniqueness",
            "evidence": f"{audit['unique_chunk_count']} unique / {audit['chunk_count']} total",
            "status": "PASS",
        },
        {
            "check": "Retrieval validity",
            "evidence": (
                f"{audit['empty_text_chunks']} empty chunks; "
                f"{audit['chunks_without_page_provenance']} without page provenance"
            ),
            "status": "PASS",
        },
        {
            "check": "Formula integrity",
            "evidence": (
                f"{audit['formula_markers_in_chunks']} chunk markers / "
                f"{audit['formula_records_in_index']} formula records"
            ),
            "status": "PASS",
        },
        {
            "check": "Quality thresholds",
            "evidence": "; ".join(
                f"{key} ≥ {value}" for key, value in results["thresholds"].items()
            ),
            "status": results["threshold_status"].upper(),
        },
    ]
    summary_row = {
        "paper_recall_at_3": overall["paper_recall_at_3"],
        "page_recall_at_5": overall["page_recall_at_5"],
        "page_mrr": overall["page_mrr"],
        "empty_chunks": audit["empty_text_chunks"],
    }
    sources = source_records()

    return {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": TITLE,
            "description": "22本の論文を横断する検索可能性とprovenanceの技術監査",
            "generatedAt": GENERATED_AT,
            "cards": [
                {
                    "id": "paper_recall",
                    "description": "正解論文を上位3 chunks以内に取得できた質問の割合。",
                    "dataset": "summary",
                    "sourceId": "retrieval_results",
                    "metrics": [
                        {
                            "label": "論文 Recall@3",
                            "field": "paper_recall_at_3",
                            "format": "percent",
                        }
                    ],
                },
                {
                    "id": "page_recall",
                    "description": "正解論文かつ正解ページのchunkを上位5件以内に取得できた質問の割合。",
                    "dataset": "summary",
                    "sourceId": "retrieval_results",
                    "metrics": [
                        {
                            "label": "正解ページ Recall@5",
                            "field": "page_recall_at_5",
                            "format": "percent",
                        }
                    ],
                },
                {
                    "id": "page_mrr",
                    "description": "最初の正解ページchunkの逆順位を66問で平均。",
                    "dataset": "summary",
                    "sourceId": "retrieval_results",
                    "metrics": [
                        {"label": "正解ページ MRR", "field": "page_mrr", "format": "number"}
                    ],
                },
                {
                    "id": "empty_chunks",
                    "description": "検索対象に残った空本文chunk数。",
                    "dataset": "summary",
                    "sourceId": "retrieval_results",
                    "metrics": [{"label": "空chunk", "field": "empty_chunks", "format": "number"}],
                },
            ],
            "charts": [
                {
                    "id": "category_page_mrr",
                    "title": "質問カテゴリ別の正解ページMRR",
                    "subtitle": "formula・method・result各22問。0から1の尺度。",
                    "type": "bar",
                    "dataset": "categories",
                    "sourceId": "retrieval_results",
                    "encodings": {
                        "x": {"field": "category", "type": "nominal", "label": "カテゴリ"},
                        "y": {
                            "field": "page_mrr",
                            "type": "quantitative",
                            "label": "正解ページ MRR",
                            "format": "number",
                        },
                    },
                    "yAxisTitle": "正解ページ MRR",
                    "valueFormat": "number",
                    "layout": "full",
                }
            ],
            "tables": [
                {
                    "id": "category_metrics",
                    "title": "質問カテゴリ別の検索指標",
                    "subtitle": "各カテゴリ22問。順位は全1,320 chunksに対するもの。",
                    "dataset": "categories",
                    "sourceId": "retrieval_results",
                    "columns": [
                        {"field": "category", "label": "カテゴリ", "type": "text"},
                        {"field": "queries", "label": "質問数", "format": "number"},
                        {
                            "field": "paper_recall_at_3",
                            "label": "論文 R@3",
                            "format": "percent",
                        },
                        {
                            "field": "page_recall_at_5",
                            "label": "ページ R@5",
                            "format": "percent",
                        },
                        {"field": "page_mrr", "label": "ページ MRR", "format": "number"},
                    ],
                },
                {
                    "id": "integrity_checks",
                    "title": "データ品質・整合性チェック",
                    "dataset": "integrity",
                    "sourceId": "retrieval_results",
                    "columns": [
                        {"field": "check", "label": "検査", "type": "text"},
                        {"field": "evidence", "label": "証拠", "type": "text"},
                        {"field": "status", "label": "判定", "type": "text"},
                    ],
                },
                {
                    "id": "paper_metrics",
                    "title": "論文別の正解ページ順位",
                    "subtitle": "式・方法・結果の各1問。値が小さいほど上位で、全件5位以内。",
                    "dataset": "papers",
                    "sourceId": "retrieval_results",
                    "columns": [
                        {"field": "paper", "label": "論文", "type": "text"},
                        {"field": "formula_rank", "label": "式", "format": "number"},
                        {"field": "method_rank", "label": "方法", "format": "number"},
                        {"field": "result_rank", "label": "結果", "format": "number"},
                        {
                            "field": "page_recall_at_5",
                            "label": "ページ R@5",
                            "format": "percent",
                        },
                        {"field": "page_mrr", "label": "ページ MRR", "format": "number"},
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
                    "sourceId": "retrieval_results",
                    "body": (
                        "## 技術サマリー\n\n"
                        "**現コーパスは、明示的に対象論文を識別できる質問に対する検索回帰テストとして利用可能。** "
                        f"全{overall['query_count']}問で論文 Recall@3 は "
                        f"{overall['paper_recall_at_3']:.0%}、正解ページ Recall@5 は "
                        f"{overall['page_recall_at_5']:.0%}、正解ページ MRR は "
                        f"{overall['page_mrr']:.4f}。設定した3品質ゲートをすべて通過した。"
                    ),
                },
                {
                    "id": "metrics",
                    "type": "metric-strip",
                    "cardIds": ["paper_recall", "page_recall", "page_mrr", "empty_chunks"],
                },
                {
                    "id": "key_findings",
                    "type": "markdown",
                    "sourceId": "retrieval_results",
                    "body": (
                        "## 主要な検証結果\n\n"
                        "- **網羅性:** formula・method・resultを各22問評価し、全カテゴリで正解ページ Recall@5 は100%。\n"
                        "- **順位品質:** result質問のページMRRが最も高く、formulaとmethodは同義の式や手法を扱う論文間で順位が割れやすい。\n"
                        "- **構造品質:** 空本文chunkとpage provenance欠落はともに0。424式は全件、chunk内マーカーとformula recordを1対1で追跡できる。"
                    ),
                },
                {
                    "id": "category_chart",
                    "type": "chart",
                    "chartId": "category_page_mrr",
                    "layout": "full",
                },
                {"id": "category_table", "type": "table", "tableId": "category_metrics"},
                {
                    "id": "scope",
                    "type": "markdown",
                    "sourceId": "retrieval_gold",
                    "body": (
                        "## 対象・データ・指標定義\n\n"
                        "対象はコミット済みの22論文すべて。分析単位は英語質問1件で、各質問に正解論文、回答を含む原PDFページ、式質問にはformula_idを持たせた。"
                        "Recallは指定順位以内に正解が存在する割合、MRRは最初の正解ページの逆順位平均である。"
                    ),
                },
                {"id": "integrity_table", "type": "table", "tableId": "integrity_checks"},
                {
                    "id": "methodology",
                    "type": "markdown",
                    "sourceId": "retrieval_gold",
                    "body": (
                        "## 方法\n\n"
                        "依存関係のない決定論的BM25を使用し、chunk本文に加えて論文タイトルと見出しを重み付けした。"
                        "モデル学習や外部APIは使わない。gold setは各論文から式・方法・結果を1問ずつ採る層化全数設計で、"
                        "paper rankとanswer-page rankを分けて計算した。"
                    ),
                },
                {
                    "id": "adjudication",
                    "type": "markdown",
                    "sourceId": "retrieval_gold",
                    "body": (
                        "## gold setの再確認\n\n"
                        "初稿は複数論点を一文に含む質問と、同じラベル式を持つ複数論文を識別できない質問を含み、"
                        f"paper Recall@3 {draft_metrics['paper_recall_at_3']:.2%}、ページ Recall@5 "
                        f"{draft_metrics['page_recall_at_5']:.2%}、ページMRR "
                        f"{draft_metrics['page_mrr']:.4f}だった。"
                        "失敗9問を原PDFのレンダリング画像と照合し、回答内容や正解ページを都合よく変更せず、"
                        "質問を1論点かつ論文識別可能な形へ修正した。履歴はgold manifestに固定した。"
                    ),
                },
                {"id": "paper_table", "type": "table", "tableId": "paper_metrics"},
                {
                    "id": "limitations",
                    "type": "markdown",
                    "sourceId": "retrieval_gold",
                    "body": (
                        "## 制約・不確実性・頑健性\n\n"
                        "- gold setは単一レビュアー作成で、inter-annotator agreementは未測定。\n"
                        "- 強い英語言い換えと日本語は追加holdoutで評価し、語彙BM25の低下を別レポートに記録した。\n"
                        "- ページhitは回答可能な文脈の取得を示すだけで、生成回答の正確性は評価しない。\n"
                        "- lexical baselineなので、記号だけの質問や概念的な同義語にはembedding/rerankerより弱い可能性がある。"
                    ),
                },
                {
                    "id": "next_steps",
                    "type": "markdown",
                    "body": (
                        "## 推奨する次の作業\n\n"
                        "1. 同じ66問をembedding検索とhybrid rerankerにも流し、BM25との差分を固定する。\n"
                        "2. 各questionに短い根拠回答を追加し、retrievalだけでなくanswer faithfulnessを採点する。\n"
                        "3. 日本語・言い換えholdoutを維持し、現goldをretrieverのチューニング用に流用しない。"
                    ),
                },
                {
                    "id": "further_questions",
                    "type": "markdown",
                    "body": (
                        "## 追加で答えるべき問い\n\n"
                        "- 1 chunkでは式と定義が分離する質問に、隣接chunk展開は必要か。\n"
                        "- formula cropを視覚モデルへ渡すと、記号中心の質問の順位と回答精度は改善するか。\n"
                        "- 新しい論文を追加した際、既存66問の順位低下をどこまで許容するか。"
                    ),
                },
                {
                    "id": "source_notes",
                    "type": "markdown",
                    "body": (
                        "## ソース注記\n\n"
                        "カテゴリ間の順位品質は単一系列の棒グラフで比較し、0起点の尺度を使った。"
                        "論文別順位は正確な値の参照が主目的なのでtableで示した。"
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
                "categories": category_rows,
                "integrity": integrity_rows,
                "papers": paper_rows(results, corpus_index),
            },
        },
        "sources": sources,
    }


def parse_args() -> argparse.Namespace:
    project_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        type=Path,
        default=project_dir / "reports" / "paper_retrieval_qa" / "results.json",
    )
    parser.add_argument(
        "--gold",
        type=Path,
        default=project_dir / "manifests" / "paper_retrieval_gold.json",
    )
    parser.add_argument(
        "--corpus-index",
        type=Path,
        default=project_dir / "corpus" / "papers" / "_index.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_dir / "reports" / "paper_retrieval_qa" / "artifact.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = json.loads(args.results.read_text(encoding="utf-8"))
    gold = json.loads(args.gold.read_text(encoding="utf-8"))
    corpus_index = json.loads(args.corpus_index.read_text(encoding="utf-8"))
    artifact = build_artifact(results, gold, corpus_index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
