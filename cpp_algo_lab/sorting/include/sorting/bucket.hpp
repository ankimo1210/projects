#pragma once
// Bucket sort: distribute into n buckets by scaled key, insertion-sort each
// bucket, concatenate. O(n) expected on uniform keys; degrades toward
// insertion sort when keys clump into few buckets. Stable as long as
// operator< is consistent with the key.
#include <algorithm>
#include <cstdint>
#include <iterator>
#include <utility>
#include <vector>

#include "sorting/insertion.hpp"
#include "sorting/keys.hpp"

namespace lab {

template <class RandomIt, class KeyFn = IntegralKey>
void bucket_sort(RandomIt first, RandomIt last, KeyFn key = {}) {
    const auto n = static_cast<std::size_t>(last - first);
    if (n < 2) return;
    std::uint64_t max_key = 0;
    for (auto it = first; it != last; ++it) max_key = std::max(max_key, key(*it));

    using T = typename std::iterator_traits<RandomIt>::value_type;
    std::vector<std::vector<T>> buckets(n);
    const long double scale =
        static_cast<long double>(n) / (static_cast<long double>(max_key) + 1.0L);
    for (auto it = first; it != last; ++it) {
        const auto b = static_cast<std::size_t>(static_cast<long double>(key(*it)) * scale);
        buckets[b].push_back(std::move(*it));
    }
    auto out = first;
    for (auto& b : buckets) {
        insertion_sort(b.begin(), b.end());
        out = std::move(b.begin(), b.end(), out);
    }
}

}  // namespace lab
