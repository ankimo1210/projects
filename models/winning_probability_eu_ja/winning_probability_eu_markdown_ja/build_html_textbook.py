#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "html_textbook"
OUT_FILE = OUT_DIR / "index.html"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def make_markdown_renderer() -> MarkdownIt:
    md = MarkdownIt("gfm-like", {"html": False})
    default_fence = md.renderer.rules["fence"]

    def fence(tokens, idx, options, env):
        token = tokens[idx]
        info = token.info.strip().split(maxsplit=1)[0] if token.info.strip() else ""
        if info == "math":
            return (
                '<pre class="math-block"><code>'
                + escape(token.content)
                + "</code></pre>\n"
            )
        return default_fence(tokens, idx, options, env)

    md.renderer.rules["fence"] = fence
    return md


MD = make_markdown_renderer()


def markdown_to_html(markdown: str) -> str:
    rendered = MD.render(markdown)
    rendered = rendered.replace("<table>", '<div class="table-wrap"><table>')
    rendered = rendered.replace("</table>", "</table></div>")
    rendered = re.sub(r"<img(?![^>]*\bloading=)", '<img loading="lazy" decoding="async"', rendered)
    return rendered


def first_heading(markdown: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def section_between(markdown: str, start_heading: str, end_heading: str) -> str:
    start = markdown.find(start_heading)
    if start == -1:
        return ""
    start += len(start_heading)
    if end_heading:
        end = markdown.find(end_heading, start)
    else:
        end = len(markdown)
    if end == -1:
        end = len(markdown)
    return markdown[start:end].strip()


@dataclass(frozen=True)
class Page:
    number: int
    title: str
    image_src: str
    location: str
    memo_md: str
    ocr_text: str


def parse_page(path: Path) -> Page:
    markdown = read_text(path)
    number_match = re.search(r"page_(\d+)_ja\.md$", path.name)
    if not number_match:
        raise ValueError(f"Unexpected page filename: {path}")
    number = int(number_match.group(1))

    image_match = re.search(r"!\[[^\]]*\]\(([^)]+)\)", markdown)
    if not image_match:
        raise ValueError(f"Missing page image in {path}")
    image_src = image_match.group(1)

    memo_md = section_between(markdown, "## 日本語メモ", "## 原文OCR/Text Layer")
    location_match = re.search(r"\*\*該当箇所:\*\*\s*(.+)", memo_md)
    location = location_match.group(1).strip() if location_match else "ページメモ"

    ocr_section = section_between(markdown, "## 原文OCR/Text Layer", "")
    ocr_match = re.search(r"```text\s*\n(.*?)\n```", ocr_section, re.DOTALL)
    ocr_text = ocr_match.group(1).strip() if ocr_match else ""

    return Page(
        number=number,
        title=first_heading(markdown, f"Page {number:03d}"),
        image_src=image_src,
        location=location,
        memo_md=memo_md,
        ocr_text=ocr_text,
    )


def page_card(page: Page) -> str:
    page_id = f"page-{page.number:03d}"
    memo_html = markdown_to_html(page.memo_md)
    return f"""
<article class="page-card searchable" id="{page_id}">
  <div class="page-card__header">
    <div>
      <p class="eyebrow">Page {page.number:03d}</p>
      <h3>{escape(page.location)}</h3>
    </div>
    <a class="source-link" href="{escape(page.image_src)}">PNG</a>
  </div>
  <img class="page-image" src="{escape(page.image_src)}" alt="Page {page.number}">
  <div class="memo">{memo_html}</div>
  <details class="ocr">
    <summary>原文OCR/Text Layerを表示</summary>
    <pre><code>{escape(page.ocr_text)}</code></pre>
  </details>
</article>
"""


def page_nav(pages: list[Page]) -> str:
    links = "\n".join(
        f'<a href="#page-{page.number:03d}">{page.number:03d}</a>' for page in pages
    )
    return f'<div class="page-links">{links}</div>'


def source_link(path: str) -> str:
    return f'<a class="source-link" href="../{escape(path)}">{escape(path)}</a>'


def markdown_chapter(section_id: str, label: str, path: str, lead: str = "") -> str:
    markdown = read_text(ROOT / path)
    lead_html = f"<p class=\"chapter-lead\">{escape(lead)}</p>" if lead else ""
    return f"""
<section class="chapter searchable" id="{escape(section_id)}">
  <div class="chapter-toolbar">
    <p class="eyebrow">{escape(label)}</p>
    {source_link(path)}
  </div>
  {lead_html}
  {markdown_to_html(markdown)}
</section>
"""


def table_chapter() -> str:
    parts = []
    for path in ["tables/table_001_ja.md", "tables/table_002_ja.md"]:
        parts.append(markdown_to_html(read_text(ROOT / path)))
    body = "\n".join(parts)
    return f"""
<section class="chapter searchable" id="tables">
  <div class="chapter-toolbar">
    <p class="eyebrow">Tables</p>
    <span>{source_link("tables/table_001_ja.md")} {source_link("tables/table_002_ja.md")}</span>
  </div>
  {body}
</section>
"""


def stat_cards(manifest: dict) -> str:
    stats = [
        ("ページ画像", f"{manifest.get('page_images', '-')}/{manifest.get('pdf_pages', '-')}"),
        ("ページ別メモ", f"{manifest.get('pages_ja', '-')}"),
        ("図", f"{len(manifest.get('figures_indexed', []))}"),
        ("表", f"{len(manifest.get('tables_indexed', []))}"),
        ("検証済み数式", f"{len(manifest.get('equations_verified', []))}"),
    ]
    cards = "\n".join(
        f'<div class="stat"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in stats
    )
    return f'<div class="stats">{cards}</div>'


def render_html() -> str:
    manifest = json.loads(read_text(ROOT / "manifest_ja.json"))
    pages = [parse_page(path) for path in sorted((ROOT / "pages_ja").glob("page_*_ja.md"))]
    page_cards = "\n".join(page_card(page) for page in pages)
    page_navigation = page_nav(pages)

    chapters = "\n".join(
        [
            markdown_chapter(
                "main-note",
                "Main Note",
                "main_translation_ja.md",
                "まず全体像を掴むための日本語メインノートです。",
            ),
            markdown_chapter(
                "equations",
                "Equations",
                "verified_equations_ja.md",
                "番号付き数式を日本語の読み方付きで確認できます。",
            ),
            markdown_chapter(
                "figures",
                "Figures",
                "figure_table_index_ja.md",
                "Figure 1-37とTable 1-2のページ対応を一覧できます。",
            ),
            table_chapter(),
            markdown_chapter("glossary", "Glossary", "glossary_ja.md"),
            markdown_chapter(
                "audit",
                "Audit",
                "accuracy_completeness_audit_ja.md",
                "この日本語版の完全性と制限事項です。",
            ),
        ]
    )

    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Winning-Probability Model for EUGV RFQ Pricing 日本語HTMLテキストブック</title>
  <style>
    :root {{
      --bg: #f7f8f7;
      --surface: #ffffff;
      --ink: #1d2522;
      --muted: #607069;
      --line: #dce3df;
      --accent: #0f766e;
      --accent-weak: #e0f2ef;
      --code: #f1f5f3;
      --shadow: 0 10px 26px rgba(20, 38, 32, 0.08);
      color-scheme: light;
    }}

    * {{
      box-sizing: border-box;
    }}

    html {{
      scroll-behavior: smooth;
    }}

    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic", "Noto Sans JP", "Segoe UI", sans-serif;
      line-height: 1.75;
      letter-spacing: 0;
    }}

    a {{
      color: var(--accent);
      text-decoration: none;
    }}

    a:hover {{
      text-decoration: underline;
    }}

    .layout {{
      display: grid;
      grid-template-columns: 292px minmax(0, 1fr);
      min-height: 100vh;
    }}

    .sidebar {{
      position: sticky;
      top: 0;
      height: 100vh;
      overflow-y: auto;
      border-right: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.92);
      padding: 22px 18px;
    }}

    .brand {{
      display: block;
      color: var(--ink);
      font-weight: 750;
      line-height: 1.35;
      margin-bottom: 18px;
    }}

    .search {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      font: inherit;
      background: var(--surface);
      color: var(--ink);
      margin-bottom: 8px;
    }}

    .search-status {{
      min-height: 24px;
      margin: 0 0 14px;
      color: var(--muted);
      font-size: 0.86rem;
    }}

    .nav-list {{
      display: grid;
      gap: 7px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}

    .nav-list a,
    .page-links a {{
      display: block;
      border-radius: 8px;
      padding: 7px 9px;
      color: var(--ink);
    }}

    .nav-list a:hover,
    .page-links a:hover {{
      background: var(--accent-weak);
      text-decoration: none;
    }}

    .sidebar details {{
      margin-top: 18px;
    }}

    .sidebar summary {{
      cursor: pointer;
      color: var(--muted);
      font-weight: 650;
    }}

    .page-links {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 4px;
      margin-top: 10px;
      font-variant-numeric: tabular-nums;
      font-size: 0.88rem;
    }}

    main {{
      min-width: 0;
    }}

    .hero {{
      padding: 52px min(6vw, 78px) 34px;
      background: var(--surface);
      border-bottom: 1px solid var(--line);
    }}

    .hero h1 {{
      max-width: 1050px;
      margin: 0 0 14px;
      font-size: clamp(2rem, 4vw, 3.25rem);
      line-height: 1.12;
      letter-spacing: 0;
    }}

    .hero p {{
      max-width: 980px;
      color: var(--muted);
      font-size: 1.05rem;
      margin: 0 0 18px;
    }}

    .notice {{
      max-width: 980px;
      border-left: 4px solid var(--accent);
      background: var(--accent-weak);
      padding: 12px 16px;
      border-radius: 0 8px 8px 0;
      color: #163c37;
    }}

    .stats {{
      display: grid;
      grid-template-columns: repeat(5, minmax(130px, 1fr));
      gap: 10px;
      max-width: 980px;
      margin-top: 24px;
    }}

    .stat {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px 14px;
      background: var(--surface);
    }}

    .stat span {{
      display: block;
      color: var(--muted);
      font-size: 0.86rem;
    }}

    .stat strong {{
      display: block;
      font-size: 1.35rem;
      line-height: 1.25;
      margin-top: 2px;
    }}

    .content {{
      width: min(1120px, calc(100vw - 292px));
      padding: 34px min(5vw, 64px) 72px;
    }}

    .chapter,
    .pages-section {{
      margin: 0 0 34px;
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }}

    .chapter-toolbar,
    .page-card__header {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 12px;
    }}

    .eyebrow {{
      margin: 0;
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 750;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }}

    .chapter-lead {{
      color: var(--muted);
      margin-top: 0;
    }}

    .source-link {{
      display: inline-flex;
      align-items: center;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 10px;
      color: var(--muted);
      font-size: 0.82rem;
      white-space: nowrap;
    }}

    h1,
    h2,
    h3 {{
      line-height: 1.35;
      letter-spacing: 0;
    }}

    h1 {{
      font-size: 2rem;
      margin: 0 0 18px;
    }}

    h2 {{
      margin-top: 2.1em;
      padding-top: 0.2em;
      font-size: 1.45rem;
      border-top: 1px solid var(--line);
    }}

    h3 {{
      font-size: 1.12rem;
      margin: 0.6em 0 0.4em;
    }}

    p,
    ul,
    ol,
    blockquote,
    pre,
    .table-wrap {{
      margin-top: 0.8em;
      margin-bottom: 0.8em;
    }}

    blockquote {{
      border-left: 4px solid var(--line);
      margin-left: 0;
      padding: 0.1px 0 0.1px 16px;
      color: var(--muted);
    }}

    code {{
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.92em;
    }}

    p code,
    li code,
    td code {{
      background: var(--code);
      border-radius: 4px;
      padding: 0.12em 0.35em;
    }}

    pre {{
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--code);
      padding: 14px 16px;
      line-height: 1.55;
      white-space: pre-wrap;
    }}

    .math-block {{
      background: #fbfcfb;
      border-left: 4px solid var(--accent);
      font-size: 0.95rem;
    }}

    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.93rem;
      line-height: 1.55;
    }}

    th,
    td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 10px;
      vertical-align: top;
    }}

    th {{
      background: #f1f5f3;
      text-align: left;
      font-weight: 700;
    }}

    tr:last-child td {{
      border-bottom: 0;
    }}

    img {{
      max-width: 100%;
      height: auto;
    }}

    .pages-section h2 {{
      margin-top: 0;
      border-top: 0;
    }}

    .page-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
      align-items: start;
    }}

    .page-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      padding: 16px;
    }}

    .page-card h3 {{
      margin-top: 2px;
    }}

    .page-image {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }}

    .memo {{
      margin-top: 12px;
    }}

    .ocr {{
      margin-top: 12px;
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}

    .ocr summary {{
      cursor: pointer;
      color: var(--muted);
      font-weight: 650;
    }}

    .ocr pre {{
      max-height: 420px;
      font-size: 0.82rem;
    }}

    .is-hidden {{
      display: none !important;
    }}

    @media (max-width: 960px) {{
      .layout {{
        display: block;
      }}

      .sidebar {{
        position: static;
        height: auto;
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }}

      .content {{
        width: 100%;
        padding: 22px 16px 48px;
      }}

      .hero {{
        padding: 34px 16px 24px;
      }}

      .stats {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}

      .chapter,
      .pages-section {{
        padding: 18px;
      }}
    }}

    @media print {{
      .sidebar,
      .search-status,
      .source-link {{
        display: none;
      }}

      .layout {{
        display: block;
      }}

      .content {{
        width: 100%;
        padding: 0;
      }}

      .chapter,
      .pages-section,
      .page-card {{
        box-shadow: none;
        break-inside: avoid;
      }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <a class="brand" href="#top">Winning-Probability Model<br>日本語HTMLテキストブック</a>
      <input class="search" id="search" type="search" placeholder="キーワード検索">
      <p class="search-status" id="search-status"></p>
      <ul class="nav-list">
        <li><a href="#main-note">1. メインノート</a></li>
        <li><a href="#equations">2. 検証済み数式</a></li>
        <li><a href="#figures">3. 図表インデックス</a></li>
        <li><a href="#tables">4. 主要表</a></li>
        <li><a href="#glossary">5. 用語集</a></li>
        <li><a href="#pages">6. ページ別ビュー</a></li>
        <li><a href="#audit">7. 監査・制限事項</a></li>
      </ul>
      <details>
        <summary>ページへ移動</summary>
        {page_navigation}
      </details>
    </aside>
    <main>
      <header class="hero" id="top">
        <p class="eyebrow">Japanese HTML Textbook</p>
        <h1>Winning-Probability Model for EUGV RFQ Pricing</h1>
        <p>既存の日本語Markdown作業版を、学習・確認しやすい静的HTMLテキストブックとして再構成しました。本文ノート、数式、図表、用語集、ページ画像、原文OCRを1ファイルから横断できます。</p>
        <div class="notice">注意: この版は完全な逐語訳ではなく、日本語で読むためのナビゲーション版です。数式・表・図・ページレイアウトの最終確認はページPNGと検証済み数式・表を優先してください。社外共有前に原資料の取扱ルールを確認してください。</div>
        {stat_cards(manifest)}
      </header>
      <div class="content">
        {chapters}
        <section class="pages-section" id="pages">
          <p class="eyebrow">Page Reader</p>
          <h2>ページ別ビュー</h2>
          <p>各ページの画像、日本語メモ、原文OCRを並べています。OCRはノイズが多いため、必要なページだけ展開して確認してください。</p>
          <div class="page-grid">
            {page_cards}
          </div>
        </section>
      </div>
    </main>
  </div>
  <script>
    const searchInput = document.getElementById('search');
    const statusEl = document.getElementById('search-status');
    const searchable = Array.from(document.querySelectorAll('.searchable'));

    function normalizeText(value) {{
      return value.toLocaleLowerCase('ja-JP').replace(/\\s+/g, ' ').trim();
    }}

    function updateSearch() {{
      const query = normalizeText(searchInput.value);
      let visible = 0;
      searchable.forEach((item) => {{
        const haystack = item.dataset.searchIndex || normalizeText(item.textContent);
        item.dataset.searchIndex = haystack;
        const match = query === '' || haystack.includes(query);
        item.classList.toggle('is-hidden', !match);
        if (match) visible += 1;
      }});
      statusEl.textContent = query ? `${{visible}}件を表示中` : '';
    }}

    searchInput.addEventListener('input', updateSearch);
  </script>
</body>
</html>
"""


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    OUT_FILE.write_text(render_html(), encoding="utf-8")
    print(OUT_FILE)


if __name__ == "__main__":
    main()
