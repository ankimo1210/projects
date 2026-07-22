from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import tarfile
import tempfile
import unicodedata
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS_DIR = PROJECT_ROOT / "corpus" / "papers"
DEFAULT_MANIFEST = PROJECT_ROOT / "manifests" / "arxiv_formula_sources.json"
DEFAULT_OVERRIDES = PROJECT_ROOT / "manifests" / "formula_overrides.json"
DEFAULT_SOURCE_ROOT = PROJECT_ROOT / "tmp" / "pdfs" / "arxiv-sources"

INPUT_PATTERN = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
DISPLAY_ENVIRONMENTS = (
    "equation",
    "equation*",
    "align",
    "align*",
    "alignat",
    "alignat*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "flalign",
    "flalign*",
    "eqnarray",
    "eqnarray*",
    "dmath",
    "displaymath",
)
DISPLAY_ENV_PATTERN = re.compile(
    r"\\begin\s*\{(?P<env>"
    + "|".join(re.escape(environment) for environment in DISPLAY_ENVIRONMENTS)
    + r")\}(?P<body>.*?)\\end\s*\{(?P=env)\}",
    flags=re.DOTALL,
)
BRACKET_DISPLAY_PATTERN = re.compile(r"\\\[(?P<body>.*?)\\\]", flags=re.DOTALL)
DOLLAR_DISPLAY_PATTERN = re.compile(r"\$\$(?P<body>.*?)\$\$", flags=re.DOTALL)
LABEL_PATTERN = re.compile(r"\\label\s*\{([^}]+)\}")
TAG_PATTERN = re.compile(r"\\tag\*?\s*\{([^}]+)\}")

UNICODE_MATH = {
    "∑": "sum",
    "∏": "prod",
    "√": "sqrt",
    "∞": "infty",
    "∆": "delta",
    "Δ": "delta",
    "δ": "delta",
    "ε": "epsilon",
    "ϵ": "epsilon",
    "\N{GREEK SMALL LETTER SIGMA}": "sigma",
    "λ": "lambda",
    "\N{GREEK SMALL LETTER ALPHA}": "alpha",
    "β": "beta",
    "\N{GREEK SMALL LETTER GAMMA}": "gamma",
    "η": "eta",
    "θ": "theta",
    "τ": "tau",
    "µ": "mu",
    "μ": "mu",
    "\N{GREEK SMALL LETTER RHO}": "rho",
    "φ": "phi",
    "π": "pi",
    "⊙": "odot",
    "⊘": "oslash",
    "≤": "leq",
    "≥": "geq",
    "≠": "neq",
    "→": "to",
    "∈": "in",
    "‖": "norm",
    "\N{DIVIDES}": "mid",
}
IGNORED_COMMANDS = {
    "begin",
    "end",
    "left",
    "right",
    "big",
    "bigg",
    "bigl",
    "bigr",
    "Big",
    "Bigg",
    "Bigl",
    "Bigr",
    "quad",
    "qquad",
    "label",
    "tag",
    "nonumber",
    "notag",
    "displaystyle",
    "textstyle",
    "scriptstyle",
    "scriptscriptstyle",
    "mathrm",
    "mathbf",
    "mathit",
    "mathsf",
    "mathtt",
    "mathcal",
    "mathbb",
    "operatorname",
    "text",
    "textrm",
    "textbf",
    "textit",
    "mbox",
    "rm",
    "bf",
    "it",
    "limits",
    "nolimits",
}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_sources(source_manifest: dict[str, Any], source_root: Path) -> None:
    source_root.mkdir(parents=True, exist_ok=True)
    for paper_id, config in source_manifest["papers"].items():
        version = config["arxiv_version"]
        archive = source_root / f"{version}.src"
        if archive.is_file():
            if sha256_file(archive) != config["archive_sha256"]:
                raise RuntimeError(f"Existing arXiv source archive hash mismatch for {paper_id}")
        else:
            request = urllib.request.Request(
                f"https://export.arxiv.org/e-print/{version}",
                headers={"User-Agent": "market_nn formula verification"},
            )
            with (
                urllib.request.urlopen(request, timeout=180) as response,
                tempfile.NamedTemporaryFile(dir=source_root, delete=False) as temporary,
            ):
                while chunk := response.read(1024 * 1024):
                    temporary.write(chunk)
                temporary_path = Path(temporary.name)
            if sha256_file(temporary_path) != config["archive_sha256"]:
                temporary_path.unlink()
                raise RuntimeError(f"Downloaded arXiv source archive hash mismatch for {paper_id}")
            temporary_path.replace(archive)

        extracted_root = source_root / version
        main_file = extracted_root / config["main_tex"]
        if main_file.is_file():
            continue
        extracted_root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, mode="r:*") as source_tar:
            root = extracted_root.resolve()
            for member in source_tar.getmembers():
                target = (extracted_root / member.name).resolve()
                if not target.is_relative_to(root):
                    raise RuntimeError(f"Unsafe path in arXiv source archive: {member.name}")
            source_tar.extractall(extracted_root, filter="data")
        if not main_file.is_file():
            raise FileNotFoundError(f"Main TeX file missing after extraction for {paper_id}")


