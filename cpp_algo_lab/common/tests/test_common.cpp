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

TEST_CASE("datagen: dist_name returns exact CSV keys") {
    CHECK(lab::dist_name(lab::Dist::random_uniform) == "random");
    CHECK(lab::dist_name(lab::Dist::sorted_asc) == "sorted");
    CHECK(lab::dist_name(lab::Dist::reversed) == "reversed");
    CHECK(lab::dist_name(lab::Dist::nearly_sorted) == "nearly_sorted");
    CHECK(lab::dist_name(lab::Dist::few_unique) == "few_unique");
}

#include "lab/csv.hpp"
#include "lab/stability.hpp"
#include "lab/table.hpp"
#include "lab/timer.hpp"

#include <filesystem>
#include <fstream>
#include <sstream>

TEST_CASE("timer: median") {
    CHECK(lab::median({3.0, 1.0, 2.0}) == 2.0);
    CHECK(lab::median({4.0, 1.0, 3.0, 2.0}) == 2.5);
    CHECK_THROWS_AS(lab::median({}), std::invalid_argument);
    volatile long sink = 0;
    const double ms = lab::time_ms([&] {
        for (long i = 0; i < 100000; ++i) sink = sink + i;
    });
    CHECK(ms >= 0.0);
}

TEST_CASE("csv: writes header and rows, creates parent dirs") {
    namespace fs = std::filesystem;
    const fs::path p = fs::temp_directory_path() / "cpp_algo_lab_test" / "out.csv";
    fs::remove_all(p.parent_path());
    {
        lab::CsvWriter w(p, {"algo", "n", "ms"});
        w.write_row({"bubble", lab::cell(256), lab::cell(1.5)});
    }
    std::ifstream in(p);
    std::string l1, l2;
    std::getline(in, l1);
    std::getline(in, l2);
    CHECK(l1 == "algo,n,ms");
    CHECK(l2 == "bubble,256,1.5");
    fs::remove_all(p.parent_path());
}

TEST_CASE("table: aligned output") {
    std::ostringstream os;
    lab::print_table({"algo", "ms"}, {{"bubble", "12.5"}, {"quick", "0.8"}}, os);
    const std::string s = os.str();
    CHECK(s.find("algo") != std::string::npos);
    CHECK(s.find("bubble") != std::string::npos);
    // header separator present
    CHECK(s.find("---") != std::string::npos);
}

TEST_CASE("stability probe: detects stable and unstable sorts") {
    // std::stable_sort must be observed stable.
    CHECK(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { std::stable_sort(v.begin(), v.end()); }));
    // A deliberately tie-reversing sort must be observed unstable.
    CHECK_FALSE(lab::observed_stable([](std::vector<lab::KeyIdx>& v) {
        std::sort(v.begin(), v.end(), [](const lab::KeyIdx& a, const lab::KeyIdx& b) {
            if (a.key != b.key) return a.key < b.key;
            return a.idx > b.idx;  // reverse ties
        });
    }));
}
