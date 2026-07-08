#!/usr/bin/env python3
"""Translate OCR pages with Ollama and build a full Japanese report."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_TEXT = ROOT / "raw_text"
PAGE_IMAGES = ROOT / "assets" / "page_images"
TRANSLATIONS = ROOT / "translations_ja"
REPORT_MD = ROOT / "full_report_ja.md"
HTML_DIR = ROOT / "html_textbook"
REPORT_HTML = HTML_DIR / "full_report_ja.html"
PAGE_COUNT = 136
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


@dataclass(frozen=True)
class TocEntry:
    number: str
    english: str
    japanese: str
    page: int


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_toc() -> list[TocEntry]:
    entries: list[TocEntry] = []
    toc_path = ROOT / "TOC_JA.md"
    if not toc_path.exists():
        return entries

    for raw_line in read_text(toc_path).splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 4 or cells[0] in {"Section", "---:"}:
            continue
        if not re.fullmatch(r"\d+(?:\.\d+)?", cells[0]):
            continue
        try:
            page = int(cells[3])
        except ValueError:
            continue
        entries.append(TocEntry(cells[0], cells[1], cells[2], page))
    return entries


def glossary_text(toc_entries: list[TocEntry]) -> str:
    pairs = [
        ("Confidential", "機密"),
        ("Executive Summary", "エグゼクティブサマリー"),
        ("Model Purpose and Intended Use", "モデルの目的と想定用途"),
        ("Model Description Summary", "モデル概要"),
        ("Business and Algo Description", "ビジネスおよびアルゴリズム説明"),
        ("Autohedger", "Autohedger"),
        ("Portfolio Risk", "ポートフォリオリスク"),
        ("Inputs and Outputs Volume", "入出力量"),
        ("Opt-Var Principle", "Opt-Varの原理"),
        ("Model Description", "モデル説明"),
        ("Model Testing", "モデルテスト"),
        ("Sensitivity Analysis", "感応度分析"),
        ("Benchmarking", "ベンチマーキング"),
        ("Backtesting", "バックテスト"),
        ("yield curve", "利回り曲線"),
        ("liquid instrument", "流動性のある商品"),
        ("illiquid instrument", "流動性の低い商品"),
        ("government bond", "国債"),
        ("hedge", "ヘッジ"),
        ("target hedge", "目標ヘッジ"),
        ("portfolio variance", "ポートフォリオ分散"),
        ("covariance matrix", "共分散行列"),
        ("risk-aversion parameter", "リスク回避パラメータ"),
        ("bucket risk limit", "バケットリスク限度"),
        ("box constraints", "ボックス制約"),
        ("inventory", "在庫"),
        ("PV01", "PV01"),
        ("MRM", "MRM"),
        ("SDLC", "SDLC"),
    ]
    seen = {english for english, _ in pairs}
    for entry in toc_entries:
        if entry.english and entry.english not in seen:
            pairs.append((entry.english, entry.japanese))
            seen.add(entry.english)
    return "\n".join(f"- {english} => {japanese}" for english, japanese in pairs)


def split_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    blocks = re.split(r"(\n\s*\n)", text)

    for block in blocks:
        if not block:
            continue
        if current_len + len(block) <= limit:
            current.append(block)
            current_len += len(block)
            continue

        if current:
            chunks.append("".join(current).strip())
            current = []
            current_len = 0

        if len(block) <= limit:
            current.append(block)
            current_len = len(block)
            continue

        lines = block.splitlines(keepends=True)
        for line in lines:
            if current_len + len(line) > limit and current:
                chunks.append("".join(current).strip())
                current = []
                current_len = 0
            if len(line) <= limit:
                current.append(line)
                current_len += len(line)
            else:
                for index in range(0, len(line), limit):
                    part = line[index : index + limit]
                    if current:
                        chunks.append("".join(current).strip())
                        current = []
                        current_len = 0
                    chunks.append(part.strip())

    if current:
        chunks.append("".join(current).strip())
    return [chunk for chunk in chunks if chunk]


def build_prompt(page: int, chunk_index: int, chunk_count: int, text: str, glossary: str) -> str:
    return f"""You are translating OCR text from a technical financial model document into Japanese.

