"""Stub macro/fundamentals connectors — interface placeholders for sources planned
in later phases. They declare the contract (so the structure matches the spec)
but raise NotImplementedError until implemented. MVP US+JP macro is served by
FRED + US Treasury; J-Quants/e-Stat are credential-gated and land next.
"""

from __future__ import annotations

from ..base import MacroConnector
from ..schema import MacroObservation


class _StubMacroConnector(MacroConnector):
    note = "not implemented in Phase 1"

    def _download(self, indicator, start, end, *, point_in_time, **_):
        raise NotImplementedError(
            f"{self.source} connector is a Phase-1 stub ({self.note}). "
            "Use FRED/Treasury for MVP US+JP macro; this source lands in a later phase."
        )

    def to_observations(self, raw, indicator, **_) -> list[MacroObservation]:
        raise NotImplementedError(self.source)


class EStatConnector(_StubMacroConnector):
    source = "estat"
    country = "JP"
    note = "needs ESTAT_APP_ID + per-table statsDataId mapping"


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


class SecEdgarConnector(_StubMacroConnector):
    source = "sec_edgar"
    country = "US"
    note = "company facts (fundamentals), not macro — modeled here for now"


class EdinetConnector(_StubMacroConnector):
    source = "edinet"
    country = "JP"
    note = "JP fundamentals"
