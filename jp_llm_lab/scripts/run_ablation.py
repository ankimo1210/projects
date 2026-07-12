"""Classical→Modern ablation chain (spec §7.3).

One architectural change at a time, each trained on the pilot snapshot with
several seeds. Records val loss, tokens/sec, param count, activation RMS,
calibration (top-1 confidence), and generations. Results feed NB18 and the
report — this is the controlled-experiment centerpiece of Milestone 3.

Chain (each step flips ONE switch from the previous):
    0 classical           layernorm + learned + gelu + bias
    1 +rmsnorm            rmsnorm  + learned + gelu + bias
    2 +rope               rmsnorm  + rope    + gelu + bias
    3 +swiglu             rmsnorm  + rope    + swiglu + bias
    4 +nobias (=modern)   rmsnorm  + rope    + swiglu + no-bias

Usage: uv run --no-sync python jp_llm_lab/scripts/run_ablation.py [--seeds 3] [--steps 300]
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

CHAIN = [
    ("classical", dict(norm="layernorm", pos="learned", mlp="gelu", bias=True)),
    ("rmsnorm", dict(norm="rmsnorm", pos="learned", mlp="gelu", bias=True)),
    ("rope", dict(norm="rmsnorm", pos="rope", mlp="gelu", bias=True)),
    ("swiglu", dict(norm="rmsnorm", pos="rope", mlp="swiglu", bias=True)),
    ("modern", dict(norm="rmsnorm", pos="rope", mlp="swiglu", bias=False)),
]

BASE = dict(d_model=320, n_heads=8, n_layers=6, context_len=512, attn_impl="sdpa")
PROMPTS = ["日本の首都は", "科学とは、", "むかしむかし、"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--steps", type=int, default=300)
    args = ap.parse_args()
    root = repo_root()
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tok = HFBpeTokenizer.load(root / "tokenizer" / "bpe8k_v1.tokenizer.json", version="bpe8k_v1")
    train_tokens = load_tokens("pilot", "bpe8k_v1")[:8_000_000]
    val_tokens = load_tokens("validation", "bpe8k_v1")[:400_000]

    summary = {"chain": [c[0] for c in CHAIN], "seeds": args.seeds, "steps": args.steps, "results": {}}
    for name, switches in CHAIN:
        cfg = ModelConfig(vocab_size=tok.vocab_size, **BASE, **switches)
        n_params = ClassicalGPT(cfg).param_breakdown()["total"]
        per_seed = []
        for seed in range(42, 42 + args.seeds):
            model = ClassicalGPT(cfg)
            tcfg = TrainConfig(
                seed=seed, steps=args.steps, batch_size=24, grad_accum=1, context_len=512,
                lr=6e-4, warmup_frac=0.03, weight_decay=0.1, dtype="bf16",
                log_interval=25, eval_interval=args.steps, eval_batches=20, ratio_interval=50,
                checkpoint_fracs=(1.0,), fixed_prompts=PROMPTS if seed == 42 else [], max_new_tokens=60,
            )
            run_dir = root / "experiments" / "runs" / f"m3_ablation_{name}_seed{seed}"
            result = train_lm(model, train_tokens, val_tokens, tcfg, run_dir, tokenizer=tok, device=device,
                              extra_meta={"ablation": name, "switches": switches})
            per_seed.append(result.final_eval)
            print(f"  {name:10s} seed{seed}: val_loss={result.final_eval['loss']:.4f} "
                  f"ppl={result.final_eval['ppl']:.1f}", flush=True)
        losses = [e["loss"] for e in per_seed]
        mean = sum(losses) / len(losses)
        var = sum((x - mean) ** 2 for x in losses) / max(1, len(losses) - 1)
        summary["results"][name] = {
            "switches": switches,
            "n_params": n_params,
            "val_loss_mean": mean,
            "val_loss_std": var**0.5,
            "val_loss_seeds": losses,
            "ppl_mean": sum(e["ppl"] for e in per_seed) / len(per_seed),
            "top1_conf_mean": sum(e["top1_conf"] for e in per_seed) / len(per_seed),
            "entropy_mean": sum(e["entropy"] for e in per_seed) / len(per_seed),
        }
        print(f"{name:10s}: val_loss {mean:.4f} ± {var**0.5:.4f} ({n_params:,} params)", flush=True)

    save_json({**summary, "meta": collect_run_metadata()}, root / "experiments" / "comparisons" / "ablation_chain.json")
    print("saved experiments/comparisons/ablation_chain.json")


if __name__ == "__main__":
    main()
    import os
    import sys

    sys.stdout.flush()
    os._exit(0)
