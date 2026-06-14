"""quantkit — local multi-asset investment **research** platform (free data only).

Research-only: this package downloads/normalizes/validates free market & macro
data and (in later phases) researches signals, models, and backtests. It is NOT
a live trading system.

Phase 1 ships the data layer: a common Connector interface, caching, data-quality
diagnostics, and point-in-time-aware macro handling (an indicator is never used
before its release_date).
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
