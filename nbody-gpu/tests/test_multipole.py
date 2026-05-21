"""Bottom-up multipole propagation correctness."""
from __future__ import annotations

import cupy as cp
import numpy as np
import pytest

from nbody.octree import LBVH, Multipole, sort_by_morton


@pytest.fixture(scope="module")
def cupy_available():
    try:
        import cupy
        _ = cupy.arange(1)
        return True
    except Exception:
        pytest.skip("CuPy/CUDA not available", allow_module_level=False)


def _setup(n: int, seed: int):
    rng = np.random.default_rng(seed)
    pos = rng.uniform(-1, 1, (n, 3)).astype(np.float32)
    # non-uniform masses so a wrong combine would skew the COM detectably
    mass = rng.uniform(0.5, 1.5, n).astype(np.float32)
    pos_d = cp.asarray(pos)
    mass_d = cp.asarray(mass)
    pos_s, mass_s, _, codes_sorted, _ = sort_by_morton(pos_d, mass_d)
    tree = LBVH(codes_sorted)
    mp = Multipole(tree, pos_s, mass_s)
    return pos_s, mass_s, tree, mp


def test_root_mass_matches_total(cupy_available):
    n = 4096
    pos_s, mass_s, tree, mp = _setup(n, seed=0)
    root_mass = float(mp.node_mass[tree.root])
    total = float(mass_s.sum())
    assert abs(root_mass - total) / total < 1e-4, f"root={root_mass} total={total}"


def test_root_com_matches_global_com(cupy_available):
    n = 4096
    pos_s, mass_s, tree, mp = _setup(n, seed=1)
    root_com = cp.asnumpy(mp.node_com[tree.root])
    expected = cp.asnumpy((mass_s[:, None] * pos_s).sum(0) / mass_s.sum())
    assert np.allclose(root_com, expected, rtol=1e-3, atol=1e-4), \
        f"root_com={root_com}  expected={expected}"


def test_root_bbox_covers_all_points(cupy_available):
    n = 4096
    pos_s, mass_s, tree, mp = _setup(n, seed=2)
    bb_min = cp.asnumpy(mp.node_bb_min[tree.root])
    bb_max = cp.asnumpy(mp.node_bb_max[tree.root])
    p = cp.asnumpy(pos_s)
    assert (p >= bb_min - 1e-6).all() and (p <= bb_max + 1e-6).all()
    # and should be tight
    assert np.allclose(bb_min, p.min(0), atol=1e-6)
    assert np.allclose(bb_max, p.max(0), atol=1e-6)


def test_every_internal_node_combines_children(cupy_available):
    """For every internal node, mass = m_L + m_R and com is the mass-weighted average."""
    n = 1024
    pos_s, mass_s, tree, mp = _setup(n, seed=3)
    left = cp.asnumpy(tree.left)
    right = cp.asnumpy(tree.right)
    nm = cp.asnumpy(mp.node_mass)
    nc = cp.asnumpy(mp.node_com)

    for k in range(n - 1):
        gid = n + k
        l, r = left[k], right[k]
        m = nm[l] + nm[r]
        assert abs(nm[gid] - m) <= 1e-3 * max(m, 1e-6), \
            f"node {k}: mass {nm[gid]} != {m}"
        expected_com = (nm[l] * nc[l] + nm[r] * nc[r]) / max(m, 1e-30)
        assert np.allclose(nc[gid], expected_com, atol=1e-4), \
            f"node {k}: com {nc[gid]} != {expected_com}"
