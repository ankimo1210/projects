"""Register §26.6 only after the M23 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M23_CHECK = "docs/validation/section-26-6/m23-check.json"
EARLIER = [
    "26.1",
    "26.2",
    "26.3",
    "26.4",
    "26.5",
    *[f"26.{n}" for n in range(9, 18)],
    *[f"27.{n}" for n in range(1, 9)],
]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m23_gate() -> None:
    path = PROJECT / M23_CHECK
    if not path.is_file():
        raise ValueError("M23 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "26.6"
        or record.get("milestone") != "M23"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M23 acceptance record is not passing")
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_cliquet_acceptance_record.py"),
            "--check",
        ],
        cwd=PROJECT.parent,
        check=True,
    )


def m23_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M23_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M23 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M23 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M23 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M23 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    for key in tuple(evidence):
        if key.startswith("m") and key[1:3].isdigit() and key.endswith(("_check", "_recheck")):
            evidence.pop(key)
    record = m23_record(section["id"])
    evidence["m23_check"] = item(M23_CHECK, "record")
    evidence["m23_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M23_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                "m23_check"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_check")
                else "m23_recheck"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_recheck")
                else ref
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m23_recheck" not in refs:
            refs.append("m23_recheck")


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
        "id": f"CQ{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m23_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_cliquet(section: dict) -> None:
    base = "docs/validation/section-26-6/"
    paths = {
        "review": ("docs/SECTION_26_6_REVIEW_2026-10-01.md", "note"),
        "acceptance_note": ("docs/SECTION_26_6_ACCEPTANCE_2026-10-01.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/cliquet.py", "source"),
        "bsm": ("hullkit/src/hullkit/bsm.py", "source"),
        "forward_start": ("hullkit/src/hullkit/forward_start.py", "source"),
        "pricing_tests": ("hullkit/tests/test_cliquet.py", "test"),
        "reference_builder": ("scripts/build_cliquet_reference.py", "source"),
        "reference_tests": ("hullkit/tests/test_cliquet_reference.py", "test"),
        "reference": (base + "reference.json", "reference"),
        "numerical_script": ("scripts/verify_cliquet_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_cliquet_numerics.py", "test"),
        "numerical": (base + "numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_cliquet_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_cliquet_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_cliquet_notebook.py", "test"),
        "notebook_script": ("scripts/verify_cliquet_notebook.py", "source"),
        "notebook_check": (base + "notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "browser_script": ("scripts/verify_cliquet_browser.cjs", "source"),
        "browser_run": (base + "browser-check.json", "record"),
        "m23_check": (M23_CHECK, "record"),
        "reset_image": (base + "portal-cliquet_reset-1000.png", "image"),
        "components_image": (base + "portal-cliquet_components-1000.png", "image"),
        "frequency_image": (base + "portal-cliquet_frequency-1000.png", "image"),
        "limits_image": (base + "portal-cliquet_limits-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-10-01",
        source_pages=[618, 618],
        scope="Hull GE §26.6の単純cliquet call/put。ATM strike reset、各期支払、vanillaとforward-startの和、複雑条項のMC診断をvol10 §4.13とBook/portalで照合する。",
        assumptions=[
            "定数r,q,σのGBM、1株当たりの株価差給付。S>0、σ≥0、市場は有限実数・broadcast。支払日は非空1次元・正・厳密増加。",
            "原典に印刷数値はない。全価格・経路は合成。独立密度求積60ケースと各524288経路の多時点MC4例。",
            "最初のstrikeはS0、以後は直前fixingの株価。各給付をそれぞれの支払日から割り引く。",
            "制約図のみr=q=0。総額floor 5/cap 20、各期cap 5、95–105で当期支払後に終了する診断。",
        ],
        limitations=[
            "公開APIは単純ATM stock-price cliquet call/putのみ。global/local制約・終了は教材用MC診断。",
            "固定notional return、実市場smile、確率的金利/変動率、取引費用は対象外。",
            "95%区間はMC平均の標本誤差。求積誤差と6標準誤差の検査閾値とは異なる。",
        ],
        acceptance_note="docs/SECTION_26_6_ACCEPTANCE_2026-10-01.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "最初のvanillaとn−1本のforward-start、strike resetと各期通貨給付を説明する。",
                "vol10 §4.13.1–4.13.2",
                ["pricing", "forward_start", "builder", "lesson"],
                ["reference", "numerical", "reference_tests"],
                ["reset_image"],
                "両画面のstock・strike・fixing・給付customdataを照合",
            ),
            requirement(
                2,
                "call/put各期PVの和を求め、支払日割引と非等間隔schedule、call−put差を照合する。",
                "vol10 §4.13.3",
                ["pricing", "bsm", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["components_image"],
                "両画面の各期価格と合成例23.584836/19.750719を照合",
            ),
            requirement(
                3,
                "n=1のvanilla、reset回数・期間の比較、zeroσ・broadcast・無効入力を確認する。",
                "vol10 §4.13.4・4.13.6",
                ["pricing", "bsm", "builder"],
                ["reference", "numerical", "pricing_tests"],
                ["frequency_image"],
                "両画面のn=1と満期固定曲線を照合",
            ),
            requirement(
                4,
                "総額制約・各期制約・範囲終了を区別し、r=q=0診断とMC平均95%区間を示す。",
                "vol10 §4.13.5",
                ["reference_builder", "lesson", "builder"],
                ["reference", "numerical", "reference_tests"],
                ["limits_image"],
                "両画面で4契約・単純和求積・誤差棒を照合",
            ),
            requirement(
                5,
                "独立密度求積60ケースとMC4例で検証し、参照4改変と実API3誤実装を拒否する。",
                "vol10 §4.13.5–4.13.6",
                ["pricing", "reference_builder"],
                ["reference", "numerical", "numerical_tests"],
                ["components_image", "limits_image"],
                "全traceの参照照合と価格改変拒否",
            ),
            requirement(
                6,
                "6小節・共有4図、旧180セル、既受入22節と両画面16状態を再検証する。",
                "vol10 §4.13とBook/portal",
                ["builder", "lesson", "portal"],
                ["numerical", "notebook_check", "notebook_tests"],
                ["reset_image", "components_image", "frequency_image", "limits_image"],
                "16状態・notebook4改変・旧22節D1と両保管庫",
            ),
        ],
    )


def main() -> None:
    require_m23_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "26.6":
            register_cliquet(section)
            seen.add(section["id"])
    expected = {*EARLIER, "26.6"}
    if seen != expected:
        raise ValueError(f"M23 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.6 and twenty-two earlier sections for M23")


if __name__ == "__main__":
    main()
