import itertools

import numpy as np
import pytest
from timesfm_lab.datasets import DATA_DIR, SPECS, build_windows, parse_tsf

_HAVE_DATA = all(s.path.exists() for s in SPECS)
needs_data = pytest.mark.skipif(not _HAVE_DATA, reason="run scripts/fetch_data.sh first")


def test_parse_tsf_reads_values_and_missing_markers(tmp_path):
    p = tmp_path / "toy.tsf"
    p.write_text(
        "# comment\n@relation Toy\n@frequency daily\n@data\n"
        "T1:2020-01-01 00-00-00:1.0,2.0,?,4.0\n"
        "T2:2020-01-01 00-00-00:5,6\n",
        encoding="utf-8",
    )
    out = parse_tsf(p)
    assert [n for n, _ in out] == ["T1", "T2"]
    assert np.isnan(out[0][1][2])
    np.testing.assert_allclose(out[1][1], [5.0, 6.0])


@needs_data
@pytest.mark.parametrize("spec", SPECS, ids=lambda s: s.key)
def test_windows_have_the_declared_shapes_and_no_nans(spec):
    ws = build_windows(spec)
    assert ws, spec.key
    for w in ws[:20]:
        assert w.context.shape == (spec.context_length,)
        assert w.actual.shape == (spec.horizon,)
        assert np.isfinite(w.context).all()
        assert np.isfinite(w.actual).all()


@needs_data
def test_evaluation_windows_do_not_overlap_within_a_series():
    spec = next(s for s in SPECS if s.key == "ett_h1")
    ws = build_windows(spec)
    by_series: dict[str, list[int]] = {}
    for w in ws:
        by_series.setdefault(w.series_id, []).append(w.cutoff)
    for cuts in by_series.values():
        cuts = sorted(cuts)
        assert all(b - a >= spec.horizon for a, b in itertools.pairwise(cuts))


@needs_data
def test_window_sampling_is_deterministic_given_a_seed():
    spec = next(s for s in SPECS if s.key == "weather_daily")
    a = [w.uid for w in build_windows(spec, seed=7)]
    b = [w.uid for w in build_windows(spec, seed=7)]
    c = [w.uid for w in build_windows(spec, seed=8)]
    assert a == b
    assert a != c


@needs_data
def test_context_and_actual_are_contiguous_and_ordered():
    spec = next(s for s in SPECS if s.key == "saugeen_river")
    from timesfm_lab.datasets import load_series

    raw = dict(load_series(spec))
    for w in build_windows(spec)[:5]:
        full = raw[w.series_id]
        np.testing.assert_allclose(full[w.cutoff : w.cutoff + spec.horizon], w.actual)
        np.testing.assert_allclose(
            full[w.cutoff - spec.context_length : w.cutoff], w.context, rtol=1e-6
        )
