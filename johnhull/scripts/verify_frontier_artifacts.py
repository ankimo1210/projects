"""Rebuild vol 19--28 in /tmp and compare them with committed references."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path

import numpy as np

try:
    from .build_frontier_artifacts import FILES, VOLUMES, build_volume
except ImportError:  # direct script execution
    from build_frontier_artifacts import FILES, VOLUMES, build_volume


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    excluded = {"nested_mc_ms", "surrogate_ms"}
    with (
        np.load(committed, allow_pickle=False) as left,
        np.load(rebuilt, allow_pickle=False) as right,
    ):
        if set(left.files) != set(right.files):
            raise RuntimeError("volume 21 array names differ from the committed reference")
        for name in set(left.files) - excluded:
            if not np.array_equal(left[name], right[name]):
                raise RuntimeError(f"volume 21 deterministic array differs: {name}")
        for name in excluded:
            if not np.all(left[name] > 0) or not np.all(right[name] > 0):
                raise RuntimeError(f"volume 21 timing sample is not positive: {name}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="johnhull-artifacts-", dir="/tmp") as temporary:
        rebuilt_root = Path(temporary)
        first_hashes: dict[Path, str] = {}
        for volume in sorted(FILES):
            rebuilt_json, rebuilt_npz = build_volume(
                volume,
                refresh_timing=volume == 21,
                output_root=rebuilt_root,
            )
            slug, json_name, npz_name = FILES[volume]
            committed = VOLUMES / slug / "reference"
            committed_json = committed / json_name
            committed_npz = committed / npz_name
            if volume == 21:
                _compare_volume21_npz(committed_npz, rebuilt_npz)
                if _normalized_volume21_json(committed_json) != _normalized_volume21_json(
                    rebuilt_json
                ):
                    raise RuntimeError("volume 21 deterministic JSON fields differ")
                print(f"[NOTE] vol 21: {volume21_measurement_provenance(committed_json)}")
            elif _sha256(committed_json) != _sha256(rebuilt_json) or _sha256(
                committed_npz
            ) != _sha256(rebuilt_npz):
                raise RuntimeError(f"volume {volume} is not reproducible from its implementation")
            first_hashes[rebuilt_json] = _sha256(rebuilt_json)
            first_hashes[rebuilt_npz] = _sha256(rebuilt_npz)
            print(f"[PASS] vol {volume}: implementation matches committed semantic values")

        for volume in sorted(FILES):
            build_volume(volume, output_root=rebuilt_root)
        changed = [path for path, digest in first_hashes.items() if _sha256(path) != digest]
        if changed:
            raise RuntimeError(f"ordinary rebuild is not byte-stable: {changed}")
        print("[PASS] vol 19--28: second ordinary rebuild is byte-identical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
