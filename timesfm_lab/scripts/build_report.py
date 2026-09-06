"""Inline the tokens, the data and the body into the two report files.

Two outputs on purpose: ``report.html`` is a standalone page with its own
``<!doctype>`` wrapper for opening off disk, and ``report_artifact.html`` starts
at ``<title>`` because the Artifact host supplies the wrapper itself.
"""

from __future__ import annotations

import json
from pathlib import Path

from timesfm_lab.bench import RESULTS_DIR

ROOT = Path(__file__).resolve().parents[2]
TOKENS = ROOT / "docs" / "templates" / "claude-report" / "tokens.css"
BODY = RESULTS_DIR / "_body.html"

# Only these panels are drawn from the per-step profile; shipping all of it would
# triple the page for numbers nothing reads.
HORIZON_DATASETS = {"traffic_hourly", "solar_10_minutes"}
HORIZON_MODELS = {"timesfm_3.0", "seasonal_naive"}


def slim(data: dict) -> dict:
    out = dict(data)
    out["horizon"] = [
        r
        for r in data["horizon"]
        if r["dataset"] in HORIZON_DATASETS and r["model"] in HORIZON_MODELS
    ]
    out["contamination"] = {
        k: v for k, v in data["contamination"].items() if k != "by_exposure"
    } | {
        "by_exposure": [
            r for r in data["contamination"]["by_exposure"] if r["model"] == "timesfm_3.0"
        ]
    }
    return out


def main() -> None:
    tokens = TOKENS.read_text(encoding="utf-8")
    body = BODY.read_text(encoding="utf-8")
    data = slim(json.loads((RESULTS_DIR / "report_data.json").read_text(encoding="utf-8")))

    page = body.replace("/*TOKENS*/", tokens).replace(
        "/*DATA*/", json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    )
    if "/*TOKENS*/" in page or "/*DATA*/" in page:
        raise RuntimeError("placeholder substitution failed")

    artifact = RESULTS_DIR / "report_artifact.html"
    artifact.write_text(page, encoding="utf-8")

    standalone = RESULTS_DIR / "report.html"
    standalone.write_text(
        '<!doctype html>\n<html lang="ja">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f"{page}\n</html>\n",
        encoding="utf-8",
    )
    for p in (artifact, standalone):
        print(f"{p}  {p.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
