"""D3 Ch1 acceptance with independent cash references and complete section sweeps.

No schema or public API changes. Conceptual requirements use reasoned N/A;
every section requires explanation and Book/portal at both configured widths.
"""

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from johnhull.scripts import evidence_store

PROJECT = Path(__file__).resolve().parents[1]
OUT = "docs/validation/chapter-01"
CONFIG = "docs/acceptance/chapters/ch01.json"
NOTE = "docs/CHAPTER_01_ACCEPTANCE_2026-10-07.md"
SOURCES = [
    CONFIG,
    "hullkit/src/hullkit/_chapter01_lesson.py",
    "hullkit/src/hullkit/_intro_contracts.py",
    "hullkit/tests/_chapter01_reference.py",
    "hullkit/tests/test_chapter01_lesson.py",
    "report/tests/test_chapter01_acceptance.py",
    "report/report_builder/build.py",
    "report/tests/test_report_build.py",
    "volumes/12_qualitative_summary/build_summary_notebook.py",
    "volumes/12_qualitative_summary/qualitative_summary.ipynb",
    "scripts/build_chapter01_portal.py",
    "scripts/verify_chapter01_browser.cjs",
    "scripts/verify_chapter01_acceptance.py",
    "book/_config.yml",
    "book/_toc.yml",
]


def read(name):
    """Read a project-relative evidence file."""
    return json.loads((PROJECT / name).read_text())


def digest(name):
    """Hash exact bytes, keeping provenance distinct from numerical equality."""
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def write(name, data):
    """Save JSON with finite-number enforcement."""
    target = PROJECT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def hashes(names):
    """Collect every explicitly declared input, rejecting missing files."""
    return {name: digest(name) for name in names}


def fresh(record):
    """Reject failed records and stale source/artifact mappings."""
    if record.get("status") != "PASS":
        raise ValueError("evidence is not PASS")
    for key in ["source_sha256", "artifact_sha256"]:
        for name, expected in record.get(key, {}).items():
            if digest(name) != expected:
                raise ValueError("stale " + name)


def prepare():
    """Build a Decimal reference without hullkit, then compare displayed cash/curves."""
    file = PROJECT / "hullkit/tests/_chapter01_reference.py"
    spec = importlib.util.spec_from_file_location("ch1_reference", file)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    from hullkit import _chapter01_lesson as lesson

    if not Path(lesson.__file__).is_relative_to(PROJECT):
        raise ValueError("wrong checkout imported")
    reference = oracle.build()
    actual = {
        k: [dict(role=t.meta["role"], x=list(t.x), y=list(t.y)) for t in f.data]
        for k, f in lesson._figures().items()
    }
    error = max(
        oracle.compare(lesson._values(), reference["values"]),
        oracle.compare(actual, reference["figures"]),
    )
    if reference["printed_value_count"] != 37:
        raise ValueError("printed coverage missing")
    reference["labels"] = {v: k for k, v in lesson.VALUE_LABELS.items()}
    write(OUT + "/reference.json", reference)
    write(
        OUT + "/numerical-check.json",
        dict(
            status="PASS",
            chapter=1,
            printed_value_count=37,
            shared_figures=4,
            shared_build_sha256=hashlib.sha256(
                (PROJECT.parent / "Makefile").read_bytes()
            ).hexdigest(),
            shared_template_sha256=hashlib.sha256(
                (PROJECT.parent / "docs/templates/claude-report/tokens.css").read_bytes()
            ).hexdigest(),
            max_absolute_error=error,
            source_sha256=hashes(SOURCES),
            artifact_sha256=hashes([OUT + "/reference.json"]),
        ),
    )
    return dict(status="PASS", max_absolute_error=error)


def run(args):
    """Run checks in this worktree with the existing workspace environment."""
    subprocess.run(args, cwd=PROJECT.parent, check=True)


