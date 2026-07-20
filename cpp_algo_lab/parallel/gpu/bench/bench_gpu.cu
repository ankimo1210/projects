// Phase 4 GPU benchmark -> results/gpu_sort.csv and results/gpu_search.csv.
// Kernel rows time resident device work with CUDA events. End-to-end rows
// include allocation, host/device transfers, kernel execution, result
// materialization, and cleanup with a host steady clock. Every configuration
// gets one warm-up, timed configurations are shuffled per round, and every
// result is verified outside its timed region. Full results are staged before
// replacing canonical CSVs; --quick writes only under build/.
#include <cuda_runtime.h>

#include <algorithm>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

#include "gpu/cuda_utils.cuh"
#include "gpu/search.cuh"
#include "gpu/sort.cuh"
#include "lab/csv.hpp"
#include "lab/datagen.hpp"
#include "lab/table.hpp"
#include "lab/textgen.hpp"
#include "lab/timer.hpp"
#include "search/bmh.hpp"
#include "search/naive.hpp"

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
    std::mt19937 rng(4200u + static_cast<unsigned>(repeat));
    std::shuffle(order.begin(), order.end(), rng);
    return order;
}

[[noreturn]] void fail_validation(std::string_view config, int repeat) {
    std::cerr << "FATAL: " << config << " disagreed with the CPU reference";
    if (repeat >= 0) std::cerr << " in repeat " << repeat;
    std::cerr << '\n';
    std::exit(1);
}

enum class SortKind { std_sort, bitonic_kernel, bitonic_end_to_end, thrust_kernel,
                      thrust_end_to_end };

struct SortConfig {
    const char* algo;
    const char* mode;
    SortKind kind;
};

void run_sort_bench(bool quick, lab::CsvWriter& csv, Summary& summary) {
    const std::size_t n = quick ? (std::size_t{1} << 20) : (std::size_t{1} << 24);
    const int repeats = quick ? 2 : 5;
    const std::vector<int> data = lab::generate(lab::Dist::random_uniform, n, 42);
    std::vector<int> reference = data;
    std::sort(reference.begin(), reference.end());

    const std::vector<SortConfig> configs{
        {"std_sort_cpu", "host", SortKind::std_sort},
        {"bitonic", "kernel", SortKind::bitonic_kernel},
        {"bitonic", "end_to_end", SortKind::bitonic_end_to_end},
        {"thrust", "kernel", SortKind::thrust_kernel},
        {"thrust", "end_to_end", SortKind::thrust_end_to_end},
    };

    lab::gpu::DeviceBuffer<int> resident(n);
    lab::gpu::EventTimer event_timer;

    auto run = [&](const SortConfig& config, int repeat, bool timed) {
        std::vector<int> output;
        double elapsed = 0.0;
        switch (config.kind) {
            case SortKind::std_sort:
                output = data;
                if (timed)
                    elapsed = lab::time_ms([&] { std::sort(output.begin(), output.end()); });
                else
                    std::sort(output.begin(), output.end());
                break;
            case SortKind::bitonic_kernel:
            case SortKind::thrust_kernel:
                lab::gpu::check_cuda(
                    cudaMemcpy(resident.get(), data.data(), n * sizeof(int),
                               cudaMemcpyHostToDevice),
                    "cudaMemcpy resident sort H2D");
                if (timed) {
                    elapsed = event_timer.measure_ms([&] {
                        if (config.kind == SortKind::bitonic_kernel)
                            lab::gpu::bitonic_sort_device(resident.get(), n);
                        else
                            lab::gpu::thrust_sort_device(resident.get(), n);
                    });
                } else {
                    if (config.kind == SortKind::bitonic_kernel)
                        lab::gpu::bitonic_sort_device(resident.get(), n);
                    else
                        lab::gpu::thrust_sort_device(resident.get(), n);
                    lab::gpu::check_cuda(cudaDeviceSynchronize(),
                                         "cudaDeviceSynchronize resident sort");
                }
                output.resize(n);
                lab::gpu::check_cuda(
                    cudaMemcpy(output.data(), resident.get(), n * sizeof(int),
                               cudaMemcpyDeviceToHost),
                    "cudaMemcpy resident sort D2H");
                break;
            case SortKind::bitonic_end_to_end:
                output = data;
                if (timed)
                    elapsed = lab::time_ms([&] { lab::gpu::bitonic_sort(output); });
                else
                    lab::gpu::bitonic_sort(output);
                break;
            case SortKind::thrust_end_to_end:
                output = data;
                if (timed)
                    elapsed = lab::time_ms([&] { lab::gpu::thrust_sort(output); });
                else
                    lab::gpu::thrust_sort(output);
                break;
        }
        if (output != reference)
            fail_validation(std::string(config.algo) + "/" + config.mode, repeat);
        return elapsed;
    };

    for (const auto& config : configs) run(config, -1, false);

    std::vector<std::vector<double>> samples(configs.size());
    for (int repeat = 0; repeat < repeats; ++repeat)
        for (const std::size_t i : shuffled_order(configs.size(), repeat))
            samples[i].push_back(run(configs[i], repeat, true));

    for (std::size_t i = 0; i < configs.size(); ++i) {
        const auto& config = configs[i];
        const double med = lab::median(samples[i]);
        const double mad = median_absolute_deviation(samples[i]);
        csv.write_row({config.algo, config.mode, lab::cell(n), lab::cell(repeats),
                       lab::cell(med), lab::cell(mad)});
        summary.push_back({"sort/" + std::string(config.algo), "-", config.mode,
                           lab::cell(med)});
        std::cout << "sort " << config.algo << '/' << config.mode << ": " << med
                  << " ms (MAD " << mad << ")\n";
    }
}

