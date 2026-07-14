#pragma once
// Quicksort: median-of-three pivot + Hoare-style partition (Sedgewick's
// variant: the pivot is swapped to the front, the scans exclude it, and it
// lands in its final slot). Recursing into the smaller side first keeps the
// stack depth O(log n). Average O(n log n); median-of-three defuses
// already-sorted input, but exactly-reversed input still degrades to
// Theta(n^2) here (see docs/sorting.md) -- the gap introsort's depth
// guard exists to close. Excluding the pivot from both partitions
// guarantees progress even on all-equal input.
#include <algorithm>
#include <functional>

namespace lab {
namespace detail {

template <class RandomIt, class Compare>
RandomIt median_of_three(RandomIt a, RandomIt b, RandomIt c, Compare comp) {
    if (comp(*b, *a)) {
        if (comp(*c, *b)) return b;
        return comp(*c, *a) ? c : a;
    }
    if (comp(*c, *a)) return a;
    return comp(*c, *b) ? c : b;
}

// Partition [first, last): returns p with *p in its final position,
// [first, p) <= pivot and (p, last) >= pivot.
template <class RandomIt, class Compare>
RandomIt hoare_partition(RandomIt first, RandomIt last, Compare comp) {
    const auto mid = first + (last - first) / 2;
    std::iter_swap(first, median_of_three(first, mid, last - 1, comp));
    const auto pivot = *first;  // copy: element positions move during the scans
    auto i = first;
    auto j = last;
    while (true) {
        do {
            ++i;
        } while (i != last && comp(*i, pivot));
        do {
            --j;
        } while (comp(pivot, *j));  // stops at first: *first == pivot
        if (i >= j) break;
        std::iter_swap(i, j);
    }
    std::iter_swap(first, j);  // pivot into its final slot
    return j;
}

template <class RandomIt, class Compare>
void quick_sort_impl(RandomIt first, RandomIt last, Compare comp) {
    while (last - first > 1) {
        const auto p = hoare_partition(first, last, comp);
        // Recurse into the smaller half, loop on the larger one. The pivot
        // at p is excluded from both, so each step strictly shrinks.
        if (p - first < last - (p + 1)) {
            quick_sort_impl(first, p, comp);
            first = p + 1;
        } else {
            quick_sort_impl(p + 1, last, comp);
            last = p;
        }
    }
}

}  // namespace detail

template <class RandomIt, class Compare = std::less<>>
void quick_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    detail::quick_sort_impl(first, last, comp);
}

}  // namespace lab
