"""Static HTML report — self-contained, ~30 KB, no plotting library.

:mod:`report` renders the interactive Plotly version (~5 MB, inline bundle).
This one hand-authors the quadrant map as inline SVG: small enough to share as
a single file, and the marks inherit the page's theme tokens directly instead
of needing a JS relayout. Both read the same frames, so the two reports cannot
drift apart.

Colour follows the workspace data-viz method. The quadrant is carried by
*position*, so only the two cells that carry the argument are tinted — top
right (escape) and bottom right (constrained) — and the other two stay hollow.
The two accents were validated for CVD separation and surface contrast in both
themes before being written down here.
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd

from .axes import sector_frame
from .company import (
    PARENT_SCOPE_CONFIRMED,
    PARENT_SCOPE_THIN,
    PARENT_SCOPE_UNKNOWN,
    company_frame,
)
from .config import Config
from .quadrant import rankable, thresholds, top_right
from .reference import ReferenceData, load_reference

Q_CLASS = {"AI解放": "escape", "人手依存": "bound", "AI増益": "margin", "低感応": "flat"}

# --- SVG geometry ------------------------------------------------------------
W, H = 720, 560
L, R, T, B = 96, 686, 34, 486


def px(v: float) -> float:
    return L + (v / 100.0) * (R - L)


def py(v: float) -> float:
    return B - (v / 100.0) * (B - T)


#: Candidate label placements as (text-anchor, dx, dy) in SVG units, in
#: preference order — the first entries are the conventional ones.
LABEL_SLOTS: tuple[tuple[str, float, float], ...] = (
    ("middle", 0.0, -14.0),
    ("middle", 0.0, 20.0),
    ("end", -13.0, 4.5),
    ("start", 13.0, 4.5),
    ("end", -13.0, -11.0),
    ("start", 13.0, -11.0),
    ("end", -13.0, 19.0),
    ("start", 13.0, 19.0),
    ("end", -32.0, -12.0),
    ("start", 32.0, -12.0),
    ("middle", 0.0, -28.0),
)

#: Only the key quadrant is captioned inside the map. The other three corners
#: are where the data is densest, and the quadrant cards below name them anyway.
CORNER_BOXES: tuple[tuple[float, float, float], ...] = ((R - 12 - 30, T + 22, 34.0),)

#: Roughly half an average CJK glyph's advance at the label font size.
CHAR_HALF_WIDTH = 6.4


def _label_targets(sectors: pd.DataFrame) -> set[str]:
    """The leading few plus each axis extreme.

    The quadrant cards below carry full membership, so the map stays readable
    rather than exhaustive — and the extremes are what make the framework's
    point (the most labour-short sectors are the ones AI cannot help).
    """
    keep = set(top_right(sectors, 5).index)
    keep |= set(sectors.nlargest(2, "shortage_score").index)
    keep |= set(sectors.nlargest(2, "ai_score").index)
    # 両軸の下端も入れる。「人手不足でない側」を見せないと、右上の意味が伝わらない。
    keep.add(sectors["shortage_score"].idxmin())
    keep.add(sectors["ai_score"].idxmin())
    return keep


def _place_labels(sectors: pd.DataFrame) -> dict[str, tuple[str, float, float]]:
    """Choose a slot per labelled point, least-penalty first.

    Scoring rather than first-fit matters: with first-fit, a point whose every
    slot collides falls back to a fixed slot that may be the worst of them.
    """
    keep = _label_targets(sectors)
    # Two obstacle classes with different clearances: text needs a full line of
    # vertical room from other text, but only needs to clear a marker's radius.
    label_boxes: list[tuple[float, float, float]] = []
    point_boxes = [
        (px(r["shortage_score"]), py(r["ai_score"]), 8.0) for _, r in sectors.iterrows()
    ]
    chosen: dict[str, tuple[str, float, float]] = {}

    def penalty(anchor: str, ax: float, ay: float, half: float) -> float:
        left = ax - half if anchor == "middle" else (ax - 2 * half if anchor == "end" else ax)
        score = 0.0
        if left < L - 90 or left + 2 * half > R + 6 or ay < T + 12 or ay > B + 4:
            score += 100.0
        score += 20.0 * sum(
            abs(ay - y) < 24 and abs(ax - x) < half + hw for x, y, hw in CORNER_BOXES
        )
        score += 10.0 * sum(
            abs(ay - y) < 15 and abs(ax - x) < half + hw for x, y, hw in label_boxes
        )
        score += 4.0 * sum(
            abs(ay - y) < 9 and abs(ax - x) < half + hw for x, y, hw in point_boxes
        )
        return score

    for name in sectors.sort_values("escape_potential", ascending=False).index:
        if name not in keep:
            continue
        row = sectors.loc[name]
        cx, cy = px(row["shortage_score"]), py(row["ai_score"])
        half = len(str(name)) * CHAR_HALF_WIDTH
        best_index = min(
            range(len(LABEL_SLOTS)),
            key=lambda i: (
                penalty(LABEL_SLOTS[i][0], cx + LABEL_SLOTS[i][1], cy + LABEL_SLOTS[i][2], half),
                i,  # slot order breaks ties toward the conventional placements
            ),
        )
        anchor, dx, dy = LABEL_SLOTS[best_index]
        chosen[name] = (anchor, dx, dy)
        label_boxes.append((cx + dx, cy + dy, half))
    return chosen


def _svg(sectors: pd.DataFrame, x_cut: float, y_cut: float) -> str:
    parts: list[str] = [
        f'<svg viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="東証33業種を人手不足の深刻度とAI代替可能性で並べた4象限マップ" class="map">'
    ]

    for i in range(0, 101, 10):  # graph-paper reference grid
        parts.append(
            f'<line class="grid" x1="{px(i):.1f}" y1="{T}" x2="{px(i):.1f}" y2="{B}"/>'
            f'<line class="grid" x1="{L}" y1="{py(i):.1f}" x2="{R}" y2="{py(i):.1f}"/>'
        )

    parts.append(
        f'<rect class="wash" x="{px(x_cut):.1f}" y="{T}" '
        f'width="{R - px(x_cut):.1f}" height="{py(y_cut) - T:.1f}"/>'
        f'<line class="cut" x1="{px(x_cut):.1f}" y1="{T}" x2="{px(x_cut):.1f}" y2="{B}"/>'
        f'<line class="cut" x1="{L}" y1="{py(y_cut):.1f}" x2="{R}" y2="{py(y_cut):.1f}"/>'
        f'<rect class="frame" x="{L}" y="{T}" width="{R - L}" height="{B - T}"/>'
        f'<text class="axis" x="{(L + R) / 2:.0f}" y="{B + 40}" text-anchor="middle">'
        f"人手不足の深刻度 →</text>"
        f'<text class="axis" x="{L - 62}" y="{(T + B) / 2:.0f}" text-anchor="middle" '
        f'transform="rotate(-90 {L - 62} {(T + B) / 2:.0f})">AI代替可能性 →</text>'
        f'<text class="corner" x="{R - 12}" y="{T + 22}" text-anchor="end">AI解放</text>'
    )
    for v in (0, 50, 100):
        parts.append(
            f'<text class="tick" x="{px(v):.1f}" y="{B + 18}" text-anchor="middle">{v}</text>'
            f'<text class="tick" x="{L - 12}" y="{py(v) + 4:.1f}" text-anchor="end">{v}</text>'
        )

    labels = _place_labels(sectors)
    for name, row in sectors.iterrows():
        cx, cy = px(row["shortage_score"]), py(row["ai_score"])
        cls = Q_CLASS[row["quadrant"]]
        tip = (
            f"{name}｜人手不足 {row['shortage_score']:.0f} / "
            f"AI代替 {row['ai_score']:.0f}（労働の{row['ai_exposure_pct']:.0f}%）"
        )
        parts.append(
            f'<g class="pt pt--{cls}"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="6.5"/>'
            f"<title>{html.escape(tip)}</title></g>"
        )
        if name in labels:
            anchor, dx, dy = labels[name]
            parts.append(
                f'<text class="lbl lbl--{cls}" x="{cx + dx:.1f}" y="{cy + dy:.1f}" '
                f'text-anchor="{anchor}">{html.escape(str(name))}</text>'
            )

    parts.append("</svg>")
    return "".join(parts)


def _quadrant_card(sectors: pd.DataFrame, name: str, blurb: str, key: bool = False) -> str:
    members = sectors[sectors["quadrant"] == name].sort_values("escape_potential", ascending=False)
    chips = "".join(
        f'<li><span class="chip-name">{html.escape(str(i))}</span>'
        f'<span class="chip-num">{r.shortage_score:.0f}'
        f'<span class="sep">/</span>{r.ai_score:.0f}</span></li>'
        for i, r in members.iterrows()
    )
    return (
        f'<article class="cell cell--{Q_CLASS[name]}{" is-key" if key else ""}">'
        f'<header><h3>{html.escape(name)}</h3>'
        f'<span class="count">{len(members)}業種</span></header>'
        f'<p>{blurb}</p><ul class="chips">{chips}</ul></article>'
    )


def _num(value: float, fmt: str = "{:.0f}") -> str:
    """Missing stays visibly missing. Nothing here is ever zero-filled."""
    return "—" if pd.isna(value) else fmt.format(value)


def _company_table(companies: pd.DataFrame, n: int, *, with_pnl: bool) -> tuple[str, str, str, int]:
    """Header, rows, a caption and the number of rows shown, for the top-right table.

    With financials the ranking switches to the P/L translation. Company scores
    come from the sector plus a 3×3 tilt, so every company in a sector shares an
    escape potential — cutting that ordering at N returns an arbitrary slice of
    the leading sector. 人件費 and 営業利益 sit next to the uplift because it is a
    ratio: a thin parent-company operating profit lifts it on the denominator
    alone.

    順位表は **単体スコープが確認できた会社だけ**で作る。「※が付いていない」は
    「単体が事業を映していると確認できた」ではなく、連結従業員が取れなかった
    判定不能を含んでしまう。3群の件数はキャプションに出す。
    """
    rows = top_right(companies)
    if with_pnl:
        rows = rows[rankable(rows)]
        scope = rows.get("parent_scope", pd.Series(PARENT_SCOPE_CONFIRMED, index=rows.index))
        counts = {k: int((scope == k).sum()) for k in
                  (PARENT_SCOPE_CONFIRMED, PARENT_SCOPE_UNKNOWN, PARENT_SCOPE_THIN)}
        rows = rows[scope == PARENT_SCOPE_CONFIRMED]
        rows = rows.sort_values("op_margin_uplift_pp", ascending=False, na_position="last")
        caption = (
            f"営業利益率の押上げ幅（pp）順。押上げ余地を定義できるのは"
            f"{sum(counts.values())}社（営業利益が0以下、人件費が売上を超える単体は除外）で、"
            f"その内訳は 単体スコープ確認済み{counts[PARENT_SCOPE_CONFIRMED]}社 / "
            f"判定不能{counts[PARENT_SCOPE_UNKNOWN]}社 / "
            f"※単体従業員が連結の20%未満{counts[PARENT_SCOPE_THIN]}社。"
            f"本表は確認済み{counts[PARENT_SCOPE_CONFIRMED]}社から。"
            "持株会社の単体は本社機能の空箱なので限界利益率が実態より高く出る"
        )
    else:
        caption = "脱出ポテンシャル（2軸の幾何平均）順"
    rows = rows.head(n)
    shown = len(rows)

    head = ('<th>コード</th><th>銘柄</th><th>業種</th><th class="num">人手不足</th>'
            '<th class="num">AI代替</th><th class="num">脱出</th>')
    if with_pnl:
        head += ('<th class="num">欠員率</th><th class="num">限界利益率</th>'
                 '<th class="num">利益率押上げ(pp)</th>'
                 '<th class="num">営業利益押上げ余地%</th>'
                 '<th class="num">回復売上(億)</th><th class="num">営業利益(億)</th>'
                 '<th class="num">単体/連結</th>')

    body = []
    for code, r in rows.iterrows():
        flag = getattr(r, "parent_scope_flag", "") or ""
        cells = (
            f'<td class="code">{html.escape(str(code))}</td>'
            f"<td>{html.escape(r['name'])}{html.escape(flag)}</td>"
            f'<td class="sec">{html.escape(r["sector33"])}</td>'
            f'<td class="num">{r.shortage_score:.0f}</td>'
            f'<td class="num">{r.ai_score:.0f}</td>'
            f'<td class="num{"" if with_pnl else " strong"}">{r.escape_potential:.0f}</td>'
        )
        if with_pnl:
            cells += (
                f'<td class="num">{_num(r.vacancy_rate_pct, "{:.1f}%")}</td>'
                f'<td class="num">{_num(r.contribution_margin * 100, "{:.0f}%")}</td>'
                f'<td class="num strong">{_num(r.op_margin_uplift_pp, "{:.2f}")}</td>'
                f'<td class="num">{_num(r.op_uplift_pct, "{:,.0f}")}</td>'
                f'<td class="num">{_num(r.recovered_revenue / 1e8, "{:,.0f}")}</td>'
                f'<td class="num">{_num(r.operating_profit / 1e8, "{:,.0f}")}</td>'
                f'<td class="num">'
                f'{_num(getattr(r, "parent_employee_share", float("nan")) * 100, "{:.0f}%")}</td>'
            )
        body.append(f"<tr>{cells}</tr>")
    return head, "".join(body), caption, shown


CSS = """
:root{
  color-scheme: light;
  --ground:#f6f7f6; --panel:#fdfdfc; --sunk:#eef0ef;
  --ink:#141a1c; --ink-2:#4d585d; --ink-3:#7d878c;
  --rule:#dde1df; --grid:#e9ecea;
  --ai:#35569a; --ai-wash:rgba(53,86,154,.07); --ai-line:rgba(53,86,154,.30);
  --clay:#a5523f;
  --shadow:0 1px 2px rgba(20,26,28,.05);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --ground:#14181a; --panel:#1b2023; --sunk:#20262a;
    --ink:#eaefee; --ink-2:#a6b1b5; --ink-3:#7d878c;
    --rule:#2a3134; --grid:#232a2d;
    --ai:#6d93de; --ai-wash:rgba(109,147,222,.11); --ai-line:rgba(109,147,222,.34);
    --clay:#d3714f;
    --shadow:0 1px 2px rgba(0,0,0,.3);
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --ground:#14181a; --panel:#1b2023; --sunk:#20262a;
  --ink:#eaefee; --ink-2:#a6b1b5; --ink-3:#7d878c;
  --rule:#2a3134; --grid:#232a2d;
  --ai:#6d93de; --ai-wash:rgba(109,147,222,.11); --ai-line:rgba(109,147,222,.34);
  --clay:#d3714f;
  --shadow:0 1px 2px rgba(0,0,0,.3);
}

