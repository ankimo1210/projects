"""Command line: ``sector-leadlag snapshot``, ``run STAGE``, ``inputs``, ``corrections``, ``report``.

The stage order of design §3.5 is enforced here. Every stage needs a committed PREREG.md; main A
also needs passed G0 and G1 and a PREREG commit made after G1 ran (the chosen pairing and the
G1 result are written into it first). Main B needs main A's result committed, and runs once (a
lock file); a rerun needs a reason and never replaces the verdict of record.

``--data corrected`` reruns the stages on the corrected data of PREREG §5 (design 2026-10-20) into
results/corrected/, under the same gates and three more: the stored inputs are the record's
snapshot, PREREG.md has §5 committed after the record's main B, and results/corrected/
corrections.json passed the known-error check and lists exactly the changes the rules make.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import click
import numpy as np
import pandas as pd

from .data.store import RAW_ROOT, manifest_records

LAB = Path(__file__).resolve().parents[2]
RESULTS = LAB / "results"
CORRECTED = RESULTS / "corrected"
DATA = ("record", "corrected")
RUNNERS = {
    "g0": ("sector_leadlag.g0", "run_g0"),
    "g1": ("sector_leadlag.g1", "run_g1"),
    "main-a": ("sector_leadlag.main", "run_main_a"),
    "main-b": ("sector_leadlag.main", "run_main_b"),
    "diagnostics": ("sector_leadlag.diagnostics", "run_diagnostics"),
}
REQUIRES = {
    "g0": (),
    "g1": ("g0",),
    "main-a": ("g0", "g1"),
    "main-b": ("g0", "main_a"),
    "diagnostics": ("g0", "main_a", "main_b"),
}


class StageError(click.ClickException):
    """A stage was asked to run before the stages it depends on, or a second time."""


def _json_default(value):
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return str(value.date())
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"cannot serialise {type(value).__name__}")


def _git(*args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(LAB), *args], capture_output=True, text=True, check=False
    )
    return done.stdout.strip()


def inputs_digest(root: Path) -> tuple[str, int]:
    """One SHA-256 over the stored payload of every input, and how many inputs there are."""
    records = manifest_records(root)
    lines = "".join(f"{key} {record['sha256']}\n" for key, record in records.items())
    return hashlib.sha256(lines.encode()).hexdigest(), len(records)


def meta(results: str = "results") -> dict:
    """What a result was computed from; ``results`` is its folder, relative to the lab."""
    digest, count = inputs_digest(RAW_ROOT)
    return {
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "dirty": bool(_git("status", "--porcelain", "--", ".", ":(exclude)results")),
        "prereg_commit": _git("log", "-1", "--format=%H", "--", "PREREG.md"),
        "prereg_committed_at": _git("log", "-1", "--format=%cI", "--", "PREREG.md"),
        "main_a_commit": _git("log", "-1", "--format=%H", "--", f"{results}/main_a.json"),
        "inputs_digest": digest,
        "inputs_count": count,
    }


def corrected_meta() -> dict:
    """``meta`` of a result on the corrected data, with what its gates need."""
    run_meta = meta("results/corrected")
    prereg = (
        _git("show", f"{run_meta['prereg_commit']}:./PREREG.md")
        if run_meta["prereg_commit"]
        else ""
    )
    return {
        **run_meta,
        "data": "corrected",
        "prereg_has_section_5": any(line.startswith("## 5.") for line in prereg.splitlines()),
        "record_main_b_commit": _git("log", "-1", "--format=%H", "--", "results/main_b.json"),
        "record_main_b_committed_at": _git(
            "log", "-1", "--format=%cI", "--", "results/main_b.json"
        ),
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


def check_ready(stage: str, results: Path, run_meta: dict) -> dict[str, dict]:
    if not run_meta["prereg_commit"]:
        raise StageError("commit PREREG.md before running any stage (design §3.5)")
    prior = {name: read_result(name, results) for name in REQUIRES[stage]}
    if "g0" in prior and not prior["g0"]["pass"]:
        raise StageError("G0 found no pairing that reproduces the ETF result (replication_failed)")
    if stage == "main-a":
        if not prior["g1"]["pass"]:
            raise StageError("G1 did not pass; fix the tools before running main A")
        ran = datetime.fromisoformat(prior["g1"]["meta"]["ran_at"])
        if datetime.fromisoformat(run_meta["prereg_committed_at"]) <= ran:
            raise StageError(
                "write the chosen pairing and the G1 result into PREREG.md and commit it"
                " before main A"
            )
    if stage == "main-b" and not run_meta["main_a_commit"]:
        raise StageError("commit results/main_a.json before main B (design §3.5)")
    return prior


def check_snapshot(run_meta: dict, record: Path) -> None:
    """The corrected data must come from the snapshot of the record's verdict (design §4)."""
    stored = read_result("main_b", record)["meta"]["inputs_digest"]
    if run_meta["inputs_digest"] != stored:
        raise StageError(
            "the stored inputs are not the snapshot of the record's main B; correct that snapshot"
        )


