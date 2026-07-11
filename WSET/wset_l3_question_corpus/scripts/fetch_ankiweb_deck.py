from __future__ import annotations

import argparse
import html
import json
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from io import BytesIO

import httpx
from bs4 import BeautifulSoup

from wset_corpus.utils import ROOT, sha256_bytes, stable_id

SOURCE_ID = "ankiweb_wset_l3_new"
SHARED_ID = 1521584113
SOURCE_URL = f"https://ankiweb.net/shared/info/{SHARED_ID}"
USER_AGENT = "wset-l3-question-corpus/0.1 private academic research"
EXPECTED_NOTES = 4075


def read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7


def protobuf_fields(data: bytes) -> list[tuple[int, int, int | bytes]]:
    fields: list[tuple[int, int, int | bytes]] = []
    offset = 0
    while offset < len(data):
        tag, offset = read_varint(data, offset)
        number, wire_type = tag >> 3, tag & 7
        if wire_type == 0:
            value, offset = read_varint(data, offset)
        elif wire_type == 2:
            length, offset = read_varint(data, offset)
            value = data[offset : offset + length]
            offset += length
        elif wire_type == 1:
            value = data[offset : offset + 8]
            offset += 8
        elif wire_type == 5:
            value = data[offset : offset + 4]
            offset += 4
        else:
            raise ValueError(f"Unsupported protobuf wire type: {wire_type}")
        fields.append((number, wire_type, value))
    return fields


def item_metadata(payload: bytes) -> tuple[int, str, str]:
    outer = protobuf_fields(payload)
    available = next(value for number, wire, value in outer if number == 1 and wire == 2)
    if not isinstance(available, bytes):
        raise ValueError("Invalid AnkiWeb item-info response")
    deck_payload = next(
        value for number, wire, value in protobuf_fields(available) if number == 10 and wire == 2
    )
    if not isinstance(deck_payload, bytes):
        raise ValueError("AnkiWeb item is not a deck")
    deck = protobuf_fields(deck_payload)
    notes = next(value for number, wire, value in deck if number == 1 and wire == 0)
    key = next(value for number, wire, value in deck if number == 5 and wire == 2)
    title = next(value for number, wire, value in protobuf_fields(available) if number == 5)
    if not isinstance(notes, int) or not isinstance(key, bytes) or not isinstance(title, bytes):
        raise ValueError("Invalid AnkiWeb deck metadata")
    return notes, title.decode("utf-8"), key.decode("utf-8")


def clean_field(value: str) -> str:
    text = BeautifulSoup(html.unescape(value), "lxml").get_text(" ", strip=True)
    return " ".join(text.split())


def select_note_fields(field_names: list[str], parts: list[str]) -> tuple[str, str]:
    values = dict(zip(field_names, parts, strict=False))
    front = values.get("Front", parts[0] if parts else "")
    back = values.get("Back", parts[1] if len(parts) > 1 else "")
    return front, back


def extract_notes(apkg: bytes) -> list[dict[str, object]]:
    with zipfile.ZipFile(BytesIO(apkg)) as archive:
        database_name = next(
            (
                name
                for name in ("collection.anki2", "collection.anki21")
                if name in archive.namelist()
            ),
            None,
        )
        if database_name is None:
            raise ValueError("Unsupported Anki package: collection database not found")
        database = archive.read(database_name)
    with tempfile.NamedTemporaryFile(suffix=".anki2") as temporary:
        temporary.write(database)
        temporary.flush()
        connection = sqlite3.connect(f"file:{temporary.name}?mode=ro", uri=True)
        try:
            models_payload = connection.execute("SELECT models FROM col").fetchone()[0]
            models = json.loads(models_payload)
            rows = connection.execute(
                "SELECT id, mid, flds, tags FROM notes ORDER BY id"
            ).fetchall()
        finally:
            connection.close()
    extracted: list[dict[str, object]] = []
    for note_id, model_id, fields, tags in rows:
        parts = str(fields).split("\x1f")
        model = models.get(str(model_id), {})
        field_names = [str(field.get("name", "")) for field in model.get("flds", [])]
        front_value, back_value = select_note_fields(field_names, parts)
        if not front_value or not back_value:
            continue
        front, back = clean_field(front_value), clean_field(back_value)
        if front and back:
            extracted.append(
                {"id": int(note_id), "front": front, "back": back, "tags": str(tags).split()}
            )
    return extracted


def main(refresh: bool = False) -> None:
    target = ROOT / "data" / "raw_private" / SOURCE_ID / stable_id(SOURCE_URL, prefix="url_")
    cached_page = target / "content.html"
    cached_deck = target / "deck.apkg"
    if not refresh and cached_page.exists() and cached_deck.exists():
        page_content = cached_page.read_bytes()
        deck_content = cached_deck.read_bytes()
        expected_notes = EXPECTED_NOTES
        title = "WSET Level 3 -- NEW"
        status_code = 200
    else:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=60
        ) as client:
            page_response = client.get(SOURCE_URL)
            page_response.raise_for_status()
            info_response = client.get(
                "https://ankiweb.net/svc/shared/item-info", params={"sharedId": SHARED_ID}
            )
            info_response.raise_for_status()
            expected_notes, title, download_key = item_metadata(info_response.content)
            deck_response = client.get(
                f"https://ankiweb.net/svc/shared/download-deck/{SHARED_ID}",
                params={"t": download_key},
            )
            deck_response.raise_for_status()
            page_content = page_response.content
            deck_content = deck_response.content
            status_code = page_response.status_code

    notes = extract_notes(deck_content)
    if expected_notes != len(notes) or len(notes) < 1000:
        raise RuntimeError(f"Expected {expected_notes} notes but extracted {len(notes)}")

    target.mkdir(parents=True, exist_ok=True)
    (target / "content.html").write_bytes(page_content)
    (target / "deck.apkg").write_bytes(deck_content)
    note_content = json.dumps(notes, ensure_ascii=False, indent=2).encode("utf-8")
    (target / "flashcards.json").write_bytes(note_content)
    retrieved_at = datetime.now(UTC).isoformat()
    manifest = {
        "source_id": SOURCE_ID,
        "url": SOURCE_URL,
        "requested_url": SOURCE_URL,
        "filename": "content.html",
        "content_type": "text/html",
        "status_code": status_code,
        "retrieved_at": retrieved_at,
        "sha256": sha256_bytes(page_content),
        "deck": {
            "filename": "deck.apkg",
            "sha256": sha256_bytes(deck_content),
            "content_type": "application/octet-stream",
        },
        "supplemental_files": [
            {
                "filename": "flashcards.json",
                "content_type": "application/json",
                "sha256": sha256_bytes(note_content),
                "retrieved_at": retrieved_at,
                "row_count": len(notes),
                "retrieval_method": "public_ankiweb_shared_deck",
            }
        ],
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    snapshot = {
        "source_id": SOURCE_ID,
        "source_url": SOURCE_URL,
        "shared_id": SHARED_ID,
        "title": title,
        "retrieved_at": retrieved_at,
        "note_count": len(notes),
        "content_hash": sha256_bytes(deck_content),
        "status": "fetched_public_shared_deck",
        "notes": "The short-lived download key was used in memory and was not saved.",
    }
    (ROOT / "data" / "source_snapshots" / f"{SOURCE_ID}.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Fetched and extracted {len(notes)} notes from {title}")


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--refresh", action="store_true")
    main(refresh=argument_parser.parse_args().refresh)