*{box-sizing:border-box;}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:system-ui,-apple-system,"Segoe UI","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif;
  font-size:16px; line-height:1.78; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1080px; margin:0 auto; padding:56px 24px 96px; display:flex; flex-direction:column; gap:56px;}
.col{max-width:64ch;}

.eyebrow{
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:.72rem; letter-spacing:.16em; text-transform:uppercase;
  color:var(--ink-3); margin:0 0 14px;
}
h1{
  font-size:clamp(2rem,4.6vw,3rem); line-height:1.16; letter-spacing:-.022em;
  font-weight:680; margin:0 0 18px; text-wrap:balance;
}
h1 .x{color:var(--ink-3); font-weight:400; padding:0 .12em;}
.standfirst{font-size:1.09rem; color:var(--ink-2); margin:0;}
.standfirst b{color:var(--ink); font-weight:640;}
h2{font-size:1.32rem; letter-spacing:-.012em; font-weight:660; margin:0 0 6px; text-wrap:balance;}
h2 + .sub{color:var(--ink-2); margin:0 0 22px;}
p{margin:0 0 18px;}
.col p:last-child{margin-bottom:0;}

figure{margin:0; display:flex; flex-direction:column; gap:14px;}
.map-frame{
  background:var(--panel); border:1px solid var(--rule); border-radius:4px;
  padding:20px 12px 8px; overflow-x:auto; box-shadow:var(--shadow);
}
.map{width:100%; min-width:660px; height:auto; display:block;}
.grid{stroke:var(--grid); stroke-width:1;}
.frame{fill:none; stroke:var(--rule); stroke-width:1;}
.wash{fill:var(--ai-wash);}
.cut{stroke:var(--ai-line); stroke-width:1.5; stroke-dasharray:5 4;}
.axis{fill:var(--ink-2); font-size:14px;}
.tick,.corner{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; fill:var(--ink-3); font-size:12px;}
.corner{font-size:12.5px; letter-spacing:.12em; fill:var(--ai);}
.pt circle{fill:var(--panel); stroke:var(--ink-3); stroke-width:1.6;}
.pt--escape circle{fill:var(--ai); stroke:var(--panel); stroke-width:2;}
.pt--bound circle{fill:var(--clay); stroke:var(--panel); stroke-width:2;}
.lbl{font-size:12.5px; fill:var(--ink-2);}
.lbl--escape{fill:var(--ai); font-weight:620;}
.lbl--bound{fill:var(--clay); font-weight:620;}
figcaption{color:var(--ink-3); font-size:.86rem; line-height:1.6; max-width:72ch;}
.key{font-size:.8em; letter-spacing:-.05em;}
.key--escape{color:var(--ai);}
.key--bound{color:var(--clay);}

