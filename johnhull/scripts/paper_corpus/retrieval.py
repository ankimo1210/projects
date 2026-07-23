"""Deterministic lexical retrieval and fixed-question evaluation."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .retrieval_gold import RETRIEVAL_QUERIES
from .semantic import _overall_status, read_jsonl

_ASCII_TOKEN_RE = re.compile(r"[a-z0-9]+")
_JAPANESE_RUN_RE = re.compile(r"[一-龯々ぁ-んァ-ヶー]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "under",
    "what",
    "which",
    "why",
    "with",
}


def tokenize(text: str) -> list[str]:
    """Tokenize English terms and overlapping Japanese character n-grams."""

    lowered = text.casefold()
    tokens = [value for value in _ASCII_TOKEN_RE.findall(lowered) if value not in _STOPWORDS]
    for run in _JAPANESE_RUN_RE.findall(lowered):
        if len(run) == 1:
            tokens.append(run)
            continue
        tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
        if len(run) >= 3:
            tokens.extend(run[index : index + 3] for index in range(len(run) - 2))
    return tokens


def rank_chunks(
    query: str,
    chunks: list[dict[str, Any]],
    *,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Rank chunks with a dependency-free BM25 implementation."""

    if not chunks:
        return []
    document_tokens = [tokenize(str(item["retrieval_text"])) for item in chunks]
    document_frequencies: Counter[str] = Counter()
    for values in document_tokens:
        document_frequencies.update(set(values))
    average_length = sum(len(values) for values in document_tokens) / len(document_tokens)
    query_counts = Counter(tokenize(query))
    scored: list[dict[str, Any]] = []
    k1 = 1.5
    b = 0.75
    total = len(chunks)
    for chunk, values in zip(chunks, document_tokens, strict=True):
        frequencies = Counter(values)
        score = 0.0
        length_norm = 1 - b + b * len(values) / max(average_length, 1.0)
        for token, query_frequency in query_counts.items():
            frequency = frequencies[token]
            if frequency == 0:
                continue
            document_frequency = document_frequencies[token]
            inverse_document_frequency = math.log(
                1 + (total - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            score += (
                inverse_document_frequency
                * (frequency * (k1 + 1))
                / (frequency + k1 * length_norm)
                * (1 + math.log(query_frequency))
            )
        scored.append({"chunk": chunk, "score": score})
    scored.sort(key=lambda item: (-float(item["score"]), str(item["chunk"]["chunk_id"])))
    return [
        {
            "rank": rank,
            "score": round(float(item["score"]), 12),
            "chunk_id": item["chunk"]["chunk_id"],
            "paper_id": item["chunk"]["paper_id"],
            "page_numbers": item["chunk"]["page_numbers"],
            "claim_ids": item["chunk"]["claim_ids"],
            "equation_ids": item["chunk"]["equation_ids"],
            "table_ids": item["chunk"]["table_ids"],
        }
        for rank, item in enumerate(scored[:top_k], start=1)
    ]


def _load_corpus(corpus_root: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    chunks: list[dict[str, Any]] = []
    equation_id_by_assertion: dict[str, str] = {}
    for paper_dir in sorted(path for path in corpus_root.iterdir() if path.is_dir()):
        chunks_path = paper_dir / "chunks.jsonl"
        if chunks_path.is_file():
            chunks.extend(read_jsonl(chunks_path))
        equations_path = paper_dir / "equations.jsonl"
        if equations_path.is_file():
            for equation in read_jsonl(equations_path):
                if equation.get("assertion_id"):
                    equation_id_by_assertion[str(equation["assertion_id"])] = str(
                        equation["equation_id"]
                    )
    if not chunks:
        raise ValueError("retrieval corpus has no semantic chunks")
    if len({item["chunk_id"] for item in chunks}) != len(chunks):
        raise ValueError("retrieval corpus has duplicate chunk ids")
    return chunks, equation_id_by_assertion


def evaluate_retrieval(
    corpus_root: Path,
    *,
    queries: Iterable[dict[str, Any]] = RETRIEVAL_QUERIES,
) -> dict[str, Any]:
    """Evaluate fixed questions against claim/equation/table evidence."""

    chunks, equation_id_by_assertion = _load_corpus(corpus_root)
    results: list[dict[str, Any]] = []
    missing_expected_equations: list[str] = []
    for query in queries:
        assertion_ids = tuple(str(value) for value in query["expected_equation_assertion_ids"])
        missing = sorted(set(assertion_ids) - equation_id_by_assertion.keys())
        if missing:
            missing_expected_equations.extend(
                f"{query['query_id']}:{assertion_id}" for assertion_id in missing
            )
        expected_equation_ids = {
            equation_id_by_assertion[value]
            for value in assertion_ids
            if value in equation_id_by_assertion
        }
        expected_claim_ids = set(str(value) for value in query["expected_claim_ids"])
        expected_table_ids = set(str(value) for value in query["expected_table_ids"])
        ranking = rank_chunks(str(query["question"]), chunks, top_k=int(query["top_k"]))
        hit_ranks = [
            int(item["rank"])
            for item in ranking
            if expected_claim_ids.intersection(item["claim_ids"])
            or expected_equation_ids.intersection(item["equation_ids"])
            or expected_table_ids.intersection(item["table_ids"])
        ]
        results.append(
            {
                **query,
                "expected_equation_ids": sorted(expected_equation_ids),
                "hit": bool(hit_ranks),
                "first_hit_rank": min(hit_ranks) if hit_ranks else None,
                "results": ranking,
            }
        )
    hits = sum(item["hit"] for item in results)
    p0_results = [item for item in results if item["p0"]]
    category_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"queries": 0, "hits": 0})
    for item in results:
        category = str(item["category"])
        category_counts[category]["queries"] += 1
        category_counts[category]["hits"] += int(item["hit"])
    return {
        "retrieval_metrics_version": "1.0.0",
        "retriever": "deterministic-bm25-en-ja-ngrams-v1",
        "top_k": 5,
        "chunk_count": len(chunks),
        "query_count": len(results),
        "hit_count": hits,
        "hit_at_5": hits / len(results),
        "p0_query_count": len(p0_results),
        "p0_hit_count": sum(item["hit"] for item in p0_results),
        "p0_hit_at_5": sum(item["hit"] for item in p0_results) / len(p0_results),
        "category_counts": dict(sorted(category_counts.items())),
        "missing_expected_equations": sorted(missing_expected_equations),
        "results": results,
    }


def validate_retrieval_metrics(value: dict[str, Any]) -> None:
    """Enforce Phase-nine retrieval gates."""

    required_categories = {"hull_white", "heston", "inflation_jgbi", "sabr", "rfr", "var_es"}
    if required_categories - set(value["category_counts"]):
        raise ValueError("fixed retrieval suite is missing a required finance category")
    if value["missing_expected_equations"]:
        raise ValueError("retrieval questions cite unresolved reviewed equations")
    if value["hit_at_5"] < 0.95:
        raise ValueError("retrieval Hit@5 is below ninety-five percent")
    if value["p0_hit_at_5"] != 1.0:
        raise ValueError("P0 retrieval Hit@5 must be one hundred percent")


def render_retrieval_metrics(value: dict[str, Any]) -> str:
    """Serialize retrieval metrics deterministically."""

    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def attach_retrieval_status(corpus_root: Path, metrics: dict[str, Any]) -> None:
    """Attach the passing corpus-level retrieval result to each paper quality record."""

    validate_retrieval_metrics(metrics)
    for paper_dir in sorted(path for path in corpus_root.iterdir() if path.is_dir()):
        quality_path = paper_dir / "quality.json"
        if not quality_path.is_file():
            continue
        quality = json.loads(quality_path.read_text(encoding="utf-8"))
        quality["retrieval_status"] = "pass"
        quality["retrieval_evaluation"] = {
            "retriever": metrics["retriever"],
            "hit_at_5": metrics["hit_at_5"],
            "p0_hit_at_5": metrics["p0_hit_at_5"],
            "query_count": metrics["query_count"],
        }
        quality["exceptions"] = [
            value
            for value in quality.get("exceptions", [])
            if value != "Corpus retrieval evaluation has not been attached."
        ]
        quality["overall_status"] = _overall_status(quality)
        quality_path.write_text(
            json.dumps(quality, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
