#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest/doctest.h"

#include <algorithm>
#include <cstdint>
#include <functional>
#include <limits>
#include <vector>

#include "lab/counted.hpp"
#include "lab/datagen.hpp"
#include "lab/stability.hpp"
#include "sorting/bubble.hpp"
#include "sorting/insertion.hpp"
#include "sorting/selection.hpp"

// Generic conformance check: sorter(begin, end) must produce exactly what
// std::sort produces, across sizes, seeds and distributions.
template <class Sorter>
void check_sorts_like_std(Sorter sorter) {
    for (const std::size_t n : {0u, 1u, 2u, 3u, 16u, 1000u}) {
        for (const std::uint32_t seed : {1u, 2u}) {
            for (const lab::Dist d : lab::all_dists()) {
                CAPTURE(n);
                CAPTURE(seed);
                CAPTURE(lab::dist_name(d));
                auto v = lab::generate(d, n, seed);
                auto expected = v;
                std::sort(expected.begin(), expected.end());
                sorter(v.begin(), v.end());
                CHECK(v == expected);
            }
        }
    }
}

// Descending order via custom comparator.
template <class Sorter>
void check_custom_compare(Sorter sorter_desc) {
    auto v = lab::generate(lab::Dist::random_uniform, 1000, 3);
    auto expected = v;
    std::sort(expected.begin(), expected.end(), std::greater<>{});
    sorter_desc(v.begin(), v.end());
    CHECK(v == expected);
}

TEST_CASE("bubble_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::bubble_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::bubble_sort(f, l, std::greater<>{}); });
    CHECK(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::bubble_sort(v.begin(), v.end()); }));
}

TEST_CASE("bubble_sort: early exit on sorted input") {
    using C = lab::Counted<int>;
    std::vector<C> v;
    for (int i = 0; i < 100; ++i) v.emplace_back(i);
    C::reset_counters();
    lab::bubble_sort(v.begin(), v.end());
    CHECK(C::counters().comparisons == 99);  // one clean pass, then stop
    CHECK(C::counters().swaps == 0);
}

TEST_CASE("insertion_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::insertion_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::insertion_sort(f, l, std::greater<>{}); });
    CHECK(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::insertion_sort(v.begin(), v.end()); }));
}

TEST_CASE("insertion_sort: exact counts on sorted input") {
    using C = lab::Counted<int>;
    std::vector<C> v;
    for (int i = 0; i < 100; ++i) v.emplace_back(i);
    C::reset_counters();
    lab::insertion_sort(v.begin(), v.end());
    // Per element after the first: 1 failed comparison, key move out + move back.
    CHECK(C::counters().comparisons == 99);
    CHECK(C::counters().moves == 198);
    CHECK(C::counters().swaps == 0);
}

TEST_CASE("selection_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::selection_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::selection_sort(f, l, std::greater<>{}); });
    // Long-range swaps break ties: observed unstable on this probe input.
    CHECK_FALSE(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::selection_sort(v.begin(), v.end()); }));
}

#include "sorting/heap.hpp"
#include "sorting/merge.hpp"
#include "sorting/quick.hpp"

TEST_CASE("merge_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::merge_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::merge_sort(f, l, std::greater<>{}); });
    CHECK(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::merge_sort(v.begin(), v.end()); }));
}

TEST_CASE("quick_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::quick_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::quick_sort(f, l, std::greater<>{}); });
    CHECK_FALSE(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::quick_sort(v.begin(), v.end()); }));
}

TEST_CASE("quick_sort: adversarial inputs stay fast and correct") {
    // sorted / reversed / all-equal, n = 20000. With median-of-three and
    // smaller-side-first recursion this must finish quickly (no O(n^2) blowup,
    // no deep stack). The sanitizer build would catch stack overflow.
    for (const lab::Dist d : {lab::Dist::sorted_asc, lab::Dist::reversed}) {
        auto v = lab::generate(d, 20000, 1);
        auto expected = v;
        std::sort(expected.begin(), expected.end());
        lab::quick_sort(v.begin(), v.end());
        CHECK(v == expected);
    }
    std::vector<int> eq(20000, 7);
    auto v = eq;
    lab::quick_sort(v.begin(), v.end());
    CHECK(v == eq);
}

