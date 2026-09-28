"""Register §27.8 and connect sixteen accepted sections to their M17 D1 records."""

import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M17_CHECK = "docs/validation/section-27-8/m17-check.json"
RECHECK_DIR = "docs/validation/d1-recheck"
EARLIER = [f"26.{number}" for number in range(9, 18)] + [f"27.{number}" for number in range(1, 8)]


def digest(path):
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path, kind):
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs, locator):
    return {"state": "verified", "refs": refs, "locator": locator}


def m17_record(section_id):
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
    evidence.pop("m16_check", None)
    evidence.pop("m16_recheck", None)
    record = m17_record(section["id"])
    evidence["m17_check"] = item(M17_CHECK, "record")
    evidence["m17_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    if section["id"].startswith("26."):
        evidence["notebook_check"] = item(M17_CHECK, "record")
    else:
        evidence["notebook_script"] = item("scripts/verify_american_mc_notebook.py", "source")
        evidence["notebook_check"] = item(
            "docs/validation/section-27-8/notebook-check.json", "record"
        )
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                {"m16_check": "m17_check", "m16_recheck": "m17_recheck"}.get(ref, ref)
                for ref in part["refs"]
            ]
        if section["id"] in ("27.3", "27.4", "27.5", "27.6", "27.7"):
            refs = need["coverage"]["independent_validation"]["refs"]
            if "m17_recheck" not in refs:
                refs.append("m17_recheck")


def requirement(number, statement, locator, implementation, validation, figures, rendered):
    return {
        "id": f"AM{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m17_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_american_mc(section):
    paths = {
        "review": ("docs/SECTION_27_8_REVIEW_2026-09-28.md", "note"),
        "acceptance_note": ("docs/SECTION_27_8_ACCEPTANCE_2026-09-28.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/american_mc.py", "source"),
        "pricing_tests": ("hullkit/tests/test_american_mc.py", "test"),
        "reference_builder": ("scripts/build_american_mc_reference.py", "source"),
        "reference": ("docs/validation/section-27-8/reference.json", "reference"),
        "numerical_script": ("scripts/verify_american_mc_numerics.py", "source"),
        "numerical": ("docs/validation/section-27-8/numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_american_mc_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_american_mc_lesson.py", "test"),
        "notebook": ("volumes/06_numerical_methods/numerical.ipynb", "source"),
        "builder": ("volumes/06_numerical_methods/build_numerical_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_american_mc_notebook.py", "test"),
        "notebook_script": ("scripts/verify_american_mc_notebook.py", "source"),
        "notebook_check": ("docs/validation/section-27-8/notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "styles": ("report/assets/style.css", "source"),
        "browser_script": ("scripts/verify_american_mc_browser.cjs", "source"),
        "browser_run": ("docs/validation/section-27-8/browser-check.json", "record"),
        "m17_check": (M17_CHECK, "record"),
        "regression_image": (
            "docs/validation/section-27-8/portal-american_mc_regression-1000.png",
            "image",
        ),
        "boundary_image": (
            "docs/validation/section-27-8/portal-american_mc_boundary-1000.png",
            "image",
        ),
        "bias_image": ("docs/validation/section-27-8/portal-american_mc_bias-1000.png", "image"),
        "dates_image": ("docs/validation/section-27-8/portal-american_mc_dates-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-09-28",
        source_pages=[660, 665],
        scope=(
            "Hull GE §27.8のモンテカルロ法によるアメリカン・オプション評価。最小二乗法（Longstaff–Schwartz）、"
            "行使境界のパラメータ化（Andersen）、推定と評価の経路の分離、行使日・基底・状態変数の拡張。"
            "vol06 §14とBook/portal実画面。"
        ),
        assumptions=[
            "原典の8経路の例はS0=1.00、K=1.10、r=6%、行使は1・2・3年目。多数の経路の実験はσ=20%を仮定し（原典に記載なし）、行使日の決まったプットの厳密値（対数正規の数値積分とCrank–Nicolson）を基準とする。",
            "二資産の例は§27.7の交換オプションを月1回行使とし、1次元に帰着した厳密値を基準とする。",
        ],
        limitations=[
            "回帰の基底は単項式だけ。Andersen–Broadieの上界、双対法、経路依存の状態の自動生成は実装しない。",
            "境界のパラメータ化は状態変数1個で、各時点の行使領域を臨界価格の片側とみなす。",
            "シミュレーションの主張は固定シードの標本に基づく統計的なもので、標準誤差とともに述べる。",
        ],
        acceptance_note="docs/SECTION_27_8_ACCEPTANCE_2026-09-28.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "原典の8経路（Table 27.4）で最小二乗法を再現する：回帰係数、継続価値（原典は印刷された係数で計算）、行使の判断（Tables 27.5–27.7）、価値0.1144が即時行使の0.10を上回ること。",
                "vol06 §14.1–14.2：8本の経路と最小二乗法",
                ["pricing", "builder"],
                ["numerical", "reference", "pricing_tests"],
                ["regression_image"],
                "Book/portalの回帰の図を確認",
            ),
            requirement(
                2,
                "行使境界のパラメータ化を再現する：候補ごとの平均価値、S*(2)=0.84とS*(1)=0.88の最適区間、時点0の0.1208（丸めない値0.12085）、問題27.15の方策の違い。",
                "vol06 §14.3：行使境界をパラメータ化する",
                ["pricing", "builder"],
                ["numerical", "reference", "pricing_tests"],
                ["boundary_image"],
                "Book/portalの境界の図を確認",
            ),
            requirement(
                3,
                "推定に使った経路を捨てて新しい経路で評価する方法を実装し、推定に使った経路での評価と新しい経路での評価の偏りを厳密なバミューダン価格と比べて示す。",
                "vol06 §14.4：推定に使った経路を捨てて評価する",
                ["pricing", "lesson"],
                ["numerical", "reference"],
                ["bias_image"],
                "Book/portalの偏りの図を確認",
            ),
            requirement(
                4,
                "行使日を増やすとアメリカンに近づくこと、2次と3次の基底（同じ評価経路でのペア差）、複数の状態変数での回帰（二資産の交換オプションと1次元に帰着した厳密値）を示す。",
                "vol06 §14.5：行使日・基底・状態変数",
                ["pricing", "lesson"],
                ["numerical", "reference"],
                ["dates_image"],
                "Book/portalの行使日の図を確認",
            ),
            requirement(
                5,
                "準最適な境界による下方バイアス、Andersen–Broadieの上界（原典は紹介のみで実装しない）、適用範囲と練習問題（27.15・27.22）を示す。",
                "vol06 §14.6：下方バイアス・上界・適用限界",
                ["builder", "lesson"],
                ["numerical", "reference"],
                ["bias_image", "dates_image"],
                "Book/portalの本文と図を確認",
            ),
            requirement(
                6,
                "vol06 §14の6小節・共有4図、旧LSM節の§15への組み替え（行使日50回の厳密値を導入に記載）、既受入16節を再検証する。",
                "vol06 §14–15：133セル、両面2幅16状態",
                ["pricing", "builder", "lesson", "portal"],
                ["numerical", "notebook_check"],
                ["regression_image", "boundary_image", "bias_image", "dates_image"],
                "Book/portal実画面、数値改変拒否、既受入16節のD1再検査",
            ),
        ],
    )


def main():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
        elif section["id"] == "27.8":
            register_american_mc(section)
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.9–§27.8 ledger evidence for M17")


if __name__ == "__main__":
    main()
