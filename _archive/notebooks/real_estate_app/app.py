"""
app.py — 不動産投資シミュレーター (Streamlit)

Local-only web application ported from real_estate_investment_sim_3.ipynb.
"""

import json
import pathlib
import numpy as np
import pandas as pd
import streamlit as st

from sim_engine import (
    run_full_analysis,
    run_scenario_analysis,
    run_ownership_comparison,
    build_ownership_comparison_summary,
    build_v3_extended_scenario_summary,
    enrich_params,
)
import charts
from formatters import (
    format_money, format_money_m, format_percent, format_multiple, format_year,
    col_money, col_percent, col_multiple, col_year,
    cashflow_column_config, nav_column_config,
    style_negatives_red,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="不動産投資シミュレーター",
    page_icon="🏢",
    layout="wide",
)

CONFIG_DIR = pathlib.Path(__file__).parent / "config"
DEFAULT_PARAMS_PATH = CONFIG_DIR / "default_params.json"
SAVED_DIR = CONFIG_DIR / "saved"
SAVED_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_default_params():
    with open(DEFAULT_PARAMS_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # Convert string keys to int keys for schedule dicts
    for key in ("capex_schedule", "capex_expense_schedule",
                "capex_capital_schedule", "prepayment_schedule"):
        if key in raw and isinstance(raw[key], dict):
            raw[key] = {int(k): v for k, v in raw[key].items()}
    return raw


def _schedule_to_df(schedule, col_name="Amount"):
    """Convert {year: amount} dict to a DataFrame for st.data_editor."""
    if not schedule:
        return pd.DataFrame({"Year": pd.Series(dtype=int), col_name: pd.Series(dtype=float)})
    rows = [{"Year": int(k), col_name: float(v)} for k, v in sorted(schedule.items())]
    return pd.DataFrame(rows)


def _df_to_schedule(df, col_name="Amount"):
    """Convert DataFrame back to {int_year: float_amount} dict."""
    if df is None or df.empty:
        return {}
    result = {}
    for _, row in df.iterrows():
        y = int(row["Year"])
        v = float(row[col_name])
        if v != 0:
            result[y] = v
    return result


def _schedule_col_config(col_name):
    """Column config for schedule data_editor tables."""
    return {
        "Year": col_year("Year"),
        col_name: col_money(col_name),
    }


# ---------------------------------------------------------------------------
# Sidebar input helpers
# ---------------------------------------------------------------------------

def _money_input(label, value, step, key=None):
    """Integer money input. Shows a formatted caption (e.g. 100,000,000 円) below."""
    kwargs = {"label": label, "value": int(value), "step": int(step), "format": "%d"}
    if key:
        kwargs["key"] = key
    v = st.sidebar.number_input(**kwargs)
    st.sidebar.caption(f"= {int(v):,} 円")
    return int(v)


def _pct_input(label, value_decimal, step_pct=0.1, fmt="%.2f", key=None, **extra):
    """Rate input shown as percent.
    
    Receives decimal (0.05), displays as percent (5.00), returns decimal (0.05).
    """
    display = round(float(value_decimal) * 100, 8)
    kwargs = {"label": label, "value": display, "step": float(step_pct), "format": fmt}
    if key:
        kwargs["key"] = key
    kwargs.update(extra)
    v_pct = st.sidebar.number_input(**kwargs)
    return float(v_pct) / 100


# ---------------------------------------------------------------------------
# Glossary helper
# ---------------------------------------------------------------------------

def _glossary_expander(tab_label, terms):
    """Render a collapsible glossary at the bottom of a tab."""
    st.divider()
    with st.expander(f"📖 用語解説・略称一覧 — {tab_label}"):
        for term, definition in terms:
            st.markdown(f"- **{term}**: {definition}")


# ---------------------------------------------------------------------------
# Sidebar: Parameter input
# ---------------------------------------------------------------------------

def _build_sidebar():
    """Build the sidebar and return a params dict."""
    st.sidebar.title("パラメータ設定")

    # --- Load / Save ---
    with st.sidebar.expander("💾 パラメータ保存・読込", expanded=False):
        # Load defaults
        if st.button("デフォルト値を読込", key="load_defaults"):
            st.session_state["params_raw"] = _load_default_params()
            st.rerun()

        # Save current
        save_name = st.text_input("保存名", value="my_case", key="save_name")
        if st.button("現在のパラメータを保存", key="save_params"):
            p = _collect_params_from_widgets()
            save_path = SAVED_DIR / f"{save_name}.json"
            # Convert int keys to str for JSON
            to_save = {}
            for k, v in p.items():
                if isinstance(v, dict):
                    to_save[k] = {str(kk): vv for kk, vv in v.items()}
                else:
                    to_save[k] = v
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(to_save, f, ensure_ascii=False, indent=2, default=str)
            st.success(f"保存しました: {save_path.name}")

        # Load saved
        saved_files = sorted(SAVED_DIR.glob("*.json"))
        if saved_files:
            chosen = st.selectbox("保存済みファイル", [f.stem for f in saved_files], key="load_choice")
            if st.button("読込", key="load_saved"):
                with open(SAVED_DIR / f"{chosen}.json", "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                for key in ("capex_schedule", "capex_expense_schedule",
                            "capex_capital_schedule", "prepayment_schedule"):
                    if key in loaded and isinstance(loaded[key], dict):
                        loaded[key] = {int(k): v for k, v in loaded[key].items()}
                st.session_state["params_raw"] = loaded
                st.rerun()

    # Initialize defaults
    if "params_raw" not in st.session_state:
        st.session_state["params_raw"] = _load_default_params()

    d = st.session_state["params_raw"]

    # --- 物件取得 ---
    st.sidebar.header("🏠 物件取得")
    purchase_price = _money_input("物件価格 (円)", d.get("purchase_price", 100_000_000), step=1_000_000)
    land_value = _money_input("土地価格 (円)", d.get("land_value", 35_000_000), step=1_000_000)
    building_value = _money_input("建物価格 (円)", d.get("building_value", 65_000_000), step=1_000_000)
    acquisition_cost_rate = _pct_input("取得諸費率 (%)", d.get("acquisition_cost_rate", 0.07), step_pct=1.0, fmt="%.2f")
    initial_capex = _money_input("初期CAPEX (円)", d.get("initial_capex", 2_000_000), step=100_000)
    hold_period_years = st.sidebar.number_input("保有年数", value=d.get("hold_period_years", 10), min_value=1, max_value=50, step=1)
    transaction_date = st.sidebar.text_input("取得日 (YYYY-MM-DD)", value=d.get("transaction_date", "2026-04-01"))
    building_completion_ym = st.sidebar.text_input("竣工年月 (YYYY-MM)", value=d.get("building_completion_ym", "2010-06"))
    building_structure = st.sidebar.selectbox("構造", ["rc", "src", "wood", "wood_mortar", "steel"],
                                              index=["rc", "src", "wood", "wood_mortar", "steel"].index(d.get("building_structure", "rc")))
    building_usage = st.sidebar.selectbox("用途", ["residential"], index=0)

    # --- 収入 ---
    st.sidebar.header("💰 収入")
    initial_gross_rent = _money_input("年間賃料収入 (円)", d.get("initial_gross_rent", 8_400_000), step=100_000)
    vacancy_rate = _pct_input("空室率 (%)", d.get("vacancy_rate", 0.05), step_pct=1.0, fmt="%.2f")
    rent_growth_rate = _pct_input("賃料成長率 (%)", d.get("rent_growth_rate", 0.005), step_pct=0.1, fmt="%.2f")
    other_income = _money_input("その他収入 (円)", d.get("other_income", 200_000), step=10_000)
    other_income_growth_rate = _pct_input("その他収入成長率 (%)", d.get("other_income_growth_rate", 0.0), step_pct=0.1, fmt="%.2f")

    # --- 費用 ---
    st.sidebar.header("📋 費用")
    initial_operating_expenses = _money_input("経費 (円)", d.get("initial_operating_expenses", 1_000_000), step=100_000)
    opex_growth_rate = _pct_input("経費成長率 (%)", d.get("opex_growth_rate", 0.01), step_pct=0.1, fmt="%.2f")
    property_tax = _money_input("固定資産税 (円)", d.get("property_tax", 900_000), step=100_000)
    property_tax_growth_rate = _pct_input("固定資産税成長率 (%)", d.get("property_tax_growth_rate", 0.005), step_pct=0.1, fmt="%.2f")
    repair_cost = _money_input("修繕費 (円)", d.get("repair_cost", 300_000), step=100_000)
    repair_growth_rate = _pct_input("修繕費成長率 (%)", d.get("repair_growth_rate", 0.02), step_pct=0.5, fmt="%.2f")

    # --- 借入 ---
    st.sidebar.header("🏦 借入")
    ltv = _pct_input("LTV (%)", d.get("ltv", 0.80), step_pct=5.0, fmt="%.1f")
    interest_rate = _pct_input("金利 (%)", d.get("interest_rate", 0.02), step_pct=0.1, fmt="%.2f")
    loan_term_years = st.sidebar.number_input("借入期間 (年)", value=d.get("loan_term_years", 30), min_value=1, max_value=50, step=1)
    amortization_type = st.sidebar.selectbox("返済方式", ["equal_payment", "interest_only_then_amortizing"],
                                              index=["equal_payment", "interest_only_then_amortizing"].index(d.get("amortization_type", "equal_payment")))
    io_years = st.sidebar.number_input("IO期間 (年)", value=d.get("io_years", 0), min_value=0, max_value=30, step=1)

    # --- インフレ・価格 ---
    st.sidebar.header("📈 インフレ・価格")
    inflation_rate = _pct_input("インフレ率 (%)", d.get("inflation_rate", 0.02), step_pct=0.1, fmt="%.2f")
    land_real_appreciation_spread = _pct_input("土地実質上昇スプレッド (%)", d.get("land_real_appreciation_spread", 0.005), step_pct=0.1, fmt="%.2f")
    building_real_appreciation_spread = _pct_input("建物実質上昇スプレッド (%)", d.get("building_real_appreciation_spread", -0.01), step_pct=0.1, fmt="%.2f")
    exit_price_method = st.sidebar.selectbox("出口価格算定", ["cap_rate", "component_growth"],
                                              index=["cap_rate", "component_growth"].index(d.get("exit_price_method", "cap_rate")))
    exit_cap_rate = _pct_input("出口Cap Rate (%)", d.get("exit_cap_rate", 0.05), step_pct=0.1, fmt="%.2f")
    closing_cost_on_sale_rate = _pct_input("売却諸費率 (%)", d.get("closing_cost_on_sale_rate", 0.035), step_pct=0.1, fmt="%.2f")

    # --- 税務 ---
    st.sidebar.header("🏛️ 税務")
    ownership_type = st.sidebar.selectbox("所有形態", ["individual", "corporate"],
                                           index=["individual", "corporate"].index(d.get("ownership_type", "individual")))
    income_tax_rate_national = _pct_input("所得税率 (国税, %)", d.get("income_tax_rate_national", 0.20), step_pct=1.0, fmt="%.2f")
    resident_tax_rate = _pct_input("住民税率 (%)", d.get("resident_tax_rate", 0.05), step_pct=1.0, fmt="%.2f")
    reconstruction_special_tax_rate = _pct_input("復興特別所得税率 (%)", d.get("reconstruction_special_tax_rate", 0.021), step_pct=0.1, fmt="%.3f")
    optional_business_tax_rate = _pct_input("事業税率 (任意, %)", d.get("optional_business_tax_rate", 0.0), step_pct=1.0, fmt="%.2f")
    corporate_effective_tax_rate = _pct_input("法人実効税率 (%)", d.get("corporate_effective_tax_rate", 0.30), step_pct=1.0, fmt="%.2f")
    use_progressive_tax = st.sidebar.checkbox("累進課税を使用", value=d.get("use_progressive_tax", True))
    use_deemed_acquisition_cost_fallback = st.sidebar.checkbox("みなし取得費フォールバック", value=d.get("use_deemed_acquisition_cost_fallback", False))
    deemed_acquisition_cost_rate = _pct_input("みなし取得費率 (%)", d.get("deemed_acquisition_cost_rate", 0.05), step_pct=1.0, fmt="%.2f")

    # --- CAPEX ---
    st.sidebar.header("🔧 CAPEX")
    capex_treatment_mode = st.sidebar.selectbox("CAPEX処理モード", ["expense_all", "capitalize_all", "mixed_schedule"],
                                                 index=["expense_all", "capitalize_all", "mixed_schedule"].index(d.get("capex_treatment_mode", "mixed_schedule")))
    capital_improvement_depr_life_years = st.sidebar.number_input("資本改良償却年数", value=d.get("capital_improvement_depr_life_years", 15), min_value=1, max_value=50, step=1)

    st.sidebar.subheader("CAPEX スケジュール")
    capex_df = st.sidebar.data_editor(
        _schedule_to_df(d.get("capex_schedule", {}), "Capex"),
        column_config=_schedule_col_config("Capex"),
        num_rows="dynamic", key="capex_schedule_editor", width="stretch")
    capex_schedule = _df_to_schedule(capex_df, "Capex")

    if capex_treatment_mode == "mixed_schedule":
        st.sidebar.subheader("費用処理スケジュール")
        capex_exp_df = st.sidebar.data_editor(
            _schedule_to_df(d.get("capex_expense_schedule", {}), "Expense"),
            column_config=_schedule_col_config("Expense"),
            num_rows="dynamic", key="capex_expense_editor", width="stretch")
        capex_expense_schedule = _df_to_schedule(capex_exp_df, "Expense")

        st.sidebar.subheader("資本計上スケジュール")
        capex_cap_df = st.sidebar.data_editor(
            _schedule_to_df(d.get("capex_capital_schedule", {}), "Capital"),
            column_config=_schedule_col_config("Capital"),
            num_rows="dynamic", key="capex_capital_editor", width="stretch")
        capex_capital_schedule = _df_to_schedule(capex_cap_df, "Capital")
    else:
        capex_expense_schedule = d.get("capex_expense_schedule", {})
        capex_capital_schedule = d.get("capex_capital_schedule", {})

    # --- 資本政策 ---
    st.sidebar.header("💼 資本政策")
    enable_refinance = st.sidebar.checkbox("リファイナンス有効", value=d.get("enable_refinance", False))
    refinance_year = st.sidebar.number_input("リファイナンス年", value=d.get("refinance_year", 5), min_value=1, max_value=50, step=1)
    refinance_ltv = _pct_input("リファイナンスLTV (%)", d.get("refinance_ltv", 0.70), step_pct=5.0, fmt="%.1f")
    refinance_interest_rate = _pct_input("リファイナンス金利 (%)", d.get("refinance_interest_rate", 0.02), step_pct=0.1, fmt="%.2f")
    refinance_term_years = st.sidebar.number_input("リファイナンス期間 (年)", value=d.get("refinance_term_years", 25), min_value=1, max_value=50, step=1)
    refinance_fee_rate = _pct_input("リファイナンス手数料率 (%)", d.get("refinance_fee_rate", 0.01), step_pct=0.1, fmt="%.2f")
    cash_out_to_equity = st.sidebar.checkbox("キャッシュアウト→自己資金", value=d.get("cash_out_to_equity", True))

    st.sidebar.subheader("繰上返済スケジュール")
    prepay_df = st.sidebar.data_editor(
        _schedule_to_df(d.get("prepayment_schedule", {}), "Prepay"),
        column_config=_schedule_col_config("Prepay"),
        num_rows="dynamic", key="prepay_editor", width="stretch")
    prepayment_schedule = _df_to_schedule(prepay_df, "Prepay")

    params = {
        "purchase_price": int(purchase_price),
        "land_value": int(land_value),
        "building_value": int(building_value),
        "acquisition_cost_rate": acquisition_cost_rate,
        "initial_capex": int(initial_capex),
        "hold_period_years": int(hold_period_years),
        "building_structure": building_structure,
        "building_usage": building_usage,
        "building_completion_ym": building_completion_ym,
        "steel_thickness_mm": None,
        "transaction_date": transaction_date,
        "initial_gross_rent": int(initial_gross_rent),
        "vacancy_rate": vacancy_rate,
        "rent_growth_rate": rent_growth_rate,
        "other_income": int(other_income),
        "other_income_growth_rate": other_income_growth_rate,
        "initial_operating_expenses": int(initial_operating_expenses),
        "opex_growth_rate": opex_growth_rate,
        "property_tax": int(property_tax),
        "property_tax_growth_rate": property_tax_growth_rate,
        "repair_cost": int(repair_cost),
        "repair_growth_rate": repair_growth_rate,
        "capex_schedule": capex_schedule,
        "ltv": ltv,
        "interest_rate": interest_rate,
        "loan_term_years": int(loan_term_years),
        "amortization_type": amortization_type,
        "io_years": int(io_years),
        "depreciation_method": "straight_line",
        "inflation_rate": inflation_rate,
        "land_real_appreciation_spread": land_real_appreciation_spread,
        "building_real_appreciation_spread": building_real_appreciation_spread,
        "exit_cap_rate": exit_cap_rate,
        "closing_cost_on_sale_rate": closing_cost_on_sale_rate,
        "exit_price_method": exit_price_method,
        "ownership_type": ownership_type,
        "income_tax_rate_national": income_tax_rate_national,
        "resident_tax_rate": resident_tax_rate,
        "reconstruction_special_tax_rate": reconstruction_special_tax_rate,
        "corporate_effective_tax_rate": corporate_effective_tax_rate,
        "use_progressive_tax": use_progressive_tax,
        "optional_business_tax_rate": optional_business_tax_rate,
        "capex_treatment_mode": capex_treatment_mode,
        "capex_expense_schedule": capex_expense_schedule,
        "capex_capital_schedule": capex_capital_schedule,
        "capital_improvement_depr_life_years": int(capital_improvement_depr_life_years),
        "capital_improvement_depr_method": "straight_line",
        "selling_expense_schedule_mode": "rate",
        "selling_expense_items": {},
        "use_deemed_acquisition_cost_fallback": use_deemed_acquisition_cost_fallback,
        "deemed_acquisition_cost_rate": deemed_acquisition_cost_rate,
        "enable_refinance": enable_refinance,
        "refinance_year": int(refinance_year),
        "refinance_ltv": refinance_ltv,
        "refinance_interest_rate": refinance_interest_rate,
        "refinance_term_years": int(refinance_term_years),
        "refinance_fee_rate": refinance_fee_rate,
        "cash_out_to_equity": cash_out_to_equity,
        "prepayment_schedule": prepayment_schedule,
    }
    return params


def _collect_params_from_widgets():
    """Collect current widget values. Re-uses sidebar logic conceptually."""
    # When called from save button, widgets are already rendered
    # and their values are in session_state. We reconstruct params from there.
    # However, the simplest approach is to just use the params that were built.
    if "current_params" in st.session_state:
        return st.session_state["current_params"]
    return _load_default_params()

# ---------------------------------------------------------------------------
# Main tabs
# ---------------------------------------------------------------------------

def _render_overview(results):
    metrics = results["metrics"]
    summary = results["summary"]
    params = results["params"]
    nav_df = results["nav_df"]
    dd_results = results["dd_results"]

    final_nav_at = nav_df["nav_after_tax"].iloc[-1]

    cols = st.columns(4)
    with cols[0]:
        st.metric("Cap Rate", format_percent(metrics["cap_rate"]))
        st.metric("Equity IRR", format_percent(metrics["equity_irr"]))
    with cols[1]:
        st.metric("Equity Multiple", format_multiple(metrics["equity_multiple"]))
        st.metric("Final NAV AT", format_money(final_nav_at))
    with cols[2]:
        be = metrics.get("break_even_year_cash")
        st.metric("Break-even Year (Cash)", f"Year {be}" if be else "N/A")
        dd_nav = dd_results["NAV After Tax"]["metrics"]["max_drawdown_pct"]
        st.metric("Max DD% (NAV)", format_percent(dd_nav))
    with cols[3]:
        st.metric("Holding Tax Total", format_money(metrics["holding_tax_total"]))
        st.metric("Sale Tax Total", format_money(metrics["sale_tax_total"]))

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("投資概要")
        info_df = pd.DataFrame({
            "項目": [
                "物件価格", "取得総額", "借入額", "自己資金",
                "保有年数", "構造 / 築年数", "中古耐用年数",
                "所有形態", "譲渡区分", "CAPEX処理",
            ],
            "値": [
                format_money(params["purchase_price"]),
                format_money(summary["total_acquisition_cost"]),
                format_money(summary["loan_amount"]),
                format_money(summary["equity_invested"]),
                f"{params['hold_period_years']} 年",
                f"{params['building_structure']} / {params.get('building_age_years_at_purchase', '?')} 年",
                f"{params.get('building_useful_life_years', '?')} 年",
                params["ownership_type"],
                params.get("sale_term_type", "?"),
                params.get("capex_treatment_mode", "?"),
            ],
        })
        st.dataframe(info_df, hide_index=True, width="stretch")

    with col2:
        st.subheader("税務・リターン指標")
        tax_df = pd.DataFrame({
            "指標": [
                "Tax Drag Ratio", "Total Tax Paid", "Interest Paid Total",
                "Final AT Wealth", "Min DSCR", "Avg DSCR", "Min ICR", "Project IRR",
            ],
            "値": [
                format_percent(metrics["tax_drag_ratio"]),
                format_money(metrics["total_tax_paid"]),
                format_money(metrics["interest_paid_total"]),
                format_money(metrics["final_after_tax_wealth"]),
                format_multiple(metrics["min_dscr"], decimals=2).replace("x", ""),
                format_multiple(metrics["avg_dscr"], decimals=2).replace("x", ""),
                format_multiple(metrics["min_icr"], decimals=2).replace("x", ""),
                format_percent(metrics.get("project_irr")),
            ],
        })
        st.dataframe(tax_df, hide_index=True, width="stretch")

    _glossary_expander("📊 Overview", [
        ("Cap Rate（還元利回り）", "NOI ÷ 物件価格。物件の収益力を示す基本利回り。"),
        ("Equity IRR（自己資金内部収益率）", "自己資金に対する時間加重収益率。初期投資・毎年のATCF・売却益を考慮した複利ベース指標。"),
        ("Equity Multiple（資金倍率）", "累積手取りCF ÷ 初期自己資金。「2.0x」なら自己資金が2倍になったことを意味する。"),
        ("NAV AT（税引後純資産価値）", "Net Asset Value After Tax = 推定市場価値 − 借入残高 − 繰延譲渡税。清算後に手元に残る純資産の推定値。"),
        ("Break-even Year / Cash（キャッシュ回収年）", "累積ATCFが初期自己資金を回収した年。この年以降が実質的な利益フェーズ。"),
        ("Max DD%（最大ドローダウン率）", "ピーク値比での最大下落率。投資リスクの大きさを示す。"),
        ("Tax Drag Ratio（税負担率）", "税金による収益圧迫度 = 総税負担 ÷ 税引前総収益。高いほど税コストが大きい。"),
        ("DSCR（返済余力比率）", "Debt Service Coverage Ratio = NOI ÷ 元利返済額。1.0未満ではNOIが返済に足りない。"),
        ("ICR（利息カバレッジ比率）", "Interest Coverage Ratio = NOI ÷ 支払利息。利息の何倍のNOIを生んでいるかを示す。"),
        ("Project IRR（プロジェクトIRR）", "レバレッジなし（全額自己資金）ベースのIRR。借入効果を除いた物件固有の収益力。"),
        ("Holding Tax Total（保有税合計）", "保有期間中の所得税・住民税等の累計額。"),
        ("Sale Tax Total（譲渡税合計）", "売却益に対して発生する譲渡所得税の額。"),
        ("Final AT Wealth（最終税引後富）", "最終年のNAV AT + 累積ATCF。投資全体の最終的な富の増加額。"),
        ("Interest Paid Total（利払累計）", "保有期間中に支払った利息の合計額。"),
    ])


def _render_cashflow(results):
    df = results["annual_df"]

    st.subheader("年次キャッシュフロー")
    cf_cols = [
        "year", "gross_rent", "egi", "noi", "capex",
        "debt_service", "interest", "principal",
        "total_depreciation", "taxable_income", "tax",
        "btcf", "atcf", "loan_balance_end",
        "sale_proceeds_net", "total_equity_cf",
    ]
    cf_cols = [c for c in cf_cols if c in df.columns]
    st.dataframe(style_negatives_red(df[cf_cols]), column_config=cashflow_column_config(cf_cols),
                 width="stretch", hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("項目別累積CF")
        fig = charts.plot_cumulative_cashflow_components(df)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Annual CF")
        fig = charts.plot_annual_cashflow(df)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("累積 Equity CF (初期投資控除後)")
    fig = charts.plot_cumulative_equity_cf(df)
    st.plotly_chart(fig, use_container_width=True)

    _glossary_expander("💵 Cash Flow", [
        ("Gross Rent（グロス賃料）", "満室想定の年間賃料収入。実際の受取賃料ではなく上限ベース。"),
        ("EGI（実効総収入）", "Effective Gross Income = Gross Rent × (1 − 空室率) + その他収入。"),
        ("NOI（純収益）", "Net Operating Income = EGI − 運営費（利息・減価償却を除く）。物件固有の収益力を示す。"),
        ("CAPEX（資本的支出）", "設備更新・大規模修繕など建物価値を維持・向上させる支出。"),
        ("DS / Debt Service（元利返済額）", "利息 + 元本返済の合計額。"),
        ("Interest（支払利息）", "借入元本残高に対して支払う年間利息。"),
        ("Principal（元本返済）", "元利返済のうち借入残高を減少させる部分。"),
        ("Total Depreciation（減価償却費合計）", "建物減価償却 + 資産計上CAPEXの追加償却の合計。課税所得を圧縮する非現金費用。"),
        ("Taxable Income（課税所得）", "NOI − 利息 − 減価償却費 − 費用処理CAPEX。この値に税率を乗じて税額を算出。"),
        ("BTCF（税引前CF）", "Before-Tax Cash Flow = NOI − 元利返済 − CAPEX ± 資本政策CF。"),
        ("ATCF（税引後CF）", "After-Tax Cash Flow = BTCF − 所得税等。手元に残る実質的なキャッシュフロー。"),
        ("Loan Balance（借入残高）", "年度末時点の未返済借入元本。"),
        ("Sale Proceeds Net（税引後手取り売却純収入）", "売却価格 − 売却費用 − 借入返済 − 譲渡税。"),
        ("Total Equity CF（累積自己資金CF）", "ATCFの累積値（売却CF含む）。自己資金に対するトータルの回収額。"),
    ])


def _render_pl(results):
    pl_df = results["pl_df"]

    st.subheader("Operating P/L テーブル")
    display_cols = [
        "year", "rental_revenue", "other_income", "effective_gross_income",
        "operating_expenses", "property_tax", "repair_cost",
        "operating_profit_before_dep", "depreciation", "interest",
        "accounting_pre_tax_income", "holding_tax",
        "accounting_after_tax_income",
    ]
    display_cols = [c for c in display_cols if c in pl_df.columns]
    st.dataframe(style_negatives_red(pl_df[display_cols]), column_config=cashflow_column_config(display_cols),
                 width="stretch", hide_index=True)

    st.subheader("Operating P/L チャート")
    fig = charts.plot_operating_pl(pl_df)
    st.plotly_chart(fig, use_container_width=True)

    _glossary_expander("📈 P/L", [
        ("Rental Revenue（賃料収入）", "EGIのうち賃料部分（空室調整後）。"),
        ("Other Income（その他収入）", "駐車場・共益費・自販機等の付随的収入。"),
        ("EGI（実効総収入）", "Effective Gross Income = 賃料収入 + その他収入。"),
        ("OpEx / Operating Expenses（運営費）", "管理委託費・損害保険料等の経常的な費用。利息・減価償却・CAPEXは含まない。"),
        ("Property Tax（固定資産税）", "固定資産税・都市計画税の合計。"),
        ("Repair Cost（修繕費）", "小規模な維持修繕費用（CAPEXとは別区分）。"),
        ("Op Profit / Operating Profit（減価償却前営業利益）", "EGI − 全運営費（減価償却・利息を除く）。NOIに近い概念。"),
        ("Depreciation（減価償却費）", "建物取得価額 ÷ 中古耐用年数（定額法）。課税所得を圧縮する非現金費用。"),
        ("Interest（支払利息）", "当年の利息支払額。"),
        ("Pre-Tax Income（税引前会計利益）", "EGI − 全費用 − 減価償却 − 支払利息。"),
        ("Holding Tax（保有税）", "当年の課税所得に基づいて計算された所得税・住民税等。"),
        ("AT Income（税引後会計利益）", "Pre-Tax Income − 保有税。"),
        ("Depr Shield（減価償却タックスシールド）", "減価償却による節税効果 = 減価償却費 × 実効税率。"),
        ("Int Shield（利息タックスシールド）", "利息支払による節税効果 = 支払利息 × 実効税率。"),
    ])


def _render_nav(results):
    nav_df = results["nav_df"]
    summary = results["summary"]

    st.subheader("NAV / Economic P/L テーブル")
    nav_cols = [
        "year", "estimated_market_value", "loan_balance_end",
        "estimated_selling_cost", "adjusted_total_tax_basis",
        "unrealized_gain_pre_tax", "deferred_sale_tax",
        "nav_pre_tax", "nav_after_tax", "nav_change_after_tax",
        "atcf", "economic_profit_after_tax",
    ]
    nav_cols = [c for c in nav_cols if c in nav_df.columns]
    st.dataframe(style_negatives_red(nav_df[nav_cols]), column_config=nav_column_config(nav_cols),
                 width="stretch", hide_index=True)

    st.subheader("MV / Loan / NAV チャート")
    fig = charts.plot_market_value_loan_nav(nav_df, summary["equity_invested"])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Loan Balance 推移")
    fig = charts.plot_loan_balance(results["annual_df"])
    st.plotly_chart(fig, use_container_width=True)

    _glossary_expander("🏠 NAV / Economic P&L", [
        ("Market Value（推定市場価値）", "出口Cap RateによるNOI還元、または土地・建物成長率ベースの年次推定売却価格。"),
        ("Loan Bal（借入残高）", "年度末の未返済借入元本。"),
        ("Sell Cost（推定売却コスト）", "売却価格 × 売却諸費率（仲介手数料等）。"),
        ("Tax Basis（調整後税務取得費）", "取得価額 − 累積減価償却額。譲渡益計算の基礎となる税務上の簿価。"),
        ("Unrealized Gain PT（未実現利益・税引前）", "Market Value − 借入残高 − 売却コスト − Tax Basis。"),
        ("Deferred Sale Tax（繰延譲渡税）", "現時点で売却した場合に発生する試算税額。NAV計算で引当として控除。"),
        ("NAV PT（税引前純資産価値）", "Market Value − 借入残高 − 売却コスト。"),
        ("NAV AT（税引後純資産価値）", "NAV PT − 繰延譲渡税。最終手取りに最も近い実質的な資産価値。"),
        ("ΔNAV AT（NAV変化額）", "前年比の税引後NAV変化。不動産価値増減・ローン返済進捗を反映。"),
        ("ATCF（税引後CF）", "当年の税引後キャッシュフロー（保有中の実際の現金回収）。"),
        ("Econ P/L（税引後経済的利益）", "ΔNAV AT + ATCF。保有によって1年間に生まれた経済的価値増加の合計。"),
    ])


def _render_risk(results):
    dd_results = results["dd_results"]

    st.subheader("Drawdown / Path Risk メトリクス")
    dd_rows = []
    for name, data in dd_results.items():
        m = data["metrics"]
        dd_rows.append({
            "Curve": name,
            "Max DD Abs": m["max_drawdown_abs"],
            "Max DD %": m["max_drawdown_pct"],
            "Max DD Year": m["max_drawdown_year"],
            "DD Duration Max": m["drawdown_duration_max"],
            "Recovery Year": str(m["recovery_year_if_any"]) if m["recovery_year_if_any"] else "N/A",
            "Worst 1Y": m["worst_1y_change"],
            "Worst 3Y": m["worst_3y_change"],
        })
    dd_df = pd.DataFrame(dd_rows)
    dd_col_config = {
        "Max DD Abs": col_money("Max DD Abs"),
        "Max DD %": col_percent("Max DD %"),
        "Max DD Year": col_year("Max DD Year"),
        "Worst 1Y": col_money("Worst 1Y"),
        "Worst 3Y": col_money("Worst 3Y"),
    }
    st.dataframe(style_negatives_red(dd_df), column_config=dd_col_config, hide_index=True, width="stretch")

    st.subheader("Drawdown Curves")
    fig = charts.plot_drawdown_curves(dd_results)
    st.plotly_chart(fig, use_container_width=True)

    _glossary_expander("⚠️ Risk / Drawdown", [
        ("Drawdown（ドローダウン）", "ピーク値からの下落幅。投資中の最大損失角を示すリスク指標。"),
        ("Max DD Abs（最大絶対DD）", "ピーク値から最低点までの絶対額（円）での下落幅。"),
        ("Max DD%（最大DD率）", "ピーク値比での最大下落率。数値が大きいほどリスクが高い。"),
        ("Max DD Year（最大DD年）", "最大ドローダウンが発生した年。"),
        ("DD Duration Max（最大継続期間）", "ドローダウン状態（ピーク未回復）が最も長く続いた期間（年単位）。"),
        ("Recovery Year（回復年）", "ドローダウン後に元のピーク水準に回復した年。「N/A」は保有期間内に未回復。"),
        ("Worst 1Y（最悪1年変化）", "任意の1年間で最も大きく下落した金額。"),
        ("Worst 3Y（最悪3年変化）", "任意の3年間で最も大きく累計下落した金額。"),
        ("NAV After Tax（曲線）", "税引後純資産価値の推移。含み益の消長を反映。"),
        ("Liquidity CF（曲線）", "累積ATCFの推移。実際の現金回収状況を反映。"),
        ("Total Return（曲線）", "NAV AT + 累積ATCF。投資全体の経済的価値の推移。"),
    ])


def _render_scenarios(results):
    params = results["params"]

    st.subheader("Multi-Metric シナリオ比較")
    with st.spinner("シナリオ分析を実行中..."):
        scenario_df = run_scenario_analysis(params)
    _display_scenario_df(scenario_df)

    st.subheader("シナリオ別バーチャート")
    fig = charts.plot_scenario_summary(scenario_df)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("v3 拡張シナリオ (所有形態×CAPEX×Refi×Deemed)")
    with st.spinner("v3拡張シナリオを実行中..."):
        v3_df = build_v3_extended_scenario_summary(params)
    _display_scenario_df(v3_df)

    _glossary_expander("🔄 Scenarios", [
        ("Equity IRR（内部収益率）", "自己資金に対する時間加重収益率。"),
        ("Avg CoC（平均キャッシュオンキャッシュ）", "期間平均ATCF ÷ 自己資金。年次の現金利回りの平均。"),
        ("Tax Drag（税負担率）", "税金による収益圧迫度 = 総税負担 ÷ 税引前総収益。"),
        ("Equity Multiple（資金倍率）", "累積手取りCF ÷ 自己資金。"),
        ("Min DSCR（最低DSCR）", "保有期間中の最低の返済余力比率。1.0未満は危険水域。"),
        ("Min ICR（最低ICR）", "保有期間中の最低の利息カバレッジ比率。"),
        ("BE Year / Cash（回収年）", "累積ATCFが自己資金を上回った年。"),
        ("Final NAV AT（M）（最終税引後NAV）", "最終年の税引後純資産価値（百万円単位）。"),
        ("Max DD% Liq / NAV / TR（最大DD%）", "流動性CF / NAV / トータルリターン各曲線の最大ドローダウン率。"),
        ("CAPEX処理モード（expense_all / capitalize_all / mixed）",
         "全額即時費用処理 / 全額資産計上・追加償却 / 年別混合の3モード。課税所得への影響が異なる。"),
    ])


def _display_scenario_df(sdf):
    col_cfg = {}
    for c in sdf.columns:
        if c in ("Equity IRR", "Avg CoC", "Tax Drag"):
            col_cfg[c] = col_percent(c)
        elif c == "Equity Multiple":
            col_cfg[c] = col_multiple(c)
        elif c in ("Min DSCR", "Min ICR"):
            col_cfg[c] = col_multiple(c)
        elif c == "BE Year (Cash)":
            col_cfg[c] = st.column_config.NumberColumn(c, format="%d")
        elif "(M)" in c:
            col_cfg[c] = st.column_config.NumberColumn(c, format="%,.1f")
        elif "DD%" in c:
            col_cfg[c] = col_percent(c)
    st.dataframe(style_negatives_red(sdf), column_config=col_cfg, hide_index=True, width="stretch")


def _render_ownership(results):
    params = results["params"]

    st.subheader("個人 vs 法人 所有形態比較")
    with st.spinner("所有形態比較を実行中..."):
        own_results = run_ownership_comparison(params)
        own_summary = build_ownership_comparison_summary(own_results)

    own_col_cfg = {}
    for c in own_summary.columns:
        if c in ("Equity IRR", "Avg CoC", "Tax Drag", "Max DD% Liq", "Max DD% NAV"):
            own_col_cfg[c] = col_percent(c)
        elif c in ("Equity Multiple", "Min DSCR"):
            own_col_cfg[c] = col_multiple(c)
        elif "(M)" in c:
            own_col_cfg[c] = st.column_config.NumberColumn(c, format="%,.1f")
    st.dataframe(style_negatives_red(own_summary), column_config=own_col_cfg, hide_index=True, width="stretch")

    st.subheader("所有形態比較チャート")
    fig = charts.plot_ownership_comparison(own_summary)
    st.plotly_chart(fig, use_container_width=True)

    _glossary_expander("👥 Ownership Compare", [
        ("個人所有（individual）", "所得税・住民税・復興税の累進課税。保有5年超で長期譲渡の軽減税率（約20%）適用。"),
        ("法人所有（corporate）", "法人実効税率が一律適用。配当・役員報酬の二重課税は本モデル未対応。"),
        ("Tax Drag（税負担率）", "税金による収益圧迫度。個人と法人で比較することで有利な所有形態を判断できる。"),
        ("Holding Tax Total（保有税合計）", "保有期間中の所得税等の累計額。"),
        ("Sale Tax（譲渡税）", "売却益に対する税額。個人は短期/長期譲渡区分で税率が異なる。"),
        ("Equity IRR / Multiple / CoC", "各指標の定義は「Scenarios」タブの用語解説を参照。"),
        ("Min DSCR / ICR", "各指標の定義は「Scenarios」タブの用語解説を参照。"),
    ])


def _render_tax_exit(results):
    sale_detail = results["sale_detail"]
    tax_bridge = results["tax_bridge"]
    holding_taxes_df = results["holding_taxes_df"]
    wf_df = results["wf_df"]
    cap_events_df = results["cap_events_df"]
    params = results["params"]

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("売却税務サマリー")
        sd_items = []
        for k, v in sale_detail.items():
            if isinstance(v, (int, float)):
                sd_items.append({"項目": k, "値": v})
            else:
                sd_items.append({"項目": k, "値": v})
        sd_df = pd.DataFrame(sd_items)
        st.dataframe(sd_df, hide_index=True, width="stretch")

    with c2:
        st.subheader("Tax Bridge")
        tb_df = pd.DataFrame({"項目": list(tax_bridge.keys()), "金額": list(tax_bridge.values())})
        st.dataframe(style_negatives_red(tb_df), column_config={"金額": col_money("金額")}, hide_index=True, width="stretch")

    st.subheader("Tax Bridge チャート")
    fig = charts.plot_tax_bridge(tax_bridge)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("年次 Holding Tax")
    ht_display = holding_taxes_df.copy()
    ht_display.columns = ["Year", "Holding Tax", "Taxable Income"]
    ht_col_cfg = {
        "Year": col_year("Year"),
        "Holding Tax": col_money("Holding Tax"),
        "Taxable Income": col_money("Taxable Income"),
    }
    st.dataframe(style_negatives_red(ht_display), column_config=ht_col_cfg, hide_index=True, width="stretch")

    st.divider()
    st.subheader("Exit Waterfall")
    st.dataframe(style_negatives_red(wf_df), column_config={"Amount": col_money("Amount")}, hide_index=True, width="stretch")
    fig = charts.plot_exit_waterfall(wf_df)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("資本政策イベント")
    cap_col_cfg = {
        "Amount": col_money("Amount"),
        "Fee/Cost": col_money("Fee/Cost"),
        "Loan Bal After": col_money("Loan Bal After"),
    }
    st.dataframe(style_negatives_red(cap_events_df), column_config=cap_col_cfg, hide_index=True, width="stretch")

    if params.get("enable_refinance", False):
        st.subheader("リファイナンス影響比較")
        fig = charts.plot_refinance_impact(params)
        st.plotly_chart(fig, use_container_width=True)

    _glossary_expander("🏦 Tax / Exit Waterfall", [
        ("Tax Bridge（税務ブリッジ）", "売却税務計算の各ステップを段階的に積み上げた表。売却価格→取得費→課税利益→税率→税額の流れを可視化。"),
        ("みなし取得費（Deemed Acquisition Cost）", "実際の取得費が証明できない場合に売却価格×5%を取得費とみなす税務上の特例。"),
        ("Exit Waterfall（売却時CF分配）", "売却価格 → 売却諸費用 → 借入返済 → 譲渡税 → 手取り純収入 の順次分配を示す。"),
        ("Tax Basis（税務上の取得費）", "取得価額（諸費用込み）− 累積減価償却額。譲渡益 = 売却価格 − Tax Basis。"),
        ("Holding Tax（年次保有税）", "各年の課税所得に対して計算された所得税・住民税等の合計。"),
        ("Capital Events（資本政策イベント）", "リファイナンスや繰上返済などの財務イベント一覧。"),
        ("Refinance Cash Out（リファイナンス調達額）", "リファイナンスにより新たに借り入れた資金（旧借入超過分）。手元資金として活用可能。"),
        ("LTV（借入比率）", "Loan to Value = 借入額 ÷ 物件価格。レバレッジの大きさを示す。"),
        ("譲渡区分（長期 / 短期）", "個人所有時、保有5年超→長期譲渡（税率約20%）、保有5年以内→短期譲渡（通常税率）。"),
    ])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    st.title("🏢 不動産投資シミュレーター")
    st.caption("v3 — 税務精緻化・CAPEX税務・所有形態比較・資本政策イベント対応")

    params = _build_sidebar()
    st.session_state["current_params"] = params

    # Run analysis button
    run_btn = st.sidebar.button("▶ Run Analysis", type="primary", width="stretch")

    params_changed = st.session_state.get("last_run_params") != params
    if run_btn or "results" not in st.session_state or params_changed:
        with st.spinner("分析を実行中..."):
            try:
                results = run_full_analysis(params)
                st.session_state["results"] = results
                st.session_state["last_run_params"] = params
            except Exception as e:
                st.error(f"エラー: {e}")
                return

    if "results" not in st.session_state:
        st.info("サイドバーでパラメータを設定し、Run Analysis を押してください。")
        return

    results = st.session_state["results"]

    tabs = st.tabs([
        "📊 Overview",
        "💵 Cash Flow",
        "📈 PL",
        "🏠 NAV / Economic P&L",
        "⚠️ Risk / Drawdown",
        "🔄 Scenarios",
        "👥 Ownership Compare",
        "🏦 Tax / Exit Waterfall",
    ])

    with tabs[0]:
        _render_overview(results)
    with tabs[1]:
        _render_cashflow(results)
    with tabs[2]:
        _render_pl(results)
    with tabs[3]:
        _render_nav(results)
    with tabs[4]:
        _render_risk(results)
    with tabs[5]:
        _render_scenarios(results)
    with tabs[6]:
        _render_ownership(results)
    with tabs[7]:
        _render_tax_exit(results)


if __name__ == "__main__":
    main()
