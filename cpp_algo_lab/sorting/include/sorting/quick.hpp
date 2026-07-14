#pragma once
// Quicksort: median-of-three pivot + Hoare partition, recursing into the
// smaller side first so stack depth stays O(log n). Average O(n log n); the
// median-of-three defuses sorted/reversed inputs, Hoare handles duplicates.
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

template <class RandomIt, class Compare>
RandomIt hoare_partition(RandomIt first, RandomIt last, Compare comp) {
    const auto mid = first + (last - first) / 2;
    const auto pivot = *median_of_three(first, mid, last - 1, comp);  // by value
    auto i = first;
    auto j = last - 1;
    while (true) {
        while (comp(*i, pivot)) ++i;
        while (comp(pivot, *j)) --j;
        if (i >= j) return j;
        std::iter_swap(i, j);
        ++i;
        --j;
    }
}

template <class RandomIt, class Compare>
void quick_sort_impl(RandomIt first, RandomIt last, Compare comp) {
    while (last - first > 1) {
        const auto p = hoare_partition(first, last, comp);
        // Recurse into the smaller half, loop on the larger one.
        if ((p + 1) - first < last - (p + 1)) {
            quick_sort_impl(first, p + 1, comp);
            first = p + 1;
        } else {
            quick_sort_impl(p + 1, last, comp);
            last = p + 1;
        }
    }
}

}  // namespace detail

template <class RandomIt, class Compare = std::less<>>
void quick_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    detail::quick_sort_impl(first, last, comp);
}

}  // namespace lab
