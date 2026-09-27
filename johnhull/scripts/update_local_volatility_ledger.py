"""Register §27.3 and connect eleven accepted sections to final M12 evidence."""

import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M12_CHECK = "docs/validation/section-27-3/m12-check.json"
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


def refresh_earlier(section):
    evidence = section["evidence"]
    evidence.pop("m11_check", None)
    evidence.pop("m11_recheck", None)
    number = section["id"].replace(".", "-")
    evidence["m12_check"] = item(M12_CHECK, "record")
    evidence["m12_recheck"] = item(f"docs/validation/section-{number}/m12-recheck.json", "record")
    evidence["browser_run"] = item(
        f"docs/validation/section-{number}/browser-m12-recheck.json", "record"
    )
    if section["id"].startswith("26."):
        evidence["notebook_check"] = item(M12_CHECK, "record")
    else:
        evidence["notebook_script"] = item("scripts/verify_local_volatility_notebook.py", "source")
        evidence["notebook_check"] = item(
            "docs/validation/section-27-3/notebook-check.json", "record"
        )
    refresh_shared(evidence)
    rename_refs(section, {"m11_check": "m12_check", "m11_recheck": "m12_recheck"})
    if section["id"] == "27.2":
        for need in section["requirements"]:
            refs = need["coverage"]["independent_validation"]["refs"]
            if "m12_recheck" not in refs:
                refs.append("m12_recheck")


def requirement(number, statement, locator, implementation, validation, visualization, rendered):
    return {
        "id": f"IV{number:02d}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m12_check", *validation], locator),
            "visualization": covered(visualization, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_ivf(section):
    paths = {
        "review": ("docs/SECTION_27_3_REVIEW_2026-09-27.md", "note"),
        "acceptance_note": ("docs/SECTION_27_3_ACCEPTANCE_2026-09-27.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/local_volatility.py", "source"),
        "pricing_tests": ("hullkit/tests/test_local_volatility.py", "test"),
        "reference_builder": ("scripts/build_local_volatility_reference.py", "source"),
        "reference": ("docs/validation/section-27-3/reference.json", "reference"),
        "numerical_script": ("scripts/verify_local_volatility_numerics.py", "source"),
        "numerical": ("docs/validation/section-27-3/numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_local_volatility_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_local_volatility_lesson.py", "test"),
        "notebook": ("volumes/06_numerical_methods/numerical.ipynb", "source"),
        "builder": ("volumes/06_numerical_methods/build_numerical_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_local_volatility_notebook.py", "test"),
        "notebook_script": ("scripts/verify_local_volatility_notebook.py", "source"),
        "notebook_check": ("docs/validation/section-27-3/notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "styles": ("report/assets/style.css", "source"),
        "browser_script": ("scripts/verify_local_volatility_browser.cjs", "source"),
        "browser_run": ("docs/validation/section-27-3/browser-check.json", "record"),
        "m12_check": (M12_CHECK, "record"),
        "smile_image": ("docs/validation/section-27-3/portal-ivf_smile-1000.png", "image"),
        "local_image": ("docs/validation/section-27-3/portal-ivf_local-1000.png", "image"),
        "repricing_image": ("docs/validation/section-27-3/portal-ivf_repricing-1000.png", "image"),
        "joint_image": ("docs/validation/section-27-3/portal-ivf_joint-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-09-27",
        source_pages=[649, 650],
        scope=(
            "Hull GE §27.3の局所ボラ過程、式27.4、平滑な合成欧州コール面の適合、"
            "一時点の分布と二時点の同時分布の違い。vol06 §9とBook/portal実画面。"
        ),
        assumptions=[
            "S0=100、r=3%、q=1%、初期に15%/35%を0.7/0.3で選ぶ平滑な合成混合BSM市場。",
            "中央差分の幅はK方向0.05、T方向0.001年。欧州バニラ、連続配当。",
            "PDEは株価刻み0.5、年400ステップ、上限400。二時点MCは15万経路・200ステップ。",
        ],
        limitations=[
            "PDE価格には格子誤差が残る。二時点MCはEuler離散化と標本誤差を含み、一般的なexotic価格誤差上界ではない。",
            "実際の気配値の平滑化・補間、日次再較正、implied tree、市場エキゾチック価格、ヘッジ成績は評価しない。",
        ],
        acceptance_note="docs/SECTION_27_3_ACCEPTANCE_2026-09-27.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "IVFのリスク中立過程と欧州バニラ価格面への適合、逆算IVと局所ボラの違いを説明する。",
                "vol06 §9.1：平滑な混合BSMの3満期IV面",
                ["pricing", "builder"],
                ["numerical", "pricing_tests"],
                ["smile_image"],
                "Book/portalのIV面3満期を確認",
            ),
            requirement(
                2,
                "式27.4を瞬間r(T),q(T)と価格のT・K微分で実装し、非正の蝶型密度・局所分散を拒否する。",
                "vol06 §9.2：定数BSMと時変carryの極限",
                ["pricing", "builder"],
                ["numerical", "pricing_tests"],
                ["local_image"],
                "Bookの式27.4と中央差分値を確認",
            ),
            requirement(
                3,
                "平滑な合成価格面から局所ボラを求め、逆算IVとは異なることを解析式と照合する。",
                "vol06 §9.3：密度重みの解析式と33点",
                ["pricing", "lesson"],
                ["numerical", "pricing_tests"],
                ["smile_image", "local_image"],
                "Book/portalのIV・局所ボラ両面を確認",
            ),
            requirement(
                4,
                "局所ボラ過程で欧州バニラ価格を再現することを独立の後退PDEで測る。",
                "vol06 §9.4：3満期×3行使価格の9価格",
                ["reference_builder", "lesson"],
                ["numerical", "reference"],
                ["repricing_image"],
                "Book/portalの価格照合を確認",
            ),
            requirement(
                5,
                "各時点の限界分布一致が複数時点の同時分布を決めないことを示す。",
                "vol06 §9.5：潜在ボラ混合と局所ボラのpaired MC",
                ["reference_builder", "lesson"],
                ["numerical", "reference"],
                ["joint_image"],
                "Book/portalの二時点比較とSE表示を確認",
            ),
            requirement(
                6,
                "日次再較正・平滑化とexoticの限界を説明し、6小節・共有4図と既受入11節の退行検査を届ける。",
                "vol06 §9.1–9.6：70セル、両面2幅16状態",
                ["builder", "lesson", "portal", "styles"],
                ["numerical", "notebook_check"],
                ["smile_image", "local_image", "repricing_image", "joint_image"],
                "Book/portal実画面、数値改変拒否、既受入11節の再検証",
            ),
        ],
    )


def main():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    for section in data["sections"]:
        if section["id"] in {f"26.{n}" for n in range(9, 18)} | {"27.1", "27.2"}:
            refresh_earlier(section)
        elif section["id"] == "27.3":
            register_ivf(section)
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.9–§27.3 ledger evidence for M12")


if __name__ == "__main__":
    main()
