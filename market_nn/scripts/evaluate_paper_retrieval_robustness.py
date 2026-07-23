#!/usr/bin/env python3
"""Evaluate paraphrased and Japanese questions against the paper corpus."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parents[1]
BASE_SCRIPT = Path(__file__).with_name("evaluate_paper_retrieval.py")
SPEC = importlib.util.spec_from_file_location("paper_retrieval_base", BASE_SCRIPT)
if not SPEC or not SPEC.loader:
    raise RuntimeError(f"Unable to load {BASE_SCRIPT}")
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)


def validate_variants(base_gold: dict[str, Any], variants: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    base_ids = {query["query_id"] for query in base_gold["queries"]}
    records = variants.get("variants", [])
    variant_ids = [record.get("source_query_id") for record in records]
    if len(variant_ids) != len(set(variant_ids)):
        errors.append("source_query_id values are not unique")
    if set(variant_ids) != base_ids:
        errors.append(
            "Variant coverage differs from canonical gold: "
            f"missing={sorted(base_ids - set(variant_ids))}, "
            f"extra={sorted(set(variant_ids) - base_ids)}"
        )
    expected_count = int(variants.get("design", {}).get("total_variants", 0))
    actual_count = sum(
        bool(record.get(variant_type))
        for record in records
        for variant_type in variants.get("design", {}).get("variant_types", [])
    )
    if actual_count != expected_count:
        errors.append(f"Expected {expected_count} variants, found {actual_count}")
    return errors


def variant_gold(
    base_gold: dict[str, Any], variants: dict[str, Any], variant_type: str
) -> dict[str, Any]:
    canonical = {query["query_id"]: query for query in base_gold["queries"]}
    queries: list[dict[str, Any]] = []
    for record in variants["variants"]:
        source_id = record["source_query_id"]
        query = dict(canonical[source_id])
        query["query_id"] = f"{source_id}--{variant_type}"
        query["source_query_id"] = source_id
        query["question"] = record[variant_type]
        queries.append(query)
    return {"queries": queries}


def threshold_failures(
    metrics: dict[str, Any], thresholds: dict[str, float], variant_type: str
) -> list[str]:
    failures: list[str] = []
    overall = metrics["overall"]
    for metric, minimum in thresholds.items():
        actual = overall.get(metric)
        if actual is None or actual < minimum:
            failures.append(
                f"{variant_type}.{metric}={actual if actual is not None else '<missing>'} "
                f"is below {minimum}"
            )
    return failures


def evaluate_robustness(
    project_dir: Path,
    base_gold_path: Path,
    variants_path: Path,
) -> dict[str, Any]:
    corpus_dir = project_dir / "corpus" / "papers"
    index, chunks = BASE.load_corpus(corpus_dir)
    base_gold = json.loads(base_gold_path.read_text(encoding="utf-8"))
    variants = json.loads(variants_path.read_text(encoding="utf-8"))
    variant_errors = validate_variants(base_gold, variants)
    corpus_audit = BASE.audit_corpus(project_dir, corpus_dir, index, chunks)
    base_gold_audit = BASE.validate_gold(project_dir, corpus_dir, index, base_gold)
    if variant_errors or corpus_audit["status"] != "pass" or base_gold_audit["status"] != "pass":
        raise ValueError(
            "; ".join(variant_errors + corpus_audit["errors"] + base_gold_audit["errors"])
        )

    retriever = BASE.BM25Retriever(chunks, **base_gold["retriever"]["parameters"])
    canonical_evaluations, canonical_metrics = BASE.evaluate(retriever, base_gold, result_limit=10)
    variant_results: dict[str, Any] = {}
    failures: list[str] = []
    for variant_type in variants["design"]["variant_types"]:
        evaluation_gold = variant_gold(base_gold, variants, variant_type)
        evaluations, metrics = BASE.evaluate(retriever, evaluation_gold, result_limit=10)
        searchable = sum(
            bool(BASE.tokenize(evaluation["question"], remove_stop_words=True))
            for evaluation in evaluations
        )
        variant_results[variant_type] = {
            "query_count": len(evaluations),
            "searchable_query_count": searchable,
            "metrics": metrics,
            "delta_vs_canonical": {
                metric: round(metrics["overall"][metric] - canonical_metrics["overall"][metric], 4)
                for metric in (
                    "paper_recall_at_3",
                    "page_recall_at_5",
                    "page_mrr",
                    "exact_evidence_recall_at_5",
                )
            },
            "evaluations": evaluations,
        }
        if variant_type in variants.get("thresholds", {}):
            failures.extend(
                threshold_failures(metrics, variants["thresholds"][variant_type], variant_type)
            )

    fingerprints = {
        "corpus_index_sha256": BASE.sha256_file(corpus_dir / "_index.json"),
        "base_gold_sha256": BASE.sha256_file(base_gold_path),
        "variants_sha256": BASE.sha256_file(variants_path),
    }
    return {
        "schema_version": 1,
        "run_id": BASE.sha256_bytes(BASE.canonical_json(fingerprints).encode())[:16],
        **fingerprints,
        "retriever": base_gold["retriever"],
        "status": "pass" if not failures else "fail",
        "thresholds": variants.get("thresholds", {}),
        "threshold_failures": failures,
        "corpus_audit": corpus_audit,
        "canonical": {
            "query_count": len(canonical_evaluations),
            "metrics": canonical_metrics,
        },
        "variants": variant_results,
        "limitations": variants["design"]["known_limitations"],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=PROJECT_DIR)
    parser.add_argument(
        "--base-gold", type=Path, default=PROJECT_DIR / "manifests/paper_retrieval_gold.json"
    )
    parser.add_argument(
        "--variants",
        type=Path,
        default=PROJECT_DIR / "manifests/paper_retrieval_robustness.json",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--allow-threshold-failures",
        action="store_true",
        help="Write diagnostic output but return success when robustness gates fail.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = evaluate_robustness(
        args.project_dir.resolve(), args.base_gold.resolve(), args.variants.resolve()
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    paraphrase = result["variants"]["strong_english_paraphrase"]["metrics"]["overall"]
    japanese = result["variants"]["japanese"]["metrics"]["overall"]
    print(
        f"Robustness QA: {result['status']} — paraphrase page R@5="
        f"{paraphrase['page_recall_at_5']:.1%}; Japanese page R@5="
        f"{japanese['page_recall_at_5']:.1%}",
        file=sys.stderr,
    )
    return int(result["status"] != "pass" and not args.allow_threshold_failures)


if __name__ == "__main__":
    raise SystemExit(main())
