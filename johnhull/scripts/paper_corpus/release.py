"""Deterministic full-corpus release and reproducibility gates."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .baseline import DEFAULT_OUTPUT as DEFAULT_BASELINE
from .baseline import read_json
from .implementation_gold import (
    DEFAULT_IMPLEMENTATION_EVIDENCE_OUTPUT,
    DEFAULT_IMPLEMENTATION_METRICS_OUTPUT,
    build_implementation_evidence,
    render_json,
    validate_implementation_evidence,
)
from .retrieval import validate_retrieval_metrics
from .semantic import build_claim_metrics, validate_claim_metrics

REQUIRED_PAPER_FILES = (
    "metadata.json",
    "pages.jsonl",
    "blocks.jsonl",
    "equations.jsonl",
    "tables.jsonl",
    "figures.jsonl",
    "symbols.json",
    "paper.md",
    "claims.jsonl",
    "chunks.jsonl",
    "quality.json",
)
QUALITY_COMPONENTS = (
    "text_status",
    "layout_status",
    "formula_status",
    "table_status",
    "claims_status",
    "retrieval_status",
    "overall_status",
)
DETERMINISM_REPORT = "determinism_report.json"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _paper_result(
    paper_dir: Path,
    baseline_source: dict[str, Any],
) -> dict[str, Any]:
    paper_id = str(baseline_source["paper_id"])
    failures: list[str] = []
    missing_files = [name for name in REQUIRED_PAPER_FILES if not (paper_dir / name).is_file()]
    if missing_files:
        return {
            "paper_id": paper_id,
            "status": "fail",
            "failures": [f"missing artifact: {name}" for name in missing_files],
        }

    metadata = read_json(paper_dir / "metadata.json")
    quality = read_json(paper_dir / "quality.json")
    pages = _jsonl(paper_dir / "pages.jsonl")
    blocks = _jsonl(paper_dir / "blocks.jsonl")
    equations = _jsonl(paper_dir / "equations.jsonl")
    tables = _jsonl(paper_dir / "tables.jsonl")
    figures = _jsonl(paper_dir / "figures.jsonl")
    claims = _jsonl(paper_dir / "claims.jsonl")
    chunks = _jsonl(paper_dir / "chunks.jsonl")

    expected_pages = int(baseline_source["source_page_count"])
    expected_page_numbers = list(range(1, expected_pages + 1))
    page_numbers = [int(page["page_number"]) for page in pages]
    if page_numbers != expected_page_numbers:
        failures.append("page coverage is incomplete or out of order")
    if metadata.get("source_pdf_sha256") != baseline_source["source_sha256"]:
        failures.append("source PDF hash differs from the frozen baseline")
    if int(metadata.get("source_page_count", -1)) != expected_pages:
        failures.append("metadata source page count differs from the frozen baseline")
    if metadata.get("converted_page_numbers") != expected_page_numbers:
        failures.append("metadata converted page list is incomplete")
    for component in QUALITY_COMPONENTS:
        if quality.get(component) != "pass":
            failures.append(f"{component}={quality.get(component)!r}")
    if quality.get("exceptions"):
        failures.append("quality record contains unresolved exceptions")
    if quality.get("unresolved_low_text_pages"):
        failures.append("low-text pages remain unresolved")
    if quality.get("unresolved_layout_pages"):
        failures.append("reading-order pages remain unresolved")
    if quality.get("formula_failures"):
        failures.append("formula representation failures remain")
    if quality.get("table_failures"):
        failures.append("table structure failures remain")

    block_ids = {str(block["block_id"]) for block in blocks}
    equation_ids = {str(equation["equation_id"]) for equation in equations}
    table_ids = {str(table["table_id"]) for table in tables}
    claim_ids = {str(claim["claim_id"]) for claim in claims}
    for page in pages:
        if not set(map(str, page["block_ids"])).issubset(block_ids):
            failures.append(f"page {page['page_number']} cites a missing block")
    for equation in equations:
        if not (paper_dir / str(equation["source_asset"])).is_file():
            failures.append(f"missing formula source asset: {equation['equation_id']}")
    for table in tables:
        for key in ("source_asset", "json_path", "html_path", "csv_path"):
            if not (paper_dir / str(table[key])).is_file():
                failures.append(f"missing table asset: {table['table_id']}:{key}")
    for figure in figures:
        if not (paper_dir / str(figure["source_asset"])).is_file():
            failures.append(f"missing figure source asset: {figure['figure_id']}")
    for claim in claims:
        if not set(map(str, claim.get("evidence_block_ids", ()))).issubset(block_ids):
            failures.append(f"claim cites a missing block: {claim['claim_id']}")
    for chunk in chunks:
        if not set(map(str, chunk["block_ids"])).issubset(block_ids):
            failures.append(f"chunk cites a missing block: {chunk['chunk_id']}")
        if not set(map(str, chunk["equation_ids"])).issubset(equation_ids):
            failures.append(f"chunk cites a missing equation: {chunk['chunk_id']}")
        if not set(map(str, chunk["table_ids"])).issubset(table_ids):
            failures.append(f"chunk cites a missing table: {chunk['chunk_id']}")
        if not set(map(str, chunk["claim_ids"])).issubset(claim_ids):
            failures.append(f"chunk cites a missing claim: {chunk['chunk_id']}")

    counts = {
        "pages": len(pages),
        "blocks": len(blocks),
        "equations": len(equations),
        "verified_equations": sum(item["verification_status"] == "verified" for item in equations),
        "tables": len(tables),
        "figures": len(figures),
        "claims": len(claims),
        "verified_claims": sum(item["verification_status"] == "verified" for item in claims),
        "chunks": len(chunks),
    }
    return {
        "paper_id": paper_id,
        "source_pdf_sha256": metadata["source_pdf_sha256"],
        "status": "pass" if not failures else "fail",
        "failures": sorted(set(failures)),
        "counts": counts,
    }


def build_release_report(
    corpus_root: Path,
    baseline_path: Path = DEFAULT_BASELINE,
) -> dict[str, Any]:
    """Build an evidence-backed aggregate release report for one corpus root."""

    baseline = read_json(baseline_path)
    sources = sorted(baseline["sources"], key=lambda item: str(item["paper_id"]))
    expected_ids = {str(item["paper_id"]) for item in sources}
    actual_ids = {
        path.name
        for path in corpus_root.iterdir()
        if path.is_dir() and (path / "metadata.json").is_file()
    }
    global_failures: list[str] = []
    for paper_id in sorted(expected_ids - actual_ids):
        global_failures.append(f"missing paper output: {paper_id}")
    for paper_id in sorted(actual_ids - expected_ids):
        global_failures.append(f"unexpected paper output: {paper_id}")

    paper_results = [
        _paper_result(corpus_root / str(source["paper_id"]), source)
        for source in sources
        if str(source["paper_id"]) in actual_ids
    ]
    if any(item["status"] != "pass" for item in paper_results):
        global_failures.append("one or more paper quality gates failed")

    retrieval_path = corpus_root / "retrieval_evaluation.json"
    retrieval: dict[str, Any] | None = None
    if not retrieval_path.is_file():
        global_failures.append("retrieval evaluation is missing")
    else:
        retrieval = read_json(retrieval_path)
        try:
            validate_retrieval_metrics(retrieval)
        except ValueError as exc:
            global_failures.append(f"retrieval evaluation failed: {exc}")

    try:
        claim_metrics = build_claim_metrics(corpus_root)
        validate_claim_metrics(claim_metrics)
    except (FileNotFoundError, ValueError) as exc:
        claim_metrics = None
        global_failures.append(f"reviewed claim gate failed: {exc}")

    try:
        implementation_evidence, implementation_metrics = build_implementation_evidence(corpus_root)
        validate_implementation_evidence(implementation_evidence, implementation_metrics)
        implementation_current = (
            DEFAULT_IMPLEMENTATION_EVIDENCE_OUTPUT.is_file()
            and DEFAULT_IMPLEMENTATION_METRICS_OUTPUT.is_file()
            and DEFAULT_IMPLEMENTATION_EVIDENCE_OUTPUT.read_text(encoding="utf-8")
            == render_json(implementation_evidence)
            and DEFAULT_IMPLEMENTATION_METRICS_OUTPUT.read_text(encoding="utf-8")
            == render_json(implementation_metrics)
        )
        if not implementation_current:
            global_failures.append("P0 implementation evidence differs from tracked Gold")
    except (FileNotFoundError, ValueError) as exc:
        implementation_metrics = None
        implementation_current = False
        global_failures.append(f"P0 implementation evidence gate failed: {exc}")

    aggregate_counts: Counter[str] = Counter()
    for result in paper_results:
        aggregate_counts.update(result.get("counts", {}))
    status_counts = Counter(str(item["status"]) for item in paper_results)
    return {
        "schema_version": "2.0.0",
        "status": "pass" if not global_failures else "fail",
        "failures": sorted(set(global_failures)),
        "inventory": {
            "expected_papers": int(baseline["source_count"]),
            "actual_papers": len(actual_ids),
            "expected_pages": int(baseline["source_page_count"]),
            "actual_pages": aggregate_counts["pages"],
            "paper_status_counts": dict(sorted(status_counts.items())),
        },
        "aggregate_counts": dict(sorted(aggregate_counts.items())),
        "retrieval": retrieval,
        "reviewed_claim_metrics": claim_metrics,
        "implementation_metrics": implementation_metrics,
        "implementation_evidence_matches_tracked_gold": implementation_current,
        "papers": paper_results,
    }


def validate_release_report(report: dict[str, Any]) -> None:
    """Fail closed unless every full-corpus release condition passed."""

    if report.get("status") != "pass" or report.get("failures"):
        raise ValueError("full-corpus release report failed")
    inventory = report["inventory"]
    if inventory["actual_papers"] != inventory["expected_papers"]:
        raise ValueError("paper inventory is incomplete")
    if inventory["actual_pages"] != inventory["expected_pages"]:
        raise ValueError("page inventory is incomplete")
    if inventory["paper_status_counts"] != {"pass": inventory["expected_papers"]}:
        raise ValueError("not every paper passed")
    if not report["implementation_evidence_matches_tracked_gold"]:
        raise ValueError("implementation evidence is not current")


def release_index(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a compact deterministic paper index from a passing report."""

    return [
        {
            "paper_id": item["paper_id"],
            "source_pdf_sha256": item["source_pdf_sha256"],
            "status": item["status"],
            **item["counts"],
        }
        for item in report["papers"]
    ]


