"""Macro connectors. Working in Phase 1: FRED/ALFRED, US Treasury. The rest are
credential-gated or stubbed for later phases.
"""

from __future__ import annotations

from .fred import FredConnector
from .stubs import (
    BeaConnector,
    BlsConnector,
    BoJConnector,
    CensusConnector,
    EdinetConnector,
    EStatConnector,
    MofConnector,
    SecEdgarConnector,
)
from .treasury import TreasuryConnector

REGISTRY = {
    "fred": FredConnector,
    "ustreasury": TreasuryConnector,
    # stubs (Phase 2+)
    "estat": EStatConnector,
    "boj": BoJConnector,
    "mof": MofConnector,
    "bea": BeaConnector,
    "bls": BlsConnector,
    "census": CensusConnector,
    "sec_edgar": SecEdgarConnector,
    "edinet": EdinetConnector,
}

IMPLEMENTED = {"fred", "ustreasury"}

__all__ = ["IMPLEMENTED", "REGISTRY", "FredConnector", "TreasuryConnector", "get_macro_connector"]


def get_macro_connector(source: str, **kwargs):
    try:
        return REGISTRY[source](**kwargs)
    except KeyError:
        raise KeyError(f"unknown macro source '{source}'; known: {sorted(REGISTRY)}") from None
