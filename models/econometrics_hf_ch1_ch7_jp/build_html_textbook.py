#!/usr/bin/env python3
"""Build a static Japanese HTML textbook from the Markdown study package."""

from __future__ import annotations

import hashlib
import html
import json
import posixpath
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = PROJECT_DIR / "econometrics_hf_ch1_ch7_markdown_ja"
OUT_DIR = PROJECT_DIR / "html_textbook"
MARKER = OUT_DIR / ".generated_by_build_html_textbook"


STYLE_CSS = r"""
:root {
  color-scheme: light;
  --bg: #f6f8f9;
  --surface: #ffffff;
  --surface-raised: #ffffff;
  --text: #17201f;
  --muted: #5f6f6d;
  --line: #d8e0df;
  --accent: #00796b;
  --accent-strong: #00594f;
  --accent-soft: #e4f3f1;
  --code-bg: #eef3f2;
  --shadow: 0 10px 30px rgba(20, 32, 31, 0.08);
  --sidebar-width: 300px;
}

:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #121615;
  --surface: #191f1e;
  --surface-raised: #202827;
  --text: #edf4f2;
  --muted: #a9b8b5;
  --line: #33403d;
  --accent: #34b6a7;
  --accent-strong: #62d0c3;
  --accent-soft: #173532;
  --code-bg: #0e1211;
  --shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
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
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Sans",
    "Yu Gothic", "Noto Sans JP", sans-serif;
  line-height: 1.78;
}

a {
  color: var(--accent-strong);
  text-decoration-thickness: 0.08em;
  text-underline-offset: 0.16em;
}

img {
  max-width: 100%;
  height: auto;
}

.skip-link {
  position: absolute;
  left: 1rem;
  top: -4rem;
  z-index: 20;
  padding: 0.5rem 0.75rem;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
}

.skip-link:focus {
  top: 1rem;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-height: 56px;
  padding: 0.5rem 1rem;
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(10px);
}

.topbar-title {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  color: var(--muted);
  font-size: 0.95rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-button,
.text-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-raised);
  color: var(--text);
  cursor: pointer;
  font: inherit;
}

.icon-button {
  width: 40px;
  font-size: 1.1rem;
}

.text-button {
  padding: 0 0.75rem;
  text-decoration: none;
}

.book-shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
  min-height: calc(100vh - 56px);
}

.sidebar {
  position: sticky;
  top: 56px;
  height: calc(100vh - 56px);
  overflow-y: auto;
  padding: 1rem;
  border-right: 1px solid var(--line);
  background: var(--surface);
}

.brand {
  display: block;
  margin-bottom: 1rem;
  color: var(--text);
  font-weight: 700;
  line-height: 1.35;
  text-decoration: none;
}

.brand small {
  display: block;
  margin-top: 0.2rem;
  color: var(--muted);
  font-size: 0.8rem;
  font-weight: 500;
}

.nav-search {
  width: 100%;
  margin-bottom: 0.75rem;
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text);
  font: inherit;
}

.nav-section-title {
  margin: 1.1rem 0 0.45rem;
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.nav-list {
  display: grid;
  gap: 0.25rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.nav-link {
  display: block;
  padding: 0.48rem 0.6rem;
  border-radius: 8px;
  color: var(--text);
  font-size: 0.92rem;
  line-height: 1.4;
  text-decoration: none;
}

.nav-link:hover,
.nav-link[aria-current="page"] {
  background: var(--accent-soft);
  color: var(--accent-strong);
}

.main-wrap {
  min-width: 0;
}

.content {
  width: min(100%, 1040px);
  margin: 0 auto;
  padding: 2rem clamp(1rem, 3vw, 3rem) 4rem;
}

.hero {
  padding: clamp(1.2rem, 3vw, 2rem);
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}

.hero h1 {
  margin-top: 0;
  font-size: clamp(1.85rem, 4vw, 3.15rem);
  line-height: 1.18;
}

.hero p {
  color: var(--muted);
  font-size: 1.05rem;
}

.meta-grid,
.chapter-grid {
  display: grid;
  gap: 1rem;
}

.meta-grid {
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  margin: 1.25rem 0;
}

.metric {
  padding: 0.9rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--bg);
}

.metric strong {
  display: block;
  font-size: 1.35rem;
}

.metric span {
  color: var(--muted);
  font-size: 0.9rem;
}

.chapter-grid {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  margin-top: 1rem;
}

.chapter-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  min-height: 100%;
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  text-decoration: none;
  box-shadow: var(--shadow);
}

.chapter-card:hover {
  border-color: var(--accent);
}

.chapter-card h3 {
  margin: 0;
  font-size: 1.05rem;
  line-height: 1.42;
}

.chapter-card p,
.chapter-card small {
  margin: 0;
  color: var(--muted);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: auto;
}

.chip {
  padding: 0.15rem 0.45rem;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--bg);
  color: var(--muted);
  font-size: 0.78rem;
}

.article {
  padding: clamp(1rem, 3vw, 2.2rem);
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow);
}

.article h1,
.article h2,
.article h3,
.article h4 {
  line-height: 1.35;
}

.article h1 {
  margin-top: 0;
  font-size: clamp(1.7rem, 3vw, 2.45rem);
}

.article h2 {
  margin-top: 2.2rem;
  padding-top: 0.8rem;
  border-top: 1px solid var(--line);
  font-size: 1.45rem;
}

.article h3 {
  margin-top: 1.8rem;
  font-size: 1.16rem;
}

.article p,
.article li {
  overflow-wrap: anywhere;
}

.article blockquote {
  margin: 1.25rem 0;
  padding: 0.85rem 1rem;
  border-left: 4px solid var(--accent);
  border-radius: 0 8px 8px 0;
  background: var(--accent-soft);
}

.article blockquote p {
  margin: 0;
}

.article code {
  padding: 0.1rem 0.28rem;
  border-radius: 5px;
  background: var(--code-bg);
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  font-size: 0.92em;
}

.article pre {
  overflow-x: auto;
  max-height: 62vh;
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--code-bg);
  line-height: 1.45;
}

.article pre code {
  padding: 0;
  background: transparent;
  white-space: pre;
}

.figure,
.page-render {
  margin: 1.4rem 0;
}

.figure img,
.page-render img {
  display: block;
  margin: 0 auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  box-shadow: var(--shadow);
}

.page-render img {
  width: min(100%, 820px);
}

.figure figcaption,
.page-render figcaption {
  margin-top: 0.45rem;
  color: var(--muted);
  font-size: 0.88rem;
  text-align: center;
}

.table-wrap {
  overflow-x: auto;
  margin: 1.25rem 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.95rem;
}

th,
td {
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--line);
  vertical-align: top;
}

th {
  background: var(--code-bg);
  text-align: left;
}

.toc {
  margin: 0 0 1rem;
  padding: 0.85rem 1rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
}

.toc-title {
  margin: 0 0 0.45rem;
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.toc ol {
  display: grid;
  gap: 0.2rem;
  margin: 0;
  padding-left: 1.2rem;
}

.toc a {
  color: var(--text);
  text-decoration: none;
}

.toc a:hover {
  color: var(--accent-strong);
  text-decoration: underline;
}

.toc .level-3 {
  margin-left: 1rem;
  font-size: 0.94rem;
}

.pager {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin: 1.25rem 0;
}

.pager a {
  max-width: 50%;
  padding: 0.65rem 0.8rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  text-decoration: none;
}

.pager a:hover {
  border-color: var(--accent);
  color: var(--accent-strong);
}

.progress {
  position: fixed;
  left: 0;
  top: 0;
  z-index: 30;
  width: 100%;
  height: 3px;
  pointer-events: none;
}

.progress-bar {
  width: 0%;
  height: 100%;
  background: var(--accent);
}

@media (max-width: 900px) {
  .book-shell {
    display: block;
  }

  .sidebar {
    position: fixed;
    inset: 56px auto 0 0;
    z-index: 15;
    width: min(86vw, var(--sidebar-width));
    transform: translateX(-105%);
    transition: transform 160ms ease;
    box-shadow: var(--shadow);
  }

  body.sidebar-open .sidebar {
    transform: translateX(0);
  }

  .content {
    padding-top: 1rem;
  }

  .pager {
    display: grid;
  }

  .pager a {
    max-width: none;
  }
}
"""


