"""Register §27.2 and connect ten earlier sections to the final M11 rechecks."""

import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M11_CHECK = "docs/validation/section-27-2/m11-check.json"
SHARED = {
    "report/report_builder/figures.py",
    "report/assets/style.css",
    "volumes/06_numerical_methods/numerical.ipynb",
    "volumes/06_numerical_methods/build_numerical_notebook.py",
}


def digest(name):
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def item(path, kind):
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs, locator):
    return {"state": "verified", "refs": refs, "locator": locator}


def rename_refs(section, mapping):
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [mapping.get(ref, ref) for ref in part["refs"]]


def refresh_shared(evidence):
    for entry in evidence.values():
        if entry["path"] in SHARED:
            entry["sha256"] = digest(entry["path"])


def update_exotics(section):
    number = section["id"].split(".")[1]
    evidence = section["evidence"]
    if "m10_recheck" in evidence:
        evidence.pop("m10_recheck")
        evidence["m11_recheck"] = item(
            f"docs/validation/section-26-{number}/m11-recheck.json", "record"
        )
    if "m10_check" in evidence:
        evidence.pop("m10_check")
        evidence["m11_check"] = item(M11_CHECK, "record")
    evidence["browser_run"] = item(
        f"docs/validation/section-26-{number}/browser-m11-recheck.json", "record"
    )
    evidence["notebook_check"] = item(M11_CHECK, "record")
    refresh_shared(evidence)
    rename_refs(section, {"m10_recheck": "m11_recheck", "m10_check": "m11_check"})


def update_alternative_models(section):
    evidence = section["evidence"]
    evidence.pop("m10_check")
    evidence["m11_check"] = item(M11_CHECK, "record")
    evidence["m11_recheck"] = item("docs/validation/section-27-1/m11-recheck.json", "record")
    evidence["browser_run"] = item(
        "docs/validation/section-27-1/browser-m11-recheck.json", "record"
    )
    evidence["notebook_script"] = item("scripts/verify_stochastic_volatility_notebook.py", "source")
    evidence["notebook_check"] = item("docs/validation/section-27-2/notebook-check.json", "record")
    refresh_shared(evidence)
    rename_refs(section, {"m10_check": "m11_check"})
    for need in section["requirements"]:
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m11_check" in refs and "m11_recheck" not in refs:
            refs.append("m11_recheck")


