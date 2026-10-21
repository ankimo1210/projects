"""One output root per run, with the facts needed to reproduce it.

The manifest pins the registration (sha256 of ``prereg.json``), the code commit
and whether the tree was dirty, so a result can be traced to the rules that
were fixed before it was computed. An existing root is never overwritten.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from portfolio_analyzer.ai_bubble.inputs import parse_utc

DATA_ROOT = Path("/home/kazumasa/projects/_data/portfolio-analyzer/ai-bubble")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_state(repo: Path | None = None) -> tuple[str, bool]:
    """HEAD commit and whether the working tree has changes."""
    where = str(repo or Path(__file__).resolve().parent)
    head = subprocess.run(
        ["git", "-C", where, "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    status = subprocess.run(
        ["git", "-C", where, "status", "--porcelain"], capture_output=True, text=True, check=True
    ).stdout
    return head, bool(status.strip())


def _stamp(when: datetime) -> str:
    return when.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run(
    root: Path,
    as_of_utc: str,
    prereg: Path,
    *,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    git: Callable[[], tuple[str, bool]] = git_state,
) -> Path:
    as_of = parse_utc(as_of_utc, "as_of_utc")
    created = now().astimezone(UTC)
    run = Path(root) / f"{as_of:%Y%m%dT%H%MZ}-r{created:%Y%m%dT%H%M%SZ}"
    run.mkdir(parents=True, exist_ok=False)
    commit, dirty = git()
    manifest = {
        "as_of_utc": _stamp(as_of),
        "created_at": _stamp(created),
        "prereg_path": str(prereg),
        "prereg_sha256": sha256_file(prereg),
        "git_commit": commit,
        "git_dirty": dirty,
        "inputs": [],
        "outputs": [],
    }
    (run / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return run


def recorded_inputs(run: Path, prefix: str) -> dict[str, dict]:
    """Manifest records of the raw files under ``prefix``, keyed by run-relative path.

    A path fetched twice keeps its latest record, which describes the file now
    on disk; a file whose bytes no longer match that record is refused.
    """
    manifest = json.loads((Path(run) / "manifest.json").read_text())
    latest = {
        entry["path"]: entry for entry in manifest["inputs"] if entry["path"].startswith(prefix)
    }
    for rel, entry in latest.items():
        if sha256_file(Path(run) / rel) != entry["sha256"]:
            raise ValueError(f"{rel}: sha256 differs from the manifest record")
    return latest


def _save(run: Path, manifest: dict) -> None:
    (Path(run) / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )


def record_outputs(run: Path) -> list[dict]:
    """List every derived file of the run (not the raw downloads) with its sha256."""
    run = Path(run)
    outputs = []
    for part in ("public", "private"):
        base = run / part
        for path in sorted(base.rglob("*")) if base.exists() else []:
            if path.is_file() and path.relative_to(base).parts[0] != "raw":
                outputs.append(
                    {
                        "path": str(path.relative_to(run)),
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    }
                )
    manifest = json.loads((run / "manifest.json").read_text())
    manifest["outputs"] = outputs
    _save(run, manifest)
    return outputs


def record_prereg_amendment(
    run: Path, prereg: Path, reason: str, *, now: Callable[[], datetime] = lambda: datetime.now(UTC)
) -> None:
    """Note a registration change made during the run; the original hash stays."""
    manifest = json.loads((Path(run) / "manifest.json").read_text())
    amendments = manifest.setdefault("prereg_amendments", [])
    previous = amendments[-1]["sha256"] if amendments else manifest["prereg_sha256"]
    amendments.append(
        {
            "at": _stamp(now()),
            "previous_sha256": previous,
            "sha256": sha256_file(prereg),
            "reason": reason,
        }
    )
    _save(run, manifest)
