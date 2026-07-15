// Tests for the string-search module: all-occurrence correctness (including
// overlapping matches and boundary conventions) and exact operation counts of
// the counted variants. Every exact count below was hand-derived in the
// Phase 2 plan; if an implementation change breaks one, re-derive by hand
// before touching the expected value.
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest/doctest.h"

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "lab/textgen.hpp"
#include "search/kmp.hpp"
#include "search/naive.hpp"

using Occ = std::vector<std::size_t>;
using Runner = Occ (*)(std::string_view, std::string_view);

TEST_CASE("naive_search: all occurrences, including overlapping ones") {
    CHECK(lab::naive_search("aaaaaa", "aaa") == Occ{0, 1, 2, 3});
    CHECK(lab::naive_search("ababab", "aba") == Occ{0, 2});
    CHECK(lab::naive_search("banana", "a") == Occ{1, 3, 5});
    CHECK(lab::naive_search("xxab", "ab") == Occ{2});
    CHECK(lab::naive_search("abc", "xyz").empty());
}

TEST_CASE("boundary conventions hold for naive and kmp") {
    const std::vector<Runner> runners = {lab::naive_search, lab::kmp_search};
    for (const Runner run : runners) {
        CHECK(run("abc", "") == Occ{0, 1, 2, 3});  // empty pattern: every position
        CHECK(run("", "") == Occ{0});
        CHECK(run("", "a").empty());
        CHECK(run("ab", "abc").empty());  // pattern longer than text
        CHECK(run("abc", "abc") == Occ{0});
    }
}

TEST_CASE("naive_search_counted: exact counts") {
    {
        const auto st = lab::naive_search_counted("aaaaaa", "aaa");
        CHECK(st.occurrences == Occ{0, 1, 2, 3});
        CHECK(st.pre_ops == 0);           // naive has no preprocessing
        CHECK(st.text_reads == 12);       // 4 alignments x 3 chars, all match
        CHECK(st.char_comparisons == 12);
    }
    {
        const auto st = lab::naive_search_counted("ababab", "aba");
        CHECK(st.occurrences == Occ{0, 2});
        CHECK(st.text_reads == 8);  // 3+1+3+1: full match, 1-char fail, repeat
    }
    {
        // The O(n*m) blowup at unit-test scale: every alignment matches m-1
        // 'a's then fails on 'b' -> (n-m+1)*m text reads.
        const std::string text = lab::generate_text(lab::Text::periodic, 1024, 42);
        const std::string pat = lab::pattern_for(lab::Text::periodic, text, 16, 42);
        const auto st = lab::naive_search_counted(text, pat);
        CHECK(st.occurrences.empty());
        CHECK(st.text_reads == (1024 - 16 + 1) * 16);  // 16144
    }
}

TEST_CASE("kmp_failure: CLRS example ababaca") {
    lab::NoTally t;
    CHECK(lab::detail::kmp_failure(std::string_view("ababaca"), t) ==
          std::vector<std::size_t>{0, 0, 1, 2, 3, 0, 1});
}

TEST_CASE("kmp_search: all occurrences, including overlapping ones") {
    CHECK(lab::kmp_search("aaaaaa", "aaa") == Occ{0, 1, 2, 3});
    CHECK(lab::kmp_search("ababab", "aba") == Occ{0, 2});
    CHECK(lab::kmp_search("banana", "a") == Occ{1, 3, 5});
    CHECK(lab::kmp_search("xxab", "ab") == Occ{2});
    CHECK(lab::kmp_search("abc", "xyz").empty());
}

TEST_CASE("kmp_search_counted: exact counts") {
    {
        // Overlapping matches cost nothing extra: exactly one comparison per
        // text char (n=6) even though there are 4 occurrences.
        const auto st = lab::kmp_search_counted("aaaaaa", "aaa");
        CHECK(st.occurrences == Occ{0, 1, 2, 3});
        CHECK(st.pre_ops == 2);      // failure build: 2 pattern comparisons
        CHECK(st.text_reads == 6);   // one per text char
        CHECK(st.char_comparisons == 6);
    }
    {
        const auto st = lab::kmp_search_counted("ababab", "aba");
        CHECK(st.occurrences == Occ{0, 2});
        CHECK(st.pre_ops == 2);
        CHECK(st.text_reads == 6);
    }
    {
        // Naive's worst case is KMP's home turf: 2n-15 reads instead of ~n*m.
        // Trace: first 15 chars match (15 reads); from then on every text char
        // costs exactly 2 reads (fail on 'b', re-match on 'a' via fail[14]=14).
        const std::string text = lab::generate_text(lab::Text::periodic, 1024, 42);
        const std::string pat = lab::pattern_for(lab::Text::periodic, text, 16, 42);
        const auto st = lab::kmp_search_counted(text, pat);
        CHECK(st.occurrences.empty());
        CHECK(st.pre_ops == 29);  // failure build: 14 matches + 15-step collapse at 'b'
        CHECK(st.text_reads == 2 * 1024 - 15);  // 2033
        CHECK(st.text_reads <= 2 * 1024);       // the classic 2n bound
    }
}

TEST_CASE("kmp agrees with naive on generated corpora") {
    for (const lab::Text t : {lab::Text::dna, lab::Text::ascii_random}) {
        for (const std::uint32_t seed : {42u, 7u}) {
            const std::string text = lab::generate_text(t, 512, seed);
            for (const std::size_t m : {std::size_t{1}, std::size_t{4}, std::size_t{16}}) {
                const std::string pat = lab::pattern_for(t, text, m, seed);
                CHECK(lab::kmp_search(text, pat) == lab::naive_search(text, pat));
            }
        }
    }
}
