#!/usr/bin/env python3
"""Build a static Japanese HTML textbook from the Opt-Var markdown archive."""

from __future__ import annotations

import html
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "html_textbook"
PAGE_COUNT = 136


@dataclass(frozen=True)
class Section:
    number: str
    english: str
    japanese: str
    page: int


@dataclass(frozen=True)
class Chapter:
    number: str
    english: str
    japanese: str
    start_page: int
    end_page: int
    sections: tuple[Section, ...]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def parse_toc() -> list[Section]:
    sections: list[Section] = []
    for raw_line in read_text(ROOT / "TOC_JA.md").splitlines():
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
        sections.append(
            Section(
                number=cells[0],
                english=cells[1],
                japanese=cells[2],
                page=page,
            )
        )
    return sections


def build_chapters(sections: list[Section]) -> list[Chapter]:
    top = [section for section in sections if "." not in section.number]
    chapters: list[Chapter] = []
    if top and top[0].page > 1:
        chapters.append(
            Chapter(
                number="0",
                english="Front Matter",
                japanese="表紙・前付",
                start_page=1,
                end_page=top[0].page - 1,
                sections=(),
            )
        )

    for index, section in enumerate(top):
        next_page = top[index + 1].page if index + 1 < len(top) else PAGE_COUNT + 1
        end_page = min(PAGE_COUNT, next_page - 1)
        prefix = f"{section.number}."
        sub_sections = tuple(
            candidate
            for candidate in sections
            if candidate.number == section.number or candidate.number.startswith(prefix)
        )
        last_section_page = max((candidate.page for candidate in sub_sections), default=section.page)
        chapters.append(
            Chapter(
                number=section.number,
                english=section.english,
                japanese=section.japanese,
                start_page=section.page,
                end_page=max(section.page, end_page, last_section_page),
                sections=sub_sections,
            )
        )
    return chapters


def load_manifest() -> dict[str, object]:
    return json.loads(read_text(ROOT / "manifest.json"))


def page_text(page: int) -> str:
    return read_text(ROOT / "raw_text" / f"page_{page:03d}.txt").strip()


def page_path(page: int) -> str:
    return f"pages/page-{page:03d}.html"


def chapter_path(chapter: Chapter) -> str:
    if chapter.number == "0":
        return "chapters/front-matter.html"
    return f"chapters/chapter-{int(chapter.number):02d}.html"


def page_image_path(page: int) -> str:
    return f"assets/page_images/page-{page:03d}.jpg"


def reset_generated_output() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for relative in [
        "index.html",
        "README.md",
        "assets/styles.css",
        "assets/app.js",
        "assets/search-index.js",
    ]:
        target = OUT / relative
        if target.exists():
            target.unlink()

    for relative in ["pages", "chapters", "references", "assets/page_images"]:
        target = OUT / relative
        if target.exists():
            shutil.rmtree(target)


def copy_page_images() -> None:
    source_dir = ROOT / "assets" / "page_images"
    target_dir = OUT / "assets" / "page_images"
    target_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(source_dir.glob("page-*.jpg")):
        shutil.copy2(source, target_dir / source.name)


def section_id(section: Section) -> str:
    return "section-" + section.number.replace(".", "-")


def current_sections_for_page(sections: list[Section], page: int) -> list[Section]:
    return [section for section in sections if section.page == page]


def current_chapter_for_page(chapters: list[Chapter], page: int) -> Chapter:
    for chapter in chapters:
        if chapter.start_page <= page <= chapter.end_page:
            return chapter
    return chapters[-1]


def closest_section_for_page(sections: list[Section], page: int) -> Section | None:
    candidates = [section for section in sections if section.page <= page]
    if not candidates:
        return None
    return max(candidates, key=lambda section: section.page)


def href_for_section(section: Section, chapters: list[Chapter]) -> str:
    if "." not in section.number:
        for chapter in chapters:
            if chapter.number == section.number:
                return chapter_path(chapter)
    return f"{page_path(section.page)}#{section_id(section)}"


