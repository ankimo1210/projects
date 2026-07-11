"""Matched size-scaling sweep (spec §19).

Train several model SIZES under identical conditions (same corpus, tokens,
architecture, tokenizer, optimizer) so validation loss vs parameters is a
clean ceteris-paribus scaling curve. This is separate from the M4 main run
(which optimized one big model); here everything but size is fixed.

Usage: uv run --no-sync python jp_llm_lab/scripts/run_scaling.py [--steps 500]
"""

from __future__ import annotations

import argparse

import torch
from jp_llm_lab.data.tokenized_cache import load_tokens
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.tokenization.hf_bpe import HFBpeTokenizer
from jp_llm_lab.training.train_config import TrainConfig
from jp_llm_lab.training.trainer import train_lm
from jp_llm_lab.utils.io import repo_root, save_json
from jp_llm_lab.utils.runmeta import collect_run_metadata

SIZES = [
    ("xs", dict(d_model=128, n_heads=4, n_layers=4)),
    ("s", dict(d_model=256, n_heads=8, n_layers=6)),
    ("m", dict(d_model=384, n_heads=8, n_layers=6)),
    ("l", dict(d_model=512, n_heads=8, n_layers=8)),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--steps", type=int, default=500)
    args = ap.parse_args()
    root = repo_root()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = HFBpeTokenizer.load(root / "tokenizer" / "bpe8k_v1.tokenizer.json", version="bpe8k_v1")
    train_tokens = load_tokens("pilot", "bpe8k_v1")[:8_000_000]
    val_tokens = load_tokens("validation", "bpe8k_v1")[:400_000]

    points = []
    for name, arch in SIZES:
        cfg = ModelConfig.modern(vocab_size=tok.vocab_size, context_len=512, **arch)
        n_params = ClassicalGPT(cfg).param_breakdown()["total"]
        model = ClassicalGPT(cfg)
        tcfg = TrainConfig(
            seed=42, steps=args.steps, batch_size=24, grad_accum=1, context_len=512,
            lr=6e-4, warmup_frac=0.03, weight_decay=0.1, dtype="bf16",
            log_interval=50, eval_interval=args.steps, eval_batches=20, ratio_interval=100,
            checkpoint_fracs=(1.0,), fixed_prompts=[], max_new_tokens=40,
        )
        run_dir = root / "experiments" / "runs" / f"m4_scaling_{name}_seed42"
        result = train_lm(model, train_tokens, val_tokens, tcfg, run_dir, tokenizer=tok, device=device,
                          extra_meta={"scaling_point": name})
        points.append({
            "name": name, "n_params": n_params,
            "val_loss": result.final_eval["loss"], "ppl": result.final_eval["ppl"],
            "tokens_seen": result.tokens_seen, "wallclock_sec": round(result.wallclock_sec, 1),
        })
        print(f"{name:3s} {n_params:>10,} params  val_loss {result.final_eval['loss']:.4f}  "
              f"ppl {result.final_eval['ppl']:.1f}", flush=True)

    save_json({"points": points, "tokens_budget": args.steps * 24 * 512, "meta": collect_run_metadata()},
              root / "experiments" / "comparisons" / "scaling.json")
    print("saved experiments/comparisons/scaling.json")


if __name__ == "__main__":
    main()
    import os
    import sys

    sys.stdout.flush()
    os._exit(0)