def strip_tex_comment(line: str) -> str:
    for index, character in enumerate(line):
        if character != "%":
            continue
        backslashes = 0
        cursor = index - 1
        while cursor >= 0 and line[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        if backslashes % 2 == 0:
            return line[:index] + ("\n" if line.endswith("\n") else "")
    return line


def resolve_input(current: Path, source_root: Path, target: str) -> Path | None:
    target = target.strip()
    if not target or "\\" in target or "#" in target:
        return None
    candidates = [current.parent / target, source_root / target]
    if not Path(target).suffix:
        candidates.extend((current.parent / f"{target}.tex", source_root / f"{target}.tex"))
    resolved_root = source_root.resolve()
    for candidate in candidates:
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if not resolved.is_relative_to(resolved_root):
            raise RuntimeError(f"TeX input escapes source root: {target}")
        return resolved
    return None


def expand_tex(main_file: Path, source_root: Path) -> tuple[str, list[tuple[int, str, int]]]:
    parts: list[str] = []
    source_points: list[tuple[int, str, int]] = []
    length = 0

    def append(text: str, path: Path, line_number: int) -> None:
        nonlocal length
        if not text:
            return
        source_points.append((length, str(path.relative_to(source_root)), line_number))
        parts.append(text)
        length += len(text)

    def visit(path: Path, stack: tuple[Path, ...]) -> None:
        if path in stack:
            raise RuntimeError(f"Cyclic TeX input: {' -> '.join(map(str, (*stack, path)))}")
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw = path.read_text(encoding="latin-1")
        for line_number, raw_line in enumerate(raw.splitlines(keepends=True), start=1):
            line = strip_tex_comment(raw_line)
            cursor = 0
            for match in INPUT_PATTERN.finditer(line):
                append(line[cursor : match.start()], path, line_number)
                included = resolve_input(path, source_root, match.group(1))
                if included is None:
                    append(match.group(0), path, line_number)
                else:
                    visit(included, (*stack, path))
                cursor = match.end()
            append(line[cursor:], path, line_number)

    visit(main_file.resolve(), ())
    return "".join(parts), source_points


def mask_inactive_blocks(text: str) -> str:
    patterns = (
        re.compile(r"\\begin\s*\{comment\}.*?\\end\s*\{comment\}", re.DOTALL),
        re.compile(r"\\iffalse\b.*?\\fi\b", re.DOTALL),
    )
    for pattern in patterns:
        text = pattern.sub(lambda match: re.sub(r"[^\n]", " ", match.group(0)), text)
    return text


def clean_source_latex(body: str) -> str:
    body = LABEL_PATTERN.sub("", body)
    body = TAG_PATTERN.sub("", body)
    body = re.sub(r"\\(?:nonumber|notag)\b", "", body)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r" *\n *", "\n", body)
    return body.strip()


def source_location(offset: int, source_points: list[tuple[int, str, int]]) -> tuple[str, int]:
    starts = [point[0] for point in source_points]
    index = max(0, bisect.bisect_right(starts, offset) - 1)
    _start, path, line = source_points[index]
    return path, line


