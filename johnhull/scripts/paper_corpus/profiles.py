"""Build the tracked page-routing profile for every source paper."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .baseline import REFERENCES_ROOT
from .preflight import profile_pdf_pages, profile_summary, sha256_file

DEFAULT_OUTPUT = REFERENCES_ROOT / "corpus_preflight.json"
LANGUAGE_OVERRIDES = {
    "1900-bachelier-theorie-de-la-speculation": "fra",
}


def build_profiles(references_root: Path = REFERENCES_ROOT) -> dict[str, Any]:
    """Return deterministic source-page classifications for the corpus."""

    papers: list[dict[str, Any]] = []
    route_counts: Counter[str] = Counter()
    for pdf_path in sorted((references_root / "papers").glob("*.pdf")):
        paper_id = pdf_path.stem
        language = LANGUAGE_OVERRIDES.get(paper_id, "eng")
        profiles = profile_pdf_pages(pdf_path, ocr_language=language)
        summary = profile_summary(profiles)
        route_counts.update(summary["route_counts"])
        papers.append(
            {
                "paper_id": paper_id,
                "source_pdf_sha256": sha256_file(pdf_path),
                "ocr_language": language,
                "summary": summary,
                "pages": [profile.to_dict() for profile in profiles],
            }
        )
    return {
        "profile_version": "1.0.0",
        "paper_count": len(papers),
        "page_count": sum(item["summary"]["page_count"] for item in papers),
        "route_counts": dict(sorted(route_counts.items())),
        "papers": papers,
    }


def render_profiles(manifest: dict[str, Any]) -> str:
    """Serialize page profiles in stable repository format."""

    return json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
