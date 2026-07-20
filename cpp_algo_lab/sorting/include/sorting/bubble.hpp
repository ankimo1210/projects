#pragma once
// Bubble sort with early exit: O(n^2) compares/swaps, O(n) best case (sorted),
// stable. Adjacent swaps only — the "swaps" counter is the story here.
#include <algorithm>
#include <functional>

namespace lab {

template <class RandomIt, class Compare = std::less<>>
void bubble_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    if (last - first < 2) return;
    for (auto end = last; end - first > 1; --end) {
        bool swapped = false;
        for (auto it = first; it + 1 != end; ++it) {
            if (comp(*(it + 1), *it)) {
                std::iter_swap(it, it + 1);
                swapped = true;
            }
        }
        if (!swapped) return;  // clean pass: already sorted
    }
}

}  // namespace lab
