# cpp_algo_lab Phase 3 (CPU Parallel Ladder) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the CPU rungs of the parallelization ladder: parallel merge sort via raw `std::thread` divide-and-conquer, OpenMP tasks, and `std::execution::par` (TBB backend), plus OpenMP chunked BMH search with the boundary-overlap correctness lesson — with thread-scaling benchmarks (1→20), 2 committed CSVs, 3 figures, and Japanese docs whose measured headline is "search scales almost linearly through 12 threads; both search and sort eventually saturate".

**Architecture:** Header-only C++20 (`parallel/include/parallel/*.hpp`, one rung per header) delegating sequential base cases to the existing `lab::merge_sort` (each call owns its buffer → concurrent calls are safe) and `lab::bmh_search`. One benchmark executable writes 2 CSVs; `scripts/plot_parallel.py` renders 3 PNGs on the shared `labviz` style. Layout note: the spec's tree sketched `parallel/cpu/`; we use `parallel/include/parallel/` to match the established `-I<module>/include` convention (GPU `.cu` files will live in `parallel/gpu/` in Phase 4). Spec: `docs/superpowers/specs/2026-07-14-cpp-algo-lab-design.md` §2.3 (CPU portion only; GPU is Phase 4).

**Tech Stack:** g++ 13.3 (C++20), `-fopenmp` (libgomp), `-ltbb` (libstdc++ parallel-STL backend), GNU make, doctest (vendored), repo-root uv (pandas/matplotlib) for plotting.

**Environment verified (2026-07-17, this machine):** OpenMP tasks + `std::execution::par` + `-ltbb` compile and run CLEAN under `-fsanitize=address,undefined -fno-sanitize-recover=undefined`; `omp_get_max_threads()` = 20.

**Model policy (SDD):** implementers T1–T4 haiku (transcription), T5–T6 sonnet (run bench / verify figures), T7 fable (Japanese docs). Task reviewers sonnet. Final whole-branch review fable. Branch: `cpp-algo-lab/phase3` from main.
Operational notes carried from Phase 2: distrust haiku implementer-report arithmetic (reviewers re-derive); physics-check thresholds must leave single-sample margin; also touch up plot_results.py's docstring wording in T7 (deferred from Phase 2).

**Execution status (2026-07-18):** Tasks 1–7 are implemented and the whole-phase verification passes on `cpp-algo-lab/phase3`. The unchecked step boxes below preserve the original execution script rather than serving as current status. A post-implementation review found the following amendments, which supersede conflicting snippets in Tasks 4–7:

- `--quick` writes ignored `build/parallel_{sort,search}_quick.csv`; it never overwrites the committed full-sweep CSVs.
- A full run writes staged CSVs under `build/` and replaces the committed-result paths only after both benchmark sections finish successfully.
- Every configuration gets an untimed warm-up. Five timed rounds use deterministic shuffled configuration order; correctness is verified after every repeat, not only the first.
- CSVs include robust dispersion (`mad_ms`) as well as the median. Plot time curves show MAD error bars and reject quick, partial, or schema-mismatched inputs.
- OpenMP dynamic team sizing is disabled and each requested team size is verified before measurement.
- The pre-review data regressed sharply after 12 threads. Two amended-protocol runs showed that fixed-order bias had exaggerated that result; the final candidate reaches its best search point at t=16 (english 11.47×, DNA 10.63×) and has large MAD at t=20, so the documented conclusion is saturation with an uncertain late-thread regression.
- Amdahl inversion is reported only as an **effective serial fraction**: it also absorbs runtime, memory-system, allocation, cutoff, and scheduling overhead. The sequential merge chain is a contributor, not a uniquely proven cause.

## Global Constraints

- Compiler: `g++` only, `-std=c++20 -Wall -Wextra -Wpedantic`. No cmake, no clang.
- Test builds: `-O1 -g -fsanitize=address,undefined -fno-sanitize-recover=undefined`. Bench builds: `-O2 -DNDEBUG`. The two parallel TUs additionally get `-fopenmp` and link `-ltbb`; no other target's flags change.
- Only vendored dependency: doctest. Do NOT include TBB headers (`<tbb/...>`) — TBB is reached only through `std::execution::par` + `-ltbb`. (Consequence: par-STL thread count is not controllable; it benches as a single "all cores" reference point.)
- All C++ code, identifiers, comments, and commit messages in English. All `docs/*.md`, `README.md` prose in Japanese.
- `make` targets run from `cpp_algo_lab/`; `results/` CSVs and PNGs are committed (`!results/**` re-include already in place).
- Python via repo root `uv run --no-sync ...`; both ruff gates must pass from repo root.
- Namespace `lab`. Commit prefixes `feat(cpp_algo_lab):` / `fix(cpp_algo_lab):` / `docs(cpp_algo_lab):`.
- Test includes go into the top include block, alphabetized, never mid-file.

## Fixed design values (used across tasks)

- **Public APIs:**
  - `template <class RandomIt, class Compare = std::less<>> void thread_merge_sort(RandomIt first, RandomIt last, Compare comp = {}, unsigned threads = 0)` — threads 0 = `hardware_concurrency()`; effective parallelism is the smallest power of two ≥ threads (whole-level spawning).
  - `template <class RandomIt, class Compare = std::less<>> void omp_merge_sort(RandomIt first, RandomIt last, Compare comp = {}, int threads = 0)` — threads ≤ 0 = OpenMP default; arbitrary counts work.
  - `template <class RandomIt, class Compare = std::less<>> void par_stl_sort(RandomIt first, RandomIt last, Compare comp = {})` — `std::sort(std::execution::par, ...)`.
  - `std::vector<std::size_t> omp_bmh_search(std::string_view text, std::string_view pattern, int threads = 0)` — returns exactly what `lab::bmh_search` returns (all overlapping occurrences, ascending; empty pattern `{0..n}`; m>n `{}`), for every thread count.
- `lab::kParallelSortCutoff = std::ptrdiff_t{1} << 15` (32768): subranges below this sort sequentially (in `parallel/tuning.hpp`).
- Both parallel merge sorts are **stable** (sequential base is stable; `std::inplace_merge` is stable). `par_stl_sort` makes no stability claim.
- **Search chunking invariant (the teaching core):** the n−m+1 start positions are split into `threads` contiguous ranges `[lo_c, hi_c)` with `lo_c = starts·c/threads`; chunk c scans the slice `text.substr(lo_c, (hi_c−lo_c)+m−1)`. A slice of that length can only contain matches starting at slice offsets `0..hi_c−lo_c−1`, so every match is found by exactly one chunk — no duplicates, no misses, no post-filtering.
- **Bench sweeps (seed 42, one warm-up, repeats 5, median + MAD; configuration order shuffled per repeat):**
  - Sort: n = 2^24 random ints. Rows: `merge_seq` (t=1), `std_sort_seq` (t=1), `thread_merge` t ∈ {1,2,4,8,16}, `omp_merge` t ∈ {1,2,4,6,8,12,16,20}, `par_stl` (t=0 meaning "library default, all cores"). 16 data rows.
  - Search: n = 2^26 chars, m = 16, texts {english, dna}. Rows per text: `bmh_seq` (t=1), `omp_bmh` t ∈ {1,2,4,6,8,12,16,20}. 18 data rows.
  - `--quick`: sort n = 2^20 with thread lists {1,4}; search n = 2^22, threads {1,4}; repeats 2; outputs go to `build/*_quick.csv` and do not touch canonical results.
