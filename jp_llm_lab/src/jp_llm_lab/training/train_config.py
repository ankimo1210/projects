"""Training configuration (YAML-serializable dataclass)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml


@dataclass
class TrainConfig:
    seed: int = 42
    steps: int = 200
    batch_size: int = 32
    grad_accum: int = 1
    context_len: int = 256
    lr: float = 3e-3
    warmup_frac: float = 0.05
    min_lr_frac: float = 0.1  # cosine decays to lr·min_lr_frac
    weight_decay: float = 0.1
    beta1: float = 0.9
    beta2: float = 0.95
    grad_clip: float = 1.0
    dtype: str = "bf16"  # "bf16" | "fp32" (bf16 only used when CUDA supports it)
    log_interval: int = 5
    eval_interval: int = 25
    eval_batches: int = 8
    eval_seed: int = 1234  # fixed eval batches across the whole run
    ratio_interval: int = 10  # update-to-weight ratio measured every N steps
    checkpoint_fracs: tuple[float, ...] = (0.0, 0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 1.0)
    fixed_prompts: list[str] = field(default_factory=list)
    max_new_tokens: int = 120

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> TrainConfig:
        d = dict(d)
        if "checkpoint_fracs" in d:
            d["checkpoint_fracs"] = tuple(d["checkpoint_fracs"])
        return cls(**d)


def load_yaml_config(path: Path | str) -> dict:
    """Load a full experiment YAML (run_name / data / tokenizer / model / train)."""
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
