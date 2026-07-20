#pragma once
// Parallel merge sort rung 1: raw std::thread divide-and-conquer. One half
// goes to a spawned thread, the other is sorted in the current thread, then
// std::inplace_merge joins the runs (stable). The depth cutoff bounds total
// spawns at 2^depth - 1; the size cutoff hands small subranges to the
// sequential lab::merge_sort, whose per-call buffer makes concurrent calls
// safe. Spawning whole levels means effective parallelism is the smallest
// power of two >= the requested thread count.
#include <algorithm>
#include <bit>
#include <exception>
#include <functional>
#include <thread>

#include "parallel/tuning.hpp"
#include "sorting/merge.hpp"

namespace lab {

namespace detail {

inline int depth_for_threads(unsigned threads) {
    if (threads <= 1) return 0;
    return static_cast<int>(std::bit_width(threads - 1));
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
    // jthread provides RAII join if the current thread throws. Exceptions in
    // the spawned branch cannot cross a thread boundary, so capture and
    // rethrow them after the explicit join.
    std::exception_ptr left_error;
    std::jthread left([first, mid, comp, depth, &left_error] {
        try {
            thread_merge_impl(first, mid, comp, depth - 1);
        } catch (...) {
            left_error = std::current_exception();
        }
    });
    thread_merge_impl(mid, last, comp, depth - 1);
    left.join();
    if (left_error) std::rethrow_exception(left_error);
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
