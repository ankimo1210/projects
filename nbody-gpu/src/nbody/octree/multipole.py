"""Bottom-up propagation of mass, centre-of-mass and bounding box.

After Karras tree construction every internal node knows its two children;
we compute each internal node's monopole moment by walking upward from the
leaves. The trick (also Karras 2012) is an atomic counter per internal node:
the *first* child to arrive bumps the counter from 0 to 1 and returns; the
*second* child sees a 1, knows both subtrees are now finished, and is
responsible for combining them and climbing further. `__threadfence()` is
used to publish the writes before the parent reads them.
"""
from __future__ import annotations

import cupy as cp

from .lbvh import LBVH


_PROPAGATE_SRC = r"""
extern "C" __global__
void propagate_up(
    const int* __restrict__ parent,
    const int* __restrict__ left,
    const int* __restrict__ right,
    float* __restrict__ node_mass,
    float* __restrict__ node_com,      // (2n-1, 3) flattened
    float* __restrict__ node_bb_min,   // (2n-1, 3) flattened
    float* __restrict__ node_bb_max,   // (2n-1, 3) flattened
    int* __restrict__ visited,         // (n-1,)
    const int n)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;

    int cur = parent[i];
    while (cur >= 0) {
        int k = cur - n;  // internal-node index
        int old = atomicAdd(&visited[k], 1);
        if (old == 0) {
            // First arrival — the sibling thread will combine us later.
            return;
        }
        // Second arrival: both children are written. Make their writes visible.
        __threadfence();

        int l = left[k];
        int r = right[k];

        float m_l = node_mass[l];
        float m_r = node_mass[r];
        float m   = m_l + m_r;
        node_mass[cur] = m;

        // mass-weighted COM
        float inv_m = (m > 0.f) ? 1.0f / m : 0.f;
        for (int d = 0; d < 3; ++d) {
            float cl = node_com[3 * l + d];
            float cr = node_com[3 * r + d];
            node_com[3 * cur + d] = (m_l * cl + m_r * cr) * inv_m;
        }

        // expanded bounding box
        for (int d = 0; d < 3; ++d) {
            float mn_l = node_bb_min[3 * l + d];
            float mn_r = node_bb_min[3 * r + d];
            float mx_l = node_bb_max[3 * l + d];
            float mx_r = node_bb_max[3 * r + d];
            node_bb_min[3 * cur + d] = fminf(mn_l, mn_r);
            node_bb_max[3 * cur + d] = fmaxf(mx_l, mx_r);
        }
        __threadfence();
        cur = parent[cur];
    }
}
"""

_propagate_kernel = cp.RawKernel(_PROPAGATE_SRC, "propagate_up")


class Multipole:
    """Monopole-level aggregates on an LBVH.

    For each node (leaf or internal) stores total mass, mass-weighted centre
    of mass, and an axis-aligned bounding box. Internal-node values are filled
    by `compute()`; leaf-node values are seeded from particle data.
    """

    def __init__(self, tree: LBVH, pos: cp.ndarray, mass: cp.ndarray):
        assert pos.dtype == cp.float32 and mass.dtype == cp.float32
        n = tree.n
        assert pos.shape == (n, 3) and mass.shape == (n,)
        total_nodes = 2 * n - 1

        self.tree = tree
        self.node_mass = cp.zeros(total_nodes, dtype=cp.float32)
        self.node_com = cp.zeros((total_nodes, 3), dtype=cp.float32)
        self.node_bb_min = cp.empty((total_nodes, 3), dtype=cp.float32)
        self.node_bb_max = cp.empty((total_nodes, 3), dtype=cp.float32)

        # seed leaves
        self.node_mass[:n] = mass
        self.node_com[:n] = pos
        self.node_bb_min[:n] = pos
        self.node_bb_max[:n] = pos
        # internal bb initialised to extremes so reductions are well-defined
        self.node_bb_min[n:] = cp.float32(cp.inf)
        self.node_bb_max[n:] = cp.float32(-cp.inf)

        visited = cp.zeros(n - 1, dtype=cp.int32)

        threads = 256
        blocks = (n + threads - 1) // threads
        _propagate_kernel(
            (blocks,), (threads,),
            (tree.parent, tree.left, tree.right,
             self.node_mass,
             self.node_com.ravel(),
             self.node_bb_min.ravel(),
             self.node_bb_max.ravel(),
             visited, cp.int32(n)),
        )

        # Per-node "size" for the BH θ-criterion: half-diagonal length of the
        # AABB. This is a conservative (slightly larger than necessary) measure
        # that ensures we never over-approximate too eagerly.
        diag = self.node_bb_max - self.node_bb_min
        self.node_size = (cp.linalg.norm(diag, axis=1) * 0.5).astype(cp.float32)

    @property
    def root(self) -> int:
        return self.tree.root

    def node_extent(self) -> cp.ndarray:
        """Per-node half-diagonal length (used for BH θ-criterion as 'size')."""
        diag = self.node_bb_max - self.node_bb_min
        return cp.linalg.norm(diag, axis=1) * 0.5
