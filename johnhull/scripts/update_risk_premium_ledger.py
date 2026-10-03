"""Register §28.1 only after the M26 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M26_CHECK = "docs/validation/section-28-1/m26-check.json"
EARLIER = [*[f"26.{n}" for n in range(1, 18)], *[f"27.{n}" for n in range(1, 9)]]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m26_gate() -> None:
    path = PROJECT / M26_CHECK
    if not path.is_file():
        raise ValueError("M26 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "28.1"
        or record.get("milestone") != "M26"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M26 acceptance record is not passing")
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_risk_premium_acceptance_record.py"),
            "--check",
        ],
        cwd=PROJECT.parent,
        check=True,
    )


def m26_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M26_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M26 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M26 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M26 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M26 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    for key in tuple(evidence):
        if key.startswith("m") and key[1:3].isdigit() and key.endswith(("_check", "_recheck")):
            evidence.pop(key)
    record = m26_record(section["id"])
    evidence["m26_check"] = item(M26_CHECK, "record")
    evidence["m26_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M26_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                "m26_check"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_check")
                else "m26_recheck"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_recheck")
                else ref
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m26_recheck" not in refs:
            refs.append("m26_recheck")


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
        "id": f"RP{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m26_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_risk_premium(section: dict) -> None:
    base = "docs/validation/section-28-1/"
    paths = {
        "review": ("docs/SECTION_28_1_REVIEW_2026-10-03.md", "note"),
        "acceptance_note": ("docs/SECTION_28_1_ACCEPTANCE_2026-10-03.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/risk_premium.py", "source"),
        "sde": ("hullkit/src/hullkit/sde.py", "source"),
        "pricing_tests": ("hullkit/tests/test_risk_premium.py", "test"),
        "reference_builder": ("scripts/build_risk_premium_reference.py", "source"),
        "reference_tests": ("hullkit/tests/test_risk_premium_reference.py", "test"),
        "reference": (base + "reference.json", "reference"),
        "numerical_script": ("scripts/verify_risk_premium_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_risk_premium_numerics.py", "test"),
        "numerical": (base + "numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_risk_premium_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_risk_premium_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_risk_premium_notebook.py", "test"),
        "notebook_script": ("scripts/verify_risk_premium_notebook.py", "source"),
        "notebook_check": (base + "notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "browser_script": ("scripts/verify_risk_premium_browser.cjs", "source"),
        "browser_run": (base + "browser-check.json", "record"),
        "m26_check": (M26_CHECK, "record"),
        **{
            key + "_image": (base + f"portal-risk_premium_{key}-1000.png", "image")
            for key in ("loading", "hedge", "density", "validation")
        },
    }
    section.update(
        status="accepted",
        reviewed_at="2026-10-03",
        source_pages=[671, 674],
        scope="Hull GE §28.1の単因子・無配当取引証券の共通λ、局所無リスクportfolio、Examples 28.1/28.2、P→Q測度変更をvol10 §6.1–6.6とBook/portalで照合。",
        assumptions=[
            "同じ一因子Brownianに従う無配当の取引証券。sは符号付き係数、通常のvolatilityは|s|。μ,rは年^(-1)、s,λは年^(-1/2)。",
            "有限実数・市場broadcast。λ=(μ−r)/sはs≠0、μ=r+λsはs=0でもr。scalar float/ndarray。空batchでも不正入力を検査。",
            "原典の印刷値λ=.2/−.15、第二証券のμ=1.5%。12合成市場と6power給付をAPIを使わず再計算。",
            "測度変更の実験は定数係数・T=2のGBM。RN重みは非正規化、262144標本×4、seed281。負sはBrownian座標の反転として扱う。",
        ],
        limitations=[
            "消費財spotの期待収益/volatilityからλを機械的に求めない。λ推定、多因子、income補正、確率的金利のnumeraire比較は対象外。",
            "金額比率の相殺は瞬間的な自己金融hedgeを説明する。固定portfolioが満期まで無リスクとはしない。",
            "表現不能な計算はValueError。s=0ではλは特定できない。定数実験の95%区間は平均の標本誤差で、求積/モデル誤差を含まない。",
        ],
        acceptance_note="docs/SECTION_28_1_ACCEPTANCE_2026-10-03.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "共通単因子・無配当の取引証券、符号付きsとλの関係と単位を説明し逆算・順算する。",
                "vol10 §6.1",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["loading_image"],
                "両画面で正負s/λの期待収益曲線を照合",
            ),
            requirement(
                2,
                "原典の株数hedgeと教材の金額weightsを区別し、拡散相殺と無リスク年率収益を検証する。",
                "vol10 §6.2",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["hedge_image"],
                "両画面のリスク寄与合計0と収益合計rを照合",
            ),
            requirement(
                3,
                "Examples 28.1/28.2の.2/−.15/1.5%を再現し、消費財spotへの機械適用を避ける。",
                "vol10 §6.3",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "reference_tests"],
                ["loading_image"],
                "Book印刷値と両画面の負λ曲線を照合",
            ),
            requirement(
                4,
                "P→QのRN符号、ドリフト変更・拡散保存、負sの座標と非正規化重みを検証する。",
                "vol10 §6.4",
                ["pricing", "sde", "builder", "lesson"],
                ["reference", "numerical", "numerical_tests"],
                ["density_image", "validation_image"],
                "両画面でQ密度=P密度×RN、平均/分散・raw重みMCを照合",
            ),
            requirement(
                5,
                "独立12市場/6power求積と262144標本×4、ペア差SE、有限値、4保存改変/4実API変異を検査する。",
                "vol10 §6.5–6.6",
                ["pricing", "reference_builder", "sde"],
                ["reference", "numerical", "reference_tests", "numerical_tests"],
                ["validation_image"],
                "4市場の求積/再重み付け/Q直接95%誤差棒と価格改変拒否",
            ),
            requirement(
                6,
                "6小節・4共有図、旧213セル、既受入25節のD1と両画面16状態を再検査する。",
                "vol10 §6.1–6.6とBook/portal",
                ["builder", "lesson", "portal"],
                ["numerical", "notebook_check", "notebook_tests"],
                ["loading_image", "hedge_image", "density_image", "validation_image"],
                "16状態・notebook4改変・旧25節D1と両保管庫",
            ),
        ],
    )


def main() -> None:
    require_m26_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "28.1":
            register_risk_premium(section)
            seen.add(section["id"])
    expected = {*EARLIER, "28.1"}
    if seen != expected:
        raise ValueError(f"M26 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §28.1 and twenty-five earlier sections for M26")


if __name__ == "__main__":
    main()
