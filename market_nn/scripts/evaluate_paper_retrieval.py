#!/usr/bin/env python3
"""Evaluate deterministic lexical retrieval over the converted paper corpus.

The evaluator deliberately uses no learned model or external service.  It is a
transparent baseline for detecting broken chunks, weak provenance, and obvious
retrieval regressions before a semantic/embedding retriever is introduced.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*")
FORMULA_ID_RE = re.compile(r'id="([^"]+:formula:\d{4})"')
STOP_WORDS = {
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
    "paper",
    "the",
    "their",
    "this",
    "to",
    "use",
    "uses",
    "what",
    "which",
    "with",
}


def canonical_json(value: Any) -> str:
    """Return stable JSON used by checksums and committed output."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_token(token: str) -> str:
    """Apply small, deterministic inflection normalization.

    This is intentionally conservative: it covers common English plurals and
    gerunds without pretending to be a language-specific stemmer.
    """

    if len(token) > 5 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 6 and token.endswith("ing"):
        base = token[:-3]
        if len(base) > 3 and base[-1:] == base[-2:-1]:
            base = base[:-1]
        return base
    if len(token) > 5 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 4 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str, *, remove_stop_words: bool = False) -> list[str]:
    tokens = [normalize_token(token) for token in TOKEN_RE.findall(text.lower())]
    if remove_stop_words:
        return [token for token in tokens if token not in STOP_WORDS and len(token) > 1]
    return tokens


@dataclass(frozen=True)
class SearchResult:
    rank: int
    score: float
    chunk: dict[str, Any]


