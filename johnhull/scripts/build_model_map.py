"""Build the offline reader map and cards from their reviewed definition.

Run from the workspace root with ``uv run --no-sync --package hullkit python
johnhull/scripts/build_model_map.py --write`` (or ``--check`` for freshness).
Only guide-local outputs are written; no shared Book asset is changed.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import html
import json
import re
from functools import lru_cache
from pathlib import Path

from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

PROJECT = Path(__file__).resolve().parents[1]
GUIDE = Path("book/notebooks/guide")
KINDS = {"special": "特殊な場合", "limit": "極限・近似", "input": "入力・較正"}
COLORS = {"special": "#23734d", "limit": "#8d5a10", "input": "#3659a6"}


def slug(text: str) -> str:
    """GitHub heading fragment for the agent catalogue's Markdown headings."""
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


def catalogue(project: Path) -> dict[str, str]:
    """Return the selected catalogue rows and their containing headings."""
    result = {}
    section = ""
    for line in (project / "MODEL_INDEX.md").read_text().splitlines():
        if line.startswith("## "):
            section = line[3:]
        prefix = section.split()[0].rstrip(".") if section else ""
        if prefix not in {*(str(i) for i in range(1, 15)), "P3", "P4"}:
            continue
        if line.startswith("| ") and not line.startswith(("| Model |", "| Module |")):
            result[prefix + "/" + line.split("|")[1].strip()] = section
    return result


def _headings(path: Path) -> set[str]:
    if path.suffix == ".ipynb":
        notebook = json.loads(path.read_text())
        text = "\n".join(
            "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "markdown"
        )
    else:
        text = path.read_text()
    soup = BeautifulSoup(MarkdownIt().render(text), "html.parser")
    return {_heading_text(h.get_text().strip()) for h in soup.select("h1,h2,h3,h4,h5,h6")}


def _heading_text(text: str) -> str:
    # Sphinx smartquotes turns the source's double/triple hyphen into dashes.
    return re.sub(r"[-–—]+", "-", text)


def validate(data: dict, project: Path = PROJECT) -> None:
    """Reject missing models, invalid relations, or unresolved local links."""
    ids = [card["id"] for card in data["cards"]]
    if len(set(ids)) != len(ids) or not all(re.fullmatch(r"[a-z0-9-]+", i) for i in ids):
        raise ValueError("duplicate or invalid card id")
    expected = catalogue(project)
    covered = {r for card in data["cards"] for r in card["catalogue_rows"]}
    if expected.keys() != covered:
        raise ValueError(
            f"catalogue coverage: missing={expected.keys() - covered}, extra={covered - expected.keys()}"
        )
    groups = {group["id"] for group in data["groups"]}
    headings = {}
    html_ids = {}
    ledger = {
        s["id"] for s in json.loads((project / "docs/section_ledger.json").read_text())["sections"]
    }
    for card in data["cards"]:
        for field in ("name", "english", "state", "assumptions", "method", "uses", "scope"):
            if not card.get(field, "").strip():
                raise ValueError(f"{card['id']}: empty {field}")
        if card["group"] not in groups or len(card["position"]) != 2:
            raise ValueError(f"{card['id']}: group or position")
        for section in card["sections"]:
            if section not in ledger:
                raise ValueError(f"{card['id']}: source section {section}")
        for link in card["links"]:
            path = project / link["path"]
            if link["kind"] == "catalogue":
                if link["heading"] not in expected.values() or link["anchor"] != slug(
                    link["heading"]
                ):
                    raise ValueError(f"link: invalid catalogue heading {link}")
            elif link["kind"] == "book":
                if not path.is_file():
                    raise ValueError(f"link: missing Book {path}")
                if path not in headings:
                    headings[path] = _headings(path)
                if _heading_text(link["heading"]) not in headings[path]:
                    raise ValueError(f"link: missing Book source heading {link}")
                built = project / "book/_build/html/notebooks" / (path.stem + ".html")
                if built.is_file():
                    if built not in html_ids:
                        html_ids[built] = {
                            e["id"]
                            for e in BeautifulSoup(built.read_text(), "html.parser").find_all(
                                id=True
                            )
                        }
                    if link["anchor"] not in html_ids[built]:
                        raise ValueError(f"link: missing Book HTML anchor {link}")
            elif link["kind"] == "portal":
                section = link["section"]
                chapter = int(section.split(".")[0])
                if section not in ledger or link["anchor"] != "section-" + section.replace(
                    ".", "-"
                ):
                    raise ValueError(f"link: invalid portal section {link}")
                if link["path"] != f"report/site/chapters/ch{chapter:02d}.html":
                    raise ValueError(f"link: invalid portal page {link}")
                if path.is_file():
                    if path not in html_ids:
                        html_ids[path] = {
                            e["id"]
                            for e in BeautifulSoup(path.read_text(), "html.parser").find_all(
                                id=True
                            )
                        }
                    if link["anchor"] not in html_ids[path]:
                        raise ValueError(f"link: missing portal HTML anchor {link}")
            else:
                raise ValueError(f"link: unknown type {link}")
    for edge in data["edges"]:
        if edge["from"] not in ids or edge["to"] not in ids:
            raise ValueError(f"relation endpoint: {edge}")
        if edge["kind"] not in KINDS or not edge["condition"].strip() or not edge["sources"]:
            raise ValueError(f"relation kind/condition/sources: {edge}")
        for source in edge["sources"]:
            if source not in data["sources"]:
                raise ValueError(f"relation source: {source}")
    for row in data["questions"]:
        if not set(row["models"]) <= set(ids):
            raise ValueError(f"question target: {row}")


