#pragma once
// Deterministic input generators for benchmarks and tests.
// Values are always non-negative and < max(n, 10), so non-comparison sorts
// (counting/radix/bucket) are applicable to every distribution.
#include <algorithm>
#include <array>
#include <cstdint>
#include <numeric>
#include <random>
#include <string_view>
#include <vector>

namespace lab {

enum class Dist { random_uniform, sorted_asc, reversed, nearly_sorted, few_unique };

inline constexpr std::array<Dist, 5> all_dists() {
    return {Dist::random_uniform, Dist::sorted_asc, Dist::reversed, Dist::nearly_sorted,
            Dist::few_unique};
}

inline std::string_view dist_name(Dist d) {
    switch (d) {
        case Dist::random_uniform: return "random";
        case Dist::sorted_asc: return "sorted";
        case Dist::reversed: return "reversed";
        case Dist::nearly_sorted: return "nearly_sorted";
        case Dist::few_unique: return "few_unique";
    }
    return "unknown";
}

inline std::vector<int> generate(Dist d, std::size_t n, std::uint32_t seed) {
    std::vector<int> v(n);
    if (n == 0) return v;
    std::mt19937 rng(seed);
    const int hi = static_cast<int>(std::max<std::size_t>(n, 10)) - 1;
    switch (d) {
        case Dist::random_uniform: {
            std::uniform_int_distribution<int> u(0, hi);
            std::generate(v.begin(), v.end(), [&] { return u(rng); });
            break;
        }
        case Dist::sorted_asc:
            std::iota(v.begin(), v.end(), 0);
            break;
        case Dist::reversed:
            std::iota(v.begin(), v.end(), 0);
            std::reverse(v.begin(), v.end());
            break;
        case Dist::nearly_sorted: {
            std::iota(v.begin(), v.end(), 0);
            if (n >= 2) {
                const std::size_t k = std::max<std::size_t>(1, n / 100);
                std::uniform_int_distribution<std::size_t> pos(0, n - 2);
                for (std::size_t i = 0; i < k; ++i) {
                    const std::size_t p = pos(rng);
                    std::swap(v[p], v[p + 1]);
                }
            }
            break;
        }
        case Dist::few_unique: {
            std::uniform_int_distribution<int> u(0, 9);
            std::generate(v.begin(), v.end(), [&] { return u(rng); });
            break;
        }
    }
    return v;
}

}  // namespace lab