def render_release_markdown(report: dict[str, Any]) -> str:
    """Render a concise human-readable release summary."""

    inventory = report["inventory"]
    counts = report["aggregate_counts"]
    retrieval = report["retrieval"] or {}
    return (
        "# Paper corpus v2 quality report\n\n"
        f"- Status: **{report['status']}**\n"
        f"- Papers: {inventory['actual_papers']} / {inventory['expected_papers']}\n"
        f"- Pages: {inventory['actual_pages']} / {inventory['expected_pages']}\n"
        f"- Equations: {counts.get('equations', 0)} "
        f"({counts.get('verified_equations', 0)} reviewed)\n"
        f"- Tables: {counts.get('tables', 0)}\n"
        f"- Claims: {counts.get('claims', 0)} "
        f"({counts.get('verified_claims', 0)} reviewed)\n"
        f"- Semantic chunks: {counts.get('chunks', 0)}\n"
        f"- Retrieval Hit@5: {retrieval.get('hit_at_5', 0):.3f}\n"
        f"- P0 retrieval Hit@5: {retrieval.get('p0_hit_at_5', 0):.3f}\n"
        "- P0 implementation evidence: tracked Gold match\n"
    )


def write_release_artifacts(
    corpus_root: Path,
    baseline_path: Path = DEFAULT_BASELINE,
) -> dict[str, Any]:
    """Validate and write deterministic index and quality artifacts."""

    report = build_release_report(corpus_root, baseline_path)
    validate_release_report(report)
    (corpus_root / "index.json").write_text(_json(release_index(report)), encoding="utf-8")
    (corpus_root / "quality_report.json").write_text(_json(report), encoding="utf-8")
    (corpus_root / "quality_report.md").write_text(
        render_release_markdown(report), encoding="utf-8"
    )
    return report


