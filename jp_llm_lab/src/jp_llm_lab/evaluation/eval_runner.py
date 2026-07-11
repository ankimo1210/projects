"""Run the fixed evaluation set over a model (spec §19).

Separates ability types and reports per-category metrics:
- cloze accuracy: does the top-1 next token match the expected word's first token?
- completion fluency: repetition rate + distinct-2 of the generation
- factual/unknown: recorded verbatim for the HUMAN comparison table (not
  auto-scored as right/wrong — small models are expected to fail knowledge)

The point is to make the ability gap observable, not to produce a single score.
"""

from __future__ import annotations

import torch

from ..generation.diversity import distinct_n, repetition_rate
from ..generation.sampler import SamplingConfig, generate
from .eval_prompts import build_eval_set


@torch.no_grad()
def run_eval(model, tokenizer, device: str, max_new_tokens: int = 40) -> dict:
    model.eval().to(device)
    prompts = build_eval_set()
    per_prompt = []
    for p in prompts:
        ids = torch.tensor([tokenizer.encode(p["prompt"])], device=device)
        row = {"id": p["id"], "category": p["category"], "kind": p["kind"], "prompt": p["prompt"]}
        if p["kind"] == "cloze" and p["expected"]:
            logits, _ = model(ids)
            top1 = int(logits[0, -1].argmax())
            exp_ids = tokenizer.encode(p["expected"])
            row["expected"] = p["expected"]
            row["top1_token"] = tokenizer.id_to_token(top1)
            row["cloze_correct"] = bool(exp_ids and top1 == exp_ids[0])
        else:
            out, _ = generate(model, ids, SamplingConfig(max_new_tokens=max_new_tokens, temperature=0.7, seed=0))
            gen = out[0, ids.shape[1] :].tolist()
            row["generation"] = tokenizer.decode(gen)
            row["repetition_rate"] = round(repetition_rate(gen), 4)
            row["distinct_2"] = round(distinct_n(gen, 2), 4)
            if p["expected"]:
                row["expected"] = p["expected"]
                row["contains_expected"] = p["expected"] in row["generation"]
        per_prompt.append(row)

    # aggregate by category
    cats: dict[str, dict] = {}
    for r in per_prompt:
        c = cats.setdefault(r["category"], {"n": 0, "cloze_correct": 0, "cloze_n": 0,
                                            "rep_sum": 0.0, "d2_sum": 0.0, "gen_n": 0})
        c["n"] += 1
        if "cloze_correct" in r:
            c["cloze_n"] += 1
            c["cloze_correct"] += int(r["cloze_correct"])
        if "repetition_rate" in r:
            c["gen_n"] += 1
            c["rep_sum"] += r["repetition_rate"]
            c["d2_sum"] += r["distinct_2"]
    summary = {}
    for c, v in cats.items():
        summary[c] = {
            "n": v["n"],
            "cloze_accuracy": round(v["cloze_correct"] / v["cloze_n"], 3) if v["cloze_n"] else None,
            "mean_repetition": round(v["rep_sum"] / v["gen_n"], 4) if v["gen_n"] else None,
            "mean_distinct2": round(v["d2_sum"] / v["gen_n"], 4) if v["gen_n"] else None,
        }
    total_cloze = [r for r in per_prompt if "cloze_correct" in r]
    overall = {
        "n_prompts": len(per_prompt),
        "cloze_accuracy": round(sum(r["cloze_correct"] for r in total_cloze) / len(total_cloze), 3) if total_cloze else None,
    }
    return {"overall": overall, "by_category": summary, "per_prompt": per_prompt}
