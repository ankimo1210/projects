#pragma once
// Top-down merge sort with one reusable buffer: O(n log n) always, O(n) extra
// space, stable (ties take the left run first).
#include <functional>
#include <iterator>
#include <utility>
#include <vector>

namespace lab {
namespace detail {

template <class RandomIt, class Buf, class Compare>
void merge_sort_impl(RandomIt first, RandomIt last, Buf& buf, Compare comp) {
    const auto n = last - first;
    if (n < 2) return;
    const auto mid = first + n / 2;
    merge_sort_impl(first, mid, buf, comp);
    merge_sort_impl(mid, last, buf, comp);

    buf.clear();
    auto l = first, r = mid;
    while (l != mid && r != last) {
        // Strictly-less from the right run keeps equal elements stable.
        if (comp(*r, *l)) {
            buf.push_back(std::move(*r));
            ++r;
        } else {
            buf.push_back(std::move(*l));
            ++l;
        }
    }
    for (; l != mid; ++l) buf.push_back(std::move(*l));
    for (; r != last; ++r) buf.push_back(std::move(*r));
    std::move(buf.begin(), buf.end(), first);
}

}  // namespace detail

template <class RandomIt, class Compare = std::less<>>
void merge_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    using T = typename std::iterator_traits<RandomIt>::value_type;
    std::vector<T> buf;
    buf.reserve(static_cast<std::size_t>(last - first));
    detail::merge_sort_impl(first, last, buf, comp);
}

}  // namespace lab
