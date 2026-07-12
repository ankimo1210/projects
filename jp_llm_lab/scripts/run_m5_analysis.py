"""Milestone-5 analysis on the main pretrained model (spec §15, §16, §20, §21).

Produces:
- experiments/analysis_m5/calibration.json  (reliability, ECE, temp scaling)
- experiments/analysis_m5/generation_anatomy.json (per-step + sampling sweep)
- experiments/analysis_m5/memorization.json
- SFT runs (assistant-only vs full) → experiments/runs/m5_sft_*/ + comparison

Temperature is fit on the CALIBRATION split and evaluated on the TEST split —
never the same data (spec §4.1).

Usage: uv run --no-sync python jp_llm_lab/scripts/run_m5_analysis.py
"""

from __future__ import annotations

import argparse
import copy

import torch
from jp_llm_lab.calibration.probability import (
    brier_top1,
    collect_logits,
    ece_equal_mass,
    ece_equal_width,
    fit_temperature,
    metrics_at_temperature,
)
from jp_llm_lab.data.sft_data import build_sft_dataset, load_sft_examples
from jp_llm_lab.data.tokenized_cache import load_tokens
from jp_llm_lab.evaluation.memorization import memorization_report
from jp_llm_lab.generation.diversity import aggregate_metrics
from jp_llm_lab.generation.sampler import SamplingConfig, generate
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.tokenization.base import EOS_ID
from jp_llm_lab.tokenization.hf_bpe import HFBpeTokenizer
from jp_llm_lab.training.sft import run_sft
from jp_llm_lab.training.trainer import load_checkpoint
from jp_llm_lab.utils.io import repo_root, save_json

RUN = "m4_model_l_modern_seed42"
OUT_REL = "experiments/analysis_m5"
PROMPTS = ["日本の首都は", "科学とは、", "むかしむかし、あるところに", "人工知能の研究は"]


def load_final_model(root, device):
    run_dir = root / "experiments" / "runs" / RUN
    ckpt = sorted(run_dir.glob("checkpoints/*100pct*.pt"))[0]
    payload = torch.load(ckpt, map_location="cpu", weights_only=False)
    model = ClassicalGPT(ModelConfig.from_dict(payload["model_cfg"]))
    load_checkpoint(ckpt, model)
    tok = HFBpeTokenizer.load(next(run_dir.glob("*.tokenizer.json")))
    return model.eval().to(device), tok, run_dir


def do_calibration(model, tok, device, out):
    calib = load_tokens("calibration", "bpe8k_v1")
    test = load_tokens("test", "bpe8k_v1")
    cal = collect_logits(model, calib, 12, 24, 512, device, seed=111)
    tst = collect_logits(model, test, 12, 24, 512, device, seed=222)

    T = fit_temperature(cal["logits"], cal["targets"])  # fit on CALIBRATION only
    raw = metrics_at_temperature(tst["logits"], tst["targets"], 1.0)
    scaled = metrics_at_temperature(tst["logits"], tst["targets"], T)  # eval on TEST

    ece_w, bins_w = ece_equal_width(tst["conf"], tst["correct"], 15)
    ece_m, bins_m = ece_equal_mass(tst["conf"], tst["correct"], 15)
    result = {
        "fitted_T": T,
        "fit_split": "calibration",
        "eval_split": "test",
        "raw": {**raw, "ece_equal_width": ece_w, "brier": brier_top1(tst["conf"], tst["correct"])},
        "temperature_scaled": scaled,
        "reliability_equal_width": bins_w,
        "reliability_equal_mass": bins_m,
        "test_top1_conf_mean": float(tst["conf"].mean()),
        "test_accuracy": float(tst["correct"].float().mean()),
        "note": "Temperature scaling changes sharpness, not argmax → accuracy identical. "
        "Next-token calibration is NOT factual correctness.",
    }
    save_json(result, out / "calibration.json")
    return result


def do_generation_anatomy(model, tok, device, out):
    prompt = "日本の首都は"
    ids = torch.tensor([tok.encode(prompt)], device=device)
    # per-step anatomy under greedy
    _, steps = generate(model, ids, SamplingConfig(max_new_tokens=30, greedy=True), record_steps=True)
    step_rows = [
        {
            "index": s.index,
            "chosen": tok.id_to_token(s.chosen_id),
            "chosen_prob": round(s.chosen_prob, 4),
            "entropy": round(s.entropy, 3),
            "top5": [(tok.id_to_token(i), round(p, 4)) for i, p in zip(s.top_ids[:5], s.top_probs[:5])],
        }
        for s in steps
    ]
    # sampling-method sweep on the SAME prompts
    methods = {
        "greedy": SamplingConfig(max_new_tokens=80, greedy=True),
        "temp0.2": SamplingConfig(max_new_tokens=80, temperature=0.2, seed=0),
        "temp0.7": SamplingConfig(max_new_tokens=80, temperature=0.7, seed=0),
        "temp1.0": SamplingConfig(max_new_tokens=80, temperature=1.0, seed=0),
        "temp1.5": SamplingConfig(max_new_tokens=80, temperature=1.5, seed=0),
        "top_k40": SamplingConfig(max_new_tokens=80, temperature=1.0, top_k=40, seed=0),
        "top_p0.9": SamplingConfig(max_new_tokens=80, temperature=1.0, top_p=0.9, seed=0),
    }
    sweep = {}
    for name, cfg in methods.items():
        seqs, texts = [], []
        for p in PROMPTS:
            pid = torch.tensor([tok.encode(p)], device=device)
            out_ids, _ = generate(model, pid, cfg)
            gen_ids = out_ids[0, pid.shape[1] :].tolist()
            seqs.append(gen_ids)
            texts.append(tok.decode(gen_ids))
        sweep[name] = {"metrics": aggregate_metrics(seqs, eos_id=EOS_ID), "sample": texts[0][:120]}
    save_json({"prompt": prompt, "steps": step_rows, "sampling_sweep": sweep}, out / "generation_anatomy.json")
    return sweep


