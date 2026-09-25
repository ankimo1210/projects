"""Register §26.17 and replace stale shared-asset evidence with M9 rechecks."""

import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"


def digest(name):
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def item(path, kind):
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs, locator):
    return {"state": "verified", "refs": refs, "locator": locator}


def requirement(
    number, statement, explanation, implementation, validation, visualization, rendered
):
    return {
        "id": f"SR{number:02d}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], explanation),
            "implementation": covered(implementation, explanation),
            "independent_validation": covered(validation, explanation),
            "visualization": covered(visualization, explanation),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def main():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    for section in data["sections"]:
        if section["id"] not in {f"26.{n}" for n in range(9, 17)}:
            continue
        number = section["id"].split(".")[1]
        evidence = section["evidence"]
        if "m8_recheck" in evidence:
            evidence["m9_recheck"] = item(
                f"docs/validation/section-26-{number}/m9-recheck.json", "record"
            )
            del evidence["m8_recheck"]
        if "m8_check" in evidence:
            evidence["m9_check"] = item("docs/validation/section-26-17/m9-check.json", "record")
            del evidence["m8_check"]
        if "m9_recheck" in evidence:
            evidence["m9_recheck"]["sha256"] = digest(evidence["m9_recheck"]["path"])
        evidence["browser_run"] = item(
            f"docs/validation/section-26-{number}/browser-m9-recheck.json", "record"
        )
        evidence["notebook_check"] = item(
            "docs/validation/section-26-17/notebook-check.json", "record"
        )
        for entry in evidence.values():
            if entry["path"] in {
                "volumes/10_exotics_martingales/build_exotics_notebook.py",
                "volumes/10_exotics_martingales/exotics.ipynb",
                "report/report_builder/figures.py",
                "report/assets/style.css",
                "docs/validation/section-26-17/m9-check.json",
            }:
                entry["sha256"] = digest(entry["path"])
        for need in section["requirements"]:
            for part in need["coverage"].values():
                part["refs"] = [
                    "m9_recheck"
                    if ref == "m8_recheck"
                    else "m9_check"
                    if ref == "m8_check"
                    else ref
                    for ref in part["refs"]
                ]

    evidence_paths = {
        "review": ("docs/SECTION_26_17_REVIEW_2026-09-25.md", "note"),
        "acceptance_note": ("docs/SECTION_26_17_ACCEPTANCE_2026-09-25.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/static_replication.py", "source"),
        "pricing_tests": ("hullkit/tests/test_static_replication.py", "test"),
        "reference_builder": ("scripts/build_static_replication_reference.py", "source"),
        "reference": ("docs/validation/section-26-17/reference.json", "reference"),
        "numerical": ("docs/validation/section-26-17/numerical-check.json", "reference"),
        "reference_tests": ("hullkit/tests/test_static_replication_reference.py", "test"),
        "lesson": ("hullkit/src/hullkit/_static_replication_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_static_replication_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_script": ("scripts/verify_static_replication_notebook.py", "source"),
        "notebook_check": ("docs/validation/section-26-17/notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "styles": ("report/assets/style.css", "source"),
        "browser_script": ("scripts/verify_static_replication_browser.cjs", "source"),
        "browser_run": ("docs/validation/section-26-17/browser-check.json", "record"),
        "m9_check": ("docs/validation/section-26-17/m9-check.json", "record"),
        "boundary_image": (
            "docs/validation/section-26-17/portal-static_boundary-1000.png",
            "image",
        ),
        "ladder_image": ("docs/validation/section-26-17/portal-static_ladder-1000.png", "image"),
        "error_image": (
            "docs/validation/section-26-17/portal-static_boundary_error-1000.png",
            "image",
        ),
        "convergence_image": (
            "docs/validation/section-26-17/portal-static_convergence-1000.png",
            "image",
        ),
    }
    section = next(section for section in data["sections"] if section["id"] == "26.17")
    section.update(
        status="accepted",
        reviewed_at="2026-09-25",
        source_pages=[632, 634],
        scope="Hull GE §26.17の連続監視アップ・アンド・アウト・コール。境界条件、Table 26.1、有限節点残差、3/18/100点、ヘッジの解消、Book/portal実画面。",
        assumptions=[
            "一定r・q・σのBlack–Scholes、連続パス・連続バリア監視。",
            "S0<H、K<H。必要な行使・満期の欧州コールを取引できる。",
        ],
        limitations=[
            "有限節点の一致は節点間の複製を保証しない。バリア到達時には解消が必要。",
            "ジャンプ、現金配当、離散観測、取引コスト、解消価格、流動性を評価しない。",
            "3/18/100点の接近はこの市場での観測であり、一般の誤差上界ではない。",
        ],
        acceptance_note="docs/SECTION_26_17_ACCEPTANCE_2026-09-25.md",
        evidence={name: item(path, kind) for name, (path, kind) in evidence_paths.items()},
        requirements=[
            requirement(
                1,
                "満期給付とノックアウト境界の2条件を説明し、有限時刻の境界照合を厳密な連続境界と区別する。",
                "vol10 §4.7.1：2境界とFigure 26.1",
                ["pricing", "lesson"],
                ["m9_check", "reference_tests"],
                ["boundary_image"],
                "Book/portalの境界図と本文を確認",
            ),
            requirement(
                2,
                "Table 26.1のA–Dの行使・満期・枚数・初期価値と後ろ向き照合を再現する。",
                "vol10 §4.7.2–3：4脚とw_j=-A_j/C_j",
                ["pricing", "reference_builder"],
                ["m9_check", "pricing_tests", "reference_tests"],
                ["ladder_image"],
                "Book/portalの4脚と保存出力を確認",
            ),
            requirement(
                3,
                "節点のゼロ残差と節点間の非ゼロ残差、バリア到達時の解消を示す。",
                "vol10 §4.7.3・4.7.5：有限節点と解消",
                ["pricing", "lesson"],
                ["m9_check", "reference_tests"],
                ["error_image"],
                "両面の3/18/100点メニューを確認",
            ),
            requirement(
                4,
                "3/18/100点の初期価値と独立解析バリア価格を原典の表示桁で再現する。",
                "vol10 §4.7.4：0.73/0.38/0.32と解析0.31",
                ["pricing", "reference_builder"],
                ["m9_check", "reference_tests"],
                ["convergence_image"],
                "両面の収束図を独立数値と照合",
            ),
            requirement(
                5,
                "ヘッジの売買符号、理想化の前提、流動性・解消・取引費用の限界を説明する。",
                "vol10 §4.7.5–6：エキゾチックの保有/売却で反対符号",
                ["pricing", "builder"],
                ["m9_check", "pricing_tests"],
                ["error_image"],
                "Bookの説明とportal実務メモを確認",
            ),
            requirement(
                6,
                "6小節・4共有図をBook/portalへ配布し、保存出力と既受入8節の退行を検査する。",
                "vol10 §4.7.1–6：共有4図と125セル",
                ["lesson", "builder", "portal", "styles"],
                ["m9_check", "notebook_check"],
                ["boundary_image", "ladder_image", "error_image", "convergence_image"],
                "両面2幅24状態、16画像と数値改変拒否",
            ),
        ],
    )
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.9–§26.17 ledger evidence for M9")


if __name__ == "__main__":
    main()
