#pragma once
// Naive (brute-force) exact matching: try every alignment, compare left to
// right. Worst case O(n*m) -- realized on periodic text with pattern
// a^(m-1) b, where every alignment survives m-1 comparisons. On random text
// a mismatch arrives after ~sigma/(sigma-1) comparisons, so it behaves ~O(n).
#include <cstddef>
#include <string_view>
#include <vector>

#include "search/stats.hpp"

namespace lab {

namespace detail {

template <class Tally>
std::vector<std::size_t> naive_core(std::string_view text, std::string_view pattern,
                                    Tally& tally) {
    std::vector<std::size_t> out;
    const std::size_t n = text.size(), m = pattern.size();
    if (m == 0) return every_position(n);
    if (m > n) return out;
    for (std::size_t i = 0; i + m <= n; ++i) {
        std::size_t j = 0;
        for (; j < m; ++j) {
            tally.read();
            tally.cmp();
            if (text[i + j] != pattern[j]) break;
        }
        if (j == m) out.push_back(i);
    }
    return out;
}

}  // namespace detail

inline std::vector<std::size_t> naive_search(std::string_view text, std::string_view pattern) {
    NoTally t;
    return detail::naive_core(text, pattern, t);
}

inline SearchStats naive_search_counted(std::string_view text, std::string_view pattern) {
    SearchStats st;
    Tally t{&st};
    st.occurrences = detail::naive_core(text, pattern, t);
    return st;
}

}  // namespace lab
