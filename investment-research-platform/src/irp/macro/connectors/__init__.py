"""Macro connectors. Implemented: FRED/ALFRED, US Treasury, e-Stat (JP). The rest
are credential-gated or stubbed until needed. (Fundamentals = SEC EDGAR, in
``irp.data.fundamentals``.)
"""

from __future__ import annotations

from .estat import EStatConnector
from .fred import FredConnector
from .stubs import (
    BeaConnector,
    BlsConnector,
    BoJConnector,
    CensusConnector,
    EdinetConnector,
    MofConnector,
)
from .treasury import TreasuryConnector

REGISTRY = {
    "fred": FredConnector,
    "ustreasury": TreasuryConnector,
    "estat": EStatConnector,
    # stubs (land when needed)
    "boj": BoJConnector,
    "mof": MofConnector,
    "bea": BeaConnector,
    "bls": BlsConnector,
    "census": CensusConnector,
    "edinet": EdinetConnector,
}

IMPLEMENTED = {"fred", "ustreasury", "estat"}

__all__ = [
    "IMPLEMENTED",
    "REGISTRY",
    "EStatConnector",
    "FredConnector",
    "TreasuryConnector",
    "get_macro_connector",
]


def get_macro_connector(source: str, **kwargs):
    try:
        return REGISTRY[source](**kwargs)
    except KeyError:
        raise KeyError(f"unknown macro source '{source}'; known: {sorted(REGISTRY)}") from None
