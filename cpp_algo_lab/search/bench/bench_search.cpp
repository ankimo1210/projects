// Search benchmark: wall-clock times for the 4 own implementations plus 3
// standard-library baselines, and elementary-operation counts for the own
// ones -> results/search_*.csv. Two sweeps: text length n (m=16 fixed) and
// pattern length m 4..1024 (n=2^20 fixed). The timed lambda includes the
// occurrence-vector allocation: returning every match is part of the job.
// Run from cpp_algo_lab/. Full run takes ~2-3 minutes.
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

#include "lab/csv.hpp"
#include "lab/table.hpp"
#include "lab/textgen.hpp"
#include "lab/timer.hpp"
#include "search/all.hpp"

namespace {

using Occurrences = std::vector<std::size_t>;

struct SearchAlgo {
    std::string name;
    std::function<Occurrences(std::string_view, std::string_view)> run;
    // Null for the std baselines: they cannot be instrumented.
    std::function<lab::SearchStats(std::string_view, std::string_view)> run_counted;
};

std::vector<SearchAlgo> make_registry() {
    return {
        {"naive", lab::naive_search, lab::naive_search_counted},
        {"kmp", lab::kmp_search, lab::kmp_search_counted},
        {"bmh", lab::bmh_search, lab::bmh_search_counted},
        {"rabin_karp", lab::rabin_karp_search, lab::rabin_karp_search_counted},
        {"sv_find", lab::sv_find_search, nullptr},
        {"std_bmh", lab::std_bmh_search, nullptr},
        {"std_bm", lab::std_bm_search, nullptr},
    };
}

struct SweepPoint {
    std::size_t n, m;
};

void run_sweep(const std::string& sweep_name, lab::CsvWriter& times, lab::CsvWriter& ops,
               const std::vector<SweepPoint>& points, int repeats,
               std::vector<std::vector<std::string>>* summary_rows, std::size_t summary_n,
               std::size_t summary_m) {
    const auto registry = make_registry();
    for (const lab::Text t : lab::all_texts()) {
        for (const auto [n, m] : points) {
            const std::string text = lab::generate_text(t, n, 42);
            const std::string pattern = lab::pattern_for(t, text, m, 42);
            const Occurrences reference = lab::naive_search(text, pattern);
            for (const auto& a : registry) {
                std::vector<double> ts;
                for (int r = 0; r < repeats; ++r) {
                    Occurrences occ;
                    ts.push_back(lab::time_ms([&] { occ = a.run(text, pattern); }));
                    if (r == 0 && occ != reference) {
                        std::cerr << "FATAL: " << a.name << " disagrees with naive (text="
                                  << lab::text_name(t) << " n=" << n << " m=" << m << ")\n";
                        std::exit(1);
                    }
                }
                const double med = lab::median(ts);
                times.write_row({a.name, std::string(lab::text_name(t)), lab::cell(n),
                                 lab::cell(m), lab::cell(repeats), lab::cell(med),
                                 lab::cell(reference.size())});
                if (a.run_counted) {
                    const lab::SearchStats st = a.run_counted(text, pattern);
                    ops.write_row({a.name, std::string(lab::text_name(t)), sweep_name,
                                   lab::cell(n), lab::cell(m),
                                   lab::cell(st.occurrences.size()), lab::cell(st.pre_ops),
                                   lab::cell(st.text_reads), lab::cell(st.char_comparisons)});
                }
                if (summary_rows != nullptr && n == summary_n && m == summary_m)
                    summary_rows->push_back({std::string(lab::text_name(t)), a.name,
                                             lab::cell(med), lab::cell(reference.size())});
            }
        }
        std::cout << "done: " << lab::text_name(t) << " (" << sweep_name << " sweep)\n";
    }
}

void run_bench(bool quick) {
    const int repeats = quick ? 2 : 5;
    lab::CsvWriter times_n("results/search_times_n.csv",
                           {"algo", "text", "n", "m", "repeats", "median_ms", "occurrences"});
    lab::CsvWriter times_m("results/search_times_m.csv",
                           {"algo", "text", "n", "m", "repeats", "median_ms", "occurrences"});
    lab::CsvWriter ops("results/search_ops.csv",
                       {"algo", "text", "sweep", "n", "m", "occurrences", "pre_ops",
                        "text_reads", "char_comparisons"});

    const std::size_t fixed_m = 16;
    const std::size_t fixed_n = quick ? 65536 : (std::size_t{1} << 20);
    std::vector<SweepPoint> n_points, m_points;
    for (const std::size_t n :
         quick ? std::vector<std::size_t>{4096, 65536}
               : std::vector<std::size_t>{4096, 16384, 65536, 262144, 1048576, 4194304})
        n_points.push_back({n, fixed_m});
    for (const std::size_t m :
         quick ? std::vector<std::size_t>{4, 32}
               : std::vector<std::size_t>{4, 8, 16, 32, 64, 128, 256, 512, 1024})
        m_points.push_back({fixed_n, m});
    const std::size_t summary_m = quick ? 4 : fixed_m;

    std::vector<std::vector<std::string>> summary_rows;
    run_sweep("n", times_n, ops, n_points, repeats, nullptr, 0, 0);
    run_sweep("m", times_m, ops, m_points, repeats, &summary_rows, fixed_n, summary_m);

    std::cout << "\nMedian time at n=" << fixed_n << ", m=" << summary_m << ":\n";
    lab::print_table({"text", "algo", "median_ms", "occurrences"}, summary_rows);
    std::cout << "\nCSV written to results/search_{times_n,times_m,ops}.csv\n";
}

}  // namespace

int main(int argc, char** argv) {
    bool quick = false;
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "--quick") == 0) quick = true;
    run_bench(quick);
    return 0;
}
