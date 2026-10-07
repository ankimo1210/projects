"""Build the Ch1 companion portal with the same explanations and shared plots."""

from pathlib import Path

from hullkit._chapter01_lesson import SECTIONS, _cells, _figures, _html
from markdown_it import MarkdownIt
from plotly.offline import get_plotlyjs

PROJECT = Path(__file__).resolve().parents[1]


def build(output_dir=None):
    """Write the offline chapter page; the nested path survives portal cleanup."""
    tokens = (PROJECT.parent / "docs/templates/claude-report/tokens.css").read_text()
    css = """
.lesson {margin:2rem 0;padding:1.5rem;background:var(--surface);border-radius:12px}
.lesson table {width:100%;border-collapse:collapse}
.lesson th,.lesson td {padding:.45rem;text-align:left;border-bottom:1px solid var(--rule)}
.lesson th {color:var(--ink-2)}
.lesson p {line-height:1.9}.lesson h3 {line-height:1.5}
.plotly-graph-div {width:100%;min-width:0}
"""
    html = [
        '<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ch1 デリバティブ入門</title><style>'
        + tokens
        + css
        + "</style><script>"
        + get_plotlyjs()
        + '</script></head><body><div class="wrap"><header class="mast"><div class="eyebrow">Hull 11e Global Edition · Ch1 · 原典時点の教材</div><h1>デリバティブの全体像</h1><p class="lede">契約の権利・義務、数量、通貨、担保と費用を区別する。</p><p><a href="../index.html">ポータルのホーム</a> · <a href="../../../book/_build/html/notebooks/12_qualitative_summary.html">Jupyter Book</a></p></header><nav>'
    ]
    for sid, title, _, _ in SECTIONS:
        html.append(f'<a href="#section-{sid.replace(".", "-")}">§{sid} {title}</a>　')
    html.append("</nav>")
    figures = _figures()
    markdowns = [cell for cell in _cells() if cell["cell_type"] == "markdown"]
    for (sid, _, _, _), cell in zip(SECTIONS, markdowns, strict=True):
        html.append(f'<section class="lesson" id="section-{sid.replace(".", "-")}">')
        html.append(MarkdownIt().enable("table").render("".join(cell["source"])))
        for key, fig in figures.items():
            if fig.layout.meta["section"] == sid:
                html.append(_html(key))
        html.append("</section>")
    html.append("""<footer>出典: Hull 11e Global Edition pp.24–40。quoteは2020-05-21、市場規模は2019年末。<br>option・現物/先物の比較は手数料・資金利息を省略。§1.3 carry例は年5%を含みます。将来予測や現行法令の判定ではありません。</footer></div>
<script>
const theme=getComputedStyle(document.documentElement);
for (const el of document.querySelectorAll('.plotly-graph-div')) {
 const colors=['--series-1','--series-2'].map(k=>theme.getPropertyValue(k).trim());
 Plotly.restyle(el, {'line.color':colors,'marker.color':colors});
 Plotly.relayout(el, {'paper_bgcolor':theme.getPropertyValue('--surface').trim(),'plot_bgcolor':theme.getPropertyValue('--surface').trim(),'font.color':theme.getPropertyValue('--ink').trim()});
}
</script></body></html>""")
    site = Path(output_dir) if output_dir is not None else PROJECT / "report/site"
    out = site / "chapters/ch01.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(html))
    return out


if __name__ == "__main__":
    print(build())
