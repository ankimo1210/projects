"""Convert local reference PDFs into an AI-friendly, page-citable corpus.

The generated full text stays under ``references/processed/``, which is ignored
by Git. PyMuPDF4LLM is intentionally an ephemeral tool dependency; run this from
the workspace root with::

    uv run --no-project --with pymupdf4llm \
        python johnhull/scripts/build_paper_corpus.py --sample

Use ``--all`` after reviewing the five-paper sample quality report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = PROJECT_ROOT / "references" / "papers"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "references" / "processed"
DEFAULT_CATALOG = PROJECT_ROOT / "references" / "README.md"
SAMPLE_PDFS = (
    "1900-bachelier-theorie-de-la-speculation.pdf",
    "1978-margrabe-exchange-option.pdf",
    "1993-heston-closed-form-stochastic-volatility.pdf",
    "2002-hagan-et-al-managing-smile-risk.pdf",
    "2026-sakuma-dml-0dte.pdf",
)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
IMAGE_TARGET_RE = re.compile(r"!\[[^\]]*\]\((?P<target>[^)]+)\)")
LOCAL_PDF_RE = re.compile(r"\(papers/(?P<filename>[^)]+\.pdf)\)")
MARKDOWN_LINK_RE = re.compile(r"^\[(?P<label>.+)]\((?P<url>https?://.+)\)$")
REPLACEMENT_CHAR = "\ufffd"


@dataclass(frozen=True)
class CatalogEntry:
    year: str
    authors: str
    title: str
    source_url: str


@dataclass(frozen=True)
class Paragraph:
    text: str
    page: int
    section: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert reference PDFs to Markdown, page JSONL, and RAG chunks."
    )
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument(
        "--sample",
        action="store_true",
        help="Convert five representative PDFs for the quality-gate trial.",
    )
    selector.add_argument("--all", action="store_true", help="Convert every PDF in input-dir.")
    selector.add_argument(
        "--pdf",
        action="append",
        metavar="PATH",
        help="Convert one PDF; repeat the option to select multiple files.",
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--ocr-language", default="eng")
    parser.add_argument("--force-ocr", action="store_true")
    parser.add_argument(
        "--write-images",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Extract equation/figure images and link them from Markdown (default: true).",
    )
    parser.add_argument(
        "--max-chunk-chars",
        type=int,
        default=4800,
        help="Soft chunk limit, about 1,200 English tokens (default: 4800).",
    )
    parser.add_argument(
        "--overlap-chars",
        type=int,
        default=400,
        help="Maximum full-paragraph overlap between adjacent chunks (default: 400).",
    )
    args = parser.parse_args()
    if args.max_chunk_chars < 1000:
        parser.error("--max-chunk-chars must be at least 1000")
    if args.overlap_chars < 0 or args.overlap_chars >= args.max_chunk_chars:
        parser.error("--overlap-chars must be non-negative and smaller than max-chunk-chars")
    return args


def import_converter() -> Any:
    try:
        import pymupdf4llm  # type: ignore[import-not-found]
    except ImportError as exc:
        command = (
            "uv run --no-project --with pymupdf4llm "
            "python johnhull/scripts/build_paper_corpus.py --sample"
        )
        raise SystemExit(f"PyMuPDF4LLM is required. Run:\n  {command}") from exc
    return pymupdf4llm


def load_catalog(path: Path) -> dict[str, CatalogEntry]:
    """Load table rows from the human-reviewed paper inventory."""
    entries: dict[str, CatalogEntry] = {}
    if not path.is_file():
        return entries
    for line in path.read_text(encoding="utf-8").splitlines():
        local_match = LOCAL_PDF_RE.search(line)
        if local_match is None or not line.startswith("|"):
            continue
        columns = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(columns) != 4:
            continue
        title_match = MARKDOWN_LINK_RE.search(columns[2])
        if title_match is None:
            continue
        entries[local_match.group("filename")] = CatalogEntry(
            year=columns[0],
            authors=columns[1],
            title=title_match.group("label"),
            source_url=title_match.group("url"),
        )
    return entries


def select_pdfs(args: argparse.Namespace) -> list[Path]:
    input_dir = args.input_dir.resolve()
    if args.sample:
        paths = [input_dir / name for name in SAMPLE_PDFS]
    elif args.all:
        paths = sorted(input_dir.glob("*.pdf"))
    else:
        paths = []
        for raw_path in args.pdf:
            path = Path(raw_path)
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            paths.append(path.resolve())
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise SystemExit("Missing PDF(s):\n  " + "\n  ".join(missing))
    if not paths:
        raise SystemExit(f"No PDFs found in {input_dir}")
    return paths


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_markdown(text: str, assets_dir: Path) -> str:
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n"))
    text = text.replace("\u00ad", "")
    asset_prefixes = {assets_dir.resolve().as_posix()}
    for base in (Path.cwd().resolve(), PROJECT_ROOT.resolve()):
        try:
            asset_prefixes.add(assets_dir.resolve().relative_to(base).as_posix())
        except ValueError:
            pass
    for prefix in sorted(asset_prefixes, key=len, reverse=True):
        text = text.replace(prefix.rstrip("/") + "/", "assets/")
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def page_records(page_chunks: list[dict[str, Any]], paper_id: str, assets_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, chunk in enumerate(page_chunks, start=1):
        metadata = dict(chunk.get("metadata") or {})
        page_number = int(metadata.get("page_number") or index)
        text = normalize_markdown(str(chunk.get("text") or ""), assets_dir)
        records.append(
            {
                "paper_id": paper_id,
                "page_number": page_number,
                "text": text,
                "char_count": len(text),
                "toc_items": chunk.get("toc_items") or [],
                "layout_blocks": chunk.get("page_boxes") or [],
            }
        )
    return records


def heading_text(line: str) -> str | None:
    match = HEADING_RE.match(line.strip())
    if match is None:
        return None
    candidate = match.group(2).strip(" *_")
    if len(candidate) > 180 or any(char in candidate for char in "=\\{}[]$"):
        return None
    if sum(char.isalpha() for char in candidate) < 3:
        return None
    return candidate


def current_section(text: str, fallback: str) -> str:
    section = fallback
    for line in text.splitlines():
        candidate = heading_text(line)
        if candidate:
            section = candidate
    return section


def paragraphs_from_pages(pages: list[dict[str, Any]]) -> list[Paragraph]:
    paragraphs: list[Paragraph] = []
    section = "Front matter"
    for page in pages:
        page_number = int(page["page_number"])
        for raw_paragraph in re.split(r"\n\s*\n", str(page["text"])):
            text = raw_paragraph.strip()
            if not text:
                continue
            section = current_section(text, section)
            paragraphs.append(Paragraph(text=text, page=page_number, section=section))
    return paragraphs


def make_chunk(
    paper_id: str,
    chunk_number: int,
    paragraphs: list[Paragraph],
) -> dict[str, Any]:
    text = "\n\n".join(paragraph.text for paragraph in paragraphs).strip()
    encoded = text.encode("utf-8")
    return {
        "chunk_id": f"{paper_id}:{chunk_number:04d}",
        "paper_id": paper_id,
        "asset_base": f"{paper_id}/assets",
        "section": paragraphs[-1].section,
        "page_start": min(paragraph.page for paragraph in paragraphs),
        "page_end": max(paragraph.page for paragraph in paragraphs),
        "text": text,
        "char_count": len(text),
        "token_count_estimate": math.ceil(len(text) / 4),
        "content_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def chunk_pages(
    pages: list[dict[str, Any]],
    paper_id: str,
    max_chars: int,
    overlap_chars: int,
) -> list[dict[str, Any]]:
    paragraphs = paragraphs_from_pages(pages)
    chunks: list[dict[str, Any]] = []
    pending: list[Paragraph] = []
    pending_chars = 0

    for paragraph in paragraphs:
        separator_chars = 2 if pending else 0
        if pending and pending_chars + separator_chars + len(paragraph.text) > max_chars:
            chunks.append(make_chunk(paper_id, len(chunks) + 1, pending))
            overlap: list[Paragraph] = []
            overlap_size = 0
            for prior in reversed(pending):
                candidate_size = len(prior.text) + (2 if overlap else 0)
                if overlap and overlap_size + candidate_size > overlap_chars:
                    break
                if not overlap and len(prior.text) > overlap_chars:
                    break
                overlap.insert(0, prior)
                overlap_size += candidate_size
            pending = overlap
            pending_chars = overlap_size
        if pending:
            pending_chars += 2
        pending.append(paragraph)
        pending_chars += len(paragraph.text)

    if pending:
        chunks.append(make_chunk(paper_id, len(chunks) + 1, pending))
    return chunks


def yaml_value(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_paper_markdown(metadata: dict[str, Any], pages: list[dict[str, Any]]) -> str:
    front_matter = [
        "---",
        f"paper_id: {yaml_value(metadata['paper_id'])}",
        f"title: {yaml_value(metadata['title'])}",
        f"authors: {yaml_value(metadata['authors'])}",
        f"year: {yaml_value(metadata['year'])}",
        f"source_url: {yaml_value(metadata['source_url'])}",
        f"source_pdf: {yaml_value(metadata['source_pdf'])}",
        f"source_sha256: {yaml_value(metadata['source_sha256'])}",
        f"converter: {yaml_value(metadata['converter'])}",
        "---",
    ]
    body: list[str] = []
    for page in pages:
        body.append(f"<!-- page: {page['page_number']} -->")
        body.append(str(page["text"]))
    return "\n".join(front_matter) + "\n\n" + "\n\n".join(body).rstrip() + "\n"


def quality_metrics(
    paper_id: str,
    pages: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    image_count: int,
    catalog_entry: CatalogEntry | None,
) -> dict[str, Any]:
    texts = [str(page["text"]) for page in pages]
    combined = "\n".join(texts)
    page_count = len(pages)
    total_chars = len(combined)
    empty_pages = [index for index, text in enumerate(texts, start=1) if not text.strip()]
    short_pages = [index for index, text in enumerate(texts, start=1) if len(text.strip()) < 100]
    replacements = combined.count(REPLACEMENT_CHAR)
    image_refs = len(IMAGE_RE.findall(combined))
    heading_count = sum(1 for line in combined.splitlines() if heading_text(line))
    math_delimiters = combined.count("$$") + combined.count("\\(") + combined.count("\\[")
    warnings: list[str] = []
    failures: list[str] = []

    if not catalog_entry:
        warnings.append("catalog metadata missing")
    if empty_pages:
        warnings.append(f"{len(empty_pages)} empty page(s)")
    if page_count and len(short_pages) / page_count > 0.2:
        warnings.append(f"{len(short_pages)} very short page(s)")
    if total_chars and replacements / total_chars > 0.001:
        warnings.append("high replacement-character ratio")
    visual_math_threshold = math_delimiters + max(5, page_count // 4)
    if image_refs > visual_math_threshold:
        warnings.append("many visual/equation images are not represented as LaTeX math")
    if image_refs != image_count:
        warnings.append(f"image references/files differ ({image_refs}/{image_count})")
    if heading_count < 2:
        warnings.append("few detected headings")
    if page_count and total_chars / page_count < 150:
        failures.append("average extracted text below 150 characters/page")
    if page_count and len(empty_pages) / page_count >= 0.15:
        failures.append("at least 15% of pages are empty")

    status = "fail" if failures else "review" if warnings else "pass"
    return {
        "paper_id": paper_id,
        "status": status,
        "page_count": page_count,
        "total_chars": total_chars,
        "average_chars_per_page": round(total_chars / page_count, 1) if page_count else 0,
        "empty_pages": empty_pages,
        "short_pages": short_pages,
        "replacement_characters": replacements,
        "heading_count": heading_count,
        "image_references": image_refs,
        "image_files": image_count,
        "latex_math_markers": math_delimiters,
        "chunk_count": len(chunks),
        "max_chunk_chars": max((int(chunk["char_count"]) for chunk in chunks), default=0),
        "warnings": warnings,
        "failures": failures,
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    lines = [json.dumps(record, ensure_ascii=False, separators=(",", ":")) for record in records]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def validate_generated_output(
    paper_dir: Path,
    paper_markdown: str,
    pages: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> int:
    marker_count = len(re.findall(r"^<!-- page: \d+ -->$", paper_markdown, flags=re.MULTILINE))
    if marker_count != len(pages):
        raise RuntimeError(f"page marker mismatch: {marker_count} markers for {len(pages)} pages")

    local_targets: set[str] = set()
    for match in IMAGE_TARGET_RE.finditer(paper_markdown):
        target = match.group("target")
        if target.startswith(("http://", "https://", "data:")):
            continue
        if not target.startswith("assets/"):
            raise RuntimeError(f"non-local image path in Markdown: {target}")
        if not (paper_dir / target).is_file():
            raise RuntimeError(f"missing extracted image: {target}")
        local_targets.add(target)

    chunk_ids: set[str] = set()
    for chunk in chunks:
        chunk_id = str(chunk["chunk_id"])
        if chunk_id in chunk_ids:
            raise RuntimeError(f"duplicate chunk id: {chunk_id}")
        chunk_ids.add(chunk_id)
        expected_hash = hashlib.sha256(str(chunk["text"]).encode("utf-8")).hexdigest()
        if chunk["content_sha256"] != expected_hash:
            raise RuntimeError(f"chunk hash mismatch: {chunk_id}")
    return len(local_targets)


def relative_to_project(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def convert_pdf(
    converter: Any,
    pdf_path: Path,
    output_root: Path,
    catalog: dict[str, CatalogEntry],
    args: argparse.Namespace,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    paper_id = pdf_path.stem
    paper_dir = output_root / paper_id
    assets_dir = paper_dir / "assets"
    paper_dir.mkdir(parents=True, exist_ok=True)
    if args.write_images:
        assets_dir.mkdir(parents=True, exist_ok=True)

    print(f"Converting {pdf_path.name}...", file=sys.stderr, flush=True)
    raw_chunks = converter.to_markdown(
        str(pdf_path.resolve()),
        page_chunks=True,
        header=False,
        footer=False,
        use_ocr=True,
        force_ocr=args.force_ocr,
        ocr_language=args.ocr_language,
        write_images=args.write_images,
        image_path=str(assets_dir.resolve()),
        show_progress=False,
    )
    pages = page_records(raw_chunks, paper_id, assets_dir)
    chunks = chunk_pages(pages, paper_id, args.max_chunk_chars, args.overlap_chars)
    catalog_entry = catalog.get(pdf_path.name)
    pdf_metadata = dict(raw_chunks[0].get("metadata") or {}) if raw_chunks else {}
    title = catalog_entry.title if catalog_entry else str(pdf_metadata.get("title") or paper_id)
    authors = catalog_entry.authors if catalog_entry else str(pdf_metadata.get("author") or "")
    year = catalog_entry.year if catalog_entry else ""
    source_url = catalog_entry.source_url if catalog_entry else ""
    metadata = {
        "paper_id": paper_id,
        "title": title,
        "authors": authors,
        "year": year,
        "source_url": source_url,
        "source_pdf": relative_to_project(pdf_path),
        "source_sha256": sha256_file(pdf_path),
        "converter": f"PyMuPDF4LLM {converter.__version__}",
        "conversion_options": {
            "header": False,
            "footer": False,
            "use_ocr": True,
            "force_ocr": args.force_ocr,
            "ocr_language": args.ocr_language,
            "write_images": args.write_images,
            "max_chunk_chars": args.max_chunk_chars,
            "overlap_chars": args.overlap_chars,
        },
        "pdf_metadata": {
            key: value
            for key, value in pdf_metadata.items()
            if key not in {"file_path", "page_number"}
        },
    }
    write_json(paper_dir / "metadata.json", metadata)
    write_jsonl(paper_dir / "pages.jsonl", pages)
    write_jsonl(paper_dir / "chunks.jsonl", chunks)
    paper_markdown = build_paper_markdown(metadata, pages)
    (paper_dir / "paper.md").write_text(paper_markdown, encoding="utf-8")

    image_count = validate_generated_output(paper_dir, paper_markdown, pages, chunks)
    quality = quality_metrics(paper_id, pages, chunks, image_count, catalog_entry)
    write_json(paper_dir / "quality.json", quality)
    index_entry = {
        **{key: metadata[key] for key in ("paper_id", "title", "authors", "year", "source_url")},
        "page_count": len(pages),
        "chunk_count": len(chunks),
        "quality_status": quality["status"],
        "paper_markdown": f"{paper_id}/paper.md",
    }
    return index_entry, chunks, quality


def quality_report_markdown(qualities: list[dict[str, Any]]) -> str:
    lines = [
        "# Paper corpus quality report",
        "",
        "Generated locally from the selected PDFs. `review` means the text is usable but",
        "equations, images, OCR, or section structure should be sampled manually.",
        "",
        "| Paper | Status | Pages | Chars/page | Chunks | Images | Warnings |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for quality in qualities:
        warnings = "; ".join(quality["failures"] + quality["warnings"]) or "—"
        lines.append(
            f"| {quality['paper_id']} | {quality['status']} | {quality['page_count']} | "
            f"{quality['average_chars_per_page']} | {quality['chunk_count']} | "
            f"{quality['image_files']} | {warnings} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    converter = import_converter()
    pdfs = select_pdfs(args)
    output_root = args.output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    catalog = load_catalog(args.catalog.resolve())

    index: list[dict[str, Any]] = []
    corpus: list[dict[str, Any]] = []
    qualities: list[dict[str, Any]] = []
    for pdf_path in pdfs:
        index_entry, chunks, quality = convert_pdf(
            converter, pdf_path, output_root, catalog, args
        )
        index.append(index_entry)
        corpus.extend(chunks)
        qualities.append(quality)

    write_json(output_root / "index.json", index)
    write_jsonl(output_root / "corpus.jsonl", corpus)
    write_json(output_root / "quality_report.json", qualities)
    (output_root / "quality_report.md").write_text(
        quality_report_markdown(qualities), encoding="utf-8"
    )
    counts: dict[str, int] = {"pass": 0, "review": 0, "fail": 0}
    for quality in qualities:
        counts[str(quality["status"])] += 1
    print(
        f"Converted {len(index)} paper(s), {len(corpus)} chunk(s): "
        f"pass={counts['pass']} review={counts['review']} fail={counts['fail']}",
        file=sys.stderr,
    )
    print(output_root / "quality_report.md")
    return 1 if counts["fail"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
