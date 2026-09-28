"""Register §27.6 and connect fourteen accepted sections to their M15 D1 records."""

import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M15_CHECK = "docs/validation/section-27-6/m15-check.json"
RECHECK_DIR = "docs/validation/d1-recheck"
EARLIER = [f"26.{number}" for number in range(9, 18)] + ["27.1", "27.2", "27.3", "27.4", "27.5"]


def digest(path):
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path, kind):
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs, locator):
    return {"state": "verified", "refs": refs, "locator": locator}


def m15_record(section_id):
    """The one schema-2 D1 record written for this section in M15."""
    folder = PROJECT / RECHECK_DIR / f"section-{section_id.replace('.', '-')}"
    records = sorted(
        path for path in folder.glob("*.json") if not path.name.endswith(".browser.json")
    )
    if len(records) != 1:
        raise ValueError(f"expected one M15 D1 record for §{section_id}, found {len(records)}")
    return records[0].relative_to(PROJECT).as_posix()


def refresh_earlier(section):
    evidence = section["evidence"]
    evidence.pop("m14_check", None)
    evidence.pop("m14_recheck", None)
    record = m15_record(section["id"])
    evidence["m15_check"] = item(M15_CHECK, "record")
    evidence["m15_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    if section["id"].startswith("26."):
        evidence["notebook_check"] = item(M15_CHECK, "record")
    else:
        evidence["notebook_script"] = item("scripts/verify_barrier_tree_notebook.py", "source")
        evidence["notebook_check"] = item(
            "docs/validation/section-27-6/notebook-check.json", "record"
        )
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                {"m14_check": "m15_check", "m14_recheck": "m15_recheck"}.get(ref, ref)
                for ref in part["refs"]
            ]
        if section["id"] in ("27.3", "27.4", "27.5"):
            refs = need["coverage"]["independent_validation"]["refs"]
            if "m15_recheck" not in refs:
                refs.append("m15_recheck")


def requirement(number, statement, locator, implementation, validation, figures, rendered):
    return {
        "id": f"BT{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m15_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_barrier_tree(section):
    paths = {
        "review": ("docs/SECTION_27_6_REVIEW_2026-09-28.md", "note"),
        "acceptance_note": ("docs/SECTION_27_6_ACCEPTANCE_2026-09-28.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/barrier_tree.py", "source"),
        "pricing_tests": ("hullkit/tests/test_barrier_tree.py", "test"),
        "reference_builder": ("scripts/build_barrier_tree_reference.py", "source"),
        "reference": ("docs/validation/section-27-6/reference.json", "reference"),
        "numerical_script": ("scripts/verify_barrier_tree_numerics.py", "source"),
        "numerical": ("docs/validation/section-27-6/numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_barrier_tree_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_barrier_tree_lesson.py", "test"),
        "notebook": ("volumes/06_numerical_methods/numerical.ipynb", "source"),
        "builder": ("volumes/06_numerical_methods/build_numerical_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_barrier_tree_notebook.py", "test"),
        "notebook_script": ("scripts/verify_barrier_tree_notebook.py", "source"),
        "notebook_check": ("docs/validation/section-27-6/notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "styles": ("report/assets/style.css", "source"),
        "browser_script": ("scripts/verify_barrier_tree_browser.cjs", "source"),
        "browser_run": ("docs/validation/section-27-6/browser-check.json", "record"),
        "m15_check": (M15_CHECK, "record"),
        "lattice_image": ("docs/validation/section-27-6/portal-barrier_lattice-1000.png", "image"),
        "convergence_image": (
            "docs/validation/section-27-6/portal-barrier_convergence-1000.png",
            "image",
        ),
        "errors_image": ("docs/validation/section-27-6/portal-barrier_errors-1000.png", "image"),
        "near_image": ("docs/validation/section-27-6/portal-barrier_near-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-09-28",
        source_pages=[656, 658],
        scope=(
            "Hull GE §27.6のバリア・オプションのツリー評価。素朴な二項・三項、内側・外側バリアと補間、"
            "ノードをバリア上に置く間隔と確率、初期価格がバリアに近いときの限界。vol06 §12とBook/portal実画面。"
        ),
        assumptions=[
            "欧州型up-and-outコール、S0=K=100ドル、H=120ドル、満期1年、r=5%、q=0%、σ=30%。連続監視の解析値を基準とする。",
            "三項の確率は対数収益率の平均と二次の素のモーメントに合わせる（分散はΔtの一次まで）。補間はバリアの株価で線形。",
        ],
        limitations=[
            "定数パラメータ・水平な単一バリアの欧州型ノックアウトのみ。ノックイン、米国型、二重バリア、adaptive meshは実装しない。",
            "格子の誤差は一次で残る。近すぎるバリアは拒否し、市場較正やヘッジ性能は検証しない。",
        ],
        acceptance_note="docs/SECTION_27_6_ACCEPTANCE_2026-09-28.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "素朴な方法（バリア以上のノードで0）を二項・三項で示し、収束が遅くのこぎり状に振れることを測る。",
                "vol06 §12.1：素朴な方法",
                ["pricing", "builder"],
                ["numerical", "reference"],
                ["convergence_image"],
                "Book/portalの20–300段の価格を確認",
            ),
            requirement(
                2,
                "内側・外側バリアを定義し、素朴なツリーが外側バリアを真のバリアとして評価することを示す。",
                "vol06 §12.2：Figure 27.4と外側バリア",
                ["pricing", "builder"],
                ["numerical", "pricing_tests"],
                ["lattice_image"],
                "Book/portalのノード配置と三本のバリアを確認",
            ),
            requirement(
                3,
                "内側・外側バリアを真とした二つの価格を求めて補間する。",
                "vol06 §12.3：内側と外側の補間",
                ["pricing", "lesson"],
                ["numerical", "pricing_tests"],
                ["convergence_image"],
                "Book/portalの補間価格を確認",
            ),
            requirement(
                4,
                "ノードをバリア上に置くN・ln u・三本の確率を原典の式で求め、平均と二次モーメントの一致を確かめる。",
                "vol06 §12.4：Figure 27.5と確率",
                ["pricing", "reference_builder"],
                ["numerical", "reference"],
                ["lattice_image"],
                "Book/portalのバリア上のノードを確認",
            ),
            requirement(
                5,
                "誤差を外側バリアの位置と格子の誤差に分け、バリア上のノードの一次収束を独立基準で測る。",
                "vol06 §12.4：誤差の分解と収束次数",
                ["pricing", "lesson"],
                ["numerical", "reference"],
                ["errors_image"],
                "Book/portalの誤差の分解を確認",
            ),
            requirement(
                6,
                "初期価格がバリアに近いときの限界（段がない・負の確率）とadaptive meshを説明し、6小節・共有4図と既受入14節を再検証する。",
                "vol06 §12.5–12.6：107セル、両面2幅16状態",
                ["pricing", "builder", "lesson", "portal"],
                ["numerical", "notebook_check"],
                ["lattice_image", "convergence_image", "errors_image", "near_image"],
                "Book/portal実画面、数値改変拒否、既受入14節のD1再検査",
            ),
        ],
    )


def main():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
        elif section["id"] == "27.6":
            register_barrier_tree(section)
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.9–§27.6 ledger evidence for M15")


if __name__ == "__main__":
    main()
