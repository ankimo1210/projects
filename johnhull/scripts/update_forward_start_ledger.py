"""Register §26.5 only after the M22 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M22_CHECK = "docs/validation/section-26-5/m22-check.json"
EARLIER = [
    "26.1",
    "26.2",
    "26.3",
    "26.4",
    *[f"26.{n}" for n in range(9, 18)],
    *[f"27.{n}" for n in range(1, 9)],
]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m22_gate() -> None:
    path = PROJECT / M22_CHECK
    if not path.is_file():
        raise ValueError("M22 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "26.5"
        or record.get("milestone") != "M22"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M22 acceptance record is not passing")
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_forward_start_acceptance_record.py"),
            "--check",
        ],
        cwd=PROJECT.parent,
        check=True,
    )


def m22_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M22_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M22 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M22 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M22 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M22 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    for key in tuple(evidence):
        if key.startswith("m") and key[1:3].isdigit() and key.endswith(("_check", "_recheck")):
            evidence.pop(key)
    record = m22_record(section["id"])
    evidence["m22_check"] = item(M22_CHECK, "record")
    evidence["m22_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M22_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                "m22_check"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_check")
                else "m22_recheck"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_recheck")
                else ref
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m22_recheck" not in refs:
            refs.append("m22_recheck")


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
        "id": f"FS{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m22_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_forward_start(section: dict) -> None:
    base = "docs/validation/section-26-5/"
    paths = {
        "review": ("docs/SECTION_26_5_REVIEW_2026-10-01.md", "note"),
        "acceptance_note": ("docs/SECTION_26_5_ACCEPTANCE_2026-10-01.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/forward_start.py", "source"),
        "bsm": ("hullkit/src/hullkit/bsm.py", "source"),
        "pricing_tests": ("hullkit/tests/test_forward_start.py", "test"),
        "reference_builder": ("scripts/build_forward_start_reference.py", "source"),
        "reference_tests": ("hullkit/tests/test_forward_start_reference.py", "test"),
        "reference": (base + "reference.json", "reference"),
        "numerical_script": ("scripts/verify_forward_start_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_forward_start_numerics.py", "test"),
        "numerical": (base + "numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_forward_start_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_forward_start_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_forward_start_notebook.py", "test"),
        "notebook_script": ("scripts/verify_forward_start_notebook.py", "source"),
        "notebook_check": (base + "notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "browser_script": ("scripts/verify_forward_start_browser.cjs", "source"),
        "browser_run": (base + "browser-check.json", "record"),
        "m22_check": (M22_CHECK, "record"),
        "contract_image": (base + "portal-forward_contract-1000.png", "image"),
        "homogeneity_image": (base + "portal-forward_homogeneity-1000.png", "image"),
        "delay_image": (base + "portal-forward_start_delay-1000.png", "image"),
        "expiry_image": (base + "portal-forward_fixed_expiry-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-10-01",
        source_pages=[618, 618],
        scope="Hull GE §26.5のATM欧州型フォワード・スタート・コール。行使価格の開始日確定、一次同次性、配当調整、期間固定と満期固定、ESOとの関係をvol10 §4.12とBook/portalで照合する。",
        assumptions=[
            "定数r,q,σのGBM、ATM欧州型コール。S>0、σ≥0、0≤T1≤T2、有限実数入力。",
            "原典に印刷数値はない。全価格・経路は合成例。独立密度求積と二時点MCで検証する。",
            "契約期間τ=T2−T1。行使価格S(T1)は開始日に確定し、給付を満期T2から割り引く。",
        ],
        limitations=[
            "put・一般moneyness・cliquet・実市場smile・確率的金利/変動率は対象外。",
            "将来ATMで付与されるESOとの関係を説明するが、権利確定や早期行使を評価するモデルではない。",
            "95%区間はMC平均の標本誤差。検査の6標準誤差閾値と求積誤差は別に記録する。",
        ],
        acceptance_note="docs/SECTION_26_5_ACCEPTANCE_2026-10-01.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "今契約し開始日にK=S(T1)を確定する二時点契約と、将来ATMのESOとの関係を説明する。",
                "vol10 §4.12.1–4.12.2",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "reference_tests"],
                ["contract_image"],
                "Book/portalの開始点と確定後のstrikeを確認",
            ),
            requirement(
                2,
                "開始時点の価値cS(T1)/S0と株価に対する一次同次性を示す。",
                "vol10 §4.12.3",
                ["pricing", "bsm", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["homogeneity_image"],
                "Book/portalで条件付き価格の比例関係を照合",
            ),
            requirement(
                3,
                "今日の価格c exp(−qT1)、q=0の同期間価格不変、T1=0・ゼロσ・ゼロ長境界を照合する。",
                "vol10 §4.12.4・4.12.6",
                ["pricing", "bsm", "builder"],
                ["reference", "numerical", "pricing_tests"],
                ["delay_image", "expiry_image"],
                "Book/portalの合成例と期間固定曲線を照合",
            ),
            requirement(
                4,
                "期間固定と満期固定の掃引を区別し、二時点MCの95%区間と独立求積を比較する。",
                "vol10 §4.12.4–4.12.5",
                ["reference_builder", "lesson", "builder"],
                ["reference", "numerical", "numerical_tests"],
                ["delay_image", "expiry_image"],
                "Book/portalのMC誤差棒とゼロ長終点を確認",
            ),
            requirement(
                5,
                "独立二増分求積36ケースとMC3例で価格を照合し、価格・tenor・fixing・割引の改変を拒否する。",
                "vol10 §4.12.5–4.12.6",
                ["pricing", "reference_builder"],
                ["reference", "numerical", "numerical_tests"],
                ["expiry_image"],
                "Book/portalの全traceを参照値と比較し数値改変を拒否",
            ),
            requirement(
                6,
                "6小節・共有4図、旧169セル、既受入21節、両画面の16状態を再検証する。",
                "vol10 §4.12とBook/portal",
                ["builder", "lesson", "portal"],
                ["numerical", "notebook_check", "notebook_tests"],
                ["contract_image", "homogeneity_image", "delay_image", "expiry_image"],
                "16状態・改変拒否・既受入21節のD1再検査",
            ),
        ],
    )


def main() -> None:
    require_m22_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "26.5":
            register_forward_start(section)
            seen.add(section["id"])
    expected = {*EARLIER, "26.5"}
    if seen != expected:
        raise ValueError(f"M22 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.5 and twenty-one earlier sections for M22")


if __name__ == "__main__":
    main()
