"""
generate_site_schema.py
複数のサンプルURLから LLM を使ってサイト固有の抽出スキーマを生成し
data/site_schemas/{platform}.md に保存する。

使い方:
    python generate_site_schema.py --platform rakumachi
    python generate_site_schema.py --platform kenbiya
    python generate_site_schema.py  # 両方
"""

import argparse
import json
import re
import textwrap
from pathlib import Path

import requests
from config import get_logger
from property_scraper import (
    _OLLAMA_BASE_URL,
    _OLLAMA_MODEL,
    _strip_html_to_text,
    fetch_property_html,
)

logger = get_logger(__name__)

SCHEMA_DIR = Path(__file__).parent / "data" / "site_schemas"
SCHEMA_DIR.mkdir(parents=True, exist_ok=True)

# ── サンプルURL ──────────────────────────────────────────────────────
SAMPLE_URLS: dict[str, list[str]] = {
    "rakumachi": [
        "https://www.rakumachi.jp/syuuekibukken/kanto/tokyo/dim2001/3487079/show.html?device_type=pc",
        "https://www.rakumachi.jp/syuuekibukken/kyushu/okinawa/dim1002/3600711/show.html",
        "https://www.rakumachi.jp/syuuekibukken/kyushu/okinawa/dim1003/3598311/show.html",
    ],
    "kenbiya": [
        "https://www.kenbiya.com/pp8/s/tokyo/setagaya-ku/re_4451615ylb/",
        "https://www.kenbiya.com/pp1/s/tokyo/nerima-ku/re_4451593j9w/",
        "https://www.kenbiya.com/pp11/f/okinawa/etc/re_44475143fe/",
    ],
}

# ── スキーマ生成プロンプト ────────────────────────────────────────────
_SCHEMA_SYSTEM = "You are a web scraping data analyst. Output only valid JSON."

_SCHEMA_USER_TEMPLATE = textwrap.dedent("""\
    Analyze these {n} plain-text samples from Japanese real estate site "{platform}".

    Return JSON in this exact format:
    {{"schema": [
      {{"field": "asking_price_yen", "labels": ["販売価格"], "pattern": "販売価格\\\\n7980万円", "example": "79800000", "conversion": "N万円 x10000"}},
      ...more fields...
    ]}}

    Fields to find (skip only if absent from ALL samples):
    asking_price_yen, gross_yield_pct, gross_rent_monthly_yen, gross_rent_annual_yen,
    address, nearest_station, station_walk_min, build_year_month, age_years,
    structure, property_type, building_area_sqm, land_area_sqm, land_rights,
    num_units, floor_plan, transaction_type, listing_date

    ---
    {samples_text}
""")


def _schema_json_to_markdown(platform: str, fields: list, notes: str = "") -> str:
    lines = [
        f"## {platform} extraction schema\n",
        "| Field | Japanese label(s) | Pattern | Example | Conversion |",
        "|-------|-------------------|---------|---------|------------|",
    ]
    for f in fields:
        if not isinstance(f, dict):
            continue
        labels = ", ".join(f.get("labels", []))
        pattern = str(f.get("pattern", "")).replace("|", "\\|")
        example = str(f.get("example", "")).replace("|", "\\|")
        conversion = str(f.get("conversion", "")).replace("|", "\\|")
        lines.append(
            f"| `{f.get('field', '')}` | {labels} | `{pattern}` | {example} | {conversion} |"
        )
    if notes:
        lines += ["\n## Notes\n", notes]
    return "\n".join(lines)


def _call_ollama(prompt: str) -> str:
    resp = requests.post(
        f"{_OLLAMA_BASE_URL}/api/generate",
        json={
            "model": _OLLAMA_MODEL,
            "prompt": f"{_SCHEMA_SYSTEM}\n\n{prompt}",
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 4096},
        },
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def generate_schema(platform: str) -> Path:
    """サンプルURLを取得し LLM でスキーマを生成、Markdown ファイルに保存する。"""
    urls = SAMPLE_URLS.get(platform, [])
    if not urls:
        raise ValueError(f"No sample URLs for platform: {platform}")

    print(f"[{platform}] {len(urls)} サンプルを取得中...")
    samples: list[str] = []
    for i, url in enumerate(urls, 1):
        try:
            html = fetch_property_html(url)
            text = _strip_html_to_text(html, max_chars=1500, platform=platform)
            samples.append(f"=== Sample {i}: {url} ===\n{text}")
            print(f"  {i}/{len(urls)} 取得完了")
        except Exception as e:
            print(f"  {i}/{len(urls)} 取得失敗: {e}")

    if not samples:
        raise RuntimeError(f"全サンプルの取得に失敗しました ({platform})")

    samples_text = "\n\n".join(samples)
    prompt = _SCHEMA_USER_TEMPLATE.format(
        n=len(samples),
        platform=platform,
        samples_text=samples_text,
    )

    print(f"[{platform}] LLM でスキーマ生成中...")
    raw = _call_ollama(prompt)

    # JSON パース（{"schema": [...]} 形式）
    raw = re.sub(r"^```(?:json)?\n?|```$", "", raw.strip())
    parsed = json.loads(raw)
    if isinstance(parsed, list):
        fields = parsed
    elif isinstance(parsed, dict):
        # {"schema": [...]} or {"fields": [...]} or first list value
        for key in ("schema", "fields", "data", "items"):
            if key in parsed and isinstance(parsed[key], list):
                fields = parsed[key]
                break
        else:
            fields = next((v for v in parsed.values() if isinstance(v, list)), [])

    schema_md = _schema_json_to_markdown(platform, fields)
    header = f"# {platform} 物件データ抽出スキーマ\n\n_自動生成: generate_site_schema.py_\n\n"
    full_md = header + schema_md

    out_path = SCHEMA_DIR / f"{platform}.md"
    out_path.write_text(full_md, encoding="utf-8")
    print(f"[{platform}] 保存完了: {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["rakumachi", "kenbiya", "all"], default="all")
    args = parser.parse_args()

    targets = list(SAMPLE_URLS.keys()) if args.platform == "all" else [args.platform]
    for p in targets:
        try:
            path = generate_schema(p)
            print(f"  → {path}\n")
        except Exception as e:
            print(f"  ERROR [{p}]: {e}\n")
