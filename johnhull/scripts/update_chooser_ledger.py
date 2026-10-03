"""Register §26.8 only after the M25 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M25_CHECK = "docs/validation/section-26-8/m25-check.json"
EARLIER = [
    "26.1",
    "26.2",
    "26.3",
    "26.4",
    "26.5",
    "26.6",
    "26.7",
    *[f"26.{n}" for n in range(9, 18)],
    *[f"27.{n}" for n in range(1, 9)],
]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m25_gate() -> None:
    path = PROJECT / M25_CHECK
    if not path.is_file():
        raise ValueError("M25 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "26.8"
        or record.get("milestone") != "M25"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M25 acceptance record is not passing")
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_chooser_acceptance_record.py"),
            "--check",
        ],
        cwd=PROJECT.parent,
        check=True,
    )


def m25_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M25_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M25 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M25 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M25 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M25 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    for key in tuple(evidence):
        if key.startswith("m") and key[1:3].isdigit() and key.endswith(("_check", "_recheck")):
            evidence.pop(key)
    record = m25_record(section["id"])
    evidence["m25_check"] = item(M25_CHECK, "record")
    evidence["m25_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M25_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                "m25_check"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_check")
                else "m25_recheck"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_recheck")
                else ref
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m25_recheck" not in refs:
            refs.append("m25_recheck")


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
        "id": f"CH{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m25_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_chooser(section: dict) -> None:
    base = "docs/validation/section-26-8/"
    paths = {
        "review": ("docs/SECTION_26_8_REVIEW_2026-10-03.md", "note"),
        "acceptance_note": ("docs/SECTION_26_8_ACCEPTANCE_2026-10-03.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/chooser.py", "source"),
        "bsm": ("hullkit/src/hullkit/bsm.py", "source"),
        "pricing_tests": ("hullkit/tests/test_chooser.py", "test"),
        "reference_builder": ("scripts/build_chooser_reference.py", "source"),
        "reference_tests": ("hullkit/tests/test_chooser_reference.py", "test"),
        "reference": (base + "reference.json", "reference"),
        "numerical_script": ("scripts/verify_chooser_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_chooser_numerics.py", "test"),
        "numerical": (base + "numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_chooser_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_chooser_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_chooser_notebook.py", "test"),
        "notebook_script": ("scripts/verify_chooser_notebook.py", "source"),
        "notebook_check": (base + "notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "browser_script": ("scripts/verify_chooser_browser.cjs", "source"),
        "browser_run": (base + "browser-check.json", "record"),
        "m25_check": (M25_CHECK, "record"),
        "threshold_image": (base + "portal-chooser_choice-1000.png", "image"),
        "strikes_image": (base + "portal-chooser_package-1000.png", "image"),
        "timing_image": (base + "portal-chooser_timing-1000.png", "image"),
        "validation_image": (base + "portal-chooser_validation-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-10-03",
        source_pages=[619, 620],
        scope="Hull GE §26.8のsimple chooser。同じK/T2の欧州call/putをT1で選ぶ価値、配当調整複製、独立条件付き求積をvol10 §4.15とBook/portalで照合。",
        assumptions=[
            "定数r,q,σのGBM、連続利回りq。T1は選択、選んだvanilla給付はT2で決済。",
            "S,K>0,σ≥0,0≤T1≤T2、有限実数・市場broadcast。scalar float/array ndarray。",
            "原典に印刷数値例なし。全価格合成、独立erfc vanillaとT1密度求積64ケース、条件付きMC524288経路×4。",
            "T1=0/T1=T2/σ=0/T2=0は正確な限界。選択境界H=K exp(−(r−q)(T2−T1))、put枚数w=exp(−q(T2−T1))。",
        ],
        limitations=[
            "simple European chooser・定数GBMのみ。異なるstrike/満期のcomplex chooser、American、smile、確率的金利/変動率、離散配当、取引費用は対象外。",
            "入力や中間計算が表現不能ならValueError。恣意的なrate上限を置かない。",
            "MCはT1 spotと条件付き選択vanilla価値。95%区間は平均の標本誤差で、求積/モデル誤差を含まない。",
        ],
        acceptance_note="docs/SECTION_26_8_ACCEPTANCE_2026-10-03.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "同じK/T2のcall/put、T1の選択価値max(c1,p1)とT2給付を説明する。",
                "vol10 §4.15.1–2",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["threshold_image"],
                "両画面でT1条件付き価値と選択境界を照合",
            ),
            requirement(
                2,
                "parityによる境界Hとcall/putの選択領域を実装する。",
                "vol10 §4.15.2–3",
                ["pricing", "bsm", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["threshold_image", "strikes_image"],
                "両画面でHと選択価値を照合",
            ),
            requirement(
                3,
                "T2 call一枚とT1のstrike Hのputをw枚持つ配当調整複製を実装する。",
                "vol10 §4.15.3",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "numerical_tests"],
                ["strikes_image"],
                "両画面のcall/追加put/chooserを照合",
            ),
            requirement(
                4,
                "即時選択/満期選択/zeroσ/zero満期/broadcast、bounds・同次性を検証する。",
                "vol10 §4.15.4・6",
                ["pricing", "bsm", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["timing_image"],
                "両画面のT1=0とT1=T2、選択時期曲線を照合",
            ),
            requirement(
                5,
                "独立求積64例とMC4例、狭い遷移の分割、有限値と保存改変/実API変異を検査する。",
                "vol10 §4.15.5–6",
                ["pricing", "reference_builder"],
                ["reference", "numerical", "reference_tests", "numerical_tests"],
                ["validation_image"],
                "4選択時期の求積/MC95%誤差棒と価格改変拒否",
            ),
            requirement(
                6,
                "6小節・4共有図、旧202セル、既受入24節のD1と両画面16状態を再検査する。",
                "vol10 §4.15とBook/portal",
                ["builder", "lesson", "portal"],
                ["numerical", "notebook_check", "notebook_tests"],
                ["threshold_image", "strikes_image", "timing_image", "validation_image"],
                "16状態・notebook4改変・旧24節D1と両保管庫",
            ),
        ],
    )


def main() -> None:
    require_m25_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "26.8":
            register_chooser(section)
            seen.add(section["id"])
    expected = {*EARLIER, "26.8"}
    if seen != expected:
        raise ValueError(f"M25 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.8 and twenty-four earlier sections for M25")


if __name__ == "__main__":
    main()
