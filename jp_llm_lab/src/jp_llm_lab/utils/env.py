"""Hardware / software environment diagnostics and training-setup recommendation.

Nothing in the lab hardcodes GPU assumptions: every script calls
`collect_env_report()` at startup and adapts via `recommend_setup()`.
"""

from __future__ import annotations

import importlib.util
import math
import platform
import sys
from dataclasses import asdict, dataclass, field

import psutil
import torch


@dataclass
class EnvReport:
    python_version: str
    torch_version: str
    cuda_version: str | None
    cuda_available: bool
    gpu_name: str | None
    vram_gb: float | None
    capability: str | None
    bf16_supported: bool
    sdpa_backends: list[str]
    compile_available: bool
    cpu_ram_gb: float
    cpu_count: int
    platform: str


def collect_env_report() -> EnvReport:
    cuda = torch.cuda.is_available()
    gpu_name = vram_gb = capability = None
    bf16 = False
    # "math" is the always-available reference SDPA backend; the fused ones are
    # reported as *enabled*, which does not guarantee every shape/dtype can use
    # them at runtime.
    backends = ["math"]
    if cuda:
        props = torch.cuda.get_device_properties(0)
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = round(props.total_memory / 2**30, 2)
        capability = f"{props.major}.{props.minor}"
        bf16 = torch.cuda.is_bf16_supported()
        for name, enabled in [
            ("flash", torch.backends.cuda.flash_sdp_enabled()),
            ("mem_efficient", torch.backends.cuda.mem_efficient_sdp_enabled()),
            ("cudnn", torch.backends.cuda.cudnn_sdp_enabled()),
        ]:
            if enabled:
                backends.append(name)
    compile_ok = hasattr(torch, "compile") and importlib.util.find_spec("triton") is not None
    return EnvReport(
        python_version=sys.version.split()[0],
        torch_version=torch.__version__,
        cuda_version=torch.version.cuda,
        cuda_available=cuda,
        gpu_name=gpu_name,
        vram_gb=vram_gb,
        capability=capability,
        bf16_supported=bf16,
        sdpa_backends=backends,
        compile_available=compile_ok,
        cpu_ram_gb=round(psutil.virtual_memory().total / 2**30, 1),
        cpu_count=psutil.cpu_count(logical=True) or 1,
        platform=platform.platform(),
    )


# Default context length per model size (spec §6).
CONTEXT_LEN = {"S": 256, "M": 512, "L": 512}


@dataclass
class RecommendedSetup:
    device: str
    dtype: str  # "bf16" | "fp32"
    attn_impl: str  # fast path; "explicit" stays available for teaching/analysis
    model_recommendation: str  # largest size that trains comfortably here
    micro_batch: dict[str, int]  # per model size S/M/L
    grad_accum: dict[str, int]  # to reach effective_tokens_target
    effective_tokens_target: int
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def recommend_setup(report: EnvReport, effective_tokens_target: int = 16384) -> RecommendedSetup:
    """Map the measured environment to a starting training configuration.

    Recommendation logic (a coarse prior, NOT a benchmark — Milestone 3's
    hardware calibration measures the real optimum):

    - dtype: bf16 whenever CUDA+BF16 exist (half memory, Ampere+ speedup,
      fp32-like exponent range so no loss scaling needed); else fp32.
    - attn_impl: SDPA as the fast path (fused kernels, no [B,H,T,T]
      materialization); the explicit implementation remains for teaching.
    - micro_batch: tiered by VRAM. Activation memory per sample grows roughly
      like n_layers·T·d_model (+ the T² attention term in explicit mode), so
      tiers are per model size; values leave ≳30% VRAM headroom.
    - grad_accum: ceil(target_tokens / (micro_batch · context_len)) — keeps the
      *effective* batch (tokens per optimizer step) comparable across machines.
    - model_recommendation: largest size trainable with that headroom.
    """
    notes = []
    if not report.cuda_available:
        device, dtype = "cpu", "fp32"
        micro = {"S": 8, "M": 2, "L": 1}
        rec = "S"
        notes.append("CPU-only: smoke tests fine; real training will be slow.")
    else:
        device = "cuda"
        dtype = "bf16" if report.bf16_supported else "fp32"
        if not report.bf16_supported:
            notes.append("GPU without BF16: using fp32 (consider fp16+GradScaler later).")
        vram = report.vram_gb or 0.0
        if vram < 6:
            micro, rec = {"S": 32, "M": 8, "L": 2}, "M"
        elif vram < 12:
            micro, rec = {"S": 64, "M": 16, "L": 8}, "L"
        else:
            micro, rec = {"S": 64, "M": 32, "L": 16}, "L"
    accum = {
        size: max(1, math.ceil(effective_tokens_target / (micro[size] * CONTEXT_LEN[size])))
        for size in micro
    }
    if report.compile_available:
        notes.append("torch.compile available — benchmark on/off in Milestone 3 (§14.1).")
    return RecommendedSetup(
        device=device,
        dtype=dtype,
        attn_impl="sdpa",
        model_recommendation=rec,
        micro_batch=micro,
        grad_accum=accum,
        effective_tokens_target=effective_tokens_target,
        notes=notes,
    )
