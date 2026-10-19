"""Command line: ``bond-timing snapshot``, ``run STAGE`` and ``report`` (design §3.6, §9).

The stage order is enforced here: PREREG.md must be committed before G1 and every
out-of-sample stage, OOS-A needs a passed G1, and OOS-B runs once (a lock file); a rerun
needs a reason and never replaces the verdict of record.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import click
import numpy as np
import pandas as pd

from .data.store import MACROKIT_RAW, RAW_ROOT

LAB = Path(__file__).resolve().parents[2]
RESULTS = LAB / "results"
RUNNERS = {
    "g0": ("bond_timing.stages", "run_g0"),
    "dev": ("bond_timing.stages", "run_dev"),
    "g1": ("bond_timing.g1", "run_g1"),
    "oos-a": ("bond_timing.oos_a", "run_oos_a"),
    "decompose": ("bond_timing.decomposition", "run_decomposition"),
    "g3": ("bond_timing.g3", "run_g3"),
    "oos-b": ("bond_timing.oos_b", "run_oos_b"),
    "decompose-monthly": ("bond_timing.decomposition", "run_monthly_decomposition"),
}
REQUIRES = {
    "g0": (),
    "dev": (),
    "g1": ("dev",),
    "oos-a": ("dev", "g1"),
    "decompose": ("oos_a",),
    "g3": ("oos_a",),
    "oos-b": ("dev", "oos_a", "g3"),
    "decompose-monthly": ("decompose", "oos_b"),  # PREREG §5: after the verdict of record
}
NEEDS_PREREG = ("g1", "oos-a", "decompose", "g3", "oos-b", "decompose-monthly")


class StageError(click.ClickException):
    """A stage was asked to run before the stages it depends on, or a second time."""


def _json_default(value):
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, (pd.Period, pd.Timestamp)):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"cannot serialise {type(value).__name__}")


def _git(*args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(LAB), *args], capture_output=True, text=True, check=False
    )
    return done.stdout.strip()


def input_records(raw_root: Path, macrokit_root: Path) -> dict[str, dict]:
    """The stored payload each input reads now: the newest manifest record with a path, for every
    indicator of the bond-timing store and for macrokit's us_term/gsw."""
    records: dict[str, dict] = {}
    for root, wanted in ((raw_root, None), (macrokit_root, {("us_term", "gsw")})):
        manifest = root / "manifest.jsonl"
        if not manifest.exists():
            continue
        for line in manifest.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue  # a blank or truncated line, as in macrokit.snapshot
            key = (record.get("source"), record.get("indicator"))
            if record.get("path") and (wanted is None or key in wanted):
                records[f"{key[0]}/{key[1]}"] = {
                    name: record.get(name) for name in ("sha256", "ingested_at", "url", "path")
                }
    return dict(sorted(records.items()))


def meta() -> dict:
    return {
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "dirty": bool(_git("status", "--porcelain", "--", ".", ":(exclude)results")),
        "prereg_commit": _git("log", "-1", "--format=%H", "--", "PREREG.md"),
        "inputs": {
            key: record["sha256"] for key, record in input_records(RAW_ROOT, MACROKIT_RAW).items()
        },
    }


def read_result(name: str, results: Path = RESULTS) -> dict:
    path = results / f"{name}.json"
    if not path.exists():
        raise StageError(f"{path} is missing; run its stage first")
    return json.loads(path.read_text(encoding="utf-8"))


def write_result(name: str, result: dict, results: Path, run_meta: dict) -> Path:
    results.mkdir(parents=True, exist_ok=True)
    path = results / f"{name}.json"
    text = json.dumps(
        {"meta": run_meta, **result}, indent=1, ensure_ascii=False, default=_json_default
    )
    path.write_text(text + "\n", encoding="utf-8")
    return path


def check_ready(stage: str, results: Path, prereg_commit: str) -> dict[str, dict]:
    prior = {name: read_result(name, results) for name in REQUIRES[stage]}
    if stage in NEEDS_PREREG and not prereg_commit:
        raise StageError("PREREG.md must be committed before G1 and the out-of-sample stages")
    if stage == "oos-a" and not prior["g1"].get("pass"):
        raise StageError("G1 did not pass; fix the tools before running OOS-A")
    return prior


def oos_b_target(results: Path, rerun_reason: str | None) -> tuple[str, dict]:
    lock = results / "oos_b.lock"
    if not lock.exists():
        return "oos_b", {}
    if not rerun_reason:
        raise StageError(
            f"OOS-B already ran ({lock.read_text().strip()}); pass --rerun-reason to run it again"
        )
    n = 1
    while (results / f"oos_b_rerun_{n}.json").exists():
        n += 1
    record = read_result("oos_b", results)["verdict"]
    return f"oos_b_rerun_{n}", {"rerun_reason": rerun_reason, "verdict_of_record": record}


def take_lock(results: Path, commit: str) -> None:
    results.mkdir(parents=True, exist_ok=True)
    with (results / "oos_b.lock").open("x", encoding="utf-8") as handle:
        handle.write(f"{datetime.now(UTC).isoformat(timespec='seconds')} {commit}\n")


@click.group()
def main() -> None:
    """Bond-timing study (design 2026-10-19)."""


@main.command()
def snapshot() -> None:
    """Fetch every raw input into the snapshot store."""
    from .data.snapshot import snapshot_all

    for line in snapshot_all():
        click.echo(line)


@main.command()
@click.argument("stage", type=click.Choice(list(RUNNERS)))
@click.option("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2), show_default=True)
@click.option("--rerun-reason", default=None, help="Required to run oos-b a second time.")
def run(stage: str, workers: int, rerun_reason: str | None) -> None:
    """Run one stage and write results/<stage>.json."""
    from .study import load_study

    run_meta = meta()
    prior = check_ready(stage, RESULTS, run_meta["prereg_commit"])
    name, extra = (stage.replace("-", "_"), {})
    if stage == "oos-b":
        name, extra = oos_b_target(RESULTS, rerun_reason)
        if name == "oos_b":
            take_lock(RESULTS, run_meta["git_commit"])
    module, function = RUNNERS[stage]
    runner = getattr(importlib.import_module(module), function)
    try:
        result = runner(load_study(), workers, prior)
    except BaseException:
        if name == "oos_b":
            (RESULTS / "oos_b.lock").unlink(missing_ok=True)  # nothing was seen; allow a clean run
        raise
    click.echo(write_result(name, {**extra, **result}, RESULTS, run_meta))


@main.command()
def inputs() -> None:
    """Write results/inputs.json: the stored payload (SHA-256, fetch time, URL) of every input."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "inputs.json"
    records = input_records(RAW_ROOT, MACROKIT_RAW)
    path.write_text(json.dumps(records, indent=1) + "\n", encoding="utf-8")
    click.echo(path)


@main.command()
def report() -> None:
    """Write results/summary.md from the results JSON."""
    from .report import render

    path = RESULTS / "summary.md"
    path.write_text(render(RESULTS), encoding="utf-8")
    click.echo(path)


if __name__ == "__main__":
    main()
