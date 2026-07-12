from __future__ import annotations

import json
import re
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup

from wset_corpus.utils import ROOT, sha256_bytes

SOURCE_ID = "portnwine_l3_quiz"


def main() -> None:
    manifests = sorted((ROOT / "data" / "raw_private" / SOURCE_ID).rglob("manifest.json"))
    if not manifests:
        raise RuntimeError("Fetch the public PortnWine page before its dynamic payload")
    manifest_path = manifests[0]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    page = (manifest_path.parent / manifest["filename"]).read_text(
        encoding="utf-8", errors="replace"
    )
    soup = BeautifulSoup(page, "lxml")
    script = next(
        (
            element.string or element.get_text() or ""
            for element in soup.find_all("script")
            if "SUPABASE_URL" in (element.string or element.get_text() or "")
        ),
        "",
    )
    endpoint_match = re.search(r"SUPABASE_URL\s*=\s*'([^']+)'", script)
    key_match = re.search(r"SUPABASE_ANON_KEY\s*=\s*'([^']+)'", script)
    level_match = re.search(r"\bLEVEL\s*=\s*'([^']+)'", script)
    if not endpoint_match or not key_match or not level_match:
        raise RuntimeError("Public frontend configuration was not found")
    endpoint, public_key, level = (
        endpoint_match.group(1),
        key_match.group(1),
        level_match.group(1),
    )
    response = httpx.get(
        f"{endpoint}/rest/v1/questions",
        params={"level": f"eq.{level}", "select": "*"},
        headers={
            "apikey": public_key,
            "Authorization": f"Bearer {public_key}",
            "User-Agent": "wset-l3-question-corpus/0.1 private research",
        },
        timeout=30,
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("Unexpected public question payload")
    required = {"question", "options", "correct_index", "explanation", "level"}
    if any(not required.issubset(row) or row.get("level") != level for row in rows):
        raise RuntimeError("Public payload failed schema or level validation")

    content = json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8")
    filename = "dynamic_questions.json"
    (manifest_path.parent / filename).write_bytes(content)
    retrieved_at = datetime.now(UTC).isoformat()
    supplement = {
        "filename": filename,
        "content_type": "application/json",
        "sha256": sha256_bytes(content),
        "retrieved_at": retrieved_at,
        "row_count": len(rows),
        "retrieval_method": "same_public_frontend_endpoint",
    }
    manifest["supplemental_files"] = [supplement]
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    snapshot = {
        "source_id": SOURCE_ID,
        "source_url": manifest["url"],
        "retrieved_at": retrieved_at,
        "row_count": len(rows),
        "content_hash": supplement["sha256"],
        "status": "fetched_public_frontend_payload",
        "notes": "Public anonymous client configuration was used in memory; its key was not saved.",
    }
    (ROOT / "data" / "source_snapshots" / f"{SOURCE_ID}_dynamic.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Fetched {len(rows)} public Level 3 rows")


if __name__ == "__main__":
    main()
