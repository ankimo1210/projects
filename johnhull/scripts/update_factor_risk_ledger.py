"""Register §28.2 only after the M27 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M27_CHECK = "docs/validation/section-28-2/m27-check.json"
EARLIER = [*[f"26.{n}" for n in range(1, 18)], *[f"27.{n}" for n in range(1, 9)], "28.1"]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m27_gate() -> None:
    path = PROJECT / M27_CHECK
    if not path.is_file():
        raise ValueError("M27 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "28.2"
        or record.get("milestone") != "M27"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M27 acceptance record is not passing")
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_factor_risk_acceptance_record.py"),
            "--check",
        ],
        cwd=PROJECT.parent,
        check=True,
    )


def m27_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M27_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M27 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M27 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M27 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M27 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    for key in tuple(evidence):
        if key.startswith("m") and key[1:3].isdigit() and key.endswith(("_check", "_recheck")):
            evidence.pop(key)
    record = m27_record(section["id"])
    evidence["m27_check"] = item(M27_CHECK, "record")
    evidence["m27_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M27_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                "m27_check"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_check")
                else "m27_recheck"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_recheck")
                else ref
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m27_recheck" not in refs:
            refs.append("m27_recheck")


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
        "id": f"FR{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m27_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_factor_risk(section: dict) -> None:
    base = "docs/validation/section-28-2/"
    paths = {
        "review": ("docs/SECTION_28_2_REVIEW_2026-10-03.md", "note"),
        "acceptance_note": ("docs/SECTION_28_2_ACCEPTANCE_2026-10-03.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/factor_risk.py", "source"),
        "one_factor": ("hullkit/src/hullkit/risk_premium.py", "source"),
        "pricing_tests": ("hullkit/tests/test_factor_risk.py", "test"),
        "reference_builder": ("scripts/build_factor_risk_reference.py", "source"),
        "reference_tests": ("hullkit/tests/test_factor_risk_reference.py", "test"),
        "reference": (base + "reference.json", "reference"),
        "numerical_script": ("scripts/verify_factor_risk_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_factor_risk_numerics.py", "test"),
        "numerical": (base + "numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_factor_risk_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_factor_risk_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_factor_risk_notebook.py", "test"),
        "notebook_script": ("scripts/verify_factor_risk_notebook.py", "source"),
        "notebook_check": (base + "notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "browser_script": ("scripts/verify_factor_risk_browser.cjs", "source"),
        "browser_run": (base + "browser-check.json", "record"),
        "m27_check": (M27_CHECK, "record"),
        **{
            key + "_image": (base + f"portal-factor_risk_{key}-1000.png", "image")
            for key in ("contributions", "loading", "hedge", "validation")
        },
    }
    section.update(
        status="accepted",
        reviewed_at="2026-10-03",
        source_pages=[674, 675],
        scope="Hull GE §28.2の符号付き因子寄与、式28.11–28.13、Example28.3の超過収益6%、APT/CAPMとの条件付き関係、同一リスク基底と局所hedgeをvol10 §6AとBook/portalで照合。",
        assumptions=[
            "同一のリスク基底のλとs。教材の線形代数は独立Brownian基底。λ,sは年^(-1/2)、μ,r,λsは年^(-1)。符号を保持する。",
            "最終軸が同じ正の因子数、先行batch軸と金利のbroadcast。有限実数/空batch可。scalar因子/空因子/非実数/不整合/overflowをValueError。",
            "印刷例の寄与(+1%,-1%,+6%)と超過6%。総収益10%は教材が追加したr=4%の合成値で、原典の総収益値ではない。",
            "無配当・無収入の取引証券の瞬間的ドリフト。正負12市場、SVD二因子hedge、4直交回転、無価格追加因子、単因子縮約を独立算術と照合。CAPM例はCAPM仮定付き。",
        ],
        limitations=[
            "リスク価格/実世界の期待収益の推定器ではない。相関spot volatilityを無調整で使わず、内積へ相関を二重に掛けない。一般の白色化/多因子測度変更は§28.5以降。",
            "局所hedgeのwは現在の金額比率で、株数はw_i/f_i。固定株数が満期まで無リスクとはしない。",
            "市場と無相関なら価格ゼロという結論はCAPMが成立する場合に限る。一般のAPTでは無相関因子にも価格があり得る。",
            "配当/収入補正、確率金利、測度変更のMCと市場較正は対象外。符号付きリスクの瞬間関係と合成恒等式の検証を受け入れる。",
        ],
        acceptance_note="docs/SECTION_28_2_ACCEPTANCE_2026-10-03.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "式28.11–28.13とsigned係数/年率単位/最終因子軸を説明し、因子寄与・超過/総収益を計算する。",
                "vol10 §6A.1",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["loading_image"],
                "両画面でsigned-loading曲線と全traceを照合",
            ),
            requirement(
                2,
                "Example28.3の+1%,-1%,+6%と合計6%を超過収益として固定し、合成r=4%の総収益10%と区別する。",
                "vol10 §6A.2",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "reference_tests"],
                ["contributions_image"],
                "両画面で因子別寄与/合計、Bookで印刷6%と合成10%を照合",
            ),
            requirement(
                3,
                "正/負/ゼロのλs、負loading、無価格追加因子の条件、単因子縮約を検証する。",
                "vol10 §6A.3",
                ["pricing", "one_factor", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["loading_image", "contributions_image"],
                "正負λ₂の傾き/zero loading交点とExampleの負寄与を照合",
            ),
            requirement(
                4,
                "金額比率の二因子相殺/SVD零空間と直交回転の内積/volatility不変性、同一基底の規約を検証する。",
                "vol10 §6A.4–6A.5",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "numerical_tests"],
                ["hedge_image"],
                "両因子の合計0と収益r、Bookの4基底出力を照合",
            ),
            requirement(
                5,
                "独立12市場・CAPMの仮定付き計算・APTとの関係を説明し、保存4改変/API4変異を拒否する。",
                "vol10 §6A.5–6A.6",
                ["pricing", "reference_builder", "builder"],
                ["reference", "numerical", "reference_tests", "numerical_tests"],
                ["validation_image"],
                "独立算術/APIの12市場、BookのCAPM条件、数値改変拒否を照合",
            ),
            requirement(
                6,
                "6小節/4共有図、旧224セル、既受入26節D1と両画面16状態・幅700px以上を検証する。",
                "vol10 §6A.1–6A.6とBook/portal",
                ["builder", "lesson", "portal"],
                ["notebook_check", "notebook_tests", "numerical"],
                ["contributions_image", "loading_image", "hedge_image", "validation_image"],
                "16状態/235セル/旧224保持/全26D1・両保管庫復元",
            ),
        ],
    )


def main() -> None:
    require_m27_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "28.2":
            register_factor_risk(section)
            seen.add(section["id"])
    expected = {*EARLIER, "28.2"}
    if seen != expected:
        raise ValueError(f"M27 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §28.2 and twenty-six earlier sections for M27")


if __name__ == "__main__":
    main()
