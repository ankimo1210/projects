"""
ui/property_investment.py
投資メトリクス・IRR/CF シミュレーション・感度分析。
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from config import get_logger
from geocoder import GeocodingError, geocode_address
from property_scraper import PropertyData
from property_state import PropertyAnalysisState

from ui.property_summary import _render_summary_panel
from ui.table import muted, num_str, plain, render_html_table

logger = get_logger(__name__)

# Investment simulation engine was prototyped under notebooks/real_estate_app/
# in the old workspace layout. That directory was archived during workspace
# consolidation and is now at _archive/notebooks/real_estate_app/. Probe both
# locations so an archived copy still works without code changes.
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
_SIM_CANDIDATES = [
    _WORKSPACE_ROOT / "notebooks" / "real_estate_app",
    _WORKSPACE_ROOT / "_archive" / "notebooks" / "real_estate_app",
]
for _candidate in _SIM_CANDIDATES:
    if _candidate.exists() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

try:
    from formatters import format_money, format_multiple, format_percent
    from sim_engine import enrich_params, run_full_analysis

    _SIM_AVAILABLE = True
except ImportError as _e:
    logger.warning("sim_engine インポート失敗: %s", _e)
    run_full_analysis = None  # type: ignore[assignment]
    _SIM_AVAILABLE = False


_SIM_DEFAULTS: dict = {
    "ltv": 0.70,
    "interest_rate": 0.020,
    "loan_term_years": 30,
    "amortization_type": "equal_payment",
    "io_years": 0,
    "acquisition_cost_rate": 0.07,
    "initial_capex": 0,
    "closing_cost_on_sale_rate": 0.035,
    "vacancy_rate": 0.05,
    "rent_growth_rate": -0.005,
    "opex_growth_rate": 0.01,
    "property_tax_growth_rate": 0.005,
    "repair_growth_rate": 0.02,
    "other_income": 0,
    "other_income_growth_rate": 0.0,
    "capex_schedule": {},
    "capex_treatment_mode": "expense_all",
    "exit_cap_rate": 0.055,
    "exit_price_method": "cap_rate",
    "hold_period_years": 10,
    "inflation_rate": 0.01,
    "land_real_appreciation_spread": 0.0,
    "building_real_appreciation_spread": -0.01,
    "ownership_type": "individual",
    "income_tax_rate_national": 0.20,
    "resident_tax_rate": 0.05,
    "reconstruction_special_tax_rate": 0.021,
    "corporate_effective_tax_rate": 0.30,
    "use_progressive_tax": False,
    "optional_business_tax_rate": 0.0,
    "enable_refinance": False,
    "use_deemed_acquisition_cost_fallback": False,
    "deemed_acquisition_cost_rate": 0.05,
    "capex_expense_schedule": {},
    "capex_capital_schedule": {},
    "capital_improvement_depr_life_years": 15,
    "selling_expense_schedule_mode": "rate",
    "selling_expense_items": {},
    "prepayment_schedule": {},
    "building_usage": "residential",
    "steel_thickness_mm": 3.2,
}

_DEFAULT_LAND_RATIO: dict[str, float] = {
    "土地": 1.0,
    "戸建て": 0.50,
    "アパート": 0.35,
    "マンション": 0.25,
}


def _compute_irr(cashflows: list) -> float | None:
    """二分法によるシンプルなIRR計算（scipy不要）。"""

    def _npv(r: float) -> float:
        return sum(cf / (1 + r) ** t for t, cf in enumerate(cashflows))

    try:
        lo, hi = -0.99, 20.0
        if _npv(lo) * _npv(hi) >= 0:
            return None
        for _ in range(100):
            mid = (lo + hi) / 2
            if _npv(mid) * _npv(lo) < 0:
                hi = mid
            else:
                lo = mid
            if abs(hi - lo) < 1e-8:
                break
        return (lo + hi) / 2
    except Exception:
        return None


def _simple_equity_cashflows(
    price: float,
    annual_rent: float,
    hold_years: int,
    ltv: float,
    interest_rate: float,
    exit_cap: float,
    vacancy: float = 0.05,
    opex_rate: float = 0.25,
    acq_cost_rate: float = 0.07,
) -> list:
    """シンプルなDCFキャッシュフロー配列を返す（Year 0 = 自己資本投下）。"""
    equity = price * (1 - ltv) * (1 + acq_cost_rate)
    loan = price * ltv
    n_months = 30 * 12
    r_mo = interest_rate / 12
    if r_mo > 0:
        monthly_pmt = loan * r_mo * (1 + r_mo) ** n_months / ((1 + r_mo) ** n_months - 1)
    else:
        monthly_pmt = loan / n_months
    debt_service = monthly_pmt * 12

    noi = annual_rent * (1 - vacancy) * (1 - opex_rate)
    cfs = [-equity]
    for _ in range(1, hold_years + 1):
        cfs.append(noi - debt_service)

    # 出口
    exit_price = noi / exit_cap if exit_cap > 0 else price
    n_paid = hold_years * 12
    if r_mo > 0:
        remaining = (
            loan * ((1 + r_mo) ** n_months - (1 + r_mo) ** n_paid) / ((1 + r_mo) ** n_months - 1)
        )
    else:
        remaining = loan * (1 - n_paid / n_months)
    cfs[-1] += exit_price * (1 - 0.035) - remaining
    return cfs


def _render_investment_metrics(prop: PropertyData) -> None:
    """実質利回り推定 + 損益分岐点空室率を表示する。"""
    price = prop.asking_price_yen
    annual_rent = (
        prop.gross_rent_annual_yen
        or (prop.gross_rent_monthly_yen * 12 if prop.gross_rent_monthly_yen else None)
        or (int(price * (prop.gross_yield_pct / 100)) if prop.gross_yield_pct and price else None)
    )
    if not price or not annual_rent:
        return

    st.markdown("---")
    st.markdown("#### 💰 実質利回り & 損益分岐点")

    # ── 実質利回り推定 ─────────────────────────────────────────────
    pm_rate = 0.05  # PM手数料
    repair_rate = 0.015  # 修繕積立
    tax_rate = 0.007  # 固定資産税（取得価格の0.7%）
    insurance_rate = 0.0005  # 保険
    misc_rate = 0.005  # 雑費
    opex_rent = annual_rent * (pm_rate + repair_rate + misc_rate)
    opex_price = price * (tax_rate + insurance_rate)
    opex_total = opex_rent + opex_price
    net_noi = annual_rent - opex_total
    net_yield = net_noi / price * 100
    gross_yield = prop.gross_yield_pct or (annual_rent / price * 100)
    spread = gross_yield - net_yield

    _render_summary_panel(
        "利回り",
        [
            ("表面利回り", f"{gross_yield:.2f}%", "年間賃料 ÷ 物件価格"),
            (
                "推定実質利回り（NOI）",
                f"{net_yield:.2f}%",
                f"Opex控除で -{spread:.2f}% / PM5%・修繕1.5%・税0.7%ほか",
            ),
            (
                "推定年間Opex",
                f"{opex_total / 1e4:,.0f} 万円",
                f"賃料連動 {opex_rent / 1e4:,.0f}万円 / 価格連動 {opex_price / 1e4:,.0f}万円",
            ),
        ],
        columns=3,
    )

    # ── 損益分岐点空室率 ───────────────────────────────────────────
    st.markdown("**📉 損益分岐点空室率**")
    # ① 無借金（NOIベース）
    be_noloan = (1 - opex_total / annual_rent) * 100 if annual_rent > 0 else None

    # ② 借入あり（LTV 70%, 金利 2.0%, 30年）
    def _be_with_loan(ltv: float, rate: float) -> float | None:
        loan = price * ltv
        r_mo = rate / 12
        n = 30 * 12
        if r_mo > 0:
            ds = loan * r_mo * (1 + r_mo) ** n / ((1 + r_mo) ** n - 1) * 12
        else:
            ds = loan / 30
        be = (1 - (ds + opex_total) / annual_rent) * 100
        return be if be >= 0 else 0.0

    be_70 = _be_with_loan(0.70, 0.020)
    be_80 = _be_with_loan(0.80, 0.025)
    _render_summary_panel(
        "損益分岐点",
        [
            (
                "Opex損益分岐点",
                f"{be_noloan:.1f}%" if be_noloan is not None else "—",
                "無借金ベースでNOIがOpexを下回る空室率",
            ),
            (
                "借入損益分岐（LTV70% / 2%）",
                f"{be_70:.1f}%" if be_70 is not None else "—",
                "30年返済時の税前CF損益分岐点空室率",
            ),
            (
                "借入損益分岐（LTV80% / 2.5%）",
                f"{be_80:.1f}%" if be_80 is not None else "—",
                "30年返済時の税前CF損益分岐点空室率",
            ),
        ],
        columns=3,
    )


def _render_sensitivity_heatmap(prop: PropertyData, sim_params: dict | None = None) -> None:
    """金利 × LTV 感度ヒートマップ（自己資本IRR）を表示する。"""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return

    price = prop.asking_price_yen
    annual_rent = (
        prop.gross_rent_annual_yen
        or (prop.gross_rent_monthly_yen * 12 if prop.gross_rent_monthly_yen else None)
        or (int(price * prop.gross_yield_pct / 100) if prop.gross_yield_pct and price else None)
    )
    if not price or not annual_rent:
        return

    exit_cap = (sim_params or {}).get("exit_cap_rate", 0.055)
    hold = int((sim_params or {}).get("hold_period_years", 10))
    vacancy = float((sim_params or {}).get("vacancy_rate", 0.05))

    ltv_vals = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
    rate_vals = [0.005, 0.010, 0.015, 0.020, 0.025, 0.030, 0.035, 0.040]

    z = []
    for rate in rate_vals:
        row = []
        for ltv in ltv_vals:
            cfs = _simple_equity_cashflows(
                price, annual_rent, hold, ltv, rate, exit_cap, vacancy=vacancy
            )
            irr = _compute_irr(cfs)
            row.append(round(irr * 100, 2) if irr is not None else None)
        z.append(row)

    x_labels = [f"{int(v * 100)}%" for v in ltv_vals]
    y_labels = [f"{v * 100:.1f}%" for v in rate_vals]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x_labels,
            y=y_labels,
            colorscale="RdYlGn",
            zmid=0,
            text=[[f"{v:.1f}%" if v is not None else "N/A" for v in row] for row in z],
            texttemplate="%{text}",
            textfont={"size": 10},
            colorbar={"title": "IRR (%)"},
        )
    )
    fig.update_layout(
        title=f"自己資本IRR（保有{hold}年・出口Cap {exit_cap * 100:.1f}%）",
        xaxis_title="LTV（借入比率）",
        yaxis_title="金利（年率）",
        height=400,
        margin={"l": 60, "r": 20, "t": 60, "b": 60},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("簡易DCF計算 (Opex 25%・取得費用率 7%・30年返済・元利均等)")


def _render_irr_by_period(prop: PropertyData, sim_params: dict | None = None) -> None:
    """保有年数別 自己資本IRR グラフを表示する。"""
    try:
        import plotly.graph_objects as go
    except ImportError:
        return

    price = prop.asking_price_yen
    annual_rent = (
        prop.gross_rent_annual_yen
        or (prop.gross_rent_monthly_yen * 12 if prop.gross_rent_monthly_yen else None)
        or (int(price * prop.gross_yield_pct / 100) if prop.gross_yield_pct and price else None)
    )
    if not price or not annual_rent:
        return

    p = sim_params or {}
    ltv = float(p.get("ltv", 0.70))
    rate = float(p.get("interest_rate", 0.020))
    exit_cap = float(p.get("exit_cap_rate", 0.055))
    vacancy = float(p.get("vacancy_rate", 0.05))

    hold_periods = list(range(5, 31))
    irr_series = []
    for h in hold_periods:
        cfs = _simple_equity_cashflows(price, annual_rent, h, ltv, rate, exit_cap, vacancy=vacancy)
        irr = _compute_irr(cfs)
        irr_series.append(round(irr * 100, 2) if irr is not None else None)

    valid = [(h, v) for h, v in zip(hold_periods, irr_series, strict=False) if v is not None]
    if not valid:
        return
    xs, ys = zip(*valid, strict=False)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=list(xs),
            y=list(ys),
            mode="lines+markers",
            line={"color": "#00c4b4", "width": 2},
            marker={"size": 6},
            hovertemplate="保有%{x}年: IRR %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(
        title=f"保有年数別 自己資本IRR（LTV{int(ltv * 100)}% / 金利{rate * 100:.1f}%）",
        xaxis_title="保有年数",
        yaxis_title="自己資本IRR (%)",
        height=350,
        margin={"l": 60, "r": 20, "t": 60, "b": 60},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("簡易DCF計算 (Opex 25%・取得費用率 7%・30年返済・元利均等)")


def _render_param_editor(base_params: dict) -> dict:
    """調整可能な8パラメータを表示し、上書き用 dict を返す。"""
    overrides: dict = {}
    col1, col2 = st.columns(2)
    with col1:
        overrides["ltv"] = st.slider(
            "借入比率 (LTV)", 0.5, 0.9, value=float(base_params.get("ltv", 0.70)), step=0.05
        )
        overrides["interest_rate"] = (
            st.number_input(
                "金利 (%/年)",
                0.5,
                5.0,
                value=float(base_params.get("interest_rate", 0.02)) * 100,
                step=0.1,
            )
            / 100
        )
        overrides["hold_period_years"] = st.slider(
            "保有年数", 5, 30, value=int(base_params.get("hold_period_years", 10)), step=1
        )
        overrides["exit_cap_rate"] = (
            st.number_input(
                "出口キャップレート (%)",
                3.0,
                10.0,
                value=float(base_params.get("exit_cap_rate", 0.055)) * 100,
                step=0.1,
            )
            / 100
        )
    with col2:
        overrides["vacancy_rate"] = st.slider(
            "空室率", 0.0, 0.30, value=float(base_params.get("vacancy_rate", 0.05)), step=0.01
        )
        land_ratio_default = (
            float(base_params.get("land_value", 0)) / float(base_params.get("purchase_price", 1))
            if base_params.get("purchase_price")
            else 0.35
        )
        land_ratio = st.slider(
            "土地割合", 0.10, 0.80, value=round(land_ratio_default, 2), step=0.05
        )
        overrides["acquisition_cost_rate"] = (
            st.number_input(
                "取得費用率 (%)",
                3.0,
                12.0,
                value=float(base_params.get("acquisition_cost_rate", 0.07)) * 100,
                step=0.5,
            )
            / 100
        )
        overrides["rent_growth_rate"] = (
            st.number_input(
                "家賃上昇率 (%/年)",
                -3.0,
                3.0,
                value=float(base_params.get("rent_growth_rate", -0.005)) * 100,
                step=0.1,
            )
            / 100
        )

    price = base_params.get("purchase_price", 0)
    overrides["land_value"] = price * land_ratio
    overrides["building_value"] = price * (1 - land_ratio)
    return overrides


def _render_simulation(results: dict, show_heading: bool = True) -> None:
    if show_heading:
        st.markdown("---")
        st.markdown("#### 💹 投資シミュレーション")

    metrics = results.get("metrics", {})
    eq_irr = metrics.get("equity_irr")
    eq_mult = metrics.get("equity_multiple")
    cap = metrics.get("cap_rate")
    dscr_min = metrics.get("min_dscr")

    _render_summary_panel(
        None,
        [
            ("自己資本IRR", f"{eq_irr * 100:.1f} %" if eq_irr is not None else "—", None),
            ("投資倍率", f"{eq_mult:.2f} x" if eq_mult is not None else "—", None),
            ("キャップレート", f"{cap * 100:.1f} %" if cap is not None else "—", None),
            ("最低DSCR", f"{dscr_min:.2f}" if dscr_min is not None else "—", None),
        ],
        columns=4,
    )

    tab_cf, tab_summary = st.tabs(["キャッシュフロー表", "サマリー"])

    with tab_cf:
        annual_df: pd.DataFrame = results.get("annual_df", pd.DataFrame())
        if not annual_df.empty:
            show_cols = ["year", "noi", "debt_service", "btcf", "tax", "atcf"]
            show_cols = [c for c in show_cols if c in annual_df.columns]
            disp = annual_df[show_cols].copy()

            # 累計ATCFを追加
            if "atcf" in disp.columns:
                disp["cum_atcf"] = disp["atcf"].cumsum()
                show_cols.append("cum_atcf")

            col_labels = {
                "year": "年",
                "noi": "NOI",
                "debt_service": "元利返済",
                "btcf": "税前CF",
                "tax": "税金",
                "atcf": "税後CF",
                "cum_atcf": "累計税後CF",
            }
            money_cols = [c for c in show_cols if c != "year"]

            def _fmt_money(v):
                try:
                    return f"{int(v):,}"
                except Exception:
                    return str(v)

            for c in money_cols:
                if c in disp.columns:
                    disp[c] = disp[c].map(_fmt_money)

            disp.columns = [col_labels.get(c, c) for c in show_cols]
            render_html_table(
                disp,
                [
                    {
                        "key": col_labels.get(c, c),
                        "label": col_labels.get(c, c),
                        "align": "right" if c != "year" else "right",
                        "render": plain if c == "year" else num_str,
                    }
                    for c in show_cols
                ],
            )

    with tab_summary:
        summary = results.get("summary", {})
        if summary:
            items = [
                ("物件価格", summary.get("purchase_price")),
                ("自己資本", summary.get("equity_invested")),
                ("借入額", summary.get("loan_amount")),
                ("取得総額", summary.get("total_acquisition_cost")),
                ("売却価格（想定）", summary.get("sale_price_selected")),
                ("売却後手取り", summary.get("net_sale_proceeds")),
                ("総税負担", summary.get("total_tax_paid")),
            ]
            rows = []
            for label, val in items:
                if val is not None:
                    rows.append({"項目": label, "金額（円）": f"{int(val):,}"})
            if rows:
                render_html_table(
                    pd.DataFrame(rows),
                    [
                        {"key": "項目", "label": "項目", "width": 140, "render": muted},
                        {
                            "key": "金額（円）",
                            "label": "金額（円）",
                            "width": 120,
                            "align": "right",
                            "render": num_str,
                        },
                    ],
                )


# --------------------------------------------------------------------------
# フォールバック（手動入力フォーム）
# --------------------------------------------------------------------------


def _render_fallback_form() -> None:
    st.markdown("---")
    st.markdown("##### 📝 手動で物件情報を入力")
    with st.form("prop_manual_form"):
        col1, col2 = st.columns(2)
        with col1:
            price = st.number_input("物件価格（万円）", min_value=100, value=5000, step=100)
            rent = st.number_input("月額賃料（万円）", min_value=1.0, value=25.0, step=0.5)
            address = st.text_input("住所", placeholder="東京都〇〇区...")
        with col2:
            build_ym = st.text_input("築年月（YYYY-MM）", value="2000-01")
            _struct_opts = {
                "RC造": "rc",
                "木造": "wood",
                "鉄骨造": "steel",
                "SRC造": "src",
                "木骨モルタル": "wood_mortar",
            }
            structure = _struct_opts[st.selectbox("構造", list(_struct_opts.keys()))]
            property_type = st.selectbox(
                "種別", ["アパート", "マンション", "戸建て", "土地", "その他"]
            )

        submitted = st.form_submit_button("この情報で分析", type="primary")
        if submitted:
            from property_scraper import PropertyData

            prop = PropertyData(
                asking_price_yen=price * 10_000,
                gross_rent_monthly_yen=int(rent * 10_000),
                address=address or None,
                build_year_month=build_ym,
                structure=structure,
                property_type=property_type,
                platform="manual",
                extraction_confidence="partial",
            )
            geo: tuple[float, float] | None = None
            city_code: str | None = None
            if prop.address:
                try:
                    geo_result = geocode_address(prop.address)
                    geo = (geo_result.lat, geo_result.lon)
                    city_code = geo_result.city_code
                except GeocodingError:
                    logger.warning("手動入力住所のジオコーディングに失敗: %s", prop.address)
            state = PropertyAnalysisState(source_url="")
            state.set_property(prop, geo=geo, city_code=city_code)
            st.rerun()


# --------------------------------------------------------------------------
# シミュレーションパラメータ構築
# --------------------------------------------------------------------------


def _build_sim_params(
    prop: PropertyData,
    nearby_land_df: pd.DataFrame,
    overrides: dict,
) -> dict:
    price = prop.asking_price_yen or 0
    annual_rent = _derive_rent(prop)
    land_value = overrides.pop("land_value", None) or _derive_land_value(
        prop, nearby_land_df, price
    )
    building_value = overrides.pop("building_value", None) or (price - land_value)

    initial_opex = annual_rent * 0.07
    property_tax = price * 0.0014
    repair_cost = (prop.building_area_sqm * 1_000) if prop.building_area_sqm else (price * 0.005)

    params: dict = {
        **_SIM_DEFAULTS,
        "purchase_price": price,
        "land_value": land_value,
        "building_value": building_value,
        "transaction_date": date.today().isoformat(),
        "building_completion_ym": prop.build_year_month or "2000-01",
        "building_structure": prop.structure or "rc",
        "initial_gross_rent": annual_rent,
        "initial_operating_expenses": initial_opex,
        "property_tax": property_tax,
        "repair_cost": repair_cost,
    }
    params.update(overrides)
    return params


def _derive_rent(prop: PropertyData) -> int:
    if prop.gross_rent_monthly_yen:
        return prop.gross_rent_monthly_yen * 12
    if prop.gross_yield_pct and prop.asking_price_yen:
        return int(prop.asking_price_yen * prop.gross_yield_pct / 100)
    return int((prop.asking_price_yen or 0) * 0.06)


def _derive_land_value(
    prop: PropertyData,
    nearby_land_df: pd.DataFrame,
    price: int,
) -> float:
    if not nearby_land_df.empty and prop.land_area_sqm:
        land_ref, _, _ = _select_land_price_reference_points(nearby_land_df, prop)
        ref_df = land_ref if not land_ref.empty else nearby_land_df
        median_unit = ref_df["price_yen_per_sqm"].median()
        estimated = median_unit * prop.land_area_sqm
        return float(max(price * 0.10, min(estimated, price * 0.70)))
    ratio = _DEFAULT_LAND_RATIO.get(prop.property_type or "", 0.35)
    return price * ratio
