#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "source_en_pages"
JA_PAGE_DIR = ROOT / "pages_ja"
TRANSLATION_DIR = ROOT / "translations_full_ja"
REPORT_MD = ROOT / "full_translation_report_ja.md"
REPORT_HTML = ROOT / "html_textbook" / "full_translation_report_ja.html"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"


SYSTEM_PROMPT = """\
あなたは金融モデル文書のプロ向け英日翻訳者です。
入力はOCR由来の英文テキストなので、改行崩れ・表崩れ・誤認識が含まれます。
必ず次のルールに従ってください。

- 要約ではなく、読み取れる本文を文書順に日本語へ翻訳する。
- ページヘッダー、表題、箇条書き、表、数式、注記、脚注、変更履歴も翻訳対象にする。
- 人名、組織名、モデルID、バージョン、日付、変数名、コード名、URL、gitブランチ、数式記号は原則として保持する。
- OCRが明らかに壊れていて意味を確定できない箇所は、推測で補わず「[OCR不明瞭: 原文断片]」と書く。
- 表は可能ならMarkdown表に整形し、無理なら箇条書きで全項目を保持する。
- 数式はLaTeXまたは原文に近い形で保持し、必要に応じて直後に日本語で読み方を書く。
- “Confidential” は「機密」と訳す。
- “Winning-Probability Model” は「勝率モデル」、“hit-rate curve” は「ヒット率曲線」または「勝率曲線」、“market spread captured” は「市場スプレッド獲得率」と訳す。
- “RFQ”, “EUGV”, “UKGV”, “GLM”, “BMET”, “MCS” などの略語は保持し、初出説明があれば日本語化する。
- 翻訳本文だけを返す。前置き、謝辞、説明、免責文、翻訳完了メッセージは書かない。
"""


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_ocr(path: Path) -> str:
    markdown = read_text(path)
    match = re.search(r"```text\s*\n(.*?)\n```", markdown, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find OCR block in {path}")
    return match.group(1).strip()


def extract_page_memo(page_number: int) -> str:
    path = JA_PAGE_DIR / f"page_{page_number:03d}_ja.md"
    if not path.exists():
        return ""
    markdown = read_text(path)
    start = markdown.find("## 日本語メモ")
    end = markdown.find("## 原文OCR/Text Layer", start)
    if start == -1:
        return ""
    if end == -1:
        end = len(markdown)
    return markdown[start + len("## 日本語メモ") : end].strip()


def chunk_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    blocks = re.split(r"(\n\s*\n)", text)

    for block in blocks:
        if not block:
            continue
        if current_len + len(block) > max_chars and current:
            chunks.append("".join(current).strip())
            current = []
            current_len = 0
        if len(block) > max_chars:
            lines = block.splitlines(keepends=True)
            for line in lines:
                if current_len + len(line) > max_chars and current:
                    chunks.append("".join(current).strip())
                    current = []
                    current_len = 0
                current.append(line)
                current_len += len(line)
        else:
            current.append(block)
            current_len += len(block)

    if current:
        chunks.append("".join(current).strip())
    return [chunk for chunk in chunks if chunk]


def call_ollama(
    *,
    model: str,
    prompt: str,
    temperature: float,
    timeout: int,
    num_ctx: int,
    num_predict: int,
) -> str:
    payload = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "30m",
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    text = data.get("response", "").strip()
    if not text:
        raise RuntimeError(f"Ollama returned an empty response: {data}")
    if data.get("done_reason") == "length":
        text += "\n\n[翻訳メモ: このチャンクはモデルの出力上限に達した可能性があります。原文OCRを確認してください。]"
    return text


def translate_page(
    *,
    page_number: int,
    model: str,
    force: bool,
    max_chars: int,
    temperature: float,
    timeout: int,
    num_ctx: int,
    num_predict: int,
) -> Path:
    output_path = TRANSLATION_DIR / f"page_{page_number:03d}_full_ja.md"
    if output_path.exists() and not force:
        log(f"[skip] page {page_number:03d}: cached")
        return output_path

    source_path = SOURCE_DIR / f"page_{page_number:03d}.md"
    ocr_text = extract_ocr(source_path)
    memo = extract_page_memo(page_number)
    chunks = chunk_text(ocr_text, max_chars=max_chars)

    translated_chunks: list[str] = []
    for chunk_index, chunk in enumerate(chunks, start=1):
        log(f"[translate] page {page_number:03d} chunk {chunk_index}/{len(chunks)} ({len(chunk)} chars)")
        memo_context = f"\n参考の既存日本語メモ:\n{memo}\n" if memo else ""
        prompt = f"""\
Page {page_number:03d} のOCRテキストを日本語に全文翻訳してください。
このチャンクは {chunk_index}/{len(chunks)} です。前後のチャンクとつながる自然な文体にしてください。
{memo_context}
OCRテキスト:
```text
{chunk}
```
"""
        for attempt in range(1, 4):
            try:
                translated = call_ollama(
                    model=model,
                    prompt=prompt,
                    temperature=temperature,
                    timeout=timeout,
                    num_ctx=num_ctx,
                    num_predict=num_predict,
                )
                translated_chunks.append(translated)
                break
            except (urllib.error.URLError, TimeoutError, RuntimeError) as exc:
                if attempt == 3:
                    raise
                wait = 5 * attempt
                log(f"[retry] page {page_number:03d} chunk {chunk_index}: {exc}; wait {wait}s")
                time.sleep(wait)

    image_path = f"../assets/page_images/page_{page_number:03d}.png"
    output = [
        f"# Page {page_number:03d} - 全文日本語訳",
        "",
        f"![Page {page_number}]({image_path})",
        "",
        "## 日本語全文訳",
        "",
        "\n\n".join(translated_chunks).strip(),
        "",
        "## 翻訳ソース",
        "",
        f"- OCR: `source_en_pages/page_{page_number:03d}.md`",
        f"- ページ画像: `{image_path}`",
        "- 注意: OCR崩れがある箇所は、ページ画像を正として確認してください。",
        "",
    ]
    output_path.write_text("\n".join(output), encoding="utf-8")
    return output_path


def parse_pages(value: str | None) -> list[int]:
    if not value:
        return list(range(1, 74))
    pages: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start), int(end) + 1))
        else:
            pages.add(int(part))
    return sorted(page for page in pages if 1 <= page <= 73)


