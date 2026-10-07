"""Accept the final Ch29–37 batch while preserving all earlier evidence."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
PROFILE_FILE = "docs/acceptance/fast-ch29-37-profile.json"
PRIOR_PROFILE = "docs/acceptance/fast-ch22-25-profile.json"
GUARD = "report/tests/test_fast_acceptance_final.py"

_spec = importlib.util.spec_from_file_location(
    "_johnhull_final_fast_core", PROJECT / "scripts/fast_acceptance_risk_credit.py"
)
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)
engine.engine.GUARD = GUARD
core = engine.core
_prior_inputs = core.inputs
_prior_register = core.register
_prior_reading = core.requirement_reading
_prior_prose = core.learner_prose


def sections():
    """Read original requirements from page tables or the chapter's headings."""
    rows = []
    contracts = core.PROFILE["section_contracts"]
    for chapter in core.GROUPS:
        prep = f"docs/prep/sections/ch{chapter:02}.md"
        text = (PROJECT / prep).read_text()
        matches = list(re.finditer(r"^## §(\d+\.(?:\d+|appendix)) ([^\n]+)", text, re.M))
        for i, match in enumerate(matches):
            sid, heading = match.groups()
            body = text[match.end() : matches[i + 1].start() if i + 1 < len(matches) else len(text)]
            body = body.split("\n## 申し送り", 1)[0]
            pages = re.search(
                r"^\|\s*§?" + re.escape(sid) + r"(?:\s[^|]*)?\s*\|\s*(\d+)(?:[–−—-](\d+))?",
                text,
                re.M,
            )
            if not pages:
                pages = re.search(r"[（(]pp?\.\s*(\d+)(?:[–−—-](\d+))?", heading)
            if not pages:
                raise ValueError("source pages missing: " + sid)
            requirements = []
            for line in body.splitlines():
                if line.startswith("| D"):
                    cells = re.split(r"\s+\|\s+", line.strip().strip("|").strip())
                    if len(cells) != 3:
                        raise ValueError("requirement columns: " + line)
                    requirements.append(dict(id=cells[0], statement=cells[1], reading=cells[2]))
            explanation = (
                core.block(body, "原典の内容")
                or core.block(body, "種別・原典の内容")
                or core.block(body, "種別")
            )
            if not explanation or not requirements:
                raise ValueError("empty lesson: " + sid)
            contract = contracts.get(sid, {})
            row = dict(
                id=sid,
                chapter=chapter,
                heading=heading,
                source_pages=[int(pages[1]), int(pages[2] or pages[1])],
                requirements=requirements,
                explanation=explanation,
                printed="\n\n".join(
                    filter(
                        None,
                        (core.block(body, label) for label in ("印刷値", "表の再計算", "成績")),
                    )
                ),
                # Current limits/supplements retain the substantive caveats;
                # the draft's obsolete research tickets are not learner prose.
                cautions="",
                prep=prep,
                lesson=f"docs/lessons/ch{chapter:02}.md",
                page=f"report/site/chapters/ch{chapter:02}.html",
                implementation=contract.get("implementation"),
                tests=contract.get("tests", []),
                limitation=core.LIMITS[sid],
                numerical_requirements=core.PROFILE["numerical_requirements"][sid],
            )
            row["printed"] = core.PROFILE.get("printed_overrides", {}).get(sid, row["printed"])
            if contract:
                calculation = core.PROFILE["calculation_rows"].get(sid)
                if not calculation or any(not (PROJECT / n).is_file() for n in row["tests"]):
                    raise ValueError("missing calculation/test contract: " + sid)
                row["calculation"] = calculation[2]
                row["calculation_scope"] = row["limitation"]
            ids = {r["id"] for r in requirements}
            numeric = set(row["numerical_requirements"])
            if (
                len(ids) != len(requirements)
                or not numeric <= ids
                or (numeric and not row["tests"])
            ):
                raise ValueError("invalid numerical requirement mapping: " + sid)
            rows.append(row)
    wanted = {
        r["id"]
        for r in core.read("docs/section_inventory.json")["entries"]
        if r["chapter"] in core.GROUPS
    }
    if {r["id"] for r in rows} != wanted or set(contracts) != {r["id"] for r in rows if r["tests"]}:
        raise ValueError("inventory/contract coverage differs")
    explanatory = {
        req["id"]
        for row in rows
        for req in row["requirements"]
        if req["id"] not in row["numerical_requirements"]
    }
    if explanatory != set(core.PROFILE["non_numerical_reasons"]):
        raise ValueError("explanatory scopes differ from original requirements")
    return rows


