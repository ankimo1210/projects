"""Stage one combined papers + QuantLib run for each of the seven models.

No candidate code is executed and no model sessions are started.
"""

import argparse
import hashlib
import json
from pathlib import Path

from datasets import outside_git, save_json
from prepare_run import CONFIG, hashes, prepare


def fingerprint(root):
    return hashlib.sha256(json.dumps(hashes(root), sort_keys=True).encode()).hexdigest()


def combined(root, suite, materials, quantlib_python):
    root = outside_git(root)
    if root.exists():
        raise FileExistsError("combined campaign already exists; refusing to overwrite")
    models = CONFIG["combined_models"]
    if len(models) != len(set(models)) or set(models) != set(CONFIG["starting_submissions"]):
        raise ValueError("combined campaign must contain every registered model exactly once")
    legacy = root.parent / "pilot"
    legacy_hash = fingerprint(legacy) if legacy.exists() else None
    root.mkdir(parents=True, mode=0o700)
    runs = []
    for order, model in enumerate(models, 1):
        path = root / f"{model}_r1"
        prepare(
            model, "D", 1, path, suite, materials, quantlib_python, campaign="combined_all_models"
        )
        runs.append(
            dict(
                order=order,
                model=model,
                arm="D",
                repeat=1,
                path=str(path),
                python_bin=str(quantlib_python),
                status="prepared_not_started",
            )
        )
    if legacy_hash is not None and fingerprint(legacy) != legacy_hash:
        raise RuntimeError("legacy pilot changed during preparation")
    save_json(
        root / "run_plan.json",
        dict(
            campaign="combined_all_models",
            design="single_arm_before_after",
            runs=runs,
            launch_ready=False,
            minutes_per_run=CONFIG["minutes_per_run"],
            maximum_agent_minutes=CONFIG["minutes_per_run"] * len(runs),
            separate_resource_effects_identifiable=False,
            legacy_pilot_sha256=legacy_hash,
        ),
    )
    print(f"Prepared {len(runs)} combined runs; one session per model; none started.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "suite", "materials", "quantlib-python"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    combined(args.root, args.suite, args.materials, args.quantlib_python)
