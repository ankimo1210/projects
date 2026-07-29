"""Evidence-backed claims and section-aware semantic chunks."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .claim_gold import GOLD_CLAIM_SPECS
from .schema import NUMBER_RE, P0_PAPER_IDS, ClaimRecord, SemanticChunkRecord


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _jsonl(values: Iterable[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for value in values
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read deterministic JSONL artifacts."""

    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _page_from_record_id(record_id: str) -> int:
    match = re.search(r":p(\d{4}):", record_id)
    if match is None:
        raise ValueError(f"record id has no page: {record_id}")
    return int(match.group(1))


def _claim_from_spec(
    spec: dict[str, Any],
    *,
    source_pdf_sha256: str,
    block_by_id: dict[str, dict[str, Any]],
    equation_by_assertion: dict[str, dict[str, Any]],
    table_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    evidence_ids = tuple(str(value) for value in spec["evidence_block_ids"])
    missing_blocks = sorted(set(evidence_ids) - block_by_id.keys())
    if missing_blocks:
        raise ValueError(f"claim evidence blocks are missing: {missing_blocks}")
    equation_assertions = tuple(str(value) for value in spec["equation_assertion_ids"])
    missing_assertions = sorted(set(equation_assertions) - equation_by_assertion.keys())
    if missing_assertions:
        raise ValueError(f"claim equation assertions are missing: {missing_assertions}")
    equations = tuple(equation_by_assertion[value] for value in equation_assertions)
    if any(item["verification_status"] != "verified" for item in equations):
        raise ValueError("reviewed claims may cite only verified equation assertions")
    table_ids = tuple(str(value) for value in spec["table_ids"])
    missing_tables = sorted(set(table_ids) - table_by_id.keys())
    if missing_tables:
        raise ValueError(f"claim tables are missing: {missing_tables}")
    if any(table_by_id[value]["verification_status"] != "verified" for value in table_ids):
        raise ValueError("reviewed claims may cite only verified tables")
    manual_excerpts = tuple(str(value) for value in spec["manual_source_excerpts"])
    if manual_excerpts and len(manual_excerpts) != len(evidence_ids):
        raise ValueError("manual source excerpts must align with evidence blocks")
    source_texts = tuple(str(block_by_id[value]["normalized_text"]) for value in evidence_ids)
    excerpts = manual_excerpts or source_texts
    record = ClaimRecord(
        claim_id=str(spec["claim_id"]),
        paper_id=str(spec["paper_id"]),
        claim_type=str(spec["claim_type"]),  # type: ignore[arg-type]
        statement=str(spec["statement"]),
        page_numbers=tuple(sorted({_page_from_record_id(value) for value in evidence_ids})),
        evidence_block_ids=evidence_ids,
        source_pdf_sha256=source_pdf_sha256,
        equation_ids=tuple(str(item["equation_id"]) for item in equations),
        table_ids=table_ids,
        verification_status=str(spec["verification_status"]),  # type: ignore[arg-type]
        reviewer=str(spec["reviewer"]),
        source_review_status=str(spec["source_review_status"]),
        source_excerpts=excerpts,
        evidence_text_sha256=tuple(
            hashlib.sha256(value.encode("utf-8")).hexdigest() for value in source_texts
        ),
        finance_tags=tuple(str(value) for value in spec["finance_tags"]),
    ).to_dict()
    record["claim_origin"] = "manual_gold_spec"
    return record


def _auto_claim_type(text: str, ordinal: int) -> str:
    lowered = text.casefold()
    if any(token in lowered for token in ("we propose", "we develop", "this paper")):
        return "research_question"
    if any(token in lowered for token in ("we assume", "assumption", "suppose")):
        return "model_assumption"
    if any(token in lowered for token in ("method", "algorithm", "simulation", "estimate")):
        return "numerical_method"
    if any(token in lowered for token in ("however", "limitation", "drawback", "cannot")):
        return "limitation"
    return ("empirical_result", "implementation_warning", "calibration_input")[ordinal % 3]


def _auto_claims(
    *,
    paper_id: str,
    source_pdf_sha256: str,
    blocks: list[dict[str, Any]],
    limit: int = 5,
) -> list[dict[str, Any]]:
    candidates = [
        block
        for block in blocks
        if block["block_type"] == "paragraph"
        and 120 <= len(str(block["normalized_text"])) <= 1400
        and not NUMBER_RE.search(str(block["normalized_text"]))
    ]
    claims: list[dict[str, Any]] = []
    seen: set[str] = set()
    for block in candidates:
        text = str(block["normalized_text"]).strip()
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        ordinal = len(claims) + 1
        claim = ClaimRecord(
            claim_id=f"{paper_id}:claim:auto-{ordinal:04d}",
            paper_id=paper_id,
            claim_type=_auto_claim_type(text, ordinal),  # type: ignore[arg-type]
            statement=text,
            page_numbers=(int(block["page_number"]),),
            evidence_block_ids=(str(block["block_id"]),),
            source_pdf_sha256=source_pdf_sha256,
            verification_status="auto",
            source_review_status="not_reviewed",
            source_excerpts=(text,),
            evidence_text_sha256=(digest,),
            finance_tags=(),
        ).to_dict()
        claim["claim_origin"] = "deterministic_extractive"
        claims.append(claim)
        if len(claims) == limit:
            break
    return claims


def build_claims(
    paper_dir: Path,
    *,
    specs: Iterable[dict[str, Any]] = GOLD_CLAIM_SPECS,
) -> list[dict[str, Any]]:
    """Resolve reviewed specs or deterministic extractive claims for one paper."""

    metadata = json.loads((paper_dir / "metadata.json").read_text(encoding="utf-8"))
    paper_id = str(metadata["paper_id"])
    source_pdf_sha256 = str(metadata["source_pdf_sha256"])
    blocks = read_jsonl(paper_dir / "blocks.jsonl")
    equations = read_jsonl(paper_dir / "equations.jsonl")
    tables = read_jsonl(paper_dir / "tables.jsonl")
    block_by_id = {str(item["block_id"]): item for item in blocks}
    equation_by_assertion = {
        str(item["assertion_id"]): item for item in equations if item.get("assertion_id")
    }
    table_by_id = {str(item["table_id"]): item for item in tables}
    selected_specs = [item for item in specs if item["paper_id"] == paper_id]
    if selected_specs:
        claims = [
            _claim_from_spec(
                item,
                source_pdf_sha256=source_pdf_sha256,
                block_by_id=block_by_id,
                equation_by_assertion=equation_by_assertion,
                table_by_id=table_by_id,
            )
            for item in selected_specs
        ]
    else:
        claims = _auto_claims(
            paper_id=paper_id,
            source_pdf_sha256=source_pdf_sha256,
            blocks=blocks,
        )
    if len({item["claim_id"] for item in claims}) != len(claims):
        raise ValueError(f"duplicate claim ids for {paper_id}")
    return claims


def _record_block_id(record: dict[str, Any], blocks: list[dict[str, Any]]) -> str | None:
    if record.get("source_block_id"):
        return str(record["source_block_id"])
    normalized_bbox = record.get("source_bbox_normalized")
    if normalized_bbox is None:
        return None
    page_number = int(record["page_number"])
    for block in blocks:
        if (
            int(block["page_number"]) == page_number
            and block.get("source_bbox_normalized") == normalized_bbox
        ):
            return str(block["block_id"])
    return None


def build_semantic_chunks(
    paper_dir: Path,
    claims: list[dict[str, Any]],
    *,
    max_chars: int = 1800,
) -> list[dict[str, Any]]:
    """Chunk ordered source blocks at headings and page discontinuities."""

    metadata = json.loads((paper_dir / "metadata.json").read_text(encoding="utf-8"))
    paper_id = str(metadata["paper_id"])
    source_pdf_sha256 = str(metadata["source_pdf_sha256"])
    blocks = read_jsonl(paper_dir / "blocks.jsonl")
    equations = read_jsonl(paper_dir / "equations.jsonl")
    tables = read_jsonl(paper_dir / "tables.jsonl")
    equations_by_block: dict[str, list[str]] = defaultdict(list)
    tables_by_block: dict[str, list[str]] = defaultdict(list)
    for equation in equations:
        block_id = _record_block_id(equation, blocks)
        if block_id:
            equations_by_block[block_id].append(str(equation["equation_id"]))
    for table in tables:
        block_id = _record_block_id(table, blocks)
        if block_id:
            tables_by_block[block_id].append(str(table["table_id"]))
    claims_by_block: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        for block_id in claim["evidence_block_ids"]:
            claims_by_block[str(block_id)].append(claim)
    table_caption_by_block = {
        block_id: str(
            next(item for item in tables if item["table_id"] == table_ids[0]).get("caption") or ""
        )
        for block_id, table_ids in tables_by_block.items()
    }

    chunks_raw: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    section_title: str | None = None
    current_section: str | None = None
    last_page: int | None = None

    def flush() -> None:
        nonlocal current, current_chars, current_section
        if current:
            chunks_raw.append({"blocks": current, "section_title": current_section})
        current = []
        current_chars = 0
        current_section = section_title

    for block in blocks:
        block_type = str(block["block_type"])
        if block_type in {"header", "footer"}:
            continue
        text = str(block["normalized_text"]).strip()
        if block_type == "table":
            text = f"[Table] {table_caption_by_block.get(str(block['block_id']), text)}".strip()
        elif block_type == "figure" and not text:
            text = "[Figure source region]"
        if not text:
            continue
        page_number = int(block["page_number"])
        if block_type in {"title", "heading"}:
            flush()
            section_title = text
            current_section = section_title
        discontinuity = last_page is not None and page_number > last_page + 1
        if current and (discontinuity or current_chars + len(text) + 1 > max_chars):
            flush()
        if not current:
            current_section = section_title
        current.append({**block, "semantic_text": text})
        current_chars += len(text) + 1
        last_page = page_number
    flush()

    chunks: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(chunks_raw, start=1):
        chunk_blocks = raw["blocks"]
        block_ids = tuple(str(item["block_id"]) for item in chunk_blocks)
        page_numbers = tuple(sorted({int(item["page_number"]) for item in chunk_blocks}))
        related_claims = {
            str(claim["claim_id"]): claim
            for block_id in block_ids
            for claim in claims_by_block.get(block_id, [])
        }
        equation_ids = tuple(
            sorted({value for block_id in block_ids for value in equations_by_block[block_id]})
        )
        table_ids = tuple(
            sorted({value for block_id in block_ids for value in tables_by_block[block_id]})
        )
        text = "\n".join(str(item["semantic_text"]) for item in chunk_blocks)
        retrieval_parts = [str(raw["section_title"] or ""), text]
        for claim in related_claims.values():
            retrieval_parts.append(str(claim["statement"]))
            retrieval_parts.extend(str(value) for value in claim.get("finance_tags", []))
        retrieval_text = "\n".join(value for value in retrieval_parts if value.strip())
        content_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        chunk_id = f"{paper_id}:p{page_numbers[0]:04d}:chunk:{ordinal:04d}"
        chunks.append(
            SemanticChunkRecord(
                chunk_id=chunk_id,
                paper_id=paper_id,
                page_numbers=page_numbers,
                section_title=str(raw["section_title"]) if raw["section_title"] else None,
                block_ids=block_ids,
                equation_ids=equation_ids,
                table_ids=table_ids,
                claim_ids=tuple(sorted(related_claims)),
                text=text,
                retrieval_text=retrieval_text,
                source_pdf_sha256=source_pdf_sha256,
                content_sha256=content_sha256,
            ).to_dict()
        )
    if not chunks:
        raise ValueError(f"no semantic chunks for {paper_id}")
    return chunks


_STATUS_RANK = {"pass": 0, "auto": 0, "review": 1, "missing": 2, "missing_source": 2, "fail": 3}


def _overall_status(quality: dict[str, Any]) -> str:
    component_names = (
        "text_status",
        "layout_status",
        "formula_status",
        "table_status",
        "claims_status",
        "retrieval_status",
    )
    values = [str(quality[name]) for name in component_names]
    worst = max(values, key=lambda value: _STATUS_RANK.get(value, 3))
    return "pass" if _STATUS_RANK.get(worst, 3) == 0 else worst


def write_paper_semantics(
    paper_dir: Path,
    *,
    specs: Iterable[dict[str, Any]] = GOLD_CLAIM_SPECS,
) -> dict[str, Any]:
    """Write claims/chunks and update the paper quality record."""

    claims = build_claims(paper_dir, specs=specs)
    chunks = build_semantic_chunks(paper_dir, claims)
    (paper_dir / "claims.jsonl").write_text(_jsonl(claims), encoding="utf-8")
    (paper_dir / "chunks.jsonl").write_text(_jsonl(chunks), encoding="utf-8")
    quality_path = paper_dir / "quality.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    is_p0 = str(quality["paper_id"]) in P0_PAPER_IDS
    if is_p0 and (
        len(claims) < 5 or any(item["verification_status"] != "verified" for item in claims)
    ):
        quality["claims_status"] = "fail"
    elif not claims:
        quality["claims_status"] = "fail"
    else:
        quality["claims_status"] = "pass"
    quality["counts"]["claims"] = len(claims)
    quality["counts"]["verified_claims"] = sum(
        item["verification_status"] == "verified" for item in claims
    )
    quality["counts"]["semantic_chunks"] = len(chunks)
    quality["exceptions"] = [
        value
        for value in quality.get("exceptions", [])
        if value != "Claims and retrieval artifacts have not been generated."
    ]
    if quality["retrieval_status"] == "missing":
        quality["exceptions"].append("Corpus retrieval evaluation has not been attached.")
    quality["overall_status"] = _overall_status(quality)
    quality_path.write_text(_json(quality), encoding="utf-8")
    return {"claims": claims, "chunks": chunks, "quality": quality}


def build_claim_metrics(corpus_root: Path) -> dict[str, Any]:
    """Measure reviewed Gold claim coverage and referential integrity."""

    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unresolved: list[str] = []
    for spec in GOLD_CLAIM_SPECS:
        by_paper[str(spec["paper_id"])].append(spec)
    claims: list[dict[str, Any]] = []
    for paper_id in sorted(by_paper):
        paper_dir = corpus_root / paper_id
        if not paper_dir.is_dir():
            raise ValueError(f"Gold semantic paper output is missing: {paper_id}")
        paper_claims = read_jsonl(paper_dir / "claims.jsonl")
        claims.extend(paper_claims)
        expected_ids = {str(item["claim_id"]) for item in by_paper[paper_id]}
        actual_ids = {str(item["claim_id"]) for item in paper_claims}
        if expected_ids != actual_ids:
            unresolved.append(f"{paper_id}:claim-set")
    type_counts = Counter(str(item["claim_type"]) for item in claims)
    evidence_total = sum(len(item["evidence_block_ids"]) for item in claims)
    evidence_resolved = sum(len(item["evidence_text_sha256"]) for item in claims)
    p0_claims = [item for item in claims if item["paper_id"] in P0_PAPER_IDS]
    verified = [item for item in claims if item["verification_status"] == "verified"]
    counts_by_paper = Counter(str(item["paper_id"]) for item in claims)
    return {
        "gold_claim_metrics_version": "1.0.0",
        "audit_basis": "manual source-page review with resolved block/equation/table evidence",
        "paper_count": len(counts_by_paper),
        "claim_count": len(claims),
        "minimum_claims_per_paper": min(counts_by_paper.values()),
        "maximum_claims_per_paper": max(counts_by_paper.values()),
        "claim_type_counts": dict(sorted(type_counts.items())),
        "evidence_reference_count": evidence_total,
        "evidence_resolved_count": evidence_resolved,
        "evidence_coverage": evidence_resolved / evidence_total,
        "audited_claim_count": len(verified),
        "audited_accuracy": len(verified) / len(claims),
        "p0_claim_count": len(p0_claims),
        "p0_verified_count": sum(item["verification_status"] == "verified" for item in p0_claims),
        "p0_verified_rate": (
            sum(item["verification_status"] == "verified" for item in p0_claims) / len(p0_claims)
        ),
        "unresolved_references": unresolved,
    }


def validate_claim_metrics(value: dict[str, Any]) -> None:
    """Enforce the Phase-eight Gold and P0 claim gates."""

    if value["paper_count"] < 10 or value["minimum_claims_per_paper"] < 5:
        raise ValueError("Gold claims require at least five claims per representative paper")
    if value["evidence_coverage"] != 1.0 or value["unresolved_references"]:
        raise ValueError("every Gold claim evidence reference must resolve")
    if value["audited_accuracy"] < 0.95:
        raise ValueError("audited Gold claim accuracy is below ninety-five percent")
    if value["p0_verified_rate"] != 1.0:
        raise ValueError("every P0 claim must be manually verified")
    required_types = {
        "research_question",
        "model_assumption",
        "state_dynamics",
        "measure_and_numeraire",
        "payoff",
        "pricing_equation",
        "calibration_input",
        "numerical_method",
        "empirical_result",
        "limitation",
        "implementation_warning",
    }
    if required_types - set(value["claim_type_counts"]):
        raise ValueError("Gold claims do not cover every required semantic claim type")


def render_claim_metrics(value: dict[str, Any]) -> str:
    """Serialize claim metrics deterministically."""

    return _json(value)
