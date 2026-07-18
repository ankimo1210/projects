#pragma once
// Parallel merge sort rung 1: raw std::thread divide-and-conquer. One half
// goes to a spawned thread, the other is sorted in the current thread, then
// std::inplace_merge joins the runs (stable). The depth cutoff bounds total
// spawns at 2^depth - 1; the size cutoff hands small subranges to the
// sequential lab::merge_sort, whose per-call buffer makes concurrent calls
// safe. Spawning whole levels means effective parallelism is the smallest
// power of two >= the requested thread count.
#include <algorithm>
#include <functional>
#include <thread>

#include "parallel/tuning.hpp"
#include "sorting/merge.hpp"

namespace lab {

namespace detail {

inline int depth_for_threads(unsigned threads) {
    int depth = 0;
    while ((1u << depth) < threads) ++depth;
    return depth;  // smallest depth with 2^depth >= threads
}

template <class RandomIt, class Compare>
void thread_merge_impl(RandomIt first, RandomIt last, Compare comp, int depth) {
    const auto n = last - first;
    if (n < 2) return;
    if (depth <= 0 || n < kParallelSortCutoff) {
        merge_sort(first, last, comp);
        return;
    }
    const auto mid = first + n / 2;
    std::thread left(
        [first, mid, comp, depth] { thread_merge_impl(first, mid, comp, depth - 1); });
    thread_merge_impl(mid, last, comp, depth - 1);
    left.join();
    std::inplace_merge(first, mid, last, comp);
}

}  // namespace detail

// threads == 0 means std::thread::hardware_concurrency().
template <class RandomIt, class Compare = std::less<>>
void thread_merge_sort(RandomIt first, RandomIt last, Compare comp = {}, unsigned threads = 0) {
    if (threads == 0) threads = std::thread::hardware_concurrency();
    if (threads == 0) threads = 1;  // hardware_concurrency may report 0
    detail::thread_merge_impl(first, last, comp, detail::depth_for_threads(threads));
}

}  // namespace lab