class BM25Retriever:
    """A field-aware BM25 retriever with a small exact-phrase bonus."""

    def __init__(
        self,
        chunks: list[dict[str, Any]],
        *,
        k1: float = 1.2,
        b: float = 0.75,
        title_weight: int = 2,
        heading_weight: int = 2,
    ) -> None:
        if not chunks:
            raise ValueError("The corpus contains no chunks")
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.document_tokens: list[list[str]] = []
        self.term_frequencies: list[Counter[str]] = []
        document_frequency: Counter[str] = Counter()

        for chunk in chunks:
            text_tokens = tokenize(str(chunk.get("text", "")))
            title_tokens = tokenize(str(chunk.get("title", ""))) * title_weight
            heading_tokens: list[str] = []
            for heading in chunk.get("headings") or []:
                heading_tokens.extend(tokenize(str(heading)) * heading_weight)
            tokens = text_tokens + title_tokens + heading_tokens
            frequencies = Counter(tokens)
            self.document_tokens.append(tokens)
            self.term_frequencies.append(frequencies)
            document_frequency.update(frequencies.keys())

        self.average_length = sum(map(len, self.document_tokens)) / len(self.document_tokens)
        count = len(self.chunks)
        self.idf = {
            token: math.log(1 + (count - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequency.items()
        }

    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        query_tokens = tokenize(query, remove_stop_words=True)
        if not query_tokens:
            raise ValueError(f"Query has no searchable tokens: {query!r}")
        query_frequency = Counter(query_tokens)
        query_phrase = " ".join(query_tokens)
        scored: list[tuple[float, str, dict[str, Any]]] = []

        for chunk, tokens, frequencies in zip(
            self.chunks, self.document_tokens, self.term_frequencies, strict=True
        ):
            length_norm = self.k1 * (1 - self.b + self.b * len(tokens) / self.average_length)
            score = 0.0
            for token, query_count in query_frequency.items():
                frequency = frequencies.get(token, 0)
                if not frequency:
                    continue
                idf = self.idf[token]
                score += (
                    idf
                    * ((frequency * (self.k1 + 1)) / (frequency + length_norm))
                    * (1 + math.log(query_count))
                )

            normalized_document = " ".join(tokens)
            if len(query_tokens) >= 2 and query_phrase in normalized_document:
                score += 0.35 * sum(self.idf.get(token, 0.0) for token in query_tokens)
            if score > 0:
                scored.append((score, str(chunk["chunk_id"]), chunk))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [
            SearchResult(rank=rank, score=score, chunk=chunk)
            for rank, (score, _, chunk) in enumerate(scored[:limit], start=1)
        ]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at {path}:{line_number}: {error}") from error
    return records


def load_corpus(corpus_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    index_path = corpus_dir / "_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    chunks: list[dict[str, Any]] = []
    for paper in index["papers"]:
        paper_id = paper["paper_id"]
        chunks.extend(read_jsonl(corpus_dir / paper_id / "chunks.jsonl"))
    return index, chunks


def audit_corpus(
    project_dir: Path, corpus_dir: Path, index: dict[str, Any], chunks: list[dict[str, Any]]
) -> dict[str, Any]:
    """Check the minimum corpus invariants needed for trustworthy retrieval QA."""

    errors: list[str] = []
    warnings: list[str] = []
    paper_ids = [paper["paper_id"] for paper in index["papers"]]
    chunk_ids = [str(chunk.get("chunk_id")) for chunk in chunks]
    if index.get("paper_count") != len(paper_ids):
        errors.append("_index.json paper_count does not match papers[]")
    if len(paper_ids) != len(set(paper_ids)):
        errors.append("paper_id values are not unique")
    if len(chunk_ids) != len(set(chunk_ids)):
        errors.append("chunk_id values are not unique")

    paper_chunk_counts = Counter(str(chunk.get("paper_id")) for chunk in chunks)
    source_hashes: dict[str, str] = {}
    for paper in index["papers"]:
        paper_id = paper["paper_id"]
        expected_chunks = paper["document"]["chunks"]
        if paper_chunk_counts.get(paper_id, 0) != expected_chunks:
            errors.append(
                f"{paper_id}: index declares {expected_chunks} chunks, "
                f"found {paper_chunk_counts.get(paper_id, 0)}"
            )
        source_path = project_dir / paper["source"]["path"]
        if not source_path.is_file():
            errors.append(f"{paper_id}: source PDF is missing: {paper['source']['path']}")
            continue
        actual_hash = sha256_file(source_path)
        source_hashes[paper_id] = actual_hash
        if actual_hash != paper["source"]["sha256"]:
            errors.append(f"{paper_id}: source PDF SHA-256 differs from the index")

    required_fields = {
        "chunk_id",
        "paper_id",
        "title",
        "source_pdf",
        "source_sha256",
        "text",
        "chunk_index",
        "page_numbers",
    }
    empty_text = 0
    missing_pages = 0
    formula_markers = 0
    for chunk in chunks:
        missing = required_fields.difference(chunk)
        if missing:
            errors.append(f"{chunk.get('chunk_id', '<unknown>')}: missing {sorted(missing)}")
        if not str(chunk.get("text", "")).strip():
            empty_text += 1
        pages = chunk.get("page_numbers")
        if not pages or not all(isinstance(page, int) and page >= 1 for page in pages):
            missing_pages += 1
        formula_markers += len(FORMULA_ID_RE.findall(str(chunk.get("text", ""))))
        paper_id = str(chunk.get("paper_id"))
        if paper_id in source_hashes and chunk.get("source_sha256") != source_hashes[paper_id]:
            errors.append(f"{chunk.get('chunk_id')}: source SHA-256 is inconsistent")

    if empty_text:
        errors.append(f"{empty_text} chunks have empty text")
    if missing_pages:
        errors.append(f"{missing_pages} chunks lack valid page provenance")

    expected_formula_total = sum(
        paper.get("formula_quality", {}).get("total", 0) for paper in index["papers"]
    )
    if formula_markers < expected_formula_total:
        warnings.append(
            f"Only {formula_markers}/{expected_formula_total} formula references occur in chunks; "
            "some formulas may sit across a chunk boundary"
        )

    return {
        "status": "pass" if not errors else "fail",
        "paper_count": len(paper_ids),
        "chunk_count": len(chunks),
        "unique_chunk_count": len(set(chunk_ids)),
        "empty_text_chunks": empty_text,
        "chunks_without_page_provenance": missing_pages,
        "formula_markers_in_chunks": formula_markers,
        "formula_records_in_index": expected_formula_total,
        "errors": errors,
        "warnings": warnings,
    }


def first_rank(
    results: list[SearchResult], paper_id: str, expected_pages: set[int] | None = None
) -> int | None:
    for result in results:
        chunk = result.chunk
        if chunk["paper_id"] != paper_id:
            continue
        if expected_pages is None or expected_pages.intersection(chunk["page_numbers"]):
            return result.rank
    return None


def validate_gold(
    project_dir: Path, corpus_dir: Path, index: dict[str, Any], gold: dict[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    queries = gold.get("queries", [])
    query_ids = [query.get("query_id") for query in queries]
    corpus_paper_ids = {paper["paper_id"] for paper in index["papers"]}
    formula_records: dict[str, dict[str, Any]] = {}
    for paper_id in corpus_paper_ids:
        for formula in read_jsonl(corpus_dir / paper_id / "formulas.jsonl"):
            formula_records[formula["formula_id"]] = formula

    if len(query_ids) != len(set(query_ids)):
        errors.append("query_id values are not unique")
    for query in queries:
        query_id = query.get("query_id", "<missing>")
        paper_id = query.get("paper_id")
        if paper_id not in corpus_paper_ids:
            errors.append(f"{query_id}: unknown paper_id {paper_id!r}")
        if query.get("category") not in {"formula", "method", "result"}:
            errors.append(f"{query_id}: invalid category")
        pages = query.get("expected_pages")
        if not pages or not all(isinstance(page, int) and page >= 1 for page in pages):
            errors.append(f"{query_id}: expected_pages must contain positive integers")
        if not tokenize(str(query.get("question", "")), remove_stop_words=True):
            errors.append(f"{query_id}: question has no searchable content")
        for formula_id in query.get("expected_formula_ids", []):
            formula = formula_records.get(formula_id)
            if formula is None:
                errors.append(f"{query_id}: unknown expected formula {formula_id}")
            elif formula["paper_id"] != paper_id or formula["page"] not in set(pages or []):
                errors.append(f"{query_id}: formula provenance conflicts with query target")

    per_paper = Counter(str(query.get("paper_id")) for query in queries)
    per_category = Counter(str(query.get("category")) for query in queries)
    expected_per_paper = gold.get("design", {}).get("queries_per_paper", 3)
    for paper_id in corpus_paper_ids:
        if per_paper[paper_id] != expected_per_paper:
            errors.append(
                f"{paper_id}: expected {expected_per_paper} queries, found {per_paper[paper_id]}"
            )

    return {
        "status": "pass" if not errors else "fail",
        "query_count": len(queries),
        "query_counts_by_category": dict(sorted(per_category.items())),
        "paper_count": len(per_paper),
        "errors": errors,
    }


def hit_at(rank: int | None, cutoff: int) -> int:
    return int(rank is not None and rank <= cutoff)


def aggregate_metrics(records: list[dict[str, Any]]) -> dict[str, float | int]:
    if not records:
        return {"query_count": 0}
    count = len(records)
    metrics: dict[str, float | int] = {"query_count": count}
    for target in ("paper", "page"):
        for cutoff in (1, 3, 5):
            metrics[f"{target}_recall_at_{cutoff}"] = round(
                sum(hit_at(record[f"{target}_rank"], cutoff) for record in records) / count,
                4,
            )
        metrics[f"{target}_mrr"] = round(
            sum(
                1 / record[f"{target}_rank"] if record[f"{target}_rank"] else 0
                for record in records
            )
            / count,
            4,
        )
    return metrics


def evaluate(
    retriever: BM25Retriever, gold: dict[str, Any], *, result_limit: int = 10
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evaluations: list[dict[str, Any]] = []
    for query in gold["queries"]:
        results = retriever.search(query["question"], limit=result_limit)
        expected_pages = set(query["expected_pages"])
        paper_rank = first_rank(results, query["paper_id"])
        page_rank = first_rank(results, query["paper_id"], expected_pages)
        evaluations.append(
            {
                "query_id": query["query_id"],
                "paper_id": query["paper_id"],
                "category": query["category"],
                "question": query["question"],
                "expected_pages": query["expected_pages"],
                "expected_formula_ids": query.get("expected_formula_ids", []),
                "paper_rank": paper_rank,
                "page_rank": page_rank,
                "top_results": [
                    {
                        "rank": result.rank,
                        "score": round(result.score, 6),
                        "chunk_id": result.chunk["chunk_id"],
                        "paper_id": result.chunk["paper_id"],
                        "page_numbers": result.chunk["page_numbers"],
                        "headings": result.chunk.get("headings") or [],
                    }
                    for result in results
                ],
            }
        )

    grouped_by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for evaluation in evaluations:
        grouped_by_category[evaluation["category"]].append(evaluation)
        grouped_by_paper[evaluation["paper_id"]].append(evaluation)
    metrics = {
        "overall": aggregate_metrics(evaluations),
        "by_category": {
            category: aggregate_metrics(records)
            for category, records in sorted(grouped_by_category.items())
        },
        "by_paper": {
            paper_id: aggregate_metrics(records)
            for paper_id, records in sorted(grouped_by_paper.items())
        },
    }
    return evaluations, metrics


def check_thresholds(metrics: dict[str, Any], thresholds: dict[str, float]) -> list[str]:
    failures: list[str] = []
    overall = metrics["overall"]
    for metric, minimum in thresholds.items():
        actual = overall.get(metric)
        if actual is None:
            failures.append(f"Unknown threshold metric: {metric}")
        elif actual < minimum:
            failures.append(f"{metric}={actual:.4f} is below {minimum:.4f}")
    return failures


def build_output(
    *,
    corpus_audit: dict[str, Any],
    gold_audit: dict[str, Any],
    gold: dict[str, Any],
    gold_path: Path,
    index_path: Path,
    evaluations: list[dict[str, Any]],
    metrics: dict[str, Any],
    threshold_failures: list[str],
) -> dict[str, Any]:
    fingerprint_payload = {
        "corpus_index_sha256": sha256_file(index_path),
        "gold_sha256": sha256_file(gold_path),
        "retriever": gold["retriever"],
    }
    return {
        "schema_version": 1,
        "run_id": sha256_bytes(canonical_json(fingerprint_payload).encode())[:16],
        "corpus_index_sha256": fingerprint_payload["corpus_index_sha256"],
        "gold_sha256": fingerprint_payload["gold_sha256"],
        "retriever": gold["retriever"],
        "corpus_audit": corpus_audit,
        "gold_audit": gold_audit,
        "metrics": metrics,
        "thresholds": gold["thresholds"],
        "threshold_status": "pass" if not threshold_failures else "fail",
        "threshold_failures": threshold_failures,
        "evaluations": evaluations,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    project_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-dir", type=Path, default=project_dir, help="market_nn project directory"
    )
    parser.add_argument("--corpus-dir", type=Path, default=None, help="paper corpus directory")
    parser.add_argument(
        "--gold",
        type=Path,
        default=project_dir / "manifests" / "paper_retrieval_gold.json",
    )
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--top-results", type=int, default=10)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_dir = args.project_dir.resolve()
    corpus_dir = (args.corpus_dir or project_dir / "corpus" / "papers").resolve()
    gold_path = args.gold.resolve()
    index, chunks = load_corpus(corpus_dir)
    gold = json.loads(gold_path.read_text(encoding="utf-8"))

    corpus_audit = audit_corpus(project_dir, corpus_dir, index, chunks)
    gold_audit = validate_gold(project_dir, corpus_dir, index, gold)
    if corpus_audit["status"] != "pass" or gold_audit["status"] != "pass":
        for error in corpus_audit["errors"] + gold_audit["errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    retriever = BM25Retriever(chunks, **gold["retriever"]["parameters"])
    evaluations, metrics = evaluate(retriever, gold, result_limit=args.top_results)
    threshold_failures = check_thresholds(metrics, gold["thresholds"])
    output = build_output(
        corpus_audit=corpus_audit,
        gold_audit=gold_audit,
        gold=gold,
        gold_path=gold_path,
        index_path=corpus_dir / "_index.json",
        evaluations=evaluations,
        metrics=metrics,
        threshold_failures=threshold_failures,
    )
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    overall = metrics["overall"]
    print(
        f"Retrieval QA: {output['threshold_status']} — "
        f"page R@5={overall['page_recall_at_5']:.1%}, "
        f"page MRR={overall['page_mrr']:.3f}",
        file=sys.stderr,
    )
    for failure in threshold_failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    return int(bool(threshold_failures))


if __name__ == "__main__":
    raise SystemExit(main())
