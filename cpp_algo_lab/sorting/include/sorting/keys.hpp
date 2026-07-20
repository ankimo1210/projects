#pragma once
// Key extraction for non-comparison sorts (counting/radix/bucket).
// The default IntegralKey maps a non-negative integral element to uint64_t;
// pass a custom KeyFn (e.g. lab::KeyIdxKey, or a lambda over Counted<int>)
// to sort other element types by an integer key.
#include <cstdint>
#include <stdexcept>
#include <type_traits>

namespace lab {

struct IntegralKey {
    template <class T>
    std::uint64_t operator()(const T& v) const {
        static_assert(std::is_integral_v<T>,
                      "IntegralKey requires an integral element type; pass a custom KeyFn");
        if constexpr (std::is_signed_v<T>) {
            if (v < 0) throw std::invalid_argument("non-comparison sort: negative key");
        }
        return static_cast<std::uint64_t>(v);
    }
};

}  // namespace lab
