"""Stage exactly one candidate's starting submission and assigned resources.

This stages files. It neither starts an agent nor enforces an OS sandbox.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from datasets import digest, outside_git, save_json

KIT = Path(__file__).resolve().parents[1]
BENCH = KIT.parents[1]
CONFIG = json.loads((KIT / "config.json").read_text())
EXCLUDED = {
    ".git",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".DS_Store",
}


def hashes(root):
    return {str(p.relative_to(root)): digest(p) for p in files(root)}


def files(root):
    # Walk pruning environments before traversing them, including Luna's venv.
    import os

    found = []
    for directory, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not d.startswith(".venv"))
        for name in dirs + names:
            if name in EXCLUDED or name.startswith(".venv"):
                continue
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError(f"symlink in candidate payload: {path}")
        found.extend(
            Path(directory) / name
            for name in sorted(names)
            if name not in EXCLUDED and not name.endswith((".pyc", ".pyo"))
        )
    return sorted(found)


def copy_project(source, destination):
    destination.mkdir(parents=True, exist_ok=False)
    for path in files(source):
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def prepare(
    model, arm, repeat, destination, suite, materials, python_bin, *, campaign="pilot_factorial"
):
    if campaign not in ("pilot_factorial", "combined_all_models"):
        raise ValueError("unknown campaign")
    if campaign == "combined_all_models" and arm != "D":
        raise ValueError("combined campaign requires both papers and QuantLib (arm D)")
    source = BENCH / CONFIG["starting_submissions"][model]
    if not source.is_dir():
        raise FileNotFoundError(source)
    if repeat < 1:
        raise ValueError("repeat must be positive")
    destination = outside_git(destination)
    if destination.exists():
        raise FileExistsError("refusing to overwrite a run")
    # Never place a run in a truth/material/runtime ancestor, or vice versa.
    for owner_path in (suite.resolve(), materials.resolve(), python_bin.resolve().parent.parent):
        if (
            destination == owner_path
            or destination.is_relative_to(owner_path)
            or owner_path.is_relative_to(destination)
        ):
            raise ValueError("candidate and owner resources must be disjoint")
    expected = json.loads((suite / "manifest.json").read_text())["hashes"]
    relative = "training/market_observations.csv"
    if digest(suite / relative) != expected[relative]:
        raise ValueError("training data hash mismatch")
    resources = json.loads((materials / "manifest.json").read_text())["resources"]
    for entry in resources:
        if digest(materials / entry["path"]) != entry["sha256"]:
            raise ValueError("research resource hash mismatch")
    before = hashes(source)
    destination.mkdir(parents=True, mode=0o700)
    copy_project(source, destination / "baseline")
    copy_project(source, destination / "work")
    market_dir = destination / "input/market_data"
    market_dir.mkdir(parents=True)
    shutil.copy2(BENCH / "input/TASK.md", destination / "input/TASK.md")
    shutil.copy2(KIT / "public/CONVENTIONS.md", market_dir / "CONVENTIONS.md")
    shutil.copy2(suite / relative, market_dir / "market_observations.csv")
    # Required sources only: no full manifest advertising the other arm's data.
    allowed = CONFIG["arms"][arm]
    (destination / "materials").mkdir()
    for group, enabled in (("papers", allowed["papers"]), ("quantlib", allowed["quantlib"])):
        if enabled:
            shutil.copytree(materials / group, destination / "materials" / group)
    template = "combined_prompt.md" if campaign == "combined_all_models" else "common_prompt.md"
    prompt = (KIT / "public" / template).read_text()
    values = dict(
        MODEL_KEY=model,
        ARM=arm,
        REPEAT=str(repeat),
        RUN_ROOT=str(destination),
        PYTHON_BIN=str(python_bin.absolute()),
    )
    for key, value in values.items():
        prompt = prompt.replace("{{" + key + "}}", value)
    (destination / "PROMPT.md").write_text(prompt)
    (destination / "audit").mkdir()
    manifest = dict(
        campaign=campaign,
        model=model,
        arm=arm,
        repeat=repeat,
        start_source=str(source),
        baseline_sha256=before,
        excluded=[*sorted(EXCLUDED), ".venv*", "*.pyc", "*.pyo"],
        input_sha256=hashes(destination / "input"),
        resource_sha256=hashes(destination / "materials"),
        prompt_sha256=digest(destination / "PROMPT.md"),
        launch_ready=False,
        isolation_enforced=False,
        pending=[
            "external filesystem/network isolation",
            "actual model/reasoning setting attestation",
            "runtime version preflight",
        ],
    )
    save_json(destination / "audit/preparation.json", manifest)
    if (
        hashes(source) != before
        or hashes(destination / "baseline") != before
        or hashes(destination / "work") != before
    ):
        raise RuntimeError("starting submission integrity check failed")
    for name in ("baseline", "input", "materials"):
        for path in (destination / name).rglob("*"):
            path.chmod(path.stat().st_mode & ~0o222)
        (destination / name).chmod(0o555)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=CONFIG["starting_submissions"], required=True)
    parser.add_argument("--arm", choices=CONFIG["arms"], required=True)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--materials", type=Path, required=True)
    parser.add_argument("--python-bin", type=Path, required=True)
    parser.add_argument(
        "--campaign", choices=("pilot_factorial", "combined_all_models"), default="pilot_factorial"
    )
    args = parser.parse_args()
    prepare(
        args.model,
        args.arm,
        args.repeat,
        args.destination,
        args.suite,
        args.materials,
        args.python_bin,
        campaign=args.campaign,
    )
    print("Staged one run. NOT launched. External isolation still required.")
