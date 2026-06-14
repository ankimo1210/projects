"""quantkit.diagnostics — signal- and strategy-level diagnostics.

Beyond a single Sharpe number, these answer *why* and *how durable*:
  * :mod:`quantkit.diagnostics.ic` — cross-sectional rank IC and its decay over horizons;
  * :mod:`quantkit.diagnostics.exposure` — factor-exposure attribution (betas + alpha);
  * :mod:`quantkit.diagnostics.capacity` — turnover/ADV-based capital capacity.
"""

from __future__ import annotations

from .capacity import capacity
from .exposure import factor_exposure
from .ic import ic_decay, rank_ic

__all__ = ["capacity", "factor_exposure", "ic_decay", "rank_ic"]
