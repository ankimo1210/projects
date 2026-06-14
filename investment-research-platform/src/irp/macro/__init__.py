"""Macro data layer: point-in-time schema, store (as_of/latest), and connectors.

Core guarantee: an indicator is never used before its release_date. Use
:func:`store.as_of` for backtests; :func:`store.latest` only for current dashboards.
"""

from __future__ import annotations

from . import connectors, store
from .base import MacroConnector
from .connectors import FredConnector, TreasuryConnector, get_macro_connector
from .schema import MACRO_COLUMNS, MacroObservation, to_macro_frame
from .store import as_of, latest, revisions

__all__ = [
    "MACRO_COLUMNS",
    "FredConnector",
    "MacroConnector",
    "MacroObservation",
    "TreasuryConnector",
    "as_of",
    "connectors",
    "get_macro_connector",
    "latest",
    "revisions",
    "store",
    "to_macro_frame",
]