- **CSV schemas:**
  - `results/parallel_sort.csv`: `algo,threads,n,repeats,median_ms,mad_ms`
  - `results/parallel_search.csv`: `algo,text,threads,n,m,repeats,median_ms,mad_ms,occurrences`
- **Figures (3):** `parallel_sort_scaling.png`, `parallel_search_scaling.png`, `parallel_speedup.png` (the headline contrast).
- **Chart palette:** thread_merge `#2a78d6`, omp_merge `#1baf7a`, omp_bmh(english) `#eda100`, omp_bmh(dna) `#008300`; sequential/library references MUTED `#898781` with linestyles merge_seq `--`, std_sort_seq `-.`, par_stl `:`; ideal-speedup diagonal MUTED dotted.

---

### Task 1: Tuning constant + `std::thread` merge sort + Makefile parallel test target

**Files:**
- Create: `cpp_algo_lab/parallel/include/parallel/tuning.hpp`
- Create: `cpp_algo_lab/parallel/include/parallel/thread_merge.hpp`
- Create: `cpp_algo_lab/parallel/tests/test_parallel.cpp`
- Modify: `cpp_algo_lab/Makefile` (full replacement below: `-Iparallel/include`, `PAR_HDRS`, `OMPFLAGS`, `TBBLIB`, `test_parallel` binary)

**Interfaces:**
- Consumes: `lab::merge_sort` (`sorting/merge.hpp` — stable, each call owns its buffer so concurrent calls are safe), `lab::generate` (`lab/datagen.hpp`), `lab::observed_stable(fn, n, seed)` (`lab/stability.hpp`).
- Produces: `lab::kParallelSortCutoff`; `lab::thread_merge_sort(first, last, comp = {}, threads = 0)`; `lab::detail::depth_for_threads(unsigned) -> int`. The Makefile's `test_parallel` binary (built with `-fopenmp`, linked `-ltbb`) that Tasks 2–3 extend.