APP_JS = r"""
(function () {
  const root = document.documentElement;
  const themeButton = document.querySelector("[data-theme-toggle]");
  const storedTheme = localStorage.getItem("textbook-theme");

  if (storedTheme) {
    root.dataset.theme = storedTheme;
  }

  function syncThemeButton() {
    if (!themeButton) return;
    themeButton.textContent = root.dataset.theme === "dark" ? "☀" : "☾";
    themeButton.setAttribute(
      "aria-label",
      root.dataset.theme === "dark" ? "ライトモードに切り替え" : "ダークモードに切り替え"
    );
  }

  syncThemeButton();

  themeButton?.addEventListener("click", function () {
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    localStorage.setItem("textbook-theme", root.dataset.theme);
    syncThemeButton();
  });

  document.querySelector("[data-menu-toggle]")?.addEventListener("click", function () {
    document.body.classList.toggle("sidebar-open");
  });

  document.addEventListener("click", function (event) {
    const target = event.target;
    if (!(target instanceof Element)) return;
    if (target.closest(".sidebar") || target.closest("[data-menu-toggle]")) return;
    document.body.classList.remove("sidebar-open");
  });

  const search = document.querySelector("[data-nav-search]");
  const navItems = Array.from(document.querySelectorAll("[data-nav-item]"));

  search?.addEventListener("input", function () {
    const query = search.value.trim().toLowerCase();
    navItems.forEach(function (item) {
      item.hidden = query.length > 0 && !item.textContent.toLowerCase().includes(query);
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
    const active = document.activeElement;
    if (active && ["INPUT", "TEXTAREA"].includes(active.tagName)) return;
    event.preventDefault();
    search?.focus();
  });

  const progress = document.querySelector("[data-progress]");
  function updateProgress() {
    if (!progress) return;
    const doc = document.documentElement;
    const max = doc.scrollHeight - doc.clientHeight;
    const value = max > 0 ? (doc.scrollTop / max) * 100 : 0;
    progress.style.width = value + "%";
  }

  updateProgress();
  document.addEventListener("scroll", updateProgress, { passive: true });
})();
"""


