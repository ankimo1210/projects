"""JohnHull-specific source pages and verified regression assertions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .baseline import REFERENCES_ROOT, read_json
from .schema import P0_PAPER_IDS

GOLD_ROOT = REFERENCES_ROOT / "gold"
DEFAULT_MANIFEST_OUTPUT = GOLD_ROOT / "gold_manifest.json"
DEFAULT_ASSERTIONS_OUTPUT = GOLD_ROOT / "gold_assertions.jsonl"

GOLD_PAGE_SELECTIONS = {
    "1900-bachelier-theorie-de-la-speculation": (1, 6, 11, 16, 23, 67),
    "1973-black-scholes-options-corporate-liabilities": (1, 2, 4, 5, 8, 19),
    "1990-hull-white-interest-rate-derivative-securities": (1, 4, 5, 6, 14, 17, 18, 20),
    "1993-heston-closed-form-stochastic-volatility": (1, 2, 3, 5, 6, 8, 16, 17),
    "2000-mcneil-frey-tail-risk-evt": (1, 5, 14, 15, 24, 29),
    "2001-longstaff-schwartz-american-options-lsm": (1, 5, 10, 20, 30, 36),
    "2002-hagan-et-al-managing-smile-risk": (1, 4, 8, 15, 25, 41),
    "2003-jarrow-yildirim-inflation-hjm": (1, 3, 5, 7, 8, 9, 20, 21, 22),
    "2008-fang-oosterlee-cos-method": (1, 3, 5, 10, 15, 16, 17, 18, 23),
    "2019-lyashenko-mercurio-backward-looking-rates": (1, 4, 8, 12, 20, 25),
    "2020-huge-savine-differential-machine-learning": (1, 5, 10, 20, 35, 51),
    "2021-mof-jgbi-indexation-notice": (1, 2, 3, 4, 5, 6),
    "2024-mof-jgbi-bei-guide": (1, 2, 5, 7, 8, 9),
}

VERIFIED_ASSERTIONS = (
    {
        "assertion_id": "hw-p6-vasicek-b",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 6,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": r"B(t,T)=\frac{1-e^{-a(T-t)}}{a}",
        "expected_text": None,
        "source_bbox_normalized": [156, 190, 838, 261],
        "source_asset_name": "958dbd9b1387f764e95241003396aa1ab876121d0968662d9b0309acdcdb9529.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "hw-p6-mean-reversion",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 6,
        "kind": "display_formula",
        "equation_number": "15",
        "expected_latex": (
            r"a(t)=-\frac{\partial^2 B(0,t)/\partial t^2}{\partial B(0,t)/\partial t}"
        ),
        "expected_text": None,
        "source_bbox_normalized": [258, 863, 537, 905],
        "source_asset_name": "b09a4e119fac6b3aaa081a82979e5b15932c7b83853b9a15aaf12a1a08329ab0.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "hw-p17-table4-ext-vas-102",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 17,
        "kind": "table_cell",
        "table_number": "4",
        "row_key": "1.0|Ext Vas",
        "column_key": "1.02",
        "expected_numeric": 0.35,
        "row_index": 2,
        "column_index": 5,
        "source_bbox_normalized": [108, 660, 861, 827],
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "hw-p17-table4-cir-102",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 17,
        "kind": "table_cell",
        "table_number": "4",
        "row_key": "1.0|Two-factor CIR",
        "column_key": "1.02",
        "expected_numeric": 0.34,
        "row_index": 3,
        "column_index": 5,
        "source_bbox_normalized": [108, 660, 861, 827],
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "hw-p17-table3-ext-vas-200-100",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 17,
        "kind": "table_cell",
        "table_number": "3",
        "row_key": "2.0|Ext Vas",
        "column_key": "1.00",
        "expected_numeric": 1.32,
        "row_index": 4,
        "column_index": 4,
        "source_bbox_normalized": [112, 118, 863, 287],
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hw-p17-table4-cir-200-100",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 17,
        "kind": "table_cell",
        "table_number": "4",
        "row_key": "2.0|Two-factor CIR",
        "column_key": "1.00",
        "expected_numeric": 0.86,
        "row_index": 5,
        "column_index": 4,
        "source_bbox_normalized": [108, 660, 861, 827],
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "heston-p5-g",
        "paper_id": "1993-heston-closed-form-stochastic-volatility",
        "page_number": 5,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": (r"g=\frac{b_j-\rho\sigma\phi i+d}{b_j-\rho\sigma\phi i-d}"),
        "expected_text": None,
        "source_bbox_normalized": [293, 534, 720, 606],
        "source_asset_name": "e99fb9e3a5803784f9a9d19b2307c336e30143e13abd1d501aa56531399c958e.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "heston-p5-d",
        "paper_id": "1993-heston-closed-form-stochastic-volatility",
        "page_number": 5,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": (r"d=\sqrt{(\rho\sigma\phi i-b_j)^2-\sigma^2(2u_j\phi i-\phi^2)}"),
        "expected_text": None,
        "source_bbox_normalized": [293, 534, 720, 606],
        "source_asset_name": "e99fb9e3a5803784f9a9d19b2307c336e30143e13abd1d501aa56531399c958e.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "mcneil-frey-p14-es",
        "paper_id": "2000-mcneil-frey-tail-risk-evt",
        "page_number": 14,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": r"S_q^t=\mu_{t+1}+\sigma_{t+1}E[Z\mid Z>z_q]",
        "expected_text": None,
        "source_bbox_normalized": [372, 69, 627, 90],
        "source_asset_name": "4a4a87078e8e6c993552cf23f70b7584687d4e4b229e8f035e1267c9f0428528.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
)


def build_gold_manifest(references_root: Path = REFERENCES_ROOT) -> dict[str, Any]:
    """Build the deterministic selected-page manifest from tracked preflight data."""

    baseline = read_json(references_root / "corpus_baseline.json")
    preflight = read_json(references_root / "corpus_preflight.json")
    source_by_id = {item["paper_id"]: item for item in baseline["sources"]}
    profile_by_id = {item["paper_id"]: item for item in preflight["papers"]}
    selected_pages: list[dict[str, Any]] = []
    for paper_id, pages in GOLD_PAGE_SELECTIONS.items():
        source = source_by_id[paper_id]
        profile = profile_by_id[paper_id]
        page_by_number = {item["page_number"]: item for item in profile["pages"]}
        for page_number in pages:
            page = page_by_number[page_number]
            reasons = [page["route"]]
            if page_number == 1:
                reasons.append("front_matter")
            if page_number == source["source_page_count"]:
                reasons.append("final_page")
            if page["math_dense"]:
                reasons.append("math_dense")
            if page["damaged"] and "damaged" not in reasons:
                reasons.append("damaged")
            selected_pages.append(
                {
                    "gold_page_id": f"{paper_id}:p{page_number:04d}",
                    "paper_id": paper_id,
                    "page_number": page_number,
                    "source_pdf_sha256": source["source_sha256"],
                    "p0": paper_id in P0_PAPER_IDS,
                    "selection_reasons": reasons,
                    "annotation_status": "selected",
                }
            )
    return {
        "gold_manifest_version": "1.0.0",
        "paper_count": len(GOLD_PAGE_SELECTIONS),
        "page_count": len(selected_pages),
        "targets": {
            "minimum_pages": 60,
            "minimum_display_equations": 150,
            "minimum_inline_equations": 200,
            "minimum_table_cells": 500,
            "minimum_claims_per_paper": 5,
        },
        "selected_pages": selected_pages,
    }


def render_json(value: Any) -> str:
    """Serialize stable indented JSON."""

    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_assertions(assertions: tuple[dict[str, Any], ...] = VERIFIED_ASSERTIONS) -> str:
    """Serialize one stable JSON record per manually reviewed assertion."""

    return "".join(
        json.dumps(item, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        for item in assertions
    )