def inputs(cfg):
    """Pin extra suites, their local dependencies and both frozen adapters."""
    names = set(_prior_inputs(cfg))
    names.update(("scripts/fast_acceptance_final.py", PRIOR_PROFILE))
    names.update(core.PROFILE["additional_inputs"])
    names.update(core.PROFILE["extra_tests"])
    return sorted(names | core.local_dependencies(names))


def requirement_reading(req):
    """Clarify the malformed currency/math delimiter without changing its source."""
    if req["id"] == "D22.6-03":
        return "同じbookの10日全再評価VaRと $\\sqrt{10}$ 倍した1日VaRを比較する。"
    return _prior_reading(req)


def learner_prose(text):
    """Preserve missing-data caveats through the frozen draft-term sanitizer."""
    text = text.replace("未再計算", "未検証")
    text = text.replace("mapping", "MAPPINGTERM")
    text = _prior_prose(text).replace("MAPPINGTERM", "mapping")
    text = re.sub(r"(?m)^#{2,6}\s*要求の下書き\s*$", "", text)
    text = text.replace("****", "")
    text = text.replace("未固定値。", "")
    text = re.sub(r"`check_[a-z0-9_]+\.py`\s*で\s*", "", text)
    text = text.replace(
        "数値固定値は TN10 が PDF の外にあるので blocked（VN-09）。",
        "TN10の配布PDFは未取得。公式索引の数値例と独立計算は下記で区別する。",
    )
    return text.strip()


def register():
    """Register native evidence and explain every non-numerical requirement."""
    result = _prior_register()
    ledger = copy.deepcopy(core.read("docs/section_ledger.json"))
    reasons = core.PROFILE["non_numerical_reasons"]
    for row in ledger["sections"]:
        if row["id"] in core.PROFILE["numerical_requirements"]:
            for req in row["requirements"]:
                if req["id"] in reasons:
                    for axis in ("implementation", "independent_validation"):
                        if req["coverage"][axis]["state"] != "not_applicable":
                            raise ValueError(
                                "explanatory requirement became numerical: " + req["id"]
                            )
                        req["coverage"][axis]["reason"] = reasons[req["id"]]
    from johnhull.scripts.verify_section_ledger import evaluate_ledger

    checked = evaluate_ledger(PROJECT, core.read("docs/section_inventory.json"), ledger)
    if checked["status"] != "PASS":
        raise ValueError("partial-scope ledger invalid: " + str(checked["errors"]))
    for row in ledger["sections"]:
        if row["id"] in core.PROFILE["numerical_requirements"]:
            row["reviewed_at"] = "2026-10-08"
    core.write("docs/section_ledger.json", ledger)
    return result


_prior_build = core.build


def build():
    """Keep legacy Ch26–28 links at their existing accepted portal locations."""
    result = _prior_build()
    for chapter in core.GROUPS:
        name = PROJECT / f"report/site/chapters/ch{chapter:02}.html"
        text = name.read_text()
        for old, target in core.PROFILE["legacy_navigation"].items():
            text = text.replace(f'href="ch{int(old):02}.html"', f'href="{target}"')
        name.write_text(text)
    return result


core.sections = sections
core.build = build
core.inputs = inputs
# The frozen runner resolves inputs in its adapter namespace, too.
engine.engine.inputs = inputs
core.requirement_reading = requirement_reading
core.learner_prose = learner_prose
core.register = register
core.configure(PROFILE_FILE)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("build", "test", "check", "register", "verify"))
    parser.add_argument("--profile", default=PROFILE_FILE)
    args = parser.parse_args()
    core.configure(args.profile)
    print(json.dumps(getattr(core, args.phase)(), ensure_ascii=False))
