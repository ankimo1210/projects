from __future__ import annotations

import argparse
import json
import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_DIR = PROJECT_ROOT / "corpus" / "papers"
DEFAULT_OVERRIDES = PROJECT_ROOT / "manifests" / "formula_overrides.json"
DEFAULT_SOURCE_MATCHES = PROJECT_ROOT / "manifests" / "formula_source_matches.json"
SOURCE_ALIGNMENT_ENVIRONMENTS = {
    "align",
    "align*",
    "alignat",
    "alignat*",
    "flalign",
    "flalign*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "eqnarray",
    "eqnarray*",
}

FORMULA_BLOCK_PATTERN = re.compile(
    r"<!-- formula-start\b[^>]*-->.*?<!-- formula-end -->"
    r"|\$\$.*?\$\$"
    r"|<!-- formula-not-decoded -->",
    flags=re.DOTALL,
)


def load_overrides(path: Path = DEFAULT_OVERRIDES) -> dict[str, dict[str, dict[str, str]]]:
    overrides = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(overrides, dict):
        raise TypeError("Formula overrides must be a JSON object")
    return overrides


def load_source_matches(path: Path = DEFAULT_SOURCE_MATCHES) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    matches = manifest.get("matches")
    if not isinstance(matches, dict):
        raise TypeError("Formula source matches must contain a matches object")
    return matches


def formula_items(document: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [item for item in document.get("texts", []) if item.get("label") == "formula"]


def _clean_latex(latex: str) -> str:
    latex = re.sub(r"(?:\\[ \t]+){2,}", " ", latex)
    return re.sub(r"[ \t]{2,}", " ", latex).strip()


def portable_source_latex(match: Mapping[str, Any]) -> str:
    latex = str(match["source_latex"])
    latex = latex.replace(r"\dmodel", r"d_{\mathrm{model}}")
    latex = latex.replace(r"\bm", r"\boldsymbol")
    latex = re.sub(r"\\myvec\s*\{([^{}]*)\}", r"\\mathbf{\1}", latex)
    latex = latex.replace(r"\vola", r"\nu")
    latex = latex.replace(r"\upnu", r"\nu")
    latex = latex.replace(r"\varoslash", r"\oslash")
    latex = re.sub(
        r"\\(?:tiny|scriptsize|footnotesize|small|normalsize|large|Large|LARGE|huge|Huge)\b",
        "",
        latex,
    )
    latex = re.sub(r"\\\\\s*$", "", latex).strip()
    if match.get("environment") in SOURCE_ALIGNMENT_ENVIRONMENTS:
        latex = rf"\begin{{aligned}}{latex}\end{{aligned}}"
    return _clean_latex(latex)


def build_formula_records(
    paper_id: str,
    document: Mapping[str, Any],
    *,
    source_pdf: str,
    overrides: Mapping[str, Mapping[str, Mapping[str, str]]],
    source_matches: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    paper_overrides = overrides.get(paper_id, {})
    resolved_source_matches = source_matches or {}
    records: list[dict[str, Any]] = []
    used_overrides: set[str] = set()
    for position, item in enumerate(formula_items(document), start=1):
        formula_id = f"{paper_id}:formula:{position:04d}"
        self_ref = str(item.get("self_ref", ""))
        override = paper_overrides.get(self_ref)
        source_match = resolved_source_matches.get(formula_id)
        decoded = str(item.get("text", "")).strip()
        provenance = item.get("prov") or []
        primary = provenance[0] if provenance else {}
        page = int(primary["page_no"]) if "page_no" in primary else None
        bbox = primary.get("bbox")

        if override:
            latex = _clean_latex(override["latex"])
            status = "verified_manual"
            note = override.get("note", "Transcribed and checked against the source PDF.")
            used_overrides.add(self_ref)
        elif decoded:
            latex = _clean_latex(decoded)
            status = "decoded_unverified"
            note = "Machine-decoded LaTeX; verify against the linked source crop before use."
        else:
            latex = None
            status = "text_layer_fallback"
            note = "No reliable LaTeX decode; use the source crop and PDF text layer together."

        verification_methods = ["manual_pdf"] if override else []
        if source_match:
            if source_match.get("document_ref") != self_ref:
                raise RuntimeError(f"Formula source match document ref drift for {formula_id}")
            if source_match.get("source_pdf") != source_pdf:
                raise RuntimeError(f"Formula source match PDF drift for {formula_id}")
            if source_match.get("base_status") != status:
                raise RuntimeError(
                    f"Formula source match base status drift for {formula_id}: "
                    f"{source_match.get('base_status')} != {status}"
                )
            verification_methods.append("arxiv_tex")
            if override:
                status = "verified_source_and_manual"
            else:
                latex = portable_source_latex(source_match)
                status = "verified_source"
            note = (
                f"Matched to exact arXiv source {source_match['arxiv_version']} at "
                f"{source_match['source_file']}:{source_match['source_line']} "
                f"(score={source_match['score']})."
            )

        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "formula_id": formula_id,
                "paper_id": paper_id,
                "position": position,
                "document_ref": self_ref,
                "status": status,
                "latex": latex,
                "docling_latex": decoded or None,
                "pdf_text": str(item.get("orig", "")).strip() or None,
                "source_pdf": source_pdf,
                "page": page,
                "bbox": bbox,
                "source_image": f"images/formula_{position:04d}.png" if page else None,
                "verification_methods": verification_methods,
                "source_verification": source_match,
                "note": note,
            }
        )

    unused = set(paper_overrides) - used_overrides
    if unused:
        raise RuntimeError(f"Unused formula overrides for {paper_id}: {sorted(unused)}")
    return records


