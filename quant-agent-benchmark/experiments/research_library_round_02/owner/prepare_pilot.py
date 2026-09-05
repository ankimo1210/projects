"""Prepare the 12 default pilot folders; never create or start model sessions."""

import argparse
import random
from pathlib import Path

from datasets import outside_git, save_json
from prepare_run import CONFIG, prepare


def pilot(root, suite, materials, base_python, quantlib_python):
    root = outside_git(root)
    if root.exists():
        raise FileExistsError("pilot already exists; do not overwrite or silently resume")
    root.mkdir(parents=True, mode=0o700)
    assignments = [
        (model, arm, repeat)
        for model in CONFIG["pilot_models"]
        for repeat in range(1, CONFIG["repeats"] + 1)
        for arm in CONFIG["arms"]
    ]
    # Operational order seed only: unrelated to unpublished curve seeds.
    random.Random(20260905).shuffle(assignments)
    runs = []
    for order, (model, arm, repeat) in enumerate(assignments, 1):
        path = root / f"{model}_{arm}_r{repeat}"
        executable = quantlib_python if CONFIG["arms"][arm]["quantlib"] else base_python
        prepare(model, arm, repeat, path, suite, materials, executable)
        runs.append(
            dict(
                order=order,
                model=model,
                arm=arm,
                repeat=repeat,
                path=str(path),
                python_bin=str(executable),
                status="prepared_not_started",
            )
        )
    save_json(
        root / "run_plan.json",
        dict(
            runs=runs, launch_ready=False, minutes_per_run=60, maximum_agent_minutes=60 * len(runs)
        ),
    )
    print(f"Prepared {len(runs)} runs; no model sessions started.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "suite", "materials", "base-python", "quantlib-python"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    pilot(args.root, args.suite, args.materials, args.base_python, args.quantlib_python)
