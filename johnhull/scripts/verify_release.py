"""Verify the johnhull A5--A8 release contract without mutating artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np

try:
    from .frontier_acceptance import evaluate_acceptance
except ImportError:  # direct script execution
    from frontier_acceptance import evaluate_acceptance

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "johnhull"
MANIFEST = PROJECT / "release_manifest.json"


@dataclass(frozen=True)
class Finding:
    check: str
    detail: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(
            handle,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"non-finite JSON constant: {value}")
            ),
        )
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    stack: list[tuple[str, object]] = [("$", payload)]
    while stack:
        location, value = stack.pop()
        if isinstance(value, float) and not np.isfinite(value):
            raise ValueError(f"non-finite JSON number at {location}: {value}")
        if isinstance(value, dict):
            stack.extend((f"{location}.{key}", item) for key, item in value.items())
        elif isinstance(value, list):
            stack.extend((f"{location}[{index}]", item) for index, item in enumerate(value))
    return payload


def _check_npz_schema(
    path: Path,
    declared: dict,
    findings: list[Finding],
) -> None:
    try:
        with np.load(path, allow_pickle=False) as payload:
            names = set(payload.files)
            if names != set(declared):
                findings.append(
                    Finding(
                        "reference-schema",
                        f"array names differ for {path}: actual={sorted(names)}, declared={sorted(declared)}",
                    )
                )
                return
            for name in sorted(names):
                array = payload[name]
                schema = declared[name]
                if list(array.shape) != schema.get("shape"):
                    findings.append(Finding("reference-schema", f"shape mismatch: {path}:{name}"))
                if str(array.dtype) != schema.get("dtype"):
                    findings.append(Finding("reference-schema", f"dtype mismatch: {path}:{name}"))
                if not isinstance(schema.get("unit"), str) or not schema["unit"].strip():
                    findings.append(Finding("reference-schema", f"unit missing: {path}:{name}"))
                if array.dtype.kind == "O":
                    findings.append(
                        Finding("reference-schema", f"object dtype forbidden: {path}:{name}")
                    )
                elif array.dtype.kind in "biufc" and not np.all(np.isfinite(array)):
                    findings.append(
                        Finding("reference-schema", f"non-finite values: {path}:{name}")
                    )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        findings.append(Finding("reference-schema", f"invalid NPZ {path}: {exc}"))


def _check_reference(
    path: Path,
    expected_volume: int,
    findings: list[Finding],
    *,
    expected_semantic_sources: list[str],
    expected_semantic_tests: list[str],
    expected_companions: list[str],
) -> None:
    if not path.exists():
        findings.append(Finding("reference", f"missing: {path.relative_to(ROOT)}"))
        return
    if path.suffix == ".json":
        try:
            payload = _load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            findings.append(Finding("reference", f"invalid JSON {path}: {exc}"))
            return
        required = {
            "schema_version",
            "volume",
            "generated_by",
            "data_policy",
            "artifact_role",
            "metrics",
            "acceptance",
            "companions",
            "companion_schemas",
            "limitations",
        }
        missing = sorted(required - payload.keys())
        if missing:
            findings.append(Finding("reference", f"{path}: missing fields {missing}"))
        if payload.get("data_policy") != "synthetic-offline":
            findings.append(Finding("reference", f"{path}: data_policy must be synthetic-offline"))
        if payload.get("schema_version") != 1:
            findings.append(Finding("reference", f"{path}: schema_version must equal 1"))
        if payload.get("volume") != expected_volume:
            findings.append(
                Finding(
                    "reference",
                    f"{path}: volume={payload.get('volume')} expected={expected_volume}",
                )
            )
        if payload.get("semantic_sources") != expected_semantic_sources:
            findings.append(Finding("semantics", f"{path}: semantic_sources mismatch"))
        if payload.get("semantic_tests") != expected_semantic_tests:
            findings.append(Finding("semantics", f"{path}: semantic_tests mismatch"))
        expected_generator = (
            "deep_hedge_price/scripts/export_johnhull_pricing_reference.py"
            if expected_volume == 18
            else "johnhull/scripts/build_frontier_artifacts.py"
        )
        if payload.get("generated_by") != expected_generator:
            findings.append(
                Finding("reference", f"{path}: generated_by must equal {expected_generator}")
            )
        if (
            not isinstance(payload.get("artifact_role"), str)
            or not payload["artifact_role"].strip()
        ):
            findings.append(Finding("reference", f"{path}: artifact_role must be non-empty"))
        metrics = payload.get("metrics")
        if not isinstance(metrics, dict) or not metrics:
            findings.append(Finding("reference", f"{path}: metrics must be a non-empty object"))
        limitations = payload.get("limitations")
        if (
            not isinstance(limitations, list)
            or not limitations
            or not all(isinstance(value, str) and value.strip() for value in limitations)
        ):
            findings.append(Finding("reference", f"{path}: limitations must be non-empty strings"))
        if expected_volume >= 19:
            expected_api = (
                "deep_hedge_price.frontier_reference.build_frontier_reference"
                if expected_volume in {19, 20}
                else "hullkit.frontier_reference.build_frontier_reference"
            )
            if payload.get("generator_api") != expected_api:
                findings.append(
                    Finding("reference", f"{path}: generator_api must equal {expected_api}")
                )
            if not isinstance(payload.get("seed"), int):
                findings.append(Finding("reference", f"{path}: integer seed is required"))
        companions = payload.get("companions", {})
        if not isinstance(companions, dict):
            findings.append(Finding("reference", f"{path}: companions must be an object"))
            return
        expected_names = {Path(name).name for name in expected_companions}
        if set(companions) != expected_names:
            findings.append(
                Finding(
                    "reference",
                    f"{path}: companions must exactly match {sorted(expected_names)}",
                )
            )
        schemas = payload.get("companion_schemas", {})
        if not isinstance(schemas, dict) or set(schemas) != expected_names:
            findings.append(
                Finding(
                    "reference-schema",
                    f"{path}: companion_schemas must exactly match {sorted(expected_names)}",
                )
            )
            schemas = {}
        loaded_arrays: dict[str, np.ndarray] = {}
        for relative, expected in companions.items():
            companion = path.parent / relative
            if not companion.exists():
                findings.append(Finding("fingerprint", f"missing companion: {companion}"))
            elif _sha256(companion) != expected:
                findings.append(Finding("fingerprint", f"digest mismatch: {companion}"))
            elif companion.suffix == ".npz":
                declared = schemas.get(relative)
                if not isinstance(declared, dict):
                    findings.append(Finding("reference-schema", f"schema missing: {companion}"))
                else:
                    _check_npz_schema(companion, declared, findings)
                try:
                    with np.load(companion, allow_pickle=False) as archive:
                        loaded_arrays.update({name: archive[name].copy() for name in archive.files})
                except (OSError, ValueError, zipfile.BadZipFile):
                    pass
        acceptance = payload.get("acceptance")
        if not isinstance(acceptance, dict):
            findings.append(Finding("acceptance", f"{path}: acceptance must be an object"))
        elif metrics and loaded_arrays:
            try:
                canonical = evaluate_acceptance(expected_volume, metrics, loaded_arrays)
            except (KeyError, TypeError, ValueError) as exc:
                findings.append(Finding("acceptance", f"{path}: cannot recompute: {exc}"))
            else:
                if acceptance != canonical:
                    findings.append(
                        Finding(
                            "acceptance", f"{path}: stored acceptance differs from recomputation"
                        )
                    )
                if canonical["passed"] is not True:
                    failed = [check["name"] for check in canonical["checks"] if not check["passed"]]
                    findings.append(Finding("acceptance", f"{path}: gate failed checks {failed}"))
                if canonical["model_performance_approved"] is not False:
                    findings.append(
                        Finding("acceptance", f"{path}: model performance must not be approved")
                    )


def _check_notebook(path: Path, forbidden: list[str], findings: list[Finding]) -> None:
    if not path.exists():
        findings.append(Finding("notebook", f"missing: {path.relative_to(ROOT)}"))
        return
    try:
        notebook = _load_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        findings.append(Finding("notebook", f"invalid notebook {path}: {exc}"))
        return
    cells = notebook.get("cells", [])
    metadata = notebook.get("metadata", {}).get("johnhull", {})
    if metadata.get("artifact_only") is not True:
        findings.append(Finding("notebook", f"artifact_only metadata missing: {path}"))
    source = "\n".join(
        "".join(cell.get("source", []))
        if isinstance(cell.get("source", []), list)
        else str(cell.get("source", ""))
        for cell in cells
    )
    for token in forbidden:
        if token in source:
            findings.append(Finding("notebook", f"forbidden token {token!r}: {path}"))
    if "限界" not in source and "Limitations" not in source:
        findings.append(Finding("notebook", f"limitations section missing: {path}"))
    if "参考文献" not in source and "References" not in source:
        findings.append(Finding("notebook", f"citations section missing: {path}"))
    code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
    if not code_cells:
        findings.append(Finding("notebook", f"no code cells: {path}"))
    for cell in code_cells:
        if not isinstance(cell.get("execution_count"), int):
            findings.append(Finding("notebook", f"unexecuted code cell in {path}"))
        for output in cell.get("outputs", []):
            if output.get("output_type") == "error":
                findings.append(Finding("notebook", f"error output in {path}"))


def _check_version_control_candidate(
    path: Path,
    *,
    require_tracked: bool,
    findings: list[Finding],
) -> None:
    if not path.exists() and not path.is_symlink():
        return
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", str(path)],
        cwd=ROOT,
        check=False,
    )
    if ignored.returncode == 0:
        findings.append(
            Finding("version-control", f"release file is ignored: {path.relative_to(ROOT)}")
        )
    if require_tracked:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path.relative_to(ROOT))],
            cwd=ROOT,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if tracked.returncode != 0:
            findings.append(
                Finding("version-control", f"release file is untracked: {path.relative_to(ROOT)}")
            )
        else:
            changed = subprocess.run(
                ["git", "diff", "--quiet", "HEAD", "--", str(path.relative_to(ROOT))],
                cwd=ROOT,
                check=False,
            )
            if changed.returncode != 0:
                findings.append(
                    Finding(
                        "version-control",
                        f"release file differs from HEAD: {path.relative_to(ROOT)}",
                    )
                )


def verify(*, require_tracked: bool = False) -> list[Finding]:
    release = _load_json(MANIFEST)
    findings: list[Finding] = []
    if release.get("schema_version") != 1:
        findings.append(Finding("manifest", "release manifest schema_version must equal 1"))
    volumes = release.get("volumes")
    if not isinstance(volumes, list):
        return [*findings, Finding("manifest", "release manifest volumes must be a list")]
    numbers = [item.get("number") for item in volumes if isinstance(item, dict)]
    if numbers != list(range(18, 28)):
        findings.append(
            Finding("manifest", f"volume numbers must exactly equal 18..27, got {numbers}")
        )
    toc = (PROJECT / "book/_toc.yml").read_text(encoding="utf-8")
    roadmap = (PROJECT / "ROADMAP.md").read_text(encoding="utf-8")
    forbidden = list(release["forbidden_notebook_tokens"])

    release_files = [
        MANIFEST,
        PROJECT / "ROADMAP.md",
        PROJECT / "VALIDATION.md",
        PROJECT / "docs/DATA_PROVENANCE.md",
        PROJECT / "research_profiles.json",
        PROJECT / "README.md",
        PROJECT / "book/_toc.yml",
        PROJECT / "book/notebooks/00_overview.md",
        PROJECT / "report/README.md",
        ROOT / "Makefile",
        ROOT / "docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-options.md",
        ROOT / "docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-a5-design.md",
        ROOT / "docs/superpowers/plans/2026-07-18-johnhull-beyond-hull-a5.md",
        ROOT / "docs/superpowers/plans/2026-07-18-johnhull-beyond-hull-g4-g7.md",
        PROJECT / "book/_config.yml",
        PROJECT / "book/_static/require.min.js",
        PROJECT / "book/_static/requirejs-LICENSE.txt",
        PROJECT / "scripts/frontier_acceptance.py",
        PROJECT / "scripts/build_frontier_artifacts.py",
        PROJECT / "scripts/build_frontier_notebooks.py",
        PROJECT / "scripts/verify_frontier_artifacts.py",
        PROJECT / "scripts/verify_frontier_notebooks.py",
        PROJECT / "scripts/verify_release.py",
        PROJECT / "report/report_builder/frontier_figures.py",
        PROJECT / "report/report_builder/figures.py",
        PROJECT / "report/templates/base.html.j2",
        PROJECT / "report/templates/gallery.html.j2",
        PROJECT / "report/tests/test_report_build.py",
        PROJECT / "report/tests/test_release_contract.py",
        ROOT / "deep_hedge_price/scripts/export_johnhull_pricing_reference.py",
    ]
    release_files.extend(
        [
            ROOT / "deep_hedge_price/.gitignore",
            ROOT / "deep_hedge_price/Makefile",
            ROOT / "deep_hedge_price/README.md",
            ROOT / "deep_hedge_price/docs/ROADMAP_DEEP_PRICING.md",
            ROOT / "deep_hedge_price/artifacts/pricing/.gitkeep",
            ROOT / "deep_hedge_price/notebooks/02_neural_pricing_surrogate.ipynb",
            ROOT / "deep_hedge_price/reports/02_neural_pricing_surrogate.html",
            ROOT / "deep_hedge_price/reports/neural_pricing_report_quick.html",
            ROOT / "deep_hedge_price/reports/pricing_ablation_quick.json",
            PROJECT / "hullkit/pyproject.toml",
        ]
    )
    for pattern in (
        "deep_hedge_price/configs/pricing_*.yaml",
        "deep_hedge_price/configs/research_*.yaml",
        "deep_hedge_price/scripts/*.py",
        "deep_hedge_price/src/deep_hedge_price/*.py",
        "deep_hedge_price/tests/*.py",
        "johnhull/hullkit/src/hullkit/*.py",
        "johnhull/hullkit/tests/*.py",
        "johnhull/scripts/*.py",
        "johnhull/report/report_builder/*.py",
        "johnhull/report/templates/*.j2",
        "johnhull/report/tests/*.py",
    ):
        release_files.extend(sorted(ROOT.glob(pattern)))
    for item in release["volumes"]:
        volume = PROJECT / "volumes" / item["slug"]
        notebook = volume / item["notebook"]
        validation = volume / item["validation"]
        if not volume.is_dir():
            findings.append(Finding("volume", f"missing: {volume.relative_to(ROOT)}"))
            continue
        _check_notebook(notebook, forbidden, findings)
        if not validation.exists():
            findings.append(Finding("validation", f"missing: {validation.relative_to(ROOT)}"))
        else:
            validation_text = validation.read_text(encoding="utf-8")
            if "Gate: **PASS** (`integration_and_reproducibility`)" not in validation_text:
                findings.append(
                    Finding("validation", f"integration gate is not PASS: {validation}")
                )
            if "Model performance approved: **no**" not in validation_text:
                findings.append(
                    Finding("validation", f"model-performance disclaimer missing: {validation}")
                )
        release_files.extend((notebook, validation))
        for field in ("semantic_sources", "semantic_tests"):
            paths = item.get(field)
            if not isinstance(paths, list) or not paths:
                findings.append(
                    Finding("semantics", f"volume {item['number']} has no {field} mapping")
                )
                continue
            for relative in paths:
                semantic_path = ROOT / relative
                if not semantic_path.is_file():
                    findings.append(Finding("semantics", f"missing semantic file: {relative}"))
                release_files.append(semantic_path)
        companion_references = [
            reference for reference in item["references"] if reference.endswith(".npz")
        ]
        for reference in item["references"]:
            reference_path = volume / reference
            release_files.append(reference_path)
            _check_reference(
                reference_path,
                item["number"],
                findings,
                expected_semantic_sources=item["semantic_sources"],
                expected_semantic_tests=item["semantic_tests"],
                expected_companions=companion_references,
            )
        book_file = PROJECT / "book/notebooks" / f"{item['book_name']}.ipynb"
        if not book_file.is_symlink() or not book_file.exists():
            findings.append(
                Finding("book", f"missing/broken symlink: {book_file.relative_to(ROOT)}")
            )
        elif book_file.resolve() != notebook.resolve():
            findings.append(
                Finding(
                    "book",
                    f"symlink target mismatch: {book_file.relative_to(ROOT)} -> "
                    f"{book_file.resolve().relative_to(ROOT)}",
                )
            )
        release_files.append(book_file)
        wrappers = sorted(volume.glob("build_*_notebook.py"))
        if not wrappers:
            findings.append(
                Finding("notebook", f"builder wrapper missing: {volume.relative_to(ROOT)}")
            )
        release_files.extend(wrappers)
        if f"notebooks/{item['book_name']}" not in toc:
            findings.append(Finding("book", f"TOC missing volume {item['number']}"))
        roadmap_pattern = rf"\|\s*{item['number']}\s*\|.*\|\s*done\s*\|"
        if not re.search(roadmap_pattern, roadmap, flags=re.IGNORECASE):
            findings.append(Finding("roadmap", f"volume {item['number']} is not done"))

    pyproject = (PROJECT / "hullkit/pyproject.toml").read_text(encoding="utf-8").lower()
    if re.search(r'^\s*["\']torch(?:[<>=\[]|["\'])', pyproject, flags=re.MULTILINE):
        findings.append(Finding("dependency", "hullkit must remain torch-free"))
    try:
        import hullkit  # noqa: F401
    except ImportError as exc:
        findings.append(Finding("dependency", f"hullkit import failed: {exc}"))
    if "torch" in sys.modules:
        findings.append(Finding("dependency", "importing hullkit pulled torch into sys.modules"))
    provenance = PROJECT / "docs/DATA_PROVENANCE.md"
    if not provenance.exists():
        findings.append(Finding("data", "DATA_PROVENANCE.md is missing"))
    research_profile = PROJECT / "research_profiles.json"
    if not research_profile.exists():
        findings.append(Finding("research", "research_profiles.json is missing"))
    else:
        research = _load_json(research_profile)
        if research.get("enabled_by_default") or research.get("core_gate_dependency"):
            findings.append(
                Finding("research", "research track must be disabled and core-independent")
            )
        if research.get("network_download"):
            findings.append(Finding("research", "research profile must not download by default"))

    final_validation = PROJECT / "VALIDATION.md"
    if not final_validation.exists():
        findings.append(Finding("validation", "johnhull/VALIDATION.md is missing"))
    else:
        final_text = final_validation.read_text(encoding="utf-8")
        required_validation_tokens = [
            "Overall gate: **PASS**",
            "Model performance approved: **NO**",
            "Full-workspace test",
            *[f"G{gate}" for gate in range(9)],
        ]
        missing_tokens = [token for token in required_validation_tokens if token not in final_text]
        if missing_tokens:
            findings.append(
                Finding(
                    "validation",
                    f"johnhull/VALIDATION.md missing final evidence {missing_tokens}",
                )
            )

    config_text = (PROJECT / "book/_config.yml").read_text(encoding="utf-8")
    remotes = sorted(set(re.findall(r"https?://[^\s]+", config_text)))
    if remotes != sorted(release["allowed_book_remote_dependencies"]):
        findings.append(Finding("book", f"unexpected remote dependencies: {remotes}"))
    vendored_require = PROJECT / "book/_static/require.min.js"
    vendored_license = PROJECT / "book/_static/requirejs-LICENSE.txt"
    if vendored_require.stat().st_size < 10_000 or "define.amd" not in vendored_require.read_text(
        encoding="utf-8"
    ):
        findings.append(Finding("book", "vendored require.js is missing or truncated"))
    if "Permission is hereby granted" not in vendored_license.read_text(encoding="utf-8"):
        findings.append(Finding("book", "vendored require.js license is missing"))
    for relative, digest in release["vendored_book_assets"].items():
        asset = PROJECT / relative
        if not asset.is_file() or _sha256(asset) != digest:
            findings.append(Finding("book", f"vendored asset digest mismatch: {relative}"))

    ignore_probes = (
        "deep_hedge_price/artifacts/checkpoints/release-probe.pt",
        "deep_hedge_price/artifacts/pricing/release-probe.pt",
    )
    for probe in ignore_probes:
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", probe],
            cwd=ROOT,
            check=False,
        )
        if ignored.returncode != 0:
            findings.append(Finding("artifact", f"output path is not ignored: {probe}"))

    runtime_remote = re.compile(
        r"<(?:script|link)\b[^>]*(?:src|href)=[\"'](https?://[^\"']+)",
        flags=re.IGNORECASE,
    )
    for rendered in (
        ROOT / "deep_hedge_price/reports/02_neural_pricing_surrogate.html",
        ROOT / "deep_hedge_price/reports/neural_pricing_report_quick.html",
    ):
        if not rendered.is_file():
            findings.append(Finding("pricing-report", f"missing offline report: {rendered}"))
            continue
        remotes = sorted(set(runtime_remote.findall(rendered.read_text(encoding="utf-8"))))
        if remotes:
            findings.append(
                Finding("pricing-report", f"remote runtime dependencies in {rendered}: {remotes}")
            )

    sys.path.insert(0, str(PROJECT / "report"))
    try:
        from report_builder.figures import BOOKS, FIGURES

        expected = release["portal"]
        if len(BOOKS) != expected["themes"]:
            findings.append(
                Finding("portal", f"themes={len(BOOKS)}, expected={expected['themes']}")
            )
        if len(FIGURES) != expected["figures"]:
            findings.append(
                Finding("portal", f"figures={len(FIGURES)}, expected={expected['figures']}")
            )
        figure_by_id = {figure.id: figure for figure in FIGURES}
        for figure in FIGURES:
            try:
                rendered_figure = figure.build()
                if not getattr(rendered_figure, "data", None):
                    findings.append(Finding("portal", f"empty figure: {figure.id}"))
            except Exception as exc:
                findings.append(Finding("portal", f"figure build failed {figure.id}: {exc}"))
        declared_ids = []
        for item in release["volumes"]:
            page = item.get("portal_page")
            ids = item.get("portal_figures")
            if page not in BOOKS or not isinstance(ids, list) or not ids:
                findings.append(
                    Finding("portal", f"volume {item['number']} portal mapping is incomplete")
                )
                continue
            declared_ids.extend(ids)
            for figure_id in ids:
                figure = figure_by_id.get(figure_id)
                if figure is None:
                    findings.append(Finding("portal", f"unknown figure id: {figure_id}"))
                elif figure.book != page:
                    findings.append(
                        Finding(
                            "portal",
                            f"figure {figure_id} belongs to {figure.book}, expected {page}",
                        )
                    )
        if len(declared_ids) != len(set(declared_ids)):
            findings.append(Finding("portal", "volume portal figure mappings contain duplicates"))
        site = PROJECT / "report/site"
        expected_html = {f"{page}.html" for page in ("index", "gallery", "integration", *BOOKS)}
        actual_html = {rendered.name for rendered in site.glob("*.html")}
        if actual_html != expected_html:
            findings.append(
                Finding(
                    "portal",
                    "rendered HTML set differs: "
                    f"missing={sorted(expected_html - actual_html)}, "
                    f"stale={sorted(actual_html - expected_html)}",
                )
            )
        for rendered in site.glob("*.html"):
            text = rendered.read_text(encoding="utf-8")
            if re.search(r"https?://", text):
                findings.append(Finding("portal", f"external URL in {rendered}"))
    except Exception as exc:
        findings.append(Finding("portal", f"registry import failed: {exc}"))
    book_site = PROJECT / "book/_build/html"
    if book_site.exists():
        runtime_urls: set[str] = set()
        for rendered in book_site.rglob("*.html"):
            matches = set(runtime_remote.findall(rendered.read_text(encoding="utf-8")))
            runtime_urls.update(matches)
            if rendered.stem in {item["book_name"] for item in release["volumes"]} and matches:
                findings.append(Finding("book", f"new volume has remote runtime asset: {rendered}"))
        allowed_legacy = set(release["allowed_legacy_book_runtime_dependencies"])
        unexpected_runtime = runtime_urls - allowed_legacy
        if unexpected_runtime:
            findings.append(
                Finding(
                    "book",
                    f"unexpected remote runtime dependencies: {sorted(unexpected_runtime)}",
                )
            )
    for path in dict.fromkeys(release_files):
        _check_version_control_candidate(
            path,
            require_tracked=require_tracked,
            findings=findings,
        )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit machine-readable findings")
    parser.add_argument(
        "--require-tracked",
        action="store_true",
        help="also require every release artifact to exist in the git index/HEAD",
    )
    args = parser.parse_args(argv)
    findings = verify(require_tracked=args.require_tracked)
    if args.json:
        print(json.dumps([finding.__dict__ for finding in findings], ensure_ascii=False, indent=2))
    elif findings:
        for finding in findings:
            print(f"[FAIL] {finding.check}: {finding.detail}")
    else:
        print("[PASS] johnhull A5--A8 release contract")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())
