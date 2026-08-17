"""Offline HTML report: the 4-quadrant map plus the ranked top-right list.

Self-contained (Plotly is inlined), no network at view time, light/dark aware.
Colour follows the workspace data-viz method: the quadrant is carried by
*position*, so marks use a single-hue sequential ramp on escape potential
rather than a categorical colour per quadrant.
"""

from __future__ import annotations

import dataclasses
import html
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from .axes import sector_frame
from .company import company_frame
from .config import Q_ESCAPE, QUADRANT_MEANING, QUADRANT_ORDER, Config
from .quadrant import quadrant_summary, rankable, thresholds, top_right
from .reference import load_reference

# --- theme -------------------------------------------------------------------
# Values from the workspace data-viz reference palette. The sequential ramp runs
# light->dark on the light surface and dark->light on the dark surface, so that
# "high escape potential" is always the step furthest from the surface.
THEME = {
    "light": {
        "surface": "#fcfcfb",
        "plane": "#f9f9f7",
        "text": "#0b0b0b",
        "secondary": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "axis": "#c3c2b7",
        "band": "rgba(42,120,214,0.05)",
        "ramp": [[0.0, "#86b6ef"], [1.0, "#104281"]],
        "accent": "#2a78d6",
        "accent_alt": "#eb6834",
        "ring": "#fcfcfb",
    },
    "dark": {
        "surface": "#1a1a19",
        "plane": "#0d0d0d",
        "text": "#ffffff",
        "secondary": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
        "band": "rgba(57,135,229,0.10)",
        "ramp": [[0.0, "#184f95"], [1.0, "#9ec5f4"]],
        "accent": "#3987e5",
        "accent_alt": "#d95926",
        "ring": "#1a1a19",
    },
}

FONT = 'system-ui, -apple-system, "Segoe UI", "Hiragino Sans", "Noto Sans JP", sans-serif'


def _base_layout(t: dict, title: str, x_title: str, y_title: str) -> dict:
    return {
        "title": {"text": title, "font": {"size": 16, "color": t["text"]}},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": FONT, "color": t["secondary"], "size": 12},
        "xaxis": {
            "title": {"text": x_title, "font": {"color": t["secondary"]}},
            "range": [-7, 107],
            "gridcolor": t["grid"],
            "zeroline": False,
            "linecolor": t["axis"],
            "tickfont": {"color": t["muted"]},
        },
        "yaxis": {
            "title": {"text": y_title, "font": {"color": t["secondary"]}},
            "range": [-7, 107],
            "gridcolor": t["grid"],
            "zeroline": False,
            "linecolor": t["axis"],
            "tickfont": {"color": t["muted"]},
        },
        "margin": {"l": 70, "r": 30, "t": 60, "b": 60},
        "hoverlabel": {"font": {"family": FONT}},
        "showlegend": False,
    }


def _quadrant_shapes(x_cut: float, y_cut: float, t: dict) -> list[dict]:
    """Neutral wash on the top-right cell plus the two threshold lines."""
    return [
        {
            "type": "rect",
            "x0": x_cut, "x1": 107, "y0": y_cut, "y1": 107,
            "fillcolor": t["band"],
            "line": {"width": 0},
            "layer": "below",
        },
        {
            "type": "line",
            "x0": x_cut, "x1": x_cut, "y0": -7, "y1": 107,
            "line": {"color": t["axis"], "width": 1, "dash": "dot"},
            "layer": "below",
        },
        {
            "type": "line",
            "x0": -7, "x1": 107, "y0": y_cut, "y1": y_cut,
            "line": {"color": t["axis"], "width": 1, "dash": "dot"},
            "layer": "below",
        },
    ]


def _quadrant_annotations(x_cut: float, y_cut: float, t: dict) -> list[dict]:
    corners = [
        (Q_ESCAPE, 105, 105, "right", "top"),
        ("AI増益", -5, 105, "left", "top"),
        ("人手依存", 105, -5, "right", "bottom"),
        ("低感応", -5, -5, "left", "bottom"),
    ]
    return [
        {
            "x": x, "y": y, "text": f"<b>{label}</b>",
            "showarrow": False,
            "xanchor": xa, "yanchor": ya,
            "font": {"color": t["muted"], "size": 12},
        }
        for label, x, y, xa, ya in corners
    ]