@dataclass
class Heading:
    level: int
    text: str
    anchor: str


@dataclass
class RenderedMarkdown:
    html: str
    title: str
    headings: list[Heading]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def strip_markdown(text: str) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return text.strip()


def slugify(text: str, used: dict[str, int]) -> str:
    plain = strip_markdown(text).lower()
    plain = re.sub(r"[^\w\s.-]+", "", plain, flags=re.UNICODE)
    plain = re.sub(r"[\s.]+", "-", plain).strip("-")
    if not plain:
        plain = "section"
    if len(plain) > 80:
        digest = hashlib.sha1(plain.encode("utf-8")).hexdigest()[:8]
        plain = f"{plain[:70].strip('-')}-{digest}"
    count = used.get(plain, 0)
    used[plain] = count + 1
    return plain if count == 0 else f"{plain}-{count + 1}"


def split_target(target: str) -> tuple[str, str]:
    if "#" not in target:
        return target, ""
    base, fragment = target.split("#", 1)
    return base, f"#{fragment}"


def is_external_target(target: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target)) or target.startswith("#")


def rel_href(target_from_out_root: str, current_subdir: str) -> str:
    return posixpath.relpath(target_from_out_root, current_subdir or ".")


def output_path_for_source(source_path: Path) -> str | None:
    name = source_path.name
    if name == "README.md":
        return "about.html"
    if name == "contents_ja.md":
        return "contents.html"
    if name == "embedded_images.md":
        return "embedded_images.html"
    if name.startswith("QA_REPORT_ja"):
        return "qa.html"
    if source_path.parent.name == "chapters" and source_path.suffix == ".md":
        return f"chapters/{source_path.stem}.html"
    try:
        rel = source_path.relative_to(SOURCE_DIR)
    except ValueError:
        return None
    return rel.as_posix()


def resolve_target(target: str, source_md: Path, current_subdir: str) -> str:
    if is_external_target(target):
        return target

    base, fragment = split_target(target)
    if not base:
        return target

    source_target = (source_md.parent / base).resolve()
    output_target = output_path_for_source(source_target)
    if source_target.suffix == ".md" and output_target:
        return rel_href(output_target, current_subdir) + fragment

    try:
        rel_to_source = source_target.relative_to(SOURCE_DIR)
    except ValueError:
        return target

    return rel_href(rel_to_source.as_posix(), current_subdir) + fragment


