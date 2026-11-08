"""Build the catalogued mathematics reader using only the standard library."""

import html
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
CATALOG = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
CHAPTERS = CATALOG["chapters"]
BOOKS = CATALOG["books"]


def escape(value: str) -> str:
    return html.escape(value, quote=True)


def chapter_nav(current: str) -> str:
    chapter = next(c for c in CHAPTERS if c["slug"] == current)
    links = []
    for item in CHAPTERS:
        if item["book"] != chapter["book"]:
            continue
        active = ' aria-current="page"' if current == item["slug"] else ""
        links.append(
            f'<a href="{item["slug"]}.html"{active}><span>{item["number"]}</span>{escape(item["title"])}</a>'
        )
    return "\n".join(links)


def local_book(output: Path, relative: str) -> str:
    return escape(Path(os.path.relpath(WORKSPACE / "analytics" / relative, output)).as_posix())


def book_link(output: Path, relative: str, label: str) -> str:
    if (WORKSPACE / "analytics" / relative).is_file():
        return f'<a href="{local_book(output, relative)}">{escape(label)} →</a>'
    return f"<span>{escape(label)}（準備中）</span>"


def landing(output: Path) -> str:
    cards, outlines = [], []
    for index, book in enumerate(BOOKS, 1):
        chapters = [c for c in CHAPTERS if c["book"] == book["id"]]
        cards.append(
            f"""<a class="chapter-card" href="#book-{book["id"]}"><span class="card-top"><span class="chapter-number">{index:02}</span><span>{len(chapters)}章</span></span><h2>{book["title"]}</h2><p>{book["description"]}</p><span class="card-go">目次へ <span aria-hidden="true">↓</span></span></a>"""
        )
        rows = "".join(
            f'<li><a class="chapter-row" href="{c["slug"]}.html"><span>{c["number"]}</span><div><strong>{escape(c["title"])}</strong><small>{escape(c["question"])}</small></div><span aria-hidden="true">→</span></a></li>'
            for c in chapters
        )
        outlines.append(
            f'<section class="home-section" id="book-{book["id"]}"><p class="edition">{len(chapters)} CHAPTERS</p><h2>{book["title"]}</h2><p>{book["description"]}</p><ol class="course-index">{rows}</ol></section>'
        )
    return f"""<div class="home-intro"><p class="edition">入門から、微積分・線形代数・確率・離散数学・複素解析・ベクトル解析・数値解析・最適化へ / 全{len(CHAPTERS)}章</p>
<h1>数学を、もう一度。</h1><p class="hero-sub">公式の向こうにある「なぜ」から。</p>
<p class="lede">なぜそんな定義をするのか。どうしてその定理が成り立つのか。<br class="desktop-break">図を動かし、少し考え、数学の見方を一緒につくっていく教科書です。</p>
<a class="primary-link" href="observation.html">はじめの章へ <span aria-hidden="true">→</span></a>
<p class="trial-note">高校数学を一度学んだ方へ。分かる章は飛ばし、必要な前提にはリンクから戻れます。</p></div>
<section id="chapters" class="home-section"><p class="edition">LEARNING PATH</p><h2>数学の言葉から、変化・偶然・つながりまで。</h2><div class="chapter-grid">{"".join(cards)}</div></section>
<section id="how-to-read" class="home-section"><p class="edition">この教科書の歩き方</p><h2>眺める。予想する。理由をたどる。</h2><div class="reading-steps"><div><span>01</span><h3>問いを持つ</h3><p>必要な前提を確認し、どんな問題を解きたいかから始めます。</p></div><div><span>02</span><h3>理由を確かめる</h3><p>観察と証明を区別し、定義と定理の条件をたどります。</p></div><div><span>03</span><h3>自分の言葉にする</h3><p>コラムで寄り道し、段階ヒントと解答のある演習で確かめます。</p></div></div></section>
{"".join(outlines)}
<section id="learning-map" class="home-section"><p class="edition">その先の数学</p><h2>学んだ道具を、組み合わせる。</h2><p>これまでの教材へ進む入口です。各教材の前提・読み方も確認してください。</p><div class="path-grid"><div><h3>空間と変換</h3><p>写像・回転から、行列や基底へ。</p>{book_link(output, "linear_algebra/book/_build/html/index.html", "線形代数の発展（既存教材）へ")}</div><div><h3>変化と振動</h3><p>微分積分から、現象を表す方程式へ。</p>{book_link(output, "differential_equation/ode-book/book/_build/html/index.html", "常微分方程式へ")}<br>{book_link(output, "fourier/book/_build/html/index.html", "フーリエ解析へ")}</div><div><h3>不確実性</h3><p>確率の基礎から、推測と判断へ。</p>{book_link(output, "statistics/book/_build/html/index.html", "確率・統計へ")}</div></div><p class="note">この先へ：既存の線形代数本編・常微分方程式との接続を深める。</p></section>"""


