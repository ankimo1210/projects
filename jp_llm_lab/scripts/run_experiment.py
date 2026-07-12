"""Run a YAML-specified experiment (Milestones 2-4).

Usage:
  uv run --no-sync python jp_llm_lab/scripts/run_experiment.py --config jp_llm_lab/configs/pilot/model_m_modern.yaml
"""

from __future__ import annotations

import argparse

from jp_llm_lab.training.experiment import run_experiment
from jp_llm_lab.training.train_config import load_yaml_config
from jp_llm_lab.utils.env import collect_env_report
from jp_llm_lab.utils.io import repo_root


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--run-name", default=None, help="override run_name in the config")
    args = ap.parse_args()
    spec = load_yaml_config(args.config)
    if args.run_name:
        spec["run_name"] = args.run_name

    env = collect_env_report()
    device = "cuda" if env.cuda_available else "cpu"
    seed = spec["train"].get("seed", 42)
    run_name = f"{spec['run_name']}_seed{seed}"
    run_dir = repo_root() / "experiments" / "runs" / run_name
    print(f"device={device} run={run_name}")

    result = run_experiment(spec, run_dir, device=device)
    print(
        f"done: steps={result.steps} tokens={result.tokens_seen:,} "
        f"wallclock={result.wallclock_sec:.1f}s val_loss={result.final_eval['loss']:.4f} "
        f"ppl={result.final_eval['ppl']:.2f}"
    )
    print(f"run dir: {result.run_dir}")


if __name__ == "__main__":
    main()
