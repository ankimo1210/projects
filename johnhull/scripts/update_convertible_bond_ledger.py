"""Register §27.4 and connect twelve accepted sections to final M13 evidence."""

import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M13_CHECK = "docs/validation/section-27-4/m13-check.json"
CHANGED = {
    "report/report_builder/figures.py",
    "report/tests/test_report_build.py",
    "report/tests/test_stochastic_volatility_notebook.py",
    "report/tests/test_local_volatility_notebook.py",
    "report/assets/style.css",
    "volumes/06_numerical_methods/numerical.ipynb",
    "volumes/06_numerical_methods/build_numerical_notebook.py",
}


def digest(path):
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path, kind):
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs, locator):
    return {"state": "verified", "refs": refs, "locator": locator}


def refresh_earlier(section):
    evidence = section["evidence"]
    evidence.pop("m12_check", None)
    evidence.pop("m12_recheck", None)
    number = section["id"].replace(".", "-")
    evidence["m13_check"] = item(M13_CHECK, "record")
    evidence["m13_recheck"] = item(f"docs/validation/section-{number}/m13-recheck.json", "record")
    evidence["browser_run"] = item(
        f"docs/validation/section-{number}/browser-m13-recheck.json", "record"
    )
    if section["id"].startswith("26."):
        evidence["notebook_check"] = item(M13_CHECK, "record")
    else:
        evidence["notebook_script"] = item("scripts/verify_convertible_bond_notebook.py", "source")
        evidence["notebook_check"] = item(
            "docs/validation/section-27-4/notebook-check.json", "record"
        )
    for entry in evidence.values():
        if entry["path"] in CHANGED:
            entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                {"m12_check": "m13_check", "m12_recheck": "m13_recheck"}.get(ref, ref)
                for ref in part["refs"]
            ]
        if section["id"] == "27.3":
            refs = need["coverage"]["independent_validation"]["refs"]
            if "m13_recheck" not in refs:
                refs.append("m13_recheck")


def requirement(number, statement, locator, implementation, validation, figures, rendered):
    return {
        "id": f"CB{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m13_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_convertible(section):
    paths = {
        "review": ("docs/SECTION_27_4_REVIEW_2026-09-27.md", "note"),
        "acceptance_note": ("docs/SECTION_27_4_ACCEPTANCE_2026-09-27.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/convertible_bond.py", "source"),
        "pricing_tests": ("hullkit/tests/test_convertible_bond.py", "test"),
        "reference_builder": ("scripts/build_convertible_bond_reference.py", "source"),
        "reference": ("docs/validation/section-27-4/reference.json", "reference"),
        "numerical_script": ("scripts/verify_convertible_bond_numerics.py", "source"),
        "numerical": ("docs/validation/section-27-4/numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_convertible_bond_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_convertible_bond_lesson.py", "test"),
        "notebook": ("volumes/06_numerical_methods/numerical.ipynb", "source"),
        "builder": ("volumes/06_numerical_methods/build_numerical_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_convertible_bond_notebook.py", "test"),
        "notebook_script": ("scripts/verify_convertible_bond_notebook.py", "source"),
        "notebook_check": ("docs/validation/section-27-4/notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "styles": ("report/assets/style.css", "source"),
        "browser_script": ("scripts/verify_convertible_bond_browser.cjs", "source"),
        "browser_run": ("docs/validation/section-27-4/browser-check.json", "record"),
        "m13_check": (M13_CHECK, "record"),
        "tree_image": ("docs/validation/section-27-4/portal-cb_tree-1000.png", "image"),
        "decision_image": ("docs/validation/section-27-4/portal-cb_decisions-1000.png", "image"),
        "credit_image": ("docs/validation/section-27-4/portal-cb_credit-1000.png", "image"),
        "convergence_image": (
            "docs/validation/section-27-4/portal-cb_convergence-1000.png",
            "image",
        ),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-09-27",
        source_pages=[650, 653],
        scope=(
            "Hull GE §27.4のデフォルト付き転換社債、転換・発行体コール・回収、"
            "Example 27.1とFigure 27.2。vol06 §10とBook/portal実画面。"
        ),
        assumptions=[
            "元本100ドル、転換株数2、コール113ドル、S0=50ドル、満期0.75年、3段、r=5%、q=0%、σ=30%、λ=1%、回収40ドル。",
            "金利・配当・生存条件付きボラ・危険中立ハザードと権利条件は一定。期末利息は生存枝で権利判断前に支払う。",
        ],
        limitations=[
            "株価依存・時変ハザード、条件付きコール、時変転換株数、契約別の回収・利息規則はモデル化しない。",
            "3段値には格子誤差が残る。信用市場からの較正や実際の転換社債価格・ヘッジ成績は検証しない。",
        ],
        acceptance_note="docs/SECTION_27_4_ACCEPTANCE_2026-09-27.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "転換・コール・再転換の契約順序と節点価値を説明する。",
                "vol06 §10.1：継続・転換・コール価値",
                ["pricing", "builder"],
                ["numerical", "pricing_tests"],
                ["decision_image"],
                "Book/portalの権利順序と判断図を確認",
            ),
            requirement(
                2,
                "生存条件付きσと危険中立λから上・下・デフォルト3枝確率を実装する。",
                "vol06 §10.2：生存確率と株価マルチンゲール",
                ["pricing", "builder"],
                ["numerical", "pricing_tests"],
                ["tree_image"],
                "Bookの確率式とツリーを確認",
            ),
            requirement(
                3,
                "原典Figure 27.2の10節点と満期・後退帰納を独立参照で照合する。",
                "vol06 §10.3：原典10節点、初期107.44ドル",
                ["pricing", "reference_builder"],
                ["numerical", "reference"],
                ["tree_image"],
                "Book/portalの3段値と節点ラベルを確認",
            ),
            requirement(
                4,
                "B・Dではコール後の転換、Eでは継続が最適と示す。",
                "vol06 §10.4：B・D・Eの継続と判断",
                ["pricing", "lesson"],
                ["numerical", "reference"],
                ["decision_image"],
                "Book/portalのコール前後の値を確認",
            ),
            requirement(
                5,
                "信用ハザード・回収額・生存条件付き利息を数値照合する。",
                "vol06 §10.5：信用・回収感応度と利付債恒等式",
                ["pricing", "lesson"],
                ["numerical", "pricing_tests"],
                ["credit_image"],
                "Book/portalの感応度と利息の説明を確認",
            ),
            requirement(
                6,
                "格子収束と状態独立ハザードの限界を示し、6小節・共有4図と既受入12節を再検証する。",
                "vol06 §10.1–10.6：82セル、両面2幅16状態",
                ["builder", "lesson", "portal"],
                ["numerical", "notebook_check"],
                ["tree_image", "decision_image", "credit_image", "convergence_image"],
                "Book/portal実画面、数値改変拒否、既受入12節の再検証",
            ),
        ],
    )


def main():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    earlier = {f"26.{number}" for number in range(9, 18)} | {"27.1", "27.2", "27.3"}
    for section in data["sections"]:
        if section["id"] in earlier:
            refresh_earlier(section)
        elif section["id"] == "27.4":
            register_convertible(section)
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.9–§27.4 ledger evidence for M13")


if __name__ == "__main__":
    main()