TEST_CASE("heap_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::heap_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::heap_sort(f, l, std::greater<>{}); });
    CHECK_FALSE(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::heap_sort(v.begin(), v.end()); }));
}

#include "sorting/all.hpp"

TEST_CASE("shell_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::shell_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::shell_sort(f, l, std::greater<>{}); });
    CHECK_FALSE(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::shell_sort(v.begin(), v.end()); }));
}

TEST_CASE("counting_sort / radix_sort / bucket_sort: sort like std::sort") {
    check_sorts_like_std([](auto f, auto l) { lab::counting_sort(f, l); });
    check_sorts_like_std([](auto f, auto l) { lab::radix_sort(f, l); });
    check_sorts_like_std([](auto f, auto l) { lab::bucket_sort(f, l); });
}

TEST_CASE("non-comparison sorts: stability via KeyFn") {
    auto by_key = lab::KeyIdxKey{};
    CHECK(lab::observed_stable([&](std::vector<lab::KeyIdx>& v) {
        lab::counting_sort(v.begin(), v.end(), by_key);
    }));
    CHECK(lab::observed_stable([&](std::vector<lab::KeyIdx>& v) {
        lab::radix_sort(v.begin(), v.end(), by_key);
    }));
    CHECK(lab::observed_stable([&](std::vector<lab::KeyIdx>& v) {
        lab::bucket_sort(v.begin(), v.end(), by_key);
    }));
}

TEST_CASE("non-comparison sorts: negative keys are rejected") {
    std::vector<int> v{3, -1, 2};
    CHECK_THROWS_AS(lab::counting_sort(v.begin(), v.end()), std::invalid_argument);
    CHECK_THROWS_AS(lab::radix_sort(v.begin(), v.end()), std::invalid_argument);
    CHECK_THROWS_AS(lab::bucket_sort(v.begin(), v.end()), std::invalid_argument);
}

TEST_CASE("counting_sort: oversized key range is rejected") {
    std::vector<int> v{0, 1 << 26};  // max_key + 1 exceeds kMaxCountingRange
    CHECK_THROWS_AS(lab::counting_sort(v.begin(), v.end()), std::length_error);
    // radix has no such limit: same data must sort fine.
    lab::radix_sort(v.begin(), v.end());
    CHECK(v[0] == 0);
    CHECK(v[1] == (1 << 26));
}

TEST_CASE("radix_sort: keys above 2^56 terminate without UB") {
    // Regression: the pass loop must stop at shift 64 instead of evaluating
    // max_key >> 64 (undefined behavior, would trip UBSan).
    std::vector<long long> v{3LL << 56, 1LL, 1LL << 40, 0LL};
    lab::radix_sort(v.begin(), v.end());
    CHECK(std::is_sorted(v.begin(), v.end()));
}

TEST_CASE("counting_sort: guard rejects huge key ranges without wrap-around") {
    // A key of 2^64-1 makes max_key+1 wrap to 0, which slipped past the old
    // `max_key + 1 > kMaxCountingRange` guard and then indexed out of bounds.
    std::vector<int> v{1, 0};
    const auto huge_key = [](const int& x) {
        return x ? std::numeric_limits<std::uint64_t>::max() : std::uint64_t{0};
    };
    CHECK_THROWS_AS(lab::counting_sort(v.begin(), v.end(), huge_key), std::length_error);
}

TEST_CASE("non-comparison sorts accept unsigned element types") {
    std::vector<unsigned> v{5u, 3u, 9u, 1u, 3u};
    std::vector<unsigned> want = v;
    std::sort(want.begin(), want.end());
    SUBCASE("counting") {
        lab::counting_sort(v.begin(), v.end());
        CHECK(v == want);
    }
    SUBCASE("radix") {
        lab::radix_sort(v.begin(), v.end());
        CHECK(v == want);
    }
    SUBCASE("bucket") {
        lab::bucket_sort(v.begin(), v.end());
        CHECK(v == want);
    }
}
