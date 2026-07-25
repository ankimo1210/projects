from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DOCLING_VERSION = "2.114.0"
SCHEMA_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = PROJECT_ROOT / "sources" / "papers"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "corpus" / "papers"
DEFAULT_TMP_DIR = PROJECT_ROOT / "tmp" / "pdfs"
HARD_CHUNK_MAX_TOKENS = 512


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_math_whitespace(text: str) -> str:
    """Collapse repeated LaTeX spacing commands emitted from wide equation boxes."""

    def clean_block(match: re.Match[str]) -> str:
        body = match.group(1)
        body = re.sub(r"(?:\\[ \t]+){2,}", " ", body)
        body = re.sub(r"[ \t]{3,}", " ", body)
        return f"$${body.strip()}$$"

    return re.sub(r"\$\$(.*?)\$\$", clean_block, text, flags=re.DOTALL)


def normalize_markdown(markdown: str, paper_id: str) -> str:
    lines = markdown.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("## "):
            lines[index] = f"# {line[3:]}"
            break
    markdown = "\n".join(lines).rstrip() + "\n"
    artifact_pattern = re.compile(rf"\((?:[^)\n]*/)?{re.escape(paper_id)}_artifacts/([^)\n]+)\)")
    markdown = artifact_pattern.sub(r"(images/\1)", markdown)
    return clean_math_whitespace(markdown)


def normalize_document_artifact_paths(value: Any, paper_id: str) -> Any:
    """Replace Docling's staging paths with portable corpus-relative image paths."""
    if isinstance(value, dict):
        return {
            key: normalize_document_artifact_paths(item, paper_id) for key, item in value.items()
        }
    if isinstance(value, list):
        return [normalize_document_artifact_paths(item, paper_id) for item in value]
    if isinstance(value, str):
        artifact_pattern = re.compile(rf"(?:^|[/\\]){re.escape(paper_id)}_artifacts[/\\]([^/\\]+)$")
        match = artifact_pattern.search(value)
        if match:
            return f"images/{match.group(1)}"
    return value


def extract_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def source_text_chars(pdf: Path) -> int:
    result = subprocess.run(
        ["pdftotext", str(pdf), "-"],
        check=True,
        capture_output=True,
    )
    return len(result.stdout.decode("utf-8", errors="replace").strip())


def enrich_chunks(
    source: Path,
    destination: Path,
    *,
    paper_id: str,
    title: str,
    source_pdf: str,
    source_sha256: str,
    docling_version: str,
) -> tuple[int, int, list[int]]:
    count = 0
    max_tokens = 0
    page_numbers: set[int] = set()
    with (
        source.open(encoding="utf-8") as input_handle,
        destination.open("w", encoding="utf-8") as output_handle,
    ):
        for count, line in enumerate(input_handle, start=1):
            chunk = json.loads(line)
            for field in ("text", "raw_text"):
                if isinstance(chunk.get(field), str):
                    chunk[field] = clean_math_whitespace(chunk[field])
            chunk_pages = [int(page) for page in chunk.get("page_numbers", [])]
            page_numbers.update(chunk_pages)
            max_tokens = max(max_tokens, int(chunk.get("num_tokens", 0)))
            enriched = {
                "schema_version": SCHEMA_VERSION,
                "chunk_id": f"{paper_id}:{count:04d}",
                "paper_id": paper_id,
                "title": title,
                "source_pdf": source_pdf,
                "source_sha256": source_sha256,
                "parser": {"name": "docling", "version": docling_version},
                **chunk,
            }
            output_handle.write(json.dumps(enriched, ensure_ascii=False) + "\n")
    return count, max_tokens, sorted(page_numbers)