def extract_display_math(
    expanded_text: str, source_points: list[tuple[int, str, int]]
) -> list[dict[str, Any]]:
    text = mask_inactive_blocks(expanded_text)
    document_start = text.find("\\begin{document}")
    document_end = text.rfind("\\end{document}")
    if document_start >= 0:
        start_offset = document_start + len("\\begin{document}")
    else:
        start_offset = 0
    if document_end < start_offset:
        document_end = len(text)
    body = text[start_offset:document_end]

    matches: list[tuple[int, int, str, str]] = []
    for pattern, default_environment in (
        (DISPLAY_ENV_PATTERN, None),
        (BRACKET_DISPLAY_PATTERN, "bracket"),
        (DOLLAR_DISPLAY_PATTERN, "double_dollar"),
    ):
        for match in pattern.finditer(body):
            environment = default_environment or match.group("env")
            matches.append(
                (
                    start_offset + match.start(),
                    start_offset + match.end(),
                    environment,
                    match.group("body"),
                )
            )
    matches.sort()
    candidates: list[dict[str, Any]] = []
    occupied_end = -1
    for start, end, environment, raw_latex in matches:
        if start < occupied_end:
            continue
        occupied_end = end
        source_file, source_line = source_location(start, source_points)
        labels = LABEL_PATTERN.findall(raw_latex)
        tags = TAG_PATTERN.findall(raw_latex)
        candidates.append(
            {
                "source_index": len(candidates) + 1,
                "environment": environment,
                "source_file": source_file,
                "source_line": source_line,
                "label": labels[0] if labels else None,
                "tag": tags[0] if tags else None,
                "source_latex": clean_source_latex(raw_latex),
            }
        )
    return candidates