def check_prereg_section(run_meta: dict) -> None:
    """Every stage on corrected data needs PREREG §5, committed after the record's main B."""
    if not run_meta["prereg_has_section_5"]:
        raise StageError("write the corrected-data rules into PREREG.md §5 and commit it first")
    record = run_meta["record_main_b_committed_at"]
    prereg = datetime.fromisoformat(run_meta["prereg_committed_at"])
    if not record or prereg <= datetime.fromisoformat(record):
        raise StageError("commit PREREG.md §5 after the record's results/main_b.json")


def plain(value):
    """``value`` as it reads back from a results file."""
    return json.loads(json.dumps(value, default=_json_default))


def check_corrections(changes: tuple[dict, ...], results: Path) -> str:
    """corrections.json passed the known-error check and lists exactly ``changes``; its SHA-256."""
    path = results / "corrections.json"
    stored = read_result("corrections", results)
    if stored["missing_known"]:
        raise StageError(f"{path} failed the known-error check; fix the rules first")
    if stored["changes"] != plain(list(changes)):
        raise StageError(f"{path} does not match the rules; run `sector-leadlag corrections` again")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main_b_target(results: Path, rerun_reason: str | None) -> tuple[str, dict]:
    lock = results / "main_b.lock"
    if not lock.exists():
        return "main_b", {}
    if not rerun_reason:
        raise StageError(
            f"main B already ran ({lock.read_text().strip()}); pass --rerun-reason to run it again"
        )
    n = 1
    while (results / f"main_b_rerun_{n}.json").exists():
        n += 1
    record = read_result("main_b", results)["verdict"]
    return f"main_b_rerun_{n}", {"rerun_reason": rerun_reason, "verdict_of_record": record}


def take_lock(results: Path, commit: str) -> None:
    results.mkdir(parents=True, exist_ok=True)
    with (results / "main_b.lock").open("x", encoding="utf-8") as handle:
        handle.write(f"{datetime.now(UTC).isoformat(timespec='seconds')} {commit}\n")


@click.group()
def main() -> None:
    """US-Japan sector lead-lag study (design 2026-10-19)."""


@main.command()
def snapshot() -> None:
    """Fetch the listed-issues file and every price history into the snapshot store."""
    from .data.snapshot import snapshot_all

    for line in snapshot_all():
        click.echo(line)


@main.command()
@click.argument("stage", type=click.Choice(list(RUNNERS)))
@click.option("--rerun-reason", default=None, help="Required to run main-b a second time.")
@click.option(
    "--data",
    type=click.Choice(DATA),
    default="record",
    help="corrected: rerun on the corrected data of PREREG §5 into results/corrected/.",
)
def run(stage: str, rerun_reason: str | None, data: str) -> None:
    """Run one stage and write results/<stage>.json (or results/corrected/<stage>.json)."""
    from .study import load_study

    corrected = data == "corrected"
    results = CORRECTED if corrected else RESULTS
    run_meta = corrected_meta() if corrected else meta()
    if corrected:
        check_snapshot(run_meta, RESULTS)
        check_prereg_section(run_meta)
    prior = check_ready(stage, results, run_meta)
    name, extra = stage.replace("-", "_"), {}
    if stage == "main-b":
        name, extra = main_b_target(results, rerun_reason)
    study = load_study(corrected=corrected)
    if corrected:
        run_meta["corrections_sha256"] = check_corrections(study.corrections, CORRECTED)
    if name == "main_b":
        take_lock(results, run_meta["git_commit"])
    module, function = RUNNERS[stage]
    runner = getattr(importlib.import_module(module), function)
    try:
        result = runner(study, prior)
    except BaseException:
        if name == "main_b":
            (results / "main_b.lock").unlink(missing_ok=True)  # nothing was seen; allow a clean run
        raise
    click.echo(write_result(name, {**extra, **result}, results, run_meta))


@main.command()
def corrections() -> None:
    """Apply the rules of PREREG §5 and write results/corrected/corrections.json (no stage)."""
    from .corrections import counts, missing_known
    from .study import load_study

    run_meta = {**meta("results/corrected"), "data": "corrected"}
    check_snapshot(run_meta, RESULTS)
    changes = list(load_study(corrected=True).corrections)
    missing = missing_known(changes)
    result = {"counts": counts(changes), "missing_known": missing, "changes": changes}
    click.echo(write_result("corrections", result, CORRECTED, run_meta))
    if missing:
        labels = "; ".join(item["label"] for item in missing)
        raise StageError(f"no rule changed these known errors (design §3): {labels}")


@main.command()
def inputs() -> None:
    """Write results/inputs.json: the stored payload (SHA-256, fetch time, URL) of every input."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "inputs.json"
    path.write_text(json.dumps(manifest_records(RAW_ROOT), indent=1) + "\n", encoding="utf-8")
    click.echo(path)


@main.command()
@click.option("--data", type=click.Choice(DATA), default="record")
def report(data: str) -> None:
    """Write results/summary.md, or results/corrected/summary.md beside the record."""
    from .report import render, render_corrected

    if data == "corrected":
        path = CORRECTED / "summary.md"
        path.write_text(render_corrected(RESULTS, CORRECTED), encoding="utf-8")
    else:
        path = RESULTS / "summary.md"
        path.write_text(render(RESULTS), encoding="utf-8")
    click.echo(path)


if __name__ == "__main__":
    main()