Requirements:
- Translate every visible English sentence into natural Japanese.
- Do not summarize. Do not omit content.
- Preserve section numbers, page numbers, model IDs, version numbers, dates, figure/table numbers, formulas, variables, code identifiers, branch/release strings, system names, and proper nouns.
- Keep mathematical expressions and OCR-unclear fragments as close to the original as possible when uncertain.
- Keep table-like layouts readable; translation can be prose if table structure is too noisy.
- Use the glossary exactly when a matching heading or term appears.
- Output Japanese only. Do not add translator commentary.

Glossary:
{glossary}

OCR text from page {page:03d}, chunk {chunk_index}/{chunk_count}:
```text
{text}
```"""


def call_ollama(model: str, prompt: str, timeout: int, retries: int) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_p": 0.9,
            "num_ctx": 16384,
        },
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request = urllib.request.Request(
            OLLAMA_URL,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            result = body.get("response", "").strip()
            if result:
                return result
            raise RuntimeError("Ollama returned an empty response")
        except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(3 * attempt)
    raise RuntimeError(f"Ollama translation failed: {last_error}")


def translation_path(page: int) -> Path:
    return TRANSLATIONS / f"page_{page:03d}_ja.md"


def translate_page(
    page: int,
    model: str,
    glossary: str,
    force: bool,
    chunk_limit: int,
    timeout: int,
    retries: int,
) -> None:
    output = translation_path(page)
    if output.exists() and not force:
        print(f"skip page {page:03d}: {output.relative_to(ROOT)} already exists", flush=True)
        return

    source = read_text(RAW_TEXT / f"page_{page:03d}.txt").strip()
    chunks = split_text(source, chunk_limit)
    translated_chunks: list[str] = []

    for index, chunk in enumerate(chunks, start=1):
        print(f"translate page {page:03d} chunk {index}/{len(chunks)} ({len(chunk)} chars)", flush=True)
        prompt = build_prompt(page, index, len(chunks), chunk, glossary)
        translated_chunks.append(call_ollama(model, prompt, timeout, retries))

    content = "\n\n".join(translated_chunks).strip()
    write_text(output, content + "\n")


def toc_markdown(entries: list[TocEntry]) -> str:
    if not entries:
        return ""
    lines = [
        "## 目次",
        "",
        "| 節 | 日本語 | 原文 | PDFページ |",
        "|---:|---|---|---:|",
    ]
    for entry in entries:
        lines.append(f"| {entry.number} | {entry.japanese} | {entry.english} | {entry.page} |")
    return "\n".join(lines)


def build_report_md(entries: list[TocEntry]) -> None:
    header = f"""# Opt-Var 全文日本語訳レポート

このレポートは、`raw_text/page_XXX.txt` のOCRテキストをページ単位で全文日本語訳したものです。
数式、表、図、脚注、番号はOCRで崩れている可能性があるため、厳密確認には各ページ画像を正本として参照してください。

{toc_markdown(entries)}

