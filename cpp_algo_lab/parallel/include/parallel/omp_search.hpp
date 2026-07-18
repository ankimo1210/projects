#pragma once
// Search parallelization: embarrassingly parallel chunking. The n-m+1 start
// positions are split into `threads` contiguous ranges; chunk c scans the
// slice text.substr(lo_c, (hi_c-lo_c) + m-1). A slice of that length can
// only contain matches starting at slice offsets 0..hi_c-lo_c-1, so every
// match is found by exactly one chunk: no duplicates, no misses, no
// post-filtering -- correctness BY CONSTRUCTION. The classic off-by-one
// (forgetting the m-1 overlap tail) is exactly what the boundary-planting
// tests probe. Each chunk rebuilds the BMH shift table (m-1 stores): the
// honest price of shared-nothing parallelism, negligible for m << n/threads.
#include <cstddef>
#include <omp.h>
#include <string_view>
#include <vector>

#include "search/bmh.hpp"

namespace lab {

// threads <= 0 means the OpenMP default (all cores). Degenerate cases
// (empty pattern, pattern longer than text, one thread) delegate to the
// sequential implementation so the module conventions hold verbatim.
inline std::vector<std::size_t> omp_bmh_search(std::string_view text, std::string_view pattern,
                                               int threads = 0) {
    const std::size_t n = text.size(), m = pattern.size();
    if (threads <= 0) threads = omp_get_max_threads();
    if (m == 0 || m > n || threads == 1) return bmh_search(text, pattern);

    const std::size_t starts = n - m + 1;  // candidate start positions
    const std::size_t nchunks = static_cast<std::size_t>(threads);
    std::vector<std::vector<std::size_t>> local(nchunks);

#pragma omp parallel for schedule(static) num_threads(threads)
    for (std::size_t c = 0; c < nchunks; ++c) {
        const std::size_t lo = starts * c / nchunks;
        const std::size_t hi = starts * (c + 1) / nchunks;
        if (lo == hi) continue;  // more chunks than start positions
        const std::string_view slice = text.substr(lo, (hi - lo) + m - 1);
        std::vector<std::size_t> found = bmh_search(slice, pattern);
        for (std::size_t& p : found) p += lo;
        local[c] = std::move(found);
    }

    std::size_t total = 0;
    for (const auto& v : local) total += v.size();
    std::vector<std::size_t> out;
    out.reserve(total);
    for (auto& v : local) out.insert(out.end(), v.begin(), v.end());
    return out;
}

}  // namespace lab
