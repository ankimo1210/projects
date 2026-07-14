#pragma once
// Fixed-width ASCII table for terminal summaries.
#include <iostream>
#include <string>
#include <vector>

namespace lab {

inline void print_table(const std::vector<std::string>& header,
                        const std::vector<std::vector<std::string>>& rows,
                        std::ostream& os = std::cout) {
    std::vector<std::size_t> w(header.size());
    for (std::size_t c = 0; c < header.size(); ++c) w[c] = header[c].size();
    for (const auto& r : rows)
        for (std::size_t c = 0; c < r.size() && c < w.size(); ++c)
            w[c] = std::max(w[c], r[c].size());

    auto line = [&](const std::vector<std::string>& cells) {
        for (std::size_t c = 0; c < w.size(); ++c) {
            const std::string& s = c < cells.size() ? cells[c] : "";
            os << s << std::string(w[c] - s.size() + 2, ' ');
        }
        os << '\n';
    };
    line(header);
    std::string sep;
    for (std::size_t c = 0; c < w.size(); ++c) sep += std::string(w[c], '-') + "  ";
    os << sep << '\n';
    for (const auto& r : rows) line(r);
}

}  // namespace lab