def cache_queries():
    """Restore exact historical HTML only for a nonsemantic MyST CSS cache query.

    Try two representations of the same local CSS bytes; accept solely the exact
    SHA-256 already required by each old record. Never change those records.
    """
    required = {}
    for section in read("docs/section_ledger.json")["sections"]:
        if section["status"] != "accepted" or section["id"].startswith("1."):
            continue
        for evidence in section["evidence"].values():
            if evidence["kind"] != "record":
                continue
            row = read(evidence["path"])
            for name, expected in row.get("artifact_sha256", {}).items():
                if name.endswith(".html"):
                    required.setdefault(name, set()).add(expected)
    changed = []
    for name, expected in required.items():
        if len(expected) != 1:
            raise ValueError("inconsistent old page pins: " + name)
        target = PROJECT / name
        wanted = next(iter(expected))
        if digest(name) == wanted:
            continue
        content = target.read_text()
        match = re.search(r'href="([^"]*mystnb\.[0-9a-f]+\.css)(?:\?v=[0-9a-f]+)?"', content)
        if not match:
            raise ValueError("old page changed; D1 needed: " + name)
        css = (target.parent / match.group(1)).resolve()
        checksum = hashlib.sha256(css.read_bytes()).hexdigest()[:8]
        before = digest(name)
        for query in ["", "?v=" + checksum]:
            candidate = (
                content[: match.start()]
                + f'href="{match.group(1)}{query}"'
                + content[match.end() :]
            )
            if hashlib.sha256(candidate.encode()).hexdigest() == wanted:
                target.write_text(candidate)
                changed.append(
                    dict(
                        page=name,
                        before=before,
                        after=wanted,
                        css_sha256=hashlib.sha256(css.read_bytes()).hexdigest(),
                    )
                )
                break
        else:
            raise ValueError("old page changed materially; D1 needed: " + name)
    write(
        OUT + "/book-cache-check.json",
        dict(
            status="PASS",
            changed=changed,
            policy="only local MyST stylesheet query; exact old HTML pins preserved",
            artifact_sha256={n: digest(n) for n in required},
        ),
    )


def build():
    """Build/fresh-execute vol12, both portals, and the Book before browser checks."""
    run([sys.executable, str(PROJECT / "volumes/12_qualitative_summary/build_summary_notebook.py")])
    import nbformat

    from johnhull.scripts.verify_core_notebooks import write_outputs

    target = PROJECT / "volumes/12_qualitative_summary/qualitative_summary.ipynb"
    metadata = nbformat.read(target, as_version=4).metadata
    errors = write_outputs(target)
    if errors:
        raise ValueError(errors)
    nb = nbformat.read(target, as_version=4)
    nb.metadata = metadata
    nbformat.write(nb, target)
    run([sys.executable, "-m", "report_builder.build"])
    run([sys.executable, str(PROJECT / "scripts/build_chapter01_portal.py")])
    run([str(Path(sys.executable).with_name("jupyter-book")), "build", str(PROJECT / "book")])
    cache_queries()
    return prepare()


def check_sweep(browser, cfg, reference):
    """Reject incomplete, duplicate, or inapplicable browser attestations."""
    expected = {(surface, w) for surface in ["book", "portal"] for w, _ in cfg["viewports"]}
    section_ids = {s["id"] for s in cfg["sections"]}
    if set(browser["sections"]) != section_ids:
        raise ValueError("section sweep coverage differs")
    figures = {
        "1.3": ["intro_forward"],
        "1.5": ["intro_options"],
        "1.7": ["intro_protection"],
        "1.8": ["intro_speculation"],
    }
    for sid, checks in browser["sections"].items():
        if {(r["surface"], r["width"]) for r in checks} != expected or len(checks) != len(expected):
            raise ValueError("missing/duplicate state: " + sid)
        for row in checks:
            if not row["explanation_checked"] or not row["layout_checked"]:
                raise ValueError("unchecked explanation/layout")
            count = len(reference["values"].get(sid, {}))
            if row["printed_value_count"] != count or row["printed_values_checked"] != bool(count):
                raise ValueError("printed values unchecked: " + sid)
            if row["checked_figures"] != figures.get(sid, []) or row[
                "figure_values_checked"
            ] != bool(figures.get(sid)):
                raise ValueError("figure values unchecked: " + sid)
    if not browser["book_mutation_rejected"] or not browser["portal_mutation_rejected"]:
        raise ValueError("numeric mutation not rejected")
    wanted = {(sid, surface, width) for sid in section_ids for surface, width in expected}
    captures = browser["captures"]
    actual = {(r["section"], r["surface"], r["width"]) for r in captures}
    if (
        actual != wanted
        or len(captures) != len(wanted)
        or len({r["path"] for r in captures}) != len(wanted)
    ):
        raise ValueError("capture coverage differs")
    if browser["state_checks"] != len(wanted):
        raise ValueError("state count differs")


