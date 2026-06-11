"""Range-notation parser: "AA,AKs:0.5,KQo" -> np.ndarray[1326] of weights.

Grammar (comma-separated entries, whitespace ignored):
  entry  = class [":" weight]
  class  = RR (pair) | RRs (suited) | RRo (offsuit), ranks from AKQJT98765432
  weight = float in [0, 1]; default 1.0; later entries overwrite earlier ones.

Bare two-rank classes without s/o ("AK") are rejected — explicit is better
than a silent 12-combo offsuit interpretation.
"""

from __future__ import annotations

import numpy as np

from gto.library.range_builder import NUM_COMBOS, hand_to_combo_indices

_RANKS = set("AKQJT98765432")


def parse_range_notation(notation: str) -> np.ndarray:
    weights = np.zeros(NUM_COMBOS, dtype=np.float64)
    entries = [e.strip() for e in notation.split(",")]
    if not any(entries):
        raise ValueError("empty range notation")
    for entry in entries:
        if not entry:
            raise ValueError("empty entry in range notation")
        cls, _, wpart = entry.partition(":")
        cls = cls.strip()
        if wpart:
            try:
                w = float(wpart)
            except ValueError as e:
                raise ValueError(f"bad weight in {entry!r}") from e
            if not 0.0 <= w <= 1.0:
                raise ValueError(f"weight out of [0,1] in {entry!r}")
        else:
            w = 1.0
        if len(cls) == 2:
            if cls[0] != cls[1]:
                raise ValueError(
                    f"{cls!r}: non-pair classes need an s/o suffix (AKs / AKo)"
                )
        elif len(cls) == 3:
            if cls[2] not in ("s", "o") or cls[0] == cls[1]:
                raise ValueError(f"bad hand class {cls!r}")
        else:
            raise ValueError(f"bad hand class {cls!r}")
        if cls[0] not in _RANKS or cls[1] not in _RANKS:
            raise ValueError(f"bad rank in {cls!r}")
        for idx in hand_to_combo_indices(cls):
            weights[idx] = w
    return weights
