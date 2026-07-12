"""Run the fixed evaluation set over one or more models (spec §19).

Compares base Model L, its SFT variant, and Model M — same prompts, so the
ability gaps are directly comparable. Saves experiments/comparisons/eval.json.

Usage: uv run --no-sync python jp_llm_lab/scripts/run_eval.py
"""

from __future__ import annotations

import torch
from jp_llm_lab.evaluation.eval_prompts import build_eval_set
from jp_llm_lab.evaluation.eval_runner import run_eval
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.tokenization.hf_bpe import HFBpeTokenizer
from jp_llm_lab.training.trainer import load_checkpoint
from jp_llm_lab.utils.io import repo_root, save_json


def load_model(run_dir):
    ckpt = sorted(run_dir.glob("checkpoints/*100pct*.pt"))[0]
    payload = torch.load(ckpt, map_location="cpu", weights_only=False)
    model = ClassicalGPT(ModelConfig.from_dict(payload["model_cfg"]))
    load_checkpoint(ckpt, model)
    tok = HFBpeTokenizer.load(next(run_dir.glob("*.tokenizer.json")))
    return model, tok


def main() -> None:
    root = repo_root()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    n_prompts = len(build_eval_set())
    print(f"evaluation set: {n_prompts} prompts")

    models = {
        "model_l_30m": root / "experiments/runs/m4_model_l_modern_seed42",
        "model_m_10m": root / "experiments/runs/m2_model_m_classical_seed42",
    }
    results = {}
    for name, run_dir in models.items():
        if not run_dir.exists():
            continue
        model, tok = load_model(run_dir)
        res = run_eval(model, tok, device)
        results[name] = res
        print(f"{name}: cloze_accuracy={res['overall']['cloze_accuracy']}")
        model.cpu()

    save_json({"n_prompts": n_prompts, "models": results}, root / "experiments" / "comparisons" / "eval.json")
    print("saved experiments/comparisons/eval.json")


if __name__ == "__main__":
    main()
    import os
    import sys

    sys.stdout.flush()
    os._exit(0)
