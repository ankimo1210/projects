"""
ui/table.py
全タブ共通のリッチ HTML テーブルレンダラー。

使い方:
    from ui.table import render_html_table, gap_bar, price_man, truncate, ...

    render_html_table(df, [
        {"key": "city_name",      "label": "市区町村", "width": 120},
        {"key": "price_yen_per_sqm", "label": "価格(万円/m²)", "width": 90,
         "align": "right", "render": price_man},
        {"key": "yoy_change_pct", "label": "前年比",  "width": 130, "render": gap_bar},
    ])
"""

from __future__ import annotations

import html as _html
from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# 内部ユーティリティ
# ---------------------------------------------------------------------------


def _safe(v: Any, fallback: str = "—") -> str:
    """NaN / None / 空文字を fallback に変換して str を返す。"""
    if v is None:
        return fallback
    if isinstance(v, float) and pd.isna(v):
        return fallback
    try:
        import numpy as np

        if isinstance(v, np.floating) and np.isnan(float(v)):
            return fallback
    except Exception:
        pass
    s = str(v).strip()
    return s if s and s not in ("nan", "None", "NaT", "nat") else fallback


# ---------------------------------------------------------------------------
# セルレンダラー  (callable(value) -> html_str)
# ---------------------------------------------------------------------------


def plain(v: Any) -> str:
    """デフォルト: テキスト表示。"""
    return f'<span style="color:#d8ecf8">{_html.escape(_safe(v))}</span>'


def muted(v: Any) -> str:
    """薄い色のテキスト（住所・地区名など補助情報）。"""
    return f'<span style="color:#a8c8e0;font-size:0.82rem">{_html.escape(_safe(v))}</span>'


def truncate(v: Any, max_width: int = 180) -> str:
    """長いテキストを省略。max_width は px。"""
    s = _safe(v)
    escaped = _html.escape(s)
    return (
        f'<span style="color:#d8ecf8;display:block;overflow:hidden;'
        f'text-overflow:ellipsis;white-space:nowrap;max-width:{max_width}px" '
        f'title="{escaped}">{escaped}</span>'
    )


def truncate_muted(v: Any, max_width: int = 160) -> str:
    """薄い色で省略テキスト（住所など）。"""
    s = _safe(v)
    escaped = _html.escape(s)
    return (
        f'<span style="color:#a8c8e0;font-size:0.82rem;display:block;overflow:hidden;'
        f'text-overflow:ellipsis;white-space:nowrap;max-width:{max_width}px" '
        f'title="{escaped}">{escaped}</span>'
    )


def price_man(v: Any) -> str:
    """万円単価: 1桁小数、右揃え用 (align="right" と組み合わせる)。"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '<span style="color:#4a6580">—</span>'
    try:
        return (
            f'<span style="color:#e8f4ff;font-weight:600;'
            f'font-variant-numeric:tabular-nums">{float(v):.1f}</span>'
        )
    except Exception:
        return '<span style="color:#4a6580">—</span>'


def count_num(v: Any) -> str:
    """カンマ区切り整数（地点数など）。"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '<span style="color:#4a6580">—</span>'
    try:
        return f'<span style="color:#b8d0e8;font-variant-numeric:tabular-nums">{int(v):,}</span>'
    except Exception:
        return '<span style="color:#4a6580">—</span>'


def year_num(v: Any) -> str:
    """年度数値。"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '<span style="color:#4a6580">—</span>'
    try:
        return f'<span style="color:#b8d0e8;font-variant-numeric:tabular-nums">{int(v)}</span>'
    except Exception:
        return '<span style="color:#4a6580">—</span>'


def rank_num(v: Any) -> str:
    """順位（1〜3位はゴールド）。"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '<span style="color:#4a6580">—</span>'
    try:
        r = int(v)
        color = "#ffd700" if r <= 3 else "#b8d0e8"
        return f'<span style="color:{color};font-weight:600;font-variant-numeric:tabular-nums">{r}</span>'
    except Exception:
        return '<span style="color:#4a6580">—</span>'


# 住宅地以外の用途区分バッジ用カラー定義
_USE_CATEGORY_STYLES: dict[str, tuple[str, str]] = {
    # bg_color, text_color
    "商業地": ("#7c3a00", "#ffb74d"),
    "工業地": ("#2d1b4e", "#ce93d8"),
    "林地": ("#1b3a1b", "#81c784"),
    "農地": ("#2a3a1b", "#aed581"),
    "準工業地": ("#1a2a4e", "#90caf9"),
    "その他": ("#2a2a2a", "#b0bec5"),
}
_RESIDENTIAL_KEYWORDS = ("住宅地",)


