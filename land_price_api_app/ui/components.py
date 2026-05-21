"""
ui/components.py
アプリ全体で再利用するUIコンポーネント関数。
"""
from __future__ import annotations

from typing import Optional

import streamlit as st


# --------------------------------------------------------------------------
# Hero Card (物件分析タブ上部の物件概要カード)
# --------------------------------------------------------------------------

def render_hero_card(
    title: str,
    address: str,
    price_label: str,
    yield_label: str,
    age_label: str,
    structure_label: str,
    area_label: str,
    source_url: Optional[str] = None,
) -> None:
    link = f'<a href="{source_url}" target="_blank" style="color:#7fc3ea;font-size:0.8rem;">物件ページ ↗</a>' if source_url else ""
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #0f2236 0%, #162d4a 100%);
            border: 1px solid #2a4a6e;
            border-radius: 14px;
            padding: 18px 22px;
            margin-bottom: 16px;
        ">
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;">
                <div style="flex:1;min-width:200px;">
                    <div style="color:#7bafd4;font-size:0.75rem;margin-bottom:2px;">{address}</div>
                    <div style="color:#e8f4ff;font-size:1.25rem;font-weight:700;line-height:1.3;">{title}</div>
                </div>
                <div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center;">
                    <div style="text-align:right;">
                        <div style="color:#a8c8e0;font-size:0.72rem;">売出価格</div>
                        <div style="color:#4fc3f7;font-size:1.4rem;font-weight:800;">{price_label}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="color:#a8c8e0;font-size:0.72rem;">表面利回り</div>
                        <div style="color:#81c784;font-size:1.4rem;font-weight:800;">{yield_label}</div>
                    </div>
                    <div style="display:flex;flex-direction:column;gap:4px;text-align:right;">
                        <span style="color:#d0e4f0;font-size:0.82rem;">築 {age_label} &nbsp;|&nbsp; {structure_label}</span>
                        <span style="color:#d0e4f0;font-size:0.82rem;">延床 {area_label}</span>
                        {link}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------
# Population Card (人口トレンド表示カード)
# --------------------------------------------------------------------------

def render_population_card(pop: dict) -> None:
    """analytics.compute_population_trend() の返却dictを受け取って表示。"""
    if not pop:
        st.caption("人口データなし（`python sync_population.py` でデータを取得してください）")
        return

    year = pop.get("latest_year", "")
    total = pop.get("total_population")
    hh = pop.get("households")
    pop_chg = pop.get("pop_5yr_change_pct")
    hh_chg = pop.get("households_5yr_change_pct")
    span = pop.get("span_years", 0)

    def _fmt_int(v) -> str:
        return f"{int(v):,}" if v is not None else "—"

    def _fmt_pct(v) -> str:
        if v is None:
            return "—"
        sign = "+" if v > 0 else ""
        return f"{sign}{v:.1f}%"

    def _chg_color(v) -> str:
        if v is None:
            return "#a8c8e0"
        return "#81c784" if v >= 0 else "#ef9a9a"

    span_label = f"（{span}年間変化）" if span else ""

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #0d1f35 0%, #142540 100%);
            border: 1px solid #1e3a5a;
            border-radius: 10px;
            padding: 12px 14px;
        ">
            <div style="color:#95b8cf;font-size:0.75rem;margin-bottom:8px;">🏙 人口・世帯（{year}年）{span_label}</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                <div>
                    <div style="color:#a8c8e0;font-size:0.7rem;">総人口</div>
                    <div style="color:#e8f4ff;font-size:1rem;font-weight:700;">{_fmt_int(total)}</div>
                    <div style="color:{_chg_color(pop_chg)};font-size:0.78rem;">{_fmt_pct(pop_chg)}</div>
                </div>
                <div>
                    <div style="color:#a8c8e0;font-size:0.7rem;">世帯数</div>
                    <div style="color:#e8f4ff;font-size:1rem;font-weight:700;">{_fmt_int(hh)}</div>
                    <div style="color:{_chg_color(hh_chg)};font-size:0.78rem;">{_fmt_pct(hh_chg)}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


