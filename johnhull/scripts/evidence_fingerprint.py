"""Section dependency fingerprints for reusing screen evidence (D1).

A fingerprint lists every input that can change what an accepted section's
browser evidence shows: the section's notebook cells and outputs, its Book DOM
slice, its portal figure cards, the page assets both surfaces load, the hullkit
modules it imports, its data files, the verifier and the rendering
environment. Only the normalizations listed in ``NORMALIZATION_RULES`` are
applied. Anything that cannot be read is reported as unknown, and an unknown
input always forces a redraw.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

FINGERPRINT_SCHEMA = 1
NORMALIZER_VERSION = 1
NORMALIZATION_RULES = (
    "Plotly div UUIDs are renamed by order of first appearance within a slice",
    "Sphinx auto-generated anchor ids (id<N>) are renamed by order of first appearance",
    "An inline plotly.js bundle is replaced by its sha256 and fingerprinted as a shared asset",
    "Notebook cell ids and execution counts are dropped (not rendered by Book or portal)",
    "Package __init__ modules are not followed when collecting hullkit sources",
)
RUNTIME_KEYS = ("browser_version", "mathjax_version", "fonts")
DEFAULT_CONFIG = Path(__file__).with_name("evidence_dependencies.json")

_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
_AUTO_ID_RE = re.compile(r'(id="|href="#)(id[0-9]+)(")')
_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.S)
_SECTION_TAG_RE = re.compile(r"<section\b[^>]*>|</section>")
_ASSET_RE = re.compile(r"<(link|script)\b([^>]*)>", re.I)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _canonical_digest(value: object) -> str:
    return _sha256_text(json.dumps(value, sort_keys=True, ensure_ascii=False))


def _extract_bundles(text: str) -> tuple[str, list[str]]:
    bundles: list[str] = []

    def replace(match: re.Match) -> str:
        script = match.group(0)
        if "plotly.js v" not in script:
            return script
        digest = _sha256_text(script)
        bundles.append(digest)
        return f"<plotly-bundle sha256={digest}>"

    return _SCRIPT_RE.sub(replace, text), bundles


class _Renamer:
    """Rename volatile identifiers by order of first appearance."""

    def __init__(self) -> None:
        self.uuids: dict[str, str] = {}
        self.auto_ids: dict[str, str] = {}

    def text(self, value: str) -> str:
        value = _UUID_RE.sub(
            lambda m: self.uuids.setdefault(m.group(0), f"plotly-id-{len(self.uuids)}"), value
        )
        return _AUTO_ID_RE.sub(
            lambda m: (
                m.group(1)
                + self.auto_ids.setdefault(m.group(2), f"auto-id-{len(self.auto_ids)}")
                + m.group(3)
            ),
            value,
        )

    def deep(self, value: object) -> object:
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, list):
            return [self.deep(item) for item in value]
        if isinstance(value, dict):
            return {key: self.deep(item) for key, item in value.items()}
        return value


def _joined(source: object) -> str:
    return "".join(source) if isinstance(source, list) else str(source or "")


def _heading_cells(notebook: dict) -> list[tuple[int, str]]:
    headings = []
    for index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") == "markdown":
            first = _joined(cell.get("source")).split("\n", 1)[0]
            if first.startswith("## "):
                headings.append((index, first[3:].strip()))
    return headings


def notebook_slice(notebook: dict, heading: str) -> tuple[list[dict], list[str]]:
    """Return the normalized cells of one ``## heading`` slice and its bundles."""
    headings = _heading_cells(notebook)
    starts = [index for index, text in headings if text.startswith(heading)]
    if len(starts) != 1:
        raise LookupError(f"notebook heading {heading!r} matched {len(starts)} cells")
    start = starts[0]
    ends = [index for index, _ in headings if index > start]
    cells = notebook["cells"][start : ends[0] if ends else None]
    renamer = _Renamer()
    bundles: list[str] = []
    content = []
    for cell in cells:
        normalized = {
            "cell_type": cell.get("cell_type"),
            "metadata": cell.get("metadata", {}),
            "source": _joined(cell.get("source")),
        }
        outputs = []
        for output in cell.get("outputs", []):
            item = {key: value for key, value in output.items() if key != "execution_count"}
            data = dict(item.get("data", {}))
            if "text/html" in data:
                html, found = _extract_bundles(_joined(data["text/html"]))
                bundles.extend(found)
                data["text/html"] = html
            if data:
                item["data"] = data
            outputs.append(renamer.deep(item))
        if cell.get("cell_type") == "code":
            normalized["outputs"] = outputs
        content.append(renamer.deep(normalized))
    return content, sorted(set(bundles))


def notebook_bundles(notebook: dict) -> list[str]:
    bundles: list[str] = []
    for cell in notebook.get("cells", []):
        for output in cell.get("outputs", []):
            html = output.get("data", {}).get("text/html")
            if html is not None:
                bundles.extend(_extract_bundles(_joined(html))[1])
    return sorted(set(bundles))


