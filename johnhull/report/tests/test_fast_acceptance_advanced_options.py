"""A lighter acceptance profile still rejects incomplete or stale evidence."""

import copy

import pytest

from johnhull.scripts.fast_acceptance_advanced_options import core as fast


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
        "tests": ["johnhull/hullkit/tests/independent.py"]
        + ["johnhull/" + name for name in fast.PROFILE["extra_tests"]],
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


def test_currency_before_formulas_does_not_consume_math_delimiters():
    source = (
        r"株価$10 でも $50 でも $dS=\mu Sdt+\sigma SdW$。$1/52=0.0192$、$400\times3=\$1,200$。"
        r"$60-$40=$20、$1×80%=$.80。"
    )
    rendered = fast.markdown_renderer().render(fast.protect_math(source))
    assert rendered.count("data-source-tex=") == 3
    assert "株価$10 でも $50 でも" in rendered
    assert r"dS=\mu Sdt+\sigma SdW" in rendered
    assert r"\,1/52=0.0192" in rendered
    assert r"\,400\times3=\$1,200" in rendered
    assert "$60-$40=$20、$1×80%=$.80。" in rendered


@pytest.mark.parametrize(
    "mutation",
    [
        "failed_test",
        "missing_test",
        "missing_extra_test",
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
    elif mutation == "missing_extra_test":
        extra = {"johnhull/" + name for name in fast.PROFILE["extra_tests"]}
        numerical["tests"] = [name for name in numerical["tests"] if name not in extra]
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
    assert len(rows) == 54
    assert len([r for r in rows if r["tests"]]) == 46
    assert all(r["explanation"] and r["requirements"] for r in rows)


def test_original_scopes_preserve_rounding_and_model_limitations():
    rows = {r["id"]: r for r in fast.sections()}
    assert "262.41331" in rows["19.4"]["limitation"]
    assert "未検証" in rows["19.11"]["limitation"]
    assert "原データ" in rows["20.2"]["limitation"]
    assert "49.885736" in rows["20.8"]["limitation"]
    assert "Tables21.1/2" in rows["21.6"]["limitation"]
    assert rows["16.3"]["numerical_requirements"] == ["D16.3-02"]
    assert not rows["16.1"]["numerical_requirements"]
    assert "Fnext|現在" in rows["18.6"]["requirements"][0]["statement"]


def test_prior_batch_engine_remains_in_its_own_namespace():
    from johnhull.scripts import fast_acceptance_options as prior

    assert prior is not fast
    assert len(prior.sections()) == 58
    assert prior.PROFILE_FILE == "docs/acceptance/fast-ch10-15-profile.json"


def test_ch21_declares_tree_mc_and_fd_per_section():
    rows = {r["id"]: r for r in fast.sections()}
    assert rows["21.1"]["implementation"].endswith("_numerical_trees.py")
    assert rows["21.6"]["implementation"].endswith("_numerical_mc.py")
    assert rows["21.8"]["implementation"].endswith("_numerical_fd.py")
    assert len({n for r in rows.values() for n in r["tests"]}) == 46