---
"""
    parts = [header.rstrip(), ""]
    for page in range(1, PAGE_COUNT + 1):
        translation = read_text(translation_path(page)).strip()
        parts.extend(
            [
                f"# ページ {page:03d}",
                "",
                f"![ページ {page:03d}](assets/page_images/page-{page:03d}.jpg)",
                "",
                "## 日本語訳",
                "",
                translation,
                "",
                "---",
                "",
            ]
        )
    write_text(REPORT_MD, "\n".join(parts).rstrip() + "\n")


def paragraph_html(markdown: str) -> str:
    lines = markdown.splitlines()
    parts: list[str] = []
    para: list[str] = []
    in_table = False
    table_lines: list[str] = []

    def flush_para() -> None:
        if para:
            text = "\n".join(para).strip()
            parts.append(f"<p>{html.escape(text).replace(chr(10), '<br>')}</p>")
            para.clear()

    def flush_table() -> None:
        nonlocal in_table
        if not table_lines:
            return
        rows = []
        for line in table_lines:
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                continue
            rows.append(cells)
        if rows:
            html_rows = []
            for row_index, row in enumerate(rows):
                tag = "th" if row_index == 0 else "td"
                html_rows.append(
                    "<tr>"
                    + "".join(f"<{tag}>{html.escape(cell)}</{tag}>" for cell in row)
                    + "</tr>"
                )
            parts.append('<div class="table-wrap"><table>' + "".join(html_rows) + "</table></div>")
        table_lines.clear()
        in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            flush_para()
            in_table = True
            table_lines.append(line)
            continue
        if in_table:
            flush_table()
        if not stripped:
            flush_para()
            continue
        if stripped.startswith("# "):
            flush_para()
            parts.append(f"<h1>{html.escape(stripped[2:].strip())}</h1>")
        elif stripped.startswith("## "):
            flush_para()
            parts.append(f"<h2>{html.escape(stripped[3:].strip())}</h2>")
        elif stripped.startswith("### "):
            flush_para()
            parts.append(f"<h3>{html.escape(stripped[4:].strip())}</h3>")
        elif stripped.startswith("- "):
            flush_para()
            parts.append(f"<p>{html.escape(stripped)}</p>")
        else:
            para.append(line)
    if in_table:
        flush_table()
    flush_para()
    return "\n".join(parts)


def build_report_html(entries: list[TocEntry]) -> None:
    if PAGE_IMAGES.exists():
        target_images = HTML_DIR / "assets" / "page_images"
        target_images.mkdir(parents=True, exist_ok=True)
        for image in sorted(PAGE_IMAGES.glob("page-*.jpg")):
            target = target_images / image.name
            if not target.exists() or image.stat().st_mtime > target.stat().st_mtime:
                shutil.copy2(image, target)

    styles_href = "assets/styles.css"
    if not (HTML_DIR / "assets" / "styles.css").exists():
        write_text(HTML_DIR / "assets" / "styles.css", BASIC_CSS)

    toc_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(entry.number)}</td>"
        f"<td>{html.escape(entry.japanese)}</td>"
        f"<td>{html.escape(entry.english)}</td>"
        f"<td>{entry.page}</td>"
        "</tr>"
        for entry in entries
    )
    page_nav = "".join(
        f'<a href="#page-{page:03d}">{page:03d}</a>' for page in range(1, PAGE_COUNT + 1)
    )
    pages_html: list[str] = []
    for page in range(1, PAGE_COUNT + 1):
        translation = read_text(translation_path(page)).strip()
        pages_html.append(
            f"""
<article class="page-article" id="page-{page:03d}">
  <header class="page-header">
    <p class="eyebrow">全文日本語訳</p>
    <h2>ページ {page:03d}</h2>
  </header>
  <figure class="page-image">
    <a href="assets/page_images/page-{page:03d}.jpg"><img src="assets/page_images/page-{page:03d}.jpg" alt="ページ {page:03d} の原本画像" loading="lazy"></a>
  </figure>
  <section class="translated-page">
    <h3>日本語訳</h3>
    {paragraph_html(translation)}
  </section>
</article>
"""
        )

    document = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Opt-Var 全文日本語訳レポート</title>
  <link rel="stylesheet" href="{styles_href}">
</head>
<body>
  <main class="content full-report">
    <nav class="breadcrumb"><a href="index.html">HTMLテキストブック</a><span>/</span><span>全文日本語訳レポート</span></nav>
    <section class="hero">
      <div>
        <p class="eyebrow">OCR全文翻訳ドラフト</p>
        <h1>Opt-Var 全文日本語訳レポート</h1>
        <p class="lead">全136ページのOCR本文を日本語訳し、ページ画像と対応させたフルレポートです。数式・表・図はページ画像を正本として確認してください。</p>
      </div>
    </section>
    <section class="notice">
      <h2>精度上の注意</h2>
      <p>この訳文はOCRテキストを翻訳したものです。OCR誤読が含まれる箇所では訳文も影響を受けるため、モデル仕様・数式・表の厳密確認には画像を参照してください。</p>
    </section>
    <section>
      <h2>目次</h2>
      <div class="table-wrap"><table><thead><tr><th>節</th><th>日本語</th><th>原文</th><th>PDFページ</th></tr></thead><tbody>{toc_rows}</tbody></table></div>
    </section>
    <section>
      <h2>ページ一覧</h2>
      <div class="page-grid">{page_nav}</div>
    </section>
    {"".join(pages_html)}
  </main>
</body>
</html>
"""
    write_text(REPORT_HTML, document)