.cells{display:grid; grid-template-columns:1fr 1fr; gap:14px;}
@media (max-width:720px){ .cells{grid-template-columns:1fr;} }
.cell{
  background:var(--panel); border:1px solid var(--rule); border-radius:4px;
  padding:18px 20px 20px; box-shadow:var(--shadow);
}
.cell.is-key{border-color:var(--ai-line); background:linear-gradient(var(--ai-wash),var(--ai-wash)),var(--panel);}
.cell header{display:flex; align-items:baseline; justify-content:space-between; gap:12px; margin-bottom:6px;}
.cell h3{font-size:1.02rem; margin:0; letter-spacing:.01em;}
.cell--escape h3{color:var(--ai);}
.cell--bound h3{color:var(--clay);}
.count{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.72rem; color:var(--ink-3);}
.cell p{font-size:.92rem; color:var(--ink-2); margin:0 0 14px; line-height:1.65;}
.chips{list-style:none; margin:0; padding:0; display:flex; flex-direction:column;}
.chips li{
  display:flex; align-items:baseline; justify-content:space-between; gap:10px;
  padding:5px 0; border-top:1px solid var(--rule); font-size:.9rem;
}
.chips li:first-child{border-top:none;}
.chip-name{color:var(--ink);}
.chip-num{
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.8rem;
  color:var(--ink-3); font-variant-numeric:tabular-nums; white-space:nowrap;
}
.sep{padding:0 .35em; opacity:.55;}

