"""Morton-code / Z-order sort verification."""

from __future__ import annotations

import cupy as cp
import numpy as np
import pytest

from nbody.octree import compute_morton_codes, sort_by_morton


@pytest.fixture(scope="module")
def cupy_available():
    try:
        import cupy

        _ = cupy.arange(1)
        return True
    except Exception:
        pytest.skip("CuPy/CUDA not available", allow_module_level=False)


def _expected_morton_30bit(xyz_int: np.ndarray) -> np.ndarray:
    """Reference 30-bit Morton: bit-interleave three 10-bit ints (x:hi, y:mid, z:lo)."""
    n = xyz_int.shape[0]
    out = np.zeros(n, dtype=np.uint32)
    for b in range(10):
        out |= ((xyz_int[:, 0] >> b) & 1).astype(np.uint32) << (3 * b + 2)
        out |= ((xyz_int[:, 1] >> b) & 1).astype(np.uint32) << (3 * b + 1)
        out |= ((xyz_int[:, 2] >> b) & 1).astype(np.uint32) << (3 * b + 0)
    return out


def test_morton_matches_reference_on_grid(cupy_available):
    """Random integer grid points should match a Python-level Morton encoder."""
    rng = np.random.default_rng(0)
    n = 4096
    xyz_int = rng.integers(0, 1024, size=(n, 3))
    # Map int grid into [0, 1024) cleanly: place at i + 0.5 so quantisation lands on i.
    pos = ((xyz_int.astype(np.float32) + 0.5) / 1024.0).astype(np.float32)
    pos_d = cp.asarray(pos)
    # We need the GPU kernel's BBox to be exactly [0, 1] for the test to mirror
    # the reference encoder, so force the corner points.
    pos_d_with_corners = cp.concatenate(
        [
            pos_d,
            cp.asarray([[0.0, 0.0, 0.0], [1.0 - 1e-7, 1.0 - 1e-7, 1.0 - 1e-7]], dtype=cp.float32),
        ]
    )
    codes_d, _ = compute_morton_codes(pos_d_with_corners)
    codes = cp.asnumpy(codes_d)[:n]
    expected = _expected_morton_30bit(xyz_int)
    assert np.array_equal(codes, expected), (
        f"first mismatch at index {np.argmax(codes != expected)}"
    )


def test_sort_by_morton_is_monotonic(cupy_available):
    rng = np.random.default_rng(1)
    n = 8192
    pos = rng.uniform(-1, 1, (n, 3)).astype(np.float32)
    mass = np.full(n, 1.0 / n, dtype=np.float32)
    pos_d = cp.asarray(pos)
    mass_d = cp.asarray(mass)
    _, _, _, sorted_codes, order = sort_by_morton(pos_d, mass_d)
    sc = cp.asnumpy(sorted_codes)
    assert np.all(sc[1:] >= sc[:-1]), "Morton codes are not monotonically non-decreasing"
    # The permutation should be a valid permutation of 0..n-1
    o = cp.asnumpy(order)
    assert np.array_equal(np.sort(o), np.arange(n))


def test_morton_locality(cupy_available):
    """Particles close in space should mostly end up close in the sorted order."""
    rng = np.random.default_rng(2)
    n = 2048
    pos = rng.normal(0, 1, (n, 3)).astype(np.float32)
    mass = np.full(n, 1.0 / n, dtype=np.float32)
    pos_d = cp.asarray(pos)
    mass_d = cp.asarray(mass)
    pos_s, _, _, _, _ = sort_by_morton(pos_d, mass_d)
    pos_s_h = cp.asnumpy(pos_s)
    # average neighbour distance should be smaller after sorting than unsorted random walk
    dist_sorted = np.linalg.norm(pos_s_h[1:] - pos_s_h[:-1], axis=1).mean()
    dist_random = np.linalg.norm(pos[1:] - pos[:-1], axis=1).mean()
    assert dist_sorted < 0.5 * dist_random, (
        f"sorted neighbour dist {dist_sorted:.3f} not much smaller than random {dist_random:.3f}"
    )
