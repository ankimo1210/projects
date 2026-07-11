"""Run all Milestone-3 calibrations and save results (spec §14).

Usage: uv run --no-sync python jp_llm_lab/scripts/run_calibrations.py [--which all|hardware|lr|init|batch]
"""

from __future__ import annotations

import argparse

import torch
from jp_llm_lab.calibration.batch_size import batch_size_calibration
from jp_llm_lab.calibration.hardware import hardware_calibration
from jp_llm_lab.calibration.init_diag import diagnose_init
from jp_llm_lab.calibration.lr_range import lr_range_test
from jp_llm_lab.data.tokenized_cache import load_tokens
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.utils.io import repo_root, save_json
from jp_llm_lab.utils.runmeta import collect_run_metadata

OUT = repo_root() / "experiments" / "calibrations"
VOCAB = 8192


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--which", default="all", choices=["all", "hardware", "lr", "init", "batch"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokens = load_tokens("pilot", "bpe8k_v1")
    train_tokens, val_tokens = tokens[:8_000_000], tokens[8_000_000:9_000_000]
    meta = collect_run_metadata()

    if args.which in ("all", "hardware"):
        print("hardware calibration…", flush=True)
        res = hardware_calibration(VOCAB, device)
        save_json({"results": res, "meta": meta}, OUT / "hardware.json")
        for r in res:
            print(" ", {k: r.get(k) for k in ["dtype", "attn", "compile", "B", "T", "tokens_per_sec", "peak_vram_gb"]})

    if args.which in ("all", "lr"):
        print("LR range test…", flush=True)
        model = ClassicalGPT(ModelConfig(vocab_size=VOCAB, d_model=256, n_layers=6, n_heads=8, context_len=256))
        res = lr_range_test(model, train_tokens, device=device, n_steps=90)
        save_json({**res, "meta": meta}, OUT / "lr_range.json")
        print(f"  suggested_lr={res['suggested_lr']:.2e} steepest={res['steepest_descent_lr']:.2e} "
              f"diverged_at={res['diverged_at_lr']}")

    if args.which in ("all", "init"):
        print("init diagnostics…", flush=True)
        schemes = ["normal_0.02", "normal_0.02_noscale", "xavier", "kaiming"]
        res = diagnose_init(VOCAB, schemes, train_tokens, seed=0)
        save_json({"results": res, "meta": meta}, OUT / "init.json")
        for s, v in res.items():
            print(f"  {s:22s} init_loss={v['init_loss']:.3f} logit_std={v['logit_std']:.3f} "
                  f"grad_norm={v['grad_norm_total']:.2f}")

    if args.which in ("all", "batch"):
        print("batch-size calibration…", flush=True)
        res = batch_size_calibration(
            VOCAB, train_tokens, val_tokens,
            effective_token_targets=[8192, 16384, 32768, 65536],
            total_tokens=2_000_000, device=device,
        )
        save_json({"results": res, "meta": meta}, OUT / "batch_size.json")
        for r in res:
            print(f"  eff_tokens={r['effective_tokens']:>6} steps={r['n_steps']:>4} "
                  f"final_val={r['final_val_loss']:.3f} wallclock={r['wallclock_sec']:.1f}s")


if __name__ == "__main__":
    main()
    import os
    import sys

    sys.stdout.flush()
    os._exit(0)  # datasets import lingers; all outputs already saved