def verify_translations(start: int, end: int) -> None:
    missing = [page for page in range(start, end + 1) if not translation_path(page).exists()]
    if missing:
        raise RuntimeError(f"missing translations: {missing[:20]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:7b", help="Ollama model name")
    parser.add_argument("--start", type=int, default=1, help="first page to translate")
    parser.add_argument("--end", type=int, default=PAGE_COUNT, help="last page to translate")
    parser.add_argument("--force", action="store_true", help="retranslate existing page files")
    parser.add_argument("--chunk-limit", type=int, default=5200, help="maximum OCR chars per translation chunk")
    parser.add_argument("--timeout", type=int, default=480, help="seconds per Ollama request")
    parser.add_argument("--retries", type=int, default=2, help="Ollama retries per chunk")
    parser.add_argument("--report-only", action="store_true", help="skip translation and only rebuild report outputs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.start < 1 or args.end > PAGE_COUNT or args.start > args.end:
        print(f"invalid page range: {args.start}-{args.end}", file=sys.stderr)
        return 2

    toc_entries = parse_toc()
    glossary = glossary_text(toc_entries)

    if not args.report_only:
        for page in range(args.start, args.end + 1):
            translate_page(
                page,
                args.model,
                glossary,
                args.force,
                args.chunk_limit,
                args.timeout,
                args.retries,
            )

    verify_translations(1, PAGE_COUNT)
    build_report_md(toc_entries)
    build_report_html(toc_entries)
    print(f"wrote {REPORT_MD.relative_to(ROOT)}", flush=True)
    print(f"wrote {REPORT_HTML.relative_to(ROOT)}", flush=True)
    return 0


BASIC_CSS = textwrap.dedent(
    """
    body { margin: 0; font-family: system-ui, sans-serif; background: #f7f8f8; color: #1b1f23; line-height: 1.7; }
    .content { width: min(1180px, 100%); margin: 0 auto; padding: 30px clamp(18px, 4vw, 52px) 70px; }
    .hero, .notice, .page-article { background: #fff; border: 1px solid #d8dddf; border-radius: 8px; padding: 18px; margin: 18px 0; }
    .lead, .eyebrow { color: #5d666f; }
    .page-image { margin: 0 -18px; padding: 14px; background: #f2f5f5; border-top: 1px solid #d8dddf; border-bottom: 1px solid #d8dddf; }
    .page-image img { display: block; max-width: 100%; height: auto; margin: 0 auto; border: 1px solid #d8dddf; background: #fff; }
    .translated-page { padding-top: 12px; }
    .table-wrap { overflow-x: auto; margin: 14px 0; }
    table { width: 100%; border-collapse: collapse; background: #fff; }
    th, td { border: 1px solid #d8dddf; padding: 8px 10px; text-align: left; vertical-align: top; }
    th { background: #eef2f2; }
    .page-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(52px, 1fr)); gap: 6px; }
    .page-grid a { display: grid; place-items: center; min-height: 34px; border: 1px solid #d8dddf; border-radius: 8px; background: #fff; color: #04636d; text-decoration: none; }
    .breadcrumb { display: flex; gap: 8px; flex-wrap: wrap; color: #5d666f; }
    .breadcrumb a { color: #04636d; }
    """
).strip()


if __name__ == "__main__":
    raise SystemExit(main())
