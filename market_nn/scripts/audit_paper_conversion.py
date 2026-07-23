#!/usr/bin/env python3
"""Audit converted paper text, structure, images, formulas, and chunk boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HARD_CHUNK_MAX_TOKENS = 512
TOKEN_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)
DEFAULT_THRESHOLDS = {
    "page_token_recall_median": 0.95,
    "page_token_recall_p10": 0.90,
    "page_token_recall_min": 0.60,
    "page_count_mismatches": 0,
    "empty_converted_pages": 0,
    "oversized_chunks": 0,
    "missing_picture_files": 0,
    "missing_formula_crop_files": 0,
    "unverified_or_fallback_formulas": 0,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def normalize_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).lower().replace("\u00ad", "")
    normalized = re.sub(r"-\s*\n\s*", "", normalized)
    return TOKEN_RE.findall(normalized)


def percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a percentile over an empty collection")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def converted_text_by_page(document: dict[str, Any]) -> tuple[dict[int, str], Counter[int]]:
    page_parts: dict[int, list[str]] = defaultdict(list)
    table_counts: Counter[int] = Counter()
    for collection in ("texts", "form_items", "key_value_items"):
        for item in document.get(collection, []):
            text = str(item.get("text") or item.get("orig") or "")
            for provenance in item.get("prov") or []:
                page_parts[int(provenance["page_no"])].append(text)
    for table in document.get("tables", []):
        cells = table.get("data", {}).get("table_cells", [])
        table_text = " ".join(str(cell.get("text") or "") for cell in cells)
        for provenance in table.get("prov") or []:
            page = int(provenance["page_no"])
            page_parts[page].append(table_text)
            table_counts[page] += 1
    return {page: "\n".join(parts) for page, parts in page_parts.items()}, table_counts


def source_page_text(pdf: Path, page: int) -> str:
    result = subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), str(pdf), "-"],
        check=True,
        capture_output=True,
    )
    return result.stdout.decode("utf-8", errors="replace")


def pdf_page_count(pdf: Path) -> int:
    result = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True)
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, flags=re.MULTILINE)
    if not match:
        raise RuntimeError(f"pdfinfo did not report a page count for {pdf}")
    return int(match.group(1))


def summarize_pages(pages: list[dict[str, Any]]) -> dict[str, Any]:
    recalls = [float(page["token_recall"]) for page in pages]
    return {
        "page_count": len(pages),
        "token_recall_mean": round(sum(recalls) / len(recalls), 4),
        "token_recall_median": round(percentile(recalls, 0.5), 4),
        "token_recall_p10": round(percentile(recalls, 0.1), 4),
        "token_recall_min": round(min(recalls), 4),
        "pages_below_0_90": sum(recall < 0.90 for recall in recalls),
        "pages_below_0_80": sum(recall < 0.80 for recall in recalls),
        "empty_converted_pages": sum(page["converted_token_count"] == 0 for page in pages),
    }


def compare_thresholds(actual: dict[str, int | float]) -> list[str]:
    failures: list[str] = []
    minimum_metrics = {
        "page_token_recall_median",
        "page_token_recall_p10",
        "page_token_recall_min",
    }
    for metric, threshold in DEFAULT_THRESHOLDS.items():
        value = actual[metric]
        if metric in minimum_metrics and value < threshold:
            failures.append(f"{metric}={value} is below {threshold}")
        elif metric not in minimum_metrics and value > threshold:
            failures.append(f"{metric}={value} exceeds {threshold}")
    return failures


def audit(project_dir: Path, visual_manifest: Path | None = None) -> dict[str, Any]:
    corpus_dir = project_dir / "corpus" / "papers"
    index_path = corpus_dir / "_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    all_pages: list[dict[str, Any]] = []
    paper_results: list[dict[str, Any]] = []
    page_count_mismatches = 0
    oversized_chunks: list[dict[str, Any]] = []
    picture_total = picture_with_caption = picture_with_annotation = 0
    missing_picture_files: list[str] = []
    missing_formula_crops: list[str] = []
    formula_statuses: Counter[str] = Counter()

    for paper in index["papers"]:
        paper_id = paper["paper_id"]
        paper_dir = corpus_dir / paper_id
        metadata = json.loads((paper_dir / "metadata.json").read_text(encoding="utf-8"))
        document = json.loads((paper_dir / "document.json").read_text(encoding="utf-8"))
        chunks = read_jsonl(paper_dir / "chunks.jsonl")
        formulas = read_jsonl(paper_dir / "formulas.jsonl")
        pdf = project_dir / metadata["source"]["path"]
        if sha256_file(pdf) != metadata["source"]["sha256"]:
            raise RuntimeError(f"Source hash mismatch: {paper_id}")
        actual_pages = pdf_page_count(pdf)
        expected_pages = int(metadata["document"]["pages"])
        page_count_mismatches += int(actual_pages != expected_pages)
        converted_pages, table_counts = converted_text_by_page(document)
        paper_pages: list[dict[str, Any]] = []
        for page in range(1, expected_pages + 1):
            source_tokens = normalize_tokens(source_page_text(pdf, page))
            converted_tokens = normalize_tokens(converted_pages.get(page, ""))
            source_counts = Counter(source_tokens)
            converted_counts = Counter(converted_tokens)
            overlap = sum((source_counts & converted_counts).values())
            recall = overlap / len(source_tokens) if source_tokens else 1.0
            precision = (
                overlap / len(converted_tokens)
                if converted_tokens
                else (1.0 if not source_tokens else 0.0)
            )
            record = {
                "paper_id": paper_id,
                "page": page,
                "source_token_count": len(source_tokens),
                "converted_token_count": len(converted_tokens),
                "overlap_token_count": overlap,
                "token_recall": round(recall, 4),
                "token_precision": round(precision, 4),
                "table_count": table_counts[page],
            }
            paper_pages.append(record)
            all_pages.append(record)

        paper_oversized = [
            {
                "paper_id": paper_id,
                "chunk_id": chunk["chunk_id"],
                "num_tokens": int(chunk.get("num_tokens", 0)),
            }
            for chunk in chunks
            if int(chunk.get("num_tokens", 0)) > HARD_CHUNK_MAX_TOKENS
        ]
        oversized_chunks.extend(paper_oversized)
        for picture in document.get("pictures", []):
            picture_total += 1
            picture_with_caption += int(bool(picture.get("captions")))
            picture_with_annotation += int(bool(picture.get("annotations")))
            image_uri = (picture.get("image") or {}).get("uri")
            if not image_uri or not (paper_dir / image_uri).is_file():
                missing_picture_files.append(f"{paper_id}:{image_uri or '<missing-uri>'}")
        for formula in formulas:
            formula_statuses[str(formula["status"])] += 1
            crop = formula.get("source_image")
            if not crop or not (paper_dir / crop).is_file():
                missing_formula_crops.append(str(formula["formula_id"]))

        paper_results.append(
            {
                "paper_id": paper_id,
                "title": metadata["title"],
                **summarize_pages(paper_pages),
                "tables": len(document.get("tables", [])),
                "pictures": len(document.get("pictures", [])),
                "formulas": len(formulas),
                "chunks": len(chunks),
                "max_chunk_tokens": max(int(chunk.get("num_tokens", 0)) for chunk in chunks),
            }
        )

    page_summary = summarize_pages(all_pages)
    unverified = formula_statuses["decoded_unverified"] + formula_statuses["text_layer_fallback"]
    threshold_actuals: dict[str, int | float] = {
        "page_token_recall_median": page_summary["token_recall_median"],
        "page_token_recall_p10": page_summary["token_recall_p10"],
        "page_token_recall_min": page_summary["token_recall_min"],
        "page_count_mismatches": page_count_mismatches,
        "empty_converted_pages": page_summary["empty_converted_pages"],
        "oversized_chunks": len(oversized_chunks),
        "missing_picture_files": len(missing_picture_files),
        "missing_formula_crop_files": len(missing_formula_crops),
        "unverified_or_fallback_formulas": unverified,
    }
    failures = compare_thresholds(threshold_actuals)
    visual_checks: dict[str, Any] | None = None
    if visual_manifest and visual_manifest.is_file():
        visual_checks = json.loads(visual_manifest.read_text(encoding="utf-8"))

    fingerprint = {
        "corpus_index_sha256": sha256_file(index_path),
        "visual_manifest_sha256": sha256_file(visual_manifest)
        if visual_manifest and visual_manifest.is_file()
        else None,
    }
    return {
        "schema_version": 1,
        "run_id": hashlib.sha256(
            json.dumps(fingerprint, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:16],
        **fingerprint,
        "status": "pass" if not failures else "fail",
        "thresholds": DEFAULT_THRESHOLDS,
        "threshold_actuals": threshold_actuals,
        "threshold_failures": failures,
        "summary": {
            "paper_count": len(paper_results),
            **page_summary,
            "chunk_count": sum(paper["chunks"] for paper in paper_results),
            "table_count": sum(paper["tables"] for paper in paper_results),
            "picture_count": picture_total,
            "pictures_with_caption": picture_with_caption,
            "pictures_without_caption": picture_total - picture_with_caption,
            "pictures_with_machine_annotations": picture_with_annotation,
            "formula_count": sum(formula_statuses.values()),
            "formula_statuses": dict(sorted(formula_statuses.items())),
        },
        "oversized_chunks": oversized_chunks,
        "missing_picture_files": missing_picture_files,
        "missing_formula_crops": missing_formula_crops,
        "lowest_recall_pages": sorted(
            all_pages, key=lambda page: (page["token_recall"], page["paper_id"], page["page"])
        )[:20],
        "papers": paper_results,
        "visual_checks": visual_checks,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    project_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=project_dir)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--visual-manifest",
        type=Path,
        default=project_dir / "manifests" / "paper_conversion_visual_checks.json",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = audit(args.project_dir.resolve(), args.visual_manifest.resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    summary = result["summary"]
    print(
        f"Conversion QA: {result['status']} — "
        f"pages={summary['page_count']}, median recall={summary['token_recall_median']:.1%}, "
        f"p10={summary['token_recall_p10']:.1%}",
        file=sys.stderr,
    )
    return int(result["status"] != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
