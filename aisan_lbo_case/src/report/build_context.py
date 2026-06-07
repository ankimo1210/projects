from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.fetch.fetch_peer_data import main as fetch_peer_data
from src.model.lbo_model import write_model_outputs
from src.model.sensitivities import run_all_sensitivities
from src.parse.parse_financials import main as parse_financials
from src.parse.parse_segments import main as parse_segments
from src.parse.parse_shareholders import main as parse_shareholders
from src.report.charts import build_chart_data
from src.report.tables import format_case_summary, records
from src.utils.formatting import fmt_jpy_bn, fmt_jpy_mn, fmt_multiple, fmt_pct
from src.utils.sources import CONFIG_DIR, OUTPUT_DIR, PROJECT_ROOT, load_sources, load_yaml, now_jst_iso, write_sources_bibliography


def ensure_base_outputs() -> None:
    parse_financials()
    parse_segments()
    parse_shareholders()
    fetch_peer_data()
    write_model_outputs()
    sensitivities = run_all_sensitivities()
    sensitivities.to_csv(OUTPUT_DIR / "sensitivity_outputs.csv", index=False)
    write_sources_bibliography(extra_rows=_raw_fetch_source_rows())


def _raw_fetch_source_rows() -> list[dict[str, Any]]:
    manifest_path = PROJECT_ROOT / "data" / "interim" / "company_ir_fetch_manifest.csv"
    if not manifest_path.exists():
        return []
    manifest = pd.read_csv(manifest_path)
    rows = []
    for row in manifest.to_dict("records"):
        rows.append(
            {
                "source_id": f"raw_{row['source_id']}",
                "title": f"Raw fetched copy: {row['source_id']}",
                "publisher": "",
                "url": row["url"],
                "source_type": "raw_fetch",
                "retrieved_at": row["retrieved_at"],
                "local_path": row["local_path"],
                "notes": f"HTTP status {row['status']}; content-type {row['content_type']}; {row.get('error', '')}",
            }
        )
    return rows


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_context() -> dict[str, Any]:
    ensure_base_outputs()
    assumptions = load_yaml(CONFIG_DIR / "assumptions.yaml")
    scenarios = load_yaml(CONFIG_DIR / "scenarios.yaml")["scenarios"]
    sources = load_sources()

    historical = _read_csv(PROJECT_ROOT / "data" / "processed" / "historical_financials.csv")
    management_forecast = _read_csv(PROJECT_ROOT / "data" / "processed" / "management_forecast.csv")
    segments = _read_csv(PROJECT_ROOT / "data" / "processed" / "segment_financials.csv")
    shareholders = _read_csv(PROJECT_ROOT / "data" / "processed" / "shareholders.csv")
    peers = _read_csv(PROJECT_ROOT / "data" / "processed" / "peer_set.csv")
    precedents = _read_csv(PROJECT_ROOT / "data" / "processed" / "precedent_transactions.csv")
    model_outputs = _read_csv(OUTPUT_DIR / "model_outputs.csv")
    projections = _read_csv(PROJECT_ROOT / "data" / "processed" / "projection_detail.csv")
    sensitivities = _read_csv(OUTPUT_DIR / "sensitivity_outputs.csv")
    bibliography = _read_csv(OUTPUT_DIR / "sources_bibliography.csv")
    summary_json = _load_json(OUTPUT_DIR / "model_summary.json")

    default_premium = float(assumptions["transaction_assumptions"]["default_premium"])
    default_outputs = model_outputs[model_outputs["premium"].round(6) == round(default_premium, 6)].copy()
    sponsor_default = default_outputs[default_outputs["scenario"] == "Sponsor"].iloc[0].to_dict()
    downside_default = default_outputs[default_outputs["scenario"] == "Downside"].iloc[0].to_dict()
    base_default = default_outputs[default_outputs["scenario"] == "Base"].iloc[0].to_dict()

    market = summary_json["market_snapshot"]
    latest_bs = assumptions["latest_balance_sheet_reference"]
    share_data = assumptions["share_data"]
    akisoku = assumptions["akisoku_subsidiary"]
    forecast = assumptions["management_forecast"]
    latest_hist = historical.iloc[-1].to_dict()

    risk_matrix = [
        {"risk": "Subsidiary investigation / accounting restatement", "rating": "Red", "mitigant": "No final bid until report, audit sign-off and remediation plan are reviewed."},
        {"risk": "Debt capacity", "rating": "Amber", "mitigant": "Model uses only 0.5x-1.15x EBITDA; returns cannot rely on leverage."},
        {"risk": "Mobility / DX revenue quality", "rating": "Amber", "mitigant": "Confirm backlog, subsidies, recurring revenue and true segment margin."},
        {"risk": "Public-sector lumpiness", "rating": "Amber", "mitigant": "Underwrite normalized revenue and working-capital seasonality."},
        {"risk": "Core public surveying software niche", "rating": "Green", "mitigant": "Long operating history and domain-specific installed base support strategic relevance."},
        {"risk": "Net-cash balance sheet", "rating": "Green", "mitigant": "Useful only if excess cash can be accessed without damaging operations or stakeholder support."},
    ]

    dd_items = [
        {"rank": 1, "item": "Accounting and investigation issue", "severity": "Critical", "why": "Gating item for financial reliability, audit timing and bid certainty."},
        {"rank": 2, "item": "Revenue quality and recurring revenue ratio", "severity": "Critical", "why": "Determines whether software-like valuation and financing assumptions are defensible."},
        {"rank": 3, "item": "Segment-level margins and true profitability", "severity": "High", "why": "Public and Mobility / DX economics appear materially different and require normalized cost allocation."},
        {"rank": 4, "item": "Customer concentration and public-sector dependency", "severity": "High", "why": "Public-sector and local-government projects may be lumpy and budget-dependent."},
        {"rank": 5, "item": "Mobility / DX backlog and pipeline quality", "severity": "High", "why": "Downside case is driven mainly by Mobility / DX underperformance."},
        {"rank": 6, "item": "R&D capitalization / expense treatment", "severity": "High", "why": "Could affect EBITDA quality and comparability."},
        {"rank": 7, "item": "Working-capital seasonality", "severity": "Medium", "why": "Historical FCF includes a negative FY2024 and rebound in FY2025."},
        {"rank": 8, "item": "Cash and excess cash availability", "severity": "High", "why": "Returns are sensitive to whether surplus cash can be used in the transaction."},
        {"rank": 9, "item": "Debt capacity and lender appetite", "severity": "High", "why": "Small EBITDA base constrains acquisition financing."},
        {"rank": 10, "item": "Management willingness and shareholder approval path", "severity": "High", "why": "Founder, strategic holders and treasury share mechanics affect TOB feasibility."},
        {"rank": 11, "item": "Major shareholder intentions", "severity": "High", "why": "Top holders include founder/individual and strategic corporate holders."},
        {"rank": 12, "item": "TOB mechanics and squeeze-out feasibility", "severity": "High", "why": "Low liquidity and required premium can dilute sponsor returns."},
        {"rank": 13, "item": "Key person dependency", "severity": "Medium", "why": "Domain software and public-sector relationships may rely on specific engineers and sales leaders."},
        {"rank": 14, "item": "IP ownership and software licensing", "severity": "Medium", "why": "Confirm ownership of Wingneo, WingEarth, ANIST and related modules."},
        {"rank": 15, "item": "Competitive position", "severity": "Medium", "why": "Assess larger GIS, CAD, mapping and autonomous mobility platforms."},
    ]

    value_up_plan = [
        "Convert more of the public surveying software base into recurring maintenance, cloud modules and data services.",
        "Separate Mobility / DX project revenue from durable platform revenue; keep low-margin one-off projects disciplined.",
        "Use private ownership to remove listing cost, simplify governance and reinvest behind product management and sales coverage.",
        "Rationalize cash: retain operating liquidity, but evaluate buyback-equivalent recapitalization or post-close dividend only after legal and lender review.",
        "Pursue targeted partnerships or bolt-ons in point-cloud processing, local government DX and high-precision map data.",
    ]

    company_fact_cards = [
        {"label": "Latest close", "value": f"JPY {float(market['close_price_jpy']):,.0f}", "note": f"as of {market['as_of']}"},
        {"label": "Market cap", "value": fmt_jpy_bn(float(market["market_cap_jpy_mn"])), "note": "gross shares basis"},
        {"label": "FY2025A revenue", "value": fmt_jpy_bn(float(latest_hist["revenue"])), "note": "sourced from IRBANK summary"},
        {"label": "FY2025A est. EBITDA", "value": fmt_jpy_mn(float(latest_hist["ebitda_estimated"])), "note": "EBIT + estimated D&A"},
        {"label": "Latest cash / debt", "value": f"{fmt_jpy_mn(float(latest_bs['cash']))} / {fmt_jpy_mn(float(latest_bs['debt']))}", "note": latest_bs["as_of"]},
        {"label": "Sponsor case IRR", "value": fmt_pct(float(sponsor_default["irr"])), "note": "30% premium, 5-year hold"},
    ]

    source_lookup = {
        source_id: {"title": item.get("title", ""), "url": item.get("url", "")}
        for source_id, item in sources.items()
    }

    return {
        "generated_at": now_jst_iso(),
        "company": assumptions["company"],
        "recommendation": summary_json["recommendation"],
        "market": market,
        "share_data": share_data,
        "latest_bs": latest_bs,
        "akisoku": akisoku,
        "forecast": forecast,
        "default_premium": default_premium,
        "company_fact_cards": company_fact_cards,
        "case_summary_rows": format_case_summary(default_outputs),
        "all_case_rows": format_case_summary(model_outputs),
        "sponsor_default": sponsor_default,
        "base_default": base_default,
        "downside_default": downside_default,
        "historical_rows": records(historical),
        "management_forecast_rows": records(management_forecast),
        "segment_rows": records(segments),
        "shareholder_rows": records(shareholders),
        "peer_rows": records(peers),
        "precedent_rows": records(precedents),
        "source_rows": records(bibliography),
        "risk_matrix": risk_matrix,
        "dd_items": dd_items,
        "value_up_plan": value_up_plan,
        "scenarios": scenarios,
        "chart_data": build_chart_data(historical, projections, model_outputs, sensitivities),
        "source_lookup": source_lookup,
        "fmt_pct": fmt_pct,
        "fmt_jpy_mn": fmt_jpy_mn,
        "fmt_jpy_bn": fmt_jpy_bn,
        "fmt_multiple": fmt_multiple,
    }