def inline_html(text: str, root_prefix: str) -> str:
    value = html.escape(text)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)

    def replace_link(match: re.Match[str]) -> str:
        label = match.group(1)
        url = rewrite_url(html.unescape(match.group(2)), root_prefix)
        return f'<a href="{esc(url)}">{label}</a>'

    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, value)
    return value


def rewrite_url(url: str, root_prefix: str) -> str:
    if re.match(r"^[a-z]+://", url) or url.startswith("#"):
        return url
    page_match = re.search(r"page[_-](\d{3})(?:_ja)?\.md$", url)
    if page_match:
        return root_prefix + page_path(int(page_match.group(1)))
    if url.startswith("assets/"):
        return root_prefix + url
    if url.startswith("../assets/"):
        return root_prefix + url.removeprefix("../")
    if url.endswith(".md"):
        return root_prefix + "index.html"
    return url


def render_markdown_table(lines: list[str], root_prefix: str) -> str:
    rows: list[list[str]] = []
    for line in lines:
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    header = rows[0] if rows else []
    body = rows[2:] if len(rows) > 1 and re.fullmatch(r"[-:| ]+", lines[1].strip()) else rows[1:]
    head_html = "".join(f"<th>{inline_html(cell, root_prefix)}</th>" for cell in header)
    body_html = "\n".join(
        "<tr>"
        + "".join(f"<td>{inline_html(cell, root_prefix)}</td>" for cell in row)
        + "</tr>"
        for row in body
    )
    return (
        '<div class="table-wrap"><table>'
        f"<thead><tr>{head_html}</tr></thead>"
        f"<tbody>{body_html}</tbody>"
        "</table></div>"
    )


def markdown_to_html(markdown: str, root_prefix: str) -> str:
    lines = markdown.splitlines()
    parts: list[str] = []
    paragraph: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(item.strip() for item in paragraph)
            parts.append(f"<p>{inline_html(text, root_prefix)}</p>")
            paragraph.clear()

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            index += 1
            continue

        if stripped.startswith("```"):
            flush_paragraph()
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            parts.append(f'<pre class="code-block"><code>{esc("\\n".join(code_lines))}</code></pre>')
            continue

        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            slug = re.sub(r"[^a-zA-Z0-9一-龥ぁ-んァ-ヶー]+", "-", text).strip("-").lower()
            parts.append(f'<h{level} id="{esc(slug)}">{inline_html(text, root_prefix)}</h{level}>')
            index += 1
            continue

        image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
        if image:
            flush_paragraph()
            alt = image.group(1)
            src = rewrite_url(image.group(2), root_prefix)
            parts.append(
                '<figure class="doc-image">'
                f'<a href="{esc(src)}"><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy"></a>'
                f"<figcaption>{esc(alt)}</figcaption>"
                "</figure>"
            )
            index += 1
            continue

        if stripped.startswith("|"):
            flush_paragraph()
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            parts.append(render_markdown_table(table_lines, root_prefix))
            continue

        if re.match(r"^- ", stripped):
            flush_paragraph()
            items: list[str] = []
            while index < len(lines) and re.match(r"^- ", lines[index].strip()):
                items.append(lines[index].strip()[2:])
                index += 1
            parts.append(
                "<ul>"
                + "".join(f"<li>{inline_html(item, root_prefix)}</li>" for item in items)
                + "</ul>"
            )
            continue

        paragraph.append(line)
        index += 1

    flush_paragraph()
    return "\n".join(parts)