.table-frame{
  background:var(--panel); border:1px solid var(--rule); border-radius:4px;
  overflow-x:auto; box-shadow:var(--shadow);
}
table{width:100%; border-collapse:collapse; font-size:.9rem; min-width:600px;}
th,td{text-align:left; padding:9px 16px; border-bottom:1px solid var(--rule); white-space:nowrap;}
thead th{
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:.7rem; letter-spacing:.09em; text-transform:uppercase;
  color:var(--ink-3); font-weight:500; background:var(--sunk);
}
tbody tr:last-child td{border-bottom:none;}
td.code,td.num{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-variant-numeric:tabular-nums;}
td.code{color:var(--ink-3);}
td.num{text-align:right; color:var(--ink-2);}
td.num.strong{color:var(--ai); font-weight:640;}
td.sec{color:var(--ink-3);}

.method{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px;}
.note{background:var(--panel); border:1px solid var(--rule); border-radius:4px; padding:16px 18px; box-shadow:var(--shadow);}
.note h4{margin:0 0 6px; font-size:.94rem;}
.note p{margin:0; font-size:.88rem; color:var(--ink-2); line-height:1.62;}
.note code{
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.82em;
  background:var(--sunk); padding:.1em .35em; border-radius:3px; color:var(--ink);
}
.limits{list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:11px;}
.limits li{padding-left:16px; position:relative; color:var(--ink-2); font-size:.94rem; line-height:1.65;}
.limits li::before{content:""; position:absolute; left:0; top:.72em; width:6px; height:1px; background:var(--ink-3);}
.limits b{color:var(--ink); font-weight:620;}
footer{border-top:1px solid var(--rule); padding-top:20px; color:var(--ink-3); font-size:.84rem;}
footer code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;}
"""

TOP_COMPANIES = 24


def render(
    cfg: Config | None = None,
    ref: ReferenceData | None = None,
    *,
    fragment: bool = False,
    financials: pd.DataFrame | None = None,
    top_companies: int = TOP_COMPANIES,
) -> str:
    """Return the report HTML.

    ``fragment=True`` omits the document skeleton and returns ``<title>`` +
    ``<style>`` + content, which is the shape a hosted artifact page expects.

    ``financials`` adds the P/L translation to the company table and ranks by
    it. This report stays self-contained and small enough to attach to an
    email, which the Plotly version (about 5 MB) is not.
    """
    cfg = cfg or Config()
    cfg.validate()
    ref = ref or load_reference()

    sectors = sector_frame(cfg, ref)
    companies = company_frame(cfg, ref, financials)
    x_cut, y_cut = thresholds(sectors["shortage_score"], sectors["ai_score"], cfg)

    cells = "".join([
        _quadrant_card(sectors, "AI増益", "人手不足ではないが、労働のAI代替余地は大きい。成長ではなくマージンの話。"),
        _quadrant_card(sectors, "AI解放", "人手不足が深刻で、かつその労働をAIで置き換えられる。制約解除の期待値が最大。", key=True),
        _quadrant_card(sectors, "低感応", "どちらも低い。この枠組みでは論点にならない。"),
        _quadrant_card(sectors, "人手依存", "人手不足は深刻だがAIでは解けない。賃上げ・自動化設備・価格転嫁・M&Aの世界。"),
    ])

    with_pnl = financials is not None and "op_uplift_pct" in companies.columns
    top_n = min(top_companies, int((companies["quadrant"] == "AI解放").sum()))
    company_head, company_body, company_caption, shown = _company_table(
        companies, top_n, with_pnl=with_pnl
    )
    content = f"""<title>人手不足×AI 4象限マップ</title>
