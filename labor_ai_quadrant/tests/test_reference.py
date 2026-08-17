"""参照テーブルの整合性。手編集される表なので、壊れたら大きな声で落ちること。"""

from __future__ import annotations

import numpy as np
import pytest
from labor_ai_quadrant.reference import SHORTAGE_INDICATORS, TILT_LEVELS, load_reference


@pytest.fixture(scope="module")
def ref():
    return load_reference()


def test_all_33_sectors_present(ref):
    assert len(ref.shortage) == 33
    assert len(ref.mix) == 33
    assert set(ref.mix.index) == set(ref.shortage.index)


def test_sector_codes_are_unique_and_four_digit(ref):
    codes = ref.shortage["code"]
    assert codes.is_unique
    assert codes.str.fullmatch(r"\d{4}").all()


def test_occupation_mix_rows_are_normalised(ref):
    totals = ref.mix.sum(axis=1)
    assert np.allclose(totals, 1.0), totals[~np.isclose(totals, 1.0)]


def test_occupation_table_covers_every_mix_column(ref):
    assert set(ref.mix.columns) == set(ref.occupations.index)
    assert len(ref.occupations) == 18


def test_shortage_weights_sum_to_one(ref):
    assert ref.shortage_weights.sum() == pytest.approx(1.0)
    assert set(ref.shortage_weights.index) == set(SHORTAGE_INDICATORS)


def test_regulation_drag_within_documented_range(ref):
    assert ref.regulation_drag.between(0.0, 0.5).all()


def test_universe_maps_onto_the_sector_master(ref):
    assert ref.universe.index.is_unique
    assert ref.universe.index.str.fullmatch(r"[0-9A-Z]{4}").all()
    assert set(ref.universe["sector33"]).issubset(set(ref.shortage.index))


def test_universe_tilts_use_the_known_levels(ref):
    for col in ("labor_intensity", "knowledge_tilt"):
        assert set(ref.universe[col]).issubset(set(TILT_LEVELS))


def test_universe_spans_a_broad_slice_of_sectors(ref):
    # The framework is only informative if the universe is not concentrated in
    # a handful of sectors — a regression here means the curated list drifted.
    assert ref.universe["sector33"].nunique() >= 30
    assert len(ref.universe) >= 150


def test_every_table_declares_a_vintage(ref):
    assert set(ref.vintages) == {
        "sector_labor_shortage",
        "occupation_ai_exposure",
        "sector_occupation_mix",
        "universe_jp",
    }
    assert all(v for v in ref.vintages.values())
