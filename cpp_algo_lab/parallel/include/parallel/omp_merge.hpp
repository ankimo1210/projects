#pragma once
// Parallel merge sort rung 2: OpenMP tasks. Same recursion shape as the
// std::thread rung, but each half becomes a #pragma omp task handed to a
// worker pool: arbitrary thread counts work and the runtime load-balances.
// Locals referenced inside a task are firstprivate by default, so the
// iterators and comparator are copied into each task -- no dangling stack
// references. Must be compiled with -fopenmp (the Makefile's parallel
// targets are).
#include <algorithm>
#include <functional>
#include <omp.h>

#include "parallel/tuning.hpp"
#include "sorting/merge.hpp"

namespace lab {

namespace detail {

template <class RandomIt, class Compare>
void omp_merge_impl(RandomIt first, RandomIt last, Compare comp) {
    const auto n = last - first;
    if (n < 2) return;
    if (n < kParallelSortCutoff) {
        merge_sort(first, last, comp);
        return;
    }
    const auto mid = first + n / 2;
#pragma omp task
    omp_merge_impl(first, mid, comp);
    omp_merge_impl(mid, last, comp);
#pragma omp taskwait
    std::inplace_merge(first, mid, last, comp);
}

}  // namespace detail

// threads <= 0 means the OpenMP default (all cores).
template <class RandomIt, class Compare = std::less<>>
void omp_merge_sort(RandomIt first, RandomIt last, Compare comp = {}, int threads = 0) {
    if (last - first < 2) return;
    if (threads <= 0) threads = omp_get_max_threads();
#pragma omp parallel num_threads(threads)
#pragma omp single nowait
    detail::omp_merge_impl(first, last, comp);
}

}  // namespace lab
