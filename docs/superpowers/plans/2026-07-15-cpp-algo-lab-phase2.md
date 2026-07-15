# cpp_algo_lab Phase 2 (String Search) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `search/` module of cpp_algo_lab: 4 exact string-matching algorithms (naive / KMP / Boyer-Moore-Horspool / Rabin-Karp) with counted variants, 3 C++17 standard-library baselines, deterministic text/pattern generators, a benchmark producing time and operation-count CSVs over two sweeps (text length n, pattern length m 4→1024), 5 matplotlib figures, and a Japanese learning doc — plus a small Phase-1 backlog hardening task.

**Architecture:** Header-only C++20 (`search/include/search/*.hpp`, one algorithm per header) on top of the existing `common/lab/` infra. Counting is injected via a template *tally policy* (`NoTally` = zero-cost for timing, `Tally` = counter for ops) so each algorithm has exactly one core implementation. New `common/lab/textgen.hpp` mirrors `datagen.hpp`. One benchmark executable writes 3 CSVs; a new `scripts/plot_search.py` renders 5 PNGs, with the shared palette extracted to `scripts/labviz.py`. Spec: `docs/superpowers/specs/2026-07-14-cpp-algo-lab-design.md` §2.2 (this plan covers Phase 2 only).

**Tech Stack:** g++ 13.3 (C++20), GNU make, doctest (already vendored), Python via repo-root uv workspace (pandas / matplotlib) for plotting only.

**Model policy (SDD):** implementers T1–T4, T8 = haiku (verbatim transcription of complete plan code); T5–T6 = sonnet (run benchmarks / verify figures with judgment); T7 = fable (Japanese docs centerpiece). Task reviewers sonnet. Final whole-branch review fable. Branch: `cpp-algo-lab/phase2` from main.

## Global Constraints

- Compiler: `g++` only, `-std=c++20 -Wall -Wextra -Wpedantic`. No cmake, no clang.
- Test builds: `-O1 -g -fsanitize=address,undefined -fno-sanitize-recover=undefined`. Bench builds: `-O2 -DNDEBUG`.
- Only vendored dependency: `third_party/doctest/doctest.h`. No other libraries in C++ code.
- All C++ code, identifiers, comments, and commit messages in English. All `docs/*.md`, `README.md` prose in Japanese.
- Everything lives under `cpp_algo_lab/`. No root-file edits in this phase.
- `make` targets are run from `cpp_algo_lab/` (bench writes CSVs to relative `results/`).
- `results/` CSVs and PNGs are committed. `cpp_algo_lab/.gitignore` already re-includes `!results/**` (do not remove it).
- Python runs via repo root: `uv run --no-sync ...`. Both ruff gates must pass from the repo root: `uv run --no-sync ruff check cpp_algo_lab/scripts` and `uv run --no-sync ruff format --check cpp_algo_lab/scripts`.
- Namespace for all C++ code: `lab`.
- Commit message prefix: `feat(cpp_algo_lab):` / `test(cpp_algo_lab):` / `fix(cpp_algo_lab):` / `docs(cpp_algo_lab):`.
- New test-case additions go into the existing include block / end of file properly — extend the include block at the top of the file, never mid-file (Phase 1 review noise).

## Fixed design values (used across tasks)

- **Public search API** (every implementation, including baselines): `std::vector<std::size_t> X_search(std::string_view text, std::string_view pattern)` returning **all** occurrence start positions in increasing order, **including overlapping ones**.
- **Empty-pattern convention:** the empty pattern matches at every position including the end: return `{0, 1, ..., n}` (n+1 positions). `pattern.size() > text.size()` returns `{}`. This must hold for all 7 implementations.
- **Counted variants** (own 4 algorithms only): `lab::SearchStats X_search_counted(text, pattern)` with fields:
  - `occurrences` — same vector as the plain function,
  - `pre_ops` — elementary pattern-preprocessing operations (KMP: pattern-vs-pattern char comparisons; BMH: shift-table stores, m−1 of them; RK: hash multiply-add steps, m for the pattern hash + m−1 for the power),
  - `text_reads` — every access to a text character during the scan (comparisons **and** hash updates),
  - `char_comparisons` — text-vs-pattern char equality tests during the scan (subset of `text_reads`; equal to it for naive/KMP/BMH, much smaller for RK).
- **Algorithm registry names (exact CSV keys):** `naive`, `kmp`, `bmh`, `rabin_karp`, `sv_find`, `std_bmh`, `std_bm`.
- **Text kinds (exact CSV keys via `text_name`):** `dna` (uniform ACGT), `ascii` (uniform printable 32–126), `english` (words from a fixed list joined by spaces), `periodic` (all `'a'`).
- **Pattern rule:** for `periodic`, the pattern is `a^(m-1) b` (classic naive/RK worst case; never occurs). For all other kinds, the pattern is a random substring of the text (guarantees ≥ 1 occurrence).
- **Bench sweeps (seed 42, repeats 5, median):**
  - n sweep at m=16: n ∈ {4096, 16384, 65536, 262144, 1048576, 4194304}
  - m sweep at n=1048576 (=2^20): m ∈ {4, 8, 16, 32, 64, 128, 256, 512, 1024}
  - `--quick`: n ∈ {4096, 65536} at m=16; m ∈ {4, 32} at n=65536; repeats 2.
- **CSV schemas:**
  - `results/search_times_n.csv` and `results/search_times_m.csv`: `algo,text,n,m,repeats,median_ms,occurrences`
  - `results/search_ops.csv`: `algo,text,sweep,n,m,occurrences,pre_ops,text_reads,char_comparisons` (sweep ∈ {`n`,`m`}; own 4 algorithms only)
- **Rabin-Karp constants:** base 257, modulus 1'000'000'007 (all arithmetic in `std::uint64_t`; max intermediate ≈ 2.57e11, far below 2^63).
- **Chart palette:** own algorithms keep entity-stable colors everywhere: naive `#2a78d6`, kmp `#1baf7a`, bmh `#eda100`, rabin_karp `#008300`. The 3 std baselines are all `#898781` (MUTED) distinguished by linestyle: sv_find `--`, std_bmh `-.`, std_bm `:`. Sequential ramp / surface / ink colors identical to Phase 1 (extracted into `scripts/labviz.py` in Task 6).

---

### Task 1: Text and pattern generators (`textgen.hpp`)

**Files:**
- Create: `cpp_algo_lab/common/lab/textgen.hpp`
- Modify: `cpp_algo_lab/common/tests/test_common.cpp` (append test cases; add includes to the top include block)

**Interfaces:**
- Consumes: nothing new (`<random>`, `<string>`).
- Produces (used by Tasks 2–5):
  - `enum class Text { dna, ascii_random, english_like, periodic };`
  - `constexpr std::array<Text, 4> all_texts();`
  - `std::string_view text_name(Text)` → exactly `"dna"`, `"ascii"`, `"english"`, `"periodic"`.
  - `std::string generate_text(Text t, std::size_t n, std::uint32_t seed)` — exactly n chars, deterministic.
  - `std::string pattern_for(Text t, const std::string& text, std::size_t m, std::uint32_t seed)` — deterministic; throws `std::invalid_argument` if `m > text.size()`; returns `""` for m=0; periodic → `a^(m-1) b`; otherwise a random substring of `text`.

- [ ] **Step 1: Append failing tests to `common/tests/test_common.cpp`**

Add `#include "lab/textgen.hpp"` and `#include <string>` to the include block at the top of the file (keep the block alphabetized as it is now). Append at the end of the file:

```cpp
TEST_CASE("textgen: text_name returns the exact CSV keys") {
    CHECK(lab::text_name(lab::Text::dna) == "dna");
    CHECK(lab::text_name(lab::Text::ascii_random) == "ascii");
    CHECK(lab::text_name(lab::Text::english_like) == "english");
    CHECK(lab::text_name(lab::Text::periodic) == "periodic");
    CHECK(lab::all_texts().size() == 4);
}

TEST_CASE("textgen: exact sizes, determinism, alphabets") {
    for (const lab::Text t : lab::all_texts()) {
        CHECK(lab::generate_text(t, 0, 42).empty());
        const std::string a = lab::generate_text(t, 1000, 42);
        const std::string b = lab::generate_text(t, 1000, 42);
        CHECK(a.size() == 1000);
        CHECK(a == b);  // same seed, same text
    }
    // different seeds give different text (checked on the random kinds)
    CHECK(lab::generate_text(lab::Text::dna, 64, 42) != lab::generate_text(lab::Text::dna, 64, 43));

    for (char c : lab::generate_text(lab::Text::dna, 500, 42))
        CHECK(std::string_view("ACGT").find(c) != std::string_view::npos);
    for (char c : lab::generate_text(lab::Text::ascii_random, 500, 42)) {
        CHECK(c >= 32);
        CHECK(c <= 126);
    }
    for (char c : lab::generate_text(lab::Text::english_like, 500, 42))
        CHECK(((c >= 'a' && c <= 'z') || c == ' '));
    for (char c : lab::generate_text(lab::Text::periodic, 500, 42)) CHECK(c == 'a');
}

TEST_CASE("textgen: pattern_for rules") {
    const std::string text = lab::generate_text(lab::Text::dna, 4096, 42);
    const std::string pat = lab::pattern_for(lab::Text::dna, text, 16, 42);
    CHECK(pat.size() == 16);
    CHECK(text.find(pat) != std::string::npos);  // sampled patterns occur in the text
    CHECK(pat == lab::pattern_for(lab::Text::dna, text, 16, 42));  // deterministic

    const std::string ptext = lab::generate_text(lab::Text::periodic, 64, 42);
    CHECK(lab::pattern_for(lab::Text::periodic, ptext, 16, 42) == "aaaaaaaaaaaaaaab");
    CHECK(lab::pattern_for(lab::Text::periodic, ptext, 1, 42) == "b");

    CHECK(lab::pattern_for(lab::Text::dna, text, 0, 42).empty());
    CHECK_THROWS_AS(lab::pattern_for(lab::Text::dna, text, text.size() + 1, 42),
                    std::invalid_argument);
}
```

- [ ] **Step 2: Run to verify failure**

Run from `cpp_algo_lab/`: `make test`
Expected: FAIL to compile — `lab/textgen.hpp: No such file or directory`.

- [ ] **Step 3: Implement `common/lab/textgen.hpp`**

```cpp
#pragma once
// Deterministic text and pattern generators for the search benchmarks.
// Four text kinds: dna (sigma=4), ascii (printable), english-like (word
// stream), periodic (all 'a' -- with pattern a^(m-1) b this is the classic
// naive / Rabin-Karp worst case and KMP's home turf).
#include <array>
#include <cstddef>
#include <cstdint>
#include <random>
#include <stdexcept>
#include <string>
#include <string_view>

namespace lab {

enum class Text { dna, ascii_random, english_like, periodic };

inline constexpr std::array<Text, 4> all_texts() {
    return {Text::dna, Text::ascii_random, Text::english_like, Text::periodic};
}

inline std::string_view text_name(Text t) {
    switch (t) {
        case Text::dna: return "dna";
        case Text::ascii_random: return "ascii";
        case Text::english_like: return "english";
        case Text::periodic: return "periodic";
    }
    return "unknown";
}

inline constexpr std::array<std::string_view, 32> kEnglishWords = {
    "the",  "of",   "and",  "to",   "in",   "is",   "that", "it",
    "was",  "for",  "on",   "are",  "with", "as",   "at",   "be",
    "this", "have", "from", "or",   "one",  "had",  "by",   "word",
    "but",  "not",  "what", "all",  "were", "when", "we",   "there"};

inline std::string generate_text(Text t, std::size_t n, std::uint32_t seed) {
    std::string s;
    s.reserve(n);
    std::mt19937 rng(seed);
    switch (t) {
        case Text::dna: {
            constexpr std::string_view abc = "ACGT";
            std::uniform_int_distribution<std::size_t> u(0, abc.size() - 1);
            for (std::size_t i = 0; i < n; ++i) s.push_back(abc[u(rng)]);
            break;
        }
        case Text::ascii_random: {
            std::uniform_int_distribution<int> u(32, 126);
            for (std::size_t i = 0; i < n; ++i) s.push_back(static_cast<char>(u(rng)));
            break;
        }
        case Text::english_like: {
            std::uniform_int_distribution<std::size_t> u(0, kEnglishWords.size() - 1);
            while (s.size() < n) {
                s.append(kEnglishWords[u(rng)]);
                s.push_back(' ');
            }
            s.resize(n);
            break;
        }
        case Text::periodic:
            s.assign(n, 'a');
            break;
    }
    return s;
}

inline std::string pattern_for(Text t, const std::string& text, std::size_t m,
                               std::uint32_t seed) {
    if (m == 0) return {};
    if (t == Text::periodic) {
        std::string p(m, 'a');
        p.back() = 'b';  // never occurs in the all-'a' text
        return p;
    }
    if (m > text.size()) throw std::invalid_argument("pattern_for: m > text size");
    std::mt19937 rng(seed ^ 0x9e3779b9u);  // decouple from the text's stream
    std::uniform_int_distribution<std::size_t> pos(0, text.size() - m);
    return text.substr(pos(rng), m);
}

}  // namespace lab
```

- [ ] **Step 4: Run to verify pass**

Run from `cpp_algo_lab/`: `make test`
Expected: both existing binaries (test_common, test_sorting) run and report SUCCESS. The new textgen cases appear in test_common's case count.

- [ ] **Step 5: Commit**

```bash
git add cpp_algo_lab/common/lab/textgen.hpp cpp_algo_lab/common/tests/test_common.cpp
git commit -m "feat(cpp_algo_lab): add deterministic text/pattern generators for search"
```

---

### Task 2: Search conventions + naive + KMP (`stats.hpp`, `naive.hpp`, `kmp.hpp`)

**Files:**
- Create: `cpp_algo_lab/search/include/search/stats.hpp`
- Create: `cpp_algo_lab/search/include/search/naive.hpp`
- Create: `cpp_algo_lab/search/include/search/kmp.hpp`
- Create: `cpp_algo_lab/search/tests/test_search.cpp`
- Modify: `cpp_algo_lab/Makefile` (full replacement below: search include root + test_search binary)

**Interfaces:**
- Consumes: `lab::generate_text` / `lab::pattern_for` (Task 1).
- Produces (used by Tasks 3–5):
  - `struct lab::SearchStats { std::vector<std::size_t> occurrences; std::uint64_t pre_ops, text_reads, char_comparisons; }`
  - Tally policies `lab::NoTally` / `lab::Tally` with methods `pre()`, `read()`, `cmp()`.
  - `lab::detail::every_position(n)` → `{0..n}` (the shared empty-pattern result).
  - `lab::naive_search`, `lab::naive_search_counted`, `lab::kmp_search`, `lab::kmp_search_counted` with the fixed signatures.
  - `lab::detail::kmp_failure(pattern, tally)` → prefix-function vector (tested directly; the failure table is itself a learning object).

