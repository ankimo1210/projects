"""D1-preflight stage 4: negative controls for evidence reuse on a real section.

Each case mutates a copy of one input through an overlay (the project is never
written), recomputes the dependency fingerprint against a redrawn baseline and
checks the decision: an unrelated section added before the target may reuse
the baseline; a change to the section's text or values, a shared stylesheet,
script or plotly.js bundle, the hullkit sources, the reference data, the
rendering environment, an unknown dependency or an older normalizer must
redraw; missing or corrupted blobs must refuse reuse. Selected cases also run
the unmodified verifier to show the meaning checks still fail on a changed
value.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

try:
    from . import d1_preflight_compare as compare
    from . import evidence_fingerprint, evidence_record, evidence_store
except ImportError:  # executed as a script from johnhull/scripts
    import d1_preflight_compare as compare
    import evidence_fingerprint
    import evidence_record
    import evidence_store

_AUTO_ID = re.compile(r'(id="|href="#)id([0-9]+)"')
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"expected exactly one {old[:40]!r}, found {count}")
    return text.replace(old, new)


def renumber_auto_ids(html: str, shift: int) -> str:
    return _AUTO_ID.sub(lambda m: f'{m.group(1)}id{int(m.group(2)) + shift}"', html)


def bump_first_y(html: str, figure_key: str, delta: float) -> str:
    """Change the first y value of a portal figure payload (like the verifier's own check)."""
    start = html.index(f'Plotly.newPlot(                        "fig-{figure_key}"')
    match = re.compile(r'"y":\[(-?[0-9.eE+-]+)').search(html, start)
    value = float(match.group(1))
    return html[: match.start(1)] + repr(value + delta) + html[match.end(1) :]


def insert_unrelated_notebook_section(notebook: dict, before_heading: str) -> dict:
    """Insert a new section before a heading and renumber ids, counts and plot UUIDs."""
    notebook = copy.deepcopy(notebook)
    cells = notebook["cells"]
    index = next(
        i
        for i, cell in enumerate(cells)
        if cell["cell_type"] == "markdown" and "".join(cell["source"]).startswith(before_heading)
    )
    new_cells = [
        {
            "cell_type": "markdown",
            "id": "x",
            "metadata": {},
            "source": ["## 8b. 追加の節（負の対照）"],
        },
        {
            "cell_type": "code",
            "id": "x",
            "execution_count": None,
            "metadata": {},
            "source": ["print('unrelated')"],
            "outputs": [{"output_type": "stream", "name": "stdout", "text": ["unrelated\n"]}],
        },
    ]
    cells[index:index] = new_cells
    counter = 0
    for position, cell in enumerate(cells):
        cell["id"] = f"cell-{position:03d}"
        if cell["cell_type"] == "code":
            counter += 1
            cell["execution_count"] = counter
    text = json.dumps(notebook, ensure_ascii=False)
    fresh: dict[str, str] = {}
    text = _UUID.sub(lambda m: fresh.setdefault(m.group(0), str(uuid.uuid4())), text)
    return json.loads(text)


def _fingerprint(project, overlay_root, section, config, replacements, environment, spec):
    overlay = compare.build_overlay(
        project,
        overlay_root,
        spec["verifier_output_dir"],
        spec["verifier_inputs"],
        replacements=replacements,
    )
    return evidence_fingerprint.compute_fingerprint(overlay, section, config, environment), overlay


def _run_verifier(config_path: Path, section: str, project: Path, overlay: Path, spec: dict):
    result = compare._run(
        [
            "node",
            str(compare.SCRIPTS / "run_browser_verifier.cjs"),
            str(config_path),
            section,
            str(project),
            str(overlay),
        ],
        project,
        dict(__import__("os").environ),
    )
    record_path = overlay / spec["verifier_output_dir"] / "browser-check.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.is_file() else {}
    return {
        "exit_code": result["exit_code"],
        "status": record.get("status"),
        "error": record.get("error"),
    }


def run_controls(
    project: Path,
    records_root: Path,
    config_path: Path,
    baseline_path: str,
    reuse_path: str,
    work: Path,
    run_verifier: bool = True,
) -> dict:
    config = evidence_fingerprint.load_config(config_path)
    baseline = json.loads((records_root / baseline_path).read_text(encoding="utf-8"))
    reused = json.loads((records_root / reuse_path).read_text(encoding="utf-8"))
    section = baseline["section_id"]
    spec = config["sections"][section]
    base_fp = baseline["dependency_fingerprint"]
    environment = base_fp["components"]["environment"]
    notebook_path = spec["notebook"]["path"]
    book_page = spec["book"]["page"]
    portal_page = spec["portal"]["page"]
    heading = spec["book"]["heading"]
    read = lambda name: (project / name).read_text(encoding="utf-8")  # noqa: E731

    notebook = json.loads(read(notebook_path))
    book_html = read(book_page)
    portal_html = read(portal_page)
    section_open = book_html[book_html.rfind("<section", 0, book_html.index(f"<h2>{heading}")) :]
    section_tag = section_open[: section_open.index(">") + 1]
    first_card = portal_html.index('<figure class="fig-card">')

    def bundle_changed(nb: dict) -> dict:
        nb = copy.deepcopy(nb)
        for cell in nb["cells"]:
            for output in cell.get("outputs", []):
                html = output.get("data", {}).get("text/html")
                if html and "plotly.js v" in "".join(html):
                    joined = "".join(html).replace("plotly.js v", "plotly.js (patched) v", 1)
                    output["data"]["text/html"] = [joined]
                    return nb
        raise ValueError("no plotly.js bundle found")

    first_text_cell = next(
        cell
        for cell in notebook["cells"]
        if cell["cell_type"] == "markdown" and "".join(cell["source"]).startswith(f"## {heading}")
    )
    first_sentence = "".join(first_text_cell["source"]).split("\n")[1]
    edited_nb = copy.deepcopy(notebook)
    for cell in edited_nb["cells"]:
        if cell is not None and "".join(cell["source"]) == "".join(first_text_cell["source"]):
            cell["source"] = [
                "".join(cell["source"]).replace(first_sentence, first_sentence + "。")
            ]
    reference = read(spec["data"][0])
    unrelated_card = (
        '<figure class="fig-card"><figcaption><h3>負の対照</h3></figcaption>'
        '<div class="fig-holder"><div id="fig-d1_negative"></div></div></figure>\n'
    )
    unrelated_section = (
        '<section id="id1"><h2>8b. 追加の節（負の対照）</h2><div id="'
        + str(uuid.uuid4())
        + '" class="plotly-graph-div"></div></section>\n'
    )
    enc = lambda text: text.encode("utf-8")  # noqa: E731
    reference_data = json.loads(reference)
    shifted_reference = reference_data | {
        "strikes": [reference_data["strikes"][0] + 1, *reference_data["strikes"][1:]]
    }
    cases = [
        {
            "id": "unrelated_section_added",
            "mutation": "new section before §27.3 in the notebook (ids, counts, plot UUIDs "
            "regenerated), Book (auto ids shifted by one) and portal (new card)",
            "expected": "reuse",
            "replacements": {
                notebook_path: enc(
                    json.dumps(
                        insert_unrelated_notebook_section(notebook, f"## {heading}"),
                        ensure_ascii=False,
                        indent=1,
                    )
                ),
                book_page: enc(
                    replace_once(
                        renumber_auto_ids(book_html, 1),
                        section_tag,
                        unrelated_section + section_tag,
                    )
                ),
                portal_page: enc(
                    portal_html[:first_card] + unrelated_card + portal_html[first_card:]
                ),
            },
            "run_verifier": True,
            "verifier_expected": "PASS",
        },
        {
            "id": "section_text_changed",
            "mutation": "one character added to the §27.3 opening sentence (notebook)",
            "expected": "redraw",
            "replacements": {notebook_path: enc(json.dumps(edited_nb, ensure_ascii=False))},
        },
        {
            "id": "section_value_changed",
            "mutation": "first y value of the portal ivf_local payload +0.5",
            "expected": "redraw",
            "replacements": {portal_page: enc(bump_first_y(portal_html, "ivf_local", 0.5))},
            "run_verifier": True,
            "verifier_expected": "FAIL",
        },
        {
            "id": "shared_css_changed",
            "mutation": "one rule appended to the portal stylesheet",
            "expected": "redraw",
            "replacements": {
                "report/site/assets/style.css": enc(
                    read("report/site/assets/style.css")
                    + "\n.d1-negative-control { color: red; }\n"
                )
            },
        },
        {
            "id": "shared_js_changed",
            "mutation": "comment appended to the Book theme script",
            "expected": "redraw",
            "replacements": {
                "book/_build/html/_static/scripts/sphinx-book-theme.js": enc(
                    read("book/_build/html/_static/scripts/sphinx-book-theme.js") + "\n// d1\n"
                )
            },
        },
        {
            "id": "plotly_bundle_changed",
            "mutation": "embedded plotly.js bundle edited in the §27.1 output of the notebook",
            "expected": "redraw",
            "replacements": {
                notebook_path: enc(json.dumps(bundle_changed(notebook), ensure_ascii=False))
            },
        },
        {
            "id": "hullkit_source_changed",
            "mutation": "comment appended to hullkit/src/hullkit/local_volatility.py",
            "expected": "redraw",
            "replacements": {
                "hullkit/src/hullkit/local_volatility.py": enc(
                    read("hullkit/src/hullkit/local_volatility.py") + "\n# d1 negative control\n"
                )
            },
        },
        {
            "id": "reference_data_changed",
            "mutation": "one value in reference.json changed (first strike +1)",
            "expected": "redraw",
            "replacements": {
                spec["data"][0]: enc(
                    json.dumps(
                        shifted_reference,
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            },
            "run_verifier": True,
            "verifier_expected": "FAIL",
        },
    ]

    results = []
    for case in cases:
        root = work / case["id"]
        fingerprint, overlay = _fingerprint(
            project, root, section, config, case["replacements"], environment, spec
        )
        verdict = evidence_fingerprint.decide(base_fp, fingerprint)
        outcome = {
            "id": case["id"],
            "mutation": case["mutation"],
            "expected": case["expected"],
            "decision": verdict["decision"],
            "reasons": verdict["reasons"],
        }
        ok = verdict["decision"] == case["expected"]
        if run_verifier and case.get("run_verifier"):
            outcome["verifier"] = _run_verifier(config_path, section, project, overlay, spec)
            outcome["verifier_expected"] = case["verifier_expected"]
            ok = ok and outcome["verifier"]["status"] == case["verifier_expected"]
        outcome["status"] = "PASS" if ok else "FAIL"
        results.append(outcome)
        shutil.rmtree(root)

    # Environment, rules and unknown dependencies (no file mutation needed).
    def add(case_id, mutation, expected, verdict):
        results.append(
            {
                "id": case_id,
                "mutation": mutation,
                "expected": expected,
                "decision": verdict["decision"],
                "reasons": verdict["reasons"],
                "status": "PASS" if verdict["decision"] == expected else "FAIL",
            }
        )

    changed_env = copy.deepcopy(base_fp)
    fonts = changed_env["components"]["environment"]["fonts"]
    first_font = next(iter(fonts))
    fonts[first_font] = {"file": "DejaVuSans.ttf", "sha256": "0" * 64}
    add(
        "static_font_changed",
        f"fc-match result for {first_font!r} changed",
        "redraw",
        evidence_fingerprint.decide(base_fp, changed_env),
    )
    older = copy.deepcopy(base_fp)
    older["rules"]["normalizer_version"] -= 1
    add(
        "normalizer_changed",
        "baseline made with an older normalizer",
        "redraw",
        evidence_fingerprint.decide(older, base_fp),
    )
    unknown = evidence_fingerprint.compute_fingerprint(project, "27.4", config, environment)
    add(
        "undeclared_section",
        "section 27.4 has no dependency declaration",
        "redraw",
        evidence_fingerprint.decide(base_fp, unknown),
    )
    missing_config = copy.deepcopy(config)
    missing_config["sections"][section]["portal"]["page"] = "report/site/missing.html"
    missing = evidence_fingerprint.compute_fingerprint(
        project, section, missing_config, environment
    )
    add(
        "missing_build_output",
        "portal page not built",
        "redraw",
        evidence_fingerprint.decide(base_fp, missing),
    )

    runtime = baseline["environment"]["runtime"]
    changed_mathjax = copy.deepcopy(runtime["mathjax_scripts"])
    changed_mathjax[0]["sha256"] = "0" * 64
    changed_fonts = copy.deepcopy(runtime["fonts"])
    first_selector = next(iter(changed_fonts))
    changed_fonts[first_selector][0]["sha256"] = "0" * 64
    for key, value in (
        ("browser_version", "146.0.0.0"),
        ("mathjax_scripts", changed_mathjax),
        ("fonts", changed_fonts),
    ):
        mismatched = evidence_fingerprint.runtime_mismatches(runtime, runtime | {key: value})
        edited = copy.deepcopy(reused)
        edited["environment"]["runtime"][key] = value
        errors = evidence_record.validate_record(records_root, edited)
        results.append(
            {
                "id": f"runtime_{key}_changed",
                "mutation": f"observed {key} differs from the baseline run",
                "expected": "reuse refused",
                "decision": "reuse refused" if mismatched and errors else "reuse accepted",
                "reasons": errors,
                "status": "PASS" if mismatched and errors else "FAIL",
            }
        )

    # Missing and corrupted blobs, on temporary copies of the stores.
    primary = evidence_store.store_from_env("PROJECTS_ARTIFACT_STORE", role="primary")
    mirror = evidence_store.store_from_env("PROJECTS_ARTIFACT_MIRROR", role="mirror")
    temp = Path(tempfile.mkdtemp(prefix="stores-", dir=work))
    for label, damage in (("blob_missing", "primary"), ("blob_corrupted", "mirror")):
        stores = (
            evidence_store.init_store(temp / label / "primary", role="primary"),
            evidence_store.init_store(temp / label / "mirror", role="mirror"),
        )
        for entry in reused["images"]:
            digest = evidence_store.parse_ref(entry["ref"])
            for source, target in ((primary, stores[0]), (mirror, stores[1])):
                target.put_bytes(source.read_verified(digest, entry["bytes"]))
        victim = evidence_store.parse_ref(reused["images"][0]["ref"])
        blob = (stores[0] if damage == "primary" else stores[1]).blob_path(victim)
        blob.chmod(0o644)
        if label == "blob_missing":
            blob.unlink()
        else:
            data = bytearray(blob.read_bytes())
            data[len(data) // 2] ^= 1
            blob.write_bytes(bytes(data))
        errors = evidence_record.validate_record(
            records_root, reused, check_artifacts=True, stores=stores
        )
        copies = evidence_store.verify_copies(
            stores[0],
            stores[1],
            {
                "schema_version": 1,
                "kind": evidence_store.MANIFEST_KIND,
                "entries": reused["images"],
            },
            temp / label / "verify",
        )
        refused = bool(errors) and copies["status"] == "FAIL"
        results.append(
            {
                "id": label,
                "mutation": f"one baseline image {'deleted from' if label == 'blob_missing' else 'with one flipped byte in'} the {damage} copy",
                "expected": "reuse refused",
                "decision": "reuse refused" if refused else "reuse accepted",
                "reasons": errors,
                "copies": {role: copies[role]["status"] for role in ("primary", "mirror")},
                "status": "PASS" if refused else "FAIL",
            }
        )
    shutil.rmtree(temp)
    return {
        "schema_version": 1,
        "kind": "johnhull-d1-negative-controls",
        "created_at": datetime.now(UTC).isoformat(),
        "section_id": section,
        "baseline_record": baseline_path,
        "reuse_record": reuse_path,
        "status": "PASS" if all(item["status"] == "PASS" for item in results) else "FAIL",
        "cases": results,
    }


def public_report_paths(report: dict, project: Path, work: Path) -> dict:
    """Keep local checkout and scratch paths out of committed control records."""
    roots = sorted(
        ((str(project.resolve()), ""), (str(work.resolve()), "<work>")),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    def convert(value):
        if isinstance(value, str):
            for source, replacement in roots:
                value = value.replace(source + "/", replacement + ("/" if replacement else ""))
            return value
        if isinstance(value, list):
            return [convert(item) for item in value]
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        return value

    return convert(report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=compare.SCRIPTS.parent)
    parser.add_argument("--records-root", type=Path, default=compare.SCRIPTS.parent)
    parser.add_argument("--config", type=Path, default=evidence_fingerprint.DEFAULT_CONFIG)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--reuse", required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--out", required=True, help="records-root relative output path")
    args = parser.parse_args(argv)
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    report = run_controls(
        args.project_root.resolve(),
        args.records_root.resolve(),
        args.config.resolve(),
        args.baseline,
        args.reuse,
        work,
    )
    report = public_report_paths(report, args.project_root, work)
    out = args.records_root.resolve() / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for case in report["cases"]:
        print(
            f"{case['status']}  {case['id']}: expected {case['expected']}, got {case['decision']}"
            + (f", verifier {case['verifier']['status']}" if "verifier" in case else "")
        )
    print("overall:", report["status"])
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