def strip_cached_translation(markdown: str) -> str:
    start = markdown.find("## 日本語全文訳")
    end = markdown.find("## 翻訳ソース")
    if start == -1:
        return balance_code_fences(markdown.strip())
    start += len("## 日本語全文訳")
    if end == -1:
        end = len(markdown)
    return balance_code_fences(markdown[start:end].strip())


def balance_code_fences(markdown: str) -> str:
    fence_count = 0
    for line in markdown.splitlines():
        if line.lstrip().startswith("```"):
            fence_count += 1
    if fence_count % 2 == 1:
        return markdown.rstrip() + "\n```"
    return markdown


def details_block(summary: str, body: str, language: str = "") -> str:
    class_attr = f' class="language-{escape(language)}"' if language else ""
    return f"""<details>
<summary>{summary}</summary>

<pre><code{class_attr}>{escape(body.rstrip())}</code></pre>

</details>
"""


def build_markdown_report(*, model: str, pages: list[int]) -> None:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    manifest = json.loads(read_text(ROOT / "manifest_ja.json"))

    parts: list[str] = [
        "# Winning-Probability Model for EUGV RFQ Pricing - 全文日本語訳フルレポート",
        "",
        f"> 生成日時: {generated_at}",
        f"> 翻訳モデル: ローカル Ollama `{model}`",
        "",
        "## 利用上の注意",
        "",
        "このレポートは、既存のページ画像とOCRテキストをもとにローカルLLMで日本語化した全文訳ドラフトです。原PDFはOCR由来のため、本文・表・数式には誤認識やレイアウト崩れが残ります。数式、表、図、ページレイアウトの最終確認はページ画像、`verified_equations_ja.md`、`tables/*_ja.md` を優先してください。",
        "",
        "## 収録状況",
        "",
        "| 項目 | 件数 |",
        "|---|---:|",
        f"| 元PDFページ | {manifest.get('pdf_pages', 73)} |",
        f"| ページ画像 | {manifest.get('page_images', 73)} |",
        f"| 全文訳ページ | {len(pages)} |",
        f"| 図インデックス | {len(manifest.get('figures_indexed', []))} |",
        f"| 表インデックス | {len(manifest.get('tables_indexed', []))} |",
        f"| 検証済み数式 | {len(manifest.get('equations_verified', []))} |",
        "",
        "## 既存メインノート",
        "",
        read_text(ROOT / "main_translation_ja.md").strip(),
        "",
        "# ページ別全文日本語訳",
        "",
    ]

    for page_number in pages:
        translation_path = TRANSLATION_DIR / f"page_{page_number:03d}_full_ja.md"
        if not translation_path.exists():
            raise FileNotFoundError(f"Missing translation cache: {translation_path}")
        translation = strip_cached_translation(read_text(translation_path))
        ocr = extract_ocr(SOURCE_DIR / f"page_{page_number:03d}.md")
        memo = extract_page_memo(page_number)
        image_path = f"assets/page_images/page_{page_number:03d}.png"

        parts.extend(
            [
                f"## Page {page_number:03d}",
                "",
                f"![Page {page_number}]({image_path})",
                "",
            ]
        )
        if memo:
            parts.extend(["### 既存日本語メモ", "", memo, ""])
        parts.extend(
            [
                "### 日本語全文訳",
                "",
                translation,
                "",
                details_block("原文OCR/Text Layerを表示", ocr, "text"),
                "",
            ]
        )

    appendices = [
        ("# 付録A: 検証済み数式", "verified_equations_ja.md"),
        ("# 付録B: 主要表", "tables/table_001_ja.md"),
        ("# 付録B: 主要表 2", "tables/table_002_ja.md"),
        ("# 付録C: 図表インデックス", "figure_table_index_ja.md"),
        ("# 付録D: 用語集", "glossary_ja.md"),
        ("# 付録E: Accuracy & Completeness Audit", "accuracy_completeness_audit_ja.md"),
    ]
    for heading, rel_path in appendices:
        appendix_md = read_text(ROOT / rel_path).strip()
        appendix_md = appendix_md.replace("](../assets/", "](assets/")
        parts.extend([heading, "", appendix_md, ""])

    REPORT_MD.write_text("\n".join(parts), encoding="utf-8")
    log(f"[write] {REPORT_MD}")