- [ ] **Step 1: Create the test file `search/tests/test_search.cpp` (failing: headers don't exist yet)**

```cpp
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
```

- [ ] **Step 2: Replace `cpp_algo_lab/Makefile` with this full content (adds `-Isearch/include`, `SEARCH_HDRS`, `test_search`)**

```make
# cpp_algo_lab — build/test/bench/plot. Run make from this directory.
.DEFAULT_GOAL := test
CXX      := g++
STD      := -std=c++20
WARN     := -Wall -Wextra -Wpedantic
INC      := -Icommon -Isorting/include -Isearch/include -Ithird_party
TESTFLAGS  := $(STD) $(WARN) $(INC) -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=undefined
BENCHFLAGS := $(STD) $(WARN) $(INC) -O2 -DNDEBUG
BUILD    := build

COMMON_HDRS  := $(wildcard common/lab/*.hpp)
SORT_HDRS    := $(wildcard sorting/include/sorting/*.hpp)
SEARCH_HDRS  := $(wildcard search/include/search/*.hpp)

.PHONY: all test bench bench-quick trace plot clean

all: $(BUILD)/test_common $(BUILD)/test_sorting $(BUILD)/test_search $(BUILD)/bench_sorting

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/test_common: common/tests/test_common.cpp $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $< -o $@

$(BUILD)/test_sorting: sorting/tests/test_sorting.cpp $(SORT_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $< -o $@

$(BUILD)/test_search: search/tests/test_search.cpp $(SEARCH_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $< -o $@

$(BUILD)/bench_sorting: sorting/bench/bench_sorting.cpp $(SORT_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(BENCHFLAGS) $< -o $@

test: $(BUILD)/test_common $(BUILD)/test_sorting $(BUILD)/test_search
	$(BUILD)/test_common
	$(BUILD)/test_sorting
	$(BUILD)/test_search

bench: $(BUILD)/bench_sorting
	$(BUILD)/bench_sorting

bench-quick: $(BUILD)/bench_sorting
	$(BUILD)/bench_sorting --quick

trace: $(BUILD)/bench_sorting
	$(BUILD)/bench_sorting --trace

plot:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_results.py

clean:
	rm -rf $(BUILD)
```

- [ ] **Step 3: Run to verify failure**

Run from `cpp_algo_lab/`: `make test`
Expected: FAIL to compile test_search — `search/naive.hpp: No such file or directory`.

- [ ] **Step 4: Implement `search/include/search/stats.hpp`**

```cpp
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
```

- [ ] **Step 5: Implement `search/include/search/naive.hpp`**

```cpp
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
```

- [ ] **Step 6: Implement `search/include/search/kmp.hpp`**

```cpp
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
```

- [ ] **Step 7: Run to verify pass**

Run from `cpp_algo_lab/`: `make test`
Expected: all three binaries build and report SUCCESS (test_search runs the new cases). ASan/UBSan silent.

- [ ] **Step 8: Commit**

```bash
git add cpp_algo_lab/search cpp_algo_lab/Makefile
git commit -m "feat(cpp_algo_lab): add naive and KMP search with counted variants"
```

---

### Task 3: Boyer-Moore-Horspool + Rabin-Karp (`bmh.hpp`, `rabin_karp.hpp`)

**Files:**
- Create: `cpp_algo_lab/search/include/search/bmh.hpp`
- Create: `cpp_algo_lab/search/include/search/rabin_karp.hpp`
- Modify: `cpp_algo_lab/search/tests/test_search.cpp` (append; add the two includes to the top include block)

**Interfaces:**
- Consumes: `SearchStats`, tally policies, `detail::every_position` (Task 2).
- Produces: `lab::bmh_search`, `lab::bmh_search_counted`, `lab::rabin_karp_search`, `lab::rabin_karp_search_counted` with the fixed signatures; constants `lab::kRkBase = 257`, `lab::kRkMod = 1'000'000'007`.

- [ ] **Step 1: Append failing tests to `search/tests/test_search.cpp`**

Add to the include block: `#include "search/bmh.hpp"` and `#include "search/rabin_karp.hpp"` (alphabetical: bmh before kmp, rabin_karp after naive). Append at the end:

```cpp
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
```

- [ ] **Step 2: Run to verify failure**

Run from `cpp_algo_lab/`: `make test`
Expected: FAIL to compile — `search/bmh.hpp: No such file or directory`.

- [ ] **Step 3: Implement `search/include/search/bmh.hpp`**

```cpp
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
```

- [ ] **Step 4: Implement `search/include/search/rabin_karp.hpp`**

```cpp
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
```

- [ ] **Step 5: Run to verify pass**

Run from `cpp_algo_lab/`: `make test`
Expected: all three binaries SUCCESS.

- [ ] **Step 6: Commit**

```bash
git add cpp_algo_lab/search
git commit -m "feat(cpp_algo_lab): add BMH and Rabin-Karp search with counted variants"
```

---

### Task 4: Standard-library baselines + umbrella header + cross-implementation conformance

**Files:**
- Create: `cpp_algo_lab/search/include/search/baselines.hpp`
- Create: `cpp_algo_lab/search/include/search/all.hpp`
- Modify: `cpp_algo_lab/search/tests/test_search.cpp` (append; switch the search includes to `search/all.hpp`)

**Interfaces:**
- Consumes: everything from Tasks 2–3; `lab::all_texts`/`generate_text`/`pattern_for` (Task 1).
- Produces (used by Task 5): `lab::sv_find_search`, `lab::std_bmh_search`, `lab::std_bm_search` (same fixed signature; no counted variants — the standard searchers cannot be instrumented); `search/all.hpp` umbrella.

- [ ] **Step 1: Append failing tests**

In the include block of `test_search.cpp`, replace the four `#include "search/..."` lines with a single `#include "search/all.hpp"`. Append at the end:

```cpp
TEST_CASE("boundary conventions hold for the std baselines") {
    const std::vector<Runner> runners = {lab::sv_find_search, lab::std_bmh_search,
                                         lab::std_bm_search};
    for (const Runner run : runners) {
        CHECK(run("abc", "") == Occ{0, 1, 2, 3});
        CHECK(run("", "") == Occ{0});
        CHECK(run("", "a").empty());
        CHECK(run("ab", "abc").empty());
        CHECK(run("abc", "abc") == Occ{0});
        CHECK(run("aaaaaa", "aaa") == Occ{0, 1, 2, 3});  // overlapping via pos+1 restart
        CHECK(run("xxab", "ab") == Occ{2});              // match at the very end
    }
}

TEST_CASE("all implementations agree with naive on generated corpora") {
    const std::vector<std::pair<std::string, Runner>> algos = {
        {"kmp", lab::kmp_search},         {"bmh", lab::bmh_search},
        {"rabin_karp", lab::rabin_karp_search}, {"sv_find", lab::sv_find_search},
        {"std_bmh", lab::std_bmh_search}, {"std_bm", lab::std_bm_search},
    };
    const std::vector<std::size_t> sizes = {1, 2, 64, 1024, 4096};
    const std::vector<std::size_t> pat_lens = {1, 4, 16};
    for (const lab::Text t : lab::all_texts()) {
        for (const std::size_t n : sizes) {
            for (const std::uint32_t seed : {42u, 7u}) {
                const std::string text = lab::generate_text(t, n, seed);
                for (const std::size_t m : pat_lens) {
                    if (m > n) continue;
                    const std::string pattern = lab::pattern_for(t, text, m, seed);
                    const Occ ref = lab::naive_search(text, pattern);
                    for (const auto& [name, run] : algos) {
                        INFO(name << " text=" << lab::text_name(t) << " n=" << n
                                  << " m=" << m << " seed=" << seed);
                        CHECK(run(text, pattern) == ref);
                    }
                    // counted variants return identical occurrences
                    CHECK(lab::naive_search_counted(text, pattern).occurrences == ref);
                    CHECK(lab::kmp_search_counted(text, pattern).occurrences == ref);
                    CHECK(lab::bmh_search_counted(text, pattern).occurrences == ref);
                    CHECK(lab::rabin_karp_search_counted(text, pattern).occurrences == ref);
                }
                // a pattern absent from every generator's alphabet
                const std::string absent(3, '\x01');
                const Occ ref = lab::naive_search(text, absent);
                CHECK(ref.empty());
                for (const auto& [name, run] : algos) {
                    INFO(name << " absent-pattern text=" << lab::text_name(t) << " n=" << n);
                    CHECK(run(text, absent) == ref);
                }
            }
        }
    }
}
```

Also add `#include <utility>` to the standard-includes block (for `std::pair`).

- [ ] **Step 2: Run to verify failure**

Run from `cpp_algo_lab/`: `make test`
Expected: FAIL to compile — `search/all.hpp: No such file or directory`.

- [ ] **Step 3: Implement `search/include/search/baselines.hpp`**

```cpp
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
```

- [ ] **Step 4: Implement `search/include/search/all.hpp`**

```cpp
#pragma once
// Umbrella header for the search module.
#include "search/baselines.hpp"
#include "search/bmh.hpp"
#include "search/kmp.hpp"
#include "search/naive.hpp"
#include "search/rabin_karp.hpp"
#include "search/stats.hpp"
```

- [ ] **Step 5: Run to verify pass**

Run from `cpp_algo_lab/`: `make test`
Expected: all three binaries SUCCESS. The conformance case alone contributes several thousand assertions.

- [ ] **Step 6: Commit**

```bash
git add cpp_algo_lab/search
git commit -m "feat(cpp_algo_lab): add std searcher baselines and cross-implementation conformance tests"
```

---

### Task 5: Search benchmark (`bench_search.cpp`) + full sweep + committed CSVs

**Files:**
- Create: `cpp_algo_lab/search/bench/bench_search.cpp`
- Modify: `cpp_algo_lab/Makefile` (full replacement below: bench_search binary, `bench` becomes sorting+search, `bench-search` / `bench-search-quick` targets)
- Create (generated, committed): `cpp_algo_lab/results/search_times_n.csv`, `cpp_algo_lab/results/search_times_m.csv`, `cpp_algo_lab/results/search_ops.csv`

**Interfaces:**
- Consumes: `search/all.hpp`, `lab/textgen.hpp`, `lab/{csv,table,timer}.hpp`.
- Produces: the three CSVs with the exact schemas from Fixed design values (Task 6 plots read them; Task 7 docs quote them).

- [ ] **Step 1: Implement `search/bench/bench_search.cpp`**

```cpp
// Search benchmark: wall-clock times for the 4 own implementations plus 3
// standard-library baselines, and elementary-operation counts for the own
// ones -> results/search_*.csv. Two sweeps: text length n (m=16 fixed) and
// pattern length m 4..1024 (n=2^20 fixed). The timed lambda includes the
// occurrence-vector allocation: returning every match is part of the job.
// Run from cpp_algo_lab/. Full run takes ~2-3 minutes.
#include <cstddef>
#include <cstring>
#include <functional>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

#include "lab/csv.hpp"
#include "lab/table.hpp"
#include "lab/textgen.hpp"
#include "lab/timer.hpp"
#include "search/all.hpp"

namespace {

using Occurrences = std::vector<std::size_t>;

struct SearchAlgo {
    std::string name;
    std::function<Occurrences(std::string_view, std::string_view)> run;
    // Null for the std baselines: they cannot be instrumented.
    std::function<lab::SearchStats(std::string_view, std::string_view)> run_counted;
};

std::vector<SearchAlgo> make_registry() {
    return {
        {"naive", lab::naive_search, lab::naive_search_counted},
        {"kmp", lab::kmp_search, lab::kmp_search_counted},
        {"bmh", lab::bmh_search, lab::bmh_search_counted},
        {"rabin_karp", lab::rabin_karp_search, lab::rabin_karp_search_counted},
        {"sv_find", lab::sv_find_search, nullptr},
        {"std_bmh", lab::std_bmh_search, nullptr},
        {"std_bm", lab::std_bm_search, nullptr},
    };
}

struct SweepPoint {
    std::size_t n, m;
};

void run_sweep(const std::string& sweep_name, lab::CsvWriter& times, lab::CsvWriter& ops,
               const std::vector<SweepPoint>& points, int repeats,
               std::vector<std::vector<std::string>>* summary_rows, std::size_t summary_n,
               std::size_t summary_m) {
    const auto registry = make_registry();
    for (const lab::Text t : lab::all_texts()) {
        for (const auto [n, m] : points) {
            const std::string text = lab::generate_text(t, n, 42);
            const std::string pattern = lab::pattern_for(t, text, m, 42);
            const Occurrences reference = lab::naive_search(text, pattern);
            for (const auto& a : registry) {
                std::vector<double> ts;
                for (int r = 0; r < repeats; ++r) {
                    Occurrences occ;
                    ts.push_back(lab::time_ms([&] { occ = a.run(text, pattern); }));
                    if (r == 0 && occ != reference) {
                        std::cerr << "FATAL: " << a.name << " disagrees with naive (text="
                                  << lab::text_name(t) << " n=" << n << " m=" << m << ")\n";
                        std::exit(1);
                    }
                }
                const double med = lab::median(ts);
                times.write_row({a.name, std::string(lab::text_name(t)), lab::cell(n),
                                 lab::cell(m), lab::cell(repeats), lab::cell(med),
                                 lab::cell(reference.size())});
                if (a.run_counted) {
                    const lab::SearchStats st = a.run_counted(text, pattern);
                    ops.write_row({a.name, std::string(lab::text_name(t)), sweep_name,
                                   lab::cell(n), lab::cell(m),
                                   lab::cell(st.occurrences.size()), lab::cell(st.pre_ops),
                                   lab::cell(st.text_reads), lab::cell(st.char_comparisons)});
                }
                if (summary_rows != nullptr && n == summary_n && m == summary_m)
                    summary_rows->push_back({std::string(lab::text_name(t)), a.name,
                                             lab::cell(med), lab::cell(reference.size())});
            }
        }
        std::cout << "done: " << lab::text_name(t) << " (" << sweep_name << " sweep)\n";
    }
}

void run_bench(bool quick) {
    const int repeats = quick ? 2 : 5;
    lab::CsvWriter times_n("results/search_times_n.csv",
                           {"algo", "text", "n", "m", "repeats", "median_ms", "occurrences"});
    lab::CsvWriter times_m("results/search_times_m.csv",
                           {"algo", "text", "n", "m", "repeats", "median_ms", "occurrences"});
    lab::CsvWriter ops("results/search_ops.csv",
                       {"algo", "text", "sweep", "n", "m", "occurrences", "pre_ops",
                        "text_reads", "char_comparisons"});

    const std::size_t fixed_m = 16;
    const std::size_t fixed_n = quick ? 65536 : (std::size_t{1} << 20);
    std::vector<SweepPoint> n_points, m_points;
    for (const std::size_t n :
         quick ? std::vector<std::size_t>{4096, 65536}
               : std::vector<std::size_t>{4096, 16384, 65536, 262144, 1048576, 4194304})
        n_points.push_back({n, fixed_m});
    for (const std::size_t m :
         quick ? std::vector<std::size_t>{4, 32}
               : std::vector<std::size_t>{4, 8, 16, 32, 64, 128, 256, 512, 1024})
        m_points.push_back({fixed_n, m});
    const std::size_t summary_m = quick ? 4 : fixed_m;

    std::vector<std::vector<std::string>> summary_rows;
    run_sweep("n", times_n, ops, n_points, repeats, nullptr, 0, 0);
    run_sweep("m", times_m, ops, m_points, repeats, &summary_rows, fixed_n, summary_m);

    std::cout << "\nMedian time at n=" << fixed_n << ", m=" << summary_m << ":\n";
    lab::print_table({"text", "algo", "median_ms", "occurrences"}, summary_rows);
    std::cout << "\nCSV written to results/search_{times_n,times_m,ops}.csv\n";
}

}  // namespace

int main(int argc, char** argv) {
    bool quick = false;
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "--quick") == 0) quick = true;
    run_bench(quick);
    return 0;
}
```

- [ ] **Step 2: Replace `cpp_algo_lab/Makefile` with this full content**

```make
# cpp_algo_lab — build/test/bench/plot. Run make from this directory.
.DEFAULT_GOAL := test
CXX      := g++
STD      := -std=c++20
WARN     := -Wall -Wextra -Wpedantic
INC      := -Icommon -Isorting/include -Isearch/include -Ithird_party
TESTFLAGS  := $(STD) $(WARN) $(INC) -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=undefined
BENCHFLAGS := $(STD) $(WARN) $(INC) -O2 -DNDEBUG
BUILD    := build

COMMON_HDRS  := $(wildcard common/lab/*.hpp)
SORT_HDRS    := $(wildcard sorting/include/sorting/*.hpp)
SEARCH_HDRS  := $(wildcard search/include/search/*.hpp)

.PHONY: all test bench bench-sorting bench-search bench-quick bench-search-quick trace plot clean

all: $(BUILD)/test_common $(BUILD)/test_sorting $(BUILD)/test_search $(BUILD)/bench_sorting $(BUILD)/bench_search

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/test_common: common/tests/test_common.cpp $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $< -o $@

$(BUILD)/test_sorting: sorting/tests/test_sorting.cpp $(SORT_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $< -o $@

$(BUILD)/test_search: search/tests/test_search.cpp $(SEARCH_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $< -o $@

$(BUILD)/bench_sorting: sorting/bench/bench_sorting.cpp $(SORT_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(BENCHFLAGS) $< -o $@

$(BUILD)/bench_search: search/bench/bench_search.cpp $(SEARCH_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(BENCHFLAGS) $< -o $@

test: $(BUILD)/test_common $(BUILD)/test_sorting $(BUILD)/test_search
	$(BUILD)/test_common
	$(BUILD)/test_sorting
	$(BUILD)/test_search

bench: bench-sorting bench-search

bench-sorting: $(BUILD)/bench_sorting
	$(BUILD)/bench_sorting

bench-search: $(BUILD)/bench_search
	$(BUILD)/bench_search

bench-quick: $(BUILD)/bench_sorting
	$(BUILD)/bench_sorting --quick

bench-search-quick: $(BUILD)/bench_search
	$(BUILD)/bench_search --quick

trace: $(BUILD)/bench_sorting
	$(BUILD)/bench_sorting --trace

plot:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_results.py

clean:
	rm -rf $(BUILD)
```

- [ ] **Step 3: Wire check with the quick sweep**

Run from `cpp_algo_lab/`: `make bench-search-quick`
Expected: builds warning-free; prints `done: dna (n sweep)` … through `periodic (m sweep)`, a summary table, and the CSV message. No FATAL lines.

Verify the quick CSVs are well-formed (run from repo root):

```bash
python3 - <<'EOF'
import csv
for f, cols in [("cpp_algo_lab/results/search_times_n.csv", 7),
                ("cpp_algo_lab/results/search_times_m.csv", 7),
                ("cpp_algo_lab/results/search_ops.csv", 9)]:
    rows = list(csv.reader(open(f)))
    assert all(len(r) == cols for r in rows), f
    print(f, len(rows), "rows ok")
EOF
```

Expected: quick run → times_n 57 rows (1 header + 4 texts × 2 n × 7 algos), times_m 57, ops 65 (1 + 4×4×4).

- [ ] **Step 4: Run the FULL sweep (this is the committed data)**

Run from `cpp_algo_lab/`: `make bench-search`
Expected: ~2–3 minutes. Expected row counts (with header): `search_times_n.csv` 169 (4 texts × 6 n × 7 algos + 1), `search_times_m.csv` 253 (4 × 9 × 7 + 1), `search_ops.csv` 241 (4 × (6+9) × 4 + 1).

Sanity-check the physics before committing (from repo root):

```bash
python3 - <<'EOF'
import csv
ops = list(csv.DictReader(open("cpp_algo_lab/results/search_ops.csv")))
# 1) naive on periodic, m sweep: text_reads == (n-m+1)*m exactly
for r in ops:
    if r["algo"] == "naive" and r["text"] == "periodic" and r["sweep"] == "m":
        n, m = int(r["n"]), int(r["m"])
        assert int(r["text_reads"]) == (n - m + 1) * m, r
# 2) kmp: text_reads <= 2n everywhere
for r in ops:
    if r["algo"] == "kmp":
        assert int(r["text_reads"]) <= 2 * int(r["n"]), r
# 3) bmh sublinear on dna at large m: reads/n < 0.5 at m>=64
for r in ops:
    if r["algo"] == "bmh" and r["text"] == "dna" and r["sweep"] == "m" and int(r["m"]) >= 64:
        assert int(r["text_reads"]) < 0.5 * int(r["n"]), r
print("physics ok")
EOF
```

Expected: `physics ok`.

- [ ] **Step 5: Commit (code + Makefile + full-sweep CSVs)**

```bash
git add cpp_algo_lab/search/bench cpp_algo_lab/Makefile cpp_algo_lab/results/search_times_n.csv cpp_algo_lab/results/search_times_m.csv cpp_algo_lab/results/search_ops.csv
git commit -m "feat(cpp_algo_lab): add search benchmark and commit full-sweep results"
```

Confirm with `git show --stat HEAD` that all three CSVs are in the commit (the root `.gitignore` ignores `*.csv` globally; `cpp_algo_lab/.gitignore`'s `!results/**` re-includes them — if a CSV is missing, that re-include was broken).

---

### Task 6: Figures — `labviz.py` extraction + `plot_search.py` (5 PNGs)

**Files:**
- Create: `cpp_algo_lab/scripts/labviz.py`
- Modify: `cpp_algo_lab/scripts/plot_results.py` (import the shared style; derive OPS_COLOR from slots — closes a Phase 1 review follow-up)
- Create: `cpp_algo_lab/scripts/plot_search.py`
- Modify: `cpp_algo_lab/Makefile` (full replacement of the `plot` section: `plot` = `plot-sorting` + `plot-search`)
- Create (generated, committed): `cpp_algo_lab/results/plots/search_time_vs_n.png`, `search_time_vs_m.png`, `search_reads_per_char.png`, `search_pre_vs_match.png`, `search_heatmap.png`

**Interfaces:**
- Consumes: the three CSVs from Task 5.
- Produces: `labviz` module (`SLOTS`, `SLOTS7`, `SEQ_CMAP`, palette constants, `apply_style()`, `save(fig, plots_dir, name)`, `slope_label(x, y, var="n")`) used by both plot scripts.

- [ ] **Step 1: Create `cpp_algo_lab/scripts/labviz.py`**

```python
"""Shared dataviz style for cpp_algo_lab plot scripts.

The dataviz reference palette (light mode) validated in Phase 1, plus small
helpers used by plot_results.py (sorting) and plot_search.py (search).
Import this module only after calling matplotlib.use("Agg") -- it imports
matplotlib.pyplot at module level.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
# Categorical series slots in validated fixed order; SLOTS7 extends them for
# figures that pool many series on one axes.
SLOTS = ["#2a78d6", "#1baf7a", "#eda100", "#008300"]
SLOTS7 = [*SLOTS, "#4a3aa7", "#e34948", "#e87ba4"]
SEQ_STEPS = [
    "#cde2fb",
    "#b7d3f6",
    "#9ec5f4",
    "#86b6ef",
    "#6da7ec",
    "#5598e7",
    "#3987e5",
    "#2a78d6",
    "#256abf",
    "#1c5cab",
    "#184f95",
    "#104281",
    "#0d366b",
]
SEQ_CMAP = LinearSegmentedColormap.from_list("lab_blue", SEQ_STEPS)


def apply_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "text.color": INK,
            "axes.labelcolor": INK_2,
            "axes.edgecolor": BASELINE,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "axes.grid": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "lines.linewidth": 2.0,
            "font.size": 10,
            "axes.titlesize": 11,
        }
    )


def save(fig: plt.Figure, plots_dir: Path, name: str) -> None:
    plots_dir.mkdir(parents=True, exist_ok=True)
    out = plots_dir / name
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")


def slope_label(x: np.ndarray, y: np.ndarray, var: str = "n") -> str:
    """Empirical exponent from the last 3 points of a log-log series."""
    if len(x) < 3 or np.any(y[-3:] <= 0):
        return ""
    k = np.polyfit(np.log(x[-3:]), np.log(y[-3:]), 1)[0]
    return f" {var}^{k:.2f}"
```

- [ ] **Step 2: Refactor `plot_results.py` onto labviz (5 edits)**

Edit 1 — replace the import block after `matplotlib.use("Agg")` (currently `import matplotlib.pyplot as plt` … `from matplotlib.colors import LinearSegmentedColormap, LogNorm`) with:

```python
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from labviz import BASELINE, INK, INK_2, MUTED, SEQ_CMAP, SLOTS, SLOTS7, apply_style
from labviz import save as labviz_save
from labviz import slope_label
from matplotlib.colors import LogNorm
```

Edit 2 — delete the entire palette block (from `# --- dataviz reference palette` through the `SEQ_CMAP = ...` line, i.e. the definitions of SURFACE/INK/INK_2/MUTED/GRID/BASELINE/SLOTS/SEQ_STEPS/SEQ_CMAP).

Edit 3 — replace the hardcoded `OPS_COLOR = { ... }` dict (7 hex entries) with:

```python
# fig_ops pools all comparison sorts on one axes, so per-family slot colors
# would collide (bubble and merge both slot 1). Give that figure its own
# assignment: the extended slot order. The quadratic family keeps the same
# colors as everywhere else.
OPS_COLOR = dict(
    zip(["bubble", "insertion", "selection", "shell", "merge", "quick", "heap"], SLOTS7,
        strict=True)
)
```

Edit 4 — replace the whole `plt.rcParams.update({...})` block with a single line:

```python
apply_style()
```

Edit 5 — replace the body of `save` with a delegation to labviz:

```python
def save(fig: plt.Figure, name: str) -> None:
    labviz_save(fig, PLOTS, name)
```

and delete the local `slope_label` function definition (it now comes from labviz).

- [ ] **Step 3: Verify sorting plots are unchanged**

From repo root:

```bash
uv run --no-sync python cpp_algo_lab/scripts/plot_results.py
git status --short cpp_algo_lab/results/plots
```

Expected: 6 `wrote ...` lines and **no modified PNGs** in git status (the refactor is behavior-preserving; matplotlib output is deterministic). If any sorting PNG shows as modified, open it, verify it is visually identical, and `git checkout -- <file>` to keep the committed one; report this in your notes.

- [ ] **Step 4: Create `cpp_algo_lab/scripts/plot_search.py`**

```python
"""Render search benchmark CSVs into PNG figures.

Run from repo root:  uv run --no-sync python cpp_algo_lab/scripts/plot_search.py
(or `make plot-search` inside cpp_algo_lab/). Reads results/search_*.csv,
writes results/plots/search_*.png.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from labviz import INK, MUTED, SEQ_CMAP, SLOTS, apply_style, save, slope_label
from matplotlib.colors import LogNorm

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"
PLOTS = RESULTS / "plots"

TEXTS = ["dna", "ascii", "english", "periodic"]
OWN = ["naive", "kmp", "bmh", "rabin_karp"]
COLOR = dict(zip(OWN, SLOTS, strict=True))
BASELINE_STYLE = {"sv_find": "--", "std_bmh": "-.", "std_bm": ":"}

apply_style()


def panel_series(ax, sub: pd.DataFrame, xcol: str, var: str) -> None:
    """Own algorithms in color with slope labels; std baselines gray-styled."""
    for algo in OWN:
        s = sub[sub["algo"] == algo].sort_values(xcol)
        x, y = s[xcol].to_numpy(float), s["median_ms"].to_numpy(float)
        ax.loglog(
            x,
            y,
            color=COLOR[algo],
            marker="o",
            markersize=4,
            label=f"{algo}{slope_label(x, y, var=var)}",
        )
    for algo, ls in BASELINE_STYLE.items():
        s = sub[sub["algo"] == algo].sort_values(xcol)
        ax.loglog(s[xcol], s["median_ms"], color=MUTED, linestyle=ls, label=algo)
    ax.legend(fontsize=7, framealpha=0.9)


def fig_time_vs_n(times_n: pd.DataFrame) -> None:
    m_fixed = int(times_n["m"].iloc[0])
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.4), sharey=True)
    for ax, text in zip(axes, TEXTS, strict=True):
        panel_series(ax, times_n[times_n["text"] == text], "n", "n")
        ax.set_title(f"text: {text}", color=INK)
        ax.set_xlabel("n (text length)")
    axes[0].set_ylabel("median wall time [ms]")
    fig.suptitle(
        f"Search: time vs text length n (m={m_fixed}, log-log) — "
        "everyone is linear in n; the constants tell the story",
        color=INK,
    )
    save(fig, PLOTS, "search_time_vs_n.png")


def fig_time_vs_m(times_m: pd.DataFrame) -> None:
    n_fixed = int(times_m["n"].max())
    sub_n = times_m[times_m["n"] == n_fixed]
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.4), sharey=True)
    for ax, text in zip(axes, TEXTS, strict=True):
        panel_series(ax, sub_n[sub_n["text"] == text], "m", "m")
        ax.set_title(f"text: {text}", color=INK)
        ax.set_xlabel("m (pattern length)")
    axes[0].set_ylabel("median wall time [ms]")
    fig.suptitle(
        f"Search: time vs pattern length m (n={n_fixed}, log-log) — "
        "BMH gets FASTER as m grows; KMP stays flat; naive×periodic pays m",
        color=INK,
    )
    save(fig, PLOTS, "search_time_vs_m.png")


def fig_reads_per_char(ops: pd.DataFrame) -> None:
    sub = ops[ops["sweep"] == "m"]
    n_fixed = int(sub["n"].max())
    sub = sub[sub["n"] == n_fixed]
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.4), sharey=True)
    for ax, text in zip(axes, TEXTS, strict=True):
        s0 = sub[sub["text"] == text]
        for algo in OWN:
            s = s0[s0["algo"] == algo].sort_values("m")
            ax.loglog(
                s["m"],
                s["text_reads"] / n_fixed,
                color=COLOR[algo],
                marker="o",
                markersize=4,
                label=algo,
            )
        ax.axhline(1.0, color=MUTED, linestyle="--", linewidth=1.2)
        ax.set_title(f"text: {text}", color=INK)
        ax.set_xlabel("m (pattern length)")
        ax.legend(fontsize=8, framealpha=0.9)
    axes[0].text(4.2, 1.12, "1 read per text char", color=MUTED, fontsize=7)
    axes[0].set_ylabel("text reads / n")
    fig.suptitle(
        f"Search: text reads per character vs m (n={n_fixed}) — "
        "BMH drops below 1 (sublinear); naive×periodic explodes to m",
        color=INK,
    )
    save(fig, PLOTS, "search_reads_per_char.png")


def fig_pre_vs_match(ops: pd.DataFrame) -> None:
    sub = ops[(ops["sweep"] == "m") & (ops["text"] == "dna")]
    n_fixed = int(sub["n"].max())
    sub = sub[sub["n"] == n_fixed]
    ms = [m for m in (4, 64, 1024) if m in set(sub["m"])]
    fig, axes = plt.subplots(1, len(ms), figsize=(4.4 * len(ms), 4.2), sharey=True)
    axes = np.atleast_1d(axes)
    x = np.arange(len(OWN))
    for ax, m in zip(axes, ms, strict=True):
        rows = sub[sub["m"] == m].set_index("algo").reindex(OWN)
        pre = np.maximum(rows["pre_ops"].to_numpy(float), 1.0)
        scan = rows["text_reads"].to_numpy(float)
        ax.bar(x - 0.2, pre, width=0.38, color=MUTED, label="preprocess (pattern ops)")
        ax.bar(x + 0.2, scan, width=0.38, color=SLOTS[0], label="scan (text reads)")
        ax.set_yscale("log")
        ax.set_xticks(x, ["naive", "kmp", "bmh", "rk"])
        ax.set_title(f"m = {m}", color=INK)
        ax.grid(False, axis="x")
    axes[0].set_ylabel("elementary ops (log)")
    axes[0].legend(fontsize=8, framealpha=0.9)
    fig.text(
        0.01,
        -0.02,
        "naive has no preprocessing; its bar is clipped to 1 on the log axis.",
        fontsize=7,
        color=MUTED,
    )
    fig.suptitle(
        f"Search: preprocessing grows with m, the scan is pinned to n={n_fixed} (dna text)",
        color=INK,
    )
    save(fig, PLOTS, "search_pre_vs_match.png")


def fig_search_heatmap(times_m: pd.DataFrame) -> None:
    n_fixed = int(times_m["n"].max())
    sub = times_m[times_m["n"] == n_fixed]
    ms = sorted(int(m) for m in sub["m"].unique())
    target_m = 16 if 16 in ms else ms[len(ms) // 2]
    sub = sub[sub["m"] == target_m]
    order = OWN + list(BASELINE_STYLE)
    pivot = (
        sub.pivot_table(index="algo", columns="text", values="median_ms")
        .reindex(index=order, columns=TEXTS)
    )
    fig, ax = plt.subplots(figsize=(7, 5.6))
    im = ax.imshow(
        pivot.to_numpy(),
        cmap=SEQ_CMAP,
        norm=LogNorm(vmin=max(pivot.min().min(), 1e-3), vmax=pivot.max().max()),
        aspect="auto",
    )
    ax.set_xticks(range(len(TEXTS)), TEXTS)
    ax.set_yticks(range(len(order)), order)
    ax.grid(False)
    mid = np.sqrt(pivot.min().min() * pivot.max().max())
    for r in range(pivot.shape[0]):
        for c in range(pivot.shape[1]):
            v = pivot.iloc[r, c]
            ax.text(
                c,
                r,
                f"{v:.2f}",
                ha="center",
                va="center",
                fontsize=8,
                color="#ffffff" if v > mid else INK,
            )
    fig.colorbar(im, ax=ax, label="median ms (log scale)")
    ax.set_title(f"Search: median time [ms] at n={n_fixed}, m={target_m}", color=INK)
    save(fig, PLOTS, "search_heatmap.png")


def main() -> None:
    times_n = pd.read_csv(RESULTS / "search_times_n.csv")
    times_m = pd.read_csv(RESULTS / "search_times_m.csv")
    ops = pd.read_csv(RESULTS / "search_ops.csv")
    fig_time_vs_n(times_n)
    fig_time_vs_m(times_m)
    fig_reads_per_char(ops)
    fig_pre_vs_match(ops)
    fig_search_heatmap(times_m)
    print("all search figures written to", PLOTS)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Update the Makefile `plot` targets**

Replace the `plot:` rule (and extend `.PHONY`) so the plot section reads:

```make
.PHONY: all test bench bench-sorting bench-search bench-quick bench-search-quick trace plot plot-sorting plot-search clean

plot: plot-sorting plot-search

plot-sorting:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_results.py

plot-search:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_search.py
```

(Keep every other rule exactly as Task 5 left it.)

- [ ] **Step 6: Generate the search figures + run the gates**

From repo root:

```bash
uv run --no-sync python cpp_algo_lab/scripts/plot_search.py
uv run --no-sync ruff check cpp_algo_lab/scripts
uv run --no-sync ruff format --check cpp_algo_lab/scripts
```

Expected: 5 `wrote ...` lines; both ruff gates clean (if ruff flags import order or formatting, apply the mechanical fix it suggests and note it in your report).

**Visually verify each PNG before committing** (open the files): (1) no overlapping/unreadable legends; (2) `search_time_vs_m.png` shows BMH-family curves descending while KMP stays flat; (3) `search_reads_per_char.png` shows bmh below the 1.0 reference line on dna/ascii/english and naive rising to ~m on periodic; (4) the heatmap annotations are legible on both light and dark cells. Fix layout issues if found (figsize/legend placement are yours to adjust; colors and content are fixed by the plan).

- [ ] **Step 7: Run `make test` (regression) and commit**

```bash
cd cpp_algo_lab && make test && cd ..
git add cpp_algo_lab/scripts cpp_algo_lab/Makefile cpp_algo_lab/results/plots
git commit -m "feat(cpp_algo_lab): add search figures and shared plot style module"
```

---

### Task 7: Japanese docs — `docs/search.md` + README + references (fable implementer)

**Files:**
- Create: `cpp_algo_lab/docs/search.md`
- Modify: `cpp_algo_lab/README.md`
- Modify: `cpp_algo_lab/docs/references.md`

**Interfaces:**
- Consumes: the committed CSVs (Task 5), the 5 PNGs (Task 6), all search headers, `docs/sorting.md` (style reference — match its voice, density, and structure).
- Produces: the Phase 2 learning centerpiece. **Every empirical number quoted must be read from the committed CSVs, not invented.** (Read them via `python3 -c` snippets, e.g. `python3 -c "import csv; print([r for r in csv.DictReader(open('cpp_algo_lab/results/search_ops.csv')) if r['algo']=='bmh' and r['text']=='dna' and r['sweep']=='m'])"`.)

- [ ] **Step 1: Write `docs/search.md` (Japanese, ~300+ lines, structure below is binding)**

1. **§1 問題設定と記法** — 全出現位置（重なり含む）を返す仕様、n / m / σ の記法、空パターン規約（`{0..n}` の n+1 箇所、`string_view::find` と同じ）、`"aaaaaa"` 中の `"aaa"` は 4 箇所という例。
2. **§2 共通実装設計** — `std::string_view`（所有しないビュー）、`SearchStats` の 3 カウンタの意味論（`pre_ops` / `text_reads` / `char_comparisons`、RK だけ reads ≠ comparisons になる理由）、**Tally ポリシーによる計数注入**：Phase 1 の `Counted<T>` が「要素型で注入」だったのに対し検索は「テンプレート引数のポリシーで注入」— `NoTally` の空メソッドはインライン展開で消える（ゼロコスト抽象）。
3. **§3 各論**（1 アルゴリズム 1 節、ヘッダと 1:1 対応）：
   - **naive** — 全アライメント総当たり。O(nm) 最悪の仕組み。単体テストの厳密値（periodic n=1024, m=16 で reads = 16144 = (n−m+1)·m）を引用。
   - **KMP** — failure（prefix）関数の意味。**"ababaca" の π 表 {0,0,1,2,3,0,1} を手動トレースで必ず掲載**。実装が「1 ループ 1 比較」に再構成してあること（教科書の while+if 形は同じ比較を 2 回書く）。periodic での 2n−15 = 2033 reads と pre_ops=29 の内訳（14 マッチ + 'b' での 15 段崩落）。重なり一致が無料である理由（"aaaaaa"/"aaa" が reads=6）。
   - **BMH** — bad-character 表の作り方。**pattern "search" の shift 表を例示**（s→5, e→4, a→3, r→2, c→1, h→6：末尾にしか無い文字は m）。last-char 先読みで 1 読み→表引きスキップが劣線形を生む。periodic では shift['a']=1 に落ちて n−m+1 = 1009 reads（優雅な退化）。
   - **Rabin-Karp** — ローリングハッシュの算術（base 257 / mod 1e9+7、`uint64_t` で中間値 < 2^38 の証明）、ハッシュ一致時のみ検証、衝突と検証の必然性。periodic worst に免疫（cmps=0）だが a^n vs a^m が自身の worst（全窓検証、576 reads の内訳）。
4. **§4 C++17 searcher という API 設計** — searcher オブジェクト = 「前処理を型に固める」設計。コンストラクタが表を作り `std::search` が走査する分離は、本モジュールの pre/match 分離計測と同じ思想。CTAD で書ける。
5. **§5 結果の読み方（5 図 × 実測値）** — 図ごとに 1 節。**引用する数値はすべて committed CSV と一致させること**：
   - `search_time_vs_n.png` — 全アルゴリズム slope ≈ 1（凡例の実測指数を引用）。
   - `search_time_vs_m.png` — BMH/std_bmh/std_bm の下降、KMP の平坦、naive×periodic の m 比例。sv_find（memchr/SIMD）がなぜ自作 4 種より速いか＝計算量とは別の「実装定数」の話。
   - `search_reads_per_char.png` — BMH < 1（dna, m=1024 の実測値を引用）、KMP ≤ 2、naive×periodic = m、RK ≈ 3 付近で平坦（1 + 2(n−m)/n + 検証分）。
   - `search_pre_vs_match.png` — 前処理は m 次元・照合は n 次元。m=1024 でも前処理 ≪ 照合である実数比。
   - `search_heatmap.png` — テキスト種 × アルゴリズムの総合対比。
6. **§6 教訓・落とし穴** — periodic テキストが 4 実装の性格を全部暴くこと（naive 爆発 / KMP 本領 / BMH 優雅な退化 / RK 素通り）、BMH の「末尾専用文字 shift=m」、RK の mod 選択、`string_view` の非所有ゆえの寿命注意。
7. **§7 Phase 3/4 への接続** — 検索は embarrassingly parallel（1 スレッド = 1 開始位置）だが KMP の failure 遷移は逐次依存で GPU に不向き — references.md の PFAC / Kouzinopoulos の実験を本ラボで縮小再現する予告。

- [ ] **Step 2: Update `README.md`**

- 概要段落: Phase 2 の一文を追加（検索 4 種 + 基準線 3 種 + 4 軸）。
- クイックスタート表: `make bench-search` / `make bench-search-quick` / `make plot-search` の行を追加し、`make bench` の説明を「ソート+検索の全計測」に、`make plot` を「全図（ソート 6 枚 + 検索 5 枚）」に更新。
- 構成ツリー: `search/` を sorting/ の後に追加（include/tests/bench の一行ずつ）、`scripts/` に `labviz.py` と `plot_search.py`、`docs/` に `search.md`。
- 学習ロードマップ: ステップを追加 — `docs/search.md` → `search/include/search/` を naive → kmp → bmh → rabin_karp → baselines の順で読む（この順は「総当たり → 失敗を知識に変える → 飛ばす → 比べない」という概念の積み上げ）→ `make bench-search && make plot-search` → 図と §5 の突き合わせ。
- Phase 状況表: Phase 2 を ✅ に。

- [ ] **Step 3: Update `docs/references.md`**

「文字列検索」節の先頭に古典 4 文献を追加（各 1 行、何がこのラボのどこに対応するかを添える）:

- **Knuth, Morris & Pratt, Fast Pattern Matching in Strings (SIAM J. Comput., 1977)** — kmp.hpp の failure 関数と ≤2n 保証の出典。
- **Boyer & Moore, A Fast String Searching Algorithm (CACM, 1977)** — 劣線形スキップの原典。std_bm 基準線。
- **Horspool, Practical Fast Searching in Strings (Software: Practice & Experience, 1980)** — bmh.hpp の bad-character 単独版。
- **Karp & Rabin, Efficient Randomized Pattern-Matching Algorithms (IBM J. Res. Dev., 1987)** — rabin_karp.hpp のローリングハッシュ。

既存の GPU 検索文献の導入文を「Phase 2 の逐次実装を Phase 4 で GPU 化する際の答え合わせ先」に更新。

- [ ] **Step 4: Cross-check every number, then commit**

Verify each quoted figure/CSV number with `python3 -c` one-liners before committing (the reviewer will re-derive them).

```bash
git add cpp_algo_lab/docs/search.md cpp_algo_lab/docs/references.md cpp_algo_lab/README.md
git commit -m "docs(cpp_algo_lab): add search learning notes and update README/references"
```

---

### Task 8: Phase-1 backlog hardening (counting guard, bucket clamp, unsigned keys)

**Files:**
- Modify: `cpp_algo_lab/sorting/include/sorting/counting.hpp:24` (wrap-around-safe range guard)
- Modify: `cpp_algo_lab/sorting/include/sorting/bucket.hpp:29` (defensive index clamp)
- Modify: `cpp_algo_lab/sorting/include/sorting/keys.hpp:17` (`if constexpr` so unsigned element types compile warning-free)
- Modify: `cpp_algo_lab/sorting/tests/test_sorting.cpp` (append 2 test cases)

**Interfaces:**
- Consumes / Produces: no API changes — behavior-preserving hardening from the Phase 1 final-review triage.

- [ ] **Step 1: Append failing tests to `sorting/tests/test_sorting.cpp`**

Add `#include <limits>` to the include block if not present. Append:

```cpp
TEST_CASE("counting_sort: guard rejects huge key ranges without wrap-around") {
    // A key of 2^64-1 makes max_key+1 wrap to 0, which slipped past the old
    // `max_key + 1 > kMaxCountingRange` guard and then indexed out of bounds.
    std::vector<int> v{1, 0};
    const auto huge_key = [](const int& x) {
        return x ? std::numeric_limits<std::uint64_t>::max() : std::uint64_t{0};
    };
    CHECK_THROWS_AS(lab::counting_sort(v.begin(), v.end(), huge_key), std::length_error);
}

TEST_CASE("non-comparison sorts accept unsigned element types") {
    std::vector<unsigned> v{5u, 3u, 9u, 1u, 3u};
    std::vector<unsigned> want = v;
    std::sort(want.begin(), want.end());
    SUBCASE("counting") {
        lab::counting_sort(v.begin(), v.end());
        CHECK(v == want);
    }
    SUBCASE("radix") {
        lab::radix_sort(v.begin(), v.end());
        CHECK(v == want);
    }
    SUBCASE("bucket") {
        lab::bucket_sort(v.begin(), v.end());
        CHECK(v == want);
    }
}
```

- [ ] **Step 2: Run to verify failure**

Run from `cpp_algo_lab/`: `make test`
Expected: the huge-key case FAILS (no throw happens — or ASan aborts on the out-of-bounds histogram access; either failure mode confirms the bug). The unsigned case may already pass functionally but emits a `-Wtype-limits`-style warning territory (`v < 0` on unsigned) — the fix removes the dead comparison.

- [ ] **Step 3: Apply the three fixes**

`counting.hpp` — replace the guard line:

```cpp
    if (max_key >= kMaxCountingRange)
        throw std::length_error("counting_sort: key range too large");
```

`bucket.hpp` — replace the bucket-index line with a clamped version:

```cpp
        // long double rounding could push key*scale to exactly n for the
        // maximum key; clamp defensively (no deterministic test can force
        // this on x86-64's 80-bit long double, hence comment-only rationale).
        const auto b = std::min(
            n - 1, static_cast<std::size_t>(static_cast<long double>(key(*it)) * scale));
```

`keys.hpp` — replace the negative-key check so unsigned instantiations don't compare `v < 0`:

```cpp
    template <class T>
    std::uint64_t operator()(const T& v) const {
        static_assert(std::is_integral_v<T>,
                      "IntegralKey requires an integral element type; pass a custom KeyFn");
        if constexpr (std::is_signed_v<T>) {
            if (v < 0) throw std::invalid_argument("non-comparison sort: negative key");
        }
        return static_cast<std::uint64_t>(v);
    }
```

- [ ] **Step 4: Run to verify pass**

Run from `cpp_algo_lab/`: `make test`
Expected: all three binaries SUCCESS, build warning-free.

- [ ] **Step 5: Commit**

```bash
git add cpp_algo_lab/sorting
git commit -m "fix(cpp_algo_lab): harden non-comparison sort guards (Phase 1 backlog)"
```

---

## Verification (whole phase)

1. `make test` from `cpp_algo_lab/` — three doctest binaries SUCCESS under ASan/UBSan (no-recover).
2. `make bench-search` regenerates the three CSVs; committed versions came from a full run (row counts 169/253/241 incl. header).
3. `make plot` renders 6 sorting + 5 search PNGs; committed search PNGs match the committed CSVs.
4. Both ruff gates clean from repo root.
5. `docs/search.md` quotes only numbers that appear in (or are exactly derivable from) the committed CSVs.