def use_category_badge(v: Any) -> str:
    """用途区分: 住宅地はmuted、それ以外は色付きバッジ。"""
    s = _safe(v)
    if s == "—":
        return '<span style="color:#4a6580">—</span>'
    # 住宅地系は通常表示
    if any(kw in s for kw in _RESIDENTIAL_KEYWORDS):
        return f'<span style="color:#a8c8e0;font-size:0.82rem">{_html.escape(s)}</span>'
    # 非住宅地はバッジ
    bg, fg = _USE_CATEGORY_STYLES.get(s, ("#2a2a2a", "#b0bec5"))
    return (
        f'<span style="background:{bg};color:{fg};border-radius:4px;'
        f'padding:1px 6px;font-size:0.75rem;font-weight:600;white-space:nowrap">'
        f"{_html.escape(s)}</span>"
    )


def gap_bar(v: Any, max_abs: float = 500) -> str:
    """前年比 / 乖離率: ミニバー + 正=緑 / 負=赤 のカラー数値。"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '<span style="color:#4a6580">—</span>'
    try:
        val = float(v)
    except Exception:
        return '<span style="color:#4a6580">—</span>'
    w = min(abs(val), max_abs) / max_abs * 54
    bar_color = "#66bb6a" if val >= 0 else "#ef5350"
    text_color = "#81c784" if val >= 0 else "#ef9a9a"
    sign = "+" if val >= 0 else ""
    return (
        f'<div style="display:flex;align-items:center;gap:5px">'
        f'<div style="width:54px;height:5px;background:#0a1c30;border-radius:3px;overflow:hidden;flex-shrink:0">'
        f'<div style="width:{w:.0f}px;height:100%;border-radius:3px;background:{bar_color}"></div></div>'
        f'<span style="color:{text_color};font-variant-numeric:tabular-nums;'
        f'min-width:52px;text-align:right;font-size:0.8rem">{sign}{val:.1f}%</span></div>'
    )


def signed_pct_str(v: Any) -> str:
    """既にフォーマット済みの符号付き % 文字列を色分けする。例: '+2.3%' → 緑。"""
    s = _safe(v)
    if s == "—":
        return '<span style="color:#4a6580">—</span>'
    color = "#81c784" if s.startswith("+") else ("#ef9a9a" if s.startswith("-") else "#b8d0e8")
    return f'<span style="color:{color};font-variant-numeric:tabular-nums">{s}</span>'


def num_str(v: Any) -> str:
    """右揃え用の数値文字列（既にフォーマット済み）。"""
    s = _safe(v)
    if s == "—":
        return '<span style="color:#4a6580">—</span>'
    return (
        f'<span style="color:#e8f4ff;font-weight:600;font-variant-numeric:tabular-nums">{s}</span>'
    )


def dist_str(v: Any) -> str:
    """距離文字列（muted + 右揃え用）。"""
    s = _safe(v)
    if s == "—":
        return '<span style="color:#4a6580">—</span>'
    return f'<span style="color:#b8d0e8;font-variant-numeric:tabular-nums">{s}</span>'


def gap_bar_small(v: Any) -> str:
    """前年比: max_abs=20 の小さいバー（都市トレンド等）。"""
    return gap_bar(v, max_abs=20)


def area_num(v: Any) -> str:
    """面積 m²: カンマ区切り整数。"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '<span style="color:#4a6580">—</span>'
    try:
        return (
            f'<span style="color:#b8d0e8;font-variant-numeric:tabular-nums">{float(v):,.0f}</span>'
        )
    except Exception:
        return '<span style="color:#4a6580">—</span>'


def yen_total(v: Any) -> str:
    """取引総額（円 → 万円 表示）。"""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return '<span style="color:#4a6580">—</span>'
    try:
        man = float(v) / 1e4
        return f'<span style="color:#e8f4ff;font-variant-numeric:tabular-nums">{man:,.0f}</span>'
    except Exception:
        return '<span style="color:#4a6580">—</span>'


# ---------------------------------------------------------------------------
# メインテーブルレンダラー
# ---------------------------------------------------------------------------


