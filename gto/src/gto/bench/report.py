from __future__ import annotations

import json
import math
from collections.abc import Sequence
from pathlib import Path

import numpy as np


def fit_slope(iters: Sequence[float], expl: Sequence[float]) -> float:
    """Return the least-squares slope of ``log(expl)`` vs ``log(iters)``.

    Non-positive and non-finite points are outside the log domain and are
    dropped. At least two valid checkpoints with distinct iteration counts
    are required.
    """
    if len(iters) != len(expl):
        raise ValueError("iters and expl must have the same length")

    pairs = [
        (float(iteration), float(exploitability))
        for iteration, exploitability in zip(iters, expl, strict=True)
        if math.isfinite(float(iteration))
        and math.isfinite(float(exploitability))
        and iteration > 0
        and exploitability > 0
    ]
    if len(pairs) < 2:
        raise ValueError("need at least two positive finite checkpoints to fit a slope")

    x = np.log(np.asarray([pair[0] for pair in pairs], dtype=np.float64))
    y = np.log(np.asarray([pair[1] for pair in pairs], dtype=np.float64))
    centered_x = x - x.mean()
    denominator = float(np.dot(centered_x, centered_x))
    if denominator == 0.0:
        raise ValueError("need at least two distinct iteration counts to fit a slope")
    return float(np.dot(centered_x, y - y.mean()) / denominator)


def fit_window(checkpoints: list[dict], min_frac: float = 0.125) -> tuple[list, list]:
    """Return the pre-registered latter-region convergence fit window."""
    if not checkpoints:
        raise ValueError("checkpoints must not be empty")
    if not math.isfinite(min_frac) or not 0.0 < min_frac <= 1.0:
        raise ValueError("min_frac must be finite and in (0, 1]")

    max_iters = max(checkpoint["iters"] for checkpoint in checkpoints)
    keep = [checkpoint for checkpoint in checkpoints if checkpoint["iters"] >= max_iters * min_frac]
    return (
        [checkpoint["iters"] for checkpoint in keep],
        [checkpoint["expl"] for checkpoint in keep],
    )


def time_to(target_expl: float, checkpoints: list[dict]) -> float | None:
    """Return cumulative solve time at the first exploitability crossing.

    Crossing time is linearly interpolated in cumulative ``solve_s`` against
    ``log(expl)``. If the target is not reached, return ``None``.
    """
    if not math.isfinite(target_expl) or target_expl <= 0:
        raise ValueError("target_expl must be positive and finite")

    previous: dict | None = None
    for checkpoint in checkpoints:
        exploitability = float(checkpoint["expl"])
        solve_s = float(checkpoint["solve_s"])
        if not math.isfinite(exploitability) or not math.isfinite(solve_s):
            raise ValueError("checkpoint expl and solve_s must be finite")
        if exploitability <= target_expl:
            if previous is None or exploitability <= 0:
                return solve_s

            previous_expl = float(previous["expl"])
            previous_solve_s = float(previous["solve_s"])
            fraction = (math.log(previous_expl) - math.log(target_expl)) / (
                math.log(previous_expl) - math.log(exploitability)
            )
            return previous_solve_s + fraction * (solve_s - previous_solve_s)
        previous = checkpoint
    return None


def artifact_time_to(target_expl: float, run: dict) -> float | None:
    """Return the G-A1 artifact time: build + solve-to-target + final BR."""
    solve_s = time_to(target_expl, run["checkpoints"])
    if solve_s is None:
        return None
    timing = run["timing"]
    return float(timing["build_s"] + solve_s + timing["final_br_s"])


def load_dir(path: Path) -> list[dict]:
    """Load RunRecord JSON files sorted by case and seed."""
    path = Path(path)
    if not path.is_dir():
        raise NotADirectoryError(path)
    runs = [
        json.loads(json_path.read_text(encoding="utf-8"))
        for json_path in sorted(path.glob("*.json"))
    ]
    return sorted(runs, key=lambda run: (run["case"], run.get("seed", 0)))


def aggregate_seeds(runs: list[dict], min_frac: float = 0.125) -> list[dict]:
    """Aggregate convergence slopes across seed replicas of each case.

    Labels are kept separate so thread sweeps or other named variants of the
    same case are never mixed into one seed interval.
    """
    grouped: dict[tuple[str, str], dict[int, dict]] = {}
    for run in runs:
        seed_runs = grouped.setdefault((run["case"], run.get("label", "")), {})
        seed = int(run.get("seed", 0))
        previous = seed_runs.get(seed)
        rank = (
            run["checkpoints"][-1]["iters"] if run.get("checkpoints") else 0,
            run.get("resume_count", 0),
        )
        previous_rank = (
            previous["checkpoints"][-1]["iters"]
            if previous is not None and previous.get("checkpoints")
            else 0,
            previous.get("resume_count", 0) if previous is not None else 0,
        )
        if previous is None or rank > previous_rank:
            seed_runs[seed] = run

    aggregated = []
    for (case, label), seed_runs in sorted(grouped.items()):
        case_runs = [seed_runs[seed] for seed in sorted(seed_runs)]
        slopes = []
        for run in case_runs:
            try:
                slopes.append(fit_slope(*fit_window(run["checkpoints"], min_frac)))
            except ValueError:
                pass
        slopes.sort()
        aggregated.append(
            {
                "case": case,
                "label": label,
                "n_seeds": len(case_runs),
                "n_slopes": len(slopes),
                "slope_median": float(np.median(slopes)) if slopes else None,
                "slope_min": slopes[0] if slopes else None,
                "slope_max": slopes[-1] if slopes else None,
                "runs": case_runs,
            }
        )
    return aggregated


def _format_time(seconds: float) -> str:
    return f"{seconds / 60:.1f}m" if seconds >= 60 else f"{seconds:.1f}s"


def _markdown_cell(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def render_markdown(runs: list[dict], targets: tuple[float, ...] = (0.5, 0.3, 0.15, 0.05)) -> str:
    """Render one audit-table row per case/label seed group."""
    header = (
        "| case | label | seeds | slope median [min, max] | "
        + " | ".join(f"t→{target}bb" for target in targets)
        + " | peak RSS |\n"
    )
    separator = "|" + "---|" * (5 + len(targets)) + "\n"
    rows = []

    for aggregate in aggregate_seeds(runs):
        if aggregate["n_slopes"] == aggregate["n_seeds"]:
            slope_cell = (
                f"{aggregate['slope_median']:.2f} "
                f"[{aggregate['slope_min']:.2f}, {aggregate['slope_max']:.2f}]"
            )
        elif aggregate["n_slopes"] > 0:
            slope_cell = "censored"
        else:
            slope_cell = "—"
        cells = [
            aggregate["case"],
            aggregate["label"],
            aggregate["n_seeds"],
            slope_cell,
        ]
        for target in targets:
            times = [artifact_time_to(target, run) for run in aggregate["runs"]]
            reached = [time for time in times if time is not None]
            if reached and len(reached) == len(times):
                cells.append(_format_time(float(np.median(reached))))
            elif reached:
                cells.append("censored")
            else:
                cells.append("—")

        peak_rss_mb = max(run["peak_rss_mb"] for run in aggregate["runs"])
        cells.append(f"{peak_rss_mb / 1024:.1f} GB")
        rows.append("| " + " | ".join(_markdown_cell(cell) for cell in cells) + " |")

    return header + separator + "\n".join(rows) + "\n"
