"""Parameter and FLOPs accounting (spec §8.3 / NB08).

Conventions: 1 multiply-accumulate = 2 FLOPs. Forward cost per token is
context-dependent through the attention T-terms; we report both the exact
per-token forward at context T and the common 6·N·tokens training
approximation (N = parameters), and show where they diverge.
Backward ≈ 2× forward, so training ≈ 3× forward FLOPs.
"""

from __future__ import annotations

from .config import ModelConfig


def flops_per_token(cfg: ModelConfig, T: int | None = None) -> dict:
    """Exact-ish forward FLOPs for ONE token with T tokens of context."""
    T = T or cfg.context_len
    d, L, V = cfg.d_model, cfg.n_layers, cfg.vocab_size
    qkv = 2 * d * 3 * d
    attn_scores = 2 * T * d  # q·k over T keys (all heads together: T·d MACs)
    attn_av = 2 * T * d  # weights @ V
    attn_proj = 2 * d * d
    if cfg.mlp == "gelu":
        mlp = 2 * (d * 4 * d) * 2
    else:  # swiglu: three matrices with hidden ≈ 8d/3 → same total as gelu by design
        hidden = 32 * round(8 * d / 3 / 32)
        mlp = 2 * (2 * d * hidden + hidden * d)
    per_layer = qkv + attn_scores + attn_av + attn_proj + mlp
    lm_head = 2 * d * V
    fwd = L * per_layer + lm_head
    return {
        "per_layer": {
            "qkv": qkv,
            "attn_scores(T)": attn_scores,
            "attn_av(T)": attn_av,
            "attn_proj": attn_proj,
            "mlp": mlp,
        },
        "lm_head": lm_head,
        "forward_per_token": fwd,
        "train_per_token": 3 * fwd,
        "context_T": T,
    }


def training_flops(cfg: ModelConfig, n_tokens: int, n_params: int | None = None) -> dict:
    exact = flops_per_token(cfg)["train_per_token"] * n_tokens
    approx = 6 * (n_params or 0) * n_tokens if n_params else None
    return {"exact_estimate": exact, "six_ND_approx": approx, "n_tokens": n_tokens}
