"""Probability calibration for next-token prediction (spec §15).

"Calibration" here = are the model's confidences trustworthy? If the model
says 0.7 for a set of predictions, are ~70% of them correct? We collect
(confidence, correct) pairs over a token set and compute:

- NLL, perplexity, Brier score
- Top-1 ECE (equal-width and equal-mass bins), Adaptive ECE
- reliability diagram data (confidence vs empirical accuracy per bin)
- Temperature Scaling: fit a single T on the CALIBRATION split (never test)
  to minimize NLL; report its effect on ECE/NLL/accuracy.

Key facts stated wherever shown: temperature scaling does NOT change the
argmax (so top-1 accuracy is unchanged), only the sharpness. Next-token
calibration is NOT the same as factual correctness / hallucination rate.
"""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F


@torch.no_grad()
def collect_logits(model, tokens: torch.Tensor, n_batches: int, batch_size: int,
                   context_len: int, device: str, seed: int = 999) -> dict:
    """Gather (top-1 confidence, correct, true-token NLL) over sampled batches,
    plus a subsample of full logit rows for temperature fitting."""
    from ..data.batches import sample_batch
    from ..utils.seed import make_generator

    model.eval().to(device)
    gen = make_generator(seed)
    conf, correct, nll, ent = [], [], [], []
    logit_rows, target_rows = [], []
    for b in range(n_batches):
        x, y = sample_batch(tokens, batch_size, context_len, gen, device)
        logits, _ = model(x)
        lf = logits.float().reshape(-1, logits.size(-1))
        tgt = y.reshape(-1)
        probs = F.softmax(lf, dim=-1)
        top_p, top_i = probs.max(dim=-1)
        conf.append(top_p.cpu())
        correct.append((top_i == tgt).cpu())
        nll.append(F.cross_entropy(lf, tgt, reduction="none").cpu())
        ent.append((-(probs * probs.clamp(min=1e-12).log()).sum(-1)).cpu())
        if b < 4:  # keep a subsample of rows for temperature fitting
            logit_rows.append(lf.cpu())
            target_rows.append(tgt.cpu())
    return {
        "conf": torch.cat(conf),
        "correct": torch.cat(correct),
        "nll": torch.cat(nll),
        "entropy": torch.cat(ent),
        "logits": torch.cat(logit_rows),
        "targets": torch.cat(target_rows),
    }


def _bin_stats(conf: torch.Tensor, correct: torch.Tensor, edges: torch.Tensor) -> list[dict]:
    bins = []
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        mask = (conf > lo) & (conf <= hi)
        n = int(mask.sum())
        if n == 0:
            bins.append({"lo": float(lo), "hi": float(hi), "n": 0, "avg_conf": None, "acc": None})
            continue
        bins.append(
            {
                "lo": float(lo), "hi": float(hi), "n": n,
                "avg_conf": float(conf[mask].mean()),
                "acc": float(correct[mask].float().mean()),
            }
        )
    return bins


def ece_equal_width(conf: torch.Tensor, correct: torch.Tensor, n_bins: int = 15) -> tuple[float, list]:
    edges = torch.linspace(0, 1, n_bins + 1)
    bins = _bin_stats(conf, correct, edges)
    total = len(conf)
    ece = sum(b["n"] / total * abs(b["avg_conf"] - b["acc"]) for b in bins if b["n"] > 0)
    return ece, bins


def ece_equal_mass(conf: torch.Tensor, correct: torch.Tensor, n_bins: int = 15) -> tuple[float, list]:
    order = torch.argsort(conf)
    conf_s, corr_s = conf[order], correct[order]
    total = len(conf)
    ece, bins = 0.0, []
    for i in range(n_bins):
        lo_i = i * total // n_bins
        hi_i = (i + 1) * total // n_bins
        if hi_i <= lo_i:
            continue
        c = conf_s[lo_i:hi_i]
        a = corr_s[lo_i:hi_i].float()
        gap = abs(float(c.mean()) - float(a.mean()))
        ece += (hi_i - lo_i) / total * gap
        bins.append({"n": hi_i - lo_i, "avg_conf": float(c.mean()), "acc": float(a.mean())})
    return ece, bins


def brier_top1(conf: torch.Tensor, correct: torch.Tensor) -> float:
    return float(((conf - correct.float()) ** 2).mean())


def fit_temperature(logits: torch.Tensor, targets: torch.Tensor, max_iter: int = 100) -> float:
    """Optimize a single scalar T>0 minimizing NLL of softmax(logits/T)."""
    log_t = torch.zeros(1, requires_grad=True)  # T = exp(log_t), keeps T>0
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=max_iter)

    def closure():
        opt.zero_grad()
        loss = F.cross_entropy(logits / log_t.exp(), targets)
        loss.backward()
        return loss

    opt.step(closure)
    return float(log_t.exp().detach())


def metrics_at_temperature(logits: torch.Tensor, targets: torch.Tensor, T: float) -> dict:
    probs = F.softmax(logits / T, dim=-1)
    top_p, top_i = probs.max(dim=-1)
    correct = (top_i == targets)
    nll = float(F.cross_entropy(logits / T, targets))
    ece, _ = ece_equal_mass(top_p, correct)
    ent = float((-(probs * probs.clamp(min=1e-12).log()).sum(-1)).mean())
    return {
        "T": T, "nll": nll, "ppl": math.exp(nll),
        "ece_equal_mass": ece, "accuracy": float(correct.float().mean()), "entropy": ent,
        "brier": brier_top1(top_p, correct),
    }
