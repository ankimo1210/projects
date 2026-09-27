"""Register §27.5 and connect thirteen accepted sections to final M14 evidence."""

import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M14_CHECK = "docs/validation/section-27-5/m14-check.json"


def digest(path):
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path, kind):
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs, locator):
    return {"state": "verified", "refs": refs, "locator": locator}


def refresh_earlier(section):
    evidence = section["evidence"]
    evidence.pop("m13_check", None)
    evidence.pop("m13_recheck", None)
    number = section["id"].replace(".", "-")
    evidence["m14_check"] = item(M14_CHECK, "record")
    evidence["m14_recheck"] = item(f"docs/validation/section-{number}/m14-recheck.json", "record")
    evidence["browser_run"] = item(
        f"docs/validation/section-{number}/browser-m14-recheck.json", "record"
    )
    if section["id"].startswith("26."):
        evidence["notebook_check"] = item(M14_CHECK, "record")
    else:
        evidence["notebook_script"] = item("scripts/verify_path_dependent_notebook.py", "source")
        evidence["notebook_check"] = item(
            "docs/validation/section-27-5/notebook-check.json", "record"
        )
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                {"m13_check": "m14_check", "m13_recheck": "m14_recheck"}.get(ref, ref)
                for ref in part["refs"]
            ]
        if section["id"] in ("27.3", "27.4"):
            refs = need["coverage"]["independent_validation"]["refs"]
            if "m14_recheck" not in refs:
                refs.append("m14_recheck")


def requirement(number, statement, locator, implementation, validation, figures, rendered):
    return {
        "id": f"PD{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m14_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_path_dependent(section):
    paths = {
        "review": ("docs/SECTION_27_5_REVIEW_2026-09-27.md", "note"),
        "acceptance_note": ("docs/SECTION_27_5_ACCEPTANCE_2026-09-27.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/path_dependent_tree.py", "source"),
        "pricing_tests": ("hullkit/tests/test_path_dependent_tree.py", "test"),
        "reference_builder": ("scripts/build_path_dependent_reference.py", "source"),
        "reference": ("docs/validation/section-27-5/reference.json", "reference"),
        "numerical_script": ("scripts/verify_path_dependent_numerics.py", "source"),
        "numerical": ("docs/validation/section-27-5/numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_path_dependent_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_path_dependent_lesson.py", "test"),
        "notebook": ("volumes/06_numerical_methods/numerical.ipynb", "source"),
        "builder": ("volumes/06_numerical_methods/build_numerical_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_path_dependent_notebook.py", "test"),
        "notebook_script": ("scripts/verify_path_dependent_notebook.py", "source"),
        "notebook_check": ("docs/validation/section-27-5/notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "styles": ("report/assets/style.css", "source"),
        "browser_script": ("scripts/verify_path_dependent_browser.cjs", "source"),
        "browser_run": ("docs/validation/section-27-5/browser-check.json", "record"),
        "m14_check": (M14_CHECK, "record"),
        "grids_image": ("docs/validation/section-27-5/portal-path_grids-1000.png", "image"),
        "interpolation_image": (
            "docs/validation/section-27-5/portal-path_interpolation-1000.png",
            "image",
        ),
        "prices_image": ("docs/validation/section-27-5/portal-path_prices-1000.png", "image"),
        "exact_image": ("docs/validation/section-27-5/portal-path_exact-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-09-27",
        source_pages=[653, 656],
        scope=(
            "Hull GE §27.5の経路依存価格、算術平均アジアン・コールの代表平均格子、"
            "Figure 27.3と20段・60段の印刷値。vol06 §11とBook/portal実画面。"
        ),
        assumptions=[
            "S0=K=50ドル、満期1年、r=10%、q=0%、σ=40%。平均は初期値を含む離散観測で等間隔の代表値を使う。",
            "CRR二項株価格子、単一の更新可能な経路状態として算術平均を持つ。欧州型・米国型を各節点で評価する。",
        ],
        limitations=[
            "離散平均は連続平均ではない。代表平均の線形補間には格子誤差があり、2状態以上の経路依存や一般のバリアは対象外。",
            "市場データによる較正、ヘッジ性能、他の経路依存契約への汎用性は検証しない。",
        ],
        acceptance_note="docs/SECTION_27_5_ACCEPTANCE_2026-09-27.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "単一の更新可能な経路状態を追加する条件と算術平均の離散観測規約を説明する。",
                "vol06 §11.1：経路状態と離散平均",
                ["pricing", "builder"],
                ["numerical", "pricing_tests"],
                ["grids_image"],
                "Book/portalの平均状態と格子を確認",
            ),
            requirement(
                2,
                "同一株価節点で到達可能な算術平均の上下限を前向きに求める。",
                "vol06 §11.2：平均の上下限",
                ["pricing", "builder"],
                ["numerical", "pricing_tests"],
                ["grids_image"],
                "Book/portalの節点平均を確認",
            ),
            requirement(
                3,
                "Figure 27.3のX・Y・Zで代表平均、線形補間、割引後の値を照合する。",
                "vol06 §11.3：Figure 27.3のX・Y・Z",
                ["pricing", "reference_builder"],
                ["numerical", "reference"],
                ["interpolation_image"],
                "Book/portalの原典グリッドと補間値を確認",
            ),
            requirement(
                4,
                "欧州型の20段×4平均と60段×100平均の印刷価格を再現する。",
                "vol06 §11.4：欧州型の価格と格子誤差",
                ["pricing", "lesson"],
                ["numerical", "reference"],
                ["prices_image"],
                "Book/portalの欧州型価格を確認",
            ),
            requirement(
                5,
                "米国型の各平均・株価節点で早期行使を評価し印刷価格を再現する。",
                "vol06 §11.5：米国型の早期行使",
                ["pricing", "lesson"],
                ["numerical", "pricing_tests"],
                ["prices_image"],
                "Book/portalの米国型価格を確認",
            ),
            requirement(
                6,
                "小格子の全経路列挙と平均期待値恒等式を照合し、6小節・共有4図と既受入13節を再検証する。",
                "vol06 §11.1–11.6：94セル、両面2幅16状態",
                ["builder", "lesson", "portal"],
                ["numerical", "notebook_check"],
                ["grids_image", "interpolation_image", "prices_image", "exact_image"],
                "Book/portal実画面、数値改変拒否、既受入13節の再検証",
            ),
        ],
    )


def main():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    earlier = {f"26.{number}" for number in range(9, 18)} | {"27.1", "27.2", "27.3", "27.4"}
    for section in data["sections"]:
        if section["id"] in earlier:
            refresh_earlier(section)
        elif section["id"] == "27.5":
            register_path_dependent(section)
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.9–§27.5 ledger evidence for M14")


if __name__ == "__main__":
    main()
