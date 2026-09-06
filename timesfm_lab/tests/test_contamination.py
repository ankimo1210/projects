import json

import numpy as np
import pytest
from timesfm_lab.contamination import Coverage, covered_fraction, label, load_index
from timesfm_lab.datasets import Window


def _window(cutoff: int, horizon: int = 10, dataset: str = "d", series: str = "T1") -> Window:
    return Window(
        dataset=dataset,
        series_id=series,
        cutoff=cutoff,
        context=np.zeros(20, dtype=np.float32),
        actual=np.zeros(horizon),
        season=7,
    )


@pytest.fixture
def index():
    return {"d": Coverage("d", "d", 1, 1, 1, 1, {"T1": 100})}


def test_a_window_entirely_before_the_corpus_end_is_fully_covered(index):
    assert covered_fraction(_window(50), index) == pytest.approx(1.0)


def test_a_window_entirely_after_the_corpus_end_is_uncovered(index):
    assert covered_fraction(_window(100), index) == pytest.approx(0.0)


def test_a_window_straddling_the_corpus_end_is_partial(index):
    # cutoff 95, horizon 10 -> indices 95..104, of which 95..99 are covered
    assert covered_fraction(_window(95), index) == pytest.approx(0.5)


def test_a_dataset_absent_from_the_corpus_is_nan_not_zero(index):
    assert np.isnan(covered_fraction(_window(50, dataset="other"), index))
    assert np.isnan(covered_fraction(_window(50, series="T9"), index))


def test_label_distinguishes_held_out_from_past_corpus():
    assert label(float("nan")) == "held out"
    assert label(0.0) == "past corpus"
    assert label(0.5) == "partial"
    assert label(1.0) == "in corpus"


def test_index_round_trips_through_disk(tmp_path, index):
    from timesfm_lab.contamination import save_index

    p = tmp_path / "cov.json"
    save_index(index, p)
    back = load_index(p)
    assert back["d"].lengths == {"T1": 100}
    assert back["d"].verified


def test_a_missing_index_is_an_empty_dict_not_an_error(tmp_path):
    assert load_index(tmp_path / "nope.json") == {}


@pytest.mark.skipif(
    not (__import__("timesfm_lab.contamination", fromlist=["INDEX_PATH"]).INDEX_PATH).exists(),
    reason="run scripts/build_contamination_index.py first",
)
def test_the_real_index_verified_the_shared_datasets_are_identical():
    idx = load_index()
    assert set(idx) == {"traffic_hourly", "weather_daily"}
    for cov in idx.values():
        assert cov.n_series_gep == cov.n_series_local
        assert cov.verified, f"{cov.dataset}: {cov.identical}/{cov.checked} matched"
