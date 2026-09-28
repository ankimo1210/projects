"""Register §27.7 and connect fifteen accepted sections to their M16 D1 records."""

import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M16_CHECK = "docs/validation/section-27-7/m16-check.json"
RECHECK_DIR = "docs/validation/d1-recheck"
EARLIER = [f"26.{number}" for number in range(9, 18)] + [f"27.{number}" for number in range(1, 7)]


def digest(path):
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path, kind):
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs, locator):
    return {"state": "verified", "refs": refs, "locator": locator}


def m16_record(section_id):
    """The section's latest D1 record; older runs stay as history, a reuse needs its baseline."""
    folder = PROJECT / RECHECK_DIR / f"section-{section_id.replace('.', '-')}"
    records = sorted(
        path for path in folder.glob("*.json") if not path.name.endswith(".browser.json")
    )
    if not records:
        raise ValueError(f"no D1 record for §{section_id}")
    latest = json.loads(records[-1].read_text(encoding="utf-8"))
    baseline = (latest.get("baseline") or {}).get("record")
    if latest.get("decision") == "reused" and not (PROJECT / str(baseline)).is_file():
        raise ValueError(f"§{section_id}: reused record without its baseline")
    return records[-1].relative_to(PROJECT).as_posix()


def refresh_earlier(section):
    evidence = section["evidence"]
    evidence.pop("m15_check", None)
    evidence.pop("m15_recheck", None)
    record = m16_record(section["id"])
    evidence["m16_check"] = item(M16_CHECK, "record")
    evidence["m16_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    if section["id"].startswith("26."):
        evidence["notebook_check"] = item(M16_CHECK, "record")
    else:
        evidence["notebook_script"] = item("scripts/verify_two_asset_notebook.py", "source")
        evidence["notebook_check"] = item(
            "docs/validation/section-27-7/notebook-check.json", "record"
        )
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                {"m15_check": "m16_check", "m15_recheck": "m16_recheck"}.get(ref, ref)
                for ref in part["refs"]
            ]
        if section["id"] in ("27.3", "27.4", "27.5", "27.6"):
            refs = need["coverage"]["independent_validation"]["refs"]
            if "m16_recheck" not in refs:
                refs.append("m16_recheck")


