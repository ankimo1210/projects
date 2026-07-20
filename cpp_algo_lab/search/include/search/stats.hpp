#pragma once
// Shared conventions for all search implementations: the counted-stats
// struct, the tally policies that inject counting into a single templated
// core per algorithm (NoTally's empty inline methods compile to nothing, so
// the timed path pays zero overhead), and the empty-pattern convention.
#include <cstddef>
#include <cstdint>
#include <vector>

namespace lab {

struct SearchStats {
    std::vector<std::size_t> occurrences;
    // Pattern-preprocessing work: KMP failure comparisons, BMH table stores,
    // RK pattern-hash multiply-adds. Unit: elementary char operations.
    std::uint64_t pre_ops = 0;
    // Every access to a text character during the scan (comparisons and hash
    // updates). The fair cross-algorithm cost metric: BMH's sublinearity
    // means text_reads < n.
    std::uint64_t text_reads = 0;
    // Text-vs-pattern char equality tests during the scan. Equal to
    // text_reads for naive/KMP/BMH; for RK only hash hits are verified, so
    // this is near zero unless the hash keeps matching.
    std::uint64_t char_comparisons = 0;
};

struct NoTally {
    void pre() {}
    void read() {}
    void cmp() {}
};

struct Tally {
    SearchStats* st;
    void pre() { ++st->pre_ops; }
    void read() { ++st->text_reads; }
    void cmp() { ++st->char_comparisons; }
};

namespace detail {

// The empty pattern matches at every position, including one past the last
// character: n+1 occurrences {0..n}. Matches string_view::find's behavior.
inline std::vector<std::size_t> every_position(std::size_t n) {
    std::vector<std::size_t> out(n + 1);
    for (std::size_t i = 0; i <= n; ++i) out[i] = i;
    return out;
}

}  // namespace detail

}  // namespace lab