def formula_markdown(record: Mapping[str, Any]) -> str:
    attributes = (
        f'id="{record["formula_id"]}" status="{record["status"]}" source-page="{record["page"]}"'
    )
    lines = [f"<!-- formula-start {attributes} -->"]
    if record.get("latex"):
        lines.extend(("$$", str(record["latex"]), "$$"))
    image = record.get("source_image")
    if image:
        lines.append(f"![Source formula {record['formula_id']}]({image})")
    if record["status"] in {"decoded_unverified", "text_layer_fallback"} and record.get("pdf_text"):
        lines.extend(("```text", f"PDF text layer: {record['pdf_text']}", "```"))
    lines.append(
        f"*Formula quality: `{record['status']}`; source PDF page {record['page']}. "
        f"{record['note']}*"
    )
    lines.append("<!-- formula-end -->")
    return "\n".join(lines)


def formula_chunk_text(record: Mapping[str, Any]) -> str:
    attributes = (
        f'id="{record["formula_id"]}" status="{record["status"]}" source-page="{record["page"]}"'
    )
    prefix = (
        f"[Formula {record['formula_id']}; quality={record['status']}; "
        f"source_page={record['page']}]"
    )
    if record.get("latex"):
        body = f"{prefix}\n$${record['latex']}$$"
    else:
        body = f"{prefix}\nPDF text layer: {record.get('pdf_text') or '(empty)'}"
    return f"<!-- formula-start {attributes} -->\n{body}\n<!-- formula-end -->"


def replace_formula_blocks(text: str, records: list[Mapping[str, Any]]) -> str:
    matches = list(FORMULA_BLOCK_PATTERN.finditer(text))
    if len(matches) != len(records):
        raise RuntimeError(
            f"Formula block count mismatch: document has {len(matches)}, records have {len(records)}"
        )
    position = 0

    def replace(_match: re.Match[str]) -> str:
        nonlocal position
        rendered = formula_markdown(records[position])
        position += 1
        return rendered

    return FORMULA_BLOCK_PATTERN.sub(replace, text)


def _repair_chunk_field(
    chunks: list[dict[str, Any]], field: str, records: list[Mapping[str, Any]]
) -> None:
    separator = "\n<!-- formula-repair-chunk-boundary -->\n"
    values = [str(chunk.get(field, "")) for chunk in chunks]
    combined = separator.join(values)
    count = len(FORMULA_BLOCK_PATTERN.findall(combined))
    if count == 0:
        return
    if count != len(records):
        raise RuntimeError(
            f"Formula block count mismatch in chunks.{field}: found {count}, expected {len(records)}"
        )
    position = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal position
        boundaries = match.group(0).count(separator)
        rendered = formula_chunk_text(records[position])
        position += 1
        return rendered + separator * boundaries

    repaired = FORMULA_BLOCK_PATTERN.sub(replace, combined)
    repaired_values = repaired.split(separator)
    if len(repaired_values) != len(chunks):
        raise RuntimeError(f"Chunk boundary count changed while repairing chunks.{field}")
    for chunk, value in zip(chunks, repaired_values, strict=True):
        if isinstance(chunk.get(field), str):
            chunk[field] = value


def repair_chunks(path: Path, records: list[Mapping[str, Any]]) -> None:
    chunks = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    for field in ("text", "raw_text"):
        _repair_chunk_field(chunks, field, records)
    path.write_text(
        "".join(json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in chunks),
        encoding="utf-8",
    )


def crop_formula_images(
    paper_dir: Path, document: Mapping[str, Any], records: list[dict[str, Any]]
) -> int:
    from PIL import Image

    pages = document.get("pages", {})
    images_dir = paper_dir / "images"
    images_dir.mkdir(exist_ok=True)
    for stale in images_dir.glob("formula_*.png"):
        stale.unlink()
    created = 0
    for record in records:
        page_number = record.get("page")
        bbox = record.get("bbox")
        page = pages.get(str(page_number), {})
        page_size = page.get("size", {})
        image_info = page.get("image") or {}
        image_uri = image_info.get("uri")
        if not (page_number and bbox and image_uri and page_size):
            record["source_image"] = None
            continue

        source = paper_dir / str(image_uri)
        destination = images_dir / f"formula_{record['position']:04d}.png"
        with Image.open(source) as image:
            scale_x = image.width / float(page_size["width"])
            scale_y = image.height / float(page_size["height"])
            if bbox.get("coord_origin") == "TOPLEFT":
                top = float(bbox["t"]) * scale_y
                bottom = float(bbox["b"]) * scale_y
            else:
                top = (float(page_size["height"]) - float(bbox["t"])) * scale_y
                bottom = (float(page_size["height"]) - float(bbox["b"])) * scale_y
            margin = 8
            crop_box = (
                max(0, math.floor(float(bbox["l"]) * scale_x) - margin),
                max(0, math.floor(min(top, bottom)) - margin),
                min(image.width, math.ceil(float(bbox["r"]) * scale_x) + margin),
                min(image.height, math.ceil(max(top, bottom)) + margin),
            )
            image.crop(crop_box).save(destination)
        created += 1
    return created


