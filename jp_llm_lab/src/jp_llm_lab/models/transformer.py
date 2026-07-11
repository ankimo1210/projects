"""ClassicalGPT — a decoder-only Transformer in the GPT-2 style (spec §7.1).

Decoder-only ・ pre-LayerNorm ・ learned positional embedding ・ causal
multi-head self-attention ・ GELU MLP ・ residual stream ・ weight tying.

Forward pass (spec §8.1):
    input_ids [B,T] → tok_emb + pos_emb [B,T,D] → N × TransformerBlock
    → final LayerNorm → lm_head → logits [B,T,V] → (softmax → next-token dist)

`trace=` threads a dict through the REAL forward pass and fills it with every
intermediate tensor (spec §8.4) — there is no separate re-implementation that
could drift from the code that actually trains.
"""

from __future__ import annotations

import math

import torch
import torch.nn.functional as F
from torch import nn

from .blocks import TransformerBlock
from .config import ModelConfig, param_group_of


class ClassicalGPT(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.cfg = cfg
        self.tok_emb = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.pos_emb = nn.Embedding(cfg.context_len, cfg.d_model)
        self.drop = nn.Dropout(cfg.dropout)
        self.blocks = nn.ModuleList([TransformerBlock(cfg, i) for i in range(cfg.n_layers)])
        self.ln_f = nn.LayerNorm(cfg.d_model)
        self.lm_head = nn.Linear(cfg.d_model, cfg.vocab_size, bias=False)
        if cfg.tie_weights:
            # Weight tying: the output projection reuses the token embedding
            # matrix (same storage). Saves V·D params and couples input/output
            # token representations.
            self.lm_head.weight = self.tok_emb.weight

        self.apply(self._init_weights)
        if cfg.residual_scaled_init:
            # GPT-2: scale the two per-block projections that write INTO the
            # residual stream by 1/sqrt(2·n_layers), so the initial residual
            # variance stays O(1) regardless of depth (2 writes per block).
            scaled = cfg.init_std / math.sqrt(2 * cfg.n_layers)
            for name, p in self.named_parameters():
                if name.endswith("attn.proj.weight") or name.endswith("mlp.proj.weight"):
                    nn.init.normal_(p, mean=0.0, std=scaled)

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=self.cfg.init_std)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=self.cfg.init_std)

    # ------------------------------------------------------------------ core
    def forward(
        self,
        idx: torch.Tensor,
        targets: torch.Tensor | None = None,
        trace: dict | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        _B, T = idx.shape
        assert T <= self.cfg.context_len, f"sequence {T} > context_len {self.cfg.context_len}"
        pos = torch.arange(T, device=idx.device)

        tok = self.tok_emb(idx)  # [B,T,D]
        posv = self.pos_emb(pos)[None, :, :]  # [1,T,D] broadcast over batch
        x = self.drop(tok + posv)
        if trace is not None:
            trace["input_ids"] = idx.detach()
            trace["token_embeddings"] = tok.detach()
            trace["position_embeddings"] = posv.detach()
            trace["embeddings"] = x.detach()

        for block in self.blocks:
            x = block(x, trace=trace)

        x = self.ln_f(x)
        logits = self.lm_head(x)  # [B,T,V]
        if trace is not None:
            trace["final_norm"] = x.detach()
            trace["logits"] = logits.detach()
            trace["probabilities"] = F.softmax(logits.detach().float(), dim=-1)

        loss = None
        if targets is not None:
            # Cross-entropy over all B·T positions at once; ignore_index kept
            # for SFT loss-masking later (Milestone 5).
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)), targets.reshape(-1), ignore_index=-100
            )
        return logits, loss

    # ------------------------------------------------------------- analysis
    @torch.no_grad()
    def trace_forward(self, idx: torch.Tensor) -> dict[str, torch.Tensor]:
        """Run a forward pass and return every intermediate tensor (§8.4)."""
        was_training = self.training
        self.eval()
        trace: dict[str, torch.Tensor] = {}
        self.forward(idx, trace=trace)
        if was_training:
            self.train()
        return trace

    @torch.no_grad()
    def attention_maps(self, idx: torch.Tensor) -> list[torch.Tensor]:
        """Per-layer attention weights, each [B,H,T,T]."""
        trace = self.trace_forward(idx)
        return [trace[f"block{i}.attn.attn_weights"] for i in range(self.cfg.n_layers)]

    def param_breakdown(self) -> dict:
        """Parameter count per architectural group (§8.3).

        With weight tying, lm_head shares the token-embedding storage and
        contributes 0 additional parameters (flagged in `tied`).
        """
        groups: dict[str, int] = {}
        for name, p in self.named_parameters():  # dedups shared params
            groups[param_group_of(name)] = groups.get(param_group_of(name), 0) + p.numel()
        total = sum(p.numel() for p in self.parameters())
        return {"groups": groups, "total": total, "tied": self.cfg.tie_weights}

    def set_attn_impl(self, impl: str) -> None:
        self.cfg.attn_impl = impl
        for block in self.blocks:
            block.attn.set_attn_impl(impl)
