#pragma once
// LSD radix sort, base 256: O(passes * n) with passes = significant bytes of
// the max key. Stable (each pass is a stable counting sort by one byte).
// Writes back into the range after every pass so traces show the progress.
#include <algorithm>
#include <cstdint>
#include <iterator>
#include <utility>
#include <vector>

#include "sorting/keys.hpp"

namespace lab {

template <class RandomIt, class KeyFn = IntegralKey>
void radix_sort(RandomIt first, RandomIt last, KeyFn key = {}) {
    const auto n = static_cast<std::size_t>(last - first);
    if (n < 2) return;
    std::uint64_t max_key = 0;
    for (auto it = first; it != last; ++it) max_key = std::max(max_key, key(*it));

    using T = typename std::iterator_traits<RandomIt>::value_type;
    std::vector<T> out(n);
    for (int shift = 0; shift == 0 || (max_key >> shift) != 0; shift += 8) {
        std::size_t count[257] = {};  // count[b+1] trick -> exclusive prefix in place
        for (auto it = first; it != last; ++it)
            ++count[((key(*it) >> shift) & 0xFF) + 1];
        for (int b = 0; b < 256; ++b) count[b + 1] += count[b];
        for (auto it = first; it != last; ++it)
            out[count[(key(*it) >> shift) & 0xFF]++] = std::move(*it);
        std::move(out.begin(), out.end(), first);
    }
}

}  // namespace lab
