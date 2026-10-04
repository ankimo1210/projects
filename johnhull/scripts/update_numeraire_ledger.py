"""Register §28.4 only after the M29 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M29_CHECK = "docs/validation/section-28-4/m29-check.json"
EARLIER = [
    *[f"26.{n}" for n in range(1, 18)],
    *[f"27.{n}" for n in range(1, 9)],
    "28.1",
    "28.2",
    "28.3",
]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m29_gate() -> None:
    path = PROJECT / M29_CHECK
    if not path.is_file():
        raise ValueError("M29 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "28.4"
        or record.get("milestone") != "M29"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M29 acceptance record is not passing")
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_numeraire_acceptance_record.py"),
            "--check",
        ],
        cwd=PROJECT.parent,
        check=True,
    )


def m29_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M29_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M29 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M29 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M29 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M29 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    for key in tuple(evidence):
        if key.startswith("m") and key[1:3].isdigit() and key.endswith(("_check", "_recheck")):
            evidence.pop(key)
    record = m29_record(section["id"])
    evidence["m29_check"] = item(M29_CHECK, "record")
    evidence["m29_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M29_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                "m29_check"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_check")
                else "m29_recheck"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_recheck")
                else ref
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m29_recheck" not in refs:
            refs.append("m29_recheck")


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
        "id": f"NC{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m29_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_numeraire(section: dict) -> None:
    base = "docs/validation/section-28-4/"
    paths = {
        "review": ("docs/SECTION_28_4_REVIEW_2026-10-04.md", "note"),
        "acceptance_note": ("docs/SECTION_28_4_ACCEPTANCE_2026-10-04.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/_numeraire_choices.py", "source"),
        "hw": ("hullkit/src/hullkit/hull_white.py", "source"),
        "pricing_tests": ("hullkit/tests/test_numeraire_choices.py", "test"),
        "hw_tests": ("hullkit/tests/test_numeraire_hw_state.py", "test"),
        "reference_builder": ("scripts/build_numeraire_reference.py", "source"),
        "reference": (base + "reference.json", "reference"),
        "numerical_script": ("scripts/verify_numeraire_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_numeraire_numerics.py", "test"),
        "numerical": (base + "numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_numeraire_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_numeraire_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_numeraire_notebook.py", "test"),
        "notebook_script": ("scripts/verify_numeraire_notebook.py", "source"),
        "notebook_check": (base + "notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "browser_script": ("scripts/verify_numeraire_browser.cjs", "source"),
        "browser_run": (base + "browser-check.json", "record"),
        "m29_check": (M29_CHECK, "record"),
        **{
            key + "_image": (base + f"portal-martingale_numeraire_{key}-1000.png", "image")
            for key in ("pricing", "forward", "payment", "annuity")
        },
    }
    section.update(
        status="accepted",
        reviewed_at="2026-10-04",
        source_pages=[676, 679],
        scope="Hull GE §28.4全12要点/式28.16–28.25/脚注5,6をvol10 §6C・Book/portal・条件付き独立計算で照合。",
        assumptions=[
            "時刻は年、rateは年率小数、spot/priceは名目単位、Aは年×単位元本。t≤fixing T<payment U、annuity支払はT後の増加schedule。",
            "無収入stockと同一通貨。合成flat-OIS HW: Q zero-mean OU x、r=x+phi、phi=r0+c(t)、a>0、eta≥0。stock loadingは符号付き同一W。",
            "term金利はTで固定、overnightはUまで未確定、両方Uで支払う。正のnumeraireを要求、rate/V/sの負値は有効。",
            "projectionは初期curveを合わせた決定的加算simple-rate basis。AはOIS割引、Vにだけbasisを適用。annuity測度は支払Gaussianの正確な有限混合。",
            "原典に本節の印刷価格pinはない。全63fixture/10直接iid MCは合成、raw RNは自己正規化しない。",
        ],
        limitations=[
            "一般多因子導出は§28.5、lognormal Black仮定/market calibrationは後続節。flat HW実演を一般の多curve市場モデルと主張しない。",
            "MC表示は95%区間、受入5SE。独立求積price1e-9/rate2e-12、tiny-ah kernelとrank2退化を検査。",
            "multiplicative basis参照は別モデルの対比。同じ初期par率でもoption価格が異なるので教材に混用しない。",
            "private新計算/既存HW documented Q state補正。公開signatureとproduction依存を保持、vol26の3price丸め差と関連notebookをrefresh。",
        ],
        acceptance_note="docs/SECTION_28_4_ACCEPTANCE_2026-10-04.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "N01–N05:口座dM=rMdtと確率割引28.16–19、定数金利極限、脚注5の再投資を区別する。",
                "vol10 §6C.1–6C.2",
                ["pricing", "hw", "builder", "lesson"],
                ["reference", "numerical", "hw_tests"],
                ["pricing_image"],
                "確率割引と同一call価格、原典口座規約を表示",
            ),
            requirement(
                2,
                "N04,N06:支払日債券28.20、P(T,T)=1、同一給付Q経路割引/T外側DF、raw RNと金利vol0を検査。",
                "vol10 §6C.2",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["pricing_image"],
                "同じcallのQ/T direct MCと誤った外側Q割引を照合",
            ),
            requirement(
                3,
                "N07–N08:一般theta forward給付と28.21、futures Q平均/forward T平均、脚注6の金利FRA規約を説明。",
                "vol10 §6C.3",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "numerical_tests"],
                ["forward_image"],
                "符号付きloadingのfutures/forward、FRAの区別",
            ),
            requirement(
                4,
                "N09–N10:対象[T,U]/δの複利年率、term固定Tとovernight実現U、U支払測度28.22、条件付きFRA PV0。",
                "vol10 §6C.4",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["payment_image"],
                "δ=.25/.5と21状態の支払測度平均、誤った固定測度との差",
            ),
            requirement(
                5,
                "N11–N12:annuity28.23–25、開始/支払schedule、OIS A/projection V、条件付きmartingaleと同一payer給付Q/A。",
                "vol10 §6C.5",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["annuity_image"],
                "複数時刻/状態、加算basisでA保持、annuity平均とQ平均との差",
            ),
            requirement(
                6,
                "全12要求/6小節/4共有図、HW Q状態/tower整合、旧246セル、28節D1/両保管庫、16表示状態を保持。",
                "vol10 §6C.1–6C.6とBook/portal",
                ["pricing", "hw", "builder", "lesson", "portal"],
                ["hw_tests", "notebook_check", "notebook_tests", "numerical"],
                ["pricing_image", "forward_image", "payment_image", "annuity_image"],
                "257セル/旧246保持、16状態・幅700px以上、全28D1/両保管庫",
            ),
        ],
    )


def main() -> None:
    require_m29_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "28.4":
            register_numeraire(section)
            seen.add(section["id"])
    expected = {*EARLIER, "28.4"}
    if seen != expected:
        raise ValueError(f"M29 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §28.4 and twenty-eight earlier sections for M29")


if __name__ == "__main__":
    main()
