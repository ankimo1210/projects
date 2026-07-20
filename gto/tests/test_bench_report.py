import json
import math

import pytest
from gto.bench import (
    aggregate_seeds,
    artifact_time_to,
    fit_slope,
    fit_window,
    load_dir,
    render_markdown,
    time_to,
)


def _synthetic_run(
    case="synth",
    seed=42,
    c=100.0,
    slope=-1.0,
    secs_per_iter=0.01,
    label="t",
):
    iters = [10, 20, 40, 80, 160, 320]
    return {
        "schema_version": 1,
        "case": case,
        "config": "cfg",
        "label": label,
        "git_commit": "deadbeef",
        "dirty": False,
        "seed": seed,
        "iterations": 320,
        "points": 6,
        "threads": 1,
        "build_profile": "release",
        "cpu": "c",
        "kernel": "k",
        "cmdline": "x",
        "table_bytes": 1,
        "peak_rss_mb": 10.0,
        "resume_count": 0,
        "timing": {
            "build_s": 2.0,
            "solve_s": 3.2,
            "checkpoint_br_s": 0.5,
            "final_br_s": 1.0,
        },
        "checkpoints": [
            {
                "iters": t,
                "solve_s": t * secs_per_iter,
                "br_s": 0.1,
                "expl": c * t**slope,
                "br0": 0.0,
                "br1": 0.0,
            }
            for t in iters
        ],
    }


def test_fit_slope_recovers_exponent():
    checkpoints = _synthetic_run(slope=-1.0)["checkpoints"]
    slope = fit_slope(
        [checkpoint["iters"] for checkpoint in checkpoints],
        [checkpoint["expl"] for checkpoint in checkpoints],
    )
    assert math.isclose(slope, -1.0, abs_tol=1e-9)


def test_fit_slope_rejects_mismatched_lengths():
    with pytest.raises(ValueError, match="same length"):
        fit_slope([1, 2, 3], [1.0, 0.5])


def test_fit_window_keeps_the_latter_region():
    checkpoints = _synthetic_run()["checkpoints"]
    iterations, exploitabilities = fit_window(checkpoints, min_frac=0.125)
    assert iterations == [40, 80, 160, 320]
    assert len(exploitabilities) == 4


def test_time_to_exact_at_checkpoint_and_interpolates():
    checkpoints = _synthetic_run(c=100.0, slope=-1.0)["checkpoints"]
    assert math.isclose(time_to(1.25, checkpoints), 0.8, rel_tol=1e-9)

    lo, hi = checkpoints[3], checkpoints[4]
    fraction = (math.log(lo["expl"]) - math.log(1.0)) / (
        math.log(lo["expl"]) - math.log(hi["expl"])
    )
    expected = lo["solve_s"] + fraction * (hi["solve_s"] - lo["solve_s"])
    assert math.isclose(time_to(1.0, checkpoints), expected, rel_tol=1e-9)
    assert time_to(1e-9, checkpoints) is None


def test_time_to_rejects_nonpositive_target():
    with pytest.raises(ValueError, match="positive"):
        time_to(0.0, _synthetic_run()["checkpoints"])


def test_artifact_time_adds_build_and_final_br():
    run = _synthetic_run()
    assert math.isclose(artifact_time_to(1.25, run), 2.0 + 0.8 + 1.0, rel_tol=1e-9)
    assert artifact_time_to(1e-9, run) is None


def test_load_aggregate_and_render(tmp_path):
    for seed in (1, 2, 3):
        (tmp_path / f"a_s{seed}.json").write_text(
            json.dumps(_synthetic_run("case_a", seed=seed)), encoding="utf-8"
        )
    (tmp_path / "b.json").write_text(json.dumps(_synthetic_run("case_b")), encoding="utf-8")

    runs = load_dir(tmp_path)
    assert [run["case"] for run in runs] == ["case_a", "case_a", "case_a", "case_b"]
    aggregated = aggregate_seeds(runs)
    case_a = next(row for row in aggregated if row["case"] == "case_a")
    assert case_a["n_seeds"] == 3
    assert math.isclose(case_a["slope_median"], -1.0, abs_tol=1e-9)

    markdown = render_markdown(runs)
    assert "case_a" in markdown
    assert "case_b" in markdown
    assert "slope" in markdown


def test_render_marks_partially_reached_target_as_censored():
    runs = [
        _synthetic_run("case_a", seed=1, c=100.0),
        _synthetic_run("case_a", seed=2, c=200.0),
    ]
    markdown = render_markdown(runs, targets=(0.5, 0.05))
    row = next(line for line in markdown.splitlines() if line.startswith("| case_a"))
    assert "censored" in row
    assert "—" in row


def test_aggregate_keeps_distinct_labels_separate():
    runs = [
        _synthetic_run("case_a", seed=1, label="threads-1"),
        _synthetic_run("case_a", seed=2, label="threads-2"),
    ]
    aggregated = aggregate_seeds(runs)
    assert [(row["label"], row["n_seeds"]) for row in aggregated] == [
        ("threads-1", 1),
        ("threads-2", 1),
    ]


def test_aggregate_deduplicates_resumed_artifacts_by_seed():
    original = _synthetic_run("case_a", seed=1)
    resumed = _synthetic_run("case_a", seed=1)
    resumed["resume_count"] = 2
    aggregated = aggregate_seeds([original, resumed])
    assert aggregated[0]["n_seeds"] == 1
    assert aggregated[0]["runs"] == [resumed]


def test_render_handles_too_few_points_for_a_slope():
    run = _synthetic_run("case_a")
    run["checkpoints"] = run["checkpoints"][:1]
    markdown = render_markdown([run])
    row = next(line for line in markdown.splitlines() if line.startswith("| case_a"))
    assert " | — | " in row