- [ ] **Step 1: Create the test file `parallel/tests/test_parallel.cpp` (failing: headers don't exist yet)**

```cpp
// Tests for the CPU parallel ladder: conformance against std::sort /
// sequential references across sizes, distributions and thread counts;
// stability of the parallel merge sorts; and the chunk-boundary planting
// tests for the parallelized search (Tasks 2-3 extend this file).
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest/doctest.h"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "lab/datagen.hpp"
#include "lab/stability.hpp"
#include "parallel/thread_merge.hpp"

TEST_CASE("depth_for_threads: smallest depth with 2^depth >= threads") {
    CHECK(lab::detail::depth_for_threads(1) == 0);
    CHECK(lab::detail::depth_for_threads(2) == 1);
    CHECK(lab::detail::depth_for_threads(3) == 2);
    CHECK(lab::detail::depth_for_threads(4) == 2);
    CHECK(lab::detail::depth_for_threads(16) == 4);
    CHECK(lab::detail::depth_for_threads(20) == 5);
}

TEST_CASE("thread_merge_sort: conformance vs std::sort") {
    const std::vector<std::size_t> sizes = {0, 1, 2, 3, 100, 4096};
    for (const lab::Dist d : lab::all_dists()) {
        for (const std::size_t n : sizes) {
            for (const unsigned threads : {1u, 2u, 4u, 8u, 16u}) {
                std::vector<int> v = lab::generate(d, n, 42);
                std::vector<int> want = v;
                std::sort(want.begin(), want.end());
                lab::thread_merge_sort(v.begin(), v.end(), std::less<>{}, threads);
                INFO("dist=" << lab::dist_name(d) << " n=" << n << " threads=" << threads);
                CHECK(v == want);
            }
        }
    }
    // Large enough to cross kParallelSortCutoff so threads really spawn.
    for (const unsigned threads : {1u, 4u, 16u}) {
        std::vector<int> v = lab::generate(lab::Dist::random_uniform, 200000, 42);
        std::vector<int> want = v;
        std::sort(want.begin(), want.end());
        lab::thread_merge_sort(v.begin(), v.end(), std::less<>{}, threads);
        CHECK(v == want);
    }
}

TEST_CASE("thread_merge_sort: stable (sequential base + inplace_merge are stable)") {
    // n=200000 crosses the cutoff, so the parallel path (spawn + inplace_merge)
    // is actually exercised, not just the sequential fallback.
    const bool stable = lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) {
            lab::thread_merge_sort(v.begin(), v.end(), std::less<>{}, 8);
        },
        200000, 7);
    CHECK(stable);
}

TEST_CASE("thread_merge_sort: custom comparator (descending)") {
    std::vector<int> v = lab::generate(lab::Dist::random_uniform, 50000, 42);
    std::vector<int> want = v;
    std::sort(want.begin(), want.end(), std::greater<>{});
    lab::thread_merge_sort(v.begin(), v.end(), std::greater<>{}, 4);
    CHECK(v == want);
}
```

- [ ] **Step 2: Replace `cpp_algo_lab/Makefile` with this full content**

```make
# cpp_algo_lab — build/test/bench/plot. Run make from this directory.
.DEFAULT_GOAL := test
CXX      := g++
STD      := -std=c++20
WARN     := -Wall -Wextra -Wpedantic
INC      := -Icommon -Isorting/include -Isearch/include -Iparallel/include -Ithird_party
TESTFLAGS  := $(STD) $(WARN) $(INC) -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=undefined
BENCHFLAGS := $(STD) $(WARN) $(INC) -O2 -DNDEBUG
OMPFLAGS := -fopenmp
TBBLIB   := -ltbb
BUILD    := build

COMMON_HDRS  := $(wildcard common/lab/*.hpp)
SORT_HDRS    := $(wildcard sorting/include/sorting/*.hpp)
SEARCH_HDRS  := $(wildcard search/include/search/*.hpp)
PAR_HDRS     := $(wildcard parallel/include/parallel/*.hpp)

.PHONY: all test bench bench-sorting bench-search bench-quick bench-search-quick trace plot plot-sorting plot-search clean

all: $(BUILD)/test_common $(BUILD)/test_sorting $(BUILD)/test_search $(BUILD)/test_parallel $(BUILD)/bench_sorting $(BUILD)/bench_search

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/test_common: common/tests/test_common.cpp $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $< -o $@

$(BUILD)/test_sorting: sorting/tests/test_sorting.cpp $(SORT_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $< -o $@

$(BUILD)/test_search: search/tests/test_search.cpp $(SEARCH_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $< -o $@

$(BUILD)/test_parallel: parallel/tests/test_parallel.cpp $(PAR_HDRS) $(SEARCH_HDRS) $(SORT_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $(OMPFLAGS) $< -o $@ $(TBBLIB)

$(BUILD)/bench_sorting: sorting/bench/bench_sorting.cpp $(SORT_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(BENCHFLAGS) $< -o $@

$(BUILD)/bench_search: search/bench/bench_search.cpp $(SEARCH_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(BENCHFLAGS) $< -o $@

test: $(BUILD)/test_common $(BUILD)/test_sorting $(BUILD)/test_search $(BUILD)/test_parallel
	$(BUILD)/test_common
	$(BUILD)/test_sorting
	$(BUILD)/test_search
	$(BUILD)/test_parallel

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

plot: plot-sorting plot-search

plot-sorting:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_results.py

plot-search:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_search.py

clean:
	rm -rf $(BUILD)
```

- [ ] **Step 3: Run to verify failure**

Run from `cpp_algo_lab/`: `make test`
Expected: FAIL to compile test_parallel — `parallel/thread_merge.hpp: No such file or directory`.

- [ ] **Step 4: Implement `parallel/include/parallel/tuning.hpp`**

```cpp
#pragma once
// Shared tuning constants for the CPU parallel ladder.
#include <cstddef>

namespace lab {

// Subranges below this size are sorted sequentially: thread-spawn / task
// overhead dominates any parallel win at this scale.
inline constexpr std::ptrdiff_t kParallelSortCutoff = std::ptrdiff_t{1} << 15;

}  // namespace lab
```

- [ ] **Step 5: Implement `parallel/include/parallel/thread_merge.hpp`**

```cpp
#pragma once
// Parallel merge sort rung 1: raw std::thread divide-and-conquer. One half
// goes to a spawned thread, the other is sorted in the current thread, then
// std::inplace_merge joins the runs (stable). The depth cutoff bounds total
// spawns at 2^depth - 1; the size cutoff hands small subranges to the
// sequential lab::merge_sort, whose per-call buffer makes concurrent calls
// safe. Spawning whole levels means effective parallelism is the smallest
// power of two >= the requested thread count.
#include <algorithm>
#include <functional>
#include <thread>

#include "parallel/tuning.hpp"
#include "sorting/merge.hpp"

namespace lab {

namespace detail {

inline int depth_for_threads(unsigned threads) {
    int depth = 0;
    while ((1u << depth) < threads) ++depth;
    return depth;  // smallest depth with 2^depth >= threads
}

template <class RandomIt, class Compare>
void thread_merge_impl(RandomIt first, RandomIt last, Compare comp, int depth) {
    const auto n = last - first;
    if (n < 2) return;
    if (depth <= 0 || n < kParallelSortCutoff) {
        merge_sort(first, last, comp);
        return;
    }
    const auto mid = first + n / 2;
    // std::jthread (C++20) joins in its destructor: if the current thread's
    // recursive call below threw, a plain std::thread would still be
    // joinable when unwound and std::terminate would fire. RAII join is the
    // language's answer to exactly this hole.
    std::jthread left(
        [first, mid, comp, depth] { thread_merge_impl(first, mid, comp, depth - 1); });
    thread_merge_impl(mid, last, comp, depth - 1);
    left.join();
    std::inplace_merge(first, mid, last, comp);
}

}  // namespace detail

// threads == 0 means std::thread::hardware_concurrency().
template <class RandomIt, class Compare = std::less<>>
void thread_merge_sort(RandomIt first, RandomIt last, Compare comp = {}, unsigned threads = 0) {
    if (threads == 0) threads = std::thread::hardware_concurrency();
    if (threads == 0) threads = 1;  // hardware_concurrency may report 0
    detail::thread_merge_impl(first, last, comp, detail::depth_for_threads(threads));
}

}  // namespace lab
```

- [ ] **Step 6: Run to verify pass**

Run from `cpp_algo_lab/`: `make test`
Expected: all four binaries build warning-free and report SUCCESS (test_parallel runs the 4 new cases). ASan/UBSan silent.

Note (2026-07-18, during execution): the block originally spawned a plain
`std::thread`; the Task 1 reviewer flagged the exception path (if the
current thread's recursion throws, the joinable thread's destructor calls
std::terminate). Fixed post-review to `std::jthread` with an explanatory
comment — C++20's RAII-join type exists precisely for this hole, which
makes it better teaching material as well. The explicit `left.join()`
before `inplace_merge` stays (the join is semantically required there;
jthread's destructor join is the safety net, not the mechanism).

- [ ] **Step 7: Commit**

```bash
git add cpp_algo_lab/parallel cpp_algo_lab/Makefile
git commit -m "feat(cpp_algo_lab): add std::thread parallel merge sort with depth cutoff"
```

---

### Task 2: OpenMP task merge sort + parallel-STL rung

**Files:**
- Create: `cpp_algo_lab/parallel/include/parallel/omp_merge.hpp`
- Create: `cpp_algo_lab/parallel/include/parallel/par_stl.hpp`
- Modify: `cpp_algo_lab/parallel/tests/test_parallel.cpp` (append; add the two includes to the top include block)

**Interfaces:**
- Consumes: `lab::merge_sort`, `lab::kParallelSortCutoff` (Task 1), `lab::observed_stable`.
- Produces: `lab::omp_merge_sort(first, last, comp = {}, int threads = 0)` (stable, arbitrary thread counts); `lab::par_stl_sort(first, last, comp = {})`.

- [ ] **Step 1: Append failing tests**

Add to the include block: `#include "parallel/omp_merge.hpp"` and `#include "parallel/par_stl.hpp"` (alphabetical: omp_merge before par_stl before thread_merge). Append at the end:

```cpp
TEST_CASE("omp_merge_sort: conformance vs std::sort (incl. odd thread counts)") {
    const std::vector<std::size_t> sizes = {0, 1, 2, 3, 100, 4096};
    for (const lab::Dist d : lab::all_dists()) {
        for (const std::size_t n : sizes) {
            for (const int threads : {1, 2, 3, 5, 8, 20}) {
                std::vector<int> v = lab::generate(d, n, 42);
                std::vector<int> want = v;
                std::sort(want.begin(), want.end());
                lab::omp_merge_sort(v.begin(), v.end(), std::less<>{}, threads);
                INFO("dist=" << lab::dist_name(d) << " n=" << n << " threads=" << threads);
                CHECK(v == want);
            }
        }
    }
    for (const int threads : {1, 3, 20}) {
        std::vector<int> v = lab::generate(lab::Dist::random_uniform, 200000, 42);
        std::vector<int> want = v;
        std::sort(want.begin(), want.end());
        lab::omp_merge_sort(v.begin(), v.end(), std::less<>{}, threads);
        CHECK(v == want);
    }
}

TEST_CASE("omp_merge_sort: stable") {
    const bool stable = lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) {
            lab::omp_merge_sort(v.begin(), v.end(), std::less<>{}, 8);
        },
        200000, 7);
    CHECK(stable);
}

TEST_CASE("par_stl_sort: conformance vs std::sort") {
    for (const std::size_t n : {std::size_t{0}, std::size_t{1}, std::size_t{1000},
                                std::size_t{100000}}) {
        std::vector<int> v = lab::generate(lab::Dist::random_uniform, n, 42);
        std::vector<int> want = v;
        std::sort(want.begin(), want.end());
        lab::par_stl_sort(v.begin(), v.end());
        CHECK(v == want);
    }
    std::vector<int> v = lab::generate(lab::Dist::random_uniform, 50000, 42);
    std::vector<int> want = v;
    std::sort(want.begin(), want.end(), std::greater<>{});
    lab::par_stl_sort(v.begin(), v.end(), std::greater<>{});
    CHECK(v == want);
}
```

- [ ] **Step 2: Run to verify failure**

Run from `cpp_algo_lab/`: `make test`
Expected: FAIL to compile — `parallel/omp_merge.hpp: No such file or directory`.

- [ ] **Step 3: Implement `parallel/include/parallel/omp_merge.hpp`**

```cpp
#pragma once
// Parallel merge sort rung 2: OpenMP tasks. Same recursion shape as the
// std::thread rung, but each half becomes a #pragma omp task handed to a
// worker pool: arbitrary thread counts work and the runtime load-balances.
// Locals referenced inside a task are firstprivate by default, so the
// iterators and comparator are copied into each task -- no dangling stack
// references. Must be compiled with -fopenmp (the Makefile's parallel
// targets are).
#include <algorithm>
#include <functional>
#include <omp.h>

#include "parallel/tuning.hpp"
#include "sorting/merge.hpp"

namespace lab {

namespace detail {

template <class RandomIt, class Compare>
void omp_merge_impl(RandomIt first, RandomIt last, Compare comp) {
    const auto n = last - first;
    if (n < 2) return;
    if (n < kParallelSortCutoff) {
        merge_sort(first, last, comp);
        return;
    }
    const auto mid = first + n / 2;
#pragma omp task
    omp_merge_impl(first, mid, comp);
    omp_merge_impl(mid, last, comp);
#pragma omp taskwait
    std::inplace_merge(first, mid, last, comp);
}

}  // namespace detail

// threads <= 0 means the OpenMP default (all cores).
template <class RandomIt, class Compare = std::less<>>
void omp_merge_sort(RandomIt first, RandomIt last, Compare comp = {}, int threads = 0) {
    if (last - first < 2) return;
    if (threads <= 0) threads = omp_get_max_threads();
#pragma omp parallel num_threads(threads)
#pragma omp single nowait
    detail::omp_merge_impl(first, last, comp);
}

}  // namespace lab
```

- [ ] **Step 4: Implement `parallel/include/parallel/par_stl.hpp`**

```cpp
#pragma once
// Parallel merge sort rung 3: buy it from the library. std::sort with the
// parallel execution policy dispatches to libstdc++'s TBB backend (link
// -ltbb). One line of user code is the entire point of this rung; the trade
// is that the thread count belongs to the library, not to you.
#include <algorithm>
#include <execution>
#include <functional>

namespace lab {

template <class RandomIt, class Compare = std::less<>>
void par_stl_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    std::sort(std::execution::par, first, last, comp);
}

}  // namespace lab
```

- [ ] **Step 5: Run to verify pass**

Run from `cpp_algo_lab/`: `make test`
Expected: all four binaries SUCCESS, warning-free, sanitizers silent. (Environment note: this exact combination — OpenMP tasks + `std::execution::par` + `-ltbb` under ASan/UBSan — was smoke-tested clean on this machine on 2026-07-17. If ASan nevertheless reports something inside libtbb/libgomp internals here, do NOT suppress it silently: report BLOCKED with the sanitizer output.)

- [ ] **Step 6: Commit**

```bash
git add cpp_algo_lab/parallel
git commit -m "feat(cpp_algo_lab): add OpenMP task merge sort and parallel-STL rung"
```

---

### Task 3: OpenMP chunked BMH search with boundary-overlap correctness

**Files:**
- Create: `cpp_algo_lab/parallel/include/parallel/omp_search.hpp`
- Modify: `cpp_algo_lab/parallel/tests/test_parallel.cpp` (append; add includes)

**Interfaces:**
- Consumes: `lab::bmh_search` (`search/bmh.hpp`), `lab::naive_search` (`search/naive.hpp`, independent test reference), `lab::generate_text` / `lab::pattern_for` (`lab/textgen.hpp`).
- Produces: `lab::omp_bmh_search(std::string_view text, std::string_view pattern, int threads = 0) -> std::vector<std::size_t>` — bit-identical results to `lab::bmh_search` for every thread count.

- [ ] **Step 1: Append failing tests**

Add to the include block: `#include "lab/textgen.hpp"`, `#include "parallel/omp_search.hpp"` (after omp_merge), `#include "search/bmh.hpp"`, `#include "search/naive.hpp"`. Append:

```cpp
TEST_CASE("omp_bmh_search: agrees with sequential bmh on generated corpora") {
    for (const lab::Text t : lab::all_texts()) {
        for (const std::size_t n : {std::size_t{1}, std::size_t{64}, std::size_t{4096},
                                    std::size_t{65536}}) {
            const std::string text = lab::generate_text(t, n, 42);
            for (const std::size_t m : {std::size_t{1}, std::size_t{4}, std::size_t{16},
                                        std::size_t{64}}) {
                if (m > n) continue;
                const std::string pattern = lab::pattern_for(t, text, m, 42);
                const auto ref = lab::bmh_search(text, pattern);
                for (const int threads : {1, 2, 3, 5, 8, 20}) {
                    INFO("text=" << lab::text_name(t) << " n=" << n << " m=" << m
                                 << " threads=" << threads);
                    CHECK(lab::omp_bmh_search(text, pattern, threads) == ref);
                }
            }
        }
    }
}

TEST_CASE("omp_bmh_search: matches straddling every chunk boundary are found") {
    // Plant the pattern at start positions that straddle each internal chunk
    // boundary (b-(m-1): maximal straddle; b-1: one char before; b: first
    // owned start). The chunk arithmetic here mirrors the implementation's
    // lo_c = starts*c/threads split on purpose -- if the implementation's
    // split changes, this test must be updated with it.
    const std::string pattern = "NEEDLE";
    const std::size_t m = pattern.size();
    for (const int threads : {2, 3, 4, 7, 16}) {
        const std::size_t n = 1000;
        std::string text(n, 'x');
        const std::size_t starts = n - m + 1;
        const auto nchunks = static_cast<std::size_t>(threads);
        std::vector<std::size_t> planted;
        for (std::size_t c = 1; c < nchunks; ++c) {
            const std::size_t b = starts * c / nchunks;  // first start owned by chunk c
            // b >= starts/16 = 62 > m-1 here, so b-(m-1) cannot underflow.
            for (const std::size_t pos : {b - (m - 1), b - 1, b}) {
                if (pos + m <= n && (planted.empty() || pos >= planted.back() + m))
                    planted.push_back(pos);
            }
        }
        for (const std::size_t pos : planted) text.replace(pos, m, pattern);
        const auto expected = lab::naive_search(text, pattern);
        REQUIRE(expected == planted);  // construction sanity: exactly the planted set
        INFO("threads=" << threads);
        CHECK(lab::omp_bmh_search(text, pattern, threads) == expected);
    }
}

TEST_CASE("omp_bmh_search: overlapping matches across boundaries") {
    // All-'a' text with pattern "aaa": every start position matches, so any
    // dropped or duplicated boundary position changes the result.
    const std::string text(1000, 'a');
    const auto ref = lab::naive_search(text, "aaa");
    CHECK(ref.size() == 998);
    for (const int threads : {2, 3, 7, 20}) {
        INFO("threads=" << threads);
        CHECK(lab::omp_bmh_search(text, "aaa", threads) == ref);
    }
}

TEST_CASE("omp_bmh_search: module conventions hold for every thread count") {
    using Occ = std::vector<std::size_t>;
    for (const int threads : {1, 8}) {
        CHECK(lab::omp_bmh_search("abc", "", threads) == Occ{0, 1, 2, 3});
        CHECK(lab::omp_bmh_search("", "", threads) == Occ{0});
        CHECK(lab::omp_bmh_search("", "a", threads).empty());
        CHECK(lab::omp_bmh_search("ab", "abc", threads).empty());
        CHECK(lab::omp_bmh_search("abc", "abc", threads) == Occ{0});
        CHECK(lab::omp_bmh_search("xxab", "ab", threads) == Occ{2});
        CHECK(lab::omp_bmh_search("banana", "a", threads) == Occ{1, 3, 5});
    }
    // More threads than candidate start positions: empty chunks must be fine.
    CHECK(lab::omp_bmh_search("needle", "needle", 20) == Occ{0});
}
```

- [ ] **Step 2: Run to verify failure**

Run from `cpp_algo_lab/`: `make test`
Expected: FAIL to compile — `parallel/omp_search.hpp: No such file or directory`.

- [ ] **Step 3: Implement `parallel/include/parallel/omp_search.hpp`**

```cpp
#pragma once
// Search parallelization: embarrassingly parallel chunking. The n-m+1 start
// positions are split into `threads` contiguous ranges; chunk c scans the
// slice text.substr(lo_c, (hi_c-lo_c) + m-1). A slice of that length can
// only contain matches starting at slice offsets 0..hi_c-lo_c-1, so every
// match is found by exactly one chunk: no duplicates, no misses, no
// post-filtering -- correctness BY CONSTRUCTION. The classic off-by-one
// (forgetting the m-1 overlap tail) is exactly what the boundary-planting
// tests probe. Each chunk rebuilds the BMH shift table (m-1 stores): the
// honest price of shared-nothing parallelism, negligible for m << n/threads.
#include <cstddef>
#include <omp.h>
#include <string_view>
#include <vector>

#include "search/bmh.hpp"

namespace lab {

// threads <= 0 means the OpenMP default (all cores). Degenerate cases
// (empty pattern, pattern longer than text, one thread) delegate to the
// sequential implementation so the module conventions hold verbatim.
inline std::vector<std::size_t> omp_bmh_search(std::string_view text, std::string_view pattern,
                                               int threads = 0) {
    const std::size_t n = text.size(), m = pattern.size();
    if (threads <= 0) threads = omp_get_max_threads();
    if (m == 0 || m > n || threads == 1) return bmh_search(text, pattern);

    const std::size_t starts = n - m + 1;  // candidate start positions
    const std::size_t nchunks = static_cast<std::size_t>(threads);
    std::vector<std::vector<std::size_t>> local(nchunks);

#pragma omp parallel for schedule(static) num_threads(threads)
    for (std::size_t c = 0; c < nchunks; ++c) {
        const std::size_t lo = starts * c / nchunks;
        const std::size_t hi = starts * (c + 1) / nchunks;
        if (lo == hi) continue;  // more chunks than start positions
        const std::string_view slice = text.substr(lo, (hi - lo) + m - 1);
        std::vector<std::size_t> found = bmh_search(slice, pattern);
        for (std::size_t& p : found) p += lo;
        local[c] = std::move(found);
    }

    std::size_t total = 0;
    for (const auto& v : local) total += v.size();
    std::vector<std::size_t> out;
    out.reserve(total);
    for (auto& v : local) out.insert(out.end(), v.begin(), v.end());
    return out;
}

}  // namespace lab
```

- [ ] **Step 4: Run to verify pass**

Run from `cpp_algo_lab/`: `make test`
Expected: all four binaries SUCCESS.

- [ ] **Step 5: Commit**

```bash
git add cpp_algo_lab/parallel
git commit -m "feat(cpp_algo_lab): add OpenMP chunked BMH search with overlap-slice correctness"
```

---

### Task 4: Umbrella header + parallel benchmark + Makefile bench targets

**Files:**
- Create: `cpp_algo_lab/parallel/include/parallel/all.hpp`
- Create: `cpp_algo_lab/parallel/bench/bench_parallel.cpp`
- Modify: `cpp_algo_lab/Makefile` (add `bench_parallel` binary + `bench-parallel` / `bench-parallel-quick` targets; `bench` gains bench-parallel)

**Interfaces:**
- Consumes: everything from Tasks 1–3; `lab::{generate,generate_text,pattern_for}`, `lab::{CsvWriter,cell,print_table,time_ms,median}`, `lab::bmh_search`, `lab::merge_sort`.
- Produces: `results/parallel_sort.csv` and `results/parallel_search.csv` with the exact schemas from Fixed design values (Task 5 runs the full sweep; Task 6 plots them).

- [ ] **Step 1: Implement `parallel/include/parallel/all.hpp`**

```cpp
#pragma once
// Umbrella header for the CPU parallel ladder.
#include "parallel/omp_merge.hpp"
#include "parallel/omp_search.hpp"
#include "parallel/par_stl.hpp"
#include "parallel/thread_merge.hpp"
#include "parallel/tuning.hpp"
```

- [ ] **Step 2: Implement `parallel/bench/bench_parallel.cpp`**

```cpp
// CPU parallel ladder benchmark -> results/parallel_sort.csv and
// results/parallel_search.csv. Sort: fixed workload n=2^24 random ints,
// thread sweep per rung (thread_merge only at powers of two -- its
// divide-and-conquer spawns whole levels). Search: n=2^26 chars (english and
// dna), m=16, thread sweep for the OpenMP chunked BMH. Every configuration's
// output is verified against the sequential reference on its first repeat.
// Run from cpp_algo_lab/ on an otherwise idle machine. Full run ~2-3 min.
#include <algorithm>
#include <cstddef>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

#include "lab/csv.hpp"
#include "lab/datagen.hpp"
#include "lab/table.hpp"
#include "lab/textgen.hpp"
#include "lab/timer.hpp"
#include "parallel/all.hpp"
#include "search/bmh.hpp"

namespace {

using Summary = std::vector<std::vector<std::string>>;

void run_sort_bench(bool quick, lab::CsvWriter& csv, Summary& summary) {
    const std::size_t n = quick ? (std::size_t{1} << 20) : (std::size_t{1} << 24);
    const int repeats = quick ? 2 : 5;
    const std::vector<int> data = lab::generate(lab::Dist::random_uniform, n, 42);
    std::vector<int> reference = data;
    std::sort(reference.begin(), reference.end());

    struct Config {
        std::string algo;
        int threads;
        std::function<void(std::vector<int>&)> run;
    };
    std::vector<Config> configs;
    configs.push_back({"merge_seq", 1,
                       [](std::vector<int>& v) { lab::merge_sort(v.begin(), v.end()); }});
    configs.push_back({"std_sort_seq", 1,
                       [](std::vector<int>& v) { std::sort(v.begin(), v.end()); }});
    for (const unsigned t : quick ? std::vector<unsigned>{1, 4}
                                  : std::vector<unsigned>{1, 2, 4, 8, 16})
        configs.push_back({"thread_merge", static_cast<int>(t), [t](std::vector<int>& v) {
                               lab::thread_merge_sort(v.begin(), v.end(), std::less<>{}, t);
                           }});
    for (const int t : quick ? std::vector<int>{1, 4}
                             : std::vector<int>{1, 2, 4, 6, 8, 12, 16, 20})
        configs.push_back({"omp_merge", t, [t](std::vector<int>& v) {
                               lab::omp_merge_sort(v.begin(), v.end(), std::less<>{}, t);
                           }});
    // threads=0 in the CSV means "library default (all cores)" -- par-STL's
    // thread count is the library's business (no TBB headers vendored).
    configs.push_back({"par_stl", 0,
                       [](std::vector<int>& v) { lab::par_stl_sort(v.begin(), v.end()); }});

    for (const auto& c : configs) {
        std::vector<double> ts;
        for (int r = 0; r < repeats; ++r) {
            std::vector<int> v = data;
            ts.push_back(lab::time_ms([&] { c.run(v); }));
            if (r == 0 && v != reference) {
                std::cerr << "FATAL: " << c.algo << " threads=" << c.threads << " mis-sorted\n";
                std::exit(1);
            }
        }
        const double med = lab::median(ts);
        csv.write_row({c.algo, lab::cell(c.threads), lab::cell(n), lab::cell(repeats),
                       lab::cell(med)});
        summary.push_back({"sort/" + c.algo, lab::cell(c.threads), lab::cell(med)});
        std::cout << "sort " << c.algo << " t=" << c.threads << ": " << med << " ms\n";
    }
}

void run_search_bench(bool quick, lab::CsvWriter& csv, Summary& summary) {
    const std::size_t n = quick ? (std::size_t{1} << 22) : (std::size_t{1} << 26);
    const std::size_t m = 16;
    const int repeats = quick ? 2 : 5;
    for (const lab::Text t : {lab::Text::english_like, lab::Text::dna}) {
        const std::string text = lab::generate_text(t, n, 42);
        const std::string pattern = lab::pattern_for(t, text, m, 42);
        const std::vector<std::size_t> reference = lab::bmh_search(text, pattern);

        struct Config {
            std::string algo;
            int threads;
        };
        std::vector<Config> configs{{"bmh_seq", 1}};
        for (const int th : quick ? std::vector<int>{1, 4}
                                  : std::vector<int>{1, 2, 4, 6, 8, 12, 16, 20})
            configs.push_back({"omp_bmh", th});

        for (const auto& c : configs) {
            std::vector<double> ts;
            for (int r = 0; r < repeats; ++r) {
                std::vector<std::size_t> occ;
                ts.push_back(lab::time_ms([&] {
                    occ = c.algo == "bmh_seq" ? lab::bmh_search(text, pattern)
                                              : lab::omp_bmh_search(text, pattern, c.threads);
                }));
                if (r == 0 && occ != reference) {
                    std::cerr << "FATAL: " << c.algo << " threads=" << c.threads
                              << " disagrees with sequential bmh (text=" << lab::text_name(t)
                              << ")\n";
                    std::exit(1);
                }
            }
            const double med = lab::median(ts);
            csv.write_row({c.algo, std::string(lab::text_name(t)), lab::cell(c.threads),
                           lab::cell(n), lab::cell(m), lab::cell(repeats), lab::cell(med),
                           lab::cell(reference.size())});
            summary.push_back({"search/" + c.algo + "/" + std::string(lab::text_name(t)),
                               lab::cell(c.threads), lab::cell(med)});
            std::cout << "search " << c.algo << " " << lab::text_name(t)
                      << " t=" << c.threads << ": " << med << " ms\n";
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    bool quick = false;
    for (int i = 1; i < argc; ++i)
        if (std::strcmp(argv[i], "--quick") == 0) quick = true;

    lab::CsvWriter sort_csv("results/parallel_sort.csv",
                            {"algo", "threads", "n", "repeats", "median_ms"});
    lab::CsvWriter search_csv("results/parallel_search.csv",
                              {"algo", "text", "threads", "n", "m", "repeats", "median_ms",
                               "occurrences"});
    Summary summary;
    run_sort_bench(quick, sort_csv, summary);
    run_search_bench(quick, search_csv, summary);
    std::cout << "\nSummary (median ms):\n";
    lab::print_table({"config", "threads", "median_ms"}, summary);
    std::cout << "\nCSV written to results/parallel_{sort,search}.csv\n";
    return 0;
}
```

- [ ] **Step 3: Add the bench targets to the Makefile**

Insert after the `$(BUILD)/bench_search` rule:

```make
$(BUILD)/bench_parallel: parallel/bench/bench_parallel.cpp $(PAR_HDRS) $(SEARCH_HDRS) $(SORT_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(BENCHFLAGS) $(OMPFLAGS) $< -o $@ $(TBBLIB)
```

Change the `bench:` line and add the two targets after `bench-search-quick`:

```make
bench: bench-sorting bench-search bench-parallel

bench-parallel: $(BUILD)/bench_parallel
	$(BUILD)/bench_parallel

bench-parallel-quick: $(BUILD)/bench_parallel
	$(BUILD)/bench_parallel --quick
```

Update the `.PHONY` line to:

```make
.PHONY: all test bench bench-sorting bench-search bench-parallel bench-quick bench-search-quick bench-parallel-quick trace plot plot-sorting plot-search clean
```

Add `$(BUILD)/bench_parallel` to the `all:` prerequisites (end of the line).

- [ ] **Step 4: Wire check with the quick sweep**

Run from `cpp_algo_lab/`: `make bench-parallel-quick`
Expected: builds warning-free; prints sort lines (merge_seq, std_sort_seq, thread_merge t=1/4, omp_merge t=1/4, par_stl) then search lines for english and dna, a summary table, no FATAL. Quick CSV rows (incl. header): parallel_sort.csv 8 (2+2+2+1+1), parallel_search.csv 7 (2 texts × 3 + 1).

- [ ] **Step 5: Run `make test` (regression — Makefile changed) and commit**

```bash
cd cpp_algo_lab && make test && cd ..
git add cpp_algo_lab/parallel cpp_algo_lab/Makefile
git commit -m "feat(cpp_algo_lab): add CPU parallel benchmark with thread sweeps"
```

(The quick CSVs are NOT committed — Task 5 commits the full-sweep versions.)

---

### Task 5: Full parallel sweep + physics checks + committed CSVs

**Files:**
- Create (generated, committed): `cpp_algo_lab/results/parallel_sort.csv`, `cpp_algo_lab/results/parallel_search.csv`

**Interfaces:**
- Consumes: `make bench-parallel` (Task 4).
- Produces: the committed full-sweep CSVs (Task 6 plots them; Task 7 quotes them).

- [ ] **Step 1: Run the FULL sweep on an idle machine**

Run from `cpp_algo_lab/`: `make bench-parallel`
Expected: ~2–3 minutes; no FATAL lines. Row counts incl. header: `parallel_sort.csv` 17 (2 + 5 + 8 + 1 data rows), `parallel_search.csv` 19 (2 texts × 9).

- [ ] **Step 2: Physics checks (thresholds are deliberately loose — single-sample WSL2 medians; do NOT tighten them)**

From repo root:

```bash
python3 - <<'EOF'
import csv
sort = list(csv.DictReader(open("cpp_algo_lab/results/parallel_sort.csv")))
search = list(csv.DictReader(open("cpp_algo_lab/results/parallel_search.csv")))
def ms(rows, **kv):
    for r in rows:
        if all(r[k] == str(v) for k, v in kv.items()):
            return float(r["median_ms"])
    raise KeyError(kv)
# 1) omp_merge speeds up: t=8 at least 2x faster than its own t=1
assert ms(sort, algo="omp_merge", threads=8) < ms(sort, algo="omp_merge", threads=1) / 2, "omp_merge t=8"
# 2) thread_merge speeds up: t=16 faster than t=1
assert ms(sort, algo="thread_merge", threads=16) < ms(sort, algo="thread_merge", threads=1), "thread_merge"
# 3) par_stl (all cores) beats sequential std::sort clearly
assert ms(sort, algo="par_stl", threads=0) < 0.8 * ms(sort, algo="std_sort_seq", threads=1), "par_stl"
# 4) omp_bmh scales on english: t=8 at least 3x faster than t=1
assert ms(search, algo="omp_bmh", text="english", threads=8) < ms(search, algo="omp_bmh", text="english", threads=1) / 3, "omp_bmh english t=8"
# 5) search occurrences identical across all thread counts per text (column constant)
for text in ("english", "dna"):
    occ = {r["occurrences"] for r in search if r["text"] == text}
    assert len(occ) == 1, (text, occ)
print("physics ok")
EOF
```

Expected: `physics ok`. If a check fails, do NOT relax it yourself — report BLOCKED with the failing numbers (controller adjudicates; the Phase 2 precedent is that thresholds may be plan bugs, but that call is not the implementer's).

- [ ] **Step 3: Sanity-judge the summary table**

Beyond the scripted checks: medians must be positive and MAD non-negative. Judge any late-thread regression against MAD and a second independent run; do not silently relabel it as oversubscription. On this WSL2 environment `lscpu` reports 20 CPUs, 20 cores, and one thread per core, so t=20 is not oversubscription by count alone. If anything looks physically absurd, stop and report.

- [ ] **Step 4: Commit the CSVs**

```bash
git add cpp_algo_lab/results/parallel_sort.csv cpp_algo_lab/results/parallel_search.csv
git commit -m "feat(cpp_algo_lab): commit full CPU parallel sweep results"
```

Confirm with `git show --stat HEAD` that both CSVs are inside the commit.

---

### Task 6: Figures — `plot_parallel.py` (3 PNGs)

**Files:**
- Create: `cpp_algo_lab/scripts/plot_parallel.py`
- Modify: `cpp_algo_lab/Makefile` (plot section gains `plot-parallel`; `plot` runs all three)
- Create (generated, committed): `cpp_algo_lab/results/plots/parallel_sort_scaling.png`, `parallel_search_scaling.png`, `parallel_speedup.png`

**Interfaces:**
- Consumes: the two CSVs (Task 5), `labviz` module (Phase 2: `INK, MUTED, SLOTS, apply_style, save`).
- Produces: the 3 committed PNGs; `make plot-parallel`.

- [ ] **Step 1: Create `cpp_algo_lab/scripts/plot_parallel.py`**

```python
"""Render CPU parallel benchmark CSVs into PNG figures.

Run from repo root:  uv run --no-sync python cpp_algo_lab/scripts/plot_parallel.py
(or `make plot-parallel` inside cpp_algo_lab/). Reads results/parallel_*.csv,
writes results/plots/parallel_*.png.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from labviz import INK, MUTED, SLOTS, apply_style, save

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"
PLOTS = RESULTS / "plots"

SORT_COLOR = {"thread_merge": SLOTS[0], "omp_merge": SLOTS[1]}
SEARCH_COLOR = {"english": SLOTS[2], "dna": SLOTS[3]}
REF_STYLE = {"merge_seq": "--", "std_sort_seq": "-.", "par_stl": ":"}

apply_style()


def curve(df: pd.DataFrame, algo: str, text: str | None = None) -> pd.DataFrame:
    sub = df[df["algo"] == algo]
    if text is not None:
        sub = sub[sub["text"] == text]
    return sub.sort_values("threads")


def ref_line(ax, label: str, y: float, ls: str) -> None:
    ax.axhline(y, color=MUTED, linestyle=ls, linewidth=1.4, label=f"{label} ({y:.0f} ms)")


def fig_sort_scaling(sort: pd.DataFrame) -> None:
    n = int(sort["n"].iloc[0])
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    for algo, color in SORT_COLOR.items():
        s = curve(sort, algo)
        ax.plot(s["threads"], s["median_ms"], color=color, marker="o", markersize=5,
                label=algo)
    ref_line(ax, "merge_seq", curve(sort, "merge_seq")["median_ms"].iloc[0], "--")
    ref_line(ax, "std_sort_seq", curve(sort, "std_sort_seq")["median_ms"].iloc[0], "-.")
    ref_line(ax, "par_stl (all cores)", curve(sort, "par_stl")["median_ms"].iloc[0], ":")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("threads")
    ax.set_ylabel("median wall time [ms]")
    ax.set_xticks([1, 2, 4, 8, 16, 20], [1, 2, 4, 8, 16, 20])
    ax.legend(fontsize=8, framealpha=0.9)
    ax.set_title(f"Parallel sort: time vs threads (n=2^24={n})", color=INK)
    save(fig, PLOTS, "parallel_sort_scaling.png")


def fig_search_scaling(search: pd.DataFrame) -> None:
    n = int(search["n"].iloc[0])
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), sharey=True)
    for ax, text in zip(axes, ["english", "dna"], strict=True):
        s = curve(search, "omp_bmh", text)
        ax.plot(s["threads"], s["median_ms"], color=SEARCH_COLOR[text], marker="o",
                markersize=5, label=f"omp_bmh ({text})")
        seq = curve(search, "bmh_seq", text)["median_ms"].iloc[0]
        ax.axhline(seq, color=MUTED, linestyle="--", linewidth=1.4,
                   label=f"bmh_seq ({seq:.0f} ms)")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xticks([1, 2, 4, 8, 16, 20], [1, 2, 4, 8, 16, 20])
        ax.set_xlabel("threads")
        ax.set_title(f"text: {text}", color=INK)
        ax.legend(fontsize=8, framealpha=0.9)
    axes[0].set_ylabel("median wall time [ms]")
    fig.suptitle(f"Parallel search: time vs threads (n=2^26={n}, m=16)", color=INK)
    save(fig, PLOTS, "parallel_search_scaling.png")


def fig_speedup(sort: pd.DataFrame, search: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.5, 5.6))
    max_t = 20
    ax.plot([1, max_t], [1, max_t], color=MUTED, linestyle=":", linewidth=1.4,
            label="ideal (y = x)")

    def speedup(sub: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        base = sub[sub["threads"] == 1]["median_ms"].iloc[0]
        return sub["threads"], base / sub["median_ms"]

    for algo, color in SORT_COLOR.items():
        t, sp = speedup(curve(sort, algo))
        ax.plot(t, sp, color=color, marker="o", markersize=5, label=f"sort: {algo}")
    for text, color in SEARCH_COLOR.items():
        t, sp = speedup(curve(search, "omp_bmh", text))
        ax.plot(t, sp, color=color, marker="s", markersize=5, label=f"search: omp_bmh ({text})")

    ax.set_xlabel("threads")
    ax.set_ylabel("speedup vs 1 thread (same implementation)")
    ax.set_xticks([1, 2, 4, 6, 8, 12, 16, 20])
    ax.legend(fontsize=8, framealpha=0.9, loc="upper left")
    ax.set_title(
        "The ladder's conclusion: search scales, sort plateaus\n"
        "(merge's final join is sequential; chunked search has no join)",
        color=INK,
    )
    save(fig, PLOTS, "parallel_speedup.png")


def main() -> None:
    sort = pd.read_csv(RESULTS / "parallel_sort.csv")
    search = pd.read_csv(RESULTS / "parallel_search.csv")
    fig_sort_scaling(sort)
    fig_search_scaling(search)
    fig_speedup(sort, search)
    print("all parallel figures written to", PLOTS)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Update the Makefile plot section**

Replace the plot section so it reads (and extend `.PHONY` with `plot-parallel`):

```make
plot: plot-sorting plot-search plot-parallel

plot-sorting:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_results.py

plot-search:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_search.py

plot-parallel:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_parallel.py
```

- [ ] **Step 3: Generate the figures + run the gates**

From repo root:

```bash
uv run --no-sync python cpp_algo_lab/scripts/plot_parallel.py
uv run --no-sync ruff check cpp_algo_lab/scripts
uv run --no-sync ruff format --check cpp_algo_lab/scripts
```

Expected: 3 `wrote ...` lines; both ruff gates clean (mechanical fixes sanctioned — note each in your report).

**Visually verify each PNG** (open the files): (1) sort_scaling shows both curves dropping then flattening, with par_stl as a distinct unstable-library reference; (2) search_scaling honestly shows both the near-linear region and any measured late-thread regression; (3) speedup states the measured scope rather than assuming monotonic scaling. MAD bars, legends, and the t=6/t=12 ticks must be readable. Do not reject a physically plausible regression merely because it complicates the planned headline.

- [ ] **Step 4: Run `make test` (regression) and commit**

```bash
cd cpp_algo_lab && make test && cd ..
git add cpp_algo_lab/scripts/plot_parallel.py cpp_algo_lab/Makefile cpp_algo_lab/results/plots
git commit -m "feat(cpp_algo_lab): add CPU parallel scaling figures"
```

---

### Task 7: Japanese docs — `docs/parallel_cpu.md` + README + references (fable implementer)

**Files:**
- Create: `cpp_algo_lab/docs/parallel_cpu.md`
- Modify: `cpp_algo_lab/README.md`
- Modify: `cpp_algo_lab/docs/references.md`
- Modify: `cpp_algo_lab/scripts/plot_results.py:3-4` (one-word docstring touch-up, deferred from Phase 2)

**Interfaces:**
- Consumes: committed CSVs (Task 5), 3 PNGs (Task 6), all parallel headers, `docs/sorting.md` and `docs/search.md` (style references).
- Produces: the Phase 3 learning centerpiece. **Every empirical number quoted must be read from the committed CSVs** (python3 one-liners from repo root; Read tool is denied on results/*.csv).

- [ ] **Step 1: Write `docs/parallel_cpu.md` (Japanese, ~250+ lines, structure binding)**

1. **§1 ラダーの思想** — 同じ問題を「手で並列化（std::thread）→ ランタイムに任せる（OpenMP task）→ ライブラリを買う（std::execution::par + TBB）」と段階的に登る。それぞれのコード量・制御できるもの・失うものの対比表。検索は別軸：「そもそも分割統治すら要らない（embarrassingly parallel）」。
2. **§2 並列マージソートの構造** — 再帰の形は 3 実装で共通（thread_merge.hpp / omp_merge.hpp のコード対応）。`kParallelSortCutoff`（2^15）の理由（spawn/task オーバーヘッド）。`merge_sort` が呼び出しごとに自前バッファを持つから並行呼び出し安全という設計上の再利用。**最後の `std::inplace_merge` は逐次**  — これが頭打ちの正体（クリティカルパスに O(n) の逐次結合が残る；Amdahl の法則の実物）。stability が保存される理由（安定な基底 + 安定な inplace_merge）。
3. **§3 OpenMP task と firstprivate** — `#pragma omp task` のデフォルトキャプチャ（locals → firstprivate）がイテレータのコピーを保証し dangling を防ぐこと。`num_threads` で任意スレッド数（thread_merge は 2 の冪のみ — depth_for_threads の意味）。
4. **§4 検索のチャンク分割と境界の証明** — omp_search.hpp の overlap-slice 不変条件を図解入りで：開始位置 [lo, hi) + スライス長 (hi−lo)+m−1 → 「重複なし・取りこぼしなしが構成的に成立」。off-by-one がどこに潜むか（m−1 を忘れる／フィルタで二重計上）。boundary-planting テストの読み方。チャンクごとの shift 表再構築 = shared-nothing の正直なコスト。
5. **§5 結果の読み方（3 図 × 実測値）** — 図ごとに 1 節、**引用数値は committed CSV と一致必須**：
   - `parallel_sort_scaling.png` — thread_merge / omp_merge の下降と頭打ち、merge_seq / std_sort_seq / par_stl の基準線。par_stl は不安定ソート、merge 系は安定ソートなので同一意味論の直接比較ではない。par_stl の優位は最適化済みバックエンド、異なるアルゴリズム、メモリ挙動を含む。
   - `parallel_search_scaling.png` — english / dna の t=1→12 の下降と、それ以降の飽和・逆転をMAD込みで記述する。
   - `parallel_speedup.png` — **見出しの結論**：検索は12スレッドまで理想直線に近いが、その後は検索も後退し得る。Amdahl の逆算は $s=(p/S(p)-1)/(p-1)$ とし、「実効逐次率」であってソースコード上の逐次部分そのものではないと明記する。
6. **§6 教訓・落とし穴** — WSL2 での計測ばらつき（中央値 + MAD、測定順シャッフル）、実測環境は20 CPU・20 core・1 thread/coreであること、t=20 の逆転はメモリ帯域・ランタイム・異種コア・WSL2 scheduling 等の候補を分離できていないこと、thread_merge の「2 の冪しか効かない」設計制約、ASan/UBSan はデータ競合を検出しないことを記す。
7. **§7 Phase 4 への接続** — 「検索 = 1 スレッド 1 開始位置」の極限が GPU（PFAC 的世界観、references の Kouzinopoulos）。ソートは GPU でも「賢い結合」が必要（bitonic / radix、Onesweep 系譜）— CPU で見た頭打ちが GPU で別の形で現れる予告。

- [ ] **Step 2: Update `README.md`**

- 概要段落: Phase 3 の一文（CPU 並列ラダー：thread/OpenMP/並列STL + チャンク検索、スケーリング実測）。
- クイックスタート表: `make bench-parallel` / `make bench-parallel-quick` / `make plot-parallel` を追加、`make bench` の説明を「ソート+検索+並列の全計測」に、`make plot` を「全図（ソート 6 + 検索 5 + 並列 3 = 14 枚）」に更新。
- 構成ツリー: `parallel/` を search/ の後に追加（include/parallel/=CPU ラダー 5 ヘッダ、tests/、bench/ の行）、`scripts/` に `plot_parallel.py`、`docs/` に `parallel_cpu.md`。
- 学習ロードマップ: ステップ追加 — `docs/parallel_cpu.md` → `parallel/include/parallel/` を tuning → thread_merge → omp_merge → par_stl → omp_search の順で読む（「手動 → ランタイム → ライブラリ → 分割統治すら不要」の積み上げ）→ `make bench-parallel && make plot-parallel` → speedup 図と §5 の突き合わせ。
- Phase 状況表: Phase 3 を ✅ に。
- 依存節: Phase 3 の OpenMP/libgomp と TBB（`std::execution::par` backend）を追加し、「C++側の外部依存ゼロ」という旧記述を訂正する。

- [ ] **Step 3: Update `docs/references.md`**

新節「並列化（Phase 3 で使用）」を「文字列検索」節の後に追加:

- **Amdahl, Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities (AFIPS 1967)** — 逐次分数が speedup の上限を決める法則。parallel_speedup.png のソート頭打ちを §5 で逆算する際の出典。
- 既存の IPS⁴o 行はソート節にあるまま参照（Phase 3 の「現実の到達点」参考値、と一言添える更新は任意）。

- [ ] **Step 4: plot_results.py docstring touch-up (deferred from Phase 2)**

In `cpp_algo_lab/scripts/plot_results.py` lines 3–4, change `(or `make plot` inside cpp_algo_lab/)` to `(or `make plot-sorting` inside cpp_algo_lab/)`. Nothing else in the file changes. Run both ruff gates after.

- [ ] **Step 5: Cross-check every number, then commit**

```bash
git add cpp_algo_lab/docs/parallel_cpu.md cpp_algo_lab/docs/references.md cpp_algo_lab/README.md cpp_algo_lab/scripts/plot_results.py
git commit -m "docs(cpp_algo_lab): add CPU parallel learning notes and update README/references"
```

---

## Verification (whole phase)

1. `make test` from `cpp_algo_lab/` — four doctest binaries SUCCESS under ASan/UBSan (no-recover), warning-free.
2. `make bench-parallel-quick` leaves both canonical result hashes unchanged and writes ignored quick CSVs under `build/`.
3. `make bench-parallel` regenerates both staged-then-published CSVs; committed versions from a full run (rows incl. header 17 / 19) include `mad_ms`.
4. `make plot` renders 6 + 5 + 3 PNGs; committed parallel PNGs match validated full-sweep CSVs.
5. Both ruff gates clean from repo root.
6. `docs/parallel_cpu.md` quotes only numbers present in (or exactly derivable from) the committed CSVs and distinguishes measured facts from causal hypotheses.