def verify():
    """Check fresh notebook outputs, recorded browser semantics and all captures."""
    from johnhull.scripts.verify_core_notebooks import check_committed_outputs

    errors = check_committed_outputs(
        PROJECT / "volumes/12_qualitative_summary/qualitative_summary.ipynb"
    )
    if errors:
        raise ValueError(errors)
    numerical = read(OUT + "/numerical-check.json")
    browser = read(OUT + "/browser-check.json")
    fresh(numerical)
    fresh(browser)
    template_hash = hashlib.sha256(
        (PROJECT.parent / "docs/templates/claude-report/tokens.css").read_bytes()
    ).hexdigest()
    if numerical.get("shared_template_sha256") != template_hash:
        raise ValueError("stale shared report template")
    if (
        numerical.get("shared_build_sha256")
        != hashlib.sha256((PROJECT.parent / "Makefile").read_bytes()).hexdigest()
    ):
        raise ValueError("stale shared build route")
    if set(numerical["source_sha256"]) != set(SOURCES):
        raise ValueError("missing numerical source bindings")
    if numerical["printed_value_count"] != 37 or numerical["shared_figures"] != 4:
        raise ValueError("numerical coverage differs")
    cfg = read(CONFIG)
    check_sweep(browser, cfg, read(OUT + "/reference.json"))
    for item in browser["captures"]:
        if digest(item["path"]) != item["sha256"]:
            raise ValueError("changed capture")
    return dict(status="PASS", sections=10, states=40)


def bind():
    """Bind all checks and independently restore both immutable image copies."""
    verify()
    fresh(read(OUT + "/full-suite.json"))
    browser = read(OUT + "/browser-check.json")
    primary = evidence_store.store_from_env("PROJECTS_ARTIFACT_STORE", role="primary")
    mirror = evidence_store.store_from_env("PROJECTS_ARTIFACT_MIRROR", role="mirror")
    entries = []
    for i, item in enumerate(browser["captures"]):
        data = (PROJECT / item["path"]).read_bytes()
        info = primary.put_bytes(data)
        evidence_store.replicate(primary, mirror, [info["sha256"]])
        entries.append(evidence_store.manifest_entry(item["path"], data))
        if i % 10 == 9:
            print("stored captures:", i + 1, flush=True)
    manifest = dict(schema_version=1, kind=evidence_store.MANIFEST_KIND, entries=entries)
    with tempfile.TemporaryDirectory(prefix="hull-ch01-copies-") as work:
        copies = evidence_store.verify_copies(primary, mirror, manifest, work)
    if copies["status"] != "PASS":
        raise ValueError("image copies do not restore")
    write(OUT + "/image-manifest.json", manifest)
    cfg = read(CONFIG)
    record = dict(
        status="PASS",
        chapter=1,
        sections=[s["id"] for s in cfg["sections"]],
        requirements=sum(len(s["requirements"]) for s in cfg["sections"]),
        state_checks=40,
        storage_verification=copies,
        source_sha256=hashes(
            [
                *SOURCES,
                NOTE,
                OUT + "/numerical-check.json",
                OUT + "/browser-check.json",
                OUT + "/full-suite.json",
                OUT + "/image-manifest.json",
            ]
        ),
        artifact_sha256=hashes([cfg["book_page"], cfg["portal_page"]]),
    )
    write(OUT + "/acceptance-check.json", record)
    return dict(
        status="PASS", sections=10, requirements=record["requirements"], copies=copies["status"]
    )


