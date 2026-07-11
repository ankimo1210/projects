"""Model configuration for the classical GPT (Milestone 1).

Modern-GPT options (RMSNorm / RoPE / SwiGLU / bias-free) are introduced as an
ablation chain in Milestone 3; the config gains those switches then, one at a
time, so each architectural change stays a controlled experiment.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class ModelConfig:
    vocab_size: int
    d_model: int = 128
    n_heads: int = 4
    n_layers: int = 4
    context_len: int = 256
    dropout: float = 0.0
    attn_impl: str = "sdpa"  # "explicit" | "sdpa" — same params, switchable at runtime
    bias: bool = True
    tie_weights: bool = True
    init_std: float = 0.02
    residual_scaled_init: bool = True  # GPT-2 style: proj layers scaled by 1/sqrt(2·n_layers)

    def __post_init__(self) -> None:
        assert self.d_model % self.n_heads == 0, "d_model must be divisible by n_heads"
        assert self.attn_impl in ("explicit", "sdpa")

    @property
    def d_head(self) -> int:
        return self.d_model // self.n_heads

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ModelConfig:
        return cls(**d)


def param_group_of(name: str) -> str:
    """Map a parameter name to its architectural group.

    Shared by param_breakdown, gradient stats and update-ratio tracking so all
    diagnostics slice the model the same way.
    """
    if name.startswith("tok_emb"):
        return "token_emb"
    if name.startswith("pos_emb"):
        return "pos_emb"
    if ".attn.qkv" in name:
        return "attn_qkv"
    if ".attn.proj" in name:
        return "attn_proj"
    if ".mlp." in name:
        return "mlp"
    if ".ln1" in name or ".ln2" in name or name.startswith("ln_f"):
        return "norm"
    if name.startswith("lm_head"):
        return "lm_head"
    return "other"
