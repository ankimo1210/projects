// CPU parallel ladder benchmark -> results/parallel_sort.csv and
// results/parallel_search.csv. Sort: fixed workload n=2^24 random ints,
// thread sweep per rung (thread_merge only at powers of two -- its
// divide-and-conquer spawns whole levels). Search: n=2^26 chars (english and
// dna), m=16, thread sweep for the OpenMP chunked BMH. Every configuration's
// output is verified against the sequential reference on its first repeat.
// Run from cpp_algo_lab/ on an otherwise idle machine. Full run ~2-3 min.
#include <algorithm>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

#include "lab/csv.hpp"
#include "lab/datagen.hpp"
#include "lab/table.hpp"
#include "lab/textgen.hpp"
#include "lab/timer.hpp"
#include "parallel/all.hpp"
#include "search/bmh.hpp"

namespace {

using Summary = std::vector<std::vector<std::string>>;

void run_sort_bench(bool quick, lab::CsvWriter& csv, Summary& summary) {
    const std::size_t n = quick ? (std::size_t{1} << 20) : (std::size_t{1} << 24);
    const int repeats = quick ? 2 : 5;
    const std::vector<int> data = lab::generate(lab::Dist::random_uniform, n, 42);
    std::vector<int> reference = data;
    std::sort(reference.begin(), reference.end());

    struct Config {
        std::string algo;
        int threads;
        std::function<void(std::vector<int>&)> run;
    };
    std::vector<Config> configs;
    configs.push_back({"merge_seq", 1,
                       [](std::vector<int>& v) { lab::merge_sort(v.begin(), v.end()); }});
    configs.push_back({"std_sort_seq", 1,
                       [](std::vector<int>& v) { std::sort(v.begin(), v.end()); }});
    for (const unsigned t : quick ? std::vector<unsigned>{1, 4}
                                  : std::vector<unsigned>{1, 2, 4, 8, 16})
        configs.push_back({"thread_merge", static_cast<int>(t), [t](std::vector<int>& v) {
                               lab::thread_merge_sort(v.begin(), v.end(), std::less<>{}, t);
                           }});
    for (const int t : quick ? std::vector<int>{1, 4}
                             : std::vector<int>{1, 2, 4, 6, 8, 12, 16, 20})
        configs.push_back({"omp_merge", t, [t](std::vector<int>& v) {
                               lab::omp_merge_sort(v.begin(), v.end(), std::less<>{}, t);
                           }});
    // threads=0 in the CSV means "library default (all cores)" -- par-STL's
    // thread count is the library's business (no TBB headers vendored).
    configs.push_back({"par_stl", 0,
                       [](std::vector<int>& v) { lab::par_stl_sort(v.begin(), v.end()); }});

    for (const auto& c : configs) {
        std::vector<double> ts;
        for (int r = 0; r < repeats; ++r) {
            std::vector<int> v = data;
            ts.push_back(lab::time_ms([&] { c.run(v); }));
            if (r == 0 && v != reference) {
                std::cerr << "FATAL: " << c.algo << " threads=" << c.threads << " mis-sorted\n";
                std::exit(1);
            }
        }
        const double med = lab::median(ts);
        csv.write_row({c.algo, lab::cell(c.threads), lab::cell(n), lab::cell(repeats),
                       lab::cell(med)});
        summary.push_back({"sort/" + c.algo, lab::cell(c.threads), lab::cell(med)});
        std::cout << "sort " << c.algo << " t=" << c.threads << ": " << med << " ms\n";
    }
}

void run_search_bench(bool quick, lab::CsvWriter& csv, Summary& summary) {
    const std::size_t n = quick ? (std::size_t{1} << 22) : (std::size_t{1} << 26);
    const std::size_t m = 16;
    const int repeats = quick ? 2 : 5;
    for (const lab::Text t : {lab::Text::english_like, lab::Text::dna}) {
        const std::string text = lab::generate_text(t, n, 42);
        const std::string pattern = lab::pattern_for(t, text, m, 42);
        const std::vector<std::size_t> reference = lab::bmh_search(text, pattern);

        struct Config {
            std::string algo;
            int threads;
        };
        std::vector<Config> configs{{"bmh_seq", 1}};
        for (const int th : quick ? std::vector<int>{1, 4}
                                  : std::vector<int>{1, 2, 4, 6, 8, 12, 16, 20})
            configs.push_back({"omp_bmh", th});

        for (const auto& c : configs) {
            std::vector<double> ts;
            for (int r = 0; r < repeats; ++r) {
                std::vector<std::size_t> occ;
                ts.push_back(lab::time_ms([&] {
                    occ = c.algo == "bmh_seq" ? lab::bmh_search(text, pattern)
                                              : lab::omp_bmh_search(text, pattern, c.threads);
                }));
                if (r == 0 && occ != reference) {
                    std::cerr << "FATAL: " << c.algo << " threads=" << c.threads
                              << " disagrees with sequential bmh (text=" << lab::text_name(t)
                              << ")\n";
                    std::exit(1);
                }
            }
            const double med = lab::median(ts);
            csv.write_row({c.algo, std::string(lab::text_name(t)), lab::cell(c.threads),
                           lab::cell(n), lab::cell(m), lab::cell(repeats), lab::cell(med),
                           lab::cell(reference.size())});
            summary.push_back({"search/" + c.algo + "/" + std::string(lab::text_name(t)),
                               lab::cell(c.threads), lab::cell(med)});
            std::cout << "search " << c.algo << " " << lab::text_name(t)
                      << " t=" << c.threads << ": " << med << " ms\n";
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    bool quick = false;
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "--quick") == 0) quick = true;

    lab::CsvWriter sort_csv("results/parallel_sort.csv",
                            {"algo", "threads", "n", "repeats", "median_ms"});
    lab::CsvWriter search_csv("results/parallel_search.csv",
                              {"algo", "text", "threads", "n", "m", "repeats", "median_ms",
                               "occurrences"});
    Summary summary;
    run_sort_bench(quick, sort_csv, summary);
    run_search_bench(quick, search_csv, summary);
    std::cout << "\nSummary (median ms):\n";
    lab::print_table({"config", "threads", "median_ms"}, summary);
    std::cout << "\nCSV written to results/parallel_{sort,search}.csv\n";
    return 0;
}