def build(output: Path | None = None) -> list[Path]:
    output = (output or ROOT / "site").resolve()
    template = (ROOT / "template.html").read_text(encoding="utf-8")
    css = (
        (WORKSPACE / "docs/templates/claude-report/tokens.css").read_text(encoding="utf-8")
        + "\n"
        + (ROOT / "assets/style.css").read_text(encoding="utf-8")
    )
    scripts = "\n".join(
        (ROOT / "assets" / name).read_text(encoding="utf-8")
        for name in (
            "math.js",
            "experiments.js",
            "calculus.js",
            "calculus-experiments.js",
            "linear.js",
            "linear-experiments.js",
            "multivariable.js",
            "multivariable-experiments.js",
            "multivariable-middle.js",
            "multivariable-middle-experiments.js",
            "multivariable-integration.js",
            "multivariable-integration-experiments.js",
            "probability.js",
            "probability-experiments.js",
            "discrete.js",
            "discrete-experiments.js",
            "complex.js",
            "complex-experiments.js",
            "vector.js",
            "vector-experiments.js",
            "numerical.js",
            "numerical-experiments.js",
            "optimization.js",
            "optimization-experiments.js",
            "linear-core.js",
            "linear-core-experiments.js",
            "reader.js",
        )
    )
    pages = [("index", "数学を、もう一度。", landing(output), "", "", "", "", "")]
    for chapter in CHAPTERS:
        slug = chapter["slug"]
        book = next(b for b in BOOKS if b["id"] == chapter["book"])
        peers = [c for c in CHAPTERS if c["book"] == chapter["book"]]
        index = peers.index(chapter)
        body = (ROOT / "chapters" / f"{slug}.html").read_text(encoding="utf-8")
        sections = re.findall(r'<section\s+id="([^"]+)"[^>]*>\s*<h2>(.*?)</h2>', body, flags=re.S)
        toc = "".join(
            f'<a href="#{escape(anchor)}">{re.sub("<[^>]+>", "", label)}</a>'
            for anchor, label in sections
        )
        previous = (
            f'<a href="{peers[index - 1]["slug"]}.html">← {peers[index - 1]["title"]}</a>'
            if index
            else f'<a href="index.html#book-{book["id"]}">← {book["title"]}の目次</a>'
        )
        following = (
            f'<a href="{peers[index + 1]["slug"]}.html">{peers[index + 1]["title"]} →</a>'
            if index + 1 < len(peers)
            else '<a href="index.html#learning-map">その先の数学へ →</a>'
        )
        book_index = BOOKS.index(book)
        if index + 1 == len(peers) and book_index + 1 < len(BOOKS):
            next_book = BOOKS[book_index + 1]
            next_chapter = next(c for c in CHAPTERS if c["book"] == next_book["id"])
            following = (
                f'<a href="{next_chapter["slug"]}.html">{escape(next_book["title"])}へ →</a>'
            )
        math_hint = (
            '<p class="math-scroll-hint">長い数式は、式の枠内を左右にスクロールして読めます。</p>'
            if "<math" in body
            else ""
        )
        table_hint = (
            '<p class="table-scroll-hint">横に長い表は、表の枠内を左右にスクロールして読めます。</p>'
            if 'class="concept-table"' in body
            else ""
        )
        subtitle = (
            f'<p class="chapter-subtitle hero-sub">{escape(chapter["subtitle"])}</p>'
            if chapter.get("subtitle")
            else ""
        )
        header = f'<header class="chapter-header"><p class="edition">{book["title"]} / CHAPTER {chapter["number"]}</p><h1>{escape(chapter["title"])}</h1>{subtitle}<p class="chapter-question">{escape(chapter["question"])}</p><p class="chapter-meta">{escape(chapter["duration"])} · 読む時間の目安</p>{math_hint}{table_hint}</header>'
        pages.append(
            (
                slug,
                chapter["title"],
                header + body,
                toc,
                previous,
                following,
                book["title"],
                chapter_nav(slug),
            )
        )
    rendered = []
    for slug, title, body, toc, previous, following, book_title, nav in pages:
        page = template
        values = {
            "TITLE": escape(title),
            "CSS": css,
            "JS": scripts,
            "BODY": body,
            "TOC": toc,
            "NAV": nav,
            "PREVIOUS": previous,
            "NEXT": following,
            "BOOK_TITLE": escape(book_title),
            "PAGE_CLASS": "home-page" if slug == "index" else "chapter-page",
            "TOTAL_CHAPTERS": str(len(CHAPTERS)),
        }
        for key, value in values.items():
            page = page.replace("{{" + key + "}}", value)
        rendered.append((output / f"{slug}.html", page))
    output.mkdir(parents=True, exist_ok=True)
    for path, content in rendered:
        path.write_text(content, encoding="utf-8")
    return [path for path, _ in rendered]


if __name__ == "__main__":
    print(f"Built {len(build())} pages in analytics/math_foundations/site/")
