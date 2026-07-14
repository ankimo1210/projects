#pragma once
// Insertion sort, shift-based (moves, not swaps): O(n^2) worst, O(n + inversions)
// adaptive, stable. The fastest of the quadratic family on nearly-sorted input.
#include <functional>
#include <utility>

namespace lab {

template <class RandomIt, class Compare = std::less<>>
void insertion_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    if (last - first < 2) return;
    for (auto it = first + 1; it != last; ++it) {
        auto key = std::move(*it);  // lift the element out, shift the hole left
        auto hole = it;
        while (hole != first && comp(key, *(hole - 1))) {
            *hole = std::move(*(hole - 1));
            --hole;
        }
        *hole = std::move(key);
    }
}

}  // namespace lab