class MarkdownRenderer:
    def __init__(self, source_md: Path, current_subdir: str) -> None:
        self.source_md = source_md
        self.current_subdir = current_subdir
        self.used_anchors: dict[str, int] = {}
        self.headings: list[Heading] = []
        self.title = source_md.stem

    def inline(self, text: str) -> str:
        code_spans: list[str] = []

        def stash_code(match: re.Match[str]) -> str:
            code_spans.append(f"<code>{html.escape(match.group(1))}</code>")
            return f"\u0000CODE{len(code_spans) - 1}\u0000"

        text = re.sub(r"`([^`]+)`", stash_code, text)
        text = html.escape(text, quote=False)

        def image_repl(match: re.Match[str]) -> str:
            alt = html.unescape(match.group(1))
            raw_target = html.unescape(match.group(2)).strip()
            href = resolve_target(raw_target, self.source_md, self.current_subdir)
            return (
                f'<img src="{html.escape(href, quote=True)}" '
                f'alt="{html.escape(alt, quote=True)}" loading="lazy" decoding="async">'
            )

        def link_repl(match: re.Match[str]) -> str:
            label = match.group(1)
            raw_target = html.unescape(match.group(2)).strip()
            href = resolve_target(raw_target, self.source_md, self.current_subdir)
            attrs = ""
            if re.match(r"^https?://", href):
                attrs = ' target="_blank" rel="noopener"'
            return f'<a href="{html.escape(href, quote=True)}"{attrs}>{label}</a>'

        text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", image_repl, text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_repl, text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        for idx, code in enumerate(code_spans):
            text = text.replace(f"\u0000CODE{idx}\u0000", code)
        return text

    def parse_table(self, lines: list[str], start: int) -> tuple[str, int] | None:
        if start + 1 >= len(lines):
            return None
        if not lines[start].lstrip().startswith("|") or not is_table_separator(lines[start + 1]):
            return None

        rows: list[str] = []
        idx = start
        while idx < len(lines) and lines[idx].lstrip().startswith("|"):
            rows.append(lines[idx])
            idx += 1

        header = split_table_row(rows[0])
        aligns = parse_alignments(rows[1])
        body_rows = [split_table_row(row) for row in rows[2:]]

        parts = ['<div class="table-wrap"><table>']
        parts.append("<thead><tr>")
        for col_idx, cell in enumerate(header):
            align = alignment_attr(aligns, col_idx)
            parts.append(f"<th{align}>{self.inline(cell.strip())}</th>")
        parts.append("</tr></thead>")
        if body_rows:
            parts.append("<tbody>")
            for row in body_rows:
                parts.append("<tr>")
                for col_idx, cell in enumerate(row):
                    align = alignment_attr(aligns, col_idx)
                    parts.append(f"<td{align}>{self.inline(cell.strip())}</td>")
                parts.append("</tr>")
            parts.append("</tbody>")
        parts.append("</table></div>")
        return "\n".join(parts), idx

    def render(self, markdown: str) -> RenderedMarkdown:
        lines = markdown.splitlines()
        out: list[str] = []
        paragraph: list[str] = []
        list_items: list[str] = []
        list_type: str | None = None
        quote_lines: list[str] = []
        in_code = False
        code_lines: list[str] = []

        def flush_paragraph() -> None:
            nonlocal paragraph
            if paragraph:
                out.append(f"<p>{self.inline(' '.join(paragraph))}</p>")
                paragraph = []

        def flush_list() -> None:
            nonlocal list_items, list_type
            if list_items:
                tag = "ol" if list_type == "ol" else "ul"
                out.append(f"<{tag}>")
                out.extend(f"<li>{item}</li>" for item in list_items)
                out.append(f"</{tag}>")
                list_items = []
                list_type = None

        def flush_quote() -> None:
            nonlocal quote_lines
            if quote_lines:
                out.append(f"<blockquote><p>{self.inline(' '.join(quote_lines))}</p></blockquote>")
                quote_lines = []

        def flush_blocks() -> None:
            flush_paragraph()
            flush_list()
            flush_quote()

        idx = 0
        while idx < len(lines):
            line = lines[idx]

            if in_code:
                if line.startswith("```"):
                    out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                    code_lines = []
                    in_code = False
                else:
                    code_lines.append(line)
                idx += 1
                continue

            if line.startswith("```"):
                flush_blocks()
                in_code = True
                code_lines = []
                idx += 1
                continue

            table = self.parse_table(lines, idx)
            if table:
                flush_blocks()
                table_html, idx = table
                out.append(table_html)
                continue

            if not line.strip():
                flush_blocks()
                idx += 1
                continue

            heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if heading:
                flush_blocks()
                level = len(heading.group(1))
                raw_text = heading.group(2)
                text = strip_markdown(raw_text)
                anchor = slugify(raw_text, self.used_anchors)
                if level == 1 and self.title == self.source_md.stem:
                    self.title = text
                self.headings.append(Heading(level=level, text=text, anchor=anchor))
                out.append(
                    f'<h{level} id="{html.escape(anchor, quote=True)}">'
                    f'{self.inline(raw_text)}'
                    f'<a class="heading-anchor" href="#{html.escape(anchor, quote=True)}" aria-label="この見出しへのリンク">#</a>'
                    f"</h{level}>"
                )
                idx += 1
                continue

            image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line.strip())
            if image:
                flush_blocks()
                alt = image.group(1)
                raw_target = image.group(2).strip()
                href = resolve_target(raw_target, self.source_md, self.current_subdir)
                klass = "page-render" if "PDF page" in alt else "figure"
                out.append(
                    f'<figure class="{klass}">'
                    f'<a href="{html.escape(href, quote=True)}">'
                    f'<img src="{html.escape(href, quote=True)}" alt="{html.escape(alt, quote=True)}" loading="lazy" decoding="async">'
                    f"</a>"
                    f"<figcaption>{html.escape(alt)}</figcaption>"
                    f"</figure>"
                )
                idx += 1
                continue

            unordered = re.match(r"^\s*[-*]\s+(.+)$", line)
            ordered = re.match(r"^\s*\d+\.\s+(.+)$", line)
            if unordered or ordered:
                flush_paragraph()
                flush_quote()
                item_type = "ol" if ordered else "ul"
                if list_type and list_type != item_type:
                    flush_list()
                list_type = item_type
                list_items.append(self.inline((ordered or unordered).group(1)))
                idx += 1
                continue

            if line.startswith(">"):
                flush_paragraph()
                flush_list()
                quote_lines.append(line.lstrip("> ").strip())
                idx += 1
                continue

            flush_list()
            flush_quote()
            paragraph.append(line.strip())
            idx += 1

        if in_code:
            out.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
        flush_blocks()
        return RenderedMarkdown(html="\n".join(out), title=self.title, headings=self.headings)


