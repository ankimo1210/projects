"""Register §27.1 and connect nine earlier sections to final M10 rechecks."""

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


def requirement(number, statement, locator, implementation, validation, visualization, rendered):
    return {
        "id": f"AM{number:02d}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m10_check", *validation], locator),
            "visualization": covered(visualization, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def main():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    for section in data["sections"]:
        if section["id"] not in {f"26.{n}" for n in range(9, 18)}:
            continue
        number = section["id"].split(".")[1]
        evidence = section["evidence"]
        if "m9_recheck" in evidence or "m10_recheck" in evidence:
            evidence.pop("m9_recheck", None)
            evidence["m10_recheck"] = item(
                f"docs/validation/section-26-{number}/m10-recheck.json", "record"
            )
        if "m9_check" in evidence or "m10_check" in evidence:
            evidence.pop("m9_check", None)
            evidence["m10_check"] = item("docs/validation/section-27-1/m10-check.json", "record")
        evidence["browser_run"] = item(
            f"docs/validation/section-26-{number}/browser-m10-recheck.json", "record"
        )
        evidence["notebook_check"] = item("docs/validation/section-27-1/m10-check.json", "record")
        for entry in evidence.values():
            if entry["path"] in {
                "report/report_builder/figures.py",
                "report/assets/style.css",
            }:
                entry["sha256"] = digest(entry["path"])
        for need in section["requirements"]:
            for part in need["coverage"].values():
                part["refs"] = [
                    "m10_recheck"
                    if ref == "m9_recheck"
                    else "m10_check"
                    if ref == "m9_check"
                    else ref
                    for ref in part["refs"]
                ]

    evidence_paths = {
        "review": ("docs/SECTION_27_1_REVIEW_2026-09-25.md", "note"),
        "acceptance_note": ("docs/SECTION_27_1_ACCEPTANCE_2026-09-25.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/alternative_models.py", "source"),
        "pricing_tests": ("hullkit/tests/test_alternative_models.py", "test"),
        "reference_builder": ("scripts/build_alternative_models_reference.py", "source"),
        "reference": ("docs/validation/section-27-1/reference.json", "reference"),
        "numerical": ("docs/validation/section-27-1/numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_alternative_models_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_alternative_models_lesson.py", "test"),
        "notebook": ("volumes/06_numerical_methods/numerical.ipynb", "source"),
        "builder": ("volumes/06_numerical_methods/build_numerical_notebook.py", "source"),
        "notebook_script": ("scripts/verify_alternative_models_notebook.py", "source"),
        "notebook_check": ("docs/validation/section-27-1/notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "styles": ("report/assets/style.css", "source"),
        "browser_script": ("scripts/verify_alternative_models_browser.cjs", "source"),
        "browser_run": ("docs/validation/section-27-1/browser-check.json", "record"),
        "m10_check": ("docs/validation/section-27-1/m10-check.json", "record"),
        "cev_image": ("docs/validation/section-27-1/portal-alternative_cev-1000.png", "image"),
        "merton_image": (
            "docs/validation/section-27-1/portal-alternative_merton-1000.png",
            "image",
        ),
        "poisson_image": (
            "docs/validation/section-27-1/portal-alternative_poisson-1000.png",
            "image",
        ),
        "vg_image": ("docs/validation/section-27-1/portal-alternative_vg-1000.png", "image"),
    }
    section = next(section for section in data["sections"] if section["id"] == "27.1")
    section.update(
        status="accepted",
        reviewed_at="2026-09-25",
        source_pages=[641, 646],
        scope="Hull GE §27.1のCEV、Mertonジャンプ拡散、分散ガンマ。Table 27.1、Figure 27.1、欧州価格とBook/portal実画面。",
        assumptions=[
            "一定r・q、定数モデルパラメータ、欧州バニラ、合成市場。",
            "CEV比較はS0の局所ボラを固定し、独立PDEはβ=0.8で実施。",
            "VGは1−θν−σ²ν/2>0、分布図は固定seedの40万標本。",
        ],
        limitations=[
            "CEVのβ>1にある無限遠境界の扱いは独立PDEで検証しない。β≈1は数値極限を用いる。",
            "VG分布図は標本誤差を持ち、価格の求積残差は選んだ26行使価格での実測。",
            "較正能力、市場予測、取引費用、ジャンプ下の動的ヘッジ成績は評価しない。",
        ],
        acceptance_note="docs/SECTION_27_1_ACCEPTANCE_2026-09-25.md",
        evidence={name: item(path, kind) for name, (path, kind) in evidence_paths.items()},
        requirements=[
            requirement(
                1,
                "CEVのSDE、βごとの局所ボラ、非心カイ二乗価格とBSM極限を説明・検証する。",
                "vol06 §7.1：β=0.7/1/1.3の局所ボラ、β=0.8の独立PDE3価格",
                ["pricing", "lesson"],
                ["numerical", "pricing_tests"],
                ["cev_image"],
                "Book/portalのCEV曲線、PDE残差表示を確認",
            ),
            requirement(
                2,
                "Mertonのジャンプ分布・ドリフト補償・BSM級数と短期スキューを説明・検証する。",
                "vol06 §7.2：元のPoisson回数による条件付き期待値と26価格",
                ["pricing", "lesson"],
                ["numerical", "pricing_tests"],
                ["merton_image"],
                "Book/portalのスキューと価格表示を確認",
            ),
            requirement(
                3,
                "Table 27.1の回数別・累積確率とジャンプ経路を再現する。",
                "vol06 §7.3–7.4：λT=1、m=0–8、複数対数ジャンプの和",
                ["reference_builder", "builder"],
                ["numerical", "pricing_tests"],
                ["poisson_image"],
                "両面のm=0–8表示と保存値を確認",
            ),
            requirement(
                4,
                "VGのガンマ時計・補償項・指数モーメント条件とFigure 27.1を説明・検証する。",
                "vol06 §7.5：独立ガンマ密度積分26価格、満期株価分布",
                ["pricing", "lesson"],
                ["numerical", "pricing_tests"],
                ["vg_image"],
                "Book/portalの満期株価軸とVG/GBM密度を確認",
            ),
            requirement(
                5,
                "3モデルのBSM極限、パラメータ比較と適用限界を区別する。",
                "vol06 §7.6：β=1、λ=0、ν=0と市場較正・ヘッジの限界",
                ["pricing", "builder"],
                ["numerical", "pricing_tests"],
                ["cev_image", "vg_image"],
                "Book本文とportal注記を確認",
            ),
            requirement(
                6,
                "6小節・4共有図を両配布面へ届け、保存出力と既受入9節の退行を検査する。",
                "vol06 §7.1–7.6：46セル、4図、両面2幅16状態",
                ["builder", "lesson", "portal", "styles"],
                ["m10_check", "notebook_check"],
                ["cev_image", "merton_image", "poisson_image", "vg_image"],
                "Book/portalの実画面、数値改変拒否、既受入9節再検証",
            ),
        ],
    )
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.9–§27.1 ledger evidence for M10")


if __name__ == "__main__":
    main()
