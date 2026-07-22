"""Build the reproducible v1 baseline used by the corpus-v2 migration."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .preflight import pdf_page_count, qpdf_check, sha256_file
from .schema import CORPUS_SCHEMA_VERSION, P0_PAPER_IDS, REQUIRED_SEMANTIC_SOURCES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCES_ROOT = PROJECT_ROOT / "references"
DEFAULT_OUTPUT = REFERENCES_ROOT / "corpus_baseline.json"


def read_json(path: Path) -> Any:
    """Read UTF-8 JSON from *path*."""

    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _metadata_source_hash(processed_root: Path, paper_id: str) -> str | None:
    path = processed_root / paper_id / "metadata.json"
    if not path.is_file():
        return None
    return str(read_json(path).get("source_sha256") or "") or None


def build_baseline(references_root: Path = REFERENCES_ROOT) -> dict[str, Any]:
    """Return a deterministic source/corpus baseline manifest."""

    papers_root = references_root / "papers"
    processed_root = references_root / "processed"
    qualities = read_json(processed_root / "quality_report.json")
    index = read_json(processed_root / "index.json")
    quality_by_id = {str(item["paper_id"]): item for item in qualities}
    index_by_id = {str(item["paper_id"]): item for item in index}

    sources: list[dict[str, Any]] = []
    for path in sorted(papers_root.glob("*.pdf")):
        paper_id = path.stem
        source_sha256 = sha256_file(path)
        page_count = pdf_page_count(path)
        structure = qpdf_check(path)
        quality = quality_by_id.get(paper_id)
        corpus_index = index_by_id.get(paper_id)
        metadata_hash = _metadata_source_hash(processed_root, paper_id)
        sources.append(
            {
                "paper_id": paper_id,
                "source_pdf": f"references/papers/{path.name}",
                "source_sha256": source_sha256,
                "source_bytes": path.stat().st_size,
                "source_page_count": page_count,
                "pdf_structure": structure.to_dict(),
                "p0": paper_id in P0_PAPER_IDS,
                "corpus_present": corpus_index is not None,
                "corpus_page_count": corpus_index.get("page_count") if corpus_index else None,
                "corpus_chunk_count": corpus_index.get("chunk_count") if corpus_index else None,
                "corpus_quality_status": quality.get("status") if quality else None,
                "image_files": quality.get("image_files") if quality else None,
                "latex_math_markers": quality.get("latex_math_markers") if quality else None,
                "replacement_characters": quality.get("replacement_characters")
                if quality
                else None,
                "source_hash_matches_metadata": metadata_hash == source_sha256,
                "page_count_matches_corpus": bool(
                    corpus_index and corpus_index.get("page_count") == page_count
                ),
            }
        )

    structure_counts = Counter(item["pdf_structure"]["status"] for item in sources)
    corpus_status_counts = Counter(str(item["corpus_quality_status"]) for item in sources)
    return {
        "manifest_version": "1.0.0",
        "target_corpus_schema_version": CORPUS_SCHEMA_VERSION,
        "source_count": len(sources),
        "source_page_count": sum(int(item["source_page_count"]) for item in sources),
        "source_bytes": sum(int(item["source_bytes"]) for item in sources),
        "corpus_chunk_count": sum(int(item["corpus_chunk_count"] or 0) for item in sources),
        "image_files": sum(int(item["image_files"] or 0) for item in sources),
        "latex_math_markers": sum(int(item["latex_math_markers"] or 0) for item in sources),
        "replacement_characters": sum(int(item["replacement_characters"] or 0) for item in sources),
        "pdf_structure_counts": dict(sorted(structure_counts.items())),
        "corpus_status_counts": dict(sorted(corpus_status_counts.items())),
        "p0_paper_ids": list(P0_PAPER_IDS),
        "required_semantic_sources": list(REQUIRED_SEMANTIC_SOURCES),
        "sources": sources,
    }


def render_baseline(manifest: dict[str, Any]) -> str:
    """Serialize a baseline manifest in stable repository format."""

    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_baseline(
    output_path: Path = DEFAULT_OUTPUT,
    references_root: Path = REFERENCES_ROOT,
) -> str:
    """Build and write the baseline, returning its serialized form."""

    rendered = render_baseline(build_baseline(references_root))
    output_path.write_text(rendered, encoding="utf-8")
    return rendered
