"""Memorization analysis (spec §20).

Distinguishes "the model reproduces training text" from "the model
generalizes". Methods:

- train vs validation loss gap (aggregate memorization signal)
- exact-match continuation: prompt with a training-doc prefix, greedy-decode,
  measure how many tokens match the true continuation vs the same for a
  validation doc (held-out control)
- longest common substring (token level) between generation and reference

Low validation loss alone does NOT prove generalization; a large train/val
gap with high train-prefix exact-match is the memorization signature.
"""

from __future__ import annotations

import torch

from ..generation.sampler import SamplingConfig, generate


def exact_match_length(pred: list[int], truth: list[int]) -> int:
    """How many leading tokens of pred match truth."""
    n = 0
    for a, b in zip(pred, truth, strict=False):
        if a != b:
            break
        n += 1
    return n


def longest_common_substring(a: list[int], b: list[int]) -> int:
    """Token-level LCS (contiguous). O(len(a)·len(b)) — keep inputs short."""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                best = max(best, cur[j])
        prev = cur
    return best


@torch.no_grad()
def continuation_probe(
    model, doc_ids: list[int], prefix_len: int, continue_len: int, device: str
) -> dict:
    """Greedy-continue a prefix and compare to the true continuation."""
    prefix = doc_ids[:prefix_len]
    truth = doc_ids[prefix_len : prefix_len + continue_len]
    idx = torch.tensor([prefix], device=device)
    out, _ = generate(model, idx, SamplingConfig(max_new_tokens=continue_len, greedy=True))
    pred = out[0, prefix_len:].tolist()
    return {
        "exact_match_len": exact_match_length(pred, truth),
        "lcs": longest_common_substring(pred, truth),
        "continue_len": len(truth),
    }


def memorization_report(
    model,
    train_docs: list[list[int]],
    val_docs: list[list[int]],
    prefix_len: int,
    continue_len: int,
    device: str,
) -> dict:
    """Compare train-doc vs val-doc reproducibility (val = held-out control)."""

    def batch(docs):
        probes = [
            continuation_probe(model, d, prefix_len, continue_len, device)
            for d in docs
            if len(d) >= prefix_len + continue_len
        ]
        if not probes:
            return {}
        return {
            "n": len(probes),
            "mean_exact_match": sum(p["exact_match_len"] for p in probes) / len(probes),
            "mean_lcs": sum(p["lcs"] for p in probes) / len(probes),
            "max_exact_match": max(p["exact_match_len"] for p in probes),
        }

    return {
        "train": batch(train_docs),
        "validation": batch(val_docs),
        "prefix_len": prefix_len,
        "continue_len": continue_len,
        "note": "train >> validation on exact-match ⇒ memorization; similar ⇒ generalization",
    }
