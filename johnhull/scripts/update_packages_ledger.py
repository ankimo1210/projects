"""Register §26.1 and connect seventeen accepted sections to their M18 D1 records."""

import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M18_CHECK = "docs/validation/section-26-1/m18-check.json"
RECHECK_DIR = "docs/validation/d1-recheck"
EARLIER = [f"26.{number}" for number in range(9, 18)] + [f"27.{number}" for number in range(1, 9)]


def digest(path):
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path, kind):
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs, locator):
    return {"state": "verified", "refs": refs, "locator": locator}


def m18_record(section_id):
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
    evidence.pop("m17_check", None)
    evidence.pop("m17_recheck", None)
    record = m18_record(section["id"])
    evidence["m18_check"] = item(M18_CHECK, "record")
    evidence["m18_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M18_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                {"m17_check": "m18_check", "m17_recheck": "m18_recheck"}.get(ref, ref)
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m18_recheck" not in refs:
            refs.append("m18_recheck")


def requirement(number, statement, locator, implementation, validation, figures, rendered):
    return {
        "id": f"PK{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m18_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_packages(section):
    paths = {
        "review": ("docs/SECTION_26_1_REVIEW_2026-09-29.md", "note"),
        "acceptance_note": ("docs/SECTION_26_1_ACCEPTANCE_2026-09-29.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/packages.py", "source"),
        "pricing_tests": ("hullkit/tests/test_packages.py", "test"),
        "reference_builder": ("scripts/build_packages_reference.py", "source"),
        "reference": ("docs/validation/section-26-1/reference.json", "reference"),
        "numerical_script": ("scripts/verify_packages_numerics.py", "source"),
        "numerical": ("docs/validation/section-26-1/numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_packages_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_packages_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_packages_notebook.py", "test"),
        "notebook_script": ("scripts/verify_packages_notebook.py", "source"),
        "notebook_check": ("docs/validation/section-26-1/notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "styles": ("report/assets/style.css", "source"),
        "browser_script": ("scripts/verify_packages_browser.cjs", "source"),
        "browser_run": ("docs/validation/section-26-1/browser-check.json", "record"),
        "m18_check": (M18_CHECK, "record"),
        "strikes_image": ("docs/validation/section-26-1/portal-packages_strikes-1000.png", "image"),
        "range_image": (
            "docs/validation/section-26-1/portal-packages_range_forward-1000.png",
            "image",
        ),
        "deferred_image": (
            "docs/validation/section-26-1/portal-packages_deferred-1000.png",
            "image",
        ),
        "risk_image": ("docs/validation/section-26-1/portal-packages_risk-1000.png", "image"),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-09-29",
        source_pages=[614, 615],
        scope=(
            "Hull GE §26.1のパッケージ。レンジ先渡し（ゼロコストのcollar、§17.2）、後払いオプション、"
            "ブレークフォワード、パッケージの損益と価値が脚の和であること、費用ゼロでもリスクが違うこと。"
            "vol10 §4.8とBook/portal実画面。"
        ),
        assumptions=[
            "原典が数値を挙げるのは§17.2の例（S0=1.32、r=rf=2%、σ=14%、T=0.25、K1=1.3000でK2=1.3414、p(1.30)=0.0273）だけ。曲線・後払い額・リスク比較はこの市場を使った独立参照の計算値で、原典の記述ではない。",
            "リスク比較は買う側、K1=0.95Fの1市場の例。損失確率はリスク中立の値。",
        ],
        limitations=[
            "定数r・q・σのBSM、欧州オプション、同一満期、連続な行使価格に限る。取引コスト、ビッドアスク、後払いの信用リスク、離散の行使価格は扱わない。",
            "K1>Fは拒否、K1=Fは先渡しそのもの、K1がFより極端に低くプットの価値が0に丸められるときはValueError。",
            "リスク比較の表は保存した独立参照にだけあり、hullkitの関数にはない。売る側は損益の符号が反転する。",
        ],
        acceptance_note="docs/SECTION_26_1_ACCEPTANCE_2026-09-29.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "パッケージが欧州コール・プット・先渡し・現金・原資産の組み合わせであり、満期損益も現在価値も脚の和になることを示す。",
                "vol10 §4.8.1：パッケージとは何か",
                ["pricing", "builder"],
                ["numerical", "reference", "pricing_tests"],
                ["range_image"],
                "Book/portalの満期損益の図を確認",
            ),
            requirement(
                2,
                "レンジ先渡しのゼロコスト条件c(K2)=p(K1)を実装し、§17.2の例（K2=1.3414、p(1.30)=0.0273）を再現する。K2は一意でK2>F、K1=Fは先渡し、K1>Fは拒否。",
                "vol10 §4.8.2：ゼロコストの条件",
                ["pricing", "builder"],
                ["numerical", "reference", "pricing_tests"],
                ["range_image"],
                "Book/portalの満期損益の図と§17.2の点を確認",
            ),
            requirement(
                3,
                "K1を動かしたときのK2の曲線（単調、K1=0.3FでK2=3.35F）とK1→Fでの傾きの極限N(σ√T/2)/N(−σ√T/2)を示す。",
                "vol10 §4.8.3：K1を動かすとK2はどう動くか",
                ["pricing", "lesson"],
                ["numerical", "reference"],
                ["strikes_image"],
                "Book/portalのK1とK2の図（原典の点とK1=Fの点つき）を確認",
            ),
            requirement(
                4,
                "後払いオプションA=c·e^{rT}（今日の価値0、最大損失A、損益分岐K±A）と、K=Fの後払いコールであるブレークフォワード（A=0.036855）を実装する。",
                "vol10 §4.8.4：プレミアムを満期に後払いする",
                ["pricing", "lesson"],
                ["numerical", "reference", "pricing_tests"],
                ["deferred_image"],
                "Book/portalの後払いの図を確認",
            ),
            requirement(
                5,
                "費用ゼロの三つ（先渡し、レンジ先渡し、ブレークフォワード）で期待損失の現在価値・損失確率・最大損失が違うことを、買う側で示す。",
                "vol10 §4.8.5：費用ゼロでもリスクは同じではない",
                ["builder", "lesson"],
                ["numerical", "reference"],
                ["risk_image"],
                "Book/portalのリスク比較の図を確認",
            ),
            requirement(
                6,
                "vol10 §4.8の6小節・共有4図、適用範囲と練習問題、既受入17節を再検証する。",
                "vol10 §4.8：136セル、両面2幅16状態",
                ["pricing", "builder", "lesson", "portal"],
                ["numerical", "notebook_check"],
                ["strikes_image", "range_image", "deferred_image", "risk_image"],
                "Book/portal実画面、数値改変拒否、既受入17節のD1再検査",
            ),
        ],
    )


def main():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
        elif section["id"] == "26.1":
            register_packages(section)
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.1 and §26.9–§27.8 ledger evidence for M18")


if __name__ == "__main__":
    main()