def repair_formula_artifacts(
    paper_dir: Path,
    document: Mapping[str, Any],
    *,
    source_pdf: str,
    overrides: Mapping[str, Mapping[str, Mapping[str, str]]] | None = None,
    source_matches: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, int]:
    resolved_overrides = overrides if overrides is not None else load_overrides()
    records = build_formula_records(
        paper_dir.name,
        document,
        source_pdf=source_pdf,
        overrides=resolved_overrides,
        source_matches=source_matches,
    )
    markdown_path = paper_dir / "document.md"
    markdown = replace_formula_blocks(markdown_path.read_text(encoding="utf-8"), records)
    markdown_path.write_text(markdown.rstrip() + "\n", encoding="utf-8")
    repair_chunks(paper_dir / "chunks.jsonl", records)
    crops = crop_formula_images(paper_dir, document, records)
    (paper_dir / "formulas.jsonl").write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    stats = {
        "total": len(records),
        "docling_decoded": sum(bool(record.get("docling_latex")) for record in records),
        "verified_manual": sum(record["status"] == "verified_manual" for record in records),
        "verified_source": sum(record["status"] == "verified_source" for record in records),
        "verified_source_and_manual": sum(
            record["status"] == "verified_source_and_manual" for record in records
        ),
        "source_verified_total": sum(
            "arxiv_tex" in record["verification_methods"] for record in records
        ),
        "manual_verified_total": sum(
            "manual_pdf" in record["verification_methods"] for record in records
        ),
        "manual_corrected": sum(
            "manual_pdf" in record["verification_methods"] and bool(record.get("docling_latex"))
            for record in records
        ),
        "manual_recovered": sum(
            "manual_pdf" in record["verification_methods"] and not record.get("docling_latex")
            for record in records
        ),
        "source_corrected": sum(
            record["status"] == "verified_source" and bool(record.get("docling_latex"))
            for record in records
        ),
        "source_recovered": sum(
            record["status"] == "verified_source" and not record.get("docling_latex")
            for record in records
        ),
        "decoded_unverified": sum(record["status"] == "decoded_unverified" for record in records),
        "text_layer_fallback": sum(record["status"] == "text_layer_fallback" for record in records),
        "source_crops": crops,
        "latex_blocks": sum(bool(record.get("latex")) for record in records),
    }
    return stats


def repair_corpus(corpus_dir: Path) -> dict[str, int]:
    overrides = load_overrides()
    source_matches = load_source_matches()
    totals = {
        "papers": 0,
        "total": 0,
        "docling_decoded": 0,
        "verified_manual": 0,
        "verified_source": 0,
        "verified_source_and_manual": 0,
        "source_verified_total": 0,
        "manual_verified_total": 0,
        "manual_corrected": 0,
        "manual_recovered": 0,
        "source_corrected": 0,
        "source_recovered": 0,
        "decoded_unverified": 0,
        "text_layer_fallback": 0,
        "source_crops": 0,
        "latex_blocks": 0,
    }
    metadata_by_id: dict[str, dict[str, Any]] = {}
    for paper_dir in sorted(path for path in corpus_dir.iterdir() if path.is_dir()):
        document = json.loads((paper_dir / "document.json").read_text(encoding="utf-8"))
        metadata_path = paper_dir / "metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        stats = repair_formula_artifacts(
            paper_dir,
            document,
            source_pdf=metadata["source"]["path"],
            overrides=overrides,
            source_matches=source_matches,
        )
        metadata["document"]["markdown_chars"] = len(
            (paper_dir / "document.md").read_text(encoding="utf-8")
        )
        metadata["document"]["math_blocks"] = stats["latex_blocks"]
        metadata["formula_quality"] = {
            "overlay": "source-linked-v2",
            **stats,
        }
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        metadata_by_id[paper_dir.name] = metadata
        totals["papers"] += 1
        for key in totals.keys() - {"papers"}:
            totals[key] += stats[key]
    if totals["source_verified_total"] != len(source_matches):
        raise RuntimeError(
            "Formula source match application count mismatch: "
            f"{totals['source_verified_total']} != {len(source_matches)}"
        )

    index_path = corpus_dir / "_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["papers"] = [metadata_by_id[paper["paper_id"]] for paper in index["papers"]]
    index["formula_quality"] = {"overlay": "source-linked-v2", **totals}
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(totals, ensure_ascii=False, indent=2))
    return totals


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair and source-link paper formula outputs.")
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repair_corpus(args.corpus_dir.resolve())


if __name__ == "__main__":
    main()
