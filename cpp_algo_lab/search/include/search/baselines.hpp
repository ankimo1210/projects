#pragma once
// Standard-library baselines. C++17 searcher objects separate preprocessing
// (the searcher's constructor builds the tables once) from matching
// (std::search runs the scan) -- the same pre/match split our counted
// variants measure, expressed as API design. Wrapped to return all
// (overlapping) occurrences under the module's shared conventions.
#include <algorithm>
#include <cstddef>
#include <functional>
#include <string_view>
#include <vector>

#include "search/stats.hpp"

namespace lab {

inline std::vector<std::size_t> sv_find_search(std::string_view text,
                                               std::string_view pattern) {
    if (pattern.empty()) return detail::every_position(text.size());
    std::vector<std::size_t> out;
    for (std::size_t pos = text.find(pattern); pos != std::string_view::npos;
         pos = text.find(pattern, pos + 1))
        out.push_back(pos);
    return out;
}

inline std::vector<std::size_t> std_bmh_search(std::string_view text,
                                               std::string_view pattern) {
    std::vector<std::size_t> out;
    const std::size_t n = text.size(), m = pattern.size();
    if (m == 0) return detail::every_position(n);
    if (m > n) return out;
    const std::boyer_moore_horspool_searcher searcher(pattern.begin(), pattern.end());
    auto it = text.begin();
    while (true) {
        it = std::search(it, text.end(), searcher);
        if (it == text.end()) break;
        out.push_back(static_cast<std::size_t>(it - text.begin()));
        ++it;  // restart one past the hit: overlapping occurrences
    }
    return out;
}

inline std::vector<std::size_t> std_bm_search(std::string_view text,
                                              std::string_view pattern) {
    std::vector<std::size_t> out;
    const std::size_t n = text.size(), m = pattern.size();
    if (m == 0) return detail::every_position(n);
    if (m > n) return out;
    const std::boyer_moore_searcher searcher(pattern.begin(), pattern.end());
    auto it = text.begin();
    while (true) {
        it = std::search(it, text.end(), searcher);
        if (it == text.end()) break;
        out.push_back(static_cast<std::size_t>(it - text.begin()));
        ++it;
    }
    return out;
}

}  // namespace lab
