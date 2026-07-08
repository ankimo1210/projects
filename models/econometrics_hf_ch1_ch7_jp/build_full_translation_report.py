#!/usr/bin/env python3
"""Build a full Japanese translation report for chapters 1-7 using Ollama."""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_DIR / "econometrics_hf_ch1_ch7_markdown_ja"
RAW_DIR = SOURCE_DIR / "raw_text"
OUT_DIR = PROJECT_DIR / "full_translation_report_ja"
CACHE_DIR = OUT_DIR / "translation_cache"
CHAPTER_DIR = OUT_DIR / "chapters"
REPORT_MD = OUT_DIR / "full_translation_report_ja.md"
REPORT_HTML = OUT_DIR / "full_translation_report_ja.html"
MANIFEST = OUT_DIR / "manifest.json"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


DEFAULT_MODEL = "gemma3:12b"
FAST_MODEL = "qwen2.5:7b"


GLOSSARY = """
Motivation=動機
high-frequency data=高頻度データ
high-frequency econometrics=高頻度計量経済学
financial econometrics=金融計量経済学
market microstructure=市場マイクロストラクチャー
intraday=日中
trade execution=取引執行
order placement=注文配置
order submission=注文発注
order book=注文板
limit order book=指値注文板
liquidity=流動性
volatility=ボラティリティ
duration=デュレーション
event time=イベント時刻
calendar time=カレンダー時刻
point process=点過程
counting process=計数過程
intensity=強度
integrated intensity=積分強度
compensator=補償過程
hazard=ハザード
Multiplicative Error Model (MEM)=乗法誤差モデル（MEM）
Autoregressive Conditional Duration (ACD)=自己回帰条件付きデュレーション（ACD）
Generalized Multiplicative Error Model=一般化乗法誤差モデル
Vector Multiplicative Error Model=ベクトル乗法誤差モデル
Autoregressive Conditional Poisson (ACP)=自己回帰条件付きポアソン（ACP）
Electronic Communication Network (ECN)=電子通信ネットワーク（ECN）
bid-ask spread=ビッド・アスク・スプレッド
market depth=市場深度
order flow=注文フロー
quote=気配
transaction=取引
trade-to-trade duration=取引間デュレーション
price duration=価格デュレーション
volume duration=出来高デュレーション
limit order=指値注文
market order=成行注文
Quasi Maximum Likelihood=疑似最尤
Maximum Likelihood=最尤
Lagrange Multiplier=ラグランジュ乗数
long range dependence=長期依存性
long memory=長記憶
seasonality=季節性
intradaily periodicity=日中周期性
latent factor=潜在因子
factor model=因子モデル
"""


PROMPT_TEMPLATE = """You are translating an econometrics textbook excerpt from English to Japanese.

Use these fixed terminology choices when applicable:
{glossary}

Requirements:
- Translate every English prose sentence into natural academic Japanese.
- Do not summarize, compress, or omit content.
- Preserve section numbers, equation numbers, citations, author names, journal names, DOI lines, page numbers, and bibliographic entries.
- Keep mathematical formulas, symbols, variables, and visibly corrupted OCR formula fragments as close to the source as possible. If a line is mostly formula, leave it unchanged.
- Preserve paragraph breaks.
- Use 「である」調 for explanatory prose.
- Translate headings directly. For example: Introduction=導入, Motivation=動機, References=参考文献.
- Do not add notes, commentary, or new references.
- Output only the Japanese translation.

English excerpt:
{text}
"""


HTML_CSS = """
:root {
  color-scheme: light;
  --bg: #f7f8f8;
  --paper: #ffffff;
  --text: #17201f;
  --muted: #667572;
  --line: #d8e1df;
  --accent: #006f63;
  --code: #eef3f2;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Sans",
    "Yu Gothic", "Noto Sans JP", sans-serif;
  line-height: 1.82;
}

a {
  color: var(--accent);
}

.layout {
  display: grid;
  grid-template-columns: minmax(220px, 300px) minmax(0, 1fr);
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  padding: 1rem;
  border-right: 1px solid var(--line);
  background: var(--paper);
}

.brand {
  margin: 0 0 1rem;
  font-weight: 700;
  line-height: 1.35;
}

.nav {
  display: grid;
  gap: 0.25rem;
}

.nav a {
  padding: 0.45rem 0.55rem;
  border-radius: 8px;
  color: var(--text);
  text-decoration: none;
}

.nav a:hover {
  background: #e6f2f0;
  color: var(--accent);
}

main {
  min-width: 0;
}

.content {
  max-width: 1040px;
  margin: 0 auto;
  padding: 2rem clamp(1rem, 3vw, 3rem) 4rem;
}

.paper {
  padding: clamp(1rem, 3vw, 2.4rem);
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--paper);
}

h1,
h2,
h3 {
  line-height: 1.35;
}

h1 {
  margin-top: 0;
  font-size: clamp(1.8rem, 4vw, 3rem);
}

h2 {
  margin-top: 2.4rem;
  padding-top: 1rem;
  border-top: 1px solid var(--line);
}

h3 {
  margin-top: 1.8rem;
}

.meta {
  color: var(--muted);
}

.note {
  padding: 0.8rem 1rem;
  border-left: 4px solid var(--accent);
  border-radius: 0 8px 8px 0;
  background: #e6f2f0;
}

.translated-page {
  margin-top: 1.5rem;
}

.translation {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.page-image {
  display: block;
  width: min(100%, 820px);
  margin: 1rem auto 0;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}

pre {
  overflow-x: auto;
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--code);
}

@media (max-width: 900px) {
  .layout {
    display: block;
  }

  .sidebar {
    position: static;
    height: auto;
  }
}
"""


