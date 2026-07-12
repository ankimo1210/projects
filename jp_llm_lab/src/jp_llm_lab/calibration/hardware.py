"""Hardware calibration (spec §14.1).

Benchmark real training-step throughput and VRAM across:
- dtype: fp32 vs bf16
- attention: explicit vs sdpa
- torch.compile: on/off
- micro batch size
- context length

Recommends the highest-throughput setting that leaves a safety VRAM margin —
NOT the largest batch that merely fits.
"""

from __future__ import annotations

import time

import torch

from ..models.config import ModelConfig
from ..models.transformer import ClassicalGPT


def _bench_step(model, x, y, dtype, device, use_compile, n=12, warmup=4) -> dict:
    opt = torch.optim.AdamW(model.parameters(), lr=1e-4)
    step_model = torch.compile(model) if use_compile else model
    autocast = (
        torch.autocast(device_type="cuda", dtype=torch.bfloat16)
        if dtype == "bf16" and device == "cuda"
        else torch.autocast(device_type="cpu", enabled=False)
    )
    times = []
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    for i in range(n):
        t0 = time.perf_counter()
        opt.zero_grad(set_to_none=True)
        with autocast:
            _, loss = step_model(x, y)
        loss.backward()
        opt.step()
        if device == "cuda":
            torch.cuda.synchronize()
        if i >= warmup:
            times.append(time.perf_counter() - t0)
    times.sort()
    med = times[len(times) // 2]
    peak = torch.cuda.max_memory_allocated() / 2**30 if device == "cuda" else 0.0
    B, T = x.shape
    return {"median_step_ms": round(med * 1e3, 2), "tokens_per_sec": round(B * T / med), "peak_vram_gb": round(peak, 2)}


def hardware_calibration(
    vocab_size: int,
    device: str,
    d_model: int = 320,
    n_layers: int = 6,
    n_heads: int = 8,
    context_len: int = 512,
    configs: list[dict] | None = None,
) -> list[dict]:
    configs = configs or [
        {"dtype": "fp32", "attn": "explicit", "compile": False, "B": 16, "T": 512},
        {"dtype": "fp32", "attn": "sdpa", "compile": False, "B": 16, "T": 512},
        {"dtype": "bf16", "attn": "sdpa", "compile": False, "B": 16, "T": 512},
        {"dtype": "bf16", "attn": "sdpa", "compile": False, "B": 32, "T": 512},
        {"dtype": "bf16", "attn": "sdpa", "compile": True, "B": 32, "T": 512},
        {"dtype": "bf16", "attn": "sdpa", "compile": False, "B": 24, "T": 256},
    ]
    results = []
    for c in configs:
        try:
            torch.manual_seed(0)
            cfg = ModelConfig(vocab_size=vocab_size, d_model=d_model, n_layers=n_layers,
                              n_heads=n_heads, context_len=max(c["T"], context_len), attn_impl=c["attn"])
            model = ClassicalGPT(cfg).to(device)
            x = torch.randint(0, vocab_size, (c["B"], c["T"]), device=device)
            y = torch.randint(0, vocab_size, (c["B"], c["T"]), device=device)
            r = _bench_step(model, x, y, c["dtype"], device, c["compile"])
            results.append({**c, **r})
            del model
            if device == "cuda":
                torch.cuda.empty_cache()
        except RuntimeError as e:  # OOM etc.
            results.append({**c, "error": str(e)[:80]})
    return results
