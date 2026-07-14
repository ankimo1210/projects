// Sorting benchmark: wall-clock times (plain int), operation counts
// (Counted<int>), and observed properties (stability probe) -> results/*.csv.
// Run from cpp_algo_lab/ (paths are relative). Full run takes a few minutes,
// dominated by the quadratic sorts at n=32768.
#include <algorithm>
#include <cstring>
#include <functional>
#include <iostream>
#include <string>
#include <vector>

#include "lab/counted.hpp"
#include "lab/csv.hpp"
#include "lab/datagen.hpp"
#include "lab/stability.hpp"
#include "lab/table.hpp"
#include "lab/timer.hpp"
#include "sorting/all.hpp"

namespace {

using IntVec = std::vector<int>;
using CountedVec = std::vector<lab::Counted<int>>;
using KeyIdxVec = std::vector<lab::KeyIdx>;

struct AlgoSpec {
    std::string name;
    std::string family;  // "n2" | "nlogn" | "linear"
    bool comparison_based = true;
    std::size_t n_cap = 1u << 20;
    std::function<void(IntVec&)> run_int;
    std::function<void(CountedVec&)> run_counted;
    std::function<void(KeyIdxVec&)> run_keyidx;

    // Trace hooks: run the algorithm on ints with an instrumented comparator /
    // key extractor. Exactly one of these is set.
    std::function<void(IntVec&, std::function<bool(const int&, const int&)>)> run_traced_comp;
    std::function<void(IntVec&, std::function<std::uint64_t(const int&)>)> run_traced_key;
};

// Key extractors for non-comparison sorts over wrapper types.
const auto kCountedKey = [](const lab::Counted<int>& c) {
    return lab::IntegralKey{}(c.value());
};

std::vector<AlgoSpec> make_registry() {
    std::vector<AlgoSpec> r;
    auto comparison = [&](std::string name, std::string family, std::size_t cap, auto fn) {
        AlgoSpec s{std::move(name), std::move(family), true, cap,
                   [fn](IntVec& v) { fn(v.begin(), v.end(), std::less<>{}); },
                   [fn](CountedVec& v) { fn(v.begin(), v.end(), std::less<>{}); },
                   [fn](KeyIdxVec& v) { fn(v.begin(), v.end(), std::less<>{}); },
                   nullptr, nullptr};
        s.run_traced_comp = [fn](IntVec& v, std::function<bool(const int&, const int&)> c) {
            fn(v.begin(), v.end(), c);
        };
        r.push_back(std::move(s));
    };
    auto keyed = [&](std::string name, auto fn) {
        AlgoSpec s{std::move(name), "linear", false, 1u << 20,
                   [fn](IntVec& v) { fn(v.begin(), v.end(), lab::IntegralKey{}); },
                   [fn](CountedVec& v) { fn(v.begin(), v.end(), kCountedKey); },
                   [fn](KeyIdxVec& v) { fn(v.begin(), v.end(), lab::KeyIdxKey{}); },
                   nullptr, nullptr};
        s.run_traced_key = [fn](IntVec& v, std::function<std::uint64_t(const int&)> k) {
            fn(v.begin(), v.end(), k);
        };
        r.push_back(std::move(s));
    };
    const std::size_t quad_cap = 32768;
    comparison("bubble", "n2", quad_cap,
               [](auto f, auto l, auto comp) { lab::bubble_sort(f, l, comp); });
    comparison("insertion", "n2", quad_cap,
               [](auto f, auto l, auto comp) { lab::insertion_sort(f, l, comp); });
    comparison("selection", "n2", quad_cap,
               [](auto f, auto l, auto comp) { lab::selection_sort(f, l, comp); });
    comparison("shell", "n2", 1u << 20,
               [](auto f, auto l, auto comp) { lab::shell_sort(f, l, comp); });
    comparison("merge", "nlogn", 1u << 20,
               [](auto f, auto l, auto comp) { lab::merge_sort(f, l, comp); });
    comparison("quick", "nlogn", 1u << 20,
               [](auto f, auto l, auto comp) { lab::quick_sort(f, l, comp); });
    comparison("heap", "nlogn", 1u << 20,
               [](auto f, auto l, auto comp) { lab::heap_sort(f, l, comp); });
    comparison("std_sort", "nlogn", 1u << 20,
               [](auto f, auto l, auto comp) { std::sort(f, l, comp); });
    comparison("std_stable_sort", "nlogn", 1u << 20,
               [](auto f, auto l, auto comp) { std::stable_sort(f, l, comp); });
    keyed("counting", [](auto f, auto l, auto k) { lab::counting_sort(f, l, k); });
    keyed("radix", [](auto f, auto l, auto k) { lab::radix_sort(f, l, k); });
    keyed("bucket", [](auto f, auto l, auto k) { lab::bucket_sort(f, l, k); });
    return r;
}

std::vector<std::size_t> sweep_for(const AlgoSpec& a, bool quick) {
    std::vector<std::size_t> base =
        quick ? std::vector<std::size_t>{256, 1024, 4096}
              : std::vector<std::size_t>{256,   1024,   4096,   16384,
                                         32768, 65536,  262144, 1048576};
    std::vector<std::size_t> out;
    for (std::size_t n : base)
        if (n <= a.n_cap) out.push_back(n);
    return out;
}

bool verify_sorted_permutation(const IntVec& sorted_out, IntVec reference) {
    std::sort(reference.begin(), reference.end());
    return sorted_out == reference;  // sorted AND a permutation of the input
}

void run_bench(bool quick) {
    const int repeats = quick ? 2 : 5;
    const std::uint32_t seed = 42;
    auto registry = make_registry();

    lab::CsvWriter times("results/sorting_times.csv",
                         {"algo", "family", "dist", "n", "repeats", "median_ms"});
    lab::CsvWriter ops("results/sorting_ops.csv",
                       {"algo", "family", "dist", "n", "comparisons", "moves", "swaps"});
    lab::CsvWriter props("results/sorting_props.csv",
                         {"algo", "family", "comparison_based", "stable_observed", "n_cap"});

    std::vector<std::vector<std::string>> summary_rows;
    for (const auto& a : registry) {
        const bool stable = lab::observed_stable(a.run_keyidx);
        props.write_row({a.name, a.family, a.comparison_based ? "yes" : "no",
                         stable ? "yes" : "no", lab::cell(a.n_cap)});
        summary_rows.push_back(
            {a.name, a.family, a.comparison_based ? "yes" : "no", stable ? "yes" : "no"});

        for (const lab::Dist d : lab::all_dists()) {
            for (const std::size_t n : sweep_for(a, quick)) {
                const IntVec data = lab::generate(d, n, seed);
                // Wall-clock: median over fresh copies.
                std::vector<double> ts;
                for (int r = 0; r < repeats; ++r) {
                    IntVec v = data;
                    ts.push_back(lab::time_ms([&] { a.run_int(v); }));
                    if (r == 0 && !verify_sorted_permutation(v, data)) {
                        std::cerr << "FATAL: " << a.name << " mis-sorted n=" << n
                                  << " dist=" << lab::dist_name(d) << "\n";
                        std::exit(1);
                    }
                }
                times.write_row({a.name, a.family, std::string(lab::dist_name(d)),
                                 lab::cell(n), lab::cell(repeats),
                                 lab::cell(lab::median(ts))});
                // Operation counts: one deterministic Counted run.
                CountedVec cv(data.begin(), data.end());
                lab::Counted<int>::reset_counters();
                a.run_counted(cv);
                const auto& c = lab::Counted<int>::counters();
                ops.write_row({a.name, a.family, std::string(lab::dist_name(d)),
                               lab::cell(n), lab::cell(c.comparisons), lab::cell(c.moves),
                               lab::cell(c.swaps)});
            }
        }
        std::cout << "done: " << a.name << "\n";
    }

    std::cout << "\nAlgorithm properties (observed):\n";
    lab::print_table({"algo", "family", "comparison", "stable"}, summary_rows);
    std::cout << "\nCSV written to results/sorting_{times,ops,props}.csv\n";
}

void run_traces() {
    constexpr std::size_t kTraceN = 256;
    constexpr std::size_t kMaxFrames = 120;
    const IntVec data = lab::generate(lab::Dist::random_uniform, kTraceN, 42);

    for (const auto& a : make_registry()) {
        if (a.name == "std_sort" || a.name == "std_stable_sort") continue;

        // Pass 1: count events (comparisons or key extractions).
        unsigned long long total = 0;
        {
            IntVec v = data;
            if (a.run_traced_comp)
                a.run_traced_comp(v, [&total](const int& x, const int& y) {
                    ++total;
                    return x < y;
                });
            else
                a.run_traced_key(v, [&total](const int& x) {
                    ++total;
                    return lab::IntegralKey{}(x);
                });
        }
        const unsigned long long interval = std::max<unsigned long long>(1, total / 119);

        // Pass 2: snapshot the array every `interval` events.
        IntVec v = data;
        std::vector<IntVec> frames;
        unsigned long long events = 0;
        auto maybe_snapshot = [&] {
            if (events % interval == 0 && frames.size() < kMaxFrames) frames.push_back(v);
            ++events;
        };
        if (a.run_traced_comp)
            a.run_traced_comp(v, [&](const int& x, const int& y) {
                maybe_snapshot();
                return x < y;
            });
        else
            a.run_traced_key(v, [&](const int& x) {
                maybe_snapshot();
                return lab::IntegralKey{}(x);
            });
        frames.push_back(v);  // final sorted state

        std::vector<std::string> header{"frame"};
        for (std::size_t i = 0; i < kTraceN; ++i) header.push_back("p" + std::to_string(i));
        lab::CsvWriter w("results/traces/trace_" + a.name + ".csv", header);
        for (std::size_t f = 0; f < frames.size(); ++f) {
            std::vector<std::string> row{lab::cell(f)};
            for (int x : frames[f]) row.push_back(lab::cell(x));
            w.write_row(row);
        }
        std::cout << "trace: " << a.name << " (" << frames.size() << " frames, " << total
                  << " events)\n";
    }
}

}  // namespace

int main(int argc, char** argv) {
    bool quick = false, trace = false;
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--quick") == 0) quick = true;
        if (std::strcmp(argv[i], "--trace") == 0) trace = true;
    }
    if (trace) {
        run_traces();
        return 0;
    }
    run_bench(quick);
    return 0;
}
