#pragma once
// One CUDA thread owns one candidate start position. The kernel emits a byte
// flag per candidate; the host materializes ascending occurrence positions.
#include <cuda_runtime.h>

#include <cstddef>
#include <string_view>
#include <vector>

#include "gpu/cuda_utils.cuh"

namespace lab::gpu {

inline std::size_t search_start_count(std::size_t n, std::size_t m) {
    if (m > n) return 0;
    return n - m + 1;
}

__global__ void naive_search_flags_kernel(const char* text, const char* pattern, std::size_t m,
                                          std::size_t starts, unsigned char* flags) {
    const std::size_t pos = static_cast<std::size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (pos >= starts) return;
    bool match = true;
    for (std::size_t j = 0; j < m; ++j) {
        if (text[pos + j] != pattern[j]) {
            match = false;
            break;
        }
    }
    flags[pos] = static_cast<unsigned char>(match);
}

inline void naive_search_flags_device(const char* text, std::size_t n, const char* pattern,
                                      std::size_t m, unsigned char* flags,
                                      cudaStream_t stream = nullptr) {
    const std::size_t starts = search_start_count(n, m);
    if (starts == 0) return;
    constexpr unsigned threads = 256;
    const auto blocks = static_cast<unsigned>(ceil_div(starts, threads));
    naive_search_flags_kernel<<<blocks, threads, 0, stream>>>(text, pattern, m, starts, flags);
    check_cuda(cudaGetLastError(), "naive_search_flags_kernel launch");
}

inline std::vector<std::size_t> gather_search_flags(const std::vector<unsigned char>& flags) {
    std::vector<std::size_t> occurrences;
    for (std::size_t i = 0; i < flags.size(); ++i)
        if (flags[i] != 0) occurrences.push_back(i);
    return occurrences;
}

inline std::vector<std::size_t> naive_search(std::string_view text, std::string_view pattern) {
    const std::size_t starts = search_start_count(text.size(), pattern.size());
    if (starts == 0) return {};

    DeviceBuffer<char> device_text(text.size());
    DeviceBuffer<char> device_pattern(pattern.size());
    DeviceBuffer<unsigned char> device_flags(starts);
    if (!text.empty())
        check_cuda(cudaMemcpy(device_text.get(), text.data(), text.size(), cudaMemcpyHostToDevice),
                   "cudaMemcpy search text H2D");
    if (!pattern.empty())
        check_cuda(cudaMemcpy(device_pattern.get(), pattern.data(), pattern.size(),
                              cudaMemcpyHostToDevice),
                   "cudaMemcpy search pattern H2D");

    naive_search_flags_device(device_text.get(), text.size(), device_pattern.get(), pattern.size(),
                              device_flags.get());
    check_cuda(cudaDeviceSynchronize(), "cudaDeviceSynchronize search");
    std::vector<unsigned char> flags(starts);
    check_cuda(cudaMemcpy(flags.data(), device_flags.get(), starts, cudaMemcpyDeviceToHost),
               "cudaMemcpy search flags D2H");
    return gather_search_flags(flags);
}

}  // namespace lab::gpu
