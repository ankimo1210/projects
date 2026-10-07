"""A lighter acceptance profile still rejects incomplete or stale evidence."""

import copy

import pytest

from johnhull.scripts import fast_acceptance as fast


def controls(monkeypatch):
    """Use a small valid numerical/rendering contract with file I/O isolated."""
    cfg = {
        "sections": [
            {
                "id": "2.4",
                "requirements": [{"id": "D2.4-01"}],
                "tests": ["hullkit/tests/independent.py"],
            }
        ],
        "template_sha256": "template",
        "expected_dom": {"section-2-4": {"text_sha256": "content", "math": ["F=S"], "tables": 1}},
    }
    numerical = {
        "status": "PASS",
        "source_sha256": {"input": "sha"},
        "artifact_sha256": {"output": "sha"},
        "tests": ["johnhull/hullkit/tests/independent.py"],
        "exit_code": 0,
    }
    browser = {
        "status": "PASS",
        "source_sha256": {"input": "sha"},
        "artifact_sha256": {"output": "sha"},
        "sections": {
            "2.4": {
                "requirements": ["D2.4-01"],
                "explanation_checked": True,
                "math_checked": True,
                "layout_checked": True,
                "links_checked": True,
                "text_sha256": "content",
                "math": 1,
                "tables": 1,
            }
        },
        "captures": [{"section": sid} for sid in fast.SAMPLE.values()],
        "missing_requirement_rejected": True,
        "mutated_requirement_rejected": True,
    }
    monkeypatch.setattr(fast, "digest", lambda name: "sha")
    monkeypatch.setattr(fast, "inputs", lambda cfg: ["input"])
    original = copy.deepcopy(cfg["sections"])
    monkeypatch.setattr(fast, "sections", lambda: original)
    import hashlib

    cfg["template_sha256"] = hashlib.sha256(
        (fast.PROJECT.parent / "docs/templates/claude-report/tokens.css").read_bytes()
    ).hexdigest()
    return cfg, numerical, browser


def test_complete_fast_contract(monkeypatch):
    fast.validate(*controls(monkeypatch))


@pytest.mark.parametrize(
    "mutation",
    [
        "failed_test",
        "missing_test",
        "missing_source",
        "missing_section",
        "missing_requirement",
        "duplicate_requirement",
        "unchecked_math",
        "unchecked_layout",
        "missing_capture",
        "duplicate_capture",
        "no_negative_control",
        "stale",
        "both_drop_section",
        "both_drop_requirement",
        "math_removed",
        "table_removed",
        "prose_changed",
        "no_prose_control",
    ],
)
def test_failed_incomplete_or_stale_evidence_is_rejected(monkeypatch, mutation):
    cfg, numerical, browser = copy.deepcopy(controls(monkeypatch))
    if mutation == "failed_test":
        numerical["exit_code"] = 1
    elif mutation == "missing_test":
        numerical["tests"] = []
    elif mutation == "missing_source":
        numerical["source_sha256"] = {"other": "sha"}
    elif mutation == "missing_section":
        browser["sections"] = {}
    elif mutation == "missing_requirement":
        browser["sections"]["2.4"]["requirements"] = []
    elif mutation == "duplicate_requirement":
        browser["sections"]["2.4"]["requirements"].append("D2.4-01")
    elif mutation == "unchecked_math":
        browser["sections"]["2.4"]["math_checked"] = False
    elif mutation == "unchecked_layout":
        browser["sections"]["2.4"]["layout_checked"] = False
    elif mutation == "missing_capture":
        browser["captures"].pop()
    elif mutation == "duplicate_capture":
        browser["captures"][-1] = browser["captures"][0]
    elif mutation == "no_negative_control":
        browser["missing_requirement_rejected"] = False
    elif mutation == "both_drop_section":
        cfg["sections"] = []
        browser["sections"] = {}
    elif mutation == "both_drop_requirement":
        cfg["sections"][0]["requirements"] = []
        browser["sections"]["2.4"]["requirements"] = []
    elif mutation == "math_removed":
        browser["sections"]["2.4"]["math"] = 0
    elif mutation == "table_removed":
        browser["sections"]["2.4"]["tables"] = 0
    elif mutation == "prose_changed":
        browser["sections"]["2.4"]["text_sha256"] = "wrong"
    elif mutation == "no_prose_control":
        browser["mutated_requirement_rejected"] = False
    else:
        numerical["source_sha256"]["input"] = "old"
    with pytest.raises(ValueError):
        fast.validate(cfg, numerical, browser)


def test_original_inventory_and_all_numerical_sections_are_mapped():
    rows = fast.sections()
    assert len(rows) == 70
    assert len([r for r in rows if r["tests"]]) == 49
    assert all(r["explanation"] and r["requirements"] for r in rows)


def test_input_missing_prices_are_not_claimed_as_reproduced():
    rows = {r["id"]: r for r in fast.sections()}
    assert "割引金利がない" in rows["5.7"]["limitation"]
    assert "Technical Note" in rows["6.3"]["limitation"]
    assert "未検証" in rows["7.8"]["limitation"]
    assert "0.9628" in rows["7.9"]["limitation"]
