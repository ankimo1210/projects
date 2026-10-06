"""Rebuild vol 19--28 in /tmp and compare them with committed references."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

import numpy as np

try:
    from .build_frontier_artifacts import FILES, VOLUMES, build_volume
except ImportError:  # direct script execution
    from build_frontier_artifacts import FILES, VOLUMES, build_volume


def _same_values(left, right) -> bool:
    """Compare numbers with tolerance and identity metadata exactly."""
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_same_values(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _same_values(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return bool(np.isclose(left, right, rtol=1e-10, atol=1e-12))
    return left == right


def _compare_npz(committed: Path, rebuilt: Path, *, timing=False) -> None:
    excluded = (
        {"nested_mc_ms", "surrogate_ms", "nested_mc_repeats_ns", "surrogate_repeats_ns"}
        if timing
        else set()
    )
    with (
        np.load(committed, allow_pickle=False) as left,
        np.load(rebuilt, allow_pickle=False) as right,
    ):
        if set(left.files) != set(right.files):
            raise RuntimeError(f"array names differ: {committed.name}")
        for name in left.files:
            if name in excluded:
                passed = (
                    np.all(np.isfinite(left[name]))
                    and np.all(left[name] > 0)
                    and np.all(np.isfinite(right[name]))
                    and np.all(right[name] > 0)
                )
            elif left[name].dtype.kind in "fc":
                passed = left[name].shape == right[name].shape and np.allclose(
                    left[name], right[name], rtol=1e-10, atol=1e-12
                )
            else:
                passed = np.array_equal(left[name], right[name])
            if not passed:
                raise RuntimeError(f"array differs: {committed.name}:{name}")


def _json_values(path: Path, *, timing=False) -> dict:
    value = _normalized_volume21_json(path) if timing else json.loads(path.read_text())
    # The on-disk SHA binds exact bytes for integrity, not a numerical oracle.
    value["companions"] = {name: "<content compared separately>" for name in value["companions"]}
    return value


def _normalized_volume21_json(path: Path) -> dict:
    payload = copy.deepcopy(json.loads(path.read_text(encoding="utf-8")))
    payload["companions"]["joint_surface.npz"] = "<timing-dependent>"
    payload["metrics"]["surrogate_speedup_1024"] = "<timing-dependent>"
    payload["benchmark"]["measurement"] = "<timing-dependent>"
    for check in payload["acceptance"]["checks"]:
        if check["name"] == "surrogate_speedup":
            check["observed"] = "<timing-dependent>"
    return payload


def volume21_measurement_provenance(path: Path) -> str:
    """Validate the committed vol 21 timing provenance and describe it.

    The timing sample is excluded from the rebuild comparison, so its
    provenance must be recorded instead: the generator digests and environment
    of the run that measured it. Returns a one-line note saying whether the
    sample was measured on the current generator.
    """
    benchmark = json.loads(path.read_text(encoding="utf-8"))["benchmark"]
    measurement = benchmark.get("measurement")
    if not isinstance(measurement, dict):
        raise RuntimeError(
            "volume 21 timing sample has no measurement provenance; "
            "rebuild with build_frontier_artifacts.py --volume 21 --refresh-timing"
        )
    sources = measurement.get("sources")
    environment = measurement.get("environment")
    if not isinstance(sources, dict) or set(sources) != set(benchmark["sources"]):
        raise RuntimeError("volume 21 measurement provenance must digest the benchmark sources")
    if not isinstance(environment, dict) or not environment:
        raise RuntimeError("volume 21 measurement provenance must record its environment")
    if sources == benchmark["sources"]:
        return "timing sample measured on the current generator"
    stale = sorted(name for name in sources if sources[name] != benchmark["sources"][name])
    return f"timing sample predates the current generator (changed since measurement: {stale})"


def _compare_volume21_npz(committed: Path, rebuilt: Path) -> None:
    _compare_npz(committed, rebuilt, timing=True)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="johnhull-artifacts-", dir="/tmp") as temporary:
        rebuilt_root = Path(temporary)
        first_values = {}
        for volume in sorted(FILES):
            rebuilt_json, rebuilt_npz = build_volume(
                volume, refresh_timing=volume == 21, output_root=rebuilt_root
            )
            slug, json_name, npz_name = FILES[volume]
            committed = VOLUMES / slug / "reference"
            _compare_npz(committed / npz_name, rebuilt_npz, timing=volume == 21)
            if not _same_values(
                _json_values(committed / json_name, timing=volume == 21),
                _json_values(rebuilt_json, timing=volume == 21),
            ):
                raise RuntimeError(f"volume {volume} JSON semantic values differ")
            if volume == 21:
                print(f"[NOTE] vol 21: {volume21_measurement_provenance(committed / json_name)}")
            with np.load(rebuilt_npz, allow_pickle=False) as stored:
                first_values[volume] = (
                    _json_values(rebuilt_json),
                    {k: stored[k].copy() for k in stored.files},
                )
            print(f"[PASS] vol {volume}: implementation matches committed semantic values")
        for volume in sorted(FILES):
            json_path, npz_path = build_volume(volume, output_root=rebuilt_root)
            before_json, before_arrays = first_values[volume]
            if not _same_values(before_json, _json_values(json_path)):
                raise RuntimeError(f"ordinary rebuild JSON values differ: {volume}")
            with np.load(npz_path, allow_pickle=False) as stored:
                for name, expected in before_arrays.items():
                    actual = stored[name]
                    if expected.dtype.kind in "fc":
                        passed = np.allclose(expected, actual, rtol=1e-10, atol=1e-12)
                    else:
                        passed = np.array_equal(expected, actual)
                    if not passed:
                        raise RuntimeError(f"ordinary rebuild values differ: {volume}:{name}")
        print("[PASS] vol 19--28: second ordinary rebuild agrees within numerical tolerance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
