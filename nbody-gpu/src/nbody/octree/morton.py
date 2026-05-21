"""Morton (Z-order) codes on GPU.

A 30-bit Morton code interleaves 10 bits from each of (x, y, z) so that
spatially close points have numerically close codes. Sorting particles by
their Morton code groups them along a space-filling curve, which is the
prerequisite for the LBVH construction (Karras 2012).
"""
from __future__ import annotations

import cupy as cp

_MORTON_SRC = r"""
__device__ __forceinline__ unsigned int expand_bits(unsigned int v) {
    // Spread the low 10 bits of v into every third bit.
    v = (v * 0x00010001u) & 0xFF0000FFu;
    v = (v * 0x00000101u) & 0x0F00F00Fu;
    v = (v * 0x00000011u) & 0xC30C30C3u;
    v = (v * 0x00000005u) & 0x49249249u;
    return v;
}

extern "C" __global__
void morton_codes(
    const float3* __restrict__ pos,
    unsigned int* __restrict__ codes,
    const float bb_min_x, const float bb_min_y, const float bb_min_z,
    const float inv_extent_x, const float inv_extent_y, const float inv_extent_z,
    const int n)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n) return;
    float3 p = pos[i];
    float x = (p.x - bb_min_x) * inv_extent_x;
    float y = (p.y - bb_min_y) * inv_extent_y;
    float z = (p.z - bb_min_z) * inv_extent_z;
    // Clamp to [0, 1 - tiny] so that the floor multiplication never hits 1024.
    x = fminf(fmaxf(x, 0.0f), 0.99999994f);
    y = fminf(fmaxf(y, 0.0f), 0.99999994f);
    z = fminf(fmaxf(z, 0.0f), 0.99999994f);
    unsigned int xx = expand_bits((unsigned int)(x * 1024.0f));
    unsigned int yy = expand_bits((unsigned int)(y * 1024.0f));
    unsigned int zz = expand_bits((unsigned int)(z * 1024.0f));
    codes[i] = (xx << 2) | (yy << 1) | zz;
}
"""

_morton_kernel = cp.RawKernel(_MORTON_SRC, "morton_codes")


def compute_morton_codes(pos: cp.ndarray) -> tuple[cp.ndarray, tuple[cp.ndarray, cp.ndarray]]:
    """Return (codes, (bb_min, bb_max)) for the given positions.

    `pos` is (N, 3) float32 on the device. The bounding box is computed on
    the GPU via CuPy reductions; the box is expanded by a tiny epsilon on the
    upper side to avoid the [0, 1) clamping eating a corner particle.
    """
    n = pos.shape[0]
    assert pos.dtype == cp.float32 and pos.shape == (n, 3)
    bb_min_d = pos.min(axis=0)
    bb_max_d = pos.max(axis=0)
    extent_d = bb_max_d - bb_min_d
    # Avoid divide-by-zero on degenerate axes (e.g., all-coplanar input).
    extent_d = cp.where(extent_d > 0, extent_d, cp.float32(1.0))
    inv_extent_d = (1.0 / extent_d).astype(cp.float32)

    # Kernel scalar parameters must be host values (or 0-d cupy arrays pass-through);
    # pull just the six floats back to the host once.
    bb_min_h = cp.asnumpy(bb_min_d)
    inv_extent_h = cp.asnumpy(inv_extent_d)

    codes = cp.empty(n, dtype=cp.uint32)
    threads = 256
    blocks = (n + threads - 1) // threads
    _morton_kernel(
        (blocks,), (threads,),
        (pos, codes,
         cp.float32(bb_min_h[0]), cp.float32(bb_min_h[1]), cp.float32(bb_min_h[2]),
         cp.float32(inv_extent_h[0]), cp.float32(inv_extent_h[1]), cp.float32(inv_extent_h[2]),
         cp.int32(n)),
    )
    return codes, (bb_min_d, bb_max_d)


def sort_by_morton(
    pos: cp.ndarray, mass: cp.ndarray, vel: cp.ndarray | None = None
) -> tuple[cp.ndarray, cp.ndarray, cp.ndarray | None, cp.ndarray, cp.ndarray]:
    """Sort particles into Z-order.

    Returns the reordered arrays plus the sorted Morton codes and the
    permutation that produced them. Sorted codes are needed by the LBVH
    construction step (Phase 3b-2).
    """
    codes, _ = compute_morton_codes(pos)
    order = cp.argsort(codes)
    sorted_codes = codes[order]
    pos_s = pos[order]
    mass_s = mass[order]
    vel_s = vel[order] if vel is not None else None
    return pos_s, mass_s, vel_s, sorted_codes, order