def register():
    """Register each actual requirement, with N/A reasons for the unnecessary axes."""
    record = read(OUT + "/acceptance-check.json")
    fresh(record)
    cfg = read(CONFIG)
    ledger = read("docs/section_ledger.json")
    figreq = {
        "D1.3-01": "intro_forward",
        "D1.3-02": "intro_forward",
        "D1.5-01": "intro_options",
        "D1.5-02": "intro_options",
        "D1.7-02": "intro_protection",
        "D1.8-02": "intro_speculation",
    }
    conceptual = {"1.1", "1.2", "1.4", "1.6", "1.10"}
    for spec in cfg["sections"]:
        sid = spec["id"]
        evidence = {}
        for key, name, kind in [
            ("lesson", "hullkit/src/hullkit/_chapter01_lesson.py", "source"),
            ("notebook", "volumes/12_qualitative_summary/qualitative_summary.ipynb", "source"),
            ("implementation", "hullkit/src/hullkit/_intro_contracts.py", "source"),
            ("reference", OUT + "/reference.json", "reference"),
            ("numerical", OUT + "/numerical-check.json", "record"),
            ("browser", OUT + "/browser-check.json", "record"),
            ("integration", OUT + "/acceptance-check.json", "record"),
            ("acceptance_note", NOTE, "note"),
        ]:
            evidence[key] = dict(path=name, kind=kind, sha256=digest(name))
        for cap in read(OUT + "/browser-check.json")["captures"]:
            if cap["section"] == sid:
                key = cap["surface"] + "_" + str(cap["width"])
                evidence[key] = dict(path=cap["path"], kind="image", sha256=cap["sha256"])
        requirements = []
        for req in spec["requirements"]:
            rid = req["id"]
            qual = sid in conceptual or rid == "D1.5-03"
            coverage = dict(
                explanation=dict(
                    state="verified",
                    refs=["lesson", "notebook", "acceptance_note"],
                    locator=spec["heading"],
                ),
                rendered=dict(
                    state="verified", refs=["browser", "integration"], locator=spec["heading"]
                ),
            )
            for axis, refs in [
                ("implementation", ["implementation"]),
                ("independent_validation", ["numerical"]),
            ]:
                coverage[axis] = (
                    dict(
                        state="not_applicable",
                        refs=[],
                        reason="原典時点の制度・目的・歴史的観測の説明。計算モデルの要求ではなく、説明と両画面の到達・意味を確認する。",
                    )
                    if qual
                    else dict(state="verified", refs=refs, locator=spec["heading"])
                )
            coverage["visualization"] = (
                dict(state="verified", refs=["book_1000", "portal_1000"], locator=figreq[rid])
                if rid in figreq
                else dict(
                    state="not_applicable",
                    refs=[],
                    reason="制度・目的は文章で、少数の算術／通貨収支は単位付き表で確認できる要求。追加グラフを必要としない。",
                )
            )
            requirements.append(dict(id=rid, statement=req["statement"], coverage=coverage))
        row = next(s for s in ledger["sections"] if s["id"] == sid)
        row.update(
            status="accepted",
            reviewed_at="2026-10-07",
            source_pages=spec["source_pages"],
            scope="Hull GE Ch1の原典要点をD3方式で節別に確認。章末問題・現在の制度調査は含めない。",
            assumptions=[
                "Tables1.1–1.3のquoteは2020-05-21、市場規模は2019年末の原典記述。",
                "金額はUSD、為替USD/GBP、数量と契約倍率を明示。§1.3 carryは年5%の利息を含む。option/現物・先物の比較は手数料・資金利息を省略。",
            ],
            limitations=[
                "Americanの定義を説明するが利益図はEuropeanの終端比較。",
                "市場較正・現在の法令適用・将来予測を主張しない。",
            ],
            acceptance_note=NOTE,
            evidence=evidence,
            requirements=requirements,
        )
    from johnhull.scripts.verify_section_ledger import evaluate_ledger

    result = evaluate_ledger(PROJECT, read("docs/section_inventory.json"), ledger)
    if result["status"] != "PASS":
        raise ValueError("registration rejected before writing: " + str(result["errors"]))
    write("docs/section_ledger.json", ledger)
    return dict(status="PASS", registered=10)


def main():
    """Expose explicit stages so evidence is refreshed before ledger registration."""
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["build", "prepare", "verify", "bind", "register"])
    phase = parser.parse_args().phase
    print(json.dumps(globals()[phase](), ensure_ascii=False))


if __name__ == "__main__":
    main()
