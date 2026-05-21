"""Parallel LBVH construction over sorted Morton codes (Karras 2012).

Given N particles sorted by 30-bit Morton code, build the radix tree of
N-1 internal nodes in O(N) work with each thread handling one internal
node independently. The construction follows:

  Karras, T. (2012). "Maximizing Parallelism in the Construction of
  BVHs, Octrees, and k-d Trees". HPG '12.

Node numbering convention used here:
  - leaf  i      -> global id = i              (i in [0, N))
  - internal k   -> global id = N + k          (k in [0, N-1))
  - root         -> internal 0  -> global id N

`parent[id]` is the global id of the node's parent, or -1 for the root.
Internal-node arrays (`left`, `right`, `range_lo`, `range_hi`) are of
length N-1 and indexed by k.
"""

from __future__ import annotations

import cupy as cp

_LBVH_SRC = r"""
// `delta(i, j)` = length of common prefix between Morton codes i and j.
// Out-of-range j returns -1 so it loses every comparison.
// Tie-breaking on identical codes uses the bit pattern of the index, which
// guarantees a strict ordering and prevents degenerate trees.
__device__ __forceinline__ int delta_(
    const unsigned int* __restrict__ codes, int n, int i, int j)
{
    if (j < 0 || j >= n) return -1;
    unsigned int a = codes[i];
    unsigned int b = codes[j];
    if (a != b) return __clz(a ^ b);
    return 32 + __clz(((unsigned int)i) ^ ((unsigned int)j));
}

__device__ __forceinline__ int sign_diff(int a, int b) {
    return (a > b) - (a < b);
}

extern "C" __global__
void build_lbvh(
    const unsigned int* __restrict__ codes,
    int* __restrict__ left,
    int* __restrict__ right,
    int* __restrict__ parent,
    int* __restrict__ range_lo,
    int* __restrict__ range_hi,
    const int n)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i >= n - 1) return;

    // --- determine range [first, last] this internal node covers ---
    int d = sign_diff(delta_(codes, n, i, i + 1), delta_(codes, n, i, i - 1));
    int delta_min = delta_(codes, n, i, i - d);

    int l_max = 2;
    while (delta_(codes, n, i, i + l_max * d) > delta_min) {
        l_max <<= 1;
    }
    int l = 0;
    for (int t = l_max >> 1; t >= 1; t >>= 1) {
        if (delta_(codes, n, i, i + (l + t) * d) > delta_min) {
            l += t;
        }
    }
    int j = i + l * d;
    int first = (i < j) ? i : j;
    int last  = (i > j) ? i : j;

    // --- find the split position within [first, last] ---
    int common_prefix = delta_(codes, n, first, last);
    int split = first;
    int step = last - first;
    do {
        step = (step + 1) >> 1;
        int new_split = split + step;
        if (new_split < last) {
            if (delta_(codes, n, first, new_split) > common_prefix) {
                split = new_split;
            }
        }
    } while (step > 1);

    // --- assign children, mapping into the global id space ---
    int left_id  = (split     == first) ? split       : (n + split);
    int right_id = (split + 1 == last ) ? (split + 1) : (n + split + 1);

    left[i]      = left_id;
    right[i]     = right_id;
    range_lo[i]  = first;
    range_hi[i]  = last;

    int my_global = n + i;
    parent[left_id]  = my_global;
    parent[right_id] = my_global;
}
"""

_lbvh_kernel = cp.RawKernel(_LBVH_SRC, "build_lbvh")


class LBVH:
    """Container for an LBVH built from sorted Morton codes.

    Attributes
    ----------
    n        : number of leaves (particles)
    left, right : (n-1,) int32 — children global ids of each internal node
    parent   : (2n-1,) int32 — parent global id; -1 for root
    range_lo, range_hi : (n-1,) int32 — covered leaf-index range
    root     : the global id of the root (always == n)
    """

    def __init__(self, codes_sorted: cp.ndarray):
        n = int(codes_sorted.shape[0])
        assert codes_sorted.dtype == cp.uint32 and n >= 2
        self.n = n
        self.left = cp.empty(n - 1, dtype=cp.int32)
        self.right = cp.empty(n - 1, dtype=cp.int32)
        self.range_lo = cp.empty(n - 1, dtype=cp.int32)
        self.range_hi = cp.empty(n - 1, dtype=cp.int32)
        # parent indexed by global id (leaves: 0..n-1, internals: n..2n-2)
        self.parent = cp.full(2 * n - 1, -1, dtype=cp.int32)

        threads = 256
        blocks = (n - 1 + threads - 1) // threads
        _lbvh_kernel(
            (blocks,),
            (threads,),
            (
                codes_sorted,
                self.left,
                self.right,
                self.parent,
                self.range_lo,
                self.range_hi,
                cp.int32(n),
            ),
        )

    @property
    def root(self) -> int:
        return self.n

    def is_leaf(self, gid: cp.ndarray) -> cp.ndarray:
        return gid < self.n