def render_sidebar(
    root_prefix: str,
    sections: list[Section],
    chapters: list[Chapter],
    active_path: str,
) -> str:
    chapter_links = []
    for chapter in chapters:
        href = chapter_path(chapter)
        active = " active" if active_path == href else ""
        label = f"{chapter.number}. {chapter.japanese}" if chapter.number != "0" else chapter.japanese
        chapter_links.append(
            f'<li><a class="{active.strip()}" href="{esc(root_prefix + href)}">{esc(label)}</a></li>'
        )

    toc_links = []
    for section in sections:
        href = href_for_section(section, chapters)
        active = " active" if active_path == href else ""
        toc_links.append(
            "<li>"
            f'<a class="{active.strip()}" href="{esc(root_prefix + href)}">'
            f'<span class="toc-num">{esc(section.number)}</span>{esc(section.japanese)}'
            "</a>"
            "</li>"
        )

    return f"""
<aside class="sidebar" aria-label="テキストブックナビゲーション">
  <div class="brand">
    <a href="{esc(root_prefix + "index.html")}">Opt-Var HTML</a>
    <span>日本語テキストブック</span>
  </div>
  <form class="search-box" data-search-form>
    <label for="site-search">OCR検索</label>
    <input id="site-search" name="q" type="search" placeholder="例: lambda, covariance" autocomplete="off" data-search-input>
    <div class="search-results" data-search-results aria-live="polite"></div>
  </form>
  <form class="page-jump" data-page-jump>
    <label for="page-number">ページへ移動</label>
    <div>
      <input id="page-number" name="page" type="number" min="1" max="{PAGE_COUNT}" placeholder="1-136">
      <button type="submit">開く</button>
    </div>
  </form>
  <nav>
    <h2>章</h2>
    <ul class="nav-list">
      {"".join(chapter_links)}
    </ul>
    <details open>
      <summary>詳細目次</summary>
      <ul class="nav-list toc-list">
        {"".join(toc_links)}
      </ul>
    </details>
  </nav>
</aside>
"""


def html_shell(
    title: str,
    body: str,
    root_prefix: str,
    sections: list[Section],
    chapters: list[Chapter],
    active_path: str,
) -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="{esc(root_prefix + "assets/styles.css")}">
</head>
<body data-root="{esc(root_prefix)}">
  <a class="skip-link" href="#content">本文へ移動</a>
  <div class="layout">
    {render_sidebar(root_prefix, sections, chapters, active_path)}
    <main id="content" class="content">
      {body}
    </main>
  </div>
  <script src="{esc(root_prefix + "assets/search-index.js")}"></script>
  <script src="{esc(root_prefix + "assets/app.js")}"></script>
</body>
</html>
"""


def render_chapter_card(chapter: Chapter) -> str:
    href = chapter_path(chapter)
    title = chapter.japanese if chapter.number == "0" else f"{chapter.number}. {chapter.japanese}"
    section_count = len(chapter.sections)
    detail = "前付資料" if chapter.number == "0" else f"{section_count} セクション"
    return f"""
<a class="chapter-card" href="{esc(href)}">
  <span class="chapter-number">{esc(chapter.number)}</span>
  <strong>{esc(title)}</strong>
  <span>{esc(chapter.english)}</span>
  <small>PDF {chapter.start_page}-{chapter.end_page} ページ / {esc(detail)}</small>
</a>
"""


def render_page_list(root_prefix: str = "") -> str:
    links = [
        f'<a href="{esc(root_prefix + page_path(page))}">{page:03d}</a>'
        for page in range(1, PAGE_COUNT + 1)
    ]
    return '<div class="page-grid">' + "".join(links) + "</div>"


def render_index(
    sections: list[Section],
    chapters: list[Chapter],
    manifest: dict[str, object],
) -> str:
    full_report_link = (
        '<a href="full_report_ja.html">全文日本語訳レポート</a>'
        if (OUT / "full_report_ja.html").exists()
        else ""
    )
    stats = [
        ("ページ", manifest.get("pages", PAGE_COUNT)),
        ("図版候補", manifest.get("figures_detected", "-")),
        ("表候補", manifest.get("tables_detected", "-")),
        ("数式候補", manifest.get("equation_candidates_detected", "-")),
    ]
    stat_html = "".join(
        f'<div class="stat"><strong>{esc(value)}</strong><span>{esc(label)}</span></div>'
        for label, value in stats
    )
    chapter_cards = "".join(render_chapter_card(chapter) for chapter in chapters)
    body = f"""
<section class="hero">
  <div>
    <p class="eyebrow">Visual-complete Markdown archive から生成</p>
    <h1>Opt-Var 日本語 HTML テキストブック</h1>
    <p class="lead">日本語の目次・ナビゲーション・検索 UI で、全136ページの原本画像とOCRテキストを読める静的HTML版です。</p>
    <div class="actions">
      <a class="button primary" href="{esc(chapter_path(chapters[0]))}">最初から読む</a>
      <a class="button" href="references/translation-notes.html">精度メモを見る</a>
    </div>
  </div>
  <figure class="cover">
    <img src="{esc(page_image_path(1))}" alt="Opt-Var 表紙ページ" loading="eager">
  </figure>
