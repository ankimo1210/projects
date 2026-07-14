#pragma once
// Heap sort with a hand-written sift-down: O(n log n) worst case, in-place,
// not stable. Build max-heap bottom-up (O(n)), then pop the max n times.
#include <algorithm>
#include <cstddef>
#include <functional>

namespace lab {
namespace detail {

template <class RandomIt, class Compare>
void sift_down(RandomIt first, std::size_t size, std::size_t root, Compare comp) {
    while (true) {
        std::size_t child = 2 * root + 1;
        if (child >= size) return;
        if (child + 1 < size && comp(first[child], first[child + 1])) ++child;
        if (!comp(first[root], first[child])) return;
        std::iter_swap(first + root, first + child);
        root = child;
    }
}

}  // namespace detail

template <class RandomIt, class Compare = std::less<>>
void heap_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    const auto n = static_cast<std::size_t>(last - first);
    if (n < 2) return;
    for (std::size_t i = n / 2; i-- > 0;) detail::sift_down(first, n, i, comp);
    for (std::size_t s = n - 1; s > 0; --s) {
        std::iter_swap(first, first + s);  // move current max to its final slot
        detail::sift_down(first, s, 0, comp);
    }
}

}  // namespace lab