@dataclass(frozen=True)
class Page:
    pdf_page: int
    printed_page: str
    text: str


@dataclass(frozen=True)
class Chapter:
    no: int
    ja: str
    en: str
    file: str
    raw_file: str
    pages: list[Page]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_metadata() -> dict:
    return json.loads(read_text(SOURCE_DIR / "metadata_ja.json"))


def parse_pages(raw_text: str) -> list[Page]:
    pattern = re.compile(
        r"^===== PDF page (?P<pdf>\d+) / printed page (?P<printed>[^=]+?) =====\n",
        flags=re.MULTILINE,
    )
    matches = list(pattern.finditer(raw_text))
    pages: list[Page] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_text)
        text = raw_text[start:end].strip()
        pages.append(
            Page(
                pdf_page=int(match.group("pdf")),
                printed_page=match.group("printed").strip(),
                text=text,
            )
        )
    return pages


def load_chapters(metadata: dict) -> list[Chapter]:
    chapters: list[Chapter] = []
    for item in metadata["chapters"]:
        raw_file = Path(item["file"]).with_suffix(".txt").name
        raw_path = RAW_DIR / raw_file
        chapters.append(
            Chapter(
                no=int(item["no"]),
                ja=item["ja"],
                en=item["en"],
                file=item["file"],
                raw_file=raw_file,
                pages=parse_pages(read_text(raw_path)),
            )
        )
    return chapters


def cache_path(model: str, chapter: Chapter, page: Page) -> Path:
    model_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", model)
    return CACHE_DIR / model_key / f"ch{chapter.no:02d}_pdf{page.pdf_page:03d}.json"


def request_ollama(model: str, prompt: str, timeout: int, retries: int = 3) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_p": 0.9,
            "num_ctx": 8192,
        },
    }
    encoded = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL,
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(5 * attempt)
    raise RuntimeError(f"Ollama request failed after {retries} attempts: {last_error}")


def is_effectively_blank(text: str) -> bool:
    stripped = text.strip()
    return len(stripped) <= 3 and re.search(r"[A-Za-z0-9]", stripped) is None