def _label_targets(df: pd.DataFrame, top_n: int) -> set:
    """Which points get a direct label.

    The top-right members carry the headline, and the axis extremes carry the
    framework's actual lesson (the most labour-short sectors are the ones AI
    cannot help), so both are labelled.
    """
    targets = set(top_right(df, top_n).index)
    targets |= set(df.nlargest(3, "shortage_score").index)
    targets |= set(df.nlargest(3, "ai_score").index)
    return targets


#: Where a label sits relative to its mark, as (position name, dx, dy) in axis units.
_LABEL_SLOTS = (
    ("top center", 0.0, 5.0),
    ("bottom center", 0.0, -5.0),
    ("middle left", -6.0, 0.0),
    ("middle right", 6.0, 0.0),
)
_LABEL_MIN_DX = 9.0
_LABEL_MIN_DY = 4.5


def _text_positions(df: pd.DataFrame, labelled: set) -> list[str]:
    """Place labels greedily, avoiding both the plot edges and each other.

    Points are visited from the highest escape potential down, so when two
    labels compete for the same slot the more important one keeps it.
    """
    placed: list[tuple[float, float]] = []
    chosen: dict = {}

    for idx in df.sort_values("escape_potential", ascending=False).index:
        if idx not in labelled:
            continue
        x, y = df.loc[idx, "shortage_score"], df.loc[idx, "ai_score"]
        for name, dx, dy in _LABEL_SLOTS:
            ax, ay = x + dx, y + dy
            if not (-7 <= ax <= 107 and -7 <= ay <= 107):
                continue
            if any(abs(ax - px) < _LABEL_MIN_DX and abs(ay - py) < _LABEL_MIN_DY for px, py in placed):
                continue
            chosen[idx] = name
            placed.append((ax, ay))
            break
        else:
            # Every slot collides or falls outside; keep the label rather than
            # drop it, and let the default position take the overlap.
            chosen[idx] = "top center"
            placed.append((x, y + 5.0))

    return [chosen.get(idx, "top center") for idx in df.index]


def _scatter_figure(
    df: pd.DataFrame,
    label_col: str,
    title: str,
    cfg: Config,
    marker_size: int,
    label_top_n: int,
) -> go.Figure:
    t = THEME["light"]
    x_cut, y_cut = thresholds(df["shortage_score"], df["ai_score"], cfg)

    # label_top_n <= 0 disables direct labels: on the company chart many names
    # land on identical coordinates, where stacked labels are unreadable and the
    # ranked table below is the better label layer.
    labelled = _label_targets(df, label_top_n) if label_top_n > 0 else set()
    text = [df.loc[i, label_col] if i in labelled else "" for i in df.index]

    hover = [
        f"<b>{html.escape(str(row[label_col]))}</b><br>"
        f"人手不足深刻度: {row['shortage_score']:.0f}<br>"
        f"AI代替可能性: {row['ai_score']:.0f}<br>"
        f"AI代替可能な労働の割合: {row['ai_substitutable_share_pct']:.0f}%<br>"
        f"脱出ポテンシャル: {row['escape_potential']:.0f}<br>"
        f"象限: {row['quadrant']}"
        for _, row in df.iterrows()
    ]

    fig = go.Figure(
        go.Scatter(
            x=df["shortage_score"],
            y=df["ai_score"],
            mode="markers+text",
            text=text,
            textposition=_text_positions(df, labelled),
            textfont={"size": 10, "color": t["secondary"], "family": FONT},
            hovertext=hover,
            hoverinfo="text",
            marker={
                "size": marker_size,
                "color": df["escape_potential"],
                "colorscale": t["ramp"],
                "cmin": 0,
                "cmax": 100,
                "opacity": 0.9,
                "line": {"width": 2, "color": t["ring"]},
                "colorbar": {
                    "title": {"text": "脱出<br>ポテンシャル", "font": {"size": 11, "color": t["secondary"]}},
                    "tickfont": {"size": 10, "color": t["muted"]},
                    "thickness": 12,
                    "len": 0.6,
                    "outlinewidth": 0,
                },
            },
        )
    )
    layout = _base_layout(t, title, "人手不足の深刻度 →", "AI代替可能性 →")
    layout["shapes"] = _quadrant_shapes(x_cut, y_cut, t)
    layout["annotations"] = _quadrant_annotations(x_cut, y_cut, t)
    fig.update_layout(**layout)
    return fig


