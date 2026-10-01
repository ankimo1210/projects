"""Register §26.7 only after the M24 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M24_CHECK = "docs/validation/section-26-7/m24-check.json"
EARLIER = [
    "26.1",
    "26.2",
    "26.3",
    "26.4",
    "26.5",
    "26.6",
    *[f"26.{n}" for n in range(9, 18)],
    *[f"27.{n}" for n in range(1, 9)],
]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m24_gate() -> None:
    path = PROJECT / M24_CHECK
    if not path.is_file():
        raise ValueError("M24 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "26.7"
        or record.get("milestone") != "M24"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M24 acceptance record is not passing")
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_compound_acceptance_record.py"),
            "--check",
        ],
        cwd=PROJECT.parent,
        check=True,
    )


def m24_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M24_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M24 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M24 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M24 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M24 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    for key in tuple(evidence):
        if key.startswith("m") and key[1:3].isdigit() and key.endswith(("_check", "_recheck")):
            evidence.pop(key)
    record = m24_record(section["id"])
    evidence["m24_check"] = item(M24_CHECK, "record")
    evidence["m24_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M24_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                "m24_check"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_check")
                else "m24_recheck"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_recheck")
                else ref
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m24_recheck" not in refs:
            refs.append("m24_recheck")


def requirement(
    number: int,
    statement: str,
    locator: str,
    implementation: list[str],
    validation: list[str],
    figures: list[str],
    rendered: str,
) -> dict:
    return {
        "id": f"CO{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m24_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_compound(section: dict) -> None:
    base = "docs/validation/section-26-7/"
    paths = {
        "review": ("docs/SECTION_26_7_REVIEW_2026-10-01.md", "note"),
        "acceptance_note": ("docs/SECTION_26_7_ACCEPTANCE_2026-10-01.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/compound.py", "source"),
        "bsm": ("hullkit/src/hullkit/bsm.py", "source"),
        "pricing_tests": ("hullkit/tests/test_compound.py", "test"),
        "reference_builder": ("scripts/build_compound_reference.py", "source"),
        "reference_tests": ("hullkit/tests/test_compound_reference.py", "test"),
        "reference": (base + "reference.json", "reference"),
        "numerical_script": ("scripts/verify_compound_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_compound_numerics.py", "test"),
        "numerical": (base + "numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_compound_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_compound_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_compound_notebook.py", "test"),
        "notebook_script": ("scripts/verify_compound_notebook.py", "source"),
        "notebook_check": (base + "notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "browser_script": ("scripts/verify_compound_browser.cjs", "source"),
        "browser_run": (base + "browser-check.json", "record"),
        "m24_check": (M24_CHECK, "record"),
        "threshold_image": (base + "portal-compound_threshold-1000.png", "image"),
        "strikes_image": (base + "portal-compound_strikes-1000.png", "image"),
        "timing_image": (base + "portal-compound_timing-1000.png", "image"),
        "validation_image": (base + "portal-compound_validation-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-10-01",
        source_pages=[618, 619],
        scope="Hull GE §26.7の欧州型4コンパウンド契約。T1外側給付、内側vanilla臨界株価、4Geske公式と独立条件付き求積をvol10 §4.14とBook/portalで照合。",
        assumptions=[
            "定数r,q,σのGBM。外側call/putはT1で内側欧州call/put価値とK1を比較、内側strike K2と満期T2。",
            "S,K2>0,K1≥0,σ≥0,0<T1<T2、有限実数・市場broadcast。scalar float/array ndarray。",
            "原典に印刷数値例はない。全価格合成、独立erfc vanillaとT1密度求積104ケース、条件付きMC524288経路×4。",
            "K1=0とzeroσは正確な限界。内側put上限以上のK1では根なしでも有効な価格。",
        ],
        limitations=[
            "欧州型・定数GBMのみ。American exercise、smile、確率的金利/変動率、取引費用は対象外。",
            "T1をT2と同日にする契約は対象外。T1/T2=.9999までの参照を含む。",
            "極端に近い有効日付（例T1/T2=.999999999999）では二変量積分が警告後ValueErrorで停止することがある。独立レビューのMinorとして保留。",
            "MCはT1 spot samplingと内側vanilla条件付き価値。二重MCではない。95%区間は平均の標本誤差で、求積/モデル誤差を含まない。",
        ],
        acceptance_note="docs/SECTION_26_7_ACCEPTANCE_2026-10-01.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "4契約・K1/K2・T1/T2とT1外側給付を説明する。",
                "vol10 §4.14.1–2",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["threshold_image"],
                "両画面の内側2価値・外側4給付を照合",
            ),
            requirement(
                2,
                "内側価値=K1の臨界株価、内側call/putの行使領域、putの根なし領域を実装する。",
                "vol10 §4.14.2–3",
                ["pricing", "bsm", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["threshold_image", "strikes_image"],
                "両画面で2根と内側put上限を照合",
            ),
            requirement(
                3,
                "S*とK2の閾値・相関の符号を区別し、Hullの4Geske公式を直接評価する。",
                "vol10 §4.14.3–4",
                ["pricing", "builder"],
                ["reference", "numerical", "numerical_tests"],
                ["strikes_image", "timing_image"],
                "両画面の4価格とT1曲線を照合",
            ),
            requirement(
                4,
                "K1=0/zeroσ/broadcastとput-call parity/通貨同次性/近接日付を検証する。",
                "vol10 §4.14.3–4・6",
                ["pricing", "bsm", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["strikes_image", "timing_image"],
                "両画面のK1=0とT1=.9999を照合",
            ),
            requirement(
                5,
                "独立条件付き求積104例とMC4例、有限値と4保存改変/4実API変異拒否を検査する。",
                "vol10 §4.14.5–6",
                ["pricing", "reference_builder"],
                ["reference", "numerical", "reference_tests", "numerical_tests"],
                ["validation_image"],
                "4契約の求積/MC95%誤差棒と価格改変拒否",
            ),
            requirement(
                6,
                "6小節・4共有図、旧191セル、既受入23節のD1と両画面16状態を再検査する。",
                "vol10 §4.14とBook/portal",
                ["builder", "lesson", "portal"],
                ["numerical", "notebook_check", "notebook_tests"],
                ["threshold_image", "strikes_image", "timing_image", "validation_image"],
                "16状態・notebook4改変・旧23節D1と両保管庫",
            ),
        ],
    )


def main() -> None:
    require_m24_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "26.7":
            register_compound(section)
            seen.add(section["id"])
    expected = {*EARLIER, "26.7"}
    if seen != expected:
        raise ValueError(f"M24 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.7 and twenty-three earlier sections for M24")


if __name__ == "__main__":
    main()
