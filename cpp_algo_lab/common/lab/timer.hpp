#pragma once
// Wall-clock timing helpers. Benchmarks take the median of repeated runs to
// damp WSL2 scheduling noise.
#include <algorithm>
#include <chrono>
#include <stdexcept>
#include <utility>
#include <vector>

namespace lab {

template <class F>
double time_ms(F&& f) {
    const auto t0 = std::chrono::steady_clock::now();
    std::forward<F>(f)();
    const auto t1 = std::chrono::steady_clock::now();
    return std::chrono::duration<double, std::milli>(t1 - t0).count();
}

inline double median(std::vector<double> v) {
    if (v.empty()) throw std::invalid_argument("median: empty input");
    std::sort(v.begin(), v.end());
    const std::size_t m = v.size() / 2;
    if (v.size() % 2 == 1) return v[m];
    return (v[m - 1] + v[m]) / 2.0;
}

}  // namespace lab
