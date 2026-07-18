// CPU parallel ladder benchmark -> results/parallel_sort.csv and
// results/parallel_search.csv. Sort: fixed workload n=2^24 random ints,
// thread sweep per rung (thread_merge only at powers of two -- its
// divide-and-conquer spawns whole levels). Search: n=2^26 chars (english and
// dna), m=16, thread sweep for the OpenMP chunked BMH. Configurations get one
// warm-up, run in shuffled order, and are verified on every timed repeat.
// Full results are staged before replacing canonical CSVs; --quick writes only
// under build/. Run from cpp_algo_lab/ on an otherwise idle machine.
#include <algorithm>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <functional>
#include <iostream>
#include <numeric>
#include <omp.h>
#include <random>
#include <string>
#include <string_view>
#include <utility>
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

double median_absolute_deviation(const std::vector<double>& samples) {
    const double med = lab::median(samples);
    std::vector<double> deviations;
    deviations.reserve(samples.size());
    for (const double value : samples)
        deviations.push_back(value >= med ? value - med : med - value);
    return lab::median(std::move(deviations));
}

std::vector<std::size_t> shuffled_order(std::size_t size, int repeat) {
    std::vector<std::size_t> order(size);
    std::iota(order.begin(), order.end(), 0);
    std::mt19937 rng(42u + static_cast<unsigned>(repeat));
    std::shuffle(order.begin(), order.end(), rng);
    return order;
}

void require_openmp_team_size(int requested) {
    int actual = 0;
#pragma omp parallel num_threads(requested)
#pragma omp single
    actual = omp_get_num_threads();
    if (actual != requested) {
        std::cerr << "FATAL: requested " << requested << " OpenMP threads, got " << actual
                  << '\n';
        std::exit(1);
    }
}

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
                             : std::vector<int>{1, 2, 4, 6, 8, 12, 16, 20}) {
        require_openmp_team_size(t);
        configs.push_back({"omp_merge", t, [t](std::vector<int>& v) {
                               lab::omp_merge_sort(v.begin(), v.end(), std::less<>{}, t);
                           }});
    }
    // threads=0 in the CSV means "library default (all cores)" -- par-STL's
    // thread count is the library's business (no TBB headers vendored).
    configs.push_back({"par_stl", 0,
                       [](std::vector<int>& v) { lab::par_stl_sort(v.begin(), v.end()); }});

    // Warm every implementation (including runtime thread pools) before
    // timing, then shuffle configuration order independently in each round
    // so thermal or scheduling drift does not systematically favor one rung.
    for (const auto& c : configs) {
        std::vector<int> v = data;
        c.run(v);
        if (v != reference) {
            std::cerr << "FATAL: " << c.algo << " threads=" << c.threads
                      << " mis-sorted during warm-up\n";
            std::exit(1);
        }
    }

    std::vector<std::vector<double>> samples(configs.size());
    for (int r = 0; r < repeats; ++r) {
        for (const std::size_t i : shuffled_order(configs.size(), r)) {
            const auto& c = configs[i];
            std::vector<int> v = data;
            samples[i].push_back(lab::time_ms([&] { c.run(v); }));
            if (v != reference) {
                std::cerr << "FATAL: " << c.algo << " threads=" << c.threads
                          << " mis-sorted in repeat " << r << '\n';
                std::exit(1);
            }
        }
    }

    for (std::size_t i = 0; i < configs.size(); ++i) {
        const auto& c = configs[i];
        const double med = lab::median(samples[i]);
        const double mad = median_absolute_deviation(samples[i]);
        csv.write_row({c.algo, lab::cell(c.threads), lab::cell(n), lab::cell(repeats),
                       lab::cell(med), lab::cell(mad)});
        summary.push_back({"sort/" + c.algo, lab::cell(c.threads), lab::cell(med)});
        std::cout << "sort " << c.algo << " t=" << c.threads << ": " << med
                  << " ms (MAD " << mad << ")\n";
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
                                  : std::vector<int>{1, 2, 4, 6, 8, 12, 16, 20}) {
            require_openmp_team_size(th);
            configs.push_back({"omp_bmh", th});
        }

        for (const auto& c : configs) {
            const auto occ = c.algo == "bmh_seq" ? lab::bmh_search(text, pattern)
                                                   : lab::omp_bmh_search(text, pattern, c.threads);
            if (occ != reference) {
                std::cerr << "FATAL: " << c.algo << " threads=" << c.threads
                          << " disagrees during warm-up (text=" << lab::text_name(t) << ")\n";
                std::exit(1);
            }
        }

        std::vector<std::vector<double>> samples(configs.size());
        for (int r = 0; r < repeats; ++r) {
            for (const std::size_t i : shuffled_order(configs.size(), r)) {
                const auto& c = configs[i];
                std::vector<std::size_t> occ;
                samples[i].push_back(lab::time_ms([&] {
                    occ = c.algo == "bmh_seq" ? lab::bmh_search(text, pattern)
                                              : lab::omp_bmh_search(text, pattern, c.threads);
                }));
                if (occ != reference) {
                    std::cerr << "FATAL: " << c.algo << " threads=" << c.threads
                              << " disagrees in repeat " << r
                              << " (text=" << lab::text_name(t) << ")\n";
                    std::exit(1);
                }
            }
        }

        for (std::size_t i = 0; i < configs.size(); ++i) {
            const auto& c = configs[i];
            const double med = lab::median(samples[i]);
            const double mad = median_absolute_deviation(samples[i]);
            csv.write_row({c.algo, std::string(lab::text_name(t)), lab::cell(c.threads),
                           lab::cell(n), lab::cell(m), lab::cell(repeats), lab::cell(med),
                           lab::cell(mad), lab::cell(reference.size())});
            summary.push_back({"search/" + c.algo + "/" + std::string(lab::text_name(t)),
                               lab::cell(c.threads), lab::cell(med)});
            std::cout << "search " << c.algo << " " << lab::text_name(t)
                      << " t=" << c.threads << ": " << med << " ms (MAD " << mad << ")\n";
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    bool quick = false;
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "--quick") == 0) quick = true;

    omp_set_dynamic(0);

    const std::filesystem::path final_sort =
        quick ? "build/parallel_sort_quick.csv" : "results/parallel_sort.csv";
    const std::filesystem::path final_search =
        quick ? "build/parallel_search_quick.csv" : "results/parallel_search.csv";
    const std::filesystem::path staged_sort =
        quick ? final_sort : std::filesystem::path{"build/parallel_sort.pending.csv"};
    const std::filesystem::path staged_search =
        quick ? final_search : std::filesystem::path{"build/parallel_search.pending.csv"};

    Summary summary;
    {
        lab::CsvWriter sort_csv(staged_sort,
                                {"algo", "threads", "n", "repeats", "median_ms", "mad_ms"});
        lab::CsvWriter search_csv(
            staged_search, {"algo", "text", "threads", "n", "m", "repeats", "median_ms",
                            "mad_ms", "occurrences"});
        run_sort_bench(quick, sort_csv, summary);
        run_search_bench(quick, search_csv, summary);
    }
    if (!quick) {
        std::filesystem::rename(staged_sort, final_sort);
        std::filesystem::rename(staged_search, final_search);
    }
    std::cout << "\nSummary (median ms):\n";
    lab::print_table({"config", "threads", "median_ms"}, summary);
    std::cout << "\nCSV written to " << final_sort << " and " << final_search << '\n';
    return 0;
}
