#pragma once
// Selection sort: always ~n^2/2 comparisons but only O(n) swaps — the mirror
// image of bubble sort's cost profile. Not stable (long-range swaps).
#include <algorithm>
#include <functional>

namespace lab {

template <class RandomIt, class Compare = std::less<>>
void selection_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    if (last - first < 2) return;
    for (auto it = first; it + 1 != last; ++it) {
        auto min_it = it;
        for (auto j = it + 1; j != last; ++j)
            if (comp(*j, *min_it)) min_it = j;
        if (min_it != it) std::iter_swap(it, min_it);
    }
}

}  // namespace lab