</section>

<section class="notice">
  <h2>このHTML版の位置づけ</h2>
  <p>本文OCRは原文英語を保持しています。数式・表・図・脚注番号はOCRで崩れることがあるため、厳密確認には各ページ画像を正本として使ってください。</p>
</section>

<section class="stats" aria-label="収録状況">
  {stat_html}
</section>

<section>
  <div class="section-heading">
    <h2>章別に読む</h2>
    <p>PDF上の日本語目次をもとに、章単位でページ画像とOCRテキストをまとめています。</p>
  </div>
  <div class="chapter-grid">
    {chapter_cards}
  </div>
</section>

<section>
  <div class="section-heading">
    <h2>補助インデックス</h2>
    <p>図版、表、数式候補、監査レポートをHTMLから参照できます。</p>
  </div>
  <div class="resource-grid">
    {full_report_link}
    <a href="references/figures.html">図版インデックス</a>
    <a href="references/tables.html">表インデックス</a>
    <a href="references/equations.html">数式候補インデックス</a>
    <a href="references/audit.html">監査レポート</a>
    <a href="references/translation-notes.html">翻訳・精度メモ</a>
  </div>
</section>

<section>
  <div class="section-heading">
    <h2>ページ一覧</h2>
    <p>ページ番号から直接開けます。</p>
  </div>
  {render_page_list()}
</section>
"""
    return html_shell(
        "Opt-Var 日本語 HTML テキストブック",
        body,
        "",
        sections,
        chapters,
        "index.html",
    )


def render_page_article(
    page: int,
    sections: list[Section],
    chapters: list[Chapter],
    root_prefix: str,
    ocr_open: bool,
) -> str:
    chapter = current_chapter_for_page(chapters, page)
    page_sections = current_sections_for_page(sections, page)
    nearest = closest_section_for_page(sections, page)
    section_badges = "".join(
        f'<a id="{esc(section_id(section))}" class="section-badge" href="#{esc(section_id(section))}">'
        f"{esc(section.number)} {esc(section.japanese)}</a>"
        for section in page_sections
    )
    if not section_badges and nearest:
        section_badges = (
            '<span class="section-badge muted">'
            f"{esc(nearest.number)} {esc(nearest.japanese)} 以降"
            "</span>"
        )

    image = root_prefix + page_image_path(page)
    details_open = " open" if ocr_open else ""
    return f"""
<article class="page-article" id="page-{page:03d}">
  <header class="page-header">
    <p class="eyebrow">{esc(chapter.japanese)}</p>
    <h2>ページ {page:03d}</h2>
    <div class="section-badges">{section_badges}</div>
  </header>
  <figure class="page-image">
    <a href="{esc(image)}"><img src="{esc(image)}" alt="ページ {page:03d} の原本画像" loading="lazy"></a>
  </figure>
  <details class="ocr-panel"{details_open}>
    <summary>原文OCRテキスト</summary>
    <pre><code>{esc(page_text(page))}</code></pre>
  </details>
</article>
"""


def render_page_document(
    page: int,
    sections: list[Section],
    chapters: list[Chapter],
) -> str:
    prev_link = (
        f'<a class="button" href="{esc(page_path(page - 1).split("/", 1)[1])}">前のページ</a>'
        if page > 1
        else '<span class="button disabled">前のページ</span>'
    )
    next_link = (
        f'<a class="button" href="{esc(page_path(page + 1).split("/", 1)[1])}">次のページ</a>'
        if page < PAGE_COUNT
        else '<span class="button disabled">次のページ</span>'
    )
    chapter = current_chapter_for_page(chapters, page)
    body = f"""
<nav class="breadcrumb">
  <a href="../index.html">トップ</a>
  <span>/</span>
  <a href="../{esc(chapter_path(chapter))}">{esc(chapter.japanese)}</a>
  <span>/</span>
  <span>ページ {page:03d}</span>
