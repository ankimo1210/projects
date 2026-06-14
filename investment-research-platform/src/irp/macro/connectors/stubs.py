"""Stub macro connectors — interface placeholders for sources not yet wired.
They declare the contract but raise NotImplementedError until implemented.
Implemented macro: FRED/ALFRED, US Treasury, e-Stat (JP). Fundamentals: SEC EDGAR
(``irp.data.fundamentals``). The connectors below land as data becomes needed.
"""

from __future__ import annotations

from ..base import MacroConnector
from ..schema import MacroObservation


class _StubMacroConnector(MacroConnector):
    note = "not implemented yet"

    def _download(self, indicator, start, end, *, point_in_time, **_):
        raise NotImplementedError(
            f"{self.source} connector is a stub ({self.note}). "
            "Use FRED/Treasury (US) or e-Stat (JP) for now; this source lands when needed."
        )

    def to_observations(self, raw, indicator, **_) -> list[MacroObservation]:
        raise NotImplementedError(self.source)


class BoJConnector(_StubMacroConnector):
    source = "boj"
    country = "JP"
    note = "BoJ time-series search CSV; tenor/series mapping TBD"


class MofConnector(_StubMacroConnector):
    source = "mof"
    country = "JP"
    note = "MoF JGB yields / trade balance"


class BeaConnector(_StubMacroConnector):
    source = "bea"
    country = "US"
    note = "needs BEA_API_KEY"


class BlsConnector(_StubMacroConnector):
    source = "bls"
    country = "US"
    note = "needs BLS_API_KEY"


class CensusConnector(_StubMacroConnector):
    source = "census"
    country = "US"
    note = "Census economic indicators"


class EdinetConnector(_StubMacroConnector):
    source = "edinet"
    country = "JP"
    note = "JP fundamentals (SEC EDGAR is implemented; EDINET equivalent lands next)"