<style>{CSS}</style>
<div class="wrap">

<header class="col">
  <p class="eyebrow">東証33業種 / 上場{len(companies)}銘柄</p>
  <h1>人手不足の深刻度<span class="x">×</span>AI代替可能性</h1>
  <p class="standfirst">日本の上場企業を2軸で並べる。<b>右上に入る企業だけが、人手不足という供給制約を賃上げ以外の手段で外せる。</b>
  そしてこの2軸は、日本では負の相関を持ちやすい — だから右上は狭く、そこに入ることが情報になる。</p>
</header>

<figure>
  <div class="map-frame">{_svg(sectors, x_cut, y_cut)}</div>
  <figcaption>点は東証33業種。境界は33業種の中央値（人手不足 {x_cut:.0f} / AI代替 {y_cut:.0f}）。
  企業の象限もこの同じ境界を投影して当てている。
  <span class="key key--escape">■</span> 右上＝AI解放、<span class="key key--bound">■</span> 右下＝人手依存、
  白抜きはその他の2象限。ホバーで各業種の数値が出る。</figcaption>
</figure>

<section class="col">
  <h2>なぜ右上が狭いのか</h2>
  <p>人手不足が最も深刻な労働 — 建設・運転・介護・保安 — は身体労働で、生成AIの射程外にある。
  逆に生成AIが最も得意な労働 — 事務・審査・コーディング — は、有効求人倍率で見れば長く1倍を下回っている。
  <b>建設業は人手不足 {sectors.loc["建設業", "shortage_score"]:.0f} / AI代替 {sectors.loc["建設業", "ai_score"]:.0f}、
  陸運業は {sectors.loc["陸運業", "shortage_score"]:.0f} / {sectors.loc["陸運業", "ai_score"]:.0f}。</b>
  どちらもAIでは救われない側にはっきり分離される。
  一方 <b>銀行業は {sectors.loc["銀行業", "shortage_score"]:.0f} / {sectors.loc["銀行業", "ai_score"]:.0f}</b> —
  人手不足ではないがAI余地は最大級で、これはコストの話であって成長の話ではない。</p>
  <p>「人手不足だからAI」という素朴な議論の大半は、実際には右下か左上に落ちる。
  2軸を掛け合わせて初めて、その区別がつく。</p>
