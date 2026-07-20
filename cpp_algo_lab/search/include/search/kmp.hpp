#pragma once
// Knuth-Morris-Pratt: never re-read a text character after a match. The
// failure (prefix) function tells how far the pattern can shift on a
// mismatch while reusing what already matched. Scan cost <= 2n comparisons
// regardless of the pattern -- flat where naive explodes.
#include <cstddef>
#include <string_view>
#include <vector>

#include "search/stats.hpp"

namespace lab {

namespace detail {

// Prefix function: fail[i] = length of the longest proper prefix of
// pattern[0..i] that is also a suffix of it. Built in O(m) with exactly one
// pattern-vs-pattern comparison per loop turn (counted as a pre op).
template <class Tally>
std::vector<std::size_t> kmp_failure(std::string_view pattern, Tally& tally) {
    const std::size_t m = pattern.size();
    std::vector<std::size_t> fail(m, 0);
    std::size_t k = 0;
    for (std::size_t i = 1; i < m; ++i) {
        for (;;) {
            tally.pre();
            if (pattern[i] == pattern[k]) {
                ++k;
                break;
            }
            if (k == 0) break;
            k = fail[k - 1];
        }
        fail[i] = k;
    }
    return fail;
}

template <class Tally>
std::vector<std::size_t> kmp_core(std::string_view text, std::string_view pattern,
                                  Tally& tally) {
    std::vector<std::size_t> out;
    const std::size_t n = text.size(), m = pattern.size();
    if (m == 0) return every_position(n);
    if (m > n) return out;
    const std::vector<std::size_t> fail = kmp_failure(pattern, tally);
    std::size_t j = 0;  // chars of the pattern currently matched
    for (std::size_t i = 0; i < n; ++i) {
        for (;;) {
            tally.read();
            tally.cmp();
            if (text[i] == pattern[j]) {
                ++j;
                break;
            }
            if (j == 0) break;
            j = fail[j - 1];  // shift the pattern, keep the matched prefix
        }
        if (j == m) {
            out.push_back(i + 1 - m);
            j = fail[m - 1];  // continue: overlapping occurrences are free
        }
    }
    return out;
}

}  // namespace detail

inline std::vector<std::size_t> kmp_search(std::string_view text, std::string_view pattern) {
    NoTally t;
    return detail::kmp_core(text, pattern, t);
}

inline SearchStats kmp_search_counted(std::string_view text, std::string_view pattern) {
    SearchStats st;
    Tally t{&st};
    st.occurrences = detail::kmp_core(text, pattern, t);
    return st;
}

}  // namespace lab