def make_markdown_renderer() -> MarkdownIt:
    md = MarkdownIt("gfm-like", {"html": True})
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


def build_html_report() -> None:
    md = make_markdown_renderer()
    markdown = read_text(REPORT_MD)
    body = md.render(markdown)
    body = body.replace("<table>", '<div class="table-wrap"><table>')
    body = body.replace("</table>", "</table></div>")
    body = re.sub(r"<img(?![^>]*\bloading=)", '<img loading="lazy" decoding="async"', body)
    body = body.replace('src="assets/', 'src="../assets/')
    html = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Winning-Probability Model 全文日本語訳フルレポート</title>
  <style>
    :root {{
      --bg: #f7f8f7;
      --surface: #ffffff;
      --ink: #202724;
      --muted: #61706a;
      --line: #dce3df;
      --accent: #0f766e;
      --accent-weak: #e0f2ef;
      --code: #f1f5f3;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Yu Gothic", "Noto Sans JP", "Segoe UI", sans-serif;
      line-height: 1.78;
      letter-spacing: 0;
    }}
    .shell {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 34px 0 72px;
    }}
    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 5;
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.94);
      padding: 12px 16px;
      backdrop-filter: blur(10px);
    }}
    .toolbar-inner {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      display: flex;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
    }}
    .toolbar a {{
      color: var(--accent);
      font-weight: 700;
      text-decoration: none;
    }}
    #search {{
      width: min(420px, 52vw);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 11px;
      font: inherit;
    }}
    article {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 28px;
      box-shadow: 0 10px 26px rgba(20, 38, 32, 0.08);
    }}
    a {{ color: var(--accent); }}
    h1, h2, h3 {{ line-height: 1.35; letter-spacing: 0; }}
    h1 {{ font-size: clamp(2rem, 4vw, 3rem); }}
    h2 {{
      margin-top: 2.4em;
      padding-top: 1em;
      border-top: 1px solid var(--line);
      font-size: 1.55rem;
    }}
    h3 {{ margin-top: 1.5em; font-size: 1.18rem; }}
    blockquote {{
      margin-left: 0;
      padding: 8px 16px;
      border-left: 4px solid var(--accent);
      background: var(--accent-weak);
      color: #163c37;
      border-radius: 0 8px 8px 0;
    }}
    img {{
      display: block;
      max-width: 100%;
      height: auto;
      margin: 14px 0;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: white;
    }}
    code {{
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.92em;
    }}
    p code, li code, td code {{
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
    }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      margin: 16px 0;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.93rem;
      line-height: 1.55;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 10px;
      vertical-align: top;
    }}
    th {{
      background: #f1f5f3;
      text-align: left;
    }}
    details {{
      margin: 16px 0;
      border-top: 1px solid var(--line);
      padding-top: 10px;
    }}
    summary {{
      cursor: pointer;
      color: var(--muted);
      font-weight: 700;
    }}
    details pre {{ max-height: 480px; font-size: 0.82rem; }}
    .is-hidden {{ display: none; }}
    @media (max-width: 760px) {{
      .toolbar-inner {{ display: block; }}
      #search {{ width: 100%; margin-top: 10px; }}
      article {{ padding: 18px; }}
    }}
    @media print {{
      .toolbar {{ display: none; }}
      .shell {{ width: 100%; padding: 0; }}
      article {{ box-shadow: none; border: 0; }}
      details pre {{ max-height: none; }}
    }}
  </style>
