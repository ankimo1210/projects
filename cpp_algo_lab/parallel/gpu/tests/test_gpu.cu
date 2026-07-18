// Correctness tests for the Phase 4 CUDA sorting and search rungs.
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest/doctest.h"

#include <algorithm>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include "gpu/cuda_utils.cuh"
#include "gpu/search.cuh"
#include "gpu/sort.cuh"
#include "lab/datagen.hpp"
#include "lab/textgen.hpp"
#include "search/naive.hpp"

namespace {

void check_bitonic(std::vector<int> values) {
    std::vector<int> expected = values;
    std::sort(expected.begin(), expected.end());
    lab::gpu::bitonic_sort(values);
    CHECK(values == expected);
}

void check_search(std::string_view text, std::string_view pattern) {
    CHECK(lab::gpu::naive_search(text, pattern) == lab::naive_search(text, pattern));
}

}  // namespace

TEST_CASE("CUDA device is available") {
    int count = 0;
    lab::gpu::check_cuda(cudaGetDeviceCount(&count), "cudaGetDeviceCount");
    REQUIRE(count > 0);
    cudaDeviceProp properties{};
    lab::gpu::check_cuda(cudaGetDeviceProperties(&properties, 0), "cudaGetDeviceProperties");
    CHECK(properties.major >= 1);
}

TEST_CASE("bitonic_sort: boundaries, padding, duplicates, and extreme values") {
    check_bitonic({});
    check_bitonic({7});
    check_bitonic({2, 1});
    check_bitonic({3, 1, 2});
    check_bitonic({5, -1, 5, 0, std::numeric_limits<int>::max(),
                   std::numeric_limits<int>::min(), 5});
    for (const std::size_t n : {std::size_t{7}, std::size_t{31}, std::size_t{32},
                                std::size_t{33}, std::size_t{255}, std::size_t{256},
                                std::size_t{257}, std::size_t{1000}, std::size_t{4096}})
        check_bitonic(lab::generate(lab::Dist::random_uniform, n, 42));
}

TEST_CASE("bitonic_sort: generated distributions and a multi-block padded input") {
    for (const lab::Dist distribution : lab::all_dists())
        check_bitonic(lab::generate(distribution, 8193, 42));
    check_bitonic(lab::generate(lab::Dist::random_uniform, 65537, 7));
}

TEST_CASE("bitonic_sort_device: rejects a non-power-of-two size") {
    lab::gpu::DeviceBuffer<int> values(3);
    CHECK_THROWS_AS(lab::gpu::bitonic_sort_device(values.get(), 3), std::invalid_argument);
}

TEST_CASE("thrust_sort: agrees with std::sort") {
    std::vector<int> values = lab::generate(lab::Dist::random_uniform, 100000, 42);
    std::vector<int> expected = values;
    std::sort(expected.begin(), expected.end());
    lab::gpu::thrust_sort(values);
    CHECK(values == expected);
}

TEST_CASE("CUDA naive search: module boundary conventions") {
    check_search("", "");
    check_search("", "a");
    check_search("abc", "");
    check_search("ab", "abc");
    check_search("abc", "abc");
    check_search("xxab", "ab");
    check_search("banana", "a");
    check_search("aaaaaa", "aaa");
}

TEST_CASE("CUDA naive search: matches around CUDA block boundaries") {
    const std::string pattern = "NEEDLE";
    for (const std::size_t pos : {std::size_t{254}, std::size_t{255}, std::size_t{256},
                                  std::size_t{510}, std::size_t{511}, std::size_t{512},
                                  std::size_t{766}, std::size_t{767}, std::size_t{768}}) {
        std::string text(2048, 'x');
        text.replace(pos, pattern.size(), pattern);
        const std::vector<std::size_t> expected{pos};
        REQUIRE(lab::naive_search(text, pattern) == expected);
        CHECK(lab::gpu::naive_search(text, pattern) == expected);
    }
}

TEST_CASE("CUDA naive search: generated corpora agree with the CPU reference") {
    for (const lab::Text text_kind : lab::all_texts()) {
        const std::string text = lab::generate_text(text_kind, 65536, 42);
        for (const std::size_t m : {std::size_t{1}, std::size_t{4}, std::size_t{16},
                                    std::size_t{64}})
            check_search(text, lab::pattern_for(text_kind, text, m, 42));
    }
}