def leave_one_out(ref, cfg: Config) -> pd.DataFrame:
    """脱出ポテンシャルが、人手不足6指標のどれを外しても残るかを測る。

    重み配分そのものが analyst 判断なので、「どれか1本を落としても順位が生きるか」
    を見るのが、この枠組みで唯一意味のある感応度になる（AI軸側は ILO の公表スコアで
    固定されており、振るパラメータが無い）。
    """
    base = sector_frame(cfg, ref)["escape_potential"]
    runs = {}
    for indicator in ref.shortage_weights.index:
        weights = ref.shortage_weights.drop(indicator)
        trimmed = dataclasses.replace(ref, shortage_weights=weights / weights.sum())
        runs[indicator] = sector_frame(cfg, trimmed)["escape_potential"]
    grid = pd.DataFrame(runs)
    return pd.DataFrame({"base": base, "low": grid.min(axis=1), "high": grid.max(axis=1),
                         "worst_when_dropping": grid.idxmin(axis=1)})


def _sensitivity_figure(ref, base_cfg: Config) -> go.Figure:
    """Leave-one-out range of escape potential over the six shortage indicators."""
    t = THEME["light"]
    loo = leave_one_out(ref, base_cfg)
    order = loo["base"].sort_values(ascending=True).index[-14:]
    fig = go.Figure()

    for name in order:
        fig.add_trace(
            go.Scatter(
                x=[loo.loc[name, "low"], loo.loc[name, "high"]],
                y=[name, name],
                mode="lines",
                line={"color": t["axis"], "width": 4},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    fig.add_trace(
        go.Scatter(
            x=loo.loc[order, "low"], y=list(order), mode="markers", name="6指標のどれかを外したときの最小",
            marker={"size": 9, "color": t["accent_alt"], "line": {"width": 2, "color": t["ring"]}},
            customdata=loo.loc[order, "worst_when_dropping"],
            hovertemplate="%{y}<br>最小 %{x:.0f}（%{customdata} を外したとき）<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=loo.loc[order, "base"], y=list(order), mode="markers", name="6指標すべて（既定）",
            marker={"size": 12, "color": t["accent"], "line": {"width": 2, "color": t["ring"]}},
            hovertemplate="%{y}<br>既定 %{x:.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        title={"text": "感応度: 人手不足6指標のどれか1本を外しても順位は残るか（脱出ポテンシャル）",
               "font": {"size": 16, "color": t["text"]}},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": FONT, "color": t["secondary"], "size": 12},
        xaxis={"title": {"text": "脱出ポテンシャル"}, "gridcolor": t["grid"], "zeroline": False,
               "linecolor": t["axis"], "tickfont": {"color": t["muted"]}},
        yaxis={"gridcolor": "rgba(0,0,0,0)", "linecolor": t["axis"], "tickfont": {"color": t["secondary"]}},
        margin={"l": 150, "r": 30, "t": 60, "b": 50},
        legend={"orientation": "h", "y": -0.12, "x": 0, "font": {"color": t["secondary"]}},
        height=520,
    )
    return fig


# --- HTML assembly -----------------------------------------------------------

def _table(df: pd.DataFrame, columns: dict[str, str], caption: str) -> str:
    head = "".join(f"<th>{html.escape(v)}</th>" for v in columns.values())
    rows = []
    for idx, row in df.iterrows():
        cells = []
        for col in columns:
            val = idx if col == "__index__" else row[col]
            if isinstance(val, float):
                # 欠損は "nan" ではなく空欄。0埋めせず落とす設計なので表に必ず出る。
                val = "—" if pd.isna(val) else f"{val:,.1f}"
            cells.append(f"<td>{html.escape(str(val))}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        f'<figure class="table-wrap"><figcaption>{html.escape(caption)}</figcaption>'
        f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></figure>"
    )


_CSS = """
:root {
  --surface: #fcfcfb; --plane: #f9f9f7; --text: #0b0b0b; --secondary: #52514e;
  --muted: #898781; --grid: #e1e0d9; --border: rgba(11,11,11,0.10); --band: rgba(42,120,214,0.06);
  color-scheme: light;
}
:root[data-theme="dark"] {
  --surface: #1a1a19; --plane: #0d0d0d; --text: #ffffff; --secondary: #c3c2b7;
  --muted: #898781; --grid: #2c2c2a; --border: rgba(255,255,255,0.10); --band: rgba(57,135,229,0.12);
  color-scheme: dark;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--plane); color: var(--text);
  font-family: system-ui, -apple-system, "Segoe UI", "Hiragino Sans", "Noto Sans JP", sans-serif;
  line-height: 1.7;
}
main { max-width: 1120px; margin: 0 auto; padding: 32px 20px 80px; }
h1 { font-size: 1.7rem; margin: 0 0 4px; letter-spacing: -0.01em; }
h2 { font-size: 1.15rem; margin: 48px 0 8px; }
h3 { font-size: 1rem; margin: 28px 0 6px; }
p, li { color: var(--secondary); }
.lede { font-size: 1.02rem; }
.meta { color: var(--muted); font-size: 0.85rem; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
        padding: 12px 12px 4px; margin: 16px 0; overflow-x: auto; }
.table-wrap { margin: 16px 0; overflow-x: auto; background: var(--surface);
              border: 1px solid var(--border); border-radius: 10px; }
figcaption { padding: 12px 14px 0; color: var(--muted); font-size: 0.85rem; }
table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
th, td { text-align: left; padding: 8px 14px; border-bottom: 1px solid var(--grid);
         font-variant-numeric: tabular-nums; white-space: nowrap; }
th { color: var(--muted); font-weight: 600; }
td { color: var(--secondary); }
td:first-child, th:first-child { white-space: normal; }
tbody tr:last-child td { border-bottom: none; }
.quads { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin: 16px 0; }
.quad { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
.quad b { color: var(--text); }
.quad.is-key { background: var(--band); }
.toggle { position: fixed; top: 14px; right: 14px; z-index: 10; background: var(--surface);
          color: var(--secondary); border: 1px solid var(--border); border-radius: 999px;
          padding: 7px 14px; font: inherit; font-size: 0.82rem; cursor: pointer; }
.note { border-left: 3px solid var(--grid); padding: 2px 0 2px 14px; margin: 16px 0; }
"""

_JS_TEMPLATE = """
const THEME = __THEME__;
const FIG_IDS = __FIG_IDS__;

function applyTheme(mode) {
  document.documentElement.setAttribute('data-theme', mode);
  document.getElementById('theme-toggle').textContent = mode === 'dark' ? 'ライト' : 'ダーク';
  const t = THEME[mode];
  FIG_IDS.forEach(function (id) {
    const el = document.getElementById(id);
    if (!el || !window.Plotly) return;
    Plotly.relayout(el, {
      'font.color': t.secondary,
      'title.font.color': t.text,
      'xaxis.gridcolor': t.grid,
      'yaxis.gridcolor': id === 'fig-sensitivity' ? 'rgba(0,0,0,0)' : t.grid,
      'xaxis.linecolor': t.axis,
      'yaxis.linecolor': t.axis,
      'xaxis.tickfont.color': t.muted,
      'yaxis.tickfont.color': id === 'fig-sensitivity' ? t.secondary : t.muted,
      'xaxis.title.font.color': t.secondary,
      'yaxis.title.font.color': t.secondary,
      'legend.font.color': t.secondary
    });
    const patch = {};
    if (id === 'fig-sensitivity') {
      Plotly.restyle(el, {'line.color': t.axis}, [...Array(el.data.length - 2).keys()]);
      Plotly.restyle(el, {'marker.color': t.accent, 'marker.line.color': t.ring}, [el.data.length - 2]);
      Plotly.restyle(el, {'marker.color': t.accent_alt, 'marker.line.color': t.ring}, [el.data.length - 1]);
    } else {
      patch['marker.colorscale'] = [t.ramp];
      patch['marker.line.color'] = t.ring;
      patch['textfont.color'] = t.secondary;
      Plotly.restyle(el, patch);
      Plotly.relayout(el, {
        'shapes[0].fillcolor': t.band,
        'shapes[1].line.color': t.axis,
        'shapes[2].line.color': t.axis
      });
      const ann = {};
      el.layout.annotations.forEach(function (_, i) { ann['annotations[' + i + '].font.color'] = t.muted; });
      Plotly.relayout(el, ann);
    }
  });
}

document.getElementById('theme-toggle').addEventListener('click', function () {
  const now = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  applyTheme(now);
});

if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
  applyTheme('dark');
} else {
  applyTheme('light');
}
"""


def build_report(
    out_path: str | Path,
    cfg: Config | None = None,
    financials: pd.DataFrame | None = None,
    ref=None,
) -> Path:
    """Render the full HTML report and return the path written.

    ``ref`` lets a caller substitute the universe (e.g. the full J-Quants
    listed set) without touching the module-level reference cache.
    """
    cfg = cfg or Config()
    cfg.validate()
    ref = ref or load_reference()

    sectors = sector_frame(cfg, ref)
    sectors["__label__"] = sectors.index
    companies = company_frame(cfg, ref, financials)

    fig_sector = _scatter_figure(sectors, "__label__", "東証33業種の4象限マップ", cfg, 13, 12)
    fig_company = _scatter_figure(companies, "name", "個別銘柄の4象限マップ", cfg, 9, 0)
    fig_sens = _sensitivity_figure(ref, cfg)

    div_sector = pio.to_html(fig_sector, full_html=False, include_plotlyjs="inline",
                             div_id="fig-sector", config={"displayModeBar": False, "responsive": True})
    div_company = pio.to_html(fig_company, full_html=False, include_plotlyjs=False,
                              div_id="fig-company", config={"displayModeBar": False, "responsive": True})
    div_sens = pio.to_html(fig_sens, full_html=False, include_plotlyjs=False,
                           div_id="fig-sensitivity", config={"displayModeBar": False, "responsive": True})

    quad_cards = "".join(
        f'<div class="quad{" is-key" if q == Q_ESCAPE else ""}"><b>{html.escape(q)}</b>'
        f"<div>{html.escape(QUADRANT_MEANING[q])}</div></div>"
        for q in QUADRANT_ORDER
    )

    top_sectors = top_right(sectors).copy()
    top_sectors["__label__"] = top_sectors.index
    top_companies = top_right(companies).copy()

    pnl_cols: dict[str, str] = {}
    ranked_by = "脱出ポテンシャル順"
    if financials is not None and "op_uplift_pct" in companies.columns:
        # 生の人件費と営業利益も並べる。押上げ余地は営業利益で割った比率なので、
        # 単体営業利益が薄い会社（商社・持株会社・小型株）が分母の小ささだけで上位に来る。
        # 分子と分母を横に置けば、それが実額なのか比率の罠なのかを読者が判別できる。
        pnl_cols = {
            "labor_cost_ratio": "人件費率",
            "op_margin_uplift_pp": "営業利益率押上げ(pp)",
            "op_uplift_pct": "営業利益押上げ余地(%)",
            "labor_cost": "人件費(単体)",
            "operating_profit": "営業利益(単体)",
        }
        if "parent_employee_share" in companies.columns:
            pnl_cols["parent_employee_share"] = "単体/連結 従業員"
        # 企業スコアは業種スコア + 3値×3値の補正で決まるので、同じ業種の銘柄は
        # 脱出ポテンシャルが完全に並ぶ。財務があるのにその順で切ると、上位20件は
        # 最上位業種から実質ランダムに選ばれた20社になる。同順位を解くのは P/L 換算。
        # 並べ替えは分母が売上の pp のほうを使う（比率の暴れに順位を支配させない）。
        # 押上げ余地が定義できない行（営業利益0以下・人件費>売上）は母集団から外す。
        top_companies = top_companies[rankable(top_companies)]
        top_companies = top_companies.sort_values(
            "op_margin_uplift_pp", ascending=False, na_position="last"
        )
        ranked_by = "営業利益率の押上げ幅（pp）順"
    top_companies = top_companies.head(25)

    tables = "".join([
        _table(
            quadrant_summary(sectors),
            {"__index__": "象限", "n": "業種数", "mean_shortage": "平均 人手不足",
             "mean_ai": "平均 AI代替", "mean_escape": "平均 脱出ポテンシャル"},
            "業種の象限別サマリー",
        ),
        _table(
            top_sectors,
            {"__index__": "業種", "shortage_score": "人手不足深刻度", "ai_score": "AI代替可能性",
             "ai_substitutable_share_pct": "AI代替可能な労働(%)", "escape_potential": "脱出ポテンシャル",
             "top_ai_occupation": "主な代替対象職種"},
            "右上象限（AI解放）に入った業種 — 脱出ポテンシャル順",
        ),
        _table(
            top_companies,
            {"name": "銘柄", "sector33": "業種", "shortage_score": "人手不足深刻度",
             "ai_score": "AI代替可能性", "escape_potential": "脱出ポテンシャル", **pnl_cols},
            f"右上象限の個別銘柄 上位{len(top_companies)}（ユニバース{len(companies)}銘柄中） — {ranked_by}",
        ),
    ])

    x_cut, y_cut = thresholds(sectors["shortage_score"], sectors["ai_score"], cfg)
    vintages = "／".join(f"{k}: {v}" for k, v in ref.vintages.items())

    theme_json = _theme_json()
    js = (
        _JS_TEMPLATE
        .replace("__THEME__", theme_json)
        .replace("__FIG_IDS__", '["fig-sector", "fig-company", "fig-sensitivity"]')
    )

    doc = f"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>人手不足 × AI代替可能性 4象限マップ</title>
<style>{_CSS}</style></head>
<body>
<button id="theme-toggle" class="toggle">ダーク</button>
<main>
<h1>人手不足の深刻度 × AI代替可能性</h1>
<p class="lede">日本の上場企業を2軸で並べ、<b>右上＝人手不足が深刻で、かつその労働をAIで置き換えられる</b>
領域を特定する。右上に入る企業だけが、人手不足という供給制約を賃上げ以外の手段で外せる。</p>
<p class="meta">ユニバース {len(companies)} 銘柄 / 東証33業種 ・
象限境界: 人手不足 {x_cut:.0f} / AI代替 {y_cut:.0f}（{'中央値分割' if cfg.threshold_method == 'median' else '固定しきい値'}） ・
realization_rate={cfg.realization_rate} ・
データ時点 {html.escape(vintages)}</p>

<h2>4つの象限が意味すること</h2>
<div class="quads">{quad_cards}</div>

<h2>業種マップ</h2>
<div class="card">{div_sector}</div>
<div class="note"><p>この枠組みの核心は、<b>2軸が負の相関を持ちやすい</b>という点にある。
人手不足が最も深刻な労働（建設・介護・運転・保安）はAIが最も苦手とする身体労働であり、
AIが最も得意な労働（事務・審査・コーディング）は必ずしも人手不足ではない。
だから右上は本質的に狭く、そこに入ることが情報になる。</p></div>

<h2>個別銘柄マップ</h2>
<div class="card">{div_company}</div>
<p class="meta">位置は業種スコアを基準に、企業属性（労働集約度・知的労働比率）で
±{cfg.tilt_points:.0f}点の範囲で調整している。ラベルは右上象限の上位のみ表示、
残りはホバーで確認できる。</p>

<h2>感応度</h2>
<div class="card">{div_sens}</div>

<h2>数表</h2>
{tables}

<h2>読み方の注意</h2>
<ul>
<li>両軸とも <b>33業種内の相対順位</b>（0-100に正規化）であり、絶対水準ではない。
「右上に入る」＝「日本の上場企業の中で相対的に条件が良い」という意味。</li>
<li>P/L への換算（営業利益押上げ余地）だけは相対値ではなく、
<code>人件費 × AI代替可能な労働の割合 × 実現率</code> という水準ベースで計算している。</li>
<li>人手不足指標は公表統計に基づく業種配賦値、AI代替ポテンシャルは文献アンカー付きの
analyst 設定値。個々のセルの精度ではなく、業種間の順序に意味がある。詳細と限界は
<code>docs/METHODOLOGY.md</code>。</li>
</ul>
</main>
<script>{js}</script>
</body></html>
"""

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return out


def _theme_json() -> str:
    import json

    payload = {
        mode: {
            "text": t["text"], "secondary": t["secondary"], "muted": t["muted"],
            "grid": t["grid"], "axis": t["axis"], "band": t["band"], "ramp": t["ramp"],
            "accent": t["accent"], "accent_alt": t["accent_alt"], "ring": t["ring"],
        }
        for mode, t in THEME.items()
    }
    return json.dumps(payload, ensure_ascii=False)