def normalize_math(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    for symbol, replacement in UNICODE_MATH.items():
        text = text.replace(symbol, replacement)
    text = LABEL_PATTERN.sub("", text)
    text = TAG_PATTERN.sub("", text)
    text = re.sub(r"\(\s*[0-9]+(?:[.:-][0-9A-Za-z.-]+|[A-Za-z])?\s*\)\s*$", "", text)
    text = re.sub(r"\\begin\s*\{[^}]+\}|\\end\s*\{[^}]+\}", "", text)

    def command(match: re.Match[str]) -> str:
        name = match.group(1)
        return "" if name in IGNORED_COMMANDS else name

    text = re.sub(r"\\([A-Za-z]+)\*?", command, text)
    text = re.sub(r"\\[^A-Za-z\s]", "", text)
    return re.sub(r"[^0-9A-Za-z]+", "", text).lower()


def formula_similarity(formula: dict[str, Any], candidate: dict[str, Any]) -> tuple[float, str]:
    source = normalize_math(candidate["source_latex"])
    if not source:
        return 0.0, "none"
    representations = {
        "latex": normalize_math(formula.get("latex")),
        "docling_latex": normalize_math(formula.get("docling_latex")),
        "pdf_text": normalize_math(formula.get("pdf_text")),
    }
    scores = {
        name: SequenceMatcher(None, representation, source, autojunk=False).ratio()
        for name, representation in representations.items()
        if representation
    }
    if not scores:
        return 0.0, "none"
    matched_on = max(scores, key=scores.get)
    return scores[matched_on], matched_on


def formula_alignment_input(formula: dict[str, Any]) -> dict[str, Any]:
    """Restore the pre-source-overlay representation for repeatable alignment."""
    restored = dict(formula)
    source_verification = formula.get("source_verification")
    if not isinstance(source_verification, dict):
        return restored
    base_status = source_verification.get("base_status")
    if base_status == "text_layer_fallback":
        restored["latex"] = None
    elif base_status == "decoded_unverified":
        restored["latex"] = restored.get("docling_latex")
    return restored


def align_formulas(
    formulas: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    formula_count = len(formulas)
    candidate_count = len(candidates)
    gap_penalty = -0.32
    details = [
        [formula_similarity(formula, candidate) for candidate in candidates] for formula in formulas
    ]
    scores = [[detail[0] for detail in row] for row in details]
    dynamic = [[0.0] * (candidate_count + 1) for _ in range(formula_count + 1)]
    choices = [[""] * (candidate_count + 1) for _ in range(formula_count + 1)]
    for index in range(1, formula_count + 1):
        dynamic[index][0] = dynamic[index - 1][0] + gap_penalty
        choices[index][0] = "formula_gap"
    for index in range(1, candidate_count + 1):
        dynamic[0][index] = dynamic[0][index - 1] + gap_penalty
        choices[0][index] = "source_gap"
    for formula_index in range(1, formula_count + 1):
        for candidate_index in range(1, candidate_count + 1):
            similarity = scores[formula_index - 1][candidate_index - 1]
            options = {
                "match": dynamic[formula_index - 1][candidate_index - 1]
                + 2.0 * (similarity - 0.45),
                "formula_gap": dynamic[formula_index - 1][candidate_index] + gap_penalty,
                "source_gap": dynamic[formula_index][candidate_index - 1] + gap_penalty,
            }
            choice = max(options, key=options.get)
            dynamic[formula_index][candidate_index] = options[choice]
            choices[formula_index][candidate_index] = choice

    aligned: list[dict[str, Any]] = []
    formula_index = formula_count
    candidate_index = candidate_count
    while formula_index or candidate_index:
        choice = choices[formula_index][candidate_index]
        if choice == "match":
            formula = formulas[formula_index - 1]
            candidate = candidates[candidate_index - 1]
            aligned.append(
                {
                    "formula_id": formula["formula_id"],
                    "source_index": candidate["source_index"],
                    "score": round(scores[formula_index - 1][candidate_index - 1], 4),
                    "matched_on": details[formula_index - 1][candidate_index - 1][1],
                    **candidate,
                }
            )
            formula_index -= 1
            candidate_index -= 1
        elif choice == "formula_gap":
            formula_index -= 1
        elif choice == "source_gap":
            candidate_index -= 1
        else:
            raise RuntimeError("Formula alignment traceback failed")
    return list(reversed(aligned))


def analyze_paper(
    paper_id: str,
    config: dict[str, Any],
    *,
    corpus_dir: Path,
    source_root: Path,
) -> dict[str, Any]:
    version = config["arxiv_version"]
    extracted_root = source_root / version
    archive = source_root / f"{version}.src"
    if sha256_file(archive) != config["archive_sha256"]:
        raise RuntimeError(f"arXiv source archive hash mismatch for {paper_id}")
    formulas_path = corpus_dir / paper_id / "formulas.jsonl"
    formulas = [
        formula_alignment_input(json.loads(line))
        for line in formulas_path.read_text(encoding="utf-8").splitlines()
    ]
    if config["source_kind"] != "tex":
        return {
            "paper_id": paper_id,
            "arxiv_version": version,
            "source_kind": config["source_kind"],
            "formula_count": len(formulas),
            "source_formula_count": 0,
            "matches": [],
        }
    main_file = extracted_root / config["main_tex"]
    expanded, source_points = expand_tex(main_file, extracted_root)
    candidates = extract_display_math(expanded, source_points)
    matches = align_formulas(formulas, candidates)
    return {
        "paper_id": paper_id,
        "arxiv_version": version,
        "source_url": f"https://export.arxiv.org/e-print/{version}",
        "archive_sha256": config["archive_sha256"],
        "source_kind": config["source_kind"],
        "formula_count": len(formulas),
        "source_formula_count": len(candidates),
        "matches": matches,
    }


def analyze_corpus(corpus_dir: Path, source_root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    papers = [
        analyze_paper(paper_id, config, corpus_dir=corpus_dir, source_root=source_root)
        for paper_id, config in manifest["papers"].items()
    ]
    return {
        "schema_version": 1,
        "papers": papers,
        "summary": {
            "paper_count": len(papers),
            "tex_papers": sum(paper["source_kind"] == "tex" for paper in papers),
            "pdf_wrappers": sum(paper["source_kind"] == "pdf_wrapper" for paper in papers),
            "formula_count": sum(paper["formula_count"] for paper in papers),
            "source_formula_count": sum(paper["source_formula_count"] for paper in papers),
            "aligned": sum(len(paper["matches"]) for paper in papers),
            "score_ge_090": sum(
                match["score"] >= 0.9 for paper in papers for match in paper["matches"]
            ),
            "score_ge_080": sum(
                match["score"] >= 0.8 for paper in papers for match in paper["matches"]
            ),
        },
    }


def build_match_manifest(
    report: dict[str, Any],
    corpus_dir: Path,
    source_manifest: dict[str, Any],
    *,
    threshold: float,
) -> dict[str, Any]:
    overrides = json.loads(DEFAULT_OVERRIDES.read_text(encoding="utf-8"))
    base_formulas: dict[str, dict[str, Any]] = {}
    for formulas_path in corpus_dir.glob("*/formulas.jsonl"):
        for line in formulas_path.read_text(encoding="utf-8").splitlines():
            formula = json.loads(line)
            if formula["document_ref"] in overrides.get(formula["paper_id"], {}):
                status = "verified_manual"
            elif formula.get("docling_latex"):
                status = "decoded_unverified"
            else:
                status = "text_layer_fallback"
            base_formulas[formula["formula_id"]] = {**formula, "status": status}

    manually_accepted = set(source_manifest.get("manually_accepted_source_matches", []))
    rejected_config = source_manifest.get("rejected_source_matches", {})
    if not isinstance(rejected_config, dict):
        raise TypeError("rejected_source_matches must be an object")
    rejected = set(rejected_config)
    overlap = manually_accepted & rejected
    if overlap:
        raise RuntimeError(f"Source matches cannot be accepted and rejected: {sorted(overlap)}")
    reviewed_recoveries = set(source_manifest.get("visually_reviewed_source_recoveries", []))
    aligned_matches = {
        match["formula_id"]: match for paper in report["papers"] for match in paper["matches"]
    }
    missing_rejected_matches = sorted(rejected - aligned_matches.keys())
    if missing_rejected_matches:
        raise RuntimeError(f"Rejected source matches were not aligned: {missing_rejected_matches}")
    accepted: dict[str, dict[str, Any]] = {}
    for paper in report["papers"]:
        for match in paper["matches"]:
            formula_id = match["formula_id"]
            if formula_id in rejected:
                continue
            if match["score"] < threshold and formula_id not in manually_accepted:
                continue
            formula = base_formulas[formula_id]
            status = formula["status"]
            accepted[formula_id] = {
                "arxiv_version": paper["arxiv_version"],
                "source_url": paper["source_url"],
                "archive_sha256": paper["archive_sha256"],
                "source_file": match["source_file"],
                "source_line": match["source_line"],
                "source_index": match["source_index"],
                "environment": match["environment"],
                "label": match["label"],
                "tag": match["tag"],
                "source_latex": match["source_latex"],
                "match_method": "ordered_normalized_similarity_v1",
                "matched_on": match["matched_on"],
                "score": match["score"],
                "base_status": status,
                "document_ref": formula["document_ref"],
                "source_pdf": formula["source_pdf"],
                "source_page": formula["page"],
                "acceptance": (
                    "similarity_threshold" if match["score"] >= threshold else "visual_crop_review"
                ),
                "visual_crop_checked": (
                    formula_id in manually_accepted or formula_id in reviewed_recoveries
                ),
            }

    missing_manual_matches = sorted(manually_accepted - accepted.keys())
    if missing_manual_matches:
        raise RuntimeError(
            f"Manually accepted source matches were not aligned: {missing_manual_matches}"
        )
    unreviewed_recoveries = sorted(
        formula_id
        for formula_id, match in accepted.items()
        if match["base_status"] == "text_layer_fallback" and not match["visual_crop_checked"]
    )
    if unreviewed_recoveries:
        raise RuntimeError(
            "Source-recovered formulas require crop review before promotion: "
            f"{unreviewed_recoveries}"
        )
    return {
        "schema_version": 1,
        "threshold": threshold,
        "matches": accepted,
        "rejected_matches": {
            formula_id: {
                "reason": rejected_config[formula_id],
                "score": aligned_matches[formula_id]["score"],
                "source_index": aligned_matches[formula_id]["source_index"],
                "source_file": aligned_matches[formula_id]["source_file"],
                "source_line": aligned_matches[formula_id]["source_line"],
            }
            for formula_id in sorted(rejected)
        },
        "summary": {
            "source_verified": len(accepted),
            "manual_confirmed": sum(
                match["base_status"] == "verified_manual" for match in accepted.values()
            ),
            "decoded_corrected": sum(
                match["base_status"] == "decoded_unverified" for match in accepted.values()
            ),
            "fallback_recovered": sum(
                match["base_status"] == "text_layer_fallback" for match in accepted.values()
            ),
            "visual_crop_checked": sum(match["visual_crop_checked"] for match in accepted.values()),
            "rejected_after_visual_review": len(rejected),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Align corpus formulas with exact arXiv TeX sources."
    )
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--matches-output", type=Path)
    parser.add_argument("--threshold", type=float, default=0.9)
    parser.add_argument("--download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    corpus_dir = args.corpus_dir.resolve()
    manifest_path = args.manifest.resolve()
    source_root = args.source_root.resolve()
    if args.download:
        ensure_sources(json.loads(manifest_path.read_text(encoding="utf-8")), source_root)
    report = analyze_corpus(corpus_dir, source_root, manifest_path)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.matches_output:
        source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        matches = build_match_manifest(
            report, corpus_dir, source_manifest, threshold=args.threshold
        )
        args.matches_output.write_text(
            json.dumps(matches, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
