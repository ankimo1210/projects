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
#include "lab/textgen.hpp"
#include "parallel/omp_merge.hpp"
#include "parallel/omp_search.hpp"
#include "parallel/par_stl.hpp"
#include "parallel/thread_merge.hpp"
#include "search/bmh.hpp"
#include "search/naive.hpp"

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

TEST_CASE("omp_merge_sort: conformance vs std::sort (incl. odd thread counts)") {
    const std::vector<std::size_t> sizes = {0, 1, 2, 3, 100, 4096};
    for (const lab::Dist d : lab::all_dists()) {
        for (const std::size_t n : sizes) {
            for (const int threads : {1, 2, 3, 5, 8, 20}) {
                std::vector<int> v = lab::generate(d, n, 42);
                std::vector<int> want = v;
                std::sort(want.begin(), want.end());
                lab::omp_merge_sort(v.begin(), v.end(), std::less<>{}, threads);
                INFO("dist=" << lab::dist_name(d) << " n=" << n << " threads=" << threads);
                CHECK(v == want);
            }
        }
    }
    for (const int threads : {1, 3, 20}) {
        std::vector<int> v = lab::generate(lab::Dist::random_uniform, 200000, 42);
        std::vector<int> want = v;
        std::sort(want.begin(), want.end());
        lab::omp_merge_sort(v.begin(), v.end(), std::less<>{}, threads);
        CHECK(v == want);
    }
}

TEST_CASE("omp_merge_sort: stable") {
    const bool stable = lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) {
            lab::omp_merge_sort(v.begin(), v.end(), std::less<>{}, 8);
        },
        200000, 7);
    CHECK(stable);
}

TEST_CASE("par_stl_sort: conformance vs std::sort") {
    for (const std::size_t n : {std::size_t{0}, std::size_t{1}, std::size_t{1000},
                                std::size_t{100000}}) {
        std::vector<int> v = lab::generate(lab::Dist::random_uniform, n, 42);
        std::vector<int> want = v;
        std::sort(want.begin(), want.end());
        lab::par_stl_sort(v.begin(), v.end());
        CHECK(v == want);
    }
    std::vector<int> v = lab::generate(lab::Dist::random_uniform, 50000, 42);
    std::vector<int> want = v;
    std::sort(want.begin(), want.end(), std::greater<>{});
    lab::par_stl_sort(v.begin(), v.end(), std::greater<>{});
    CHECK(v == want);
}

TEST_CASE("omp_bmh_search: agrees with sequential bmh on generated corpora") {
    for (const lab::Text t : lab::all_texts()) {
        for (const std::size_t n : {std::size_t{1}, std::size_t{64}, std::size_t{4096},
                                    std::size_t{65536}}) {
            const std::string text = lab::generate_text(t, n, 42);
            for (const std::size_t m : {std::size_t{1}, std::size_t{4}, std::size_t{16},
                                        std::size_t{64}}) {
                if (m > n) continue;
                const std::string pattern = lab::pattern_for(t, text, m, 42);
                const auto ref = lab::bmh_search(text, pattern);
                for (const int threads : {1, 2, 3, 5, 8, 20}) {
                    INFO("text=" << lab::text_name(t) << " n=" << n << " m=" << m
                                 << " threads=" << threads);
                    CHECK(lab::omp_bmh_search(text, pattern, threads) == ref);
                }
            }
        }
    }
}

TEST_CASE("omp_bmh_search: matches straddling every chunk boundary are found") {
    // Plant the pattern at start positions that straddle each internal chunk
    // boundary (b-(m-1): maximal straddle; b-1: one char before; b: first
    // owned start). The chunk arithmetic here mirrors the implementation's
    // lo_c = starts*c/threads split on purpose -- if the implementation's
    // split changes, this test must be updated with it.
    const std::string pattern = "NEEDLE";
    const std::size_t m = pattern.size();
    for (const int threads : {2, 3, 4, 7, 16}) {
        const std::size_t n = 1000;
        std::string text(n, 'x');
        const std::size_t starts = n - m + 1;
        const auto nchunks = static_cast<std::size_t>(threads);
        std::vector<std::size_t> planted;
        for (std::size_t c = 1; c < nchunks; ++c) {
            const std::size_t b = starts * c / nchunks;  // first start owned by chunk c
            // b >= starts/16 = 62 > m-1 here, so b-(m-1) cannot underflow.
            for (const std::size_t pos : {b - (m - 1), b - 1, b}) {
                if (pos + m <= n && (planted.empty() || pos >= planted.back() + m))
                    planted.push_back(pos);
            }
        }
        for (const std::size_t pos : planted) text.replace(pos, m, pattern);
        const auto expected = lab::naive_search(text, pattern);
        REQUIRE(expected == planted);  // construction sanity: exactly the planted set
        INFO("threads=" << threads);
        CHECK(lab::omp_bmh_search(text, pattern, threads) == expected);
    }
}

TEST_CASE("omp_bmh_search: overlapping matches across boundaries") {
    // All-'a' text with pattern "aaa": every start position matches, so any
    // dropped or duplicated boundary position changes the result.
    const std::string text(1000, 'a');
    const auto ref = lab::naive_search(text, "aaa");
    CHECK(ref.size() == 998);
    for (const int threads : {2, 3, 7, 20}) {
        INFO("threads=" << threads);
        CHECK(lab::omp_bmh_search(text, "aaa", threads) == ref);
    }
}

TEST_CASE("omp_bmh_search: module conventions hold for every thread count") {
    using Occ = std::vector<std::size_t>;
    for (const int threads : {1, 8}) {
        CHECK(lab::omp_bmh_search("abc", "", threads) == Occ{0, 1, 2, 3});
        CHECK(lab::omp_bmh_search("", "", threads) == Occ{0});
        CHECK(lab::omp_bmh_search("", "a", threads).empty());
        CHECK(lab::omp_bmh_search("ab", "abc", threads).empty());
        CHECK(lab::omp_bmh_search("abc", "abc", threads) == Occ{0});
        CHECK(lab::omp_bmh_search("xxab", "ab", threads) == Occ{2});
        CHECK(lab::omp_bmh_search("banana", "a", threads) == Occ{1, 3, 5});
    }
    // More threads than candidate start positions: empty chunks must be fine.
    CHECK(lab::omp_bmh_search("needle", "needle", 20) == Occ{0});
}
