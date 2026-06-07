from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.report.build_context import build_context
from src.utils.sources import OUTPUT_DIR, PROJECT_ROOT


TEMPLATE_DIR = PROJECT_ROOT / "src" / "templates"


def write_assumptions_log(context: dict) -> None:
    lines = [
        "# AISAN LBO Assumptions Log",
        "",
        f"Generated at: {context['generated_at']}",
        "",
        "## Recommendation",
        "",
        f"- Recommendation: {context['recommendation']['recommendation']}",
        f"- Investment view: {context['recommendation']['investment_view']}",
        f"- Gating issue: {context['recommendation']['gating_issue']}",
        "",
        "## Key Sourced Inputs",
        "",
        f"- Latest close: JPY {float(context['market']['close_price_jpy']):,.0f} as of {context['market']['as_of']} (source: {context['market'].get('source_id', 'market source')})",
        f"- Shares outstanding: {context['share_data']['shares_outstanding']:,.0f} (source: {context['share_data']['source_id']})",
        f"- Latest cash / debt: {context['latest_bs']['cash']:,.0f} / {context['latest_bs']['debt']:,.0f} JPYm (source: {context['latest_bs']['source_id']})",
        f"- FY2026 forecast sales / EBIT: {context['forecast']['revenue']:,.0f} / {context['forecast']['ebit']:,.0f} JPYm (source: {context['forecast']['source_id']})",
        "",
        "## Key Estimated Inputs",
        "",
    ]
    for scenario, cfg in context["scenarios"].items():
        lines.append(f"### {scenario}")
        lines.append(f"- Exit multiple: {cfg['exit_multiple']}x")
        lines.append(f"- Debt / EBITDA: {cfg['debt_to_ebitda']}x")
        lines.append(f"- EBITDA margin path: {', '.join(f'{x:.1%}' for x in cfg['ebitda_margin'])}")
        lines.append(f"- Mobility / DX growth path: {', '.join(f'{x:.1%}' for x in cfg['mobility_dx_growth'])}")
        lines.append("")
    lines.extend(
        [
            "## Manual Data Limitations",
            "",
            "- EDINET annual securities reports require API-key/manual refresh in this scaffold.",
            "- Peer and precedent multiples are placeholders unless refreshed from transaction filings or market databases.",
            "- EBITDA is estimated as EBIT plus D&A estimated at 3.0% of revenue unless official D&A is loaded.",
            "- Excess cash availability is a sponsor estimate and must be verified legally and operationally.",
            "",
        ]
    )
    (OUTPUT_DIR / "assumptions_log.md").write_text("\n".join(lines), encoding="utf-8")


def render_report() -> Path:
    context = build_context()
    styles = (TEMPLATE_DIR / "styles.css").read_text(encoding="utf-8")
    context["styles"] = styles
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.j2")
    html = template.render(**context)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "aisan_lbo_investment_report.html"
    out_path.write_text(html, encoding="utf-8")
    write_assumptions_log(context)
    return out_path


def main() -> None:
    path = render_report()
    print(path)


if __name__ == "__main__":
    main()