def do_memorization(model, tok, device, out):
    train = load_tokens("main", "bpe8k_v1")
    val = load_tokens("validation", "bpe8k_v1")

    # slice a handful of "documents" (EOS-delimited) from each
    def docs_from(tokens, k=40, doc_len=120):
        arr = tokens.tolist()
        eos_positions = [i for i, t in enumerate(arr[:200000]) if t == EOS_ID][: k + 1]
        out_docs = []
        for a, b in zip(eos_positions, eos_positions[1:], strict=False):
            seg = arr[a + 1 : b]
            if len(seg) >= doc_len:
                out_docs.append(seg[:doc_len])
        return out_docs[:k]

    report = memorization_report(
        model, docs_from(train), docs_from(val), prefix_len=40, continue_len=60, device=device
    )
    save_json(report, out / "memorization.json")
    return report


def do_sft(model, tok, device, root, out):
    build_sft_dataset(n=1200)
    examples = load_sft_examples()
    base = copy.deepcopy(model)
    results = {}
    for regime, ao in [("assistant_only", True), ("full_sequence", False)]:
        m = copy.deepcopy(base)
        res = run_sft(m, examples, tok, assistant_only=ao, steps=400, batch_size=16,
                      context_len=256, lr=2e-4, device=device, seed=0)
        # sample responses to fixed instructions
        samples = []
        for instr in ["日本の首都はどこですか？", "犬について一文で説明してください。", "2たす3はいくつですか？"]:
            from jp_llm_lab.tokenization.base import ASSISTANT_ID, BOS_ID, USER_ID

            prompt = [BOS_ID, USER_ID, *tok.encode(instr), ASSISTANT_ID]
            pid = torch.tensor([prompt], device=device)
            out_ids, _ = generate(m, pid, SamplingConfig(max_new_tokens=60, temperature=0.7, seed=1, stop_id=EOS_ID))
            samples.append({"instruction": instr, "response": tok.decode(out_ids[0, len(prompt):].tolist(), skip_special=True)})
        results[regime] = {"final_loss": res.final_loss, "curve": res.curve, "samples": samples}
        m.cpu()

    # base (pretrained, no SFT) completions for the same instructions, for contrast
    base_samples = []
    for instr in ["日本の首都はどこですか？", "犬について一文で説明してください。", "2たす3はいくつですか？"]:
        pid = torch.tensor([tok.encode(instr)], device=device)
        out_ids, _ = generate(base.to(device), pid, SamplingConfig(max_new_tokens=60, temperature=0.7, seed=1))
        base_samples.append({"instruction": instr, "completion": tok.decode(out_ids[0, pid.shape[1]:].tolist())})
    save_json({"regimes": results, "base_pretrained_samples": base_samples,
               "sft_examples": len(examples)}, out / "sft.json")
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip", nargs="*", default=[])
    args = ap.parse_args()
    root = repo_root()
    out = root / OUT_REL
    out.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, tok, run_dir = load_final_model(root, device)
    print(f"loaded {RUN}, vocab {tok.vocab_size}, device {device}")

    if "calibration" not in args.skip:
        r = do_calibration(model, tok, device, out)
        print(f"calibration: T={r['fitted_T']:.3f} rawECE={r['raw']['ece_equal_width']:.4f} "
              f"scaledNLL={r['temperature_scaled']['nll']:.3f} (rawNLL={r['raw']['nll']:.3f})")
    if "generation" not in args.skip:
        sweep = do_generation_anatomy(model, tok, device, out)
        for name, d in sweep.items():
            print(f"  {name:9s} rep={d['metrics']['repetition_rate']:.3f} distinct2={d['metrics']['distinct_2']:.3f}")
    if "memorization" not in args.skip:
        r = do_memorization(model, tok, device, out)
        print(f"memorization train_exact={r['train'].get('mean_exact_match'):.1f} "
              f"val_exact={r['validation'].get('mean_exact_match'):.1f}")
    if "sft" not in args.skip:
        r = do_sft(model, tok, device, root, out)
        for regime, d in r.items():
            print(f"  SFT {regime}: final_loss {d['final_loss']:.3f}")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
    import os
    import sys

    sys.stdout.flush()
    os._exit(0)
