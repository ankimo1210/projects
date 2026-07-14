#pragma once
// Shell sort with the Ciura gap sequence (extended by x2.25): gapped insertion
// sort, subquadratic in practice (~n^1.3), not stable. The bridge between the
// quadratic family and the O(n log n) family.
#include <functional>
#include <iterator>
#include <utility>
#include <vector>

namespace lab {

template <class RandomIt, class Compare = std::less<>>
void shell_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    using diff_t = typename std::iterator_traits<RandomIt>::difference_type;
    const diff_t n = last - first;
    if (n < 2) return;
    // Ciura (2001) empirically best-known prefix, then *2.25.
    std::vector<diff_t> gaps{1, 4, 10, 23, 57, 132, 301, 701, 1750};
    while (gaps.back() < n / 2) gaps.push_back(gaps.back() * 9 / 4);
    for (auto g = gaps.rbegin(); g != gaps.rend(); ++g) {
        const diff_t gap = *g;
        if (gap >= n) continue;
        for (auto it = first + gap; it != last; ++it) {
            auto key = std::move(*it);
            auto hole = it;
            while (hole - first >= gap && comp(key, *(hole - gap))) {
                *hole = std::move(*(hole - gap));
                hole -= gap;
            }
            *hole = std::move(key);
        }
    }
}

}  // namespace lab
