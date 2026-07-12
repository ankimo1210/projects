"""Micro-benchmark: explicit attention vs SDPA (forward+backward).

Same module, same parameters — only the code path differs. Saves medians to
reports/figures/attn_bench.json for the notebook and HTML report.

Usage: uv run --no-sync python jp_llm_lab/scripts/bench_attention.py
"""

from __future__ import annotations

import statistics
import time

import torch
from jp_llm_lab.models.attention import CausalSelfAttention
from jp_llm_lab.utils.io import repo_root, save_json
from jp_llm_lab.utils.runmeta import collect_run_metadata


def bench_once(attn, x) -> float:
    t0 = time.perf_counter()
    y = attn(x)
    y.square().mean().backward()
    if x.is_cuda:
        torch.cuda.synchronize()
    return time.perf_counter() - t0


def main() -> None:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    results = []
    dtypes = [torch.float32] + ([torch.bfloat16] if device == "cuda" else [])
    for dtype in dtypes:
        for T in (128, 256, 512):
            for impl in ("explicit", "sdpa"):
                torch.manual_seed(0)
                attn = CausalSelfAttention(128, 4, T, attn_impl=impl).to(device=device, dtype=dtype)
                B = 32
                times = []
                for i in range(25):
                    x = torch.randn(B, T, 128, device=device, dtype=dtype, requires_grad=True)
                    dt = bench_once(attn, x)
                    if i >= 5:  # warmup discarded
                        times.append(dt)
                    attn.zero_grad(set_to_none=True)
                med = statistics.median(times)
                results.append(
                    {
                        "impl": impl,
                        "dtype": str(dtype).replace("torch.", ""),
                        "T": T,
                        "B": B,
                        "d_model": 128,
                        "median_ms": round(med * 1e3, 3),
                        "tokens_per_sec": round(B * T / med),
                        "device": device,
                    }
                )
                print(results[-1])
    out = repo_root() / "reports" / "figures" / "attn_bench.json"
    save_json({"results": results, "meta": collect_run_metadata()}, out)
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