def figure(data: dict) -> dict:
    """Make a deterministic Plotly definition using the authored coordinates."""
    cards = {c["id"]: c for c in data["cards"]}
    traces, annotations = [], []
    for edge in data["edges"]:
        a, b = cards[edge["from"]], cards[edge["to"]]
        x0, y0 = a["position"]
        x1, y1 = b["position"]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "x": [x0, x1],
                "y": [y0, y1],
                "line": {
                    "color": COLORS[edge["kind"]],
                    "width": 1.5,
                    "dash": {"special": "solid", "limit": "dash", "input": "dot"}[edge["kind"]],
                },
                "name": KINDS[edge["kind"]],
                "text": KINDS[edge["kind"]]
                + "："
                + a["name"]
                + " → "
                + b["name"]
                + "。条件と出典は下の関係表を参照してください。",
                "hoverinfo": "skip",
                "showlegend": False,
                "meta": {"groups": [a["group"], b["group"]]},
            }
        )
        annotations.append(
            {
                "x": x1,
                "y": y1,
                "ax": x0,
                "ay": y0,
                "xref": "x",
                "yref": "y",
                "axref": "x",
                "ayref": "y",
                "text": "",
                "showarrow": True,
                "arrowhead": 3,
                "arrowsize": 1.3,
                "arrowwidth": 1.3,
                "arrowcolor": COLORS[edge["kind"]],
                "standoff": 12,
                "startstandoff": 12,
                "visible": a["group"] == b["group"] == data["groups"][0]["id"],
            }
        )
    for group in data["groups"]:
        nodes = [c for c in data["cards"] if c["group"] == group["id"]]
        traces.append(
            {
                "type": "scatter",
                "mode": "markers+text",
                "name": group["name"],
                "x": [c["position"][0] for c in nodes],
                "y": [c["position"][1] for c in nodes],
                "customdata": [c["id"] for c in nodes],
                "text": [c.get("short", c["name"]) for c in nodes],
                "textposition": "bottom center",
                "textfont": {"size": 12},
                "marker": {
                    "size": 17,
                    "color": group["color"],
                    "line": {"color": "white", "width": 1},
                },
                "hovertext": [c["name"] + "：" + c["uses"] for c in nodes],
                "hoverinfo": "text",
                "showlegend": False,
                "meta": {"group": group["id"]},
            }
        )
    initial = data["groups"][0]["id"]
    for trace in traces:
        meta = trace["meta"]
        trace["visible"] = meta.get("group") == initial or meta.get("groups") == [initial, initial]
    return {
        "data": traces,
        "layout": {
            "autosize": True,
            "height": 600,
            "margin": {"l": 25, "r": 25, "t": 20, "b": 35},
            "paper_bgcolor": "white",
            "plot_bgcolor": "white",
            "font": {"family": "sans-serif", "color": "#222222"},
            "dragmode": "pan",
            "xaxis": {"visible": False},
            "yaxis": {"visible": False},
            "annotations": annotations,
            "hovermode": "closest",
        },
    }


