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

# The report draws only these two models' calibration curves; the rest of the
# per-quantile records would triple the page for numbers nothing reads.
CALIBRATION_MODELS = {"timesfm_3.0", "seasonal_naive"}


def slim(data: dict) -> dict:
    """Drop the records the page never reads, so the payload stays small."""
    out = dict(data)
    out["calibration"] = [
        r for r in data["calibration"] if r["model"] in CALIBRATION_MODELS
    ]
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