</section>

<section>
  <h2>4象限</h2>
  <p class="sub">配置はマップの象限と同じ。数字は 人手不足 / AI代替。</p>
  <div class="cells">{cells}</div>
</section>

<section>
  <h2>右上に入った銘柄</h2>
  <p class="sub">{company_caption}・上位{shown}。ユニバース{len(companies)}銘柄中。</p>
  <div class="table-frame">
    <table>
      <thead><tr>{company_head}</tr></thead>
      <tbody>{company_body}</tbody>
    </table>
  </div>
</section>

<section>
  <h2>軸の作り方</h2>
  <div class="method">
    <div class="note"><h4>X軸 — 人手不足の深刻度</h4>
      <p>欠員率(0.30)・短観 雇用人員判断DI(0.30)・有効求人倍率(0.20)・55歳以上比率(0.10)・
      離職率(0.05)・所定外労働時間(0.05) の6指標を33業種横断で z 化し、±2.5σ でクリップして
      重み付き合成。出典は雇用動向調査・日銀短観・一般職業紹介状況・労働力調査・毎月勤労統計。
      有効求人倍率はハローワーク経由しか映さないので重みを 0.20 に抑えている。</p></div>
    <div class="note"><h4>Y軸 — 生成AI曝露度</h4>
      <p>業種の職業構成比（労働力調査 産業×職業、18区分）と、職業別の生成AI exposure
      （ILO Working Paper 140, Gmyrek et al. 2025）の内積に、規制ドラッグを掛ける。
      ILO のスコアは<b>タスク単位の自動化ポテンシャルの職業平均</b>で、
      「置き換えられた従業員の割合」ではない。「Not Exposed」に分類された231職業でも
      0.09〜0.36 の値を持つ連続量である。
      また単一の数値で<b>物理的自動化を測っていない</b>ので、この軸は生成AIの話に限られる。
      倉庫AMR・自動運転はこの地図の外にある。</p></div>
    <div class="note"><h4>P/L への換算 — 人減らしではなく売上回復</h4>
      <p>経路は <b>AI → 人手不足の緩和 → 取り逃していた売上の回復 → 利益増</b>。
      人が採れずに需要を取り逃している業種では、AIが空けた労働は「増員できたのと同じこと」として
      まず売上に効く。<code>埋められる欠員 = min(AI曝露度 × 実現率, 欠員率)</code>、
      <code>利益増 = 売上 × 埋められる欠員 × 限界利益率</code>、
      <code>限界利益率 = (営業利益 + 人件費) ÷ 売上</code>。
      人を増やさない前提なので人件費は固定費として扱い、限界利益率の分子に入る。
      実現率の既定は {cfg.realization_rate:.2f}。既定設定では全33業種で
      「空く労働 &gt; 欠員」なので、効く量を決めるのは欠員率で、AI軸は
      <b>そもそも埋められるのかという関門</b>として働く。
      これは推定ではなく<b>シナリオ</b>で、曝露が労働時間の解放に等しいという仮定の上に立つ。
      導入コストは引いていない。</p></div>
  </div>
