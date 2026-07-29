"""Deterministic source-PDF integrity and structure checks."""

from __future__ import annotations

import hashlib
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .schema import PdfStructureCheck

PAGES_RE = re.compile(r"^Pages:\s+(?P<count>\d+)\s*$", re.MULTILINE)
QPDF_ERROR_PAGE_RE = re.compile(r"ERROR:\s+page\s+(?P<page>\d+):", re.IGNORECASE)
XML_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


@dataclass(frozen=True)
class PageProfile:
    """Source-only routing signals for one PDF page."""

    page_number: int
    width: float
    height: float
    word_count: int
    text_characters: int
    replacement_characters: int
    image_count: int
    wide_image_count: int
    route: str
    ocr_language: str
    math_dense: bool
    damaged: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-compatible page profile."""

        return asdict(self)


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of *path*."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pdf_page_count(path: Path) -> int:
    """Read the source page count with Poppler's ``pdfinfo``."""

    result = subprocess.run(
        ["pdfinfo", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdfinfo failed for {path.name} with code {result.returncode}")
    match = PAGES_RE.search(result.stdout)
    if match is None:
        raise RuntimeError(f"pdfinfo did not report pages for {path.name}")
    return int(match.group("count"))


def parse_qpdf_result(return_code: int, output: str) -> PdfStructureCheck:
    """Normalize qpdf's exit code and diagnostic counts."""

    warning_count = sum(1 for line in output.splitlines() if "WARNING:" in line)
    error_count = sum(1 for line in output.splitlines() if "ERROR:" in line)
    if return_code == 0:
        status = "clean"
    elif return_code == 3 and error_count == 0:
        status = "warning"
    else:
        status = "error"
    return PdfStructureCheck(
        status=status,
        return_code=return_code,
        warning_count=warning_count,
        error_count=error_count,
    )


def qpdf_check(path: Path) -> PdfStructureCheck:
    """Run ``qpdf --check`` without modifying the source PDF."""

    try:
        result = subprocess.run(
            ["qpdf", "--check", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return PdfStructureCheck(
            status="unavailable",
            return_code=None,
            warning_count=0,
            error_count=0,
        )
    output = "\n".join((result.stdout, result.stderr))
    return parse_qpdf_result(result.returncode, output)


def qpdf_error_pages(path: Path) -> set[int]:
    """Return source page numbers named in qpdf content errors."""

    try:
        result = subprocess.run(
            ["qpdf", "--check", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return set()
    output = "\n".join((result.stdout, result.stderr))
    return {int(match.group("page")) for match in QPDF_ERROR_PAGE_RE.finditer(output)}


def _pdftotext_page_data(path: Path) -> list[tuple[float, float, list[str]]]:
    result = subprocess.run(
        ["pdftotext", "-bbox-layout", str(path), "-"],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed for {path.name} with code {result.returncode}")
    xml_text = result.stdout.decode("utf-8", errors="replace")
    xml_text = XML_CONTROL_RE.sub("\ufffd", xml_text)
    root = ET.fromstring(xml_text)
    pages: list[tuple[float, float, list[str]]] = []
    for page in root.iter():
        if page.tag.rsplit("}", 1)[-1] != "page":
            continue
        words = [(node.text or "") for node in page.iter() if node.tag.rsplit("}", 1)[-1] == "word"]
        pages.append((float(page.attrib["width"]), float(page.attrib["height"]), words))
    return pages


def _pdfimages_counts(path: Path) -> tuple[Counter[int], Counter[int]]:
    result = subprocess.run(
        ["pdfimages", "-list", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return Counter(), Counter()
    images: Counter[int] = Counter()
    wide_images: Counter[int] = Counter()
    for line in result.stdout.splitlines()[2:]:
        columns = line.split()
        if len(columns) < 5 or not columns[0].isdigit():
            continue
        page_number = int(columns[0])
        width = int(columns[3])
        height = int(columns[4])
        images[page_number] += 1
        if height > 0 and width / height >= 3:
            wide_images[page_number] += 1
    return images, wide_images


def profile_pdf_pages(path: Path, *, ocr_language: str = "eng") -> list[PageProfile]:
    """Profile every source page and choose a deterministic extraction route."""

    page_data = _pdftotext_page_data(path)
    image_counts, wide_image_counts = _pdfimages_counts(path)
    damaged_pages = qpdf_error_pages(path)
    profiles: list[PageProfile] = []
    for page_number, (width, height, words) in enumerate(page_data, start=1):
        text = " ".join(words)
        word_count = len(words)
        image_count = image_counts[page_number]
        wide_image_count = wide_image_counts[page_number]
        damaged = page_number in damaged_pages
        if damaged:
            route = "damaged"
        elif word_count == 0 and image_count:
            route = "scan"
        elif word_count >= 20 and image_count:
            route = "hybrid"
        elif word_count >= 20:
            route = "born_digital"
        else:
            route = "sparse"
        profiles.append(
            PageProfile(
                page_number=page_number,
                width=width,
                height=height,
                word_count=word_count,
                text_characters=len(text),
                replacement_characters=text.count("\ufffd"),
                image_count=image_count,
                wide_image_count=wide_image_count,
                route=route,
                ocr_language=ocr_language,
                math_dense=wide_image_count >= 3,
                damaged=damaged,
            )
        )
    return profiles


def profile_summary(profiles: list[PageProfile]) -> dict[str, Any]:
    """Aggregate page profiles without losing per-page evidence."""

    routes = Counter(profile.route for profile in profiles)
    return {
        "page_count": len(profiles),
        "route_counts": dict(sorted(routes.items())),
        "math_dense_pages": sum(profile.math_dense for profile in profiles),
        "damaged_pages": [profile.page_number for profile in profiles if profile.damaged],
        "word_count": sum(profile.word_count for profile in profiles),
        "image_count": sum(profile.image_count for profile in profiles),
    }
