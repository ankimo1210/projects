from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

from src.utils.sources import CONFIG_DIR, PROJECT_ROOT, load_sources, now_jst_iso, write_sources_bibliography


RAW_DIR = PROJECT_ROOT / "data" / "raw" / "company_ir"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"


SOURCE_IDS_TO_FETCH = [
    "official_ir_top",
    "official_business_overview",
    "official_business_model",
    "official_stock_status",
    "irbank_quote",
    "irbank_results",
    "irbank_balance_sheet",
    "irbank_cash_flow",
    "irbank_segments",
    "tdnet_investigation_20260403",
    "tdnet_results_delay_20260430",
    "tdnet_q3_20260212",
]


def _safe_name(source_id: str, url: str) -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix or ".html"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{source_id}{suffix}")


def fetch_url(source_id: str, url: str) -> dict[str, str]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0 aisan-lbo-case public research bot"}
    filename = _safe_name(source_id, url)
    path = RAW_DIR / filename
    row = {
        "source_id": source_id,
        "url": url,
        "retrieved_at": now_jst_iso(),
        "local_path": str(path.relative_to(PROJECT_ROOT)),
        "status": "pending",
        "content_type": "",
        "error": "",
    }
    try:
        response = requests.get(url, timeout=30, headers=headers)
        row["status"] = str(response.status_code)
        row["content_type"] = response.headers.get("content-type", "")
        response.raise_for_status()
        if "pdf" in row["content_type"].lower() or path.suffix.lower() == ".pdf":
            path.write_bytes(response.content)
        else:
            path.write_text(response.text, encoding=response.encoding or "utf-8")
    except Exception as exc:  # noqa: BLE001
        row["error"] = repr(exc)
        placeholder = path.with_suffix(path.suffix + ".fetch_error.txt")
        placeholder.write_text(f"Fetch failed for {url}\n{row['retrieved_at']}\n{exc!r}\n", encoding="utf-8")
        row["local_path"] = str(placeholder.relative_to(PROJECT_ROOT))
    return row


def extract_ir_links(html_path: Path) -> pd.DataFrame:
    if not html_path.exists() or html_path.suffix != ".html":
        return pd.DataFrame()
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    rows = []
    for a in soup.find_all("a", href=True):
        text = " ".join(a.get_text(" ", strip=True).split())
        href = a["href"]
        if any(token in text for token in ["決算", "調査", "中期", "自動運転", "点群", "WingEarth", "ANIST"]):
            rows.append({"text": text, "href": href})
    return pd.DataFrame(rows).drop_duplicates()


def main() -> None:
    sources = load_sources()
    rows = []
    for source_id in SOURCE_IDS_TO_FETCH:
        source = sources[source_id]
        rows.append(fetch_url(source_id, source["url"]))

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    manifest = pd.DataFrame(rows)
    manifest.to_csv(INTERIM_DIR / "company_ir_fetch_manifest.csv", index=False)

    link_frames = []
    for row in rows:
        local_path = PROJECT_ROOT / row["local_path"]
        links = extract_ir_links(local_path)
        if not links.empty:
            links.insert(0, "source_id", row["source_id"])
            link_frames.append(links)
    if link_frames:
        pd.concat(link_frames, ignore_index=True).to_csv(INTERIM_DIR / "company_ir_links.csv", index=False)

    extra = [
        {
            "source_id": row["source_id"],
            "title": f"Fetched raw file for {row['source_id']}",
            "publisher": "",
            "url": row["url"],
            "source_type": "raw_fetch",
            "retrieved_at": row["retrieved_at"],
            "local_path": row["local_path"],
            "notes": f"HTTP status {row['status']}; {row['error']}",
        }
        for row in rows
    ]
    write_sources_bibliography(extra_rows=extra)


if __name__ == "__main__":
    main()