def render_html_table(
    df: pd.DataFrame,
    col_specs: list[dict],
    *,
    caption: str | None = None,
    min_width: int = 700,
    max_height: int | None = None,
    sortable: bool = False,
    row_style_fn: Callable[[pd.Series], str] | None = None,
) -> None:
    """
    デザインシステム準拠のリッチ HTML テーブルを st.markdown で描画する。

    col_specs の各要素:
        key      : str                — df の列名
        label    : str                — 表示ヘッダー
        width    : int | None         — px 幅（省略可）
        align    : 'left'|'right'     — 配置（省略時 'left'）
        render   : callable(v)->str   — セルレンダラー（省略時 plain）
        sortable : bool               — 列ソート有効（sortable=True 時のみ有効）
        sort_key : str | None         — ソートに使う生の列名（省略時は key と同じ）

    sortable=True の場合、ヘッダークリックで昇順/降順ソートができる。
    sort_key を指定すると、表示用 render とは別の数値列でソートできる。
    """
    if df.empty:
        st.info("データがありません。")
        return

    import uuid

    table_id = f"tbl_{uuid.uuid4().hex[:8]}"

    th_base = (
        "padding:9px 10px;color:#95b8cf;font-size:0.72rem;font-weight:600;"
        "white-space:nowrap;border-bottom:2px solid #243d5e;background:#132035"
    )

    active_specs = [s for s in col_specs if s["key"] in df.columns]

    # raw ソートキー列を付与（ソート用の数値を hidden data-* に埋め込む）
    df = df.copy()
    for spec in active_specs:
        sk = spec.get("sort_key")
        if sk and sk in df.columns and sk != spec["key"]:
            pass  # 既存列なのでそのまま使う

    # ヘッダー
    ths = ""
    for col_idx, spec in enumerate(active_specs):
        label = spec.get("label", spec["key"])
        w = spec.get("width")
        align = spec.get("align", "left")
        w_style = f"width:{w}px;min-width:{w}px;" if w else ""
        col_sortable = sortable and spec.get("sortable", sortable)
        sort_style = "cursor:pointer;user-select:none;" if col_sortable else ""
        onclick = f'onclick="sortTable_{table_id}(this, {col_idx})"' if col_sortable else ""
        sort_icon = (
            ' <span class="sort-icon" style="opacity:0.4;font-size:0.65rem">⇅</span>'
            if col_sortable
            else ""
        )
        ths += (
            f'<th {onclick} style="{th_base};{w_style}text-align:{align};{sort_style}">'
            f"{_html.escape(label)}{sort_icon}</th>"
        )

    # データ行
    rows = ""
    for i, (_, row) in enumerate(df.iterrows()):
        zebra = "rgba(19,32,53,0.4)" if i % 2 == 0 else "transparent"
        extra_style = row_style_fn(row) if row_style_fn is not None else ""
        cells = ""
        for spec in active_specs:
            align = spec.get("align", "left")
            renderer: Callable = spec.get("render", plain)
            cell_html = renderer(row[spec["key"]])
            # ソート用の raw 値を data-sort 属性に埋め込む
            sk = spec.get("sort_key", spec["key"])
            raw_val = row.get(sk, row[spec["key"]])
            try:
                sort_val = float(raw_val) if raw_val is not None and raw_val == raw_val else 0
            except (TypeError, ValueError):
                sort_val = str(raw_val) if raw_val is not None else ""
            cells += (
                f'<td data-sort="{sort_val}" '
                f'style="padding:8px 10px;text-align:{align};vertical-align:middle">'
                f"{cell_html}</td>"
            )
        rows += (
            f'<tr style="background:{zebra};border-bottom:1px solid rgba(36,61,94,0.4);'
            f'transition:background 0.1s;{extra_style}" '
            f"onmouseover=\"this.style.background='rgba(26,46,71,0.6)'\" "
            f"onmouseout=\"this.style.background='{zebra}'\">{cells}</tr>"
        )

    caption_html = (
        f'<p style="color:#4a6580;font-size:0.72rem;margin-top:6px">{_html.escape(caption)}</p>'
        if caption
        else ""
    )
    scroll_y_style = f"max-height:{max_height}px;overflow-y:auto;" if max_height else ""

    sort_js = ""
    if sortable:
        sort_js = f"""
<script>
(function() {{
  var _sortState_{table_id} = {{}};
  window.sortTable_{table_id} = function(th, colIdx) {{
    var table = document.getElementById('{table_id}');
    var tbody = table.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr'));
    var asc = !_sortState_{table_id}[colIdx];
    _sortState_{table_id} = {{}};
    _sortState_{table_id}[colIdx] = asc;
    rows.sort(function(a, b) {{
      var aVal = a.querySelectorAll('td')[colIdx].getAttribute('data-sort');
      var bVal = b.querySelectorAll('td')[colIdx].getAttribute('data-sort');
      var aNum = parseFloat(aVal), bNum = parseFloat(bVal);
      if (!isNaN(aNum) && !isNaN(bNum)) return asc ? aNum - bNum : bNum - aNum;
      return asc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    }});
    rows.forEach(function(r, i) {{
      r.style.background = i % 2 === 0 ? 'rgba(19,32,53,0.4)' : 'transparent';
      tbody.appendChild(r);
    }});
    table.querySelectorAll('thead th .sort-icon').forEach(function(el) {{ el.style.opacity = '0.4'; el.textContent = '⇅'; }});
    th.querySelector('.sort-icon').style.opacity = '1';
    th.querySelector('.sort-icon').textContent = asc ? '↑' : '↓';
  }};
}})();
</script>"""

    st.markdown(
        f"{sort_js}"
        f'<div style="border-radius:10px;overflow:hidden;border:1px solid #243d5e">'
        f'<div style="overflow-x:auto;{scroll_y_style}">'
        f'<table id="{table_id}" style="width:100%;border-collapse:collapse;background:#0a1c30;min-width:{min_width}px">'
        f"<thead><tr>{ths}</tr></thead>"
        f"<tbody>{rows}</tbody>"
        f"</table></div></div>{caption_html}",
        unsafe_allow_html=True,
    )
