"""MinerU-to-corpus-v2 conversion tests."""

from __future__ import annotations

import json
from pathlib import Path

from johnhull.scripts.paper_corpus.baseline import REFERENCES_ROOT
from johnhull.scripts.paper_corpus.mineru import (
    convert_mineru_paper,
    latex_syntax_status,
    normalized_bbox_to_pdf,
    parse_numeric,
    parse_table_html,
)

GOLD_MINERU_ROOT = Path(__file__).resolve().parents[1] / "fixtures/paper_corpus/mineru"
HULL_WHITE = "1990-hull-white-interest-rate-derivative-securities"
HULL_WHITE_GOLD_PAGES = [1, 4, 5, 6, 7, 14, 17, 18, 20]
MOF_NOTICE = "2021-mof-jgbi-indexation-notice"
MOF_NOTICE_GOLD_PAGES = [1, 2, 3, 4, 5, 6]


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_table_parser_preserves_merged_coordinates_and_numeric_typing():
    cells = parse_table_html(
        "<table><tr><th rowspan='2'>Term</th><th colspan='2'>Value</th></tr>"
        "<tr><td>1.0</td><td>2.0%</td></tr></table>"
    )

    assert [(cell.row, cell.column, cell.row_span, cell.column_span) for cell in cells] == [
        (0, 0, 2, 1),
        (0, 1, 1, 2),
        (1, 1, 1, 1),
        (1, 2, 1, 1),
    ]
    assert parse_numeric("2.0%") == 0.02
    assert parse_numeric("1.2 years") is None


def test_bbox_scaling_and_latex_syntax_are_conservative():
    bbox = normalized_bbox_to_pdf([100, 200, 900, 800], 600, 800)

    assert bbox.to_list() == [60.0, 160.0, 540.0, 640.0]
    assert latex_syntax_status(r"\frac{a}{b}") == "passed"
    assert latex_syntax_status(r"\frac{a}{b") == "failed"


def test_gold_conversion_applies_only_explicit_verified_overrides(tmp_path):
    if not GOLD_MINERU_ROOT.is_dir():
        raise AssertionError("reviewed MinerU gold fixture is required")
    output = tmp_path / HULL_WHITE

    result = convert_mineru_paper(
        paper_id=HULL_WHITE,
        source_pdf=REFERENCES_ROOT / "papers" / f"{HULL_WHITE}.pdf",
        mineru_root=GOLD_MINERU_ROOT,
        output_dir=output,
        page_mapping=HULL_WHITE_GOLD_PAGES,
    )
    equations = _read_jsonl(output / "equations.jsonl")
    tables = _read_jsonl(output / "tables.jsonl")
    verified_equations = {
        item.get("assertion_id"): item
        for item in equations
        if item["verification_status"] == "verified"
    }

    assert verified_equations["hw-p6-mean-reversion"]["latex"] == (
        r"a(t)=-\frac{\partial^2 B(0,t)/\partial t^2}{\partial B(0,t)/\partial t}"
    )
    assert all(item.get("assertion_id") for item in verified_equations.values())
    assert any(item["verification_status"] == "unverified" for item in equations)
    assert all(item["latex_compile_status"] == "passed" for item in equations)
    assert all(
        item["render_validation_status"] == "passed"
        and (output / item["render_asset"]).is_file()
        and item["source_comparison_status"] == "manual_review_pass"
        for item in verified_equations.values()
    )
    cells = {item.get("assertion_id"): item for table in tables for item in table["cells"]}
    assert cells["hw-p17-table3-ext-vas-200-100"]["extractor_raw_text"] == "132"
    assert cells["hw-p17-table3-ext-vas-200-100"]["raw_text"] == "1.32"
    assert cells["hw-p17-table3-ext-vas-200-100"]["numeric_value"] == 1.32
    assert cells["hw-p17-table4-cir-200-100"]["extractor_raw_text"] == "0.06"
    assert cells["hw-p17-table4-cir-200-100"]["raw_text"] == "0.86"
    assert cells["hw-p17-table4-cir-200-100"]["numeric_value"] == 0.86
    assert result["quality"]["overall_status"] == "missing"
    assert result["quality"]["counts"]["compiled_equations"] == len(equations)
    assert all((output / item["source_asset"]).is_file() for item in equations)


def test_japanese_vertical_notice_fails_closed_on_text_and_reading_order(tmp_path):
    output = tmp_path / MOF_NOTICE

    result = convert_mineru_paper(
        paper_id=MOF_NOTICE,
        source_pdf=REFERENCES_ROOT / "papers" / f"{MOF_NOTICE}.pdf",
        mineru_root=GOLD_MINERU_ROOT,
        output_dir=output,
        page_mapping=MOF_NOTICE_GOLD_PAGES,
    )
    pages = _read_jsonl(output / "pages.jsonl")

    assert result["quality"]["text_status"] == "fail"
    assert result["quality"]["layout_status"] == "review"
    assert result["quality"]["low_text_coverage_pages"] == [2, 6]
    assert all(page["reading_order_status"] == "review" for page in pages)


def test_conversion_is_byte_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    kwargs = {
        "paper_id": HULL_WHITE,
        "source_pdf": REFERENCES_ROOT / "papers" / f"{HULL_WHITE}.pdf",
        "mineru_root": GOLD_MINERU_ROOT,
        "page_mapping": HULL_WHITE_GOLD_PAGES,
    }

    convert_mineru_paper(output_dir=first, **kwargs)
    convert_mineru_paper(output_dir=second, **kwargs)
    first_files = {
        path.relative_to(first): path.read_bytes() for path in first.rglob("*") if path.is_file()
    }
    second_files = {
        path.relative_to(second): path.read_bytes() for path in second.rglob("*") if path.is_file()
    }

    assert first_files == second_files
