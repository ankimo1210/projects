#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest/doctest.h"

TEST_CASE("smoke: doctest runs under sanitizers") {
    CHECK(1 + 1 == 2);
}

#include "lab/counted.hpp"

#include <algorithm>
#include <utility>
#include <vector>

TEST_CASE("Counted: comparisons are counted") {
    using C = lab::Counted<int>;
    C::reset_counters();
    C a{1}, b{2};
    CHECK(a < b);
    CHECK_FALSE(b < a);
    CHECK(a <= b);
    CHECK(b > a);
    CHECK(b >= a);
    CHECK(a == a);
    CHECK(a != b);
    CHECK(C::counters().comparisons == 7);
    CHECK(C::counters().moves == 0);
    CHECK(C::counters().swaps == 0);
}

TEST_CASE("Counted: moves and swaps are counted") {
    using C = lab::Counted<int>;
    C::reset_counters();
    C a{1};
    C b = a;             // copy ctor -> 1 move
    C c = std::move(a);  // move ctor -> 1 move
    b = c;               // copy assign -> 1 move
    c = std::move(b);    // move assign -> 1 move
    CHECK(C::counters().moves == 4);
    C x{1}, y{2};
    C::reset_counters();
    using std::swap;
    swap(x, y);          // ADL swap -> 1 swap, 0 moves
    CHECK(C::counters().swaps == 1);
    CHECK(C::counters().moves == 0);
    CHECK(x.value() == 2);
    CHECK(y.value() == 1);
}

TEST_CASE("Counted: works with std::sort") {
    using C = lab::Counted<int>;
    std::vector<C> v{C{3}, C{1}, C{2}};
    C::reset_counters();
    std::sort(v.begin(), v.end());
    CHECK(C::counters().comparisons > 0);
    CHECK(v[0].value() == 1);
    CHECK(v[1].value() == 2);
    CHECK(v[2].value() == 3);
}

#include "lab/datagen.hpp"

#include <set>

TEST_CASE("datagen: size, determinism, non-negative range") {
    for (lab::Dist d : lab::all_dists()) {
        CAPTURE(lab::dist_name(d));
        auto v1 = lab::generate(d, 1000, 42);
        auto v2 = lab::generate(d, 1000, 42);
        auto v3 = lab::generate(d, 1000, 43);
        CHECK(v1.size() == 1000);
        CHECK(v1 == v2);  // same seed -> same data
        if (d == lab::Dist::random_uniform) CHECK(v1 != v3);
        for (int x : v1) {
            CHECK(x >= 0);
            CHECK(x < 1000);
        }
        CHECK(lab::generate(d, 0, 42).empty());
    }
}

TEST_CASE("datagen: per-distribution shape") {
    auto sorted = lab::generate(lab::Dist::sorted_asc, 500, 1);
    CHECK(std::is_sorted(sorted.begin(), sorted.end()));

    auto rev = lab::generate(lab::Dist::reversed, 500, 1);
    CHECK(std::is_sorted(rev.rbegin(), rev.rend()));
    CHECK_FALSE(std::is_sorted(rev.begin(), rev.end()));

    auto few = lab::generate(lab::Dist::few_unique, 500, 1);
    std::set<int> uniq(few.begin(), few.end());
    CHECK(uniq.size() <= 10);

    auto nearly = lab::generate(lab::Dist::nearly_sorted, 500, 1);
    int in_order = 0;
    for (std::size_t i = 1; i < nearly.size(); ++i)
        if (nearly[i - 1] <= nearly[i]) ++in_order;
    CHECK(in_order >= 450);  // >= 90% adjacent pairs in order
    CHECK_FALSE(std::is_sorted(nearly.begin(), nearly.end()));
}
