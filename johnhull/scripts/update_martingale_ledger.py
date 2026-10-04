"""Register §28.3 only after the M28 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M28_CHECK = "docs/validation/section-28-3/m28-check.json"
EARLIER = [*[f"26.{n}" for n in range(1, 18)], *[f"27.{n}" for n in range(1, 9)], "28.1", "28.2"]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m28_gate() -> None:
    path = PROJECT / M28_CHECK
    if not path.is_file():
        raise ValueError("M28 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "28.3"
        or record.get("milestone") != "M28"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M28 acceptance record is not passing")
    subprocess.run(
        [
            sys.executable,
            str(PROJECT / "scripts/build_martingale_acceptance_record.py"),
            "--check",
        ],
        cwd=PROJECT.parent,
        check=True,
    )


def m28_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M28_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M28 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M28 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M28 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M28 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    for key in tuple(evidence):
        if key.startswith("m") and key[1:3].isdigit() and key.endswith(("_check", "_recheck")):
            evidence.pop(key)
    record = m28_record(section["id"])
    evidence["m28_check"] = item(M28_CHECK, "record")
    evidence["m28_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M28_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                "m28_check"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_check")
                else "m28_recheck"
                if ref.startswith("m") and ref[1:3].isdigit() and ref.endswith("_recheck")
                else ref
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m28_recheck" not in refs:
            refs.append("m28_recheck")


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
        "id": f"MT{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m28_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_martingale(section: dict) -> None:
    base = "docs/validation/section-28-3/"
    paths = {
        "review": ("docs/SECTION_28_3_REVIEW_2026-10-04.md", "note"),
        "acceptance_note": ("docs/SECTION_28_3_ACCEPTANCE_2026-10-04.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/_martingales.py", "source"),
        "one_factor": ("hullkit/src/hullkit/risk_premium.py", "source"),
        "pricing_tests": ("hullkit/tests/test_martingales.py", "test"),
        "reference_builder": ("scripts/build_martingale_reference.py", "source"),
        "reference_tests": ("hullkit/tests/test_martingale_reference.py", "test"),
        "reference": (base + "reference.json", "reference"),
        "numerical_script": ("scripts/verify_martingale_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_martingale_numerics.py", "test"),
        "numerical": (base + "numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_martingale_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_martingale_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_martingale_notebook.py", "test"),
        "notebook_script": ("scripts/verify_martingale_notebook.py", "source"),
        "notebook_check": (base + "notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "browser_script": ("scripts/verify_martingale_browser.cjs", "source"),
        "browser_run": (base + "browser-check.json", "record"),
        "m28_check": (M28_CHECK, "record"),
        **{
            key + "_image": (base + f"portal-martingale_{key}-1000.png", "image")
            for key in ("ito", "conditional", "conditional_mc", "pricing")
        },
    }
    section.update(
        status="accepted",
        reviewed_at="2026-10-04",
        source_pages=[675, 676],
        scope="Hull GE §28.3の条件付きmartingale定義、式28.14のsigned Itô相殺、式28.15の同一給付価格をvol10 §6BとBook/portalで照合。",
        assumptions=[
            "同一のWiener過程、signed sf,sg。μ,r,driftは年^(-1)、sf,sg,λは年^(-1/2)、hは年。正のratioと非負h。",
            "無収入の正の取引numeraire Gと定数係数GBM。有限時間の解析mean/第二モーメントにより可積分性を確認。一般の零drift過程は局所martingaleに留まる。",
            "6市場/9時刻状態/262144標本毎組/同一call2numeraire符号×2測度。全数値は合成値で原典の印刷数値ではない。",
            "t=0の異なるratioは別初期市場。条件付き将来増分を独立にサンプルし、非正規化の直接価格平均を使う。",
        ],
        limitations=[
            "一般のstrict local martingale、確率金利、配当、複数因子、市場較正は後続節で扱う。この検査を一般モデルのmartingale性の証明としない。",
            "H/G≤S/Gで可積分性を示す。G≠SなのでH/G≤1は主張しない。測度分布と確率的G_Tの分母を一緒に変更する。",
            "95%誤差棒は固定seedでのMC推定誤差、受入境界は5SE。API許容1e−12、Gaussian求積1e−9。",
            "新計算はprivate moduleで、公開API/依存は不変。",
        ],
        acceptance_note="docs/SECTION_28_3_ACCEPTANCE_2026-10-04.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "脚注3の条件付き定義、局所/真martingaleと追加可積分性条件を区別する。",
                "vol10 §6B.1/6B.3",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "pricing_tests"],
                ["conditional_image"],
                "両画面の条件付き平均とBookの定義/有限第二モーメント",
            ),
            requirement(
                2,
                "同一Wienerの式28.14とsigned Itô補正、relative driftとlog driftを計算する。",
                "vol10 §6B.2",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "reference_tests"],
                ["ito_image"],
                "符号付き4寄与と合計0を両画面で照合",
            ),
            requirement(
                3,
                "λ=sgにおけるμf=r+sg sf, μg=r+sg²、年率単位と別測度の非零driftを検証する。",
                "vol10 §6B.2–6B.3",
                ["pricing", "one_factor", "builder"],
                ["reference", "numerical", "pricing_tests"],
                ["ito_image", "conditional_image"],
                "g測度の定数平均と別測度の曲線を照合",
            ),
            requirement(
                4,
                "9時刻・状態の条件付き解析mean/MC、有限第二モーメント、t=0別市場、5SE/95%区間を区別する。",
                "vol10 §6B.3–6B.4",
                ["pricing", "builder", "lesson"],
                ["reference", "numerical", "numerical_tests"],
                ["conditional_mc_image"],
                "9点の差と95%区間を両画面で照合",
            ),
            requirement(
                5,
                "式28.15で同じcall給付をQ/Gで評価し、確率的G_Tの分母と測度drift、独立求積/直接MC、保存4/API4変異拒否を検証する。",
                "vol10 §6B.5–6B.6",
                ["pricing", "reference_builder", "builder"],
                ["reference", "numerical", "reference_tests", "numerical_tests"],
                ["pricing_image"],
                "同一call17.2494832790と正負sg×Q/G4点を照合",
            ),
            requirement(
                6,
                "6小節/4共有図、旧235セル、既受入27節D1と両画面16状態・幅700px以上を検証する。",
                "vol10 §6B.1–6B.6とBook/portal",
                ["builder", "lesson", "portal"],
                ["notebook_check", "notebook_tests", "numerical"],
                ["ito_image", "conditional_image", "conditional_mc_image", "pricing_image"],
                "16状態/246セル/旧235保持/全27D1・両保管庫復元",
            ),
        ],
    )


def main() -> None:
    require_m28_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "28.3":
            register_martingale(section)
            seen.add(section["id"])
    expected = {*EARLIER, "28.3"}
    if seen != expected:
        raise ValueError(f"M28 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §28.3 and twenty-seven earlier sections for M28")


if __name__ == "__main__":
    main()
