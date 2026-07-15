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
#include "search/bmh.hpp"
#include "search/kmp.hpp"
#include "search/naive.hpp"
#include "search/rabin_karp.hpp"

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

TEST_CASE("bmh_search: all occurrences, including overlapping ones") {
    CHECK(lab::bmh_search("aaaaaa", "aaa") == Occ{0, 1, 2, 3});
    CHECK(lab::bmh_search("ababab", "aba") == Occ{0, 2});
    CHECK(lab::bmh_search("banana", "a") == Occ{1, 3, 5});
    CHECK(lab::bmh_search("xxab", "ab") == Occ{2});
    CHECK(lab::bmh_search("abc", "xyz").empty());
}

TEST_CASE("rabin_karp_search: all occurrences, including overlapping ones") {
    CHECK(lab::rabin_karp_search("aaaaaa", "aaa") == Occ{0, 1, 2, 3});
    CHECK(lab::rabin_karp_search("ababab", "aba") == Occ{0, 2});
    CHECK(lab::rabin_karp_search("banana", "a") == Occ{1, 3, 5});
    CHECK(lab::rabin_karp_search("xxab", "ab") == Occ{2});
    CHECK(lab::rabin_karp_search("abc", "xyz").empty());
}

TEST_CASE("boundary conventions hold for bmh and rabin_karp") {
    const std::vector<Runner> runners = {lab::bmh_search, lab::rabin_karp_search};
    for (const Runner run : runners) {
        CHECK(run("abc", "") == Occ{0, 1, 2, 3});
        CHECK(run("", "") == Occ{0});
        CHECK(run("", "a").empty());
        CHECK(run("ab", "abc").empty());
        CHECK(run("abc", "abc") == Occ{0});
    }
}

TEST_CASE("bmh_search_counted: exact counts") {
    {
        // shift['a'] ends at 1 (stores: pattern[0] -> 2, then pattern[1] -> 1),
        // so each of the 4 alignments does 1 last-char read + 2 inner reads.
        const auto st = lab::bmh_search_counted("aaaaaa", "aaa");
        CHECK(st.occurrences == Occ{0, 1, 2, 3});
        CHECK(st.pre_ops == 2);  // m-1 shift-table stores
        CHECK(st.text_reads == 12);
        CHECK(st.char_comparisons == 12);
    }
    {
        // Naive's worst case degrades gracefully for BMH: the last-char probe
        // ('a' vs pattern's 'b') fails immediately at every alignment and
        // shift['a']=1, giving exactly n-m+1 reads -- linear, not quadratic,
        // but no skipping either.
        const std::string text = lab::generate_text(lab::Text::periodic, 1024, 42);
        const std::string pat = lab::pattern_for(lab::Text::periodic, text, 16, 42);
        const auto st = lab::bmh_search_counted(text, pat);
        CHECK(st.occurrences.empty());
        CHECK(st.pre_ops == 15);
        CHECK(st.text_reads == 1024 - 16 + 1);  // 1009
    }
    {
        // The headline property: on realistic text BMH reads FEWER than n
        // characters (sublinear), and far fewer than naive.
        const std::string text = lab::generate_text(lab::Text::dna, 4096, 42);
        const std::string pat = lab::pattern_for(lab::Text::dna, text, 16, 42);
        const auto st = lab::bmh_search_counted(text, pat);
        const auto naive = lab::naive_search_counted(text, pat);
        CHECK(st.occurrences == naive.occurrences);
        CHECK(st.text_reads < 4096);
        CHECK(st.text_reads < naive.text_reads);
    }
}

TEST_CASE("rabin_karp_search_counted: exact counts") {
    {
        // pre = m pattern-hash steps + (m-1) power steps = 5. Reads: first
        // window 3, then per alignment a 3-read verification (hash always
        // hits on all-equal text) and a 2-read slide except after the last.
        const auto st = lab::rabin_karp_search_counted("aaaaaa", "aaa");
        CHECK(st.occurrences == Occ{0, 1, 2, 3});
        CHECK(st.pre_ops == 5);
        CHECK(st.text_reads == 21);  // 3 + 4*3 (verify) + 3*2 (slides)
        CHECK(st.char_comparisons == 12);
    }
    {
        // Immune to naive's worst case: the pattern contains 'b', the text
        // doesn't, so the window hash never equals the pattern hash and NO
        // char comparison ever happens. Reads = m (first window) + 2(n-m).
        const std::string text = lab::generate_text(lab::Text::periodic, 1024, 42);
        const std::string pat = lab::pattern_for(lab::Text::periodic, text, 16, 42);
        const auto st = lab::rabin_karp_search_counted(text, pat);
        CHECK(st.occurrences.empty());
        CHECK(st.pre_ops == 31);
        CHECK(st.text_reads == 16 + 2 * (1024 - 16));  // 2032
        CHECK(st.char_comparisons == 0);
    }
    {
        // RK's OWN worst case: text a^64, pattern a^8 -- every window's hash
        // hits, so every alignment pays the full m-char verification.
        const std::string text(64, 'a');
        const std::string pat(8, 'a');
        const auto st = lab::rabin_karp_search_counted(text, pat);
        CHECK(st.occurrences.size() == 57);  // positions 0..56
        CHECK(st.pre_ops == 15);             // 8 hash steps + 7 power steps
        CHECK(st.text_reads == 8 + 57 * 8 + 56 * 2);  // 576
        CHECK(st.char_comparisons == 57 * 8);         // 456
    }
}