enum class SearchKind { naive_cpu, bmh_cpu, cuda_kernel, cuda_end_to_end };

struct SearchConfig {
    const char* algo;
    const char* mode;
    SearchKind kind;
};

void run_search_bench(bool quick, lab::CsvWriter& csv, Summary& summary) {
    const std::size_t n = quick ? (std::size_t{1} << 22) : (std::size_t{1} << 26);
    const std::size_t m = 16;
    const int repeats = quick ? 2 : 5;
    const std::vector<SearchConfig> configs{
        {"naive_cpu", "host", SearchKind::naive_cpu},
        {"bmh_cpu", "host", SearchKind::bmh_cpu},
        {"cuda_naive", "kernel", SearchKind::cuda_kernel},
        {"cuda_naive", "end_to_end", SearchKind::cuda_end_to_end},
    };

    for (const lab::Text text_kind : {lab::Text::english_like, lab::Text::dna}) {
        const std::string text = lab::generate_text(text_kind, n, 42);
        const std::string pattern = lab::pattern_for(text_kind, text, m, 42);
        const std::vector<std::size_t> reference = lab::bmh_search(text, pattern);
        const std::size_t starts = lab::gpu::search_start_count(n, m);

        lab::gpu::DeviceBuffer<char> resident_text(n);
        lab::gpu::DeviceBuffer<char> resident_pattern(m);
        lab::gpu::DeviceBuffer<unsigned char> resident_flags(starts);
        lab::gpu::check_cuda(
            cudaMemcpy(resident_text.get(), text.data(), n, cudaMemcpyHostToDevice),
            "cudaMemcpy resident search text H2D");
        lab::gpu::check_cuda(
            cudaMemcpy(resident_pattern.get(), pattern.data(), m, cudaMemcpyHostToDevice),
            "cudaMemcpy resident search pattern H2D");
        std::vector<unsigned char> flags(starts);
        lab::gpu::EventTimer event_timer;

        auto run = [&](const SearchConfig& config, int repeat, bool timed) {
            std::vector<std::size_t> occurrences;
            double elapsed = 0.0;
            switch (config.kind) {
                case SearchKind::naive_cpu:
                    if (timed)
                        elapsed = lab::time_ms([&] { occurrences = lab::naive_search(text, pattern); });
                    else
                        occurrences = lab::naive_search(text, pattern);
                    break;
                case SearchKind::bmh_cpu:
                    if (timed)
                        elapsed = lab::time_ms([&] { occurrences = lab::bmh_search(text, pattern); });
                    else
                        occurrences = lab::bmh_search(text, pattern);
                    break;
                case SearchKind::cuda_kernel:
                    if (timed) {
                        elapsed = event_timer.measure_ms([&] {
                            lab::gpu::naive_search_flags_device(
                                resident_text.get(), n, resident_pattern.get(), m,
                                resident_flags.get());
                        });
                    } else {
                        lab::gpu::naive_search_flags_device(
                            resident_text.get(), n, resident_pattern.get(), m,
                            resident_flags.get());
                        lab::gpu::check_cuda(cudaDeviceSynchronize(),
                                             "cudaDeviceSynchronize resident search");
                    }
                    lab::gpu::check_cuda(
                        cudaMemcpy(flags.data(), resident_flags.get(), starts,
                                   cudaMemcpyDeviceToHost),
                        "cudaMemcpy resident search flags D2H");
                    occurrences = lab::gpu::gather_search_flags(flags);
                    break;
                case SearchKind::cuda_end_to_end:
                    if (timed)
                        elapsed = lab::time_ms(
                            [&] { occurrences = lab::gpu::naive_search(text, pattern); });
                    else
                        occurrences = lab::gpu::naive_search(text, pattern);
                    break;
            }
            if (occurrences != reference)
                fail_validation(std::string(config.algo) + "/" + config.mode + "/" +
                                    std::string(lab::text_name(text_kind)),
                                repeat);
            return elapsed;
        };

        for (const auto& config : configs) run(config, -1, false);

        std::vector<std::vector<double>> samples(configs.size());
        for (int repeat = 0; repeat < repeats; ++repeat)
            for (const std::size_t i : shuffled_order(configs.size(), repeat))
                samples[i].push_back(run(configs[i], repeat, true));

        for (std::size_t i = 0; i < configs.size(); ++i) {
            const auto& config = configs[i];
            const double med = lab::median(samples[i]);
            const double mad = median_absolute_deviation(samples[i]);
            csv.write_row({config.algo, std::string(lab::text_name(text_kind)), config.mode,
                           lab::cell(n), lab::cell(m), lab::cell(repeats), lab::cell(med),
                           lab::cell(mad), lab::cell(reference.size())});
            summary.push_back({"search/" + std::string(config.algo),
                               std::string(lab::text_name(text_kind)), config.mode,
                               lab::cell(med)});
            std::cout << "search " << config.algo << '/' << config.mode << ' '
                      << lab::text_name(text_kind) << ": " << med << " ms (MAD " << mad
                      << ")\n";
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    bool quick = false;
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--quick") == 0)
            quick = true;
        else {
            std::cerr << "usage: " << argv[0] << " [--quick]\n";
            return 2;
        }
    }

    lab::gpu::check_cuda(cudaSetDevice(0), "cudaSetDevice");
    lab::gpu::check_cuda(cudaFree(nullptr), "initialize CUDA context");
    cudaDeviceProp properties{};
    lab::gpu::check_cuda(cudaGetDeviceProperties(&properties, 0), "cudaGetDeviceProperties");
    std::cout << "GPU: " << properties.name << " (compute " << properties.major << '.'
              << properties.minor << ")\n";

    const std::filesystem::path final_sort =
        quick ? "build/gpu_sort_quick.csv" : "results/gpu_sort.csv";
    const std::filesystem::path final_search =
        quick ? "build/gpu_search_quick.csv" : "results/gpu_search.csv";
    const std::filesystem::path staged_sort =
        quick ? final_sort : std::filesystem::path{"build/gpu_sort.pending.csv"};
    const std::filesystem::path staged_search =
        quick ? final_search : std::filesystem::path{"build/gpu_search.pending.csv"};

    Summary summary;
    {
        lab::CsvWriter sort_csv(staged_sort,
                                {"algo", "mode", "n", "repeats", "median_ms", "mad_ms"});
        lab::CsvWriter search_csv(
            staged_search, {"algo", "text", "mode", "n", "m", "repeats", "median_ms",
                            "mad_ms", "occurrences"});
        run_sort_bench(quick, sort_csv, summary);
        run_search_bench(quick, search_csv, summary);
    }
    if (!quick) {
        std::filesystem::rename(staged_sort, final_sort);
        std::filesystem::rename(staged_search, final_search);
    }

    std::cout << "\nSummary (median ms):\n";
    lab::print_table({"config", "text", "mode", "median_ms"}, summary);
    std::cout << "\nCSV written to " << final_sort << " and " << final_search << '\n';
    return 0;
}