def requirement(number, statement, locator, implementation, validation, figures, rendered):
    return {
        "id": f"TA{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m16_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_two_asset(section):
    paths = {
        "review": ("docs/SECTION_27_7_REVIEW_2026-09-28.md", "note"),
        "acceptance_note": ("docs/SECTION_27_7_ACCEPTANCE_2026-09-28.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/two_asset_tree.py", "source"),
        "pricing_tests": ("hullkit/tests/test_two_asset_tree.py", "test"),
        "reference_builder": ("scripts/build_two_asset_reference.py", "source"),
        "reference": ("docs/validation/section-27-7/reference.json", "reference"),
        "numerical_script": ("scripts/verify_two_asset_numerics.py", "source"),
        "numerical": ("docs/validation/section-27-7/numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_two_asset_tree_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_two_asset_tree_lesson.py", "test"),
        "notebook": ("volumes/06_numerical_methods/numerical.ipynb", "source"),
        "builder": ("volumes/06_numerical_methods/build_numerical_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_two_asset_notebook.py", "test"),
        "notebook_script": ("scripts/verify_two_asset_notebook.py", "source"),
        "notebook_check": ("docs/validation/section-27-7/notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "styles": ("report/assets/style.css", "source"),
        "browser_script": ("scripts/verify_two_asset_browser.cjs", "source"),
        "browser_run": ("docs/validation/section-27-7/browser-check.json", "record"),
        "m16_check": (M16_CHECK, "record"),
        "nodes_image": ("docs/validation/section-27-7/portal-two_asset_nodes-1000.png", "image"),
        "convergence_image": (
            "docs/validation/section-27-7/portal-two_asset_convergence-1000.png",
            "image",
        ),
        "errors_image": ("docs/validation/section-27-7/portal-two_asset_errors-1000.png", "image"),
        "correlation_image": (
            "docs/validation/section-27-7/portal-two_asset_correlation-1000.png",
            "image",
        ),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-09-28",
        source_pages=[658, 661],
        scope=(
            "Hull GE §27.7の相関のある二資産のオプション。無相関ツリーの積、変数変換、"
            "Rubinsteinの非矩形ツリー、確率の調整（Tables 27.2–27.3）、米国型の評価。"
            "vol06 §13とBook/portal実画面。"
        ),
        assumptions=[
            "S1=S2=K=100ドル、r=5%、q1=6%、q2=2%、σ1=20%、σ2=30%、ρ=0.5、満期1年。欧州型はStulzとMargrabeの式、米国型の交換オプションは1次元に帰着した値を基準とする。",
            "変数変換の二項は1段の平均と分散をともに合わせる（h=√(v+m²)。よく使う近似 h=σ√Δt ではない）。",
        ],
        limitations=[
            "定数パラメータの二資産のみ。三資産以上、確率ボラティリティ、相関の推定、金利ツリーへの応用は実装しない。",
            "格子の誤差は一次で残る。1次元に帰着できない米国型（maxコールなど）には独立の基準がなく、三構成とコントロール変量の一致で確かめる。",
        ],
        acceptance_note="docs/SECTION_27_7_ACCEPTANCE_2026-09-28.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "無相関の二変数は二つの二項ツリーの積で三次元ツリーにでき、枝の確率は積になることを示す。",
                "vol06 §13.1：無相関なら二つのツリーの積",
                ["pricing", "builder"],
                ["numerical", "pricing_tests"],
                ["nodes_image"],
                "Book/portalの1ステップの枝を確認",
            ),
            requirement(
                2,
                "変数変換 x1・x2 のドリフト・ボラティリティ・逆変換と二項の h_i・p_i を実装し、1段のモーメントの一致を確かめる。",
                "vol06 §13.2：変数を変換して無相関にする",
                ["pricing", "builder"],
                ["numerical", "reference"],
                ["nodes_image"],
                "Book/portalの変数変換の枝を確認",
            ),
            requirement(
                3,
                "Rubinsteinの非矩形ツリー（確率0.25、u1・d1・A–D）を実装し、ρ=0で代替二項ツリー2本と一致することを示す。",
                "vol06 §13.3：Rubinsteinの非矩形ツリー",
                ["pricing", "lesson"],
                ["numerical", "pricing_tests"],
                ["nodes_image", "correlation_image"],
                "Book/portalのRubinsteinの枝と相関の図を確認",
            ),
            requirement(
                4,
                "確率の調整（Tables 27.2・27.3）を再現し、周辺が代替二項ツリーのままで共分散が一致することを確かめる。",
                "vol06 §13.4：確率を調整する",
                ["pricing", "builder"],
                ["numerical", "pricing_tests"],
                ["nodes_image"],
                "Book/portalの確率の調整の枝を確認",
            ),
            requirement(
                5,
                "三つの構成で米国型を評価し、交換オプションを1次元に帰着した独立の基準と比べる。",
                "vol06 §13.5：米国型を評価する",
                ["pricing", "lesson"],
                ["numerical", "reference"],
                ["convergence_image"],
                "Book/portalの米国型交換オプションの収束を確認",
            ),
            requirement(
                6,
                "欧州型maxコールの収束と相関の端での挙動を測り、6小節・共有4図と既受入15節を再検証する。",
                "vol06 §13.5–13.6：120セル、両面2幅16状態",
                ["pricing", "builder", "lesson", "portal"],
                ["numerical", "notebook_check"],
                ["nodes_image", "convergence_image", "errors_image", "correlation_image"],
                "Book/portal実画面、数値改変拒否、既受入15節のD1再検査",
            ),
        ],
    )


def main():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
        elif section["id"] == "27.7":
            register_two_asset(section)
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.9–§27.7 ledger evidence for M16")


if __name__ == "__main__":
    main()