</nav>
<div class="reader-controls">
  {prev_link}
  <a class="button" href="../{esc(chapter_path(chapter))}">章へ戻る</a>
  {next_link}
</div>
{render_page_article(page, sections, chapters, "../", True)}
<div class="reader-controls bottom">
  {prev_link}
  <a class="button" href="../index.html">トップへ戻る</a>
  {next_link}
</div>
"""
    return html_shell(
        f"ページ {page:03d} - Opt-Var",
        body,
        "../",
        sections,
        chapters,
        page_path(page),
    )


def render_chapter_document(
    chapter: Chapter,
    sections: list[Section],
    chapters: list[Chapter],
) -> str:
    section_rows = ""
    if chapter.sections:
        section_rows = "".join(
            "<tr>"
            f'<td><a href="#{esc(section_id(section))}">{esc(section.number)}</a></td>'
            f"<td>{esc(section.japanese)}</td>"
            f"<td>{esc(section.english)}</td>"
            f'<td><a href="../{esc(page_path(section.page))}">{section.page}</a></td>'
            "</tr>"
            for section in chapter.sections
        )
        section_table = f"""
<div class="table-wrap">
  <table>
    <thead><tr><th>節</th><th>日本語</th><th>English</th><th>ページ</th></tr></thead>
    <tbody>{section_rows}</tbody>
  </table>
</div>
"""
    else:
        section_table = "<p>表紙、変更履歴、原PDF目次などの前付ページです。</p>"

    pages_html = "\n".join(
        render_page_article(page, sections, chapters, "../", False)
        for page in range(chapter.start_page, chapter.end_page + 1)
    )
    title = chapter.japanese if chapter.number == "0" else f"{chapter.number}. {chapter.japanese}"
    body = f"""
<nav class="breadcrumb">
  <a href="../index.html">トップ</a>
  <span>/</span>
  <span>{esc(title)}</span>
</nav>
<header class="chapter-header">
  <p class="eyebrow">PDF {chapter.start_page}-{chapter.end_page} ページ</p>
  <h1>{esc(title)}</h1>
  <p>{esc(chapter.english)}</p>
</header>
<section>
  <h2>この章の目次</h2>
  {section_table}
</section>
<section>
  <h2>ページ本文</h2>
  {pages_html}
</section>
"""
    return html_shell(
        f"{title} - Opt-Var",
        body,
        "../",
        sections,
        chapters,
        chapter_path(chapter),
    )


def render_reference_document(
    title: str,
    markdown_file: str,
    sections: list[Section],
    chapters: list[Chapter],
) -> str:
    source = read_text(ROOT / markdown_file)
    body = f"""
<nav class="breadcrumb">
  <a href="../index.html">トップ</a>
  <span>/</span>
  <span>{esc(title)}</span>
</nav>
<article class="reference-doc">
  {markdown_to_html(source, "../")}
</article>
"""
    output_path = f"references/{markdown_file.removesuffix('.md').lower().replace('_ja', '').replace('_', '-')}.html"
    if markdown_file == "figure_index.md":
        output_path = "references/figures.html"
    elif markdown_file == "table_index.md":
        output_path = "references/tables.html"
    elif markdown_file == "equation_candidates.md":
        output_path = "references/equations.html"
    elif markdown_file == "AUDIT_REPORT_JA.md":
        output_path = "references/audit.html"
    elif markdown_file == "TRANSLATION_NOTES_JA.md":
        output_path = "references/translation-notes.html"

    return output_path, html_shell(title, body, "../", sections, chapters, output_path)


def build_search_index(sections: list[Section], chapters: list[Chapter]) -> list[dict[str, object]]:
    index: list[dict[str, object]] = []
    for page in range(1, PAGE_COUNT + 1):
        chapter = current_chapter_for_page(chapters, page)
        nearest = closest_section_for_page(sections, page)
        section_label = nearest.japanese if nearest else chapter.japanese
        index.append(
            {
                "page": page,
                "title": f"ページ {page:03d}",
                "section": section_label,
                "chapter": chapter.japanese,
                "path": page_path(page),
                "text": page_text(page),
            }
        )
    return index


def write_assets(search_index: list[dict[str, object]]) -> None:
    write_text(OUT / "assets" / "styles.css", STYLES_CSS)
    write_text(OUT / "assets" / "app.js", APP_JS)
    payload = json.dumps(search_index, ensure_ascii=False, separators=(",", ":"))
    write_text(OUT / "assets" / "search-index.js", f"window.SEARCH_INDEX = {payload};\n")


def write_readme() -> None:
    full_report_note = (
        "\n- `full_report_ja.html`: OCR全文日本語訳レポート。\n"
        if (OUT / "full_report_ja.html").exists()
        else ""
    )
    content = """# Opt-Var 日本語 HTML テキストブック