</head>
<body>
  <div class="toolbar">
    <div class="toolbar-inner">
      <a href="#winning-probability-model-for-eugv-rfq-pricing---全文日本語訳フルレポート">全文日本語訳フルレポート</a>
      <input id="search" type="search" placeholder="キーワード検索">
    </div>
  </div>
  <main class="shell">
    <article id="report">
      {body}
    </article>
  </main>
  <script>
    const input = document.getElementById('search');
    const sections = Array.from(document.querySelectorAll('h2')).map((heading) => {{
      const nodes = [];
      let node = heading;
      while (node && !(node !== heading && node.tagName === 'H2')) {{
        nodes.push(node);
        node = node.nextElementSibling;
      }}
      return {{ heading, nodes, text: nodes.map((n) => n.textContent).join(' ').toLowerCase() }};
    }});
    input.addEventListener('input', () => {{
      const q = input.value.trim().toLowerCase();
      sections.forEach((section) => {{
        const show = !q || section.text.includes(q);
        section.nodes.forEach((node) => node.classList.toggle('is-hidden', !show));
      }});
    }});
  </script>
</body>
</html>
"""
    REPORT_HTML.parent.mkdir(exist_ok=True)
    REPORT_HTML.write_text(html, encoding="utf-8")
    log(f"[write] {REPORT_HTML}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a full Japanese translation report.")
    parser.add_argument("--model", default="qwen2.5:7b", help="Ollama model name")
    parser.add_argument("--pages", help="Page list, e.g. 1-3,8,10")
    parser.add_argument("--force", action="store_true", help="Retranslate cached pages")
    parser.add_argument("--skip-translation", action="store_true", help="Only rebuild reports from cache")
    parser.add_argument("--max-chars", type=int, default=4200, help="Max OCR chars per translation chunk")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--num-ctx", type=int, default=12288)
    parser.add_argument("--num-predict", type=int, default=4096)
    args = parser.parse_args()

    pages = parse_pages(args.pages)
    TRANSLATION_DIR.mkdir(exist_ok=True)

    if not args.skip_translation:
        started = time.time()
        for page_number in pages:
            translate_page(
                page_number=page_number,
                model=args.model,
                force=args.force,
                max_chars=args.max_chars,
                temperature=args.temperature,
                timeout=args.timeout,
                num_ctx=args.num_ctx,
                num_predict=args.num_predict,
            )
        elapsed = time.time() - started
        log(f"[done] translated/reused {len(pages)} pages in {elapsed:.1f}s")

    build_markdown_report(model=args.model, pages=pages)
    build_html_report()


if __name__ == "__main__":
    main()