def is_table_separator(line: str) -> bool:
    if not line.lstrip().startswith("|"):
        return False
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def parse_alignments(line: str) -> list[str]:
    aligns = []
    for cell in split_table_row(line):
        cell = cell.strip()
        if cell.startswith(":") and cell.endswith(":"):
            aligns.append("center")
        elif cell.endswith(":"):
            aligns.append("right")
        else:
            aligns.append("left")
    return aligns


def alignment_attr(aligns: list[str], idx: int) -> str:
    if idx >= len(aligns):
        return ""
    return f' style="text-align: {aligns[idx]}"'


def render_markdown_file(source_md: Path, current_subdir: str) -> RenderedMarkdown:
    renderer = MarkdownRenderer(source_md=source_md, current_subdir=current_subdir)
    return renderer.render(read_text(source_md))


def build_toc(rendered: RenderedMarkdown, current_subdir: str) -> str:
    visible = [
        h
        for h in rendered.headings
        if h.level in (2, 3) and not h.text.startswith("PDF page")
    ]
    if not visible:
        return ""
    items = []
    for heading in visible:
        items.append(
            f'<li class="level-{heading.level}"><a href="#{html.escape(heading.anchor, quote=True)}">'
            f"{html.escape(heading.text)}</a></li>"
        )
    return (
        '<nav class="toc" aria-label="ページ内目次">'
        '<p class="toc-title">ページ内目次</p>'
        "<ol>"
        + "\n".join(items)
        + "</ol></nav>"
    )