def _file_hashes(root: Path, excluded: Iterable[str] = ()) -> dict[str, str]:
    excluded_set = set(excluded)
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.relative_to(root).as_posix() not in excluded_set
    }


def build_determinism_report(first_root: Path, second_root: Path) -> dict[str, Any]:
    """Compare two complete builds by relative file set and SHA-256."""

    first = _file_hashes(first_root, (DETERMINISM_REPORT,))
    second = _file_hashes(second_root, (DETERMINISM_REPORT,))
    first_names, second_names = set(first), set(second)
    changed = sorted(name for name in first_names & second_names if first[name] != second[name])
    missing_from_first = sorted(second_names - first_names)
    missing_from_second = sorted(first_names - second_names)
    status = "pass" if not (changed or missing_from_first or missing_from_second) else "fail"
    return {
        "status": status,
        "compared_file_count": len(first_names & second_names),
        "changed_files": changed,
        "missing_from_first": missing_from_first,
        "missing_from_second": missing_from_second,
    }


def write_determinism_report(first_root: Path, second_root: Path) -> dict[str, Any]:
    """Write the same comparison evidence into both build roots."""

    report = build_determinism_report(first_root, second_root)
    if report["status"] != "pass":
        raise ValueError("full-corpus builds are not byte-identical")
    rendered = _json(report)
    (first_root / DETERMINISM_REPORT).write_text(rendered, encoding="utf-8")
    (second_root / DETERMINISM_REPORT).write_text(rendered, encoding="utf-8")
    if build_determinism_report(first_root, second_root)["status"] != "pass":
        raise ValueError("determinism evidence changed build equality")
    return report
