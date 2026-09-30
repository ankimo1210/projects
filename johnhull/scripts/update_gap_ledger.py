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
        "review": ("docs/SECTION_26_4_REVIEW_2026-09-30.md", "note"),
        "acceptance_note": ("docs/SECTION_26_4_ACCEPTANCE_2026-09-30.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/gap_options.py", "source"),
        "formula": ("hullkit/src/hullkit/exotics.py", "source"),
        "pricing_tests": ("hullkit/tests/test_gap_options.py", "test"),
        "reference_builder": ("scripts/build_gap_reference.py", "source"),
        "reference_tests": ("hullkit/tests/test_gap_reference_builder.py", "test"),
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
        "settlement_image": (base + "portal-gap_settlement_line-1000.png", "image"),
        "insurance_image": (base + "portal-gap_insurance-1000.png", "image"),
        "transfer_image": (base + "portal-gap_transfer_cost-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-09-30",
        source_pages=[617, 617],
        scope=(
            "Hull GE §26.4のギャップ・コールとギャップ・プット。トリガーK2と決済の行使価格K1、"
            "式26.1・26.2、通常のオプションとの差、例題26.1の保険会社の費用。vol10 §4.11とBook/portal実画面。"
        ),
        assumptions=[
            "原資産は定数r,q,σの幾何ブラウン運動。支払の条件は満期にだけ判定する欧州型。",
            "原典の数値は例題26.1（3,436、1,896、約45%）だけ。その他の市場と移転費用の曲線は明示した合成例である。",
            "例題26.1の契約者は、満期に手取りが正なら必ず請求すると仮定する。",
        ],
        limitations=[
            "支払はmax(·,0)で抑えない。K1とK2の順序によって保有者の支払が負になる。",
            "移転費用以外の取引費用、保険会社の信用リスク、離散配当、K2付近のヘッジ誤差は扱わない。",
            "hullkit.exotics.gap_call・gap_putは入力を検証しない。検証はhullkit.gap_options.gap_optionが行う。",
        ],
        acceptance_note="docs/SECTION_26_4_ACCEPTANCE_2026-09-30.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "ギャップ・コール・プットの支払を、トリガーK2と決済の行使価格K1を分けて定義し、負の支払と跳びを示す。",
                "vol10 §4.11.1：支払の条件と支払額",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["payoff_image"],
                "Book/portalで満期の支払とK2での切れ目を確認",
            ),
            requirement(
                2,
                "式26.1・26.2の価格を実装し、d1・d2にK2、現金の項にK1を使うことを独立参照で確かめる。",
                "vol10 §4.11.2：価格式と分解",
                ["pricing", "formula"],
                ["reference", "numerical", "reference_tests"],
                ["settlement_image"],
                "Book/portalで K1 と価格の直線が保存参照と一致することを確認",
            ),
            requirement(
                3,
                "通常のオプションとの差(K2−K1)e^{−rT}N(d2)を符号付きで示し、パリティとK1=0の極限を確かめる。",
                "vol10 §4.11.2–4.11.3：分解と直線関係",
                ["pricing", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["settlement_image"],
                "Book/portalでK1と価格の直線、価値ゼロのK1を確認",
            ),
            requirement(
                4,
                "例題26.1の通常のプット3,436とギャップ・プット1,896、約45%の減少を再現する。",
                "vol10 §4.11.4：例題26.1",
                ["pricing", "reference_builder"],
                ["reference", "numerical", "numerical_tests"],
                ["insurance_image", "transfer_image"],
                "Book/portalで原典の数値と保険会社の支払を確認",
            ),
            requirement(
                5,
                "保険会社の費用を、契約者の価値と移転費用の現在価値に分けて説明する。",
                "vol10 §4.11.5：保険会社と契約者",
                ["reference_builder", "lesson"],
                ["reference", "numerical", "reference_tests"],
                ["insurance_image", "transfer_image"],
                "Book/portalで移転費用と費用の関係を確認",
            ),
            requirement(
                6,
                "vol10 §4.11の6小節・共有4図、前提と限界、節外セルと既受入20節の保持、両画面の表示を再検証する。",
                "vol10 §4.11とBook/portalの共有図",
                ["pricing", "builder", "lesson", "portal"],
                ["numerical", "notebook_check", "notebook_tests"],
                ["payoff_image", "settlement_image", "insurance_image", "transfer_image"],
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
