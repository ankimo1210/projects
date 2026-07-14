#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest/doctest.h"

#include <algorithm>
#include <functional>
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