def chapter_filename(chapter: dict) -> str:
    return Path(chapter["file"]).with_suffix(".html").name


def build_sidebar(metadata: dict, active: str, current_subdir: str) -> str:
    def link(target: str, label: str, key: str) -> str:
        current = ' aria-current="page"' if key == active else ""
        return (
            f'<li data-nav-item><a class="nav-link" href="{html.escape(rel_href(target, current_subdir), quote=True)}"{current}>'
            f"{html.escape(label)}</a></li>"
        )

    chapter_links = []
    for chapter in metadata["chapters"]:
        label = f"第{chapter['no']}章 {chapter['ja']}"
        chapter_links.append(link(f"chapters/{chapter_filename(chapter)}", label, f"ch{chapter['no']:02d}"))

    utility_links = [
        link("index.html", "ホーム", "index"),
        link("contents.html", "章一覧と使い方", "contents"),
        link("embedded_images.html", "埋め込み図版", "embedded_images"),
        link("qa.html", "QAレポート", "qa"),
        link("about.html", "README", "about"),
    ]

    return (
        '<aside class="sidebar" aria-label="テキストブック ナビゲーション">'
        f'<a class="brand" href="{html.escape(rel_href("index.html", current_subdir), quote=True)}">'
        "高頻度金融データの計量経済学"
        "<small>第1〜7章 日本語HTML版</small></a>"
        '<input class="nav-search" data-nav-search type="search" placeholder="章を検索 /" aria-label="ナビゲーション検索">'
        '<p class="nav-section-title">教材</p><ul class="nav-list">'
        + "".join(utility_links)
        + '</ul><p class="nav-section-title">章</p><ul class="nav-list">'
        + "".join(chapter_links)
        + "</ul></aside>"
    )


def page_shell(
    *,
    metadata: dict,
    title: str,
    body: str,
    active: str,
    current_subdir: str,
    toc: str = "",
) -> str:
    css_href = rel_href("style.css", current_subdir)
    js_href = rel_href("app.js", current_subdir)
    sidebar = build_sidebar(metadata, active, current_subdir)
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} | 高頻度金融データの計量経済学</title>
  <link rel="stylesheet" href="{html.escape(css_href, quote=True)}">
</head>
<body>
  <a class="skip-link" href="#main">本文へ移動</a>
  <div class="progress" aria-hidden="true"><div class="progress-bar" data-progress></div></div>
  <header class="topbar">
    <button class="icon-button" type="button" data-menu-toggle aria-label="ナビゲーションを開閉">☰</button>
    <div class="topbar-title">{html.escape(title)}</div>
    <button class="icon-button" type="button" data-theme-toggle aria-label="テーマを切り替え">☾</button>
  </header>
  <div class="book-shell">
    {sidebar}
    <main id="main" class="main-wrap">
      <div class="content">
        {toc}
        {body}
      </div>
    </main>
  </div>
  <script src="{html.escape(js_href, quote=True)}"></script>
</body>
</html>
"""


def extract_section(markdown: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*\n(?P<body>.*?)(?=^## |\Z)"
    match = re.search(pattern, markdown, flags=re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    body = match.group("body").strip()
    body = re.sub(r"^### .*$", "", body, flags=re.MULTILINE).strip()
    paragraphs = [p.strip().replace("\n", " ") for p in body.split("\n\n") if p.strip()]
    return paragraphs[0] if paragraphs else ""


def extract_concepts(markdown: str) -> list[str]:
    pattern = r"^## 重要概念\s*\n(?P<body>.*?)(?=^## |\Z)"
    match = re.search(pattern, markdown, flags=re.MULTILINE | re.DOTALL)
    if not match:
        return []
    text = match.group("body").strip().splitlines()[0]
    concepts = [item.strip() for item in re.split(r"[,、]", text) if item.strip()]
    return concepts[:6]


def build_index(metadata: dict) -> str:
    chapter_cards = []
    for chapter in metadata["chapters"]:
        md_path = SOURCE_DIR / "chapters" / chapter["file"]
        md = read_text(md_path)
        summary = extract_section(md, "この章の位置づけ")
        concepts = extract_concepts(md)
        chips = "".join(f'<span class="chip">{html.escape(concept)}</span>' for concept in concepts)
        href = f"chapters/{chapter_filename(chapter)}"
        chapter_cards.append(
            f'<a class="chapter-card" href="{html.escape(href, quote=True)}">'
            f"<small>PDF {html.escape(chapter['pdf'])} / 書籍 {html.escape(chapter['printed'])}</small>"
            f"<h3>第{chapter['no']}章: {html.escape(chapter['ja'])}</h3>"
            f"<p>{html.escape(summary)}</p>"
            f'<div class="chips">{chips}</div>'
            "</a>"
        )

    counts = metadata.get("counts", {})
    body = f"""