def book_section(html: str, heading: str) -> str:
    """Return the normalized ``<section>`` element whose ``<h2>`` starts with ``heading``."""
    matches = list(re.finditer(r"<h2\b[^>]*>\s*" + re.escape(heading), html))
    if len(matches) != 1:
        raise LookupError(f"Book heading {heading!r} matched {len(matches)} times")
    start = html.rfind("<section", 0, matches[0].start())
    if start < 0:
        raise LookupError(f"Book heading {heading!r} is not inside a section")
    depth = 0
    for tag in _SECTION_TAG_RE.finditer(html, start):
        depth += -1 if tag.group(0) == "</section>" else 1
        if depth == 0:
            section, _ = _extract_bundles(html[start : tag.end()])
            return _Renamer().text(section)
    raise LookupError(f"Book section for {heading!r} is not closed")


def html_bundles(html: str) -> list[str]:
    return sorted(set(_extract_bundles(html)[1]))


def portal_cards(html: str, keys: list[str]) -> dict[str, str]:
    """Return the ``<figure class="fig-card">`` element that holds each figure key."""
    cards = {}
    for key in keys:
        marker = html.find(f'id="fig-{key}"')
        if marker < 0:
            raise LookupError(f"portal figure {key!r} not found")
        start = html.rfind('<figure class="fig-card">', 0, marker)
        end = html.find("</figure>", marker)
        if start < 0 or end < 0:
            raise LookupError(f"portal figure {key!r} is not inside a fig-card")
        cards[key] = html[start : end + len("</figure>")]
    return cards


def _attribute(attributes: str, name: str) -> str | None:
    match = re.search(rf'\b{name}\s*=\s*"([^"]*)"', attributes)
    return match.group(1) if match else None


def page_assets(project: Path | str, page: str) -> dict:
    """Hash the stylesheets and scripts a page loads; list external URLs as floating."""
    project = Path(project).resolve()
    page_path = project / page
    html = page_path.read_text(encoding="utf-8")
    local: dict[str, str | None] = {}
    external: set[str] = set()
    for match in _ASSET_RE.finditer(html):
        tag, attributes = match.group(1).lower(), match.group(2)
        if tag == "link":
            rel = _attribute(attributes, "rel") or ""
            if "stylesheet" not in rel.split():
                continue
            reference = _attribute(attributes, "href")
        else:
            reference = _attribute(attributes, "src")
        if not reference:
            continue
        if re.match(r"^[a-z][a-z0-9+.-]*:", reference, re.I):
            external.add(reference)
            continue
        target = (page_path.parent / reference.split("#")[0].split("?")[0]).resolve()
        if not target.is_relative_to(project):
            external.add(reference)
            continue
        relative = target.relative_to(project).as_posix()
        local[relative] = _sha256_bytes(target.read_bytes()) if target.is_file() else None
    return {"local": dict(sorted(local.items())), "external": sorted(external)}