</section>

<section class="col">
  <h2>この地図が言っていないこと</h2>
  <ul class="limits">
    <li><b>両軸とも相対値。</b>33業種内での順位を0-100に正規化したもので、絶対水準ではない。
    象限の境界は33業種の中央値で一度だけ決め、企業にはそれを投影して当てている。</li>
    <li><b>ISCO と日本標準職業分類の対応は analyst が当てている。</b>ILO のスコア自体は公表値だが、
    ISCO-08 のどのグループを日本の職業区分に対応させるかは判断であり、
    グループ内は（日本の職業別就業者数が ISCO 粒度で無いため）単純平均している。</li>
    <li><b>物理的自動化が入っていない。</b>ILO の指数は生成AIの exposure のみ。
    陸運・倉庫の人手不足は自動運転やAMRで解ける可能性があるが、この軸には映らない。</li>
    <li><b>回復する売上には需要があると仮定している。</b>「人がいれば取れたはずの需要」が
    今も残っている前提。欠員率は募集中の求人しか映さないので、諦めて募集をやめた分は入らない
    （＝過小側）。一方で需要が消えていれば回復しない（＝過大側）。両側に振れる。</li>
    <li><b>限界利益率は控えめに出る。</b>人件費以外の費用をすべて変動費として扱っているため、
    減価償却や地代のような固定費まで変動費に数えている。実際の増分利益はこれより大きい。</li>
    <li><b>単体基準の限界利益率は持株会社で壊れる。</b>単体売上が管理報酬だけの空箱では
    (営業利益+人件費)÷売上 が0.9近くまで上がる。単体従業員が連結の20%未満を ※、
    連結従業員が取れず判定できないものを † とし、順位表は<b>確認済みだけ</b>で作っている。
    「※が付いていない」は「確認できた」ではない。</li>
    <li><b>AI案件による売上増（需要側）は入っていない。</b>SIerや半導体はAIそのものが商売になるが、
    この枠組みは供給制約側だけを測る。</li>
    <li><b>省力化が顧客に移転する分を引いていない。</b>受託型（SI・人材・警備）では、
    余力が利益ではなく単価下落として出る可能性が高い。</li>
    <li><b>バリュエーションでも競争優位でもない。</b>制約に対する感応度の地図であって、投資判断ではない。</li>
  </ul>
</section>

<footer>
  再現コード・参照テーブル（出典と時点つき）は <code>labor_ai_quadrant/</code> に。
  既定設定は <code>realization_rate={cfg.realization_rate}</code>、参照データ時点 {ref.vintages["sector_labor_shortage"]}。
</footer>

</div>
"""
    if fragment:
        return content

    head, rest = content.split('<div class="wrap">', 1)
    return (
        '<!doctype html>\n<html lang="ja"><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'{head}</head>\n<body>\n<div class="wrap">{rest}</body></html>\n'
    )


def build_static_report(
    out_path: str | Path,
    cfg: Config | None = None,
    ref: ReferenceData | None = None,
    *,
    fragment: bool = False,
    financials: pd.DataFrame | None = None,
    top_companies: int = TOP_COMPANIES,
) -> Path:
    """Render the static report and return the path written."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        render(cfg, ref, fragment=fragment, financials=financials, top_companies=top_companies),
        encoding="utf-8",
    )
    return out