`index.html` をブラウザで開くと、生成済みの静的HTMLテキストブックを閲覧できます。
""" + full_report_note + """

## 生成元

- `TOC_JA.md`: 日本語目次
- `raw_text/page_XXX.txt`: 検索用OCRテキスト
- `assets/page_images/page-XXX.jpg`: 視覚正本のページ画像

## 再生成

プロジェクトルートで以下を実行してください。

```bash
python3 tools/build_html_textbook.py
```

本文OCRは原文英語のままです。数式、表、図は各ページ画像を正本として確認してください。
"""
    write_text(OUT / "README.md", content)


def build() -> None:
    sections = parse_toc()
    chapters = build_chapters(sections)
    manifest = load_manifest()

    reset_generated_output()
    copy_page_images()
    write_assets(build_search_index(sections, chapters))

    write_text(OUT / "index.html", render_index(sections, chapters, manifest))
    for page in range(1, PAGE_COUNT + 1):
        write_text(OUT / page_path(page), render_page_document(page, sections, chapters))
    for chapter in chapters:
        write_text(OUT / chapter_path(chapter), render_chapter_document(chapter, sections, chapters))

    for title, markdown_file in [
        ("図版インデックス", "figure_index.md"),
        ("表インデックス", "table_index.md"),
        ("数式候補インデックス", "equation_candidates.md"),
        ("監査レポート", "AUDIT_REPORT_JA.md"),
        ("翻訳・精度メモ", "TRANSLATION_NOTES_JA.md"),
    ]:
        output_path, html_doc = render_reference_document(title, markdown_file, sections, chapters)
        write_text(OUT / output_path, html_doc)

    write_readme()


STYLES_CSS = r"""
:root {
  --bg: #f7f8f8;
  --panel: #ffffff;
  --text: #1b1f23;
  --muted: #5d666f;
  --line: #d8dddf;
  --accent: #087f8c;
  --accent-strong: #04636d;
  --accent-soft: #e7f4f5;
  --warn: #fff4d6;
  --code: #f0f3f4;
  --shadow: 0 1px 2px rgba(27, 31, 35, 0.08);
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.7;
}

a {
  color: var(--accent-strong);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

img {
  max-width: 100%;
  height: auto;
}

.skip-link {
  position: absolute;
  left: -999px;
  top: 8px;
  z-index: 10;
  padding: 8px 12px;
  background: var(--panel);
  border: 1px solid var(--line);
}

.skip-link:focus {
  left: 8px;
}

.layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
  padding: 20px 18px;
  background: var(--panel);
  border-right: 1px solid var(--line);
}

.brand {
  display: grid;
  gap: 2px;
  margin-bottom: 20px;
}

.brand a {
  color: var(--text);
  font-weight: 800;
  font-size: 1.08rem;
}

.brand span,
.eyebrow,
.chapter-card small,
.chapter-card span,
.section-heading p,
.chapter-header p,
.search-results small {
  color: var(--muted);
}

.search-box,
.page-jump {
  display: grid;
  gap: 7px;
  margin-bottom: 18px;
}

.search-box label,
.page-jump label {
  font-size: 0.82rem;
  font-weight: 700;
}

input,
button {
  font: inherit;
}

.search-box input,
.page-jump input {
  width: 100%;
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
}

.page-jump div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
}

.page-jump button,
.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 7px 12px;
  background: #fff;
  color: var(--text);
  cursor: pointer;
}

