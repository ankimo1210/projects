"""Accept Ch16–21 with explicit per-section contracts and frozen fast-v1 checks."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
PROFILE_FILE = "docs/acceptance/fast-ch16-21-profile.json"
PRIOR_PROFILE = "docs/acceptance/fast-ch10-15-profile.json"
GUARD = "report/tests/test_fast_acceptance_advanced_options.py"

# Keep the earlier batch's globals and evidence immutable in the same process.
_spec = importlib.util.spec_from_file_location(
    "_johnhull_advanced_fast_core", PROJECT / "scripts/fast_acceptance_options.py"
)
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)
_prior_inputs = core.inputs
_prior_prose = core.learner_prose
_prior_register = core.register
_prior_validate = core.validate


def configure(name=PROFILE_FILE):
    """Select a recipe declaring modules per section, including tree/MC/FD in Ch21."""
    core.PROFILE_FILE = name
    core.PROFILE = core.read(name)
    for key in ("out", "config", "note", "policy", "details"):
        setattr(core, key.upper(), core.PROFILE[key])
    core.GROUPS = {int(c): None for c in core.PROFILE["chapters"]}
    core.LIMITS = core.PROFILE["limitations"]
    core.SAMPLE = {int(c): s for c, s in core.PROFILE["samples"].items()}
    if set(core.GROUPS) != set(core.SAMPLE):
        raise ValueError("representatives differ from chapter coverage")


def block(body, label):
    """Read both **label:** and **label**: without swallowing adjacent draft fields."""
    match = re.search(r"\*\*" + re.escape(label) + r"[^*\n]*\*\*\s*[:：]?\s*", body)
    if not match:
        return ""
    tail = body[match.end() :]
    stop = re.search(
        r"\n- \*\*|\n\| ID|\n## |\*\*(?:要求の下書き|既存の実装|足りないもの|"
        r"独立参照の案|図の案|依存・注意|規模|関連)[^*\n]*\*\*",
        tail,
    )
    return (tail[: stop.start()] if stop else tail).strip()


def sections():
    """Preserve original IDs/statements and map all numerical sections explicitly."""
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
                r"^\|\s*" + re.escape(sid) + r"\s*\|\s*(\d+)(?:[–−—-](\d+))?", text, re.M
            )
            if not pages:
                raise ValueError("source pages missing: " + sid)
            requirements = []
            for line in body.splitlines():
                if not line.startswith("| D"):
                    continue
                # A literal conditional bar (Fnext|現在) is not a table delimiter.
                cells = re.split(r"\s+\|\s+", line.strip().strip("|").strip())
                if len(cells) != 3:
                    raise ValueError("requirement columns: " + line)
                requirements.append(dict(id=cells[0], statement=cells[1], reading=cells[2]))
            explanation = (
                block(body, "原典の内容") or block(body, "種別・原典の内容") or block(body, "種別")
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
                    filter(None, (block(body, label) for label in ("印刷値", "表の再計算", "成績")))
                ),
                cautions=block(body, "依存・注意"),
                prep=prep,
                lesson=f"docs/lessons/ch{chapter:02}.md",
                page=f"report/site/chapters/ch{chapter:02}.html",
                implementation=contract.get("implementation"),
                tests=contract.get("tests", []),
                limitation=core.LIMITS[sid],
                numerical_requirements=core.PROFILE["numerical_requirements"][sid],
            )
            if contract:
                calculation = core.PROFILE["calculation_rows"].get(sid)
                if not calculation or any(not (PROJECT / n).is_file() for n in row["tests"]):
                    raise ValueError("missing calculation/test contract: " + sid)
                row["calculation"] = calculation[2]
                row["calculation_scope"] = row["limitation"]
            if sid == "16.3":
                row["cautions"] = (
                    "付与日公正価値による認識と、著者の継続再評価案を分ける。本文の付与年全額費用という簡略化を現行の一般則にはしない。"
                )
            if sid == "20.2":
                row["printed"] = (
                    "Table20.1は2005–2015の10通貨。1～6SD超の実測"
                    "23.32/4.67/1.30/.49/.24/.13%、正規31.73/4.55/.27/.01/.00/.00%。"
                    "実測列は原データ不足で未検証。正規列は2Φ(−n)で独立検証した。"
                    "Figs20.1/2は模式図で数値曲線なし。"
                )
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
    return rows


def learner_prose(text):
    """Remove stale draft instructions while preserving unresolved original discrepancies."""
    text = _prior_prose(text)
    text = text.replace("全21行の逐次丸め・組版を後続確認", "元の非丸め入力は不明")
    text = re.sub(r"個別丸め判定(?:は)?未実施", "表示丸め幅で確認", text)
    text = re.sub(r"\*\*D3候補\*\*[^。\n]*。?", "", text)
    text = re.sub(r"(?:詳細は\s*)?\[P8再確認\]\([^)]*\)(?:参照)?。", "", text)
    return text.strip()


def inputs(cfg):
    """Pin the adapter, frozen core/import recipe and actual current guard suites."""
    names = set(_prior_inputs(cfg)) - {"report/tests/test_fast_acceptance_options.py"}
    names.update(("scripts/fast_acceptance_advanced_options.py", PRIOR_PROFILE, GUARD))
    return sorted(names | core.local_dependencies(names))


def test():
    """Run declared calculation and rejection suites and bind their fresh results."""
    cfg = core.read(core.CONFIG)
    suites = sorted(
        {n for row in cfg["sections"] for n in row["tests"]} | set(core.PROFILE["extra_tests"])
    )
    tests = ["johnhull/" + name for name in suites]
    (PROJECT / core.OUT).mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        *tests,
        "--junitxml=" + str(PROJECT / core.OUT / "targeted-tests.xml"),
    ]
    start = time.monotonic()
    result = subprocess.run(
        command, cwd=PROJECT.parent, capture_output=True, text=True, check=False
    )
    (PROJECT / core.OUT / "targeted-tests.log").write_text(result.stdout + result.stderr)
    record = dict(
        status="PASS" if result.returncode == 0 else "FAIL",
        command=command,
        exit_code=result.returncode,
        seconds=round(time.monotonic() - start, 2),
        tests=tests,
        runtime=dict(
            python=sys.version,
            packages={
                p: core.importlib.metadata.version(p)
                for p in ("numpy", "scipy", "markdown-it-py", "mdit-py-plugins")
            },
        ),
        summary=(result.stdout.strip().splitlines() or [result.stderr.strip()])[-1],
        source_sha256=core.hashes(inputs(cfg)),
        artifact_sha256=core.hashes(
            [core.OUT + "/targeted-tests.xml", core.OUT + "/targeted-tests.log"]
        ),
    )
    core.write(core.OUT + "/numerical-check.json", record)
    if result.returncode:
        raise ValueError(record["summary"])
    return dict(status="PASS", summary=record["summary"], seconds=record["seconds"])


def validate(cfg, numerical, browser):
    """Require the recipe's rejection suites as well as section calculation tests."""
    _prior_validate(cfg, numerical, browser)
    extra = {"johnhull/" + name for name in core.PROFILE["extra_tests"]}
    if not extra.issubset(numerical.get("tests", [])):
        raise ValueError("acceptance rejection test coverage incomplete")


