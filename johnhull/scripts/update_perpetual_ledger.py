"""Register §26.2 only after the M19 integrated gate passes on current assets."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
LEDGER = PROJECT / "docs/section_ledger.json"
M19_CHECK = "docs/validation/section-26-2/m19-check.json"
EARLIER = ["26.1", *[f"26.{n}" for n in range(9, 18)], *[f"27.{n}" for n in range(1, 9)]]


def digest(path: str) -> str:
    return hashlib.sha256((PROJECT / path).read_bytes()).hexdigest()


def item(path: str, kind: str) -> dict:
    return {"path": path, "kind": kind, "sha256": digest(path)}


def covered(refs: list[str], locator: str) -> dict:
    return {"state": "verified", "refs": refs, "locator": locator}


def require_m19_gate() -> None:
    path = PROJECT / M19_CHECK
    if not path.is_file():
        raise ValueError("M19 acceptance record is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if (
        record.get("section") != "26.2"
        or record.get("milestone") != "M19"
        or record.get("status") != "PASS"
    ):
        raise ValueError("M19 acceptance record is not passing")
    subprocess.run(
        [sys.executable, str(PROJECT / "scripts/build_perpetual_acceptance_record.py"), "--check"],
        cwd=PROJECT.parent,
        check=True,
    )


def m19_record(section_id: str) -> str:
    integrated = json.loads((PROJECT / M19_CHECK).read_text(encoding="utf-8"))
    try:
        selected = integrated["regression"]["d1"][section_id]["record"]
        expected = integrated["source_sha256"][selected]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"M19 selected D1 record missing for §{section_id}") from exc
    if not isinstance(selected, str):
        raise ValueError(f"M19 selected D1 path is invalid for §{section_id}: {selected!r}")
    relative = PurePosixPath(selected)
    folder = f"docs/validation/d1-recheck/section-{section_id.replace('.', '-')}/"
    if (
        not selected.startswith(folder)
        or relative.is_absolute()
        or ".." in relative.parts
        or "\\" in selected
        or not selected.endswith(".json")
    ):
        raise ValueError(f"M19 selected D1 path is invalid for §{section_id}: {selected!r}")
    if digest(selected) != expected:
        raise ValueError(f"M19 selected D1 record changed for §{section_id}: {selected}")
    return selected


def refresh_earlier(section: dict) -> None:
    evidence = section["evidence"]
    evidence.pop("m18_check", None)
    evidence.pop("m18_recheck", None)
    record = m19_record(section["id"])
    evidence["m19_check"] = item(M19_CHECK, "record")
    evidence["m19_recheck"] = item(record, "record")
    evidence["browser_run"] = item(record, "record")
    evidence["notebook_check"] = item(M19_CHECK, "record")
    for entry in evidence.values():
        entry["sha256"] = digest(entry["path"])
    for need in section["requirements"]:
        for part in need["coverage"].values():
            part["refs"] = [
                {"m18_check": "m19_check", "m18_recheck": "m19_recheck"}.get(ref, ref)
                for ref in part["refs"]
            ]
        refs = need["coverage"]["independent_validation"]["refs"]
        if "m19_recheck" not in refs:
            refs.append("m19_recheck")


def requirement(
    number: int,
    statement: str,
    locator: str,
    implementation: list[str],
    validation: list[str],
    figures: list[str],
    rendered: str,
) -> dict:
    return {
        "id": f"PA{number:02}",
        "statement": statement,
        "coverage": {
            "explanation": covered(["builder", "review", "acceptance_note"], locator),
            "implementation": covered(implementation, locator),
            "independent_validation": covered(["m19_check", *validation], locator),
            "visualization": covered(figures, locator),
            "rendered": covered(["browser_run", "notebook_check"], rendered),
        },
    }


def register_perpetual(section: dict) -> None:
    paths = {
        "review": ("docs/SECTION_26_2_REVIEW_2026-09-29.md", "note"),
        "acceptance_note": ("docs/SECTION_26_2_ACCEPTANCE_2026-09-29.md", "note"),
        "textbook": ("options, futures and other derivatives 11th.pdf", "reference"),
        "pricing": ("hullkit/src/hullkit/perpetual_american.py", "source"),
        "pricing_tests": ("hullkit/tests/test_perpetual_american.py", "test"),
        "reference_builder": ("scripts/build_perpetual_reference.py", "source"),
        "reference_tests": ("hullkit/tests/test_perpetual_reference_builder.py", "test"),
        "reference": ("docs/validation/section-26-2/reference.json", "reference"),
        "numerical_script": ("scripts/verify_perpetual_numerics.py", "source"),
        "numerical_tests": ("hullkit/tests/test_perpetual_numerics_gate.py", "test"),
        "numerical": ("docs/validation/section-26-2/numerical-check.json", "reference"),
        "lesson": ("hullkit/src/hullkit/_perpetual_american_lesson.py", "source"),
        "lesson_tests": ("hullkit/tests/test_perpetual_american_lesson.py", "test"),
        "notebook": ("volumes/10_exotics_martingales/exotics.ipynb", "source"),
        "builder": ("volumes/10_exotics_martingales/build_exotics_notebook.py", "source"),
        "notebook_tests": ("report/tests/test_perpetual_american_notebook.py", "test"),
        "notebook_script": ("scripts/verify_perpetual_notebook.py", "source"),
        "notebook_check": ("docs/validation/section-26-2/notebook-check.json", "record"),
        "portal": ("report/report_builder/figures.py", "source"),
        "styles": ("report/assets/style.css", "source"),
        "browser_script": ("scripts/verify_perpetual_browser.cjs", "source"),
        "browser_run": ("docs/validation/section-26-2/browser-check.json", "record"),
        "m19_check": (M19_CHECK, "record"),
        "value_image": ("docs/validation/section-26-2/portal-perpetual_value-1000.png", "image"),
        "boundaries_image": (
            "docs/validation/section-26-2/portal-perpetual_boundaries-1000.png",
            "image",
        ),
        "zero_yield_image": (
            "docs/validation/section-26-2/portal-perpetual_zero_dividend-1000.png",
            "image",
        ),
        "convergence_image": (
            "docs/validation/section-26-2/portal-perpetual_convergence-1000.png",
            "image",
        ),
    }
    section.update(
        status="accepted",
        reviewed_at="2026-09-29",
        source_pages=[615, 616],
        scope=(
            "Hull GE §26.2の永久アメリカン・コールとプット。特性方程式、価値一致と滑らかな接続、"
            "有限または無限の行使境界、無配当コールの極限、有限満期CRRとの比較。"
            "vol10 §4.9とBook/portal実画面。"
        ),
        assumptions=[
            "原典§26.2に印刷された数値例はない。6市場の価格・境界・有限満期格子は独立参照から作成した教材上の例である。",
            "原資産は幾何ブラウン運動、r>0、q>=0、σ>0を定数とする。SとKは正の有限値、満期は無限。",
        ],
        limitations=[
            "有限満期CRRは満期20/40/80/160年、年10ステップの近似。永久解との差は有限満期と離散格子の両方を含み、厳密な誤差上界ではない。",
            "無配当コールは価値S・行使境界は無限として扱う。市場摩擦、離散配当、確率的金利/利回り/ボラティリティは扱わない。",
        ],
        acceptance_note="docs/SECTION_26_2_ACCEPTANCE_2026-09-29.md",
        evidence={name: item(path, kind) for name, (path, kind) in paths.items()},
        requirements=[
            requirement(
                1,
                "永久アメリカン・オプションの特性方程式と正負の指数を示し、継続価値を解析する。",
                "vol10 §4.9.1：永久オプションの前提と指数",
                ["pricing", "builder"],
                ["numerical", "reference", "pricing_tests"],
                ["value_image"],
                "Book/portalの価格曲線を確認",
            ),
            requirement(
                2,
                "配当利回りが正のコールとプットの有限行使境界・価値一致・滑らかな接続を実装する。",
                "vol10 §4.9.2–4.9.3：コールとプットの境界",
                ["pricing", "lesson"],
                ["numerical", "reference", "reference_tests"],
                ["value_image", "boundaries_image"],
                "Book/portalの価値と行使境界を確認",
            ),
            requirement(
                3,
                "無配当コールでは有限の行使境界がなく、永久価値がSになる極限を示す。",
                "vol10 §4.9.4：無配当コールの極限",
                ["pricing", "lesson"],
                ["numerical", "reference", "pricing_tests"],
                ["zero_yield_image"],
                "Book/portalの無配当コールの図を確認",
            ),
            requirement(
                4,
                "独立した有限満期CRRの後退帰納（20/40/80/160年）と永久解析値の差を比較する。",
                "vol10 §4.9.5：有限満期からの接近",
                ["reference_builder", "builder"],
                ["numerical", "reference", "numerical_tests"],
                ["convergence_image"],
                "Book/portalの有限満期比較図を確認",
            ),
            requirement(
                5,
                "適用条件、境界の例外、有限満期格子の誤差の読み方を明示する。",
                "vol10 §4.9.6：条件と限界",
                ["pricing", "builder"],
                ["numerical", "reference"],
                ["boundaries_image", "convergence_image"],
                "Book/portalの条件説明と図を確認",
            ),
            requirement(
                6,
                "vol10 §4.9の6小節・共有4図、節外セルと既受入18節の保持、両画面の表示を再検証する。",
                "vol10 §4.9とBook/portalの共有図",
                ["pricing", "builder", "lesson", "portal"],
                ["numerical", "notebook_check"],
                ["value_image", "boundaries_image", "zero_yield_image", "convergence_image"],
                "Book/portalの16状態と数値改変拒否、既受入18節のD1再検査",
            ),
        ],
    )


def main() -> None:
    require_m19_gate()
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    seen = set()
    for section in data["sections"]:
        if section["id"] in EARLIER:
            refresh_earlier(section)
            seen.add(section["id"])
        elif section["id"] == "26.2":
            register_perpetual(section)
            seen.add(section["id"])
    expected = {*EARLIER, "26.2"}
    if seen != expected:
        raise ValueError(f"M19 ledger sections missing: {sorted(expected - seen)}")
    LEDGER.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated §26.2 and eighteen earlier sections for M19")


if __name__ == "__main__":
    main()