def _module_file(src: Path, module: str) -> Path | None:
    base = src.joinpath(*module.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    return None


def python_closure(project: Path | str, modules: list[str], package: str = "hullkit") -> dict:
    """Whole-file hashes of the listed modules and the package modules they import."""
    project = Path(project)
    src = project / package / "src"
    pending = list(modules)
    seen: dict[str, str] = {}
    while pending:
        module = pending.pop()
        path = _module_file(src, module)
        if path is None or module in seen:
            continue
        data = path.read_bytes()
        seen[module] = path.relative_to(project).as_posix()
        tree = ast.parse(data)
        parent = module.rsplit(".", 1)[0]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                pending.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    anchor = parent.rsplit(".", node.level - 1)[0] if node.level > 1 else parent
                    base = f"{anchor}.{base}" if base else anchor
                if base.split(".")[0] != package:
                    continue
                pending.append(base)
                pending.extend(f"{base}.{alias.name}" for alias in node.names)
    closure = {}
    for relative in sorted(seen.values()):
        closure[relative] = _sha256_bytes((project / relative).read_bytes())
    return closure


def _file_hashes(project: Path, paths: list[str]) -> dict:
    return {
        path: _sha256_bytes((project / path).read_bytes()) if (project / path).is_file() else None
        for path in paths
    }


def _run(command: list[str]) -> str | None:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def static_environment(fonts: tuple[str, ...] = ("Noto Sans JP", "sans-serif")) -> dict:
    """Rendering environment known before the browser starts."""
    playwright = None
    module = os.environ.get("PLAYWRIGHT_MODULE")
    if module:
        package = Path(module) / "package.json"
        if package.is_file():
            playwright = json.loads(package.read_text(encoding="utf-8")).get("version")
    font_files = {}
    for family in fonts:
        path = _run(["fc-match", "-f", "%{file}", family])
        font_files[family] = (
            {"file": Path(path).name, "sha256": _sha256_bytes(Path(path).read_bytes())}
            if path and Path(path).is_file()
            else None
        )
    return {
        "node": _run(["node", "--version"]),
        "playwright": playwright,
        "chromium_bin": Path(os.environ["CHROMIUM_BIN"]).name
        if os.environ.get("CHROMIUM_BIN")
        else None,
        "fonts": font_files,
        "locale": os.environ.get("LC_ALL") or os.environ.get("LANG"),
        "timezone": os.environ.get("TZ"),
    }


def _rules() -> dict:
    return {
        "fingerprint_schema": FINGERPRINT_SCHEMA,
        "normalizer_version": NORMALIZER_VERSION,
        "normalization": list(NORMALIZATION_RULES),
    }


def compute_fingerprint(
    project: Path | str, section_id: str, config: dict, environment: dict | None = None
) -> dict:
    project = Path(project)
    result = {"section_id": section_id, "rules": _rules(), "components": {}, "unknown": []}
    spec = config.get("sections", {}).get(section_id)
    if spec is None:
        result["unknown"].append(f"section {section_id} has no dependency declaration")
        result["digest"] = None
        return result
    components = result["components"]
    unknown = result["unknown"]

    def attempt(name, function):
        try:
            components[name] = function()
        except (OSError, LookupError, ValueError, json.JSONDecodeError) as exc:
            components[name] = None
            unknown.append(f"{name}: {exc}")

    notebook_spec = spec["notebook"]

    def load_notebook():
        return json.loads((project / notebook_spec["path"]).read_text(encoding="utf-8"))

    attempt(
        "notebook_slice",
        lambda: _canonical_digest(notebook_slice(load_notebook(), notebook_spec["heading"])[0]),
    )
    attempt("notebook_shared_assets", lambda: notebook_bundles(load_notebook()))
    book = spec["book"]
    attempt(
        "book_section",
        lambda: _sha256_text(
            book_section((project / book["page"]).read_text(encoding="utf-8"), book["heading"])
        ),
    )
    attempt(
        "book_assets",
        lambda: (
            page_assets(project, book["page"])
            | {"inline_bundles": html_bundles((project / book["page"]).read_text(encoding="utf-8"))}
        ),
    )
    portal = spec["portal"]
    attempt(
        "portal_cards",
        lambda: {
            key: _sha256_text(card)
            for key, card in portal_cards(
                (project / portal["page"]).read_text(encoding="utf-8"), portal["figures"]
            ).items()
        },
    )
    attempt("portal_assets", lambda: page_assets(project, portal["page"]))
    attempt("python_sources", lambda: python_closure(project, spec["python_modules"]))
    attempt("data_files", lambda: _file_hashes(project, spec["data"]))
    attempt("verifier", lambda: _file_hashes(project, [spec["verifier"]]))
    components["viewports"] = spec.get("viewports")
    components["environment"] = environment if environment is not None else static_environment()

    for name in ("book_assets", "portal_assets"):
        value = components.get(name) or {}
        missing = [path for path, digest in value.get("local", {}).items() if digest is None]
        unknown.extend(f"{name}: missing {path}" for path in missing)
    for name in ("data_files", "verifier"):
        value = components.get(name) or {}
        unknown.extend(
            f"{name}: missing {path}" for path, digest in value.items() if digest is None
        )
    result["digest"] = _canonical_digest({"rules": result["rules"], "components": components})
    return result


def compare_fingerprints(baseline: dict, current: dict) -> list[str]:
    names = set(baseline.get("components", {})) | set(current.get("components", {}))
    return sorted(
        name
        for name in names
        if baseline.get("components", {}).get(name) != current.get("components", {}).get(name)
    )


def decide(baseline: dict, current: dict) -> dict:
    """Decide whether baseline screen evidence may be reused for the current state."""
    unknown = list(baseline.get("unknown", [])) + list(current.get("unknown", []))
    if unknown or baseline.get("digest") is None or current.get("digest") is None:
        return {
            "decision": "redraw",
            "reasons": [f"unknown dependency: {item}" for item in unknown]
            or ["unknown dependency: missing fingerprint digest"],
        }
    if baseline.get("rules") != current.get("rules"):
        return {
            "decision": "redraw",
            "reasons": ["rules changed: fingerprint schema or normalizer"],
        }
    changed = compare_fingerprints(baseline, current)
    if changed:
        return {"decision": "redraw", "reasons": [f"{name} changed" for name in changed]}
    return {"decision": "reuse", "reasons": []}


def runtime_mismatches(baseline: dict, current: dict, keys: tuple[str, ...] = RUNTIME_KEYS) -> list:
    """Runtime facts observed in the browser that must match the baseline run."""
    return [
        key
        for key in keys
        if baseline.get(key) is None or current.get(key) is None or baseline[key] != current[key]
    ]


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("dependency config schema_version must be 1")
    return config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("section")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    fingerprint = compute_fingerprint(args.project_root, args.section, load_config(args.config))
    print(json.dumps(fingerprint, indent=2, ensure_ascii=False))
    return 1 if fingerprint["unknown"] else 0


if __name__ == "__main__":
    sys.exit(main())
