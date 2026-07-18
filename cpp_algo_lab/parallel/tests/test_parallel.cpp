// Tests for the CPU parallel ladder: conformance against std::sort /
// sequential references across sizes, distributions and thread counts;
// stability of the parallel merge sorts; and the chunk-boundary planting
// tests for the parallelized search (Tasks 2-3 extend this file).
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest/doctest.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "lab/datagen.hpp"
#include "lab/stability.hpp"
#include "parallel/thread_merge.hpp"

TEST_CASE("depth_for_threads: smallest depth with 2^depth >= threads") {
    CHECK(lab::detail::depth_for_threads(1) == 0);
    CHECK(lab::detail::depth_for_threads(2) == 1);
    CHECK(lab::detail::depth_for_threads(3) == 2);
    CHECK(lab::detail::depth_for_threads(4) == 2);
    CHECK(lab::detail::depth_for_threads(16) == 4);
    CHECK(lab::detail::depth_for_threads(20) == 5);
}

TEST_CASE("thread_merge_sort: conformance vs std::sort") {
    const std::vector<std::size_t> sizes = {0, 1, 2, 3, 100, 4096};
    for (const lab::Dist d : lab::all_dists()) {
        for (const std::size_t n : sizes) {
            for (const unsigned threads : {1u, 2u, 4u, 8u, 16u}) {
                std::vector<int> v = lab::generate(d, n, 42);
                std::vector<int> want = v;
                std::sort(want.begin(), want.end());
                lab::thread_merge_sort(v.begin(), v.end(), std::less<>{}, threads);
                INFO("dist=" << lab::dist_name(d) << " n=" << n << " threads=" << threads);
                CHECK(v == want);
            }
        }
    }
    // Large enough to cross kParallelSortCutoff so threads really spawn.
    for (const unsigned threads : {1u, 4u, 16u}) {
        std::vector<int> v = lab::generate(lab::Dist::random_uniform, 200000, 42);
        std::vector<int> want = v;
        std::sort(want.begin(), want.end());
        lab::thread_merge_sort(v.begin(), v.end(), std::less<>{}, threads);
        CHECK(v == want);
    }
}

TEST_CASE("thread_merge_sort: stable (sequential base + inplace_merge are stable)") {
    // n=200000 crosses the cutoff, so the parallel path (spawn + inplace_merge)
    // is actually exercised, not just the sequential fallback.
    const bool stable = lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) {
            lab::thread_merge_sort(v.begin(), v.end(), std::less<>{}, 8);
        },
        200000, 7);
    CHECK(stable);
}

TEST_CASE("thread_merge_sort: custom comparator (descending)") {
    std::vector<int> v = lab::generate(lab::Dist::random_uniform, 50000, 42);
    std::vector<int> want = v;
    std::sort(want.begin(), want.end(), std::greater<>{});
    lab::thread_merge_sort(v.begin(), v.end(), std::greater<>{}, 4);
    CHECK(v == want);
}
