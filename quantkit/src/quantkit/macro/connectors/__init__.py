"""Macro connectors — all implemented (key-gated where the source requires it):
FRED/ALFRED + US Treasury + e-Stat (JP) + BoJ/MoF (JP CSV) + BLS/BEA/Census (US).
(Fundamentals: SEC EDGAR + EDINET in ``quantkit.data.fundamentals``.)
"""

from __future__ import annotations

from .estat import EStatConnector
from .fred import FredConnector
from .jp_extra import BoJConnector, MofConnector
from .treasury import TreasuryConnector
from .us_gov import BeaConnector, BlsConnector, CensusConnector

REGISTRY = {
    "fred": FredConnector,
    "ustreasury": TreasuryConnector,
    "estat": EStatConnector,
    "boj": BoJConnector,
    "mof": MofConnector,
    "bls": BlsConnector,
    "bea": BeaConnector,
    "census": CensusConnector,
}

#: connectors needing a key still implement the full contract (parsers tested offline)
KEY_GATED = {"fred", "bea", "census"}

__all__ = [
    "KEY_GATED",
    "REGISTRY",
    "BeaConnector",
    "BlsConnector",
    "BoJConnector",
    "CensusConnector",
    "EStatConnector",
    "FredConnector",
    "MofConnector",
    "TreasuryConnector",
    "get_macro_connector",
]


def get_macro_connector(source: str, **kwargs):
    try:
        return REGISTRY[source](**kwargs)
    except KeyError:
        raise KeyError(f"unknown macro source '{source}'; known: {sorted(REGISTRY)}") from None
