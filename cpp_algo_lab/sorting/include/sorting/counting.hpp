#pragma once
// Counting sort: O(n + k) where k = key range. No comparisons at all — the
// histogram + exclusive prefix sum + forward scatter make it stable. Only
// viable while k stays small; kMaxCountingRange guards the histogram size.
#include <algorithm>
#include <cstdint>
#include <iterator>
#include <stdexcept>
#include <utility>
#include <vector>

#include "sorting/keys.hpp"

namespace lab {

inline constexpr std::uint64_t kMaxCountingRange = std::uint64_t{1} << 26;  // 64M counters

template <class RandomIt, class KeyFn = IntegralKey>
void counting_sort(RandomIt first, RandomIt last, KeyFn key = {}) {
    const auto n = static_cast<std::size_t>(last - first);
    if (n < 2) return;
    std::uint64_t max_key = 0;
    for (auto it = first; it != last; ++it) max_key = std::max(max_key, key(*it));
    if (max_key >= kMaxCountingRange)
        throw std::length_error("counting_sort: key range too large");

    std::vector<std::size_t> count(static_cast<std::size_t>(max_key) + 1, 0);
    for (auto it = first; it != last; ++it) ++count[key(*it)];
    std::size_t sum = 0;  // exclusive prefix sum -> stable scatter positions
    for (auto& c : count) {
        const std::size_t old = c;
        c = sum;
        sum += old;
    }
    using T = typename std::iterator_traits<RandomIt>::value_type;
    std::vector<T> out(n);
    for (auto it = first; it != last; ++it) out[count[key(*it)]++] = std::move(*it);
    std::move(out.begin(), out.end(), first);
}

}  // namespace lab
