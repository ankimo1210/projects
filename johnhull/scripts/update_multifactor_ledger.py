"""Register §28.5 only after the M30 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M30_CHECK = "docs/validation/section-28-5/m30-check.json"
EARLIER = [
    *[f"26.{n}" for n in range(1, 18)],
    *[f"27.{n}" for n in range(1, 9)],
    "28.1",
    "28.2",
    "28.3",
    "28.4",
]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m30_gate() -> None:
    path = PROJECT / M30_CHECK
    if not path.is_file():
        raise ValueError("M30 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "28.5"
        or record.get("milestone") != "M30"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M30 acceptance record is not passing")
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_multifactor_acceptance_record.py"),
            "--check",
        ],
        cwd=PROJECT.parent,
        check=True,
    )


def m30_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M30_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M30 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M30 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M30 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M30 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    for key in tuple(evidence):
        if key.startswith("m") and key[1:3].isdigit() and key.endswith(("_check", "_recheck")):
            evidence.pop(key)
    record = m30_record(section["id"])
    evidence["m30_check"] = item(M30_CHECK, "record")
    evidence["m30_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M30_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                "m30_check"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_check")
                else "m30_recheck"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_recheck")
                else ref
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m30_recheck" not in refs:
            refs.append("m30_recheck")


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
        "id": f"MF{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m30_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_multifactor(section: dict) -> None:
    base = "docs/validation/section-28-5/"
    paths = {
        "review": ("docs/SECTION_28_5_REVIEW_2026-10-04.md", "note"),
        "acceptance_note": ("docs/SECTION_28_5_ACCEPTANCE_2026-10-04.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/_multi_factor_martingales.py", "source"),
        "pricing_tests": ("hullkit/tests/test_multi_factor_martingales.py", "test"),
        "reference_builder": ("scripts/build_multifactor_reference.py", "source"),
        "reference": (base + "reference.json", "reference"),
        "numerical_script": ("scripts/verify_multifactor_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_multifactor_numerics.py", "test"),
        "numerical": (base + "numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_multi_factor_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_multifactor_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_multifactor_notebook.py", "test"),
        "notebook_script": ("scripts/verify_multifactor_notebook.py", "source"),
        "notebook_check": (base + "notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "browser_script": ("scripts/verify_multifactor_browser.cjs", "source"),
        "browser_run": (base + "browser-check.json", "record"),
        "m30_check": (M30_CHECK, "record"),
        **{
            key + "_image": (base + f"portal-{key}-1000.png", "image")
            for key in (
                "factor_ratio_ito",
                "factor_ratio_conditional",
                "factor_basis_covariance",
                "factor_measure_price",
            )
        },
    }
    section.update(
        status="accepted",
        reviewed_at="2026-10-04",
        source_pages=[679, 680],
        scope="Hull GE §28.5 pp679–680/脚注7をMF01–06全五軸、vol10 §6D.1–6D.6と4共有図へ対応。",
        assumptions=[
            "無収入取引f/g、正値numeraire。同じ独立basisでsignedloadingとrisk-priceを扱う。時間は年、driftは1/年、loadingは1/√年、比は無次元。",
            "Cはsingle NxN対称unit-diagonal PSD、C=L Lᵀ。相関rowloadingはs L、相関risk vectorはC sg。ρ±1もinverse不要。",
            "一般ゼロdriftは局所martingale。条件付き平均は有限時間・一定係数GBMの可積分性を独立確認。観測比>0/h≥0。time0の異なる比は別の初期市場。",
            "原典に印刷数値pinはない。11市場/132条件付き状態は明示synthetic。価格fixtureはr一定、Qとgで同じcallを評価しraw RN自己正規化をしない。",
        ],
        limitations=[
            "一般状態依存SDEの真のmartingale条件を定数GBMの数値例で証明しない。確率金利の配布契約はM29のまま保持。",
            "MC262144/187集計、受入5SE/表示±1.96SE。SE0は数学的に決定的な給付だけ許容。独立drift1e−12/price1e−9、変異8拒否。",
            "浮動小数PSDは64eps*N*normの丸め境界のみ許容し、invalid correlationを修復しない。overflow/positive underflow/temporal/bool等を拒否。",
            "新計算と教材はprivate。Black市場分布仮定/交換/測度変更は28.6–28.8、市場較正・LMM等は後続P3未完。",
        ],
        acceptance_note="docs/SECTION_28_5_ACCEPTANCE_2026-10-04.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "MF01: n独立WienerのQ drift r/一般world r+lambda・s、符号付き共通basisと単位。",
                "vol10 §6D.1",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["factor_ratio_ito_image"],
                "Q/g drift、signed factorと単位を表示",
            ),
            requirement(
                2,
                "MF02: 比の相対Itô driftとlog drift、g-world lambda=sgで共分散補正が相殺。",
                "vol10 §6D.2",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "numerical_tests"],
                ["factor_ratio_ito_image"],
                "相関三因子の三寄与と相対drift0/log driftの区別",
            ),
            requirement(
                3,
                "MF03: 現在観測比から未来増分の条件付き期待値、有限GBM可積分性と一般局所条件の区別。",
                "vol10 §6D.3",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["factor_ratio_conditional_image"],
                "132条件付き状態の検査と6状態の直接MC/95%区間",
            ),
            requirement(
                4,
                "MF04: 多因子でも同一給付Q/g価格、raw RN方向・ランダム分母、同じf市場で3種類g。",
                "vol10 §6D.5",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "lesson_tests"],
                ["factor_measure_price_image"],
                "同じfを固定した正/負/zero g loading、価格−oracle ±95%区間",
            ),
            requirement(
                5,
                "MF05: 脚注7、相関C→L→独立basisの変換、sf C sg、risk-price C sg、直交回転不変。",
                "vol10 §6D.4",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["factor_basis_covariance_image"],
                "相関/独立covariance一致、C二重掛けを拒否",
            ),
            requirement(
                6,
                "MF06: PSD退化ρ±1/inverse不要、入力domain/単位/比較量、全6小節/旧257/29D1/両保管庫/16表示。",
                "vol10 §6D.6とBook/portal",
                ["pricing", "builder", "lesson", "portal"],
                ["reference", "numerical", "notebook_check", "notebook_tests"],
                ["factor_basis_covariance_image", "factor_measure_price_image"],
                "268セル/旧257保持、幅700px、全29D1/両保管庫とsource/result消費拒否",
            ),
        ],
    )


def main() -> None:
    require_m30_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "28.5":
            register_multifactor(section)
            seen.add(section["id"])
    expected = {*EARLIER, "28.5"}
    if seen != expected:
        raise ValueError(f"M30 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §28.5 and twenty-nine earlier sections for M30")


if __name__ == "__main__":
    main()