<section class="hero">
  <h1>Econometrics of Financial High-Frequency Data<br>第1〜7章 日本語HTMLテキストブック</h1>
  <p>Markdown版の日本語学習パッケージを、ブラウザで読みやすい静的HTML教材として再構成しました。各章は日本語要約、重要概念、学習上の読み方、原文抽出、ページ画像レンダーを含みます。</p>
  <div class="meta-grid">
    <div class="metric"><strong>{html.escape(str(counts.get("chapters_md", 7)))}</strong><span>章</span></div>
    <div class="metric"><strong>{html.escape(str(counts.get("page_renders", 194)))}</strong><span>ページ画像</span></div>
    <div class="metric"><strong>{html.escape(str(counts.get("embedded_images", 11)))}</strong><span>埋め込み図版</span></div>
    <div class="metric"><strong>{html.escape(metadata.get("coverage", {}).get("printed_pages", "1-194"))}</strong><span>書籍ページ範囲</span></div>
  </div>
  <p>注意: このHTML版は既存の日本語学習版Markdownをもとにした教材です。完全な逐語訳ではなく、数式・図表はページ画像レンダーを正本として確認する構成です。</p>
</section>

<section>
  <h2>章一覧</h2>
  <div class="chapter-grid">
    {"".join(chapter_cards)}
  </div>
</section>

<section class="article">
  <h2>読み方</h2>
  <ol>
    <li>各章冒頭の日本語要約で、章の位置づけと主要概念を確認する。</li>
    <li>必要な節を読んだ後、ページ画像レンダーで数式・図表・表の形を確認する。</li>
    <li>原文の細部や引用関係を確認したい場合は、章後半の原文ページ別抽出または raw text を参照する。</li>
  </ol>