def prepare_paper(
    pdf: Path,
    staging: Path,
    prepared_root: Path,
    *,
    docling_version: str,
    device: str,
    formula_enrichment: bool,
) -> dict[str, Any]:
    paper_id = pdf.stem
    staged_markdown = staging / f"{paper_id}.md"
    staged_json = staging / f"{paper_id}.json"
    staged_chunks = staging / f"{paper_id}.chunks.jsonl"
    missing = [
        path.name for path in (staged_markdown, staged_json, staged_chunks) if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(f"Docling outputs missing for {paper_id}: {missing}")

    destination = prepared_root / paper_id
    destination.mkdir(parents=True)
    markdown = normalize_markdown(staged_markdown.read_text(encoding="utf-8"), paper_id)
    title = extract_title(markdown, paper_id)
    (destination / "document.md").write_text(markdown, encoding="utf-8")
    document = normalize_document_artifact_paths(
        json.loads(staged_json.read_text(encoding="utf-8")), paper_id
    )
    (destination / "document.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    artifacts = staging / f"{paper_id}_artifacts"
    if artifacts.is_dir():
        shutil.copytree(artifacts, destination / "images")

    source_digest = sha256_file(pdf)
    source_pdf = str(pdf.relative_to(PROJECT_ROOT))
    chunk_count, max_chunk_tokens, pages_in_chunks = enrich_chunks(
        staged_chunks,
        destination / "chunks.jsonl",
        paper_id=paper_id,
        title=title,
        source_pdf=source_pdf,
        source_sha256=source_digest,
        docling_version=docling_version,
    )
    page_count = len(document.get("pages", {}))
    raw_text_chars = source_text_chars(pdf)
    extraction_ratio = len(markdown) / raw_text_chars if raw_text_chars else None
    metadata: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "paper_id": paper_id,
        "title": title,
        "source": {
            "path": source_pdf,
            "filename": pdf.name,
            "sha256": source_digest,
            "bytes": pdf.stat().st_size,
        },
        "conversion": {
            "tool": "docling",
            "version": docling_version,
            "generated_at": datetime.now(UTC).isoformat(),
            "device": device,
            "ocr": False,
            "table_mode": "accurate",
            "formula_enrichment": formula_enrichment,
            "chunker": "hybrid",
            "chunk_max_tokens": 480,
        },
        "document": {
            "pages": page_count,
            "text_blocks": len(document.get("texts", [])),
            "tables": len(document.get("tables", [])),
            "pictures": len(document.get("pictures", [])),
            "markdown_chars": len(markdown),
            "math_blocks": markdown.count("$$") // 2,
            "chunks": chunk_count,
            "max_chunk_tokens": max_chunk_tokens,
            "pages_in_chunks": pages_in_chunks,
        },
        "quality": {
            "source_text_chars": raw_text_chars,
            "markdown_to_source_text_ratio": (
                round(extraction_ratio, 4) if extraction_ratio is not None else None
            ),
            "has_abstract": bool(re.search(r"\babstract\b", markdown, flags=re.IGNORECASE)),
            "has_references": bool(
                re.search(
                    r"^#{1,6}\s+(references|bibliography)\b",
                    markdown,
                    flags=re.IGNORECASE | re.MULTILINE,
                )
            ),
        },
    }
    (destination / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata


def docling_version() -> str:
    try:
        return importlib.metadata.version("docling")
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError(
            f"Docling {DOCLING_VERSION} is required; run via `make paper-corpus`."
        ) from error


def convert_papers(
    source_dir: Path,
    output_dir: Path,
    *,
    device: str,
    enrich_formula: bool,
    overwrite: bool,
) -> dict[str, Any]:
    pdfs = sorted(source_dir.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDFs found in {source_dir}")
    version = docling_version()
    if version != DOCLING_VERSION:
        raise RuntimeError(f"Docling {DOCLING_VERSION} required, found {version}")
    if enrich_formula and device == "cuda":
        include_paths = [Path(path) for path in os.environ.get("CPATH", "").split(":") if path]
        if (
            not any((path / "Python.h").is_file() for path in include_paths)
            and not Path("/usr/include/python3.12/Python.h").is_file()
        ):
            raise RuntimeError(
                "CUDA formula enrichment requires Python.h. Install python3.12-dev or add its "
                "include directory to CPATH."
            )

    DEFAULT_TMP_DIR.mkdir(parents=True, exist_ok=True)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="paper-corpus-", dir=DEFAULT_TMP_DIR) as temp_name:
        temporary = Path(temp_name)
        staging = temporary / "docling"
        prepared = temporary / "prepared"
        runtime = temporary / "runtime"
        staging.mkdir()
        prepared.mkdir()
        runtime.mkdir()
        command = [
            "docling",
            "convert",
            str(source_dir),
            "--from",
            "pdf",
            "--to",
            "md",
            "--to",
            "json",
            "--to",
            "chunks",
            "--chunks-type",
            "hybrid",
            "--chunks-max-tokens",
            "480",
            "--image-export-mode",
            "referenced",
            "--pipeline",
            "standard",
            "--no-ocr",
            "--tables",
            "--table-mode",
            "accurate",
            "--device",
            device,
            "--num-threads",
            "4",
            "--document-timeout",
            "900",
            "--output",
            str(staging),
        ]
        if enrich_formula:
            command.append("--enrich-formula")
        environment = os.environ.copy()
        environment["TMPDIR"] = str(runtime)
        subprocess.run(command, check=True, cwd=PROJECT_ROOT, env=environment)

        papers = [
            prepare_paper(
                pdf,
                staging,
                prepared,
                docling_version=version,
                device=device,
                formula_enrichment=enrich_formula,
            )
            for pdf in pdfs
        ]
        index = {
            "schema_version": SCHEMA_VERSION,
            "generated_at": datetime.now(UTC).isoformat(),
            "paper_count": len(papers),
            "papers": papers,
        }
        (prepared / "_index.json").write_text(
            json.dumps(index, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("repair_paper_formulas.py")),
                "--corpus-dir",
                str(prepared),
            ],
            check=True,
            cwd=PROJECT_ROOT,
        )

        if output_dir.exists():
            if not overwrite:
                raise FileExistsError(f"{output_dir} exists; pass --overwrite to replace it")
            backup = temporary / "previous"
            output_dir.rename(backup)
        try:
            shutil.move(str(prepared), str(output_dir))
        except Exception:
            backup = temporary / "previous"
            if backup.exists() and not output_dir.exists():
                backup.rename(output_dir)
            raise
    return validate_corpus(source_dir, output_dir)


def validate_corpus(source_dir: Path, output_dir: Path) -> dict[str, Any]:
    pdfs = sorted(source_dir.glob("*.pdf"))
    expected_ids = {pdf.stem for pdf in pdfs}
    actual_ids = {path.name for path in output_dir.iterdir() if path.is_dir()}
    if expected_ids != actual_ids:
        raise RuntimeError(
            f"Corpus paper set mismatch: missing={sorted(expected_ids - actual_ids)}, "
            f"extra={sorted(actual_ids - expected_ids)}"
        )
    chunk_count = 0
    math_blocks = 0
    formula_count = 0
    verified_formula_count = 0
    semantic_high_confidence_count = 0
    semantic_not_formula_count = 0
    for pdf in pdfs:
        paper_dir = output_dir / pdf.stem
        required = [
            paper_dir / "document.md",
            paper_dir / "document.json",
            paper_dir / "chunks.jsonl",
            paper_dir / "metadata.json",
        ]
        missing = [path.name for path in required if not path.is_file() or path.stat().st_size == 0]
        formula_manifest = paper_dir / "formulas.jsonl"
        if not formula_manifest.is_file():
            missing.append(formula_manifest.name)
        if missing:
            raise RuntimeError(f"Missing or empty corpus files for {pdf.stem}: {missing}")
        metadata = json.loads((paper_dir / "metadata.json").read_text(encoding="utf-8"))
        if metadata["source"]["sha256"] != sha256_file(pdf):
            raise RuntimeError(f"Source hash mismatch for {pdf.stem}")
        with (paper_dir / "chunks.jsonl").open(encoding="utf-8") as handle:
            chunks = [json.loads(line) for line in handle]
        if not chunks or any(chunk["paper_id"] != pdf.stem for chunk in chunks):
            raise RuntimeError(f"Invalid chunks for {pdf.stem}")
        if any(not str(chunk.get("text", "")).strip() for chunk in chunks):
            raise RuntimeError(f"Empty retrieval chunk for {pdf.stem}")
        if metadata["document"]["chunks"] != len(chunks):
            raise RuntimeError(f"Chunk metadata count mismatch for {pdf.stem}")
        oversized_chunks = [
            chunk for chunk in chunks if int(chunk.get("num_tokens", 0)) > HARD_CHUNK_MAX_TOKENS
        ]
        if oversized_chunks:
            raise RuntimeError(
                f"Chunks exceed {HARD_CHUNK_MAX_TOKENS} tokens for {pdf.stem}: "
                f"{[chunk['chunk_id'] for chunk in oversized_chunks]}"
            )
        with formula_manifest.open(encoding="utf-8") as handle:
            formulas = [json.loads(line) for line in handle]
        if any(formula["paper_id"] != pdf.stem for formula in formulas):
            raise RuntimeError(f"Invalid formula provenance for {pdf.stem}")
        formula_ids = [formula["formula_id"] for formula in formulas]
        document_markdown = (paper_dir / "document.md").read_text(encoding="utf-8")
        if "<!-- formula-not-decoded -->" in document_markdown:
            raise RuntimeError(f"Unresolved formula placeholder for {pdf.stem}")
        document_formula_ids = re.findall(r'<!-- formula-start id="([^"]+)"', document_markdown)
        if document_formula_ids != formula_ids:
            raise RuntimeError(f"Formula order mismatch in document.md for {pdf.stem}")
        for field in ("text", "raw_text"):
            chunk_formula_ids = [
                formula_id
                for chunk in chunks
                for formula_id in re.findall(
                    r'<!-- formula-start id="([^"]+)"', str(chunk.get(field, ""))
                )
            ]
            if chunk_formula_ids != formula_ids:
                raise RuntimeError(f"Formula order mismatch in chunks.{field} for {pdf.stem}")
        for formula in formulas:
            image = formula.get("source_image")
            if image and not (paper_dir / image).is_file():
                raise RuntimeError(f"Missing formula source crop for {formula['formula_id']}")
            if formula["status"].startswith("verified_") and not formula.get("latex"):
                raise RuntimeError(f"Verified formula has no LaTeX: {formula['formula_id']}")
            if "source" in formula["status"] and not formula.get("source_verification"):
                raise RuntimeError(
                    f"Source-verified formula has no provenance: {formula['formula_id']}"
                )
            if formula["status"].startswith("semantic_") and not formula.get("semantic_review"):
                raise RuntimeError(
                    f"Semantic formula has no review record: {formula['formula_id']}"
                )
            if formula["status"] == "semantic_high_confidence" and not formula.get("latex"):
                raise RuntimeError(
                    f"High-confidence semantic formula has no LaTeX: {formula['formula_id']}"
                )
            if formula["status"] == "semantic_not_formula" and formula.get("latex"):
                raise RuntimeError(
                    f"Non-formula semantic record still has LaTeX: {formula['formula_id']}"
                )
        quality = metadata.get("formula_quality", {})
        if quality.get("total") != len(formulas):
            raise RuntimeError(f"Formula metadata count mismatch for {pdf.stem}")
        chunk_count += len(chunks)
        math_blocks += int(metadata["document"]["math_blocks"])
        formula_count += len(formulas)
        verified_formula_count += sum(
            formula["status"].startswith("verified_") for formula in formulas
        )
        semantic_high_confidence_count += sum(
            formula["status"] == "semantic_high_confidence" for formula in formulas
        )
        semantic_not_formula_count += sum(
            formula["status"] == "semantic_not_formula" for formula in formulas
        )
    summary = {
        "ok": True,
        "paper_count": len(pdfs),
        "chunk_count": chunk_count,
        "math_blocks": math_blocks,
        "formula_count": formula_count,
        "verified_formula_count": verified_formula_count,
        "semantic_high_confidence_count": semantic_high_confidence_count,
        "semantic_not_formula_count": semantic_not_formula_count,
        "output_dir": str(output_dir),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an AI-readable corpus from paper PDFs.")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda", "mps"), default="auto")
    parser.add_argument("--enrich-formula", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    if args.check_only:
        validate_corpus(source_dir, output_dir)
    else:
        convert_papers(
            source_dir,
            output_dir,
            device=args.device,
            enrich_formula=args.enrich_formula,
            overwrite=args.overwrite,
        )


if __name__ == "__main__":
    main()
