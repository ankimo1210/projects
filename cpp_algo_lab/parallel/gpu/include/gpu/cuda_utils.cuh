#pragma once
// Small CUDA host-side utilities shared by the Phase 4 algorithms, tests,
// and benchmark. Device allocations and events are RAII-owned; every CUDA
// API boundary reports the failing operation through a C++ exception.
#include <cuda_runtime.h>

#include <cstddef>
#include <stdexcept>
#include <string>
#include <utility>

namespace lab::gpu {

inline void check_cuda(cudaError_t status, const char* operation) {
    if (status != cudaSuccess)
        throw std::runtime_error(std::string(operation) + ": " + cudaGetErrorString(status));
}

template <class T>
class DeviceBuffer {
public:
    DeviceBuffer() = default;

    explicit DeviceBuffer(std::size_t size) : size_(size) {
        if (size_ != 0)
            check_cuda(cudaMalloc(reinterpret_cast<void**>(&data_), size_ * sizeof(T)),
                       "cudaMalloc");
    }

    ~DeviceBuffer() {
        if (data_ != nullptr) cudaFree(data_);
    }

    DeviceBuffer(const DeviceBuffer&) = delete;
    DeviceBuffer& operator=(const DeviceBuffer&) = delete;

    DeviceBuffer(DeviceBuffer&& other) noexcept
        : data_(std::exchange(other.data_, nullptr)), size_(std::exchange(other.size_, 0)) {}

    DeviceBuffer& operator=(DeviceBuffer&& other) noexcept {
        if (this == &other) return *this;
        if (data_ != nullptr) cudaFree(data_);
        data_ = std::exchange(other.data_, nullptr);
        size_ = std::exchange(other.size_, 0);
        return *this;
    }

    T* get() noexcept { return data_; }
    const T* get() const noexcept { return data_; }
    std::size_t size() const noexcept { return size_; }

private:
    T* data_ = nullptr;
    std::size_t size_ = 0;
};

class EventTimer {
public:
    EventTimer() {
        check_cuda(cudaEventCreate(&start_), "cudaEventCreate(start)");
        try {
            check_cuda(cudaEventCreate(&stop_), "cudaEventCreate(stop)");
        } catch (...) {
            cudaEventDestroy(start_);
            throw;
        }
    }

    ~EventTimer() {
        cudaEventDestroy(stop_);
        cudaEventDestroy(start_);
    }

    EventTimer(const EventTimer&) = delete;
    EventTimer& operator=(const EventTimer&) = delete;

    template <class F>
    double measure_ms(F&& operation, cudaStream_t stream = nullptr) {
        check_cuda(cudaEventRecord(start_, stream), "cudaEventRecord(start)");
        std::forward<F>(operation)();
        check_cuda(cudaEventRecord(stop_, stream), "cudaEventRecord(stop)");
        check_cuda(cudaEventSynchronize(stop_), "cudaEventSynchronize(stop)");
        float elapsed = 0.0F;
        check_cuda(cudaEventElapsedTime(&elapsed, start_, stop_), "cudaEventElapsedTime");
        return static_cast<double>(elapsed);
    }

private:
    cudaEvent_t start_{};
    cudaEvent_t stop_{};
};

inline std::size_t ceil_div(std::size_t value, std::size_t divisor) {
    return value / divisor + static_cast<std::size_t>(value % divisor != 0);
}

}  // namespace lab::gpu
