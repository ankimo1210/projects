"""Thin wrapper around the TimesFM 3.0 evaluator.

Keeps two things out of the benchmark loop: the 20-second checkpoint load, and
the flag choices.  We use the flags the TimesFM authors use for their own
published benchmark numbers, so a loss here cannot be blamed on us having
misconfigured the model.
"""

from __future__ import annotations

import dataclasses
import time

import numpy as np

from .baselines import QUANTILE_LEVELS, Forecast

CHECKPOINT = "google/timesfm-3.0-pytorch"
MODEL_KEY = "timesfm_3.0"


@dataclasses.dataclass
class TimesFMRunner:
    checkpoint: str = CHECKPOINT
    device: str = "cuda"
    batch_size: int = 16
    # The README's benchmark call passes use_symmetric_averaging=False; the rest
    # are the evaluator's own benchmark defaults.
    use_symmetric_averaging: bool = False
    make_positive: bool = True

    def __post_init__(self) -> None:
        from timesfm3 import ModelConfig, TimesFM3Evaluator

        t0 = time.time()
        self._evaluator = TimesFM3Evaluator(
            ModelConfig(
                checkpoint_path=self.checkpoint,
                per_core_batch_size=self.batch_size,
                device=self.device,
            )
        )
        self.load_seconds = time.time() - t0
        levels = np.asarray(self._evaluator.config.quantiles, dtype=float)
        if not np.allclose(levels, QUANTILE_LEVELS):
            raise RuntimeError(
                f"TimesFM quantile grid {levels} differs from the baseline grid "
                f"{QUANTILE_LEVELS}; the CRPS comparison would not be like-for-like."
            )

    def predict(self, contexts: list[np.ndarray], horizon: int) -> tuple[list[Forecast], float]:
        """Forecast a batch of univariate contexts. Returns forecasts and wall seconds."""
        t0 = time.time()
        outputs = list(
            self._evaluator.predict_batch(
                [np.asarray(c, dtype=np.float32) for c in contexts],
                horizon=horizon,
                return_quantiles=True,
                use_symmetric_averaging=self.use_symmetric_averaging,
                make_positive=self.make_positive,
            )
        )
        elapsed = time.time() - t0
        forecasts = []
        for o in outputs:
            fan = np.sort(np.asarray(o.quantiles, dtype=np.float64), axis=1)
            forecasts.append(Forecast(np.asarray(o.forecast, dtype=np.float64), fan))
        if len(forecasts) != len(contexts):
            raise RuntimeError(f"got {len(forecasts)} forecasts for {len(contexts)} contexts")
        return forecasts, elapsed
