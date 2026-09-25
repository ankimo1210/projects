"""Verify §27.1 delivery and nine earlier sections on the final M10 assets."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / "docs/validation/section-27-1/m10-check.json"
SECTION = "docs/validation/section-27-1/"


def digest(name):
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, str(PROJECT / "scripts"))
    from verify_alternative_models_notebook import check as check_numerical_notebook
    from verify_alternative_models_numerics import evaluate as check_numerics
    from verify_static_replication_notebook import check as check_exotics_notebook

    check_numerics()
    numerical_findings = check_numerical_notebook()
    if numerical_findings:
        raise ValueError(f"new vol06 notebook differs: {numerical_findings[:2]}")
    findings = check_exotics_notebook()
    if findings:
        raise ValueError(f"existing vol10 notebook changed: {findings[:2]}")

    records = [
        SECTION + name
        for name in ("numerical-check.json", "notebook-check.json", "browser-check.json")
    ]
    records.extend(
        f"docs/validation/section-26-{number}/m10-recheck.json" for number in range(9, 18)
    )
    records.extend(
        f"docs/validation/section-26-{number}/browser-m10-recheck.json" for number in range(9, 18)
    )
    for name in records:
        record = json.loads((PROJECT / name).read_text(encoding="utf-8"))
        if record.get("status") != "PASS":
            raise ValueError(f"not passing: {name}")
        for category in ("source_sha256", "artifact_sha256"):
            hashes = record.get(category, {})
            if isinstance(hashes, dict):
                for source, expected in hashes.items():
                    if digest(source) != expected:
                        raise ValueError(f"stale {category}: {name}: {source}")
    sources = [
        "scripts/build_alternative_models_acceptance_record.py",
        "scripts/build_alternative_models_reference.py",
        "scripts/verify_alternative_models_numerics.py",
        "scripts/verify_alternative_models_notebook.py",
        "scripts/verify_alternative_models_browser.cjs",
        "scripts/recheck_exotics_m10.py",
        "scripts/recheck_exotics_m10.cjs",
        "hullkit/src/hullkit/alternative_models.py",
        "hullkit/src/hullkit/_alternative_models_lesson.py",
        "hullkit/tests/test_alternative_models.py",
        "hullkit/tests/test_alternative_models_lesson.py",
        "report/tests/test_alternative_models_notebook.py",
        "report/report_builder/figures.py",
        "report/assets/style.css",
        "volumes/06_numerical_methods/build_numerical_notebook.py",
        "volumes/06_numerical_methods/numerical.ipynb",
        *records,
    ]
    artifacts = [
        SECTION + "reference.json",
        "report/site/numerics.html",
        "book/_build/html/notebooks/06_numerical.html",
        "report/site/exotics.html",
        "book/_build/html/notebooks/10_exotics.html",
        *(
            SECTION + f"{surface}-{key}-{width}.png"
            for surface in ("book", "portal")
            for key in (
                "alternative_cev",
                "alternative_merton",
                "alternative_poisson",
                "alternative_vg",
            )
            for width in (1440, 1000)
        ),
    ]
    result = {
        "section": "27.1",
        "status": "PASS",
        "numerical": "CEV PDE (3), original-Poisson Merton (26), gamma-integral VG (26), Table 27.1",
        "notebook": "46 fresh-executed cells; all cells outside §7 preserved; four exact saved Plotly payloads",
        "browser": "Book/portal, 1440/1000px, 16 numeric states, 16 screenshots",
        "regression": "nine accepted §26.9–§26.17 sections rerun in tests and browser",
        "exotics_notebook_fresh": True,
        "numerical_notebook_fresh": True,
        "independent_prices_fresh": True,
        "source_sha256": {name: digest(name) for name in sources},
        "artifact_sha256": {name: digest(name) for name in artifacts},
    }
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.is_file() or OUT.read_text(encoding="utf-8") != payload:
            raise ValueError("m10-check.json is missing or stale")
    else:
        OUT.write_text(payload, encoding="utf-8")
    print("PASS: §27.1 M10 acceptance record and nine earlier lessons")


if __name__ == "__main__":
    main()