.button.primary {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.button.disabled {
  color: #98a1a8;
  cursor: default;
}

.search-results {
  display: none;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  box-shadow: var(--shadow);
  overflow: hidden;
}

.search-results.visible {
  display: block;
}

.search-results a,
.search-results .empty {
  display: grid;
  gap: 3px;
  padding: 10px;
  border-top: 1px solid var(--line);
}

.search-results a:first-child,
.search-results .empty:first-child {
  border-top: 0;
}

.search-results strong {
  color: var(--text);
}

.search-results mark {
  background: var(--warn);
  color: var(--text);
  padding: 0 2px;
}

.sidebar h2 {
  margin: 18px 0 8px;
  font-size: 0.9rem;
}

.sidebar details {
  margin-top: 14px;
}

.sidebar summary {
  cursor: pointer;
  font-weight: 700;
}

.nav-list {
  display: grid;
  gap: 2px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.nav-list a {
  display: block;
  padding: 7px 8px;
  border-radius: 8px;
  color: var(--text);
  font-size: 0.92rem;
}

.nav-list a:hover,
.nav-list a.active {
  background: var(--accent-soft);
  text-decoration: none;
}

.toc-list a {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 6px;
  font-size: 0.86rem;
}

.toc-num {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.content {
  width: min(1180px, 100%);
  padding: 30px clamp(18px, 4vw, 52px) 70px;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(220px, 0.6fr);
  gap: 28px;
  align-items: start;
  margin-bottom: 28px;
}

h1,
h2,
h3 {
  line-height: 1.25;
}

h1 {
  margin: 5px 0 14px;
  font-size: clamp(2rem, 4vw, 3.1rem);
}

h2 {
  margin-top: 30px;
}

.lead {
  max-width: 760px;
  font-size: 1.08rem;
}

.actions,
.reader-controls {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.cover {
  margin: 0;
  padding: 12px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: var(--shadow);
}

.cover img {
  display: block;
  border: 1px solid var(--line);
}

.notice,
.page-article,
.reference-doc {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: var(--shadow);
}

.notice {
  padding: 18px 20px;
}

.notice h2 {
  margin-top: 0;
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 20px 0 28px;
}

.stat {
  padding: 16px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}

.stat strong {
  display: block;
  font-size: 1.6rem;
}

.stat span {
  color: var(--muted);
}

.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
}

.section-heading h2 {
  margin-bottom: 0;
}

.section-heading p {
  max-width: 620px;
  margin-bottom: 0;
}

.chapter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.chapter-card,
.resource-grid a {
  display: grid;
  gap: 6px;
  min-height: 130px;
  padding: 15px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  color: var(--text);
  box-shadow: var(--shadow);
}

.chapter-card:hover,
.resource-grid a:hover {
  border-color: var(--accent);
  text-decoration: none;
}

.chapter-number {
  width: max-content;
  min-width: 34px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-strong);
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.resource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.resource-grid a {
  min-height: 74px;
  align-content: center;
  font-weight: 700;
}

.page-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(52px, 1fr));
  gap: 6px;
  margin-top: 16px;
}

.page-grid a {
  display: grid;
  place-items: center;
  min-height: 34px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  font-variant-numeric: tabular-nums;
}

.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  color: var(--muted);
  margin-bottom: 18px;
}

.chapter-header {
  margin-bottom: 20px;
}

.chapter-header h1 {
  margin-bottom: 6px;
}

.reader-controls {
  margin: 14px 0 18px;
}

.reader-controls.bottom {
  margin-top: 20px;
}

.page-article {
  margin: 18px 0;
  overflow: hidden;
}

.page-header {
  padding: 16px 18px 8px;
}

.page-header h2 {
  margin: 2px 0 8px;
}

.section-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.section-badge {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent-strong);
  font-size: 0.85rem;
  font-weight: 700;
}

.section-badge.muted {
  background: var(--code);
  color: var(--muted);
}

.page-image {
  margin: 0;
  padding: 14px;
  background: #f2f5f5;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}

.page-image img,
.doc-image img {
  display: block;
  margin: 0 auto;
  border: 1px solid var(--line);
  background: #fff;
}

.ocr-panel {
  padding: 0 16px 16px;
}

.ocr-panel summary {
  cursor: pointer;
  padding: 12px 0;
  font-weight: 700;
}

pre {
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--code);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  line-height: 1.55;
}