def requirement(number, statement, locator, implementation, validation, visualization, rendered):
    return {
        "id": f"SV{number:02d}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m11_check", *validation], locator),
            "visualization": covered(visualization, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_stochastic_volatility(section):
    paths = {
        "review": ("docs/SECTION_27_2_REVIEW_2026-09-26.md", "note"),
        "acceptance_note": ("docs/SECTION_27_2_ACCEPTANCE_2026-09-26.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/stochastic_volatility.py", "source"),
        "sabr": ("hullkit/src/hullkit/sabr.py", "source"),
        "pricing_tests": ("hullkit/tests/test_stochastic_volatility.py", "test"),
        "reference_tests": ("hullkit/tests/test_stochastic_volatility_reference.py", "test"),
        "reference_builder": ("scripts/build_stochastic_volatility_reference.py", "source"),
        "reference": ("docs/validation/section-27-2/reference.json", "reference"),
        "numerical_script": ("scripts/verify_stochastic_volatility_numerics.py", "source"),
        "numerical": ("docs/validation/section-27-2/numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_stochastic_volatility_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_stochastic_volatility_lesson.py", "test"),
        "notebook": ("volumes/06_numerical_methods/numerical.ipynb", "source"),
        "builder": ("volumes/06_numerical_methods/build_numerical_notebook.py", "source"),
        "notebook_script": ("scripts/verify_stochastic_volatility_notebook.py", "source"),
        "notebook_check": ("docs/validation/section-27-2/notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "styles": ("report/assets/style.css", "source"),
        "browser_script": ("scripts/verify_stochastic_volatility_browser.cjs", "source"),
        "browser_run": ("docs/validation/section-27-2/browser-check.json", "record"),
        "m11_check": (M11_CHECK, "record"),
        "term_image": ("docs/validation/section-27-2/portal-stochvol_term-1000.png", "image"),
        "mixing_image": ("docs/validation/section-27-2/portal-stochvol_mixing-1000.png", "image"),
        "correlation_image": (
            "docs/validation/section-27-2/portal-stochvol_correlation-1000.png",
            "image",
        ),
        "sabr_rho_image": ("docs/validation/section-27-2/portal-stochvol_sabr-1000.png", "image"),
        "sabr_nu_image": ("docs/validation/section-27-2/portal-stochvol_sabr-nu-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-09-26",
        source_pages=[646, 649],
        scope=(
            "Hull GE §27.2の式27.1–27.3、Hull–Whiteの混合公式、相関とHeston、SABRの近似式、"
            "GARCH・rough volatilityの位置付け。vol06 §8とBook/portal実画面。"
        ),
        assumptions=[
            "一定パラメータ、欧州バニラ、合成市場。α=0.5（平方根過程）で数値検証する。",
            "混合公式は株価とボラが無相関のときだけ使う。SABRはβ=0.5、F0=3%、T=1年の例。",
        ],
        limitations=[
            "混合公式のMCは平均分散の台形則と標本誤差を含む。SABR式とMCの差は7行使価格・1満期の実測で誤差上界ではない。",
            "GARCHとrough volatilityは説明と参照先のみで数値検証しない。",
            "市場較正、ヘッジ成績、ジャンプは評価しない。",
        ],
        acceptance_note="docs/SECTION_27_2_ACCEPTANCE_2026-09-26.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "式27.1の時間依存ボラで、BSMに平均分散率を入れれば正しいことと原典の0.065・25.5%を説明・検証する。",
                "vol06 §8.1：独立CN PDE（3行使価格）と単純平均25%との差",
                ["pricing", "builder"],
                ["numerical", "pricing_tests", "reference_tests"],
                ["term_image"],
                "Book/portalの瞬時ボラ・残存期間の平均ボラ曲線を確認",
            ),
            requirement(
                2,
                "式27.2–27.3と、無相関のときBSM価格を平均分散率の分布で平均するHull–Whiteの結果を説明・検証する。",
                "vol06 §8.2：厳密CIR遷移の条件付きMCと独立Gil-Pelaez（26価格）",
                ["pricing", "builder"],
                ["numerical", "pricing_tests"],
                ["mixing_image"],
                "Book本文の混合公式と価格比較の出力を確認",
            ),
            requirement(
                3,
                "無相関の確率ボラでBSMがATM付近を過大・深いITM/OTMを過小評価することとU字スマイルを示す。",
                "vol06 §8.3：過大評価帯K=88–128、ρ=0の対称性",
                ["pricing", "lesson"],
                ["numerical", "pricing_tests"],
                ["mixing_image"],
                "Book/portalのIV曲線と√E[V̄]の水準線を確認",
            ),
            requirement(
                4,
                "相関とα=0.5のHestonで、負の相関が株式型スキューを作ることを説明・検証する。",
                "vol06 §8.4：COSと独立Gil-Pelaez（78価格）、ATMの傾き",
                ["pricing", "lesson"],
                ["numerical", "reference_tests"],
                ["correlation_image"],
                "Book/portalの3相関のIV曲線を確認",
            ),
            requirement(
                5,
                "SABRの過程、原典の近似式とATM式、σ0・ρ・νの役割とβ=0.5を説明・検証する。",
                "vol06 §8.5：原典式の独立転記（216値）とEuler MC（7行使価格）",
                ["sabr", "lesson"],
                ["numerical", "reference_tests"],
                ["sabr_rho_image", "sabr_nu_image"],
                "Book/portalのSABRメニュー2状態とMC点を確認",
            ),
            requirement(
                6,
                "GARCH・rough volatilityの位置付けと極限・限界を示し、6小節・4共有図を両配布面へ届け、既受入10節の退行を検査する。",
                "vol06 §8.1–8.6：58セル、4図、両面2幅20状態、ξ→0と決定的分散の極限",
                ["builder", "lesson", "portal", "styles"],
                ["numerical", "notebook_check"],
                ["term_image", "mixing_image", "correlation_image", "sabr_rho_image"],
                "Book/portalの実画面、数値改変拒否、既受入10節の再検証",
            ),
        ],
    )


def main():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    for section in data["sections"]:
        if section["id"] in {f"26.{n}" for n in range(9, 18)}:
            update_exotics(section)
        elif section["id"] == "27.1":
            update_alternative_models(section)
        elif section["id"] == "27.2":
            register_stochastic_volatility(section)
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.9–§27.2 ledger evidence for M11")


if __name__ == "__main__":
    main()
