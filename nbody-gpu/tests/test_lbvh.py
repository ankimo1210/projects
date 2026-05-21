"""Karras LBVH structural invariants."""
from __future__ import annotations

import cupy as cp
import numpy as np
import pytest

from nbody.octree import LBVH, sort_by_morton


@pytest.fixture(scope="module")
def cupy_available():
    try:
        import cupy
        _ = cupy.arange(1)
        return True
    except Exception:
        pytest.skip("CuPy/CUDA not available", allow_module_level=False)


def _build_tree(n: int, seed: int) -> LBVH:
    rng = np.random.default_rng(seed)
    pos = rng.uniform(-1, 1, (n, 3)).astype(np.float32)
    mass = np.full(n, 1.0 / n, dtype=np.float32)
    pos_d = cp.asarray(pos)
    mass_d = cp.asarray(mass)
    _, _, _, sorted_codes, _ = sort_by_morton(pos_d, mass_d)
    return LBVH(sorted_codes)


def test_tree_has_2n_minus_1_nodes(cupy_available):
    n = 1024
    tree = _build_tree(n, seed=0)
    assert tree.parent.shape == (2 * n - 1,)
    assert tree.left.shape == (n - 1,)
    assert tree.right.shape == (n - 1,)


def test_root_parent_is_minus_one(cupy_available):
    """Exactly one node has no parent: the root (internal #0, global id n)."""
    n = 1024
    tree = _build_tree(n, seed=1)
    parent = cp.asnumpy(tree.parent)
    no_parent = np.where(parent == -1)[0]
    assert len(no_parent) == 1, f"expected exactly one root, got {len(no_parent)}"
    assert no_parent[0] == n, f"root global id should be {n}, got {no_parent[0]}"


def test_every_non_root_has_one_parent(cupy_available):
    """Each internal node's children record their parent. So parent[id] >= 0
    for every id != root, and each id appears as a child exactly once."""
    n = 4096
    tree = _build_tree(n, seed=2)
    parent = cp.asnumpy(tree.parent)
    left = cp.asnumpy(tree.left)
    right = cp.asnumpy(tree.right)

    children = np.concatenate([left, right])
    # Each leaf and each non-root internal must appear exactly once as a child.
    expected_children = np.concatenate([
        np.arange(n),                       # leaves
        np.arange(n + 1, 2 * n - 1),        # internals except root
    ])
    assert np.array_equal(np.sort(children), expected_children), \
        "child ids do not cover every non-root node exactly once"

    # parent[id] for each non-root must be a valid internal-node id.
    non_root_ids = np.delete(np.arange(2 * n - 1), n)
    p = parent[non_root_ids]
    assert (p >= n).all() and (p < 2 * n - 1).all(), "non-root parent out of internal range"


def test_range_covers_all_leaves(cupy_available):
    """The root's [range_lo, range_hi] must cover all N leaves."""
    n = 8192
    tree = _build_tree(n, seed=3)
    lo = int(tree.range_lo[0])
    hi = int(tree.range_hi[0])
    assert lo == 0 and hi == n - 1, f"root range = [{lo}, {hi}], expected [0, {n-1}]"


def test_child_ranges_partition_parent(cupy_available):
    """For every internal node, its two children's leaf-ranges must
    partition the parent's range exactly (LBVH invariant)."""
    n = 2048
    tree = _build_tree(n, seed=4)
    left = cp.asnumpy(tree.left)
    right = cp.asnumpy(tree.right)
    lo = cp.asnumpy(tree.range_lo)
    hi = cp.asnumpy(tree.range_hi)

    def leaf_range(gid: int) -> tuple[int, int]:
        if gid < n:
            return (gid, gid)
        k = gid - n
        return (lo[k], hi[k])

    for k in range(n - 1):
        l_lo, l_hi = leaf_range(left[k])
        r_lo, r_hi = leaf_range(right[k])
        # children must be adjacent and together span the parent
        assert (l_lo, r_hi) == (lo[k], hi[k]), \
            f"node {k}: parent=[{lo[k]},{hi[k]}], left=[{l_lo},{l_hi}], right=[{r_lo},{r_hi}]"
        assert l_hi + 1 == r_lo, \
            f"node {k}: gap between children ({l_hi}+1 != {r_lo})"
