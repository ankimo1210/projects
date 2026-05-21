"""Barnes-Hut traversal on GPU.

Each thread independently descends the LBVH from the root using a local
stack. At every node we apply the Barnes-Hut θ-criterion:

    s / d < θ   →  treat the node as a single monopole at its COM
    otherwise   →  descend into both children

`s` here is the node's AABB half-diagonal (`Multipole.node_size`) and `d`
is the distance from the query particle to the node's centre of mass.
Leaves contribute directly; the query particle skips itself.
"""
from __future__ import annotations

import cupy as cp

from .octree.lbvh import LBVH
from .octree.morton import sort_by_morton
from .octree.multipole import Multipole


_BH_SRC = r"""
extern "C" __global__
void bh_force(
    const float3* __restrict__ pos,
    const int*    __restrict__ left,
    const int*    __restrict__ right,
    const float*  __restrict__ node_mass,
    const float*  __restrict__ node_com,   // (total_nodes, 3) flattened
    const float*  __restrict__ node_size,
    float3*       __restrict__ acc,
    const int   n,
    const int   root,
    const float theta2,
    const float eps2,
    const float G)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;

    float3 p = pos[i];
    float3 ai = make_float3(0.f, 0.f, 0.f);

    // Local stack. log2(N) is the balanced depth; LBVH on Morton-sorted
    // points is well behaved so 64 is plenty up to N ~ 10^7.
    int stack[64];
    int sp = 0;
    stack[sp++] = root;

    while (sp > 0) {
        int node = stack[--sp];

        float cx = node_com[3 * node + 0];
        float cy = node_com[3 * node + 1];
        float cz = node_com[3 * node + 2];
        float dx = cx - p.x;
        float dy = cy - p.y;
        float dz = cz - p.z;
        float r2_raw = dx*dx + dy*dy + dz*dz;

        if (node < n) {
            // Leaf — skip self-interaction; otherwise add monopole.
            if (node == i) continue;
            float r2 = r2_raw + eps2;
            float inv_r = rsqrtf(r2);
            float s = node_mass[node] * inv_r * inv_r * inv_r;
            ai.x += s * dx;
            ai.y += s * dy;
            ai.z += s * dz;
        } else {
            float s = node_size[node];
            // accept-as-monopole criterion: s^2 < theta^2 * d^2
            if (s * s < theta2 * r2_raw) {
                float r2 = r2_raw + eps2;
                float inv_r = rsqrtf(r2);
                float w = node_mass[node] * inv_r * inv_r * inv_r;
                ai.x += w * dx;
                ai.y += w * dy;
                ai.z += w * dz;
            } else {
                int k = node - n;
                if (sp + 2 > 64) {
                    // Stack overflow guard: fall back to descending only the
                    // closer child (rare, only if the tree is pathological).
                    stack[sp++] = right[k];
                } else {
                    stack[sp++] = left[k];
                    stack[sp++] = right[k];
                }
            }
        }
    }

    acc[i].x = G * ai.x;
    acc[i].y = G * ai.y;
    acc[i].z = G * ai.z;
}
"""

_bh_kernel = cp.RawKernel(_BH_SRC, "bh_force")


def compute_acceleration_bh(
    pos: cp.ndarray,
    mass: cp.ndarray,
    theta: float = 0.5,
    eps: float = 1e-2,
    G: float = 1.0,
    block_size: int = 128,
) -> tuple[cp.ndarray, cp.ndarray]:
    """One-shot Barnes-Hut acceleration on a sorted LBVH.

    Builds Morton-sorted permutation, LBVH, multipole moments, and runs the
    traversal kernel. Returns acceleration *in the original particle order*
    (we undo the Morton permutation on the way out).

    Returns
    -------
    acc : (N, 3) float32  — gravitational acceleration on each input particle
    order : (N,) int32    — the Morton permutation actually used
                            (kept in case callers want to reuse it)
    """
    n = pos.shape[0]
    assert pos.dtype == cp.float32 and mass.dtype == cp.float32
    assert pos.shape == (n, 3) and mass.shape == (n,)

    pos_s, mass_s, _, codes_sorted, order = sort_by_morton(pos, mass)
    tree = LBVH(codes_sorted)
    mp = Multipole(tree, pos_s, mass_s)

    acc_s = cp.empty((n, 3), dtype=cp.float32)
    threads = block_size
    blocks = (n + threads - 1) // threads
    _bh_kernel(
        (blocks,), (threads,),
        (pos_s, tree.left, tree.right,
         mp.node_mass, mp.node_com.ravel(), mp.node_size,
         acc_s,
         cp.int32(n), cp.int32(tree.root),
         cp.float32(theta * theta), cp.float32(eps * eps), cp.float32(G)),
    )

    # Undo the permutation: acc_s[k] is the force on the k-th sorted particle,
    # which corresponds to the original particle `order[k]`.
    acc = cp.empty_like(acc_s)
    acc[order] = acc_s
    return acc, order
