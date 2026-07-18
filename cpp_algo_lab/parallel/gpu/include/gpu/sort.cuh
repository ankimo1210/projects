#pragma once
// GPU sorting ladder: an educational bitonic network followed by the
// optimized Thrust baseline. Host wrappers include allocation and transfers;
// device functions let the benchmark time resident-data execution separately.
#include <cuda_runtime.h>
#include <thrust/device_ptr.h>
#include <thrust/sort.h>
#include <thrust/system/cuda/execution_policy.h>

#include <algorithm>
#include <bit>
#include <cstddef>
#include <limits>
#include <stdexcept>
#include <vector>

#include "gpu/cuda_utils.cuh"

namespace lab::gpu {

inline std::size_t next_power_of_two(std::size_t n) {
    if (n <= 1) return n;
    constexpr int digits = std::numeric_limits<std::size_t>::digits;
    const std::size_t largest = std::size_t{1} << (digits - 1);
    if (n > largest) throw std::length_error("bitonic padding size overflow");
    return std::bit_ceil(n);
}

__global__ void bitonic_step_kernel(int* values, std::size_t n, std::size_t stride,
                                    std::size_t sequence) {
    const std::size_t i = static_cast<std::size_t>(blockIdx.x) * blockDim.x + threadIdx.x;
    if (i >= n) return;
    const std::size_t partner = i ^ stride;
    if (partner <= i || partner >= n) return;

    const bool ascending = (i & sequence) == 0;
    const int left = values[i];
    const int right = values[partner];
    if ((ascending && left > right) || (!ascending && left < right)) {
        values[i] = right;
        values[partner] = left;
    }
}

inline void bitonic_sort_device(int* values, std::size_t n, cudaStream_t stream = nullptr) {
    if (n < 2) return;
    if (!std::has_single_bit(n))
        throw std::invalid_argument("bitonic_sort_device requires a power-of-two size");

    constexpr unsigned threads = 256;
    const auto blocks = static_cast<unsigned>(ceil_div(n, threads));
    for (std::size_t sequence = 2;; sequence <<= 1) {
        for (std::size_t stride = sequence >> 1; stride != 0; stride >>= 1) {
            bitonic_step_kernel<<<blocks, threads, 0, stream>>>(values, n, stride, sequence);
            check_cuda(cudaGetLastError(), "bitonic_step_kernel launch");
        }
        if (sequence == n) break;
    }
}

inline void thrust_sort_device(int* values, std::size_t n, cudaStream_t stream = nullptr) {
    if (n < 2) return;
    auto first = thrust::device_pointer_cast(values);
    thrust::sort(thrust::cuda::par.on(stream), first, first + n);
    check_cuda(cudaGetLastError(), "thrust::sort");
}

inline void bitonic_sort(std::vector<int>& values) {
    if (values.size() < 2) return;
    const std::size_t padded_size = next_power_of_two(values.size());
    std::vector<int> padded(padded_size, std::numeric_limits<int>::max());
    std::copy(values.begin(), values.end(), padded.begin());

    DeviceBuffer<int> device(padded_size);
    check_cuda(cudaMemcpy(device.get(), padded.data(), padded_size * sizeof(int),
                          cudaMemcpyHostToDevice),
               "cudaMemcpy bitonic H2D");
    bitonic_sort_device(device.get(), padded_size);
    check_cuda(cudaDeviceSynchronize(), "cudaDeviceSynchronize bitonic");
    check_cuda(cudaMemcpy(padded.data(), device.get(), padded_size * sizeof(int),
                          cudaMemcpyDeviceToHost),
               "cudaMemcpy bitonic D2H");
    std::copy_n(padded.begin(), values.size(), values.begin());
}

inline void thrust_sort(std::vector<int>& values) {
    if (values.size() < 2) return;
    DeviceBuffer<int> device(values.size());
    check_cuda(cudaMemcpy(device.get(), values.data(), values.size() * sizeof(int),
                          cudaMemcpyHostToDevice),
               "cudaMemcpy thrust H2D");
    thrust_sort_device(device.get(), values.size());
    check_cuda(cudaDeviceSynchronize(), "cudaDeviceSynchronize thrust");
    check_cuda(cudaMemcpy(values.data(), device.get(), values.size() * sizeof(int),
                          cudaMemcpyDeviceToHost),
               "cudaMemcpy thrust D2H");
}

}  // namespace lab::gpu