@lru_cache(maxsize=1)
def _runtime() -> bytes:
    from plotly.offline import get_plotlyjs

    # gzip's timestamp is fixed; the full MIT-licensed library remains embedded.
    encoded = base64.b64encode(gzip.compress(get_plotlyjs().encode(), mtime=0)).decode()
    return (
        '''<!-- Plotly.js, MIT license; see model_map/LICENSE.plotly. No CDN. -->
<script>
// The installed theme names a missing ScrollSpy target. Scope this page's
// ScrollSpy to its real TOC so external numeric catalogue fragments are not
// interpreted as CSS selectors. Other Book pages are untouched.
document.body.setAttribute('data-bs-target','#pst-page-toc-nav');
window.readingGuidePlotlyReady = (async () => {
  if (!window.DecompressionStream) throw new Error('このブラウザでは図を開けません。下のカードと早見表を使ってください。');
  const bytes = Uint8Array.from(atob("'''
        + encoded
        + """"), c => c.charCodeAt(0));
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  const library = await new Response(stream).text();
  // Keep RequireJS's AMD hook outside this isolated UMD-library scope.
  const url = URL.createObjectURL(new Blob(['(function(){var define;\\n', library, '\\n}).call(window);'], {type:'text/javascript'}));
  try { await new Promise((resolve,reject) => { const s=document.createElement('script'); s.src=url; s.onload=resolve; s.onerror=reject; document.head.appendChild(s); }); }
  finally { URL.revokeObjectURL(url); }
  return window.Plotly;
})();
</script>
"""
    ).encode()


