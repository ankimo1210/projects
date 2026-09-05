"""Explicit numerical and data-quality policy; rates are annual decimals."""
from dataclasses import asdict, dataclass
import math


@dataclass(frozen=True)
class Config:
    seed: int = 20260115
    stale_days: float = 3.0
    rate_sigma_floor: float = 0.00001
    price_sigma_floor: float = 0.0125
    huber_threshold: float = 2.5
    smoothing: float = 0.0001
    smoothing_candidates: tuple = (0.00001, 0.0001, 0.001, 0.01)
    max_irls: int = 100
    irls_tolerance: float = 0.0002
    grid_rows: int = 721
    removal_trials: int = 8

    def __post_init__(self):
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        for name in ("rate_sigma_floor", "price_sigma_floor", "huber_threshold", "irls_tolerance"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if not math.isfinite(self.stale_days) or self.stale_days < 0:
            raise ValueError("stale_days must be finite and nonnegative")
        if not math.isfinite(self.smoothing) or self.smoothing < 0:
            raise ValueError("smoothing must be finite and nonnegative")
        if not self.smoothing_candidates or any(not math.isfinite(x) or x < 0 for x in self.smoothing_candidates):
            raise ValueError("smoothing_candidates must contain finite nonnegative values")
        for name, floor in (("grid_rows", 361), ("max_irls", 1), ("removal_trials", 1)):
            if not isinstance(getattr(self, name), int) or getattr(self, name) < floor:
                raise ValueError(f"{name} must be an integer >= {floor}")

    def to_dict(self):
        return asdict(self)
