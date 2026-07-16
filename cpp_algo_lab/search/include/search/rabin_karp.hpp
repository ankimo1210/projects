#pragma once
// Rabin-Karp: compare a rolling polynomial hash of each text window against
// the pattern hash; only verify char-by-char on a hash hit. Every text char
// is touched by the rolling update, so it is Theta(n) hash work no matter
// what -- immune to naive's periodic worst case, but text a^n vs pattern a^m
// makes every window verify (its own worst case). Base 257 > alphabet 256;
// modulus 1e9+7 keeps all intermediates below 2^38 in uint64_t.
#include <cstddef>
#include <cstdint>
#include <string_view>
#include <vector>

#include "search/stats.hpp"

namespace lab {

inline constexpr std::uint64_t kRkBase = 257;
inline constexpr std::uint64_t kRkMod = 1'000'000'007;

namespace detail {

template <class Tally>
std::vector<std::size_t> rabin_karp_core(std::string_view text, std::string_view pattern,
                                         Tally& tally) {
    std::vector<std::size_t> out;
    const std::size_t n = text.size(), m = pattern.size();
    if (m == 0) return every_position(n);
    if (m > n) return out;

    // Preprocessing: pattern hash (m steps) and B^(m-1) mod M (m-1 steps).
    std::uint64_t phash = 0, pow = 1;
    for (std::size_t i = 0; i < m; ++i) {
        tally.pre();
        phash = (phash * kRkBase + static_cast<unsigned char>(pattern[i])) % kRkMod;
    }
    for (std::size_t i = 0; i + 1 < m; ++i) {
        tally.pre();
        pow = pow * kRkBase % kRkMod;
    }

    // First window hash: reads m text chars.
    std::uint64_t whash = 0;
    for (std::size_t i = 0; i < m; ++i) {
        tally.read();
        whash = (whash * kRkBase + static_cast<unsigned char>(text[i])) % kRkMod;
    }

    for (std::size_t i = 0;; ++i) {
        if (whash == phash) {
            std::size_t j = 0;  // verify: hashes can collide
            for (; j < m; ++j) {
                tally.read();
                tally.cmp();
                if (text[i + j] != pattern[j]) break;
            }
            if (j == m) out.push_back(i);
        }
        if (i + m == n) break;
        // Roll the window: drop text[i], append text[i+m] (2 text reads).
        tally.read();
        const std::uint64_t drop =
            static_cast<unsigned char>(text[i]) * pow % kRkMod;
        whash = (whash + kRkMod - drop) % kRkMod;
        tally.read();
        whash = (whash * kRkBase + static_cast<unsigned char>(text[i + m])) % kRkMod;
    }
    return out;
}

}  // namespace detail

inline std::vector<std::size_t> rabin_karp_search(std::string_view text,
                                                  std::string_view pattern) {
    NoTally t;
    return detail::rabin_karp_core(text, pattern, t);
}

inline SearchStats rabin_karp_search_counted(std::string_view text,
                                             std::string_view pattern) {
    SearchStats st;
    Tally t{&st};
    st.occurrences = detail::rabin_karp_core(text, pattern, t);
    return st;
}

}  // namespace lab