</section>
"""
    return page_shell(metadata=metadata, title="ホーム", body=body, active="index", current_subdir=".")


def build_pager(metadata: dict, chapter_no: int, current_subdir: str) -> str:
    chapters = metadata["chapters"]
    index = chapter_no - 1
    links = []
    if index > 0:
        prev = chapters[index - 1]
        href = rel_href(f"chapters/{chapter_filename(prev)}", current_subdir)
        links.append(f'<a href="{html.escape(href, quote=True)}">← 第{prev["no"]}章 {html.escape(prev["ja"])}</a>')
    else:
        links.append("<span></span>")
    if index + 1 < len(chapters):
        nxt = chapters[index + 1]
        href = rel_href(f"chapters/{chapter_filename(nxt)}", current_subdir)
        links.append(f'<a href="{html.escape(href, quote=True)}">第{nxt["no"]}章 {html.escape(nxt["ja"])} →</a>')
    else:
        href = rel_href("index.html", current_subdir)
        links.append(f'<a href="{html.escape(href, quote=True)}">ホームへ戻る →</a>')
    return f'<nav class="pager" aria-label="前後の章">{"".join(links)}</nav>'


def build_chapter_pages(metadata: dict) -> list[dict]:
    search_entries: list[dict] = []
    for chapter in metadata["chapters"]:
        source = SOURCE_DIR / "chapters" / chapter["file"]
        rendered = render_markdown_file(source, "chapters")
        pager = build_pager(metadata, chapter["no"], "chapters")
        body = f'{pager}<article class="article">{rendered.html}</article>{pager}'
        toc = build_toc(rendered, "chapters")
        title = f"第{chapter['no']}章: {chapter['ja']}"
        html_page = page_shell(
            metadata=metadata,
            title=title,
            body=body,
            active=f"ch{chapter['no']:02d}",
            current_subdir="chapters",
            toc=toc,
        )
        write_text(OUT_DIR / "chapters" / chapter_filename(chapter), html_page)
        search_entries.append(
            {
                "title": title,
                "href": f"chapters/{chapter_filename(chapter)}",
                "headings": [
                    {"level": h.level, "text": h.text, "anchor": h.anchor}
                    for h in rendered.headings
                    if h.level <= 3 and not h.text.startswith("PDF page")
                ],
            }
        )
    return search_entries


def build_markdown_page(metadata: dict, source_name: str, output_name: str, title: str, active: str) -> None:
    source = SOURCE_DIR / source_name
    rendered = render_markdown_file(source, ".")
    body = f'<article class="article">{rendered.html}</article>'
    page = page_shell(
        metadata=metadata,
        title=title,
        body=body,
        active=active,
        current_subdir=".",
        toc=build_toc(rendered, "."),
    )
    write_text(OUT_DIR / output_name, page)


def copy_tree_filtered(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for path in src.rglob("*"):
        if path.name.endswith(":Zone.Identifier"):
            continue
        rel = path.relative_to(src)
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def prepare_output_dir() -> None:
    if OUT_DIR.exists():
        if not MARKER.exists():
            raise SystemExit(
                f"Refusing to overwrite {OUT_DIR}; marker file is missing. "
                "Move it aside or remove it manually if it is disposable."
            )
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True)
    write_text(MARKER, "Generated by build_html_textbook.py\n")


def validate_links() -> list[str]:
    problems: list[str] = []
    attr_re = re.compile(r'(?:href|src)="([^"]+)"')
    for html_file in OUT_DIR.rglob("*.html"):
        content = read_text(html_file)
        for target in attr_re.findall(content):
            if is_external_target(target) or target.startswith("data:") or target.startswith("javascript:"):
                continue
            base, _fragment = split_target(target)
            if not base:
                continue
            resolved = (html_file.parent / base).resolve()
            if not resolved.exists():
                problems.append(f"{html_file.relative_to(OUT_DIR)} -> {target}")
    return problems


def main() -> None:
    if not SOURCE_DIR.exists():
        raise SystemExit(f"Source directory not found: {SOURCE_DIR}")

    metadata = json.loads(read_text(SOURCE_DIR / "metadata_ja.json"))
    prepare_output_dir()

    write_text(OUT_DIR / "style.css", STYLE_CSS.strip() + "\n")
    write_text(OUT_DIR / "app.js", APP_JS.strip() + "\n")
    copy_tree_filtered(SOURCE_DIR / "assets", OUT_DIR / "assets")
    copy_tree_filtered(SOURCE_DIR / "raw_text", OUT_DIR / "raw_text")

    write_text(OUT_DIR / "index.html", build_index(metadata))
    build_markdown_page(metadata, "contents_ja.md", "contents.html", "章一覧と使い方", "contents")
    build_markdown_page(metadata, "README.md", "about.html", "README", "about")
    build_markdown_page(metadata, "embedded_images.md", "embedded_images.html", "埋め込み図版", "embedded_images")
    qa_source = "QA_REPORT_ja_checked.md" if (SOURCE_DIR / "QA_REPORT_ja_checked.md").exists() else "QA_REPORT_ja.md"
    build_markdown_page(metadata, qa_source, "qa.html", "QAレポート", "qa")
    search_entries = build_chapter_pages(metadata)
    write_text(OUT_DIR / "search_index.json", json.dumps(search_entries, ensure_ascii=False, indent=2) + "\n")

    problems = validate_links()
    if problems:
        for problem in problems:
            print(f"Broken link: {problem}")
        raise SystemExit(f"Generated HTML has {len(problems)} broken local links.")

    html_files = len(list(OUT_DIR.rglob("*.html")))
    image_files = len([p for p in (OUT_DIR / "assets").rglob("*") if p.is_file()])
    print(f"Wrote {html_files} HTML files to {OUT_DIR}")
    print(f"Copied {image_files} asset files and generated search_index.json")


if __name__ == "__main__":
    main()
