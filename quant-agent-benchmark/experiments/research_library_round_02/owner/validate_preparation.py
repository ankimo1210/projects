"""Read-only checks of staged runs, old evidence, resource separation and runtimes."""

import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path

from datasets import digest, save_json
from prepare_combined import fingerprint
from prepare_run import BENCH, CONFIG, KIT, hashes


def validate(private, campaign="pilot_factorial"):
    if campaign not in ("pilot_factorial", "combined_all_models"):
        raise ValueError("unknown campaign")
    checks = []

    def check(name, condition):
        checks.append(dict(name=name, passed=bool(condition)))

    for folder, key in (("input", "public_file_hashes"), ("evaluator", "evaluator_file_hashes")):
        manifest = json.loads((BENCH / folder / "MANIFEST.json").read_text())
        for relative, expected in manifest[key].items():
            check(f"old_{folder}:{relative}", digest(BENCH / folder / relative) == expected)
    plan_folder = "combined_all_models" if campaign == "combined_all_models" else "pilot"
    plan = json.loads((private / plan_folder / "run_plan.json").read_text())
    expected_assignments = (
        {(model, "D", 1) for model in CONFIG["combined_models"]}
        if campaign == "combined_all_models"
        else {
            (model, arm, repeat)
            for model in CONFIG["pilot_models"]
            for arm in CONFIG["arms"]
            for repeat in range(1, CONFIG["repeats"] + 1)
        }
    )
    check("assignment_count", len(plan["runs"]) == len(expected_assignments))
    check(
        "assignments_exact",
        {(r["model"], r["arm"], r["repeat"]) for r in plan["runs"]} == expected_assignments,
    )
    check("no_automatic_launch", plan["launch_ready"] is False)
    if campaign == "combined_all_models":
        check("single_arm_not_factorial", plan["separate_resource_effects_identifiable"] is False)
        if plan.get("legacy_pilot_sha256") is not None:
            check(
                "legacy_pilot_unchanged",
                fingerprint(private / "pilot") == plan["legacy_pilot_sha256"],
            )
    private_hashes = json.loads((private / "suite/manifest.json").read_text())["hashes"]
    check(
        "private_suite_integrity",
        all(
            digest(private / "suite" / path) == expected
            for path, expected in private_hashes.items()
        ),
    )
    for run in plan["runs"]:
        root = Path(run["path"])
        label = f"{run['model']}_{run['arm']}_r{run['repeat']}"
        prep = json.loads((root / "audit/preparation.json").read_text())
        check(label + ":campaign_matches", prep.get("campaign", "pilot_factorial") == campaign)
        if "prompt_sha256" in prep:
            check(label + ":prompt_integrity", digest(root / "PROMPT.md") == prep["prompt_sha256"])
        runtime_kind = "quantlib" if CONFIG["arms"][run["arm"]]["quantlib"] else "base"
        check(
            label + ":assigned_runtime",
            Path(run["python_bin"]).absolute()
            == (private.parent / f"runtime-round-02-{runtime_kind}/bin/python").absolute(),
        )
        check(
            label + ":source_unchanged",
            hashes(Path(prep["start_source"])) == prep["baseline_sha256"],
        )
        check(label + ":baseline_copy", hashes(root / "baseline") == prep["baseline_sha256"])
        check(label + ":work_copy", hashes(root / "work") == prep["baseline_sha256"])
        check(label + ":input_integrity", hashes(root / "input") == prep["input_sha256"])
        check(label + ":resources_integrity", hashes(root / "materials") == prep["resource_sha256"])
        expected = {
            g
            for g, enabled in (
                ("papers", CONFIG["arms"][run["arm"]]["papers"]),
                ("quantlib", CONFIG["arms"][run["arm"]]["quantlib"]),
            )
            if enabled
        }
        check(
            label + ":only_assigned_resources",
            {p.name for p in (root / "materials").iterdir()} == expected,
        )
        check(
            label + ":no_truth_in_input",
            set(prep["input_sha256"])
            == {"TASK.md", "market_data/CONVENTIONS.md", "market_data/market_observations.csv"},
        )
        check(
            label + ":same_training_market",
            digest(root / "input/market_data/market_observations.csv")
            == digest(private / "suite/training/market_observations.csv"),
        )
        check(label + ":prompt_assigned", "{{" not in (root / "PROMPT.md").read_text())
        check(
            label + ":isolation_not_claimed",
            prep["isolation_enforced"] is False and prep["launch_ready"] is False,
        )
        check(
            label + ":immutable_payload",
            all(
                (p.stat().st_mode & 0o222) == 0
                for name in ("baseline", "input", "materials")
                for p in (root / name).rglob("*")
            ),
        )
    query = "import json,importlib.metadata as m,sys; print(json.dumps({'python':sys.version,'packages':{d.metadata['Name'].lower():d.version for d in m.distributions()}}))"
    envs = {}
    for label in ("base", "quantlib"):
        executable = private.parent / f"runtime-round-02-{label}/bin/python"
        envs[label] = json.loads(subprocess.check_output([str(executable), "-c", query], text=True))
    base = envs["base"]["packages"]
    extra = envs["quantlib"]["packages"].copy()
    check("quantlib_pinned", extra.pop("quantlib", None) == "1.43")
    check("base_has_no_quantlib", "quantlib" not in base)
    check("otherwise_same_packages", base == extra)
    check("same_python", envs["base"]["python"] == envs["quantlib"]["python"])
    suite = unittest.defaultTestLoader.discover(str(KIT / "tests"))
    tested = unittest.TextTestRunner(verbosity=1, stream=sys.stderr).run(suite)
    check("unit_tests", tested.wasSuccessful())
    result = dict(
        campaign=campaign,
        preparation_valid=all(c["passed"] for c in checks),
        checks=checks,
        check_count=len(checks),
        tests_run=tested.testsRun,
        tests_failed=len(tested.failures) + len(tested.errors),
        launch_ready=False,
        models_started=0,
        runtimes=envs,
        required_before_launch=[
            "host-enforced filesystem/network isolation and access-denial probe",
            "actual model/reasoning/session-ID attestation",
        ],
        kit_source_hashes={
            str(p.relative_to(KIT)): digest(p)
            for p in KIT.rglob("*")
            if p.is_file() and p.suffix in (".py", ".md", ".txt")
        },
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--campaign", choices=("pilot_factorial", "combined_all_models"), default="pilot_factorial"
    )
    args = parser.parse_args()
    result = validate(args.private_root, args.campaign)
    save_json(args.output, result)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "preparation_valid",
                    "check_count",
                    "tests_run",
                    "tests_failed",
                    "launch_ready",
                    "models_started",
                )
            }
        )
    )
    sys.exit(0 if result["preparation_valid"] else 1)