def _figure_html(data: dict, graph: dict) -> bytes:
    options = '<option value="all">全系統</option>' + "".join(
        f'<option value="{g["id"]}"'
        + (" selected" if i == 0 else "")
        + f">{html.escape(g['name'])}</option>"
        for i, g in enumerate(data["groups"])
    )
    targets = "".join(
        f'<option value="{c["id"]}">{html.escape(c["name"])}</option>' for c in data["cards"]
    )
    payload = json.dumps(graph, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return (
        """<style>
#reading-model-map-controls label {max-width:100%;min-width:0;display:grid;gap:.25rem}
#reading-model-map-controls select {max-width:100%;min-width:0;width:100%;font-size:1rem;min-height:44px}
#reading-model-map-controls button {min-height:44px;padding:.25rem .5rem}
</style>
<div id="reading-model-map-controls" style="display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin:1rem 0">
<label>系統 <select id="model-map-family">"""
        + options
        + """</select></label>
<button type="button" id="model-map-zoom-in">拡大 ＋</button>
<button type="button" id="model-map-zoom-out">縮小 −</button>
<button type="button" id="model-map-reset">全体に戻す</button>
<label>カードへ <select id="model-map-card"><option value="">名前で選ぶ</option>"""
        + targets
        + """</select></label>
</div>
<p>線の種類：実線＝特殊な場合、破線＝極限・近似、点線＝入力・較正。式の記号は各関係の説明で定めます。</p>
<p id="model-map-state" role="status">図を準備しています。本文のカードは先に読めます。</p>
<div id="reading-model-map" role="img" aria-label="系統を選び、モデルをタップすると説明カードへ進むモデル地図" style="width:100%;min-height:600px;touch-action:none"></div>
<script type="application/json" id="reading-model-map-definition">"""
        + payload
        + """</script>
<script>
(async () => {
 const status=document.getElementById('model-map-state');
 const jump=id=>{if(!id)return;const target=document.getElementById('model-'+id);if(target){location.hash='model-'+id;target.scrollIntoView({behavior:'instant',block:'start'});}};
 document.getElementById('model-map-card').addEventListener('change',e=>jump(e.target.value));
 try {
  const Plotly=await window.readingGuidePlotlyReady;
  const graph=JSON.parse(document.getElementById('reading-model-map-definition').textContent);
  const gd=document.getElementById('reading-model-map');
  const family=document.getElementById('model-map-family');
  const edges=graph.data.filter(t=>t.meta.groups);
 const visible=g=>graph.data.map(t=>Boolean(g==='all'||t.meta.group===g||(t.meta.groups&&t.meta.groups.every(x=>x===g))));
  const fit=()=>{const nodes=graph.data.filter(t=>t.meta.group&&(family.value==='all'||t.meta.group===family.value));
   const xs=nodes.flatMap(t=>t.x),ys=nodes.flatMap(t=>t.y);
   let xr=[Math.min(...xs)-1.8,Math.max(...xs)+1.8],yr=[Math.min(...ys)-1.4,Math.max(...ys)+1.4];
   if(innerWidth<600&&xr[1]-xr[0]>8){xr=[xr[0],xr[0]+8];}
   return {'xaxis.range':xr,'yaxis.range':yr};};
  await Plotly.newPlot(gd,graph.data,graph.layout,{responsive:true,scrollZoom:true,displaylogo:false,modeBarButtonsToRemove:['toImage','lasso2d','select2d']});
  async function select(){const group=family.value;await Plotly.restyle(gd,{visible:visible(group)});
   const annotations=graph.layout.annotations.map((a,i)=>({...a,visible:group==='all'||edges[i].meta.groups.every(x=>x===group)}));
   await Plotly.relayout(gd,{...fit(),annotations});status.textContent='モデルをタップすると本文へ移ります。線の条件は下の関係表にあります。狭い画面ではドラッグして続きへ進めます。';}
  family.addEventListener('change',select);
  document.getElementById('model-map-reset').addEventListener('click',()=>Plotly.relayout(gd,fit()));
  const zoom=factor=>{const range=axis=>{const [a,b]=gd.layout[axis].range,m=(a+b)/2,h=(b-a)*factor/2;return[m-h,m+h];};Plotly.relayout(gd,{'xaxis.range':range('xaxis'),'yaxis.range':range('yaxis')});};
  document.getElementById('model-map-zoom-in').addEventListener('click',()=>zoom(.65));
  document.getElementById('model-map-zoom-out').addEventListener('click',()=>zoom(1/.65));
  gd.on('plotly_click',e=>jump(e.points[0].customdata));
  await select(); window.readingModelMapReady=true;
 } catch(error){status.textContent=String(error);window.readingModelMapError=String(error);}
})();
</script>
"""
    ).encode()


def _href(link: dict) -> str:
    path = link["path"]
    if link["kind"] == "book":
        return "../" + Path(path).stem + ".html#" + link["anchor"]
    return "../../../../../" + path + "#" + link["anchor"]


def _markdown(data: dict) -> bytes:
    cards = {c["id"]: c for c in data["cards"]}
    lines = [
        "(guide-models)=",
        "# モデル地図：問いから道具へ進む",
        "",
        "モデルの名前を覚える前に、何を動かし、何の支払いを求めたいかを決めます。株価を動かす BSM と、計算を近似する有限差分法は役割が違います。この地図は商品・確率モデル・数値手法・検証手順を区別して読み、同じ問いに使う道具を見渡すためのページです。",
        "",
        "[用語と記号](glossary.md) ／ {ref}`章どうしのつながり <chapter-connections>`",
        "",
        "## 地図の読み方",
        "",
        "まず系統を選び、拡大・縮小やドラッグで位置を動かします。点をクリック・タップするとモデルカードへ進みます。名前の選択欄でも移動できます。JS が使えない場合も、下の早見表・関係表・すべてのカードを読めます。",
        "",
        "矢印は、矢印の元から先へ次の関係を読みます。特殊な場合はパラメーター等を制限する向き、極限・近似は条件を満たして近づける向き、入力・較正は推定・評価に入力を渡す向きです。優劣や学習の前後を示す線ではありません。線のないカードにも独立した役割があり、数学的な関係を確認できたものだけを結んでいます。",
        "",
        "```{raw} html",
        ":file: model_map/runtime.html",
        "```",
        "",
        "```{raw} html",
        ":file: model_map/figure.html",
        "```",
        "",
        "## 問いから選ぶ早見表",
        "",
        "| 知りたいこと | 最初に開くカード | 選ぶときの分かれ目 |",
        "|---|---|---|",
    ]
    for q in data["questions"]:
        links = "・".join(f"[{cards[i]['name']}](#model-{i})" for i in q["models"])
        lines.append(f"| {q['question']} | {links} | {q['boundary']} |")
    lines += [
        "",
        "## 関係を、条件と一緒に読む",
        "",
        "各関係はここで条件を確認できます。カード側にも行き先・戻り先を表示します。",
        "",
    ]
    for i, edge in enumerate(data["edges"], 1):
        sources = "、".join(data["sources"][s]["citation"] for s in edge["sources"])
        lines += [
            f"(map-relation-{i})=",
            f"### {cards[edge['from']]['name']} → {cards[edge['to']]['name']}",
            "",
            f"**{KINDS[edge['kind']]}。** {edge['condition']} 出典：{sources}。",
            "",
        ]
        if edge.get("equation"):
            lines += ["$$", edge["equation"], "$$", ""]
    lines += [
        "(model-cards)=",
        "## モデルカード",
        "",
        f"索引の対象 {data['catalogue_row_count']} 行を {len(cards)} 枚へ対応づけています。同じモデルの公開実装・非公開教材・図の生成部品は同じカードにまとめ、異なる状態や契約は区別しました。実装名・テストの範囲は各カードから MODEL_INDEX の該当節へ進めます。§15 の基盤と RB-F* の研究行は対象に含めていません。",
        "",
        "合成データでの恒等式・独立比較・再現性の確認と、市場での性能は別です。各章のガイドは現在 Ch8・Ch13 があり、残りは追加後にリンクします。",
        "",
    ]
    for group in data["groups"]:
        lines += [f"## {group['name']}", "", group["intro"], ""]
        for card in data["cards"]:
            if card["group"] != group["id"]:
                continue
            lines += [
                f"(model-{card['id']})=",
                f"### {card['name']}",
                "",
                f"{card['english']}"
                + (f"（{card['abbreviation']}）" if card.get("abbreviation") else "")
                + "。",
                "",
                f"**何を表すか：** {card['state']}",
                "",
                f"**仮定と限界：** {card['assumptions']}",
                "",
                f"**解き方・手順：** {card['method']}",
                "",
                f"**使う場面：** {card['uses']}",
                "",
                f"**実装と検証の範囲：** {card['scope']}",
                "",
            ]
            refs = [html.escape(link.get("label", link["heading"])) for link in card["links"]]
            links = [
                f'<a href="{_href(link)}">{label}</a>'
                for link, label in zip(card["links"], refs, strict=True)
            ]
            source = "、".join(card["source_pages"])
            lines += [
                f"**読む場所：** {card['hull_role']} {source}。" + " ／ ".join(links) + "。",
                "",
            ]
            chapter_numbers = {s.split(".")[0] for s in card["sections"]}
            guide_links = [
                f"[Ch{ch}のガイド](ch{int(ch):02d}.md)"
                for ch in sorted(chapter_numbers)
                if (PROJECT / GUIDE / f"ch{int(ch):02d}.md").is_file()
            ]
            if guide_links:
                lines += ["・".join(guide_links) + "から説明を読み直せます。", ""]
            relations = []
            for i, edge in enumerate(data["edges"], 1):
                if card["id"] == edge["from"]:
                    other = edge["to"]
                    relations.append(
                        f"[{cards[other]['name']}](#model-{other}) へ（[条件・出典](#map-relation-{i})：{KINDS[edge['kind']]}）"
                    )
                elif card["id"] == edge["to"]:
                    other = edge["from"]
                    relations.append(
                        f"[{cards[other]['name']}](#model-{other}) から（[条件・出典](#map-relation-{i})：{KINDS[edge['kind']]}）"
                    )
            if relations:
                lines += ["**関係：** " + "。".join(relations) + "。", ""]
    lines += [
        "## 出典と更新",
        "",
        "Hull の章節・頁は Global Edition の本文と照合しています。モデルカードの記述は本書の案内と、この repo の実装・検証範囲を独自にまとめたものです。Beyond Hull の理論文献は MODEL_INDEX 各行の Theory 欄、制限は各巻の VALIDATION と CONTENTS_INDEX §7 に戻って確認できます。新しい数値例はこの地図には置いていません。図の条件・カード・索引行の対応の正本は `model_map.json` です。",
        "",
    ]
    return ("\n".join(lines).rstrip() + "\n").encode()


def render(data: dict, project: Path = PROJECT) -> dict[str, bytes]:
    """Return the generated Markdown, figure definition and offline fragments."""
    validate(data, project)
    graph = figure(data)
    return {
        "models.md": _markdown(data),
        "model_map/figure.json": (
            json.dumps(graph, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode(),
        "model_map/figure.html": _figure_html(data, graph),
        "model_map/runtime.html": _runtime(),
    }


def check_outputs(directory: Path, outputs: dict[str, bytes]) -> list[str]:
    """List missing or stale outputs without modifying any of them."""
    return [
        name
        for name, content in outputs.items()
        if not (directory / name).is_file() or (directory / name).read_bytes() != content
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    directory = PROJECT / GUIDE
    data = json.loads((directory / "model_map.json").read_text())
    outputs = render(data)
    if args.write:
        for name, content in outputs.items():
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    stale = check_outputs(directory, outputs)
    if stale:
        print("[FAIL] stale model-map output: " + ", ".join(stale))
        return 1
    print(
        f"[PASS] model map: {len(data['cards'])} cards, {len(data['edges'])} relations, {data['catalogue_row_count']} catalogue rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
