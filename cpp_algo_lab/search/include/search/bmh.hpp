#pragma once
// Boyer-Moore-Horspool: compare right to left; on any outcome, shift by the
// bad-character rule keyed on the text char under the pattern's LAST
// position. Skipping makes it sublinear on realistic text (text_reads < n),
// the headline result of this module. A char that only occurs at the
// pattern's last position gets shift m -- the classic table subtlety.
#include <array>
#include <cstddef>
#include <string_view>
#include <vector>

#include "search/stats.hpp"

namespace lab {

namespace detail {

template <class Tally>
std::vector<std::size_t> bmh_core(std::string_view text, std::string_view pattern,
                                  Tally& tally) {
    std::vector<std::size_t> out;
    const std::size_t n = text.size(), m = pattern.size();
    if (m == 0) return every_position(n);
    if (m > n) return out;

    // Bad-character table over pattern[0..m-2]: shift[c] = distance from c's
    // rightmost occurrence there to the last position. Absent chars shift m.
    std::array<std::size_t, 256> shift;
    shift.fill(m);
    for (std::size_t i = 0; i + 1 < m; ++i) {
        tally.pre();
        shift[static_cast<unsigned char>(pattern[i])] = m - 1 - i;
    }

    std::size_t i = 0;  // alignment: pattern[0] sits at text[i]
    while (i + m <= n) {
        tally.read();
        const unsigned char last = static_cast<unsigned char>(text[i + m - 1]);
        tally.cmp();
        if (last == static_cast<unsigned char>(pattern[m - 1])) {
            std::size_t j = m - 1;  // last char matched; check the rest
            while (j > 0) {
                tally.read();
                tally.cmp();
                if (text[i + j - 1] != pattern[j - 1]) break;
                --j;
            }
            if (j == 0) out.push_back(i);
        }
        i += shift[last];  // shift is >= 1 by construction
    }
    return out;
}

}  // namespace detail

inline std::vector<std::size_t> bmh_search(std::string_view text, std::string_view pattern) {
    NoTally t;
    return detail::bmh_core(text, pattern, t);
}

inline SearchStats bmh_search_counted(std::string_view text, std::string_view pattern) {
    SearchStats st;
    Tally t{&st};
    st.occurrences = detail::bmh_core(text, pattern, t);
    return st;
}

}  // namespace lab
