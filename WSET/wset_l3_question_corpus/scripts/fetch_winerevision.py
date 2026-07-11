from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import chompjs
import httpx

from wset_corpus.utils import ROOT, sha256_bytes, stable_id

SOURCE_ID = "winerevision_public"
SOURCE_URL = "https://winerevision.com/"
USER_AGENT = "wset-l3-question-corpus/0.1 private academic research"


def balanced_arrays(script: str) -> list[str]:
    arrays: list[str] = []
    for match in re.finditer(r"=\s*\[\s*\{", script):
        start = match.end() - 2
        depth = 0
        quote: str | None = None
        escaped = False
        for index in range(start, len(script)):
            char = script[index]
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in {'"', "'", "`"}:
                quote = char
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
                if depth == 0:
                    arrays.append(script[start : index + 1])
                    break
    return arrays


def walk(value: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if isinstance(value, dict):
        rows.append(value)
        for child in value.values():
            rows.extend(walk(child))
    elif isinstance(value, list):
        for child in value:
            rows.extend(walk(child))
    return rows


def extract_rows(script: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    questions: dict[tuple[object, object], dict[str, object]] = {}
    flashcards: dict[tuple[object, object], dict[str, object]] = {}
    for candidate in balanced_arrays(script):
        try:
            parsed = chompjs.parse_js_object(candidate)
        except ValueError:
            continue
        for row in walk(parsed):
            if (
                isinstance(row.get("question"), str)
                and isinstance(row.get("options"), list)
                and isinstance(row.get("correctAnswer"), int)
            ):
                questions[(row.get("id"), row["question"])] = row
            if isinstance(row.get("front"), str) and isinstance(row.get("back"), str):
                flashcards[(row.get("id"), row["front"])] = row
    return list(questions.values()), list(flashcards.values())


def write_json(path: Path, rows: list[dict[str, object]]) -> dict[str, object]:
    content = json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(content)
    return {
        "filename": path.name,
        "content_type": "application/json",
        "sha256": sha256_bytes(content),
        "row_count": len(rows),
        "retrieval_method": "public_static_javascript_bundle",
    }


def main() -> None:
    with httpx.Client(
        headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=30
    ) as client:
        homepage_response = client.get(SOURCE_URL)
        homepage_response.raise_for_status()
        asset_match = re.search(r'<script[^>]+src="([^"]+index-[^"]+\.js)"', homepage_response.text)
        if not asset_match:
            raise RuntimeError("WineRevision application bundle was not found")
        bundle_url = urljoin(str(homepage_response.url), asset_match.group(1))
        bundle_response = client.get(bundle_url)
        bundle_response.raise_for_status()

    questions, flashcards = extract_rows(bundle_response.text)
    if len(questions) < 300 or len(flashcards) < 300:
        raise RuntimeError(
            "Unexpected extraction counts: "
            f"{len(questions)} questions, {len(flashcards)} flashcards"
        )

    target = ROOT / "data" / "raw_private" / SOURCE_ID / stable_id(SOURCE_URL, prefix="url_")
    target.mkdir(parents=True, exist_ok=True)
    (target / "content.html").write_bytes(homepage_response.content)
    (target / "bundle.js").write_bytes(bundle_response.content)
    retrieved_at = datetime.now(UTC).isoformat()
    supplemental = [
        write_json(target / "questions.json", questions),
        write_json(target / "flashcards.json", flashcards),
    ]
    for item in supplemental:
        item["retrieved_at"] = retrieved_at
    manifest = {
        "source_id": SOURCE_ID,
        "url": str(homepage_response.url),
        "requested_url": SOURCE_URL,
        "filename": "content.html",
        "content_type": "text/html",
        "status_code": homepage_response.status_code,
        "retrieved_at": retrieved_at,
        "sha256": sha256_bytes(homepage_response.content),
        "bundle": {
            "filename": "bundle.js",
            "url": bundle_url,
            "sha256": sha256_bytes(bundle_response.content),
        },
        "supplemental_files": supplemental,
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    snapshot = {
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "bundle_url": bundle_url,
        "retrieved_at": retrieved_at,
        "question_count": len(questions),
        "flashcard_count": len(flashcards),
        "content_hash": sha256_bytes(bundle_response.content),
        "status": "fetched_public_static_bundle",
    }
    snapshot_path = ROOT / "data" / "source_snapshots" / f"{SOURCE_ID}_dynamic.json"
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Fetched {len(questions)} questions and {len(flashcards)} flashcards")


if __name__ == "__main__":
    main()
