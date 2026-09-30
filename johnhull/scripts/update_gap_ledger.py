"""Register §26.4 only after the M21 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M21_CHECK = "docs/validation/section-26-4/m21-check.json"
EARLIER = [
    "26.1",
    "26.2",
    "26.3",
    *[f"26.{n}" for n in range(9, 18)],
    *[f"27.{n}" for n in range(1, 9)],
]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m21_gate() -> None:
    path = PROJECT / M21_CHECK
    if not path.is_file():
        raise ValueError("M21 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "26.4"
        or record.get("milestone") != "M21"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M21 acceptance record is not passing")
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_gap_acceptance_record.py"),
            "--check",
        ],
        cwd=PROJECT.parent,
        check=True,
    )


def m21_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M21_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M21 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M21 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M21 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M21 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    for key in tuple(evidence):
        if key.startswith("m") and key[1:3].isdigit() and key.endswith(("_check", "_recheck")):
            evidence.pop(key)
    record = m21_record(section["id"])
    evidence["m21_check"] = item(M21_CHECK, "record")
    evidence["m21_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M21_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                "m21_check"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_check")
                else "m21_recheck"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_recheck")
                else ref
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m21_recheck" not in refs:
            refs.append("m21_recheck")


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
        "id": f"GP{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m21_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_gap(section: dict) -> None:
    base = "docs/validation/section-26-4/"
    paths = {
        "review": ("docs/SECTION_26_4_REVIEW_2026-10-01.md", "note"),
        "acceptance_note": ("docs/SECTION_26_4_ACCEPTANCE_2026-10-01.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/exotics.py", "source"),
        "bsm": ("hullkit/src/hullkit/bsm.py", "source"),
        "pricing_tests": ("hullkit/tests/test_exotics.py", "test"),
        "reference_builder": ("scripts/build_gap_reference.py", "source"),
        "reference_tests": ("hullkit/tests/test_gap_reference.py", "test"),
        "reference": (base + "reference.json", "reference"),
        "numerical_script": ("scripts/verify_gap_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_gap_numerics.py", "test"),
        "numerical": (base + "numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_gap_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_gap_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_gap_notebook.py", "test"),
        "notebook_script": ("scripts/verify_gap_notebook.py", "source"),
        "notebook_check": (base + "notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "browser_script": ("scripts/verify_gap_browser.cjs", "source"),
        "browser_run": (base + "browser-check.json", "record"),
        "m21_check": (M21_CHECK, "record"),
        "payoff_image": (base + "portal-gap_payoff-1000.png", "image"),
        "decomposition_image": (base + "portal-gap_decomposition-1000.png", "image"),
        "insurance_image": (base + "portal-gap_insurance-1000.png", "image"),
        "premium_image": (base + "portal-gap_premium-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-10-01",
        source_pages=[617, 617],
        scope=(
            "Hull GE §26.4のギャップ・オプション。トリガーと決済額、符号付き給付、バニラと現金バイナリの分解、"
            "Example26.1の保険料と費用負担を独立求積で照合する。vol10 §4.11とBook/portal実画面。"
        ),
        assumptions=[
            "定数r,q,σのGBM。正のspot・両行使価格・変動率・満期を対象とする。",
            "原典Example26.1はS=500000、K1=400000、r=5%、q=0、σ=20%、T=1。その他の市場条件は合成例。",
            "トリガーは厳密不等号で、S_T=K2の給付は0。価格parityは連続分布のもとで成立する。",
        ],
        limitations=[
            "負の給付を0へ切り上げない。符号付き契約は一般のロング・オプションと異なる負の価格を取り得る。",
            "実市場較正、契約者の行動モデル、移転費用の確率変動、信用リスクは検証しない。",
        ],
        acceptance_note="docs/SECTION_26_4_ACCEPTANCE_2026-10-01.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "コールとプットの決済額K1とトリガーK2を分離し、厳密不等号と給付の跳びを示す。",
                "vol10 §4.11.1–4.11.2：契約と給付",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "reference_tests"],
                ["payoff_image"],
                "Book/portalで負の給付・一側極限・トリガー点0を確認",
            ),
            requirement(
                2,
                "バニラと現金バイナリの分解、同一行使価格の極限、価格parityを確認し負の給付を維持する。",
                "vol10 §4.11.3：価格公式と分解",
                ["pricing", "bsm", "lesson"],
                ["reference", "numerical", "numerical_tests"],
                ["payoff_image", "decomposition_image"],
                "Book/portalで決済額の掃引と符号付き価格を確認",
            ),
            requirement(
                3,
                "Example26.1の印刷価格3436・1896ドルと約45%の保険料減を整数ドル丸めで照合する。",
                "vol10 §4.11.4：保険契約の原典例",
                ["pricing", "reference_builder", "builder"],
                ["reference", "numerical", "reference_tests"],
                ["insurance_image", "premium_image"],
                "Book/portalの本文・実行出力・保険料を照合",
            ),
            requirement(
                4,
                "保険会社の経済的支出、契約者の費用控除後手取り、移転費用の割引期待額を区別する。",
                "vol10 §4.11.4–4.11.5：移転費用と両当事者",
                ["reference_builder", "lesson", "builder"],
                ["reference", "numerical", "numerical_tests"],
                ["insurance_image", "premium_image"],
                "Book/portalで支出・手取りとその差を確認",
            ),
            requirement(
                5,
                "独立対数正規求積で合成call/putと価格曲線を照合し、価格・トリガー・費用負担・給付の改変を拒否する。",
                "vol10 §4.11.6：独立検証と前提",
                ["pricing", "reference_builder"],
                ["reference", "numerical", "numerical_tests"],
                ["decomposition_image"],
                "Book/portalの表示値を保存参照と比較し数値改変を拒否",
            ),
            requirement(
                6,
                "6小節・共有4図、旧158セル、既受入20節、両画面の16状態を再検証する。",
                "vol10 §4.11とBook/portalの共有図",
                ["builder", "lesson", "portal"],
                ["numerical", "notebook_check", "notebook_tests"],
                ["payoff_image", "decomposition_image", "insurance_image", "premium_image"],
                "Book/portalの16状態と数値改変拒否、既受入20節のD1再検査",
            ),
        ],
    )


def main() -> None:
    require_m21_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "26.4":
            register_gap(section)
            seen.add(section["id"])
    expected = {*EARLIER, "26.4"}
    if seen != expected:
        raise ValueError(f"M21 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.4 and twenty earlier sections for M21")


if __name__ == "__main__":
    main()