def register():
    """Use native registration, then give partial N/A requirements precise reasons."""
    result = _prior_register()
    ledger = copy.deepcopy(core.read("docs/section_ledger.json"))
    reasons = {
        "D16.3-01": "会計制度史と著者の再評価案の説明を確認する。報酬の算術は別要件D16.3-02で検証し、現行会計の適用判断は対象外。",
        "D16.5-02": "研究の観測と因果・制度史を説明する。因果推定や現在の法的判断は検証対象外。8ドルの算術は別要件で検証する。",
        "D20.2-02": "原典Table20.1の実測FX標本がなく歴史列の再計算は未検証。今回は説明と正規列の方法を確認する。実測の再現をverifiedとはしない。",
    }
    for row in ledger["sections"]:
        if row["id"] not in core.PROFILE["numerical_requirements"]:
            continue
        for req in row["requirements"]:
            if req["id"] in reasons:
                for axis in ("implementation", "independent_validation"):
                    if req["coverage"][axis]["state"] != "not_applicable":
                        raise ValueError("partial N/A became numerical: " + req["id"])
                    req["coverage"][axis]["reason"] = reasons[req["id"]]
    from johnhull.scripts.verify_section_ledger import evaluate_ledger

    checked = evaluate_ledger(PROJECT, core.read("docs/section_inventory.json"), ledger)
    if checked["status"] != "PASS":
        raise ValueError("partial-scope ledger invalid: " + str(checked["errors"]))
    core.write("docs/section_ledger.json", ledger)
    return result


core.configure = configure
core.block = block
core.sections = sections
core.learner_prose = learner_prose
core.inputs = inputs
core.test = test
core.validate = validate
core.register = register
configure()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("build", "test", "check", "register", "verify"))
    parser.add_argument("--profile", default=PROFILE_FILE)
    args = parser.parse_args()
    configure(args.profile)
    print(json.dumps(getattr(core, args.phase)(), ensure_ascii=False))
