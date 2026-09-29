"""Register §26.3 only after the M20 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M20_CHECK = "docs/validation/section-26-3/m20-check.json"
EARLIER = ["26.1", "26.2", *[f"26.{n}" for n in range(9, 18)], *[f"27.{n}" for n in range(1, 9)]]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m20_gate() -> None:
    path = PROJECT / M20_CHECK
    if not path.is_file():
        raise ValueError("M20 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "26.3"
        or record.get("milestone") != "M20"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M20 acceptance record is not passing")
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_nonstandard_acceptance_record.py"),
            "--check",
        ],
        cwd=PROJECT.parent,
        check=True,
    )


def m20_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M20_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M20 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M20 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M20 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M20 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    for key in tuple(evidence):
        if key.startswith("m") and key[1:3].isdigit() and key.endswith(("_check", "_recheck")):
            evidence.pop(key)
    record = m20_record(section["id"])
    evidence["m20_check"] = item(M20_CHECK, "record")
    evidence["m20_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M20_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                "m20_check"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_check")
                else "m20_recheck"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_recheck")
                else ref
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m20_recheck" not in refs:
            refs.append("m20_recheck")


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
        "id": f"NA{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m20_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_nonstandard(section: dict) -> None:
    base = "docs/validation/section-26-3/"
    paths = {
        "review": ("docs/SECTION_26_3_REVIEW_2026-09-30.md", "note"),
        "acceptance_note": ("docs/SECTION_26_3_ACCEPTANCE_2026-09-30.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/nonstandard_american.py", "source"),
        "pricing_tests": ("hullkit/tests/test_nonstandard_american.py", "test"),
        "reference_builder": ("scripts/build_nonstandard_reference.py", "source"),
        "reference_tests": ("hullkit/tests/test_nonstandard_reference_builder.py", "test"),
        "reference": (base + "reference.json", "reference"),
        "numerical_script": ("scripts/verify_nonstandard_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_nonstandard_numerics.py", "test"),
        "numerical": (base + "numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_nonstandard_american_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_nonstandard_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_nonstandard_american_notebook.py", "test"),
        "notebook_script": ("scripts/verify_nonstandard_notebook.py", "source"),
        "notebook_check": (base + "notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "browser_script": ("scripts/verify_nonstandard_browser.cjs", "source"),
        "browser_run": (base + "browser-check.json", "record"),
        "m20_check": (M20_CHECK, "record"),
        "ordering_image": (base + "portal-scheduled_ordering-1000.png", "image"),
        "exercise_image": (base + "portal-scheduled_exercise-1000.png", "image"),
        "warrant_image": (base + "portal-scheduled_warrant-1000.png", "image"),
        "frequency_image": (base + "portal-scheduled_frequency-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-09-30",
        source_pages=[616, 616],
        scope=(
            "Hull GE §26.3の非標準アメリカン・オプション。行使可能日の制限、ロックアウト、"
            "時間変化する行使価格、7年ワラントの契約例をCRR格子で示す。vol10 §4.10とBook/portal実画面。"
        ),
        assumptions=[
            "原典§26.3に数値の市場条件や価格はない。ワラントの市場条件と評価額は明示した合成例である。",
            "行使可能日とその行使価格を0からNまでの整数格子点で指定し、満期Nでの行使を必須とする。",
            "原資産は定数r,q,σの幾何ブラウン運動。CRRでexp((r-q)Δt)を無裁定範囲とする。",
        ],
        limitations=[
            "格子日以外の契約日付は自動丸めしない。契約書の日付を整数格子へ写す作業は利用者が明示的に行う。",
            "ワラントの希薄化、発行体信用、離散配当、確率的パラメータ、連続行使の厳密価格は扱わない。",
        ],
        acceptance_note="docs/SECTION_26_3_ACCEPTANCE_2026-09-30.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "行使可能日を制限するBermudan型と行使不能期間を持つアメリカン型の後退帰納を実装する。",
                "vol10 §4.10.1–4.10.2：行使日とロックアウト",
                ["pricing", "builder"],
                ["reference", "numerical", "pricing_tests"],
                ["ordering_image", "exercise_image"],
                "Book/portalで価格順序と行使日のマスクを確認",
            ),
            requirement(
                2,
                "時点ごとの行使価格を受け取り、満期を含む契約条件を明示・検証する。",
                "vol10 §4.10.3：可変行使価格",
                ["pricing", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["exercise_image"],
                "Book/portalで行使価格の切替を確認",
            ),
            requirement(
                3,
                "7年ワラントの契約例を、合成市場条件を付けた離散格子例として評価する。",
                "vol10 §4.10.4：7年ワラント",
                ["reference_builder", "pricing", "lesson"],
                ["reference", "numerical", "reference_tests"],
                ["warrant_image"],
                "Book/portalで契約上の行使日と価格を確認",
            ),
            requirement(
                4,
                "小さな格子の全経路手計算と独立CRR実装で公開APIの節点・初期価格を照合する。",
                "vol10 §4.10.5：独立計算",
                ["pricing", "reference_builder"],
                ["reference", "numerical", "numerical_tests"],
                ["ordering_image"],
                "Book/portalで数値と大小関係を確認",
            ),
            requirement(
                5,
                "格子解像度、契約日、希薄化などの前提と限界を明示する。",
                "vol10 §4.10.6：前提と限界",
                ["pricing", "builder"],
                ["reference", "numerical"],
                ["frequency_image"],
                "Book/portalで頻度比較と限界の説明を確認",
            ),
            requirement(
                6,
                "vol10 §4.10の6小節・共有4図、節外セルと既受入19節の保持、両画面の表示を再検証する。",
                "vol10 §4.10とBook/portalの共有図",
                ["pricing", "builder", "lesson", "portal"],
                ["numerical", "notebook_check", "notebook_tests"],
                ["ordering_image", "exercise_image", "warrant_image", "frequency_image"],
                "Book/portalの16状態と数値改変拒否、既受入19節のD1再検査",
            ),
        ],
    )


def main() -> None:
    require_m20_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "26.3":
            register_nonstandard(section)
            seen.add(section["id"])
    expected = {*EARLIER, "26.3"}
    if seen != expected:
        raise ValueError(f"M20 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.3 and nineteen earlier sections for M20")


if __name__ == "__main__":
    main()
