"""Tokenized snapshot caches: snapshot docs → one uint16 token array on disk.

Documents are joined with a single <EOS> token so the model sees document
boundaries (and generation has a meaningful EOS concept). Token counts per
snapshot are recorded in the snapshots manifest under "tokenized".
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from ..tokenization.base import EOS_ID
from ..utils.io import load_json, repo_root, save_json
from .snapshots import MANIFEST_REL, iter_snapshot_docs

TOKENIZED_REL = Path("data/tokenized")


def cache_path(snapshot: str, tokenizer_version: str, root: Path | None = None) -> Path:
    root = root or repo_root()
    return root / TOKENIZED_REL / f"{snapshot}_{tokenizer_version}.npy"


def tokenize_snapshot(
    snapshot: str,
    tokenizer,
    root: Path | None = None,
    batch_docs: int = 512,
    force: bool = False,
) -> Path:
    root = root or repo_root()
    out = cache_path(snapshot, tokenizer.version, root)
    if out.exists() and not force:
        return out
    assert tokenizer.vocab_size <= 65535, "uint16 cache requires vocab <= 65535"

    chunks: list[np.ndarray] = []
    batch: list[str] = []
    n_docs = n_chars = 0

    def flush() -> None:
        nonlocal batch
        if not batch:
            return
        if hasattr(tokenizer, "encode_batch"):
            encoded = tokenizer.encode_batch(batch)
        else:
            encoded = [tokenizer.encode(t) for t in batch]
        for ids in encoded:
            chunks.append(np.asarray([*ids, EOS_ID], dtype=np.uint16))
        batch = []

    for doc in iter_snapshot_docs(snapshot, root):
        batch.append(doc)
        n_docs += 1
        n_chars += len(doc)
        if len(batch) >= batch_docs:
            flush()
    flush()

    arr = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.uint16)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(out, arr)

    manifest = load_json(root / MANIFEST_REL)
    manifest.setdefault("tokenized", {})[f"{snapshot}_{tokenizer.version}"] = {
        "snapshot": snapshot,
        "tokenizer": tokenizer.version,
        "n_tokens": int(arr.size),
        "n_docs": n_docs,
        "n_chars": n_chars,
        "chars_per_token": round(n_chars / max(1, int(arr.size) - n_docs), 4),  # excl. EOS
        "file": out.name,
    }
    save_json(manifest, root / MANIFEST_REL)
    return out


def load_tokens(snapshot: str, tokenizer_version: str, root: Path | None = None) -> torch.Tensor:
    """Full token array as int64 CPU tensor (fits RAM comfortably: 100M → 800MB)."""
    arr = np.load(cache_path(snapshot, tokenizer_version, root))
    return torch.from_numpy(arr.astype(np.int64))
