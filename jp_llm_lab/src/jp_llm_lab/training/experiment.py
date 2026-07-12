"""Config-driven experiment runner shared by Milestones 2-4.

Resolves a YAML experiment spec into (model, train_tokens, val_tokens,
tokenizer) and runs the instrumented trainer. Supports:

- data.source: "snapshot" (tokenized cache) | "sample" (char-tokenized text)
- model.preset: "classical" | "modern" plus explicit overrides (for ablations)
- validation from a SEPARATE snapshot (real generalization, unlike M1's
  contiguous tail split)
"""

from __future__ import annotations

from pathlib import Path

import torch

from ..data.batches import split_tokens
from ..data.tokenized_cache import load_tokens
from ..models.config import ModelConfig
from ..models.transformer import ClassicalGPT
from ..tokenization.hf_bpe import HFBpeTokenizer
from ..training.train_config import TrainConfig
from ..training.trainer import RunResult, train_lm
from ..utils.io import repo_root


def build_model(vocab_size: int, model_spec: dict) -> ClassicalGPT:
    spec = dict(model_spec)
    preset = spec.pop("preset", "classical")
    if preset == "modern":
        cfg = ModelConfig.modern(vocab_size=vocab_size, **spec)
    else:
        cfg = ModelConfig(vocab_size=vocab_size, **spec)
    return ClassicalGPT(cfg)


def load_experiment_data(data_spec: dict) -> tuple[torch.Tensor, torch.Tensor, object]:
    """Return (train_tokens, val_tokens, tokenizer)."""
    root = repo_root()
    if data_spec["source"] == "snapshot":
        tok_version = data_spec["tokenizer_version"]
        tokenizer = HFBpeTokenizer.load(root / "tokenizer" / f"{tok_version}.tokenizer.json", version=tok_version)
        train_tokens = load_tokens(data_spec["train_snapshot"], tok_version)
        if "max_train_tokens" in data_spec:
            train_tokens = train_tokens[: data_spec["max_train_tokens"]]
        if "val_snapshot" in data_spec:
            val_tokens = load_tokens(data_spec["val_snapshot"], tok_version)
            if "max_val_tokens" in data_spec:
                val_tokens = val_tokens[: data_spec["max_val_tokens"]]
        else:
            train_tokens, val_tokens = split_tokens(train_tokens, data_spec.get("val_frac", 0.05))
        return train_tokens, val_tokens, tokenizer
    raise ValueError(f"unknown data source: {data_spec['source']}")


def run_experiment(spec: dict, run_dir: Path | str, device: str | None = None) -> RunResult:
    train_tokens, val_tokens, tokenizer = load_experiment_data(spec["data"])
    model = build_model(tokenizer.vocab_size, spec["model"])
    train_cfg = TrainConfig.from_dict(spec["train"])
    run_dir = Path(run_dir)
    # persist the production tokenizer next to the run for analysis
    tokenizer.save(run_dir / f"{tokenizer.version}.tokenizer.json")
    return train_lm(
        model,
        train_tokens,
        val_tokens,
        train_cfg,
        run_dir,
        tokenizer=tokenizer,
        device=device,
        extra_meta={"experiment": spec.get("run_name"), "data": spec["data"]},
    )
