"""Dump the hand-authored preflop charts to a dev fixture JSON for the app.

Reads the 15 charts in gto.trainer.preflop_data (5 RFI + 5 BB-defend +
5 opener-vs-3bet) and writes gto/fixtures/packs/preflop-charts.dev.v1.json
in the P1 dev-fixture schema consumed by @gto/packs. This is NOT the H1
Rust-writer golden fixture — it exists so the mobile Study tab can be built
against real chart content before the P0b pack pipeline lands.

Frequencies are quantized to u8 (0..255) with largest-remainder rounding so
every hand's action row sums to exactly 255. Output is deterministic.

Run from gto/:  PYTHONPATH=src python3 scripts/build_preflop_fixture.py
"""

from __future__ import annotations

import json
from pathlib import Path

from gto.trainer.preflop_data import (
    RANKS,
    FACING_RANGES,
    RFI_BY_POS,
    VS_3BET_RANGES,
)

SCHEMA = "gto.preflop-chart-pack"
SCHEMA_VERSION = "1.0.0"
OUT_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "packs" / "preflop-charts.dev.v1.json"


def grid_hand_labels() -> list[str]:
    """169 hand labels in row-major 13x13 grid order (AA top-left).

    Row i / col j over RANKS "AKQJT98765432": diagonal = pair,
    upper triangle (j > i) = suited, lower triangle (j < i) = offsuit.
    Must match ALL_HAND_LABELS_GRID in @gto/domain.
    """
    labels = []
    for i, r_row in enumerate(RANKS):
        for j, r_col in enumerate(RANKS):
            if i == j:
                labels.append(r_row + r_col)
            elif j > i:
                labels.append(r_row + r_col + "s")
            else:
                labels.append(r_col + r_row + "o")
    return labels


def quantize_row(freqs: dict[str, float], actions: list[str]) -> list[int]:
    """Percent frequencies -> u8 (sum exactly 255) via largest remainder."""
    raw = [freqs.get(a, 0) * 255 / 100 for a in actions]
    floors = [int(x) for x in raw]
    remainder = 255 - sum(floors)
    if remainder < 0:  # defensive; cannot happen if input sums to 100
        raise ValueError(f"frequencies exceed 100%: {freqs}")
    # Distribute leftover units to the largest fractional parts; ties broken
    # by action order for determinism.
    order = sorted(range(len(actions)), key=lambda k: (-(raw[k] - floors[k]), k))
    for k in order[:remainder]:
        floors[k] += 1
    assert sum(floors) == 255
    return floors


def build_chart(chart_id: str, kind: str, title: str, actions: list[str], table: dict[str, dict]) -> dict:
    labels = grid_hand_labels()
    missing = [h for h in labels if h not in table]
    if missing:
        raise ValueError(f"{chart_id}: missing hands {missing[:5]}...")
    freqs = [quantize_row(table[h], actions) for h in labels]
    return {
        "id": chart_id,
        "kind": kind,
        "title": title,
        "actions": actions,
        "freqs": freqs,
    }


def main() -> None:
    charts = []
    for pos in ["UTG", "HJ", "CO", "BTN", "SB"]:
        charts.append(build_chart(
            f"rfi:{pos}", "rfi", f"{pos} open", ["R", "F"], RFI_BY_POS[pos],
        ))
    for scenario in ["BB_vs_UTG", "BB_vs_HJ", "BB_vs_CO", "BB_vs_BTN", "BB_vs_SB"]:
        opp = scenario.partition("_vs_")[2]
        charts.append(build_chart(
            f"facing:{scenario}", "facing", f"BB vs {opp} open", ["3B", "C", "F"],
            FACING_RANGES[scenario],
        ))
    for scenario in ["UTG_vs_BB_3bet", "HJ_vs_BB_3bet", "CO_vs_BB_3bet", "BTN_vs_BB_3bet", "SB_vs_BB_3bet"]:
        pos = scenario.partition("_vs_")[0]
        charts.append(build_chart(
            f"vs3bet:{scenario}", "vs3bet", f"{pos} vs BB 3bet", ["4B", "C", "F"],
            VS_3BET_RANGES[scenario],
        ))

    pack = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "quality": "CHART",
        "game": "nlhe-cash-6max-100bb",
        "generated_from": "src/gto/trainer/preflop_data.py",
        "hand_grid_order": "row-major 13x13 over AKQJT98765432; diag=pair, upper=suited, lower=offsuit",
        "charts": charts,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(pack, separators=(",", ":")) + "\n")
    print(f"wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes, {len(charts)} charts)")


if __name__ == "__main__":
    main()
