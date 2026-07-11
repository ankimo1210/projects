"""Token-embedding representation analysis (spec §10).

Caveats surfaced wherever these are plotted:
- 2-D projections (PCA) discard information; cluster shapes depend on method.
- cosine "nearest neighbors" in a 128-D space can be misleading for rare tokens
  whose embeddings barely moved from init.
"""

from __future__ import annotations

import numpy as np
import torch


def embedding_matrix(model) -> torch.Tensor:
    return model.tok_emb.weight.detach().float()


def token_norms(model) -> torch.Tensor:
    return embedding_matrix(model).norm(dim=1)


def nearest_neighbors(model, token_id: int, k: int = 10) -> list[tuple[int, float]]:
    E = embedding_matrix(model)
    E = E / E.norm(dim=1, keepdim=True).clamp(min=1e-12)
    sims = E @ E[token_id]
    top = torch.topk(sims, k + 1)
    return [(int(i), float(s)) for i, s in zip(top.indices, top.values, strict=True) if int(i) != token_id][:k]


def pca_2d(model, ids: list[int] | None = None) -> np.ndarray:
    E = embedding_matrix(model)
    if ids is not None:
        E = E[ids]
    X = (E - E.mean(0)).numpy()
    U, S, _Vt = np.linalg.svd(X, full_matrices=False)
    return (U[:, :2] * S[:2])


def drift(model_a, model_b) -> torch.Tensor:
    """Per-token L2 distance between two checkpoints' embeddings."""
    return (embedding_matrix(model_a) - embedding_matrix(model_b)).norm(dim=1)