code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
  font-size: 0.92em;
}

.table-wrap {
  overflow-x: auto;
  margin: 14px 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
}

th,
td {
  border: 1px solid var(--line);
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

th {
  background: #eef2f2;
}

.reference-doc {
  padding: 20px;
}

.reference-doc h1:first-child {
  margin-top: 0;
}

.doc-image {
  margin: 18px 0;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #f2f5f5;
}

.doc-image img {
  max-height: 760px;
}

.doc-image figcaption {
  margin-top: 8px;
  color: var(--muted);
  font-size: 0.9rem;
}

@media (max-width: 920px) {
  .layout {
    display: block;
  }

  .sidebar {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--line);
  }

  .content {
    padding-top: 22px;
  }

  .hero {
    grid-template-columns: 1fr;
  }

  .cover {
    max-width: 360px;
  }

  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .content {
    padding-inline: 14px;
  }

  .stats {
    grid-template-columns: 1fr;
  }

  .section-heading {
    display: block;
  }

  .page-image {
    padding: 8px;
  }
}
"""


APP_JS = r"""
(function () {
  const root = document.body.dataset.root || "";
  const searchIndex = window.SEARCH_INDEX || [];
  const forms = document.querySelectorAll("[data-search-form]");
  const inputs = document.querySelectorAll("[data-search-input]");
  const results = document.querySelectorAll("[data-search-results]");
  const pageJumpForms = document.querySelectorAll("[data-page-jump]");

  function normalize(value) {
    return (value || "").toString().toLowerCase();
  }

  function escapeHtml(value) {
    return value.replace(/[&<>"']/g, function (char) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char];
    });
  }

  function makeSnippet(text, query) {
    const normalizedText = normalize(text);
    const normalizedQuery = normalize(query);
    const found = normalizedText.indexOf(normalizedQuery);
    const start = Math.max(0, found - 55);
    const end = Math.min(text.length, found + query.length + 85);
    let snippet = text.slice(start, end).replace(/\s+/g, " ").trim();
    if (start > 0) snippet = "... " + snippet;
    if (end < text.length) snippet += " ...";
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return escapeHtml(snippet).replace(new RegExp(escapedQuery, "ig"), function (match) {
      return "<mark>" + escapeHtml(match) + "</mark>";
    });
  }

  function renderSearch(query) {
    const trimmed = query.trim();
    results.forEach(function (target) {
      if (trimmed.length < 2) {
        target.classList.remove("visible");
        target.innerHTML = "";
        return;
      }

      const normalizedQuery = normalize(trimmed);
      const matches = searchIndex
        .map(function (item) {
          const haystack = normalize([item.title, item.section, item.chapter, item.text].join(" "));
          const score = haystack.indexOf(normalizedQuery);
          return score === -1 ? null : { item: item, score: score };
        })
        .filter(Boolean)
        .sort(function (a, b) {
          return a.score - b.score || a.item.page - b.item.page;
        })
        .slice(0, 8);

      target.classList.add("visible");
      if (!matches.length) {
        target.innerHTML = '<div class="empty">該当ページがありません。</div>';
        return;
      }

      target.innerHTML = matches.map(function (match) {
        const item = match.item;
        return [
          '<a href="',
          root + item.path,
          '"><strong>',
          escapeHtml(item.title),
          " / ",
          escapeHtml(item.section),
          "</strong><small>",
          makeSnippet(item.text, trimmed),
          "</small></a>"
        ].join("");
      }).join("");
    });
  }

  forms.forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const input = form.querySelector("[data-search-input]");
      renderSearch(input ? input.value : "");
    });
  });

  inputs.forEach(function (input) {
    input.addEventListener("input", function () {
      renderSearch(input.value);
    });
  });

  pageJumpForms.forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      const input = form.querySelector("input[name='page']");
      const value = input ? parseInt(input.value, 10) : NaN;
      if (!Number.isFinite(value) || value < 1 || value > 136) return;
      window.location.href = root + "pages/page-" + String(value).padStart(3, "0") + ".html";
    });
  });
})();
"""


if __name__ == "__main__":
    build()
    print(f"Built {OUT}")
