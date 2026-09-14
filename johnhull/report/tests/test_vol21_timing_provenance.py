"""Provenance of the vol 21 timing sample.

The ordinary rebuild preserves the committed perf_counter sample and the
artifact check excludes it from comparison, so nothing tied the timings to the
implementation they measured: after a generator change the old sample was kept
next to the new source digest. The reference now records the generator digests
and environment of the run that measured the sample, carries them over when the
sample is preserved, and the artifact check requires them.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from johnhull.scripts.build_frontier_artifacts import (
    _benchmark_contract,
    _preserve_vol21_timing_reference,
)
from johnhull.scripts.verify_frontier_artifacts import volume21_measurement_provenance

GENERATOR = {
    "generated_by": "johnhull/scripts/build_frontier_artifacts.py",
    "generator_api": "hullkit.frontier_reference.build_frontier_reference",
}


def _arrays(nested: float, surrogate: float) -> dict[str, np.ndarray]:
    return {
        "batch_size": np.array([16, 128, 1024]),
        "nested_mc_ms": np.full(3, nested),
        "surrogate_ms": np.full(3, surrogate),
    }


def _commit(folder, benchmark, speedup, arrays):
    folder.mkdir(parents=True, exist_ok=True)
    payload = {**GENERATOR, "benchmark": benchmark, "metrics": {"surrogate_speedup_1024": speedup}}
    (folder / "metrics.json").write_text(json.dumps(payload), encoding="utf-8")
    np.savez(folder / "joint_surface.npz", **arrays)


def test_contract_records_the_measurement_provenance():
    benchmark = _benchmark_contract(21, _arrays(1.0, 1.0))

    assert benchmark["measurement"]["sources"] == benchmark["sources"]
    assert benchmark["measurement"]["environment"]["python"]
    assert "benchmark.measurement" in benchmark["nondeterministic_fields"]


def test_preserved_sample_keeps_the_provenance_of_its_measurement(tmp_path):
    committed = _benchmark_contract(21, _arrays(1.0, 1.0))
    committed["measurement"] = {"sources": {"old.py": "aaa"}, "environment": {"python": "3.0"}}
    _commit(tmp_path, committed, 50.0, _arrays(100.0, 2.0))

    metrics = {"surrogate_speedup_1024": 7.0}
    arrays = _arrays(70.0, 10.0)
    current = _benchmark_contract(21, arrays)
    _preserve_vol21_timing_reference(tmp_path, metrics, arrays, current)

    assert metrics["surrogate_speedup_1024"] == 50.0
    assert np.all(arrays["nested_mc_ms"] == 100.0)
    assert current["measurement"] == committed["measurement"]
    assert current["sources"] != current["measurement"]["sources"]


def test_sample_without_provenance_is_measured_again(tmp_path):
    legacy = _benchmark_contract(21, _arrays(1.0, 1.0))
    del legacy["measurement"]
    _commit(tmp_path, legacy, 50.0, _arrays(100.0, 2.0))

    metrics = {"surrogate_speedup_1024": 7.0}
    arrays = _arrays(70.0, 10.0)
    current = _benchmark_contract(21, arrays)
    fresh_measurement = current["measurement"]
    _preserve_vol21_timing_reference(tmp_path, metrics, arrays, current)

    assert metrics["surrogate_speedup_1024"] == 7.0
    assert np.all(arrays["nested_mc_ms"] == 70.0)
    assert current["measurement"] == fresh_measurement


def _reference(tmp_path, benchmark):
    path = tmp_path / "metrics.json"
    path.write_text(json.dumps({"benchmark": benchmark}), encoding="utf-8")
    return path


def test_artifact_check_reports_whether_timings_predate_the_generator(tmp_path):
    benchmark = _benchmark_contract(21, _arrays(1.0, 1.0))
    assert "current generator" in volume21_measurement_provenance(_reference(tmp_path, benchmark))

    name = next(iter(benchmark["sources"]))
    benchmark["measurement"]["sources"][name] = "0" * 64
    note = volume21_measurement_provenance(_reference(tmp_path, benchmark))
    assert "predates" in note and name in note


@pytest.mark.parametrize(
    "measurement",
    [None, {"sources": {}, "environment": {"python": "3"}}, {"sources": None, "environment": {}}],
)
def test_artifact_check_requires_the_provenance(tmp_path, measurement):
    benchmark = _benchmark_contract(21, _arrays(1.0, 1.0))
    if measurement is None:
        del benchmark["measurement"]
    else:
        benchmark["measurement"] = measurement

    with pytest.raises(RuntimeError, match="provenance"):
        volume21_measurement_provenance(_reference(tmp_path, benchmark))