def translate_page(model: str, chapter: Chapter, page: Page, timeout: int, force: bool) -> dict:
    path = cache_path(model, chapter, page)
    if path.exists() and not force:
        return json.loads(read_text(path))

    started = time.time()
    if is_effectively_blank(page.text):
        translation = page.text.strip()
    else:
        prompt = PROMPT_TEMPLATE.format(glossary=GLOSSARY.strip(), text=page.text)
        response = request_ollama(model=model, prompt=prompt, timeout=timeout)
        translation = response.get("response", "").strip()
    record = {
        "model": model,
        "chapter": chapter.no,
        "chapter_ja": chapter.ja,
        "chapter_en": chapter.en,
        "pdf_page": page.pdf_page,
        "printed_page": page.printed_page,
        "source_chars": len(page.text),
        "translation_chars": len(translation),
        "elapsed_seconds": round(time.time() - started, 3),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "translation": translation,
    }
    write_text(path, json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    return record


def iter_selected_pages(
    chapters: Iterable[Chapter],
    chapter_filter: set[int] | None,
    limit: int | None,
) -> Iterable[tuple[Chapter, Page]]:
    count = 0
    for chapter in chapters:
        if chapter_filter and chapter.no not in chapter_filter:
            continue
        for page in chapter.pages:
            if limit is not None and count >= limit:
                return
            yield chapter, page
            count += 1


def markdown_escape_heading(text: str) -> str:
    return text.replace("\n", " ").strip()


def image_rel_path(page: Page, from_chapter: bool = False) -> str:
    prefix = "../" if from_chapter else ""
    return f"{prefix}../econometrics_hf_ch1_ch7_markdown_ja/assets/page_renders/page-{page.pdf_page}.jpeg"


def build_chapter_markdown(model: str, chapter: Chapter, from_chapter_dir: bool = True) -> str:
    lines: list[str] = []
    lines.append(f"# 第{chapter.no}章: {chapter.ja}（{chapter.en}）")
    lines.append("")
    lines.append(f"- 翻訳モデル: `{model}`")
    lines.append(f"- 原文抽出テキスト: `../econometrics_hf_ch1_ch7_markdown_ja/raw_text/{chapter.raw_file}`")
    lines.append("- 注: 数式・表・図はPDF抽出テキストでは崩れている場合があるため、ページ画像を併読してください。")
    lines.append("")

    for page in chapter.pages:
        record = json.loads(read_text(cache_path(model, chapter, page)))
        lines.append(f"## PDF page {page.pdf_page} / printed page {page.printed_page}")
        lines.append("")
        lines.append(record["translation"].strip())
        lines.append("")
        lines.append(f"![PDF page {page.pdf_page} render]({image_rel_path(page, from_chapter=from_chapter_dir)})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_full_markdown(model: str, metadata: dict, chapters: list[Chapter]) -> str:
    lines: list[str] = []
    lines.append("# Econometrics of Financial High-Frequency Data 第1〜7章 全文日本語訳フルレポート")
    lines.append("")
    lines.append(f"- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 翻訳モデル: `{model}`")
    lines.append(f"- 対象: 第{metadata['coverage']['chapters']}章、PDF pages {metadata['coverage']['pdf_pages']}、書籍 pages {metadata['coverage']['printed_pages']}")
    lines.append("- 原文抽出テキストをページ単位で日本語に翻訳したレポートです。")
    lines.append("- 数式・表・図はPDF抽出テキストでは崩れている可能性があるため、各ページ末尾のレンダー画像を正本として確認してください。")
    lines.append("")
    lines.append("## 章一覧")
    lines.append("")
    for chapter in chapters:
        lines.append(
            f"- [第{chapter.no}章: {chapter.ja}（{chapter.en}）](#第{chapter.no}章-{chapter.ja}{chapter.en})"
        )
    lines.append("")

    for chapter in chapters:
        chapter_md = build_chapter_markdown(model, chapter, from_chapter_dir=True)
        write_text(CHAPTER_DIR / f"ch{chapter.no:02d}_{Path(chapter.file).stem}_full_ja.md", chapter_md)
        chapter_md = build_chapter_markdown(model, chapter, from_chapter_dir=False)
        lines.append(chapter_md)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []

    def inline(text: str) -> str:
        text = html.escape(text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img class="page-image" src="\2" alt="\1" loading="lazy">', text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        return text

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            out.append(f'<p class="translation">{" ".join(inline(p) for p in paragraph)}</p>')
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            out.append("<ul>")
            out.extend(f"<li>{item}</li>" for item in list_items)
            out.append("</ul>")
            list_items = []

    for line in lines:
        if not line.strip():
            flush_paragraph()
            flush_list()
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(len(heading.group(1)), 3)
            text = markdown_escape_heading(heading.group(2))
            anchor = slugify(text)
            out.append(f'<h{level} id="{anchor}">{inline(text)}</h{level}>')
            continue
        image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", line.strip())
        if image:
            flush_paragraph()
            flush_list()
            alt = html.escape(image.group(1))
            src = html.escape(image.group(2), quote=True)
            out.append(
                f'<figure><a href="{src}"><img class="page-image" src="{src}" alt="{alt}" loading="lazy"></a>'
                f"<figcaption>{alt}</figcaption></figure>"
            )
            continue
        item = re.match(r"^-\s+(.+)$", line)
        if item:
            flush_paragraph()
            list_items.append(inline(item.group(1)))
            continue
        flush_list()
        paragraph.append(line)
    flush_paragraph()
    flush_list()
    return "\n".join(out)


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w一-龯ぁ-んァ-ヶー]+", "-", text, flags=re.UNICODE).strip("-").lower()
    return slug or "section"


def build_html_report(markdown: str, chapters: list[Chapter], model: str) -> str:
    nav = "\n".join(
        f'<a href="#{slugify(f"第{chapter.no}章: {chapter.ja}（{chapter.en}）")}">第{chapter.no}章 {html.escape(chapter.ja)}</a>'
        for chapter in chapters
    )
    body = markdown_to_html(markdown)
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>全文日本語訳フルレポート | Econometrics of Financial High-Frequency Data</title>
  <style>{HTML_CSS}</style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <p class="brand">全文日本語訳フルレポート<br><span class="meta">model: {html.escape(model)}</span></p>
      <nav class="nav">
        <a href="#econometrics-of-financial-high-frequency-data-第1-7章-全文日本語訳フルレポート">先頭</a>
        {nav}
      </nav>
    </aside>
    <main>
      <div class="content">
        <article class="paper">
          <p class="note">このHTMLはローカル抽出テキストから生成した日本語訳です。数式・表・図はページ画像レンダーを併読してください。</p>
          {body}
        </article>
      </div>
    </main>
  </div>
</body>
</html>
"""


def write_outputs(model: str, metadata: dict, chapters: list[Chapter]) -> None:
    markdown = build_full_markdown(model, metadata, chapters)
    write_text(REPORT_MD, markdown)
    write_text(REPORT_HTML, build_html_report(markdown, chapters, model))
    records = []
    total_elapsed = 0.0
    total_translation_chars = 0
    for chapter in chapters:
        for page in chapter.pages:
            path = cache_path(model, chapter, page)
            if not path.exists():
                continue
            record = json.loads(read_text(path))
            records.append(
                {
                    "chapter": chapter.no,
                    "pdf_page": page.pdf_page,
                    "printed_page": page.printed_page,
                    "translation_chars": record.get("translation_chars", 0),
                    "elapsed_seconds": record.get("elapsed_seconds", 0),
                }
            )
            total_elapsed += float(record.get("elapsed_seconds", 0))
            total_translation_chars += int(record.get("translation_chars", 0))
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "model": model,
        "source": str(SOURCE_DIR.relative_to(PROJECT_DIR)),
        "chapters": len(chapters),
        "pages": len(records),
        "translation_chars": total_translation_chars,
        "model_elapsed_seconds_sum": round(total_elapsed, 3),
        "outputs": {
            "markdown": str(REPORT_MD.relative_to(PROJECT_DIR)),
            "html": str(REPORT_HTML.relative_to(PROJECT_DIR)),
            "chapter_markdown_dir": str(CHAPTER_DIR.relative_to(PROJECT_DIR)),
        },
        "pages_detail": records,
    }
    write_text(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def missing_pages(model: str, chapters: list[Chapter]) -> list[tuple[Chapter, Page]]:
    missing: list[tuple[Chapter, Page]] = []
    for chapter in chapters:
        for page in chapter.pages:
            if not cache_path(model, chapter, page).exists():
                missing.append((chapter, page))
    return missing


def parse_chapter_filter(values: list[str] | None) -> set[int] | None:
    if not values:
        return None
    selected: set[int] = set()
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start, end = part.split("-", 1)
                selected.update(range(int(start), int(end) + 1))
            else:
                selected.add(int(part))
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model name, default: {DEFAULT_MODEL}")
    parser.add_argument("--fast", action="store_true", help=f"Use faster default model: {FAST_MODEL}")
    parser.add_argument("--chapter", action="append", help="Chapter numbers to translate, e.g. 1 or 1,2 or 3-5")
    parser.add_argument("--limit-pages", type=int, help="Translate only the first N selected pages")
    parser.add_argument("--force", action="store_true", help="Retranslate pages even when cache exists")
    parser.add_argument("--timeout", type=int, default=600, help="Per-page Ollama timeout in seconds")
    parser.add_argument("--report-only", action="store_true", help="Only rebuild Markdown/HTML from existing cache")
    args = parser.parse_args()

    model = FAST_MODEL if args.fast else args.model
    metadata = load_metadata()
    chapters = load_chapters(metadata)
    selected = parse_chapter_filter(args.chapter)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CHAPTER_DIR.mkdir(parents=True, exist_ok=True)

    if not args.report_only:
        selected_pages = list(iter_selected_pages(chapters, selected, args.limit_pages))
        total = len(selected_pages)
        for index, (chapter, page) in enumerate(selected_pages, start=1):
            path = cache_path(model, chapter, page)
            if path.exists() and not args.force:
                print(f"[{index}/{total}] cached ch{chapter.no:02d} pdf {page.pdf_page}")
                continue
            print(f"[{index}/{total}] translating ch{chapter.no:02d} pdf {page.pdf_page}...", flush=True)
            record = translate_page(model, chapter, page, args.timeout, args.force)
            print(
                f"    done {record['elapsed_seconds']:.1f}s "
                f"{record['source_chars']} -> {record['translation_chars']} chars",
                flush=True,
            )

    missing = missing_pages(model, chapters)
    if missing:
        print(f"Translation cache is incomplete: {len(missing)} pages missing.")
        print("Run again without --limit-pages/--chapter, or use --report-only after completing translation.")
        if args.report_only:
            raise SystemExit(1)
        return

    write_outputs(model, metadata, chapters)
    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_HTML}")
    print(f"Wrote {MANIFEST}")


if __name__ == "__main__":
    main()
