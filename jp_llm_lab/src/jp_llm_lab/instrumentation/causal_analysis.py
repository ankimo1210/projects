"""Causal attention analysis: head ablation & activation patching (spec §9).

These answer "does this head/position MATTER to the output?" — a causal
question that attention weights alone cannot answer. Both work by intervening
on the real forward pass and measuring the change in next-token loss/logits.
"""

from __future__ import annotations

import torch


@torch.no_grad()
def head_ablation_effect(model, idx: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
    """[L,H] increase in loss when each head is individually zeroed.

    We temporarily patch each block's attention output projection input by
    zeroing one head's contribution via a forward hook. Larger Δloss = the
    head carries more task-relevant information (a causal notion, unlike the
    descriptive weight statistics).
    """
    model.eval()
    _, base_loss = model(idx, targets)
    base_loss = float(base_loss)
    L = model.cfg.n_layers
    H = model.cfg.n_heads
    dh = model.cfg.d_head
    effects = torch.zeros(L, H)

    for layer in range(L):
        proj = model.blocks[layer].attn.proj
        for head in range(H):
            # The output projection reads heads as contiguous column blocks of
            # its weight (input dim = concat of per-head outputs). Zeroing one
            # head's block removes exactly that head's contribution to the
            # residual stream, leaving all others intact.
            cols = slice(head * dh, (head + 1) * dh)
            saved = proj.weight.data[:, cols].clone()
            proj.weight.data[:, cols] = 0.0
            _, loss = model(idx, targets)
            effects[layer, head] = float(loss) - base_loss
            proj.weight.data[:, cols] = saved
    return effects


@torch.no_grad()
def activation_patch_positions(model, idx_clean: torch.Tensor, idx_corrupt: torch.Tensor, layer: int) -> torch.Tensor:
    """[T] effect of patching each position's residual (after `layer`) from the
    clean run into the corrupt run, measured as recovery of the clean logits at
    the final position.

    Returns per-position L2 distance between patched-corrupt and clean final
    logits — small = patching that position recovered the clean behavior, i.e.
    that position carried the information.
    """
    model.eval()
    store = {}

    def capture(module, inp, out):
        store["h"] = out.detach().clone()

    h = model.blocks[layer].register_forward_hook(capture)
    model(idx_clean)
    clean_resid = store["h"]
    logits_clean, _ = model(idx_clean)
    h.remove()

    T = idx_clean.shape[1]
    out = torch.zeros(T)
    for pos in range(T):
        def patch(module, inp, output, pos=pos):
            output = output.clone()
            output[:, pos, :] = clean_resid[:, pos, :]
            return output

        hh = model.blocks[layer].register_forward_hook(patch)
        logits_patched, _ = model(idx_corrupt)
        hh.remove()
        out[pos] = float((logits_patched[:, -1] - logits_clean[:, -1]).norm())
    return out
