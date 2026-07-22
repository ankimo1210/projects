from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parents[1]
SCRIPT_PATH = PROJECT_DIR / "scripts" / "evaluate_paper_retrieval.py"
SPEC = importlib.util.spec_from_file_location("evaluate_paper_retrieval", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

REPORT_SCRIPT_PATH = PROJECT_DIR / "scripts" / "build_paper_retrieval_report.py"
REPORT_SPEC = importlib.util.spec_from_file_location(
    "build_paper_retrieval_report", REPORT_SCRIPT_PATH
)
assert REPORT_SPEC and REPORT_SPEC.loader
REPORT_MODULE = importlib.util.module_from_spec(REPORT_SPEC)
sys.modules[REPORT_SPEC.name] = REPORT_MODULE
REPORT_SPEC.loader.exec_module(REPORT_MODULE)


def test_paper_retrieval_gold_set_and_corpus_pass_quality_gates() -> None:
    corpus_dir = PROJECT_DIR / "corpus" / "papers"
    gold = json.loads(
        (PROJECT_DIR / "manifests" / "paper_retrieval_gold.json").read_text(encoding="utf-8")
    )
    index, chunks = MODULE.load_corpus(corpus_dir)

    corpus_audit = MODULE.audit_corpus(PROJECT_DIR, corpus_dir, index, chunks)
    gold_audit = MODULE.validate_gold(PROJECT_DIR, corpus_dir, index, gold)
    retriever = MODULE.BM25Retriever(chunks, **gold["retriever"]["parameters"])
    evaluations, metrics = MODULE.evaluate(retriever, gold, result_limit=10)

    assert corpus_audit["status"] == "pass"
    assert corpus_audit["paper_count"] == 22
    assert corpus_audit["chunk_count"] == 1318
    assert corpus_audit["formula_markers_in_chunks"] == 424
    assert gold_audit == {
        "status": "pass",
        "query_count": 66,
        "query_counts_by_category": {"formula": 22, "method": 22, "result": 22},
        "paper_count": 22,
        "errors": [],
    }
    assert len(evaluations) == 66
    assert MODULE.check_thresholds(metrics, gold["thresholds"]) == []


def test_bm25_tie_breaking_is_deterministic() -> None:
    chunks = [
        {
            "chunk_id": "paper-b:0001",
            "paper_id": "paper-b",
            "title": "Same title",
            "headings": ["Same heading"],
            "text": "same body",
            "page_numbers": [1],
        },
        {
            "chunk_id": "paper-a:0001",
            "paper_id": "paper-a",
            "title": "Same title",
            "headings": ["Same heading"],
            "text": "same body",
            "page_numbers": [1],
        },
    ]

    results = MODULE.BM25Retriever(chunks).search("same body", limit=2)

    assert [result.chunk["chunk_id"] for result in results] == [
        "paper-a:0001",
        "paper-b:0001",
    ]


def test_committed_retrieval_report_artifact_is_current() -> None:
    report_dir = PROJECT_DIR / "reports" / "paper_retrieval_qa"
    results = json.loads((report_dir / "results.json").read_text(encoding="utf-8"))
    gold = json.loads(
        (PROJECT_DIR / "manifests" / "paper_retrieval_gold.json").read_text(encoding="utf-8")
    )
    corpus_index = json.loads(
        (PROJECT_DIR / "corpus" / "papers" / "_index.json").read_text(encoding="utf-8")
    )
    committed_artifact = json.loads((report_dir / "artifact.json").read_text(encoding="utf-8"))

    assert REPORT_MODULE.build_artifact(results, gold, corpus_index) == committed_artifact
