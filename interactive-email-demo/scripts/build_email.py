#!/usr/bin/env python3
"""Build AMP, HTML, text, browser-preview, and RFC 5322 email outputs."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = PROJECT_ROOT / "templates"
METRIC_ID = re.compile(r"^[a-z][a-z0-9-]*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=PROJECT_ROOT / "sample-report.json")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument("--from-address", default="reports@example.com")
    parser.add_argument("--to-address", default="reader@example.net")
    return parser.parse_args()


def load_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    required = {"subject", "report_date", "summary", "action", "dashboard_url", "metrics"}
    missing = required - report.keys()
    if missing:
        raise ValueError(f"Missing report fields: {', '.join(sorted(missing))}")

    url = urlparse(str(report["dashboard_url"]))
    if url.scheme != "https" or not url.netloc:
        raise ValueError("dashboard_url must be an absolute HTTPS URL")

    metrics = report["metrics"]
    if not isinstance(metrics, list) or not metrics:
        raise ValueError("metrics must be a non-empty list")

    seen: set[str] = set()
    for metric in metrics:
        for field in ("id", "label", "headline", "comparison", "unit", "values"):
            if field not in metric:
                raise ValueError(f"Metric is missing {field!r}")
        metric_id = str(metric["id"])
        if not METRIC_ID.fullmatch(metric_id):
            raise ValueError(f"Invalid metric id: {metric_id!r}")
        if metric_id in seen:
            raise ValueError(f"Duplicate metric id: {metric_id!r}")
        seen.add(metric_id)
        if not isinstance(metric["values"], list) or not metric["values"]:
            raise ValueError(f"Metric {metric_id!r} needs at least one value")
        for point in metric["values"]:
            value = point.get("value")
            if "label" not in point or not isinstance(value, (int, float)):
                raise ValueError(f"Invalid data point in metric {metric_id!r}")
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(f"Metric values must be finite and non-negative: {value!r}")
    return report


def escaped(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_template(name: str, replacements: dict[str, str]) -> str:
    rendered = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    leftovers = sorted(set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", rendered)))
    if leftovers:
        raise ValueError(f"Unresolved template values in {name}: {', '.join(leftovers)}")
    return rendered


def format_value(value: float | int) -> str:
    if isinstance(value, int) or float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.1f}"


def bar_rows(metric: dict[str, Any], *, email_style: bool) -> str:
    max_value = max(float(point["value"]) for point in metric["values"]) or 1.0
    rows: list[str] = []
    for point in metric["values"]:
        width = round(float(point["value"]) / max_value * 100)
        label = escaped(point["label"])
        value = escaped(format_value(point["value"]))
        unit = escaped(metric["unit"])
        if email_style:
            rows.append(
                '<div class="bar-row">'
                f'<div class="bar-label">{label}</div>'
                '<div class="bar-track">'
                f'<div class="bar" style="width:{width}%"></div>'
                "</div>"
                f'<div class="bar-value">{value} {unit}</div>'
                "</div>"
            )
        else:
            rows.append(
                "<tr>"
                f'<td style="width:42px;padding:5px 0;font-size:12px;color:#486581">{label}</td>'
                '<td style="padding:5px 8px"><div style="height:18px;background:#edf2f7">'
                f'<div style="width:{width}%;height:18px;background:#137c8b"></div></div></td>'
                f'<td style="width:90px;padding:5px 0;font-size:12px;font-weight:bold">{value} {unit}</td>'
                "</tr>"
            )
    return "\n".join(rows)


def amp_buttons(metrics: list[dict[str, Any]]) -> str:
    buttons: list[str] = []
    for index, metric in enumerate(metrics):
        metric_id = metric["id"]
        default_class = "metric-button-active" if index == 0 else "metric-button"
        expression = f"metric == '{metric_id}' ? 'metric-button-active' : 'metric-button'"
        buttons.append(
            f'<button type="button" class="{default_class}" [class]="{expression}" '
            f"on=\"tap:AMP.setState({{ metric: '{metric_id}' }})\">"
            f"{escaped(metric['label'])}</button>"
        )
    return "\n".join(buttons)


def amp_panels(metrics: list[dict[str, Any]]) -> str:
    panels: list[str] = []
    for index, metric in enumerate(metrics):
        hidden = "" if index == 0 else " hidden"
        max_value = max(float(point["value"]) for point in metric["values"])
        panels.append(
            f'<section class="chart"{hidden} [hidden]="metric != \'{metric["id"]}\'">'
            f'<div class="headline">{escaped(metric["headline"])}</div>'
            f'<div class="comparison">{escaped(metric["comparison"])}</div>'
            f"{bar_rows(metric, email_style=True)}"
            f'<div class="axis-note">Scale: 0–{escaped(format_value(max_value))} '
            f"{escaped(metric['unit'])}</div>"
            "</section>"
        )
    return "\n".join(panels)


def fallback_panel(metric: dict[str, Any]) -> str:
    max_value = max(float(point["value"]) for point in metric["values"])
    return (
        '<div style="padding:18px;border:1px solid #dbe3ee">'
        f'<div style="font-size:28px;font-weight:bold;color:#102a43">{escaped(metric["headline"])}</div>'
        f'<div style="margin:4px 0 13px;font-size:13px;color:#627d98">{escaped(metric["comparison"])}</div>'
        '<table role="img" aria-label="Revenue bar chart" width="100%" cellspacing="0" cellpadding="0">'
        f"{bar_rows(metric, email_style=False)}"
        "</table>"
        f'<div style="margin-top:8px;text-align:right;font-size:11px;color:#829ab1">Scale: 0–{escaped(format_value(max_value))} {escaped(metric["unit"])}</div>'
        "</div>"
    )


def build_outputs(
    report: dict[str, Any], output_dir: Path, from_address: str, to_address: str
) -> dict[str, Path]:
    if from_address.casefold() == to_address.casefold():
        raise ValueError("From and To addresses must be different for Gmail AMP testing")

    common = {
        "SUBJECT": escaped(report["subject"]),
        "REPORT_DATE": escaped(report["report_date"]),
        "SUMMARY": escaped(report["summary"]),
        "ACTION": escaped(report["action"]),
        "DASHBOARD_URL": escaped(report["dashboard_url"]),
    }
    metrics = report["metrics"]
    amp_html = render_template(
        "report.amp.html",
        common
        | {
            "INITIAL_METRIC_JSON": json.dumps(metrics[0]["id"]),
            "AMP_BUTTONS": amp_buttons(metrics),
            "AMP_PANELS": amp_panels(metrics),
        },
    )
    fallback_html = render_template(
        "report.html", common | {"FALLBACK_PANEL": fallback_panel(metrics[0])}
    )
    safe_json = json.dumps(report, ensure_ascii=False).replace("<", "\\u003c")
    browser_html = render_template("browser-preview.html", common | {"REPORT_JSON": safe_json})
    plain_text = (
        f"{report['subject']}\n\n"
        f"{report['summary']}\n\n"
        f"{metrics[0]['label']}: {metrics[0]['headline']}\n"
        f"{metrics[0]['comparison']}\n\n"
        f"Next action: {report['action']}\n\n"
        f"Interactive report: {report['dashboard_url']}\n"
    )

    message = EmailMessage(policy=SMTP)
    message["Subject"] = str(report["subject"])
    message["From"] = from_address
    message["To"] = to_address
    message.set_content(plain_text)
    message.add_alternative(amp_html, subtype="x-amp-html")
    message.add_alternative(fallback_html, subtype="html")

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "eml": output_dir / "weekly-report.eml",
        "amp": output_dir / "weekly-report.amp.html",
        "html": output_dir / "weekly-report.html",
        "text": output_dir / "weekly-report.txt",
        "browser": output_dir / "browser-preview.html",
    }
    paths["eml"].write_bytes(message.as_bytes())
    paths["amp"].write_text(amp_html, encoding="utf-8")
    paths["html"].write_text(fallback_html, encoding="utf-8")
    paths["text"].write_text(plain_text, encoding="utf-8")
    paths["browser"].write_text(browser_html, encoding="utf-8")
    return paths


def main() -> None:
    args = parse_args()
    report = load_report(args.data)
    paths = build_outputs(report, args.output_dir, args.from_address, args.to_address)
    for kind, path in paths.items():
        print(f"{kind:>7}: {path}")


if __name__ == "__main__":
    main()
