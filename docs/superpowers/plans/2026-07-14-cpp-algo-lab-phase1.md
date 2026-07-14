# cpp_algo_lab Phase 1 (Foundation + Sorting) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `cpp_algo_lab/` project skeleton, the shared measurement library, and the complete sorting module: 10 sorting algorithms with STL-style interfaces, doctest tests under sanitizers, a benchmark producing CSVs (time / operation counts / stability), trace snapshots, matplotlib visualizations, and rich Japanese docs.

**Architecture:** Header-only C++20 library (`common/lab/*.hpp` shared infra + `sorting/include/sorting/*.hpp` one header per algorithm), a single benchmark executable writing CSVs to `results/`, and one Python script rendering PNGs from those CSVs. Tests are doctest binaries built with ASan+UBSan. Spec: `docs/superpowers/specs/2026-07-14-cpp-algo-lab-design.md` (this plan covers Phase 1 only; Phases 2–5 get their own plans).

**Tech Stack:** g++ 13.3 (C++20), GNU make, doctest (vendored single header, the only dependency), Python via repo-root uv workspace (pandas 3.0.3 / matplotlib 3.10.9) for plotting only.

## Global Constraints

- Compiler: `g++` only, `-std=c++20 -Wall -Wextra -Wpedantic`. No cmake, no clang.
- Test builds: `-O1 -g -fsanitize=address,undefined`. Bench builds: `-O2 -DNDEBUG`.
- Only vendored dependency: `third_party/doctest/doctest.h`. No other libraries in C++ code.
- All C++ code, identifiers, comments, and commit messages in English. All `docs/*.md`, `README.md` prose in Japanese.
- Everything lives under `cpp_algo_lab/` except: 1 line in root `README.md` index, 1 line in root `Makefile` help text (Task 12).
- `make` targets are run from `cpp_algo_lab/` (bench writes CSVs to relative `results/`).
- `results/` CSVs and PNGs are committed (workspace precedent: deep_hedge_price). `build/` is gitignored.
- Python runs via repo root: `uv run --no-sync ...` (never create a venv inside `cpp_algo_lab/`).
- Namespace for all C++ code: `lab`.
- Commit message prefix: `feat(cpp_algo_lab):` / `test(cpp_algo_lab):` / `docs(cpp_algo_lab):`.

## Fixed design values (used across tasks)

- Distributions: `random_uniform, sorted_asc, reversed, nearly_sorted, few_unique`; values are non-negative ints in `[0, n)` (so counting sort is feasible: key range ≈ n).
- N sweep: `{256, 1024, 4096, 16384, 65536, 262144, 1048576}`; per-algorithm cap: bubble/insertion/selection stop at `32768` (extra point `32768` added for them), all others run the full sweep.
- Bench repeats: 5 (median). Quick mode: Ns `{256, 1024, 4096}`, repeats 2.
- Algorithms (families): `n2` = bubble, insertion, selection, shell; `nlogn` = merge, quick, heap, std_sort, std_stable_sort; `linear` = counting, radix, bucket.
- Chart palette (dataviz reference palette, light mode): series slots in fixed order `#2a78d6` (blue), `#1baf7a` (aqua), `#eda100` (yellow), `#008300` (green); baselines (std_sort/std_stable_sort) always neutral `#898781` dashed. Surface `#fcfcfb`, ink `#0b0b0b`, secondary `#52514e`, muted `#898781`, grid `#e1e0d9`. Sequential ramp (heatmap/traces): `#cde2fb → #0d366b` (13 steps, Task 10).

---

### Task 1: Scaffolding, vendored doctest, Makefile skeleton

**Files:**
- Create: `cpp_algo_lab/.gitignore`
- Create: `cpp_algo_lab/third_party/doctest/doctest.h` (downloaded)
- Create: `cpp_algo_lab/common/tests/test_common.cpp` (smoke only, grows in Tasks 2–4)
- Create: `cpp_algo_lab/Makefile`

**Interfaces:**
- Consumes: nothing.
- Produces: `make test` entry point; include roots `-Icommon -Isorting/include -Ithird_party` (so code writes `#include "lab/counted.hpp"`, `#include "sorting/bubble.hpp"`, `#include "doctest/doctest.h"`).

- [ ] **Step 1: Create directory tree and .gitignore**

```bash
mkdir -p cpp_algo_lab/{third_party/doctest,common/lab,common/tests,sorting/include/sorting,sorting/tests,sorting/bench,scripts,results/plots,results/traces,docs}
```

Create `cpp_algo_lab/.gitignore`:

```gitignore
build/
# The workspace root .gitignore ignores *.csv globally; benchmark outputs
# under results/ are deliberately committed (see the Phase 1 plan).
!results/**
```

Note (2026-07-14, during execution): the `!results/**` re-include was added at Task 8
time — the plan originally missed that the workspace root `.gitignore` has a global
`*.csv` pattern, which silently kept `results/` out of Task 8's commit (fixed in
`c5b9ada`).

- [ ] **Step 2: Vendor doctest single header (pinned v2.4.11)**

```bash
curl -fsSL https://raw.githubusercontent.com/doctest/doctest/v2.4.11/doctest/doctest.h \
  -o cpp_algo_lab/third_party/doctest/doctest.h
head -5 cpp_algo_lab/third_party/doctest/doctest.h
```

Expected: file ~650KB; head shows the doctest banner comment. If the URL fails, use the latest v2.4.x tag from https://github.com/doctest/doctest/releases.

- [ ] **Step 3: Write the smoke test (failing build first — no Makefile yet)**

`cpp_algo_lab/common/tests/test_common.cpp`:

```cpp
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest/doctest.h"

TEST_CASE("smoke: doctest runs under sanitizers") {
    CHECK(1 + 1 == 2);
}
```

- [ ] **Step 4: Write the Makefile**

`cpp_algo_lab/Makefile`:

```make
# cpp_algo_lab — build/test/bench/plot. Run make from this directory.
.DEFAULT_GOAL := test
CXX      := g++
STD      := -std=c++20
WARN     := -Wall -Wextra -Wpedantic
INC      := -Icommon -Isorting/include -Ithird_party
TESTFLAGS  := $(STD) $(WARN) $(INC) -O1 -g -fsanitize=address,undefined
BENCHFLAGS := $(STD) $(WARN) $(INC) -O2 -DNDEBUG
BUILD    := build

COMMON_HDRS  := $(wildcard common/lab/*.hpp)
SORT_HDRS    := $(wildcard sorting/include/sorting/*.hpp)

.PHONY: all test bench bench-quick trace plot clean

all: $(BUILD)/test_common $(BUILD)/test_sorting $(BUILD)/bench_sorting

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/test_common: common/tests/test_common.cpp $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $< -o $@

$(BUILD)/test_sorting: sorting/tests/test_sorting.cpp $(SORT_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(TESTFLAGS) $< -o $@

$(BUILD)/bench_sorting: sorting/bench/bench_sorting.cpp $(SORT_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(BENCHFLAGS) $< -o $@

test: $(BUILD)/test_common
	$(BUILD)/test_common

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

Note: `test` runs only `test_common` for now; Task 5 extends it to `test_sorting` (shown there).

- [ ] **Step 5: Run the smoke test**

```bash
cd cpp_algo_lab && make test
```

Expected: compiles, runs, output contains `[doctest] Status: SUCCESS!`.

- [ ] **Step 6: Commit**

```bash
git add cpp_algo_lab
git commit -m "feat(cpp_algo_lab): scaffold project with vendored doctest and Makefile"
```

---

### Task 2: `Counted<T>` operation-counting wrapper

**Files:**
- Create: `cpp_algo_lab/common/lab/counted.hpp`
- Modify: `cpp_algo_lab/common/tests/test_common.cpp` (append)

**Interfaces:**
- Consumes: nothing.
- Produces (used by Tasks 5–9):
  - `struct lab::OpCounters { unsigned long long comparisons, moves, swaps; }`
  - `template <class T> class lab::Counted` — implicit ctor from `T`, `const T& value() const`, static `OpCounters& counters()` (thread-local), static `void reset_counters()`. All six comparison operators count 1 comparison each; copy/move ctor and assignment count 1 move each; ADL `swap` counts 1 swap (and no moves).

- [ ] **Step 1: Append failing tests**

Append to `cpp_algo_lab/common/tests/test_common.cpp`:

```cpp
#include "lab/counted.hpp"

#include <algorithm>
#include <utility>
#include <vector>

TEST_CASE("Counted: comparisons are counted") {
    using C = lab::Counted<int>;
    C::reset_counters();
    C a{1}, b{2};
    CHECK(a < b);
    CHECK_FALSE(b < a);
    CHECK(a <= b);
    CHECK(b > a);
    CHECK(b >= a);
    CHECK(a == a);
    CHECK(a != b);
    CHECK(C::counters().comparisons == 7);
    CHECK(C::counters().moves == 0);
    CHECK(C::counters().swaps == 0);
}

TEST_CASE("Counted: moves and swaps are counted") {
    using C = lab::Counted<int>;
    C::reset_counters();
    C a{1};
    C b = a;             // copy ctor -> 1 move
    C c = std::move(a);  // move ctor -> 1 move
    b = c;               // copy assign -> 1 move
    c = std::move(b);    // move assign -> 1 move
    CHECK(C::counters().moves == 4);
    C x{1}, y{2};
    C::reset_counters();
    using std::swap;
    swap(x, y);          // ADL swap -> 1 swap, 0 moves
    CHECK(C::counters().swaps == 1);
    CHECK(C::counters().moves == 0);
    CHECK(x.value() == 2);
    CHECK(y.value() == 1);
}

TEST_CASE("Counted: works with std::sort") {
    using C = lab::Counted<int>;
    std::vector<C> v{C{3}, C{1}, C{2}};
    C::reset_counters();
    std::sort(v.begin(), v.end());
    CHECK(C::counters().comparisons > 0);
    CHECK(v[0].value() == 1);
    CHECK(v[1].value() == 2);
    CHECK(v[2].value() == 3);
}
```

- [ ] **Step 2: Run to verify failure**

```bash
cd cpp_algo_lab && make test
```

Expected: FAIL — `lab/counted.hpp: No such file or directory`.

- [ ] **Step 3: Implement `counted.hpp`**

`cpp_algo_lab/common/lab/counted.hpp`:

```cpp
#pragma once
// Counted<T>: element wrapper that counts comparisons, moves and swaps.
// Feed a std::vector<Counted<int>> through any sort template to measure
// operation counts without touching the algorithm (time runs use plain int).
#include <utility>

namespace lab {

struct OpCounters {
    unsigned long long comparisons = 0;
    unsigned long long moves = 0;  // copy/move construction and assignment
    unsigned long long swaps = 0;  // ADL swap calls
};

template <class T>
class Counted {
public:
    Counted() = default;
    Counted(T v) : value_(std::move(v)) {}  // implicit: allows Counted<int> c = 3

    Counted(const Counted& o) : value_(o.value_) { ++counters().moves; }
    Counted(Counted&& o) noexcept : value_(std::move(o.value_)) { ++counters().moves; }
    Counted& operator=(const Counted& o) {
        value_ = o.value_;
        ++counters().moves;
        return *this;
    }
    Counted& operator=(Counted&& o) noexcept {
        value_ = std::move(o.value_);
        ++counters().moves;
        return *this;
    }

    const T& value() const noexcept { return value_; }

    static OpCounters& counters() {
        thread_local OpCounters c;
        return c;
    }
    static void reset_counters() { counters() = OpCounters{}; }

    friend bool operator<(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return a.value_ < b.value_;
    }
    friend bool operator>(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return b.value_ < a.value_;
    }
    friend bool operator<=(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return !(b.value_ < a.value_);
    }
    friend bool operator>=(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return !(a.value_ < b.value_);
    }
    friend bool operator==(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return a.value_ == b.value_;
    }
    friend bool operator!=(const Counted& a, const Counted& b) {
        ++counters().comparisons;
        return !(a.value_ == b.value_);
    }
    friend void swap(Counted& a, Counted& b) noexcept {
        using std::swap;
        swap(a.value_, b.value_);
        ++counters().swaps;
    }

private:
    T value_{};
};

}  // namespace lab
```

- [ ] **Step 4: Run tests**

```bash
cd cpp_algo_lab && make test
```

Expected: `Status: SUCCESS!` (4 test cases).

- [ ] **Step 5: Commit**

```bash
git add cpp_algo_lab/common
git commit -m "feat(cpp_algo_lab): add Counted<T> operation-counting wrapper"
```

---

### Task 3: Data generation (`datagen.hpp`)

**Files:**
- Create: `cpp_algo_lab/common/lab/datagen.hpp`
- Modify: `cpp_algo_lab/common/tests/test_common.cpp` (append)

**Interfaces:**
- Consumes: nothing.
- Produces (used by Tasks 5–9):
  - `enum class lab::Dist { random_uniform, sorted_asc, reversed, nearly_sorted, few_unique }`
  - `constexpr std::array<lab::Dist, 5> lab::all_dists()`
  - `std::string_view lab::dist_name(Dist)` — returns `"random"`, `"sorted"`, `"reversed"`, `"nearly_sorted"`, `"few_unique"`
  - `std::vector<int> lab::generate(Dist d, std::size_t n, std::uint32_t seed)` — values always in `[0, max(n,10))`, non-negative.

- [ ] **Step 1: Append failing tests**

Append to `cpp_algo_lab/common/tests/test_common.cpp`:

```cpp
#include "lab/datagen.hpp"

#include <set>

TEST_CASE("datagen: size, determinism, non-negative range") {
    for (lab::Dist d : lab::all_dists()) {
        CAPTURE(lab::dist_name(d));
        auto v1 = lab::generate(d, 1000, 42);
        auto v2 = lab::generate(d, 1000, 42);
        auto v3 = lab::generate(d, 1000, 43);
        CHECK(v1.size() == 1000);
        CHECK(v1 == v2);  // same seed -> same data
        if (d == lab::Dist::random_uniform) CHECK(v1 != v3);
        for (int x : v1) {
            CHECK(x >= 0);
            CHECK(x < 1000);
        }
        CHECK(lab::generate(d, 0, 42).empty());
    }
}

TEST_CASE("datagen: per-distribution shape") {
    auto sorted = lab::generate(lab::Dist::sorted_asc, 500, 1);
    CHECK(std::is_sorted(sorted.begin(), sorted.end()));

    auto rev = lab::generate(lab::Dist::reversed, 500, 1);
    CHECK(std::is_sorted(rev.rbegin(), rev.rend()));
    CHECK_FALSE(std::is_sorted(rev.begin(), rev.end()));

    auto few = lab::generate(lab::Dist::few_unique, 500, 1);
    std::set<int> uniq(few.begin(), few.end());
    CHECK(uniq.size() <= 10);

    auto nearly = lab::generate(lab::Dist::nearly_sorted, 500, 1);
    int in_order = 0;
    for (std::size_t i = 1; i < nearly.size(); ++i)
        if (nearly[i - 1] <= nearly[i]) ++in_order;
    CHECK(in_order >= 450);  // >= 90% adjacent pairs in order
    CHECK_FALSE(std::is_sorted(nearly.begin(), nearly.end()));
}
```

- [ ] **Step 2: Run to verify failure**

```bash
cd cpp_algo_lab && make test
```

Expected: FAIL — `lab/datagen.hpp: No such file or directory`.

- [ ] **Step 3: Implement `datagen.hpp`**

`cpp_algo_lab/common/lab/datagen.hpp`:

```cpp
#pragma once
// Deterministic input generators for benchmarks and tests.
// Values are always non-negative and < max(n, 10), so non-comparison sorts
// (counting/radix/bucket) are applicable to every distribution.
#include <algorithm>
#include <array>
#include <cstdint>
#include <numeric>
#include <random>
#include <string_view>
#include <vector>

namespace lab {

enum class Dist { random_uniform, sorted_asc, reversed, nearly_sorted, few_unique };

inline constexpr std::array<Dist, 5> all_dists() {
    return {Dist::random_uniform, Dist::sorted_asc, Dist::reversed, Dist::nearly_sorted,
            Dist::few_unique};
}

inline std::string_view dist_name(Dist d) {
    switch (d) {
        case Dist::random_uniform: return "random";
        case Dist::sorted_asc: return "sorted";
        case Dist::reversed: return "reversed";
        case Dist::nearly_sorted: return "nearly_sorted";
        case Dist::few_unique: return "few_unique";
    }
    return "unknown";
}

inline std::vector<int> generate(Dist d, std::size_t n, std::uint32_t seed) {
    std::vector<int> v(n);
    if (n == 0) return v;
    std::mt19937 rng(seed);
    const int hi = static_cast<int>(std::max<std::size_t>(n, 10)) - 1;
    switch (d) {
        case Dist::random_uniform: {
            std::uniform_int_distribution<int> u(0, hi);
            std::generate(v.begin(), v.end(), [&] { return u(rng); });
            break;
        }
        case Dist::sorted_asc:
            std::iota(v.begin(), v.end(), 0);
            break;
        case Dist::reversed:
            std::iota(v.begin(), v.end(), 0);
            std::reverse(v.begin(), v.end());
            break;
        case Dist::nearly_sorted: {
            std::iota(v.begin(), v.end(), 0);
            if (n >= 2) {
                const std::size_t k = std::max<std::size_t>(1, n / 100);
                std::uniform_int_distribution<std::size_t> pos(0, n - 2);
                for (std::size_t i = 0; i < k; ++i) {
                    const std::size_t p = pos(rng);
                    std::swap(v[p], v[p + 1]);
                }
            }
            break;
        }
        case Dist::few_unique: {
            std::uniform_int_distribution<int> u(0, 9);
            std::generate(v.begin(), v.end(), [&] { return u(rng); });
            break;
        }
    }
    return v;
}

}  // namespace lab
```

- [ ] **Step 4: Run tests**

```bash
cd cpp_algo_lab && make test
```

Expected: `Status: SUCCESS!`. Note: the `nearly_sorted` swap loop can revert a swap by hitting the same position twice; with n=500, k=5 the ≥90 %-in-order and not-fully-sorted checks hold for seed 1. If `CHECK_FALSE(is_sorted)` ever fails, change the test seed, not the generator.

- [ ] **Step 5: Commit**

```bash
git add cpp_algo_lab/common
git commit -m "feat(cpp_algo_lab): add deterministic input distribution generators"
```

---

### Task 4: Timing, CSV, table, stability probe

**Files:**
- Create: `cpp_algo_lab/common/lab/timer.hpp`
- Create: `cpp_algo_lab/common/lab/csv.hpp`
- Create: `cpp_algo_lab/common/lab/table.hpp`
- Create: `cpp_algo_lab/common/lab/stability.hpp`
- Modify: `cpp_algo_lab/common/tests/test_common.cpp` (append)

**Interfaces:**
- Consumes: `lab::generate`, `lab::Dist` (Task 3).
- Produces (used by Tasks 5–9):
  - `template <class F> double lab::time_ms(F&& f)` — wall-clock milliseconds of one call.
  - `double lab::median(std::vector<double> v)` — throws `std::invalid_argument` on empty.
  - `class lab::CsvWriter { CsvWriter(const std::filesystem::path&, const std::vector<std::string>& header); void write_row(const std::vector<std::string>&); }` — creates parent dirs, writes header on construction.
  - `template <class T> std::string lab::cell(const T&)` — value → CSV cell string (8 significant digits for floating point).
  - `void lab::print_table(const std::vector<std::string>& header, const std::vector<std::vector<std::string>>& rows, std::ostream& os = std::cout)`.
  - `struct lab::KeyIdx { int key; int idx; }` with `operator<` / `operator==` comparing **key only**; `struct lab::KeyIdxKey` (key extractor returning `std::uint64_t`); `template <class SortFn> bool lab::observed_stable(SortFn fn, std::size_t n = 4096, std::uint32_t seed = 7)` where `fn` takes `std::vector<lab::KeyIdx>&`.

- [ ] **Step 1: Append failing tests**

Append to `cpp_algo_lab/common/tests/test_common.cpp`:

```cpp
#include "lab/csv.hpp"
#include "lab/stability.hpp"
#include "lab/table.hpp"
#include "lab/timer.hpp"

#include <filesystem>
#include <fstream>
#include <sstream>

TEST_CASE("timer: median") {
    CHECK(lab::median({3.0, 1.0, 2.0}) == 2.0);
    CHECK(lab::median({4.0, 1.0, 3.0, 2.0}) == 2.5);
    CHECK_THROWS_AS(lab::median({}), std::invalid_argument);
    volatile long sink = 0;
    const double ms = lab::time_ms([&] {
        for (long i = 0; i < 100000; ++i) sink = sink + i;
    });
    CHECK(ms >= 0.0);
}

TEST_CASE("csv: writes header and rows, creates parent dirs") {
    namespace fs = std::filesystem;
    const fs::path p = fs::temp_directory_path() / "cpp_algo_lab_test" / "out.csv";
    fs::remove_all(p.parent_path());
    {
        lab::CsvWriter w(p, {"algo", "n", "ms"});
        w.write_row({"bubble", lab::cell(256), lab::cell(1.5)});
    }
    std::ifstream in(p);
    std::string l1, l2;
    std::getline(in, l1);
    std::getline(in, l2);
    CHECK(l1 == "algo,n,ms");
    CHECK(l2 == "bubble,256,1.5");
    fs::remove_all(p.parent_path());
}

TEST_CASE("table: aligned output") {
    std::ostringstream os;
    lab::print_table({"algo", "ms"}, {{"bubble", "12.5"}, {"quick", "0.8"}}, os);
    const std::string s = os.str();
    CHECK(s.find("algo") != std::string::npos);
    CHECK(s.find("bubble") != std::string::npos);
    // header separator present
    CHECK(s.find("---") != std::string::npos);
}

TEST_CASE("stability probe: detects stable and unstable sorts") {
    // std::stable_sort must be observed stable.
    CHECK(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { std::stable_sort(v.begin(), v.end()); }));
    // A deliberately tie-reversing sort must be observed unstable.
    CHECK_FALSE(lab::observed_stable([](std::vector<lab::KeyIdx>& v) {
        std::sort(v.begin(), v.end(), [](const lab::KeyIdx& a, const lab::KeyIdx& b) {
            if (a.key != b.key) return a.key < b.key;
            return a.idx > b.idx;  // reverse ties
        });
    }));
}
```

- [ ] **Step 2: Run to verify failure**

```bash
cd cpp_algo_lab && make test
```

Expected: FAIL — missing headers.

- [ ] **Step 3: Implement the four headers**

`cpp_algo_lab/common/lab/timer.hpp`:

```cpp
#pragma once
// Wall-clock timing helpers. Benchmarks take the median of repeated runs to
// damp WSL2 scheduling noise.
#include <algorithm>
#include <chrono>
#include <stdexcept>
#include <utility>
#include <vector>

namespace lab {

template <class F>
double time_ms(F&& f) {
    const auto t0 = std::chrono::steady_clock::now();
    std::forward<F>(f)();
    const auto t1 = std::chrono::steady_clock::now();
    return std::chrono::duration<double, std::milli>(t1 - t0).count();
}

inline double median(std::vector<double> v) {
    if (v.empty()) throw std::invalid_argument("median: empty input");
    std::sort(v.begin(), v.end());
    const std::size_t m = v.size() / 2;
    if (v.size() % 2 == 1) return v[m];
    return (v[m - 1] + v[m]) / 2.0;
}

}  // namespace lab
```

`cpp_algo_lab/common/lab/csv.hpp`:

```cpp
#pragma once
// Minimal CSV output. Cells never contain commas/quotes in this project,
// so no quoting/escaping is implemented.
#include <filesystem>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace lab {

template <class T>
std::string cell(const T& v) {
    std::ostringstream os;
    os.precision(8);
    os << v;
    return os.str();
}

class CsvWriter {
public:
    CsvWriter(const std::filesystem::path& file, const std::vector<std::string>& header) {
        if (file.has_parent_path()) std::filesystem::create_directories(file.parent_path());
        out_.open(file);
        if (!out_) throw std::runtime_error("CsvWriter: cannot open " + file.string());
        write_row(header);
    }

    void write_row(const std::vector<std::string>& cells) {
        for (std::size_t i = 0; i < cells.size(); ++i) {
            if (i) out_ << ',';
            out_ << cells[i];
        }
        out_ << '\n';
    }

private:
    std::ofstream out_;
};

}  // namespace lab
```

`cpp_algo_lab/common/lab/table.hpp`:

```cpp
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
```

`cpp_algo_lab/common/lab/stability.hpp`:

```cpp
#pragma once
// Stability probe: sort (key, original index) records where ordering sees the
// key only; a sort is observed stable iff every equal-key run keeps ascending
// original indices.
#include <cstdint>
#include <stdexcept>
#include <vector>

#include "lab/datagen.hpp"

namespace lab {

struct KeyIdx {
    int key = 0;
    int idx = 0;
    friend bool operator<(const KeyIdx& a, const KeyIdx& b) { return a.key < b.key; }
    friend bool operator==(const KeyIdx& a, const KeyIdx& b) { return a.key == b.key; }
};

struct KeyIdxKey {
    std::uint64_t operator()(const KeyIdx& e) const {
        if (e.key < 0) throw std::invalid_argument("KeyIdxKey: negative key");
        return static_cast<std::uint64_t>(e.key);
    }
};

// fn: void(std::vector<KeyIdx>&) — must sort by key.
template <class SortFn>
bool observed_stable(SortFn fn, std::size_t n = 4096, std::uint32_t seed = 7) {
    const auto keys = generate(Dist::few_unique, n, seed);
    std::vector<KeyIdx> v(n);
    for (std::size_t i = 0; i < n; ++i) v[i] = KeyIdx{keys[i], static_cast<int>(i)};
    fn(v);
    for (std::size_t i = 1; i < n; ++i) {
        if (v[i - 1].key > v[i].key) return false;  // not even sorted
        if (v[i - 1].key == v[i].key && v[i - 1].idx > v[i].idx) return false;
    }
    return true;
}

}  // namespace lab
```

- [ ] **Step 4: Run tests**

```bash
cd cpp_algo_lab && make test
```

Expected: `Status: SUCCESS!`.

- [ ] **Step 5: Commit**

```bash
git add cpp_algo_lab/common
git commit -m "feat(cpp_algo_lab): add timer, csv writer, ascii table, stability probe"
```

---

### Task 5: Quadratic sorts — bubble, insertion, selection

**Files:**
- Create: `cpp_algo_lab/sorting/include/sorting/bubble.hpp`
- Create: `cpp_algo_lab/sorting/include/sorting/insertion.hpp`
- Create: `cpp_algo_lab/sorting/include/sorting/selection.hpp`
- Create: `cpp_algo_lab/sorting/tests/test_sorting.cpp`
- Modify: `cpp_algo_lab/Makefile` (extend `test` target)

**Interfaces:**
- Consumes: `lab::generate`, `lab::all_dists` (Task 3), `lab::Counted` (Task 2), `lab::observed_stable`, `lab::KeyIdx` (Task 4).
- Produces (used by Tasks 8–9): `lab::bubble_sort`, `lab::insertion_sort`, `lab::selection_sort` — all `template <class RandomIt, class Compare = std::less<>> void X_sort(RandomIt first, RandomIt last, Compare comp = {})`. Also the shared test helper `check_sorts_like_std` in `test_sorting.cpp` (Tasks 6–7 append to this file).

- [ ] **Step 1: Write failing tests (new test binary)**

`cpp_algo_lab/sorting/tests/test_sorting.cpp`:

```cpp
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest/doctest.h"

#include <algorithm>
#include <functional>
#include <vector>

#include "lab/counted.hpp"
#include "lab/datagen.hpp"
#include "lab/stability.hpp"
#include "sorting/bubble.hpp"
#include "sorting/insertion.hpp"
#include "sorting/selection.hpp"

// Generic conformance check: sorter(begin, end) must produce exactly what
// std::sort produces, across sizes, seeds and distributions.
template <class Sorter>
void check_sorts_like_std(Sorter sorter) {
    for (const std::size_t n : {0u, 1u, 2u, 3u, 16u, 1000u}) {
        for (const std::uint32_t seed : {1u, 2u}) {
            for (const lab::Dist d : lab::all_dists()) {
                CAPTURE(n);
                CAPTURE(seed);
                CAPTURE(lab::dist_name(d));
                auto v = lab::generate(d, n, seed);
                auto expected = v;
                std::sort(expected.begin(), expected.end());
                sorter(v.begin(), v.end());
                CHECK(v == expected);
            }
        }
    }
}

// Descending order via custom comparator.
template <class Sorter>
void check_custom_compare(Sorter sorter_desc) {
    auto v = lab::generate(lab::Dist::random_uniform, 1000, 3);
    auto expected = v;
    std::sort(expected.begin(), expected.end(), std::greater<>{});
    sorter_desc(v.begin(), v.end());
    CHECK(v == expected);
}

TEST_CASE("bubble_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::bubble_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::bubble_sort(f, l, std::greater<>{}); });
    CHECK(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::bubble_sort(v.begin(), v.end()); }));
}

TEST_CASE("bubble_sort: early exit on sorted input") {
    using C = lab::Counted<int>;
    std::vector<C> v;
    for (int i = 0; i < 100; ++i) v.emplace_back(i);
    C::reset_counters();
    lab::bubble_sort(v.begin(), v.end());
    CHECK(C::counters().comparisons == 99);  // one clean pass, then stop
    CHECK(C::counters().swaps == 0);
}

TEST_CASE("insertion_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::insertion_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::insertion_sort(f, l, std::greater<>{}); });
    CHECK(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::insertion_sort(v.begin(), v.end()); }));
}

TEST_CASE("insertion_sort: exact counts on sorted input") {
    using C = lab::Counted<int>;
    std::vector<C> v;
    for (int i = 0; i < 100; ++i) v.emplace_back(i);
    C::reset_counters();
    lab::insertion_sort(v.begin(), v.end());
    // Per element after the first: 1 failed comparison, key move out + move back.
    CHECK(C::counters().comparisons == 99);
    CHECK(C::counters().moves == 198);
    CHECK(C::counters().swaps == 0);
}

TEST_CASE("selection_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::selection_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::selection_sort(f, l, std::greater<>{}); });
    // Long-range swaps break ties: observed unstable on this probe input.
    CHECK_FALSE(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::selection_sort(v.begin(), v.end()); }));
}
```

Note: the `CHECK_FALSE(observed_stable(...))` assertions are deterministic (fixed probe seed). If an implementation change ever makes one accidentally hold order, adjust the probe seed in the test, not the implementation.

- [ ] **Step 2: Extend Makefile `test` target**

In `cpp_algo_lab/Makefile` replace the `test:` rule with:

```make
test: $(BUILD)/test_common $(BUILD)/test_sorting
	$(BUILD)/test_common
	$(BUILD)/test_sorting
```

- [ ] **Step 3: Run to verify failure**

```bash
cd cpp_algo_lab && make test
```

Expected: FAIL — `sorting/bubble.hpp: No such file or directory`.

- [ ] **Step 4: Implement the three headers**

`cpp_algo_lab/sorting/include/sorting/bubble.hpp`:

```cpp
#pragma once
// Bubble sort with early exit: O(n^2) compares/swaps, O(n) best case (sorted),
// stable. Adjacent swaps only — the "swaps" counter is the story here.
#include <algorithm>
#include <functional>

namespace lab {

template <class RandomIt, class Compare = std::less<>>
void bubble_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    if (last - first < 2) return;
    for (auto end = last; end - first > 1; --end) {
        bool swapped = false;
        for (auto it = first; it + 1 != end; ++it) {
            if (comp(*(it + 1), *it)) {
                std::iter_swap(it, it + 1);
                swapped = true;
            }
        }
        if (!swapped) return;  // clean pass: already sorted
    }
}

}  // namespace lab
```

`cpp_algo_lab/sorting/include/sorting/insertion.hpp`:

```cpp
#pragma once
// Insertion sort, shift-based (moves, not swaps): O(n^2) worst, O(n + inversions)
// adaptive, stable. The fastest of the quadratic family on nearly-sorted input.
#include <functional>
#include <utility>

namespace lab {

template <class RandomIt, class Compare = std::less<>>
void insertion_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    if (last - first < 2) return;
    for (auto it = first + 1; it != last; ++it) {
        auto key = std::move(*it);  // lift the element out, shift the hole left
        auto hole = it;
        while (hole != first && comp(key, *(hole - 1))) {
            *hole = std::move(*(hole - 1));
            --hole;
        }
        *hole = std::move(key);
    }
}

}  // namespace lab
```

`cpp_algo_lab/sorting/include/sorting/selection.hpp`:

```cpp
#pragma once
// Selection sort: always ~n^2/2 comparisons but only O(n) swaps — the mirror
// image of bubble sort's cost profile. Not stable (long-range swaps).
#include <algorithm>
#include <functional>

namespace lab {

template <class RandomIt, class Compare = std::less<>>
void selection_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    if (last - first < 2) return;
    for (auto it = first; it + 1 != last; ++it) {
        auto min_it = it;
        for (auto j = it + 1; j != last; ++j)
            if (comp(*j, *min_it)) min_it = j;
        if (min_it != it) std::iter_swap(it, min_it);
    }
}

}  // namespace lab
```

- [ ] **Step 5: Run tests**

```bash
cd cpp_algo_lab && make test
```

Expected: both binaries `Status: SUCCESS!`.

- [ ] **Step 6: Commit**

```bash
git add cpp_algo_lab/sorting cpp_algo_lab/Makefile
git commit -m "feat(cpp_algo_lab): add bubble, insertion, selection sorts with tests"
```

---

### Task 6: O(n log n) sorts — merge, quick, heap

**Files:**
- Create: `cpp_algo_lab/sorting/include/sorting/merge.hpp`
- Create: `cpp_algo_lab/sorting/include/sorting/quick.hpp`
- Create: `cpp_algo_lab/sorting/include/sorting/heap.hpp`
- Modify: `cpp_algo_lab/sorting/tests/test_sorting.cpp` (append)

**Interfaces:**
- Consumes: test helpers from Task 5 (`check_sorts_like_std`, `check_custom_compare`).
- Produces (used by Tasks 8–9): `lab::merge_sort` (stable), `lab::quick_sort` (median-of-three + Hoare partition + smaller-side recursion), `lab::heap_sort` (hand-written sift-down) — same STL-style signature as Task 5.

- [ ] **Step 1: Append failing tests**

Append to `cpp_algo_lab/sorting/tests/test_sorting.cpp`:

```cpp
#include "sorting/heap.hpp"
#include "sorting/merge.hpp"
#include "sorting/quick.hpp"

TEST_CASE("merge_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::merge_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::merge_sort(f, l, std::greater<>{}); });
    CHECK(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::merge_sort(v.begin(), v.end()); }));
}

TEST_CASE("quick_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::quick_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::quick_sort(f, l, std::greater<>{}); });
    CHECK_FALSE(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::quick_sort(v.begin(), v.end()); }));
}

TEST_CASE("quick_sort: adversarial inputs stay fast and correct") {
    // sorted / reversed / all-equal, n = 20000. With median-of-three and
    // smaller-side-first recursion this must finish quickly (no O(n^2) blowup,
    // no deep stack). The sanitizer build would catch stack overflow.
    for (const lab::Dist d : {lab::Dist::sorted_asc, lab::Dist::reversed}) {
        auto v = lab::generate(d, 20000, 1);
        auto expected = v;
        std::sort(expected.begin(), expected.end());
        lab::quick_sort(v.begin(), v.end());
        CHECK(v == expected);
    }
    std::vector<int> eq(20000, 7);
    auto v = eq;
    lab::quick_sort(v.begin(), v.end());
    CHECK(v == eq);
}

TEST_CASE("heap_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::heap_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::heap_sort(f, l, std::greater<>{}); });
    CHECK_FALSE(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::heap_sort(v.begin(), v.end()); }));
}
```

- [ ] **Step 2: Run to verify failure**

```bash
cd cpp_algo_lab && make test
```

Expected: FAIL — `sorting/merge.hpp: No such file or directory`.

- [ ] **Step 3: Implement the three headers**

`cpp_algo_lab/sorting/include/sorting/merge.hpp`:

```cpp
#pragma once
// Top-down merge sort with one reusable buffer: O(n log n) always, O(n) extra
// space, stable (ties take the left run first).
#include <functional>
#include <iterator>
#include <utility>
#include <vector>

namespace lab {
namespace detail {

template <class RandomIt, class Buf, class Compare>
void merge_sort_impl(RandomIt first, RandomIt last, Buf& buf, Compare comp) {
    const auto n = last - first;
    if (n < 2) return;
    const auto mid = first + n / 2;
    merge_sort_impl(first, mid, buf, comp);
    merge_sort_impl(mid, last, buf, comp);

    buf.clear();
    auto l = first, r = mid;
    while (l != mid && r != last) {
        // Strictly-less from the right run keeps equal elements stable.
        if (comp(*r, *l)) {
            buf.push_back(std::move(*r));
            ++r;
        } else {
            buf.push_back(std::move(*l));
            ++l;
        }
    }
    for (; l != mid; ++l) buf.push_back(std::move(*l));
    for (; r != last; ++r) buf.push_back(std::move(*r));
    std::move(buf.begin(), buf.end(), first);
}

}  // namespace detail

template <class RandomIt, class Compare = std::less<>>
void merge_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    using T = typename std::iterator_traits<RandomIt>::value_type;
    std::vector<T> buf;
    buf.reserve(static_cast<std::size_t>(last - first));
    detail::merge_sort_impl(first, last, buf, comp);
}

}  // namespace lab
```

`cpp_algo_lab/sorting/include/sorting/quick.hpp`:

```cpp
#pragma once
// Quicksort: median-of-three pivot + Hoare-style partition (Sedgewick's
// variant: the pivot is swapped to the front, the scans exclude it, and it
// lands in its final slot). Recursing into the smaller side first keeps the
// stack depth O(log n). Average O(n log n); median-of-three defuses
// sorted/reversed inputs, and excluding the pivot from both partitions
// guarantees progress even on all-equal input.
#include <algorithm>
#include <functional>

namespace lab {
namespace detail {

template <class RandomIt, class Compare>
RandomIt median_of_three(RandomIt a, RandomIt b, RandomIt c, Compare comp) {
    if (comp(*b, *a)) {
        if (comp(*c, *b)) return b;
        return comp(*c, *a) ? c : a;
    }
    if (comp(*c, *a)) return a;
    return comp(*c, *b) ? c : b;
}

// Partition [first, last): returns p with *p in its final position,
// [first, p) <= pivot and (p, last) >= pivot.
template <class RandomIt, class Compare>
RandomIt hoare_partition(RandomIt first, RandomIt last, Compare comp) {
    const auto mid = first + (last - first) / 2;
    std::iter_swap(first, median_of_three(first, mid, last - 1, comp));
    const auto pivot = *first;  // copy: element positions move during the scans
    auto i = first;
    auto j = last;
    while (true) {
        do {
            ++i;
        } while (i != last && comp(*i, pivot));
        do {
            --j;
        } while (comp(pivot, *j));  // stops at first: *first == pivot
        if (i >= j) break;
        std::iter_swap(i, j);
    }
    std::iter_swap(first, j);  // pivot into its final slot
    return j;
}

template <class RandomIt, class Compare>
void quick_sort_impl(RandomIt first, RandomIt last, Compare comp) {
    while (last - first > 1) {
        const auto p = hoare_partition(first, last, comp);
        // Recurse into the smaller half, loop on the larger one. The pivot
        // at p is excluded from both, so each step strictly shrinks.
        if (p - first < last - (p + 1)) {
            quick_sort_impl(first, p, comp);
            first = p + 1;
        } else {
            quick_sort_impl(p + 1, last, comp);
            last = p;
        }
    }
}

}  // namespace detail

template <class RandomIt, class Compare = std::less<>>
void quick_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    detail::quick_sort_impl(first, last, comp);
}

}  // namespace lab
```

Note (2026-07-14, during execution): the original plan version of `hoare_partition`
(while-form scans, partition split at `p + 1`) could return `p = last - 1` when the
pivot was the maximum (e.g. n=2 sorted input), so `last = p + 1` made no progress —
an infinite loop found by the Task 6 implementer. Replaced with the pivot-to-front
variant above; fix commit `e2a5d54`.

`cpp_algo_lab/sorting/include/sorting/heap.hpp`:

```cpp
#pragma once
// Heap sort with a hand-written sift-down: O(n log n) worst case, in-place,
// not stable. Build max-heap bottom-up (O(n)), then pop the max n times.
#include <algorithm>
#include <cstddef>
#include <functional>

namespace lab {
namespace detail {

template <class RandomIt, class Compare>
void sift_down(RandomIt first, std::size_t size, std::size_t root, Compare comp) {
    while (true) {
        std::size_t child = 2 * root + 1;
        if (child >= size) return;
        if (child + 1 < size && comp(first[child], first[child + 1])) ++child;
        if (!comp(first[root], first[child])) return;
        std::iter_swap(first + root, first + child);
        root = child;
    }
}

}  // namespace detail

template <class RandomIt, class Compare = std::less<>>
void heap_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    const auto n = static_cast<std::size_t>(last - first);
    if (n < 2) return;
    for (std::size_t i = n / 2; i-- > 0;) detail::sift_down(first, n, i, comp);
    for (std::size_t s = n - 1; s > 0; --s) {
        std::iter_swap(first, first + s);  // move current max to its final slot
        detail::sift_down(first, s, 0, comp);
    }
}

}  // namespace lab
```

- [ ] **Step 4: Run tests**

```bash
cd cpp_algo_lab && make test
```

Expected: `Status: SUCCESS!`.

- [ ] **Step 5: Commit**

```bash
git add cpp_algo_lab/sorting
git commit -m "feat(cpp_algo_lab): add merge, quick, heap sorts with adversarial tests"
```

---

### Task 7: Shell sort + non-comparison sorts (counting, radix, bucket) + `all.hpp`

**Files:**
- Create: `cpp_algo_lab/sorting/include/sorting/shell.hpp`
- Create: `cpp_algo_lab/sorting/include/sorting/keys.hpp`
- Create: `cpp_algo_lab/sorting/include/sorting/counting.hpp`
- Create: `cpp_algo_lab/sorting/include/sorting/radix.hpp`
- Create: `cpp_algo_lab/sorting/include/sorting/bucket.hpp`
- Create: `cpp_algo_lab/sorting/include/sorting/all.hpp`
- Modify: `cpp_algo_lab/sorting/tests/test_sorting.cpp` (append)

**Interfaces:**
- Consumes: `lab::insertion_sort` (Task 5, reused inside bucket sort), test helpers (Task 5).
- Produces (used by Tasks 8–9):
  - `lab::shell_sort` — STL-style signature (Ciura gap sequence).
  - `struct lab::IntegralKey` in `keys.hpp` — `template <class T> std::uint64_t operator()(const T&) const`; throws `std::invalid_argument` on negative values; `static_assert`s integral `T`.
  - `inline constexpr std::uint64_t lab::kMaxCountingRange = 1ull << 26;`
  - `template <class RandomIt, class KeyFn = lab::IntegralKey> void lab::counting_sort(RandomIt, RandomIt, KeyFn = {})` — stable; throws `std::length_error` if `max_key + 1 > kMaxCountingRange`.
  - Same signature: `lab::radix_sort` (LSD base-256, writes back into the range after every byte pass — trace-friendly), `lab::bucket_sort` (n buckets, per-bucket `insertion_sort`).
  - `sorting/all.hpp` — includes all 10 algorithm headers + `keys.hpp`.

- [ ] **Step 1: Append failing tests**

Append to `cpp_algo_lab/sorting/tests/test_sorting.cpp`:

```cpp
#include "sorting/all.hpp"

TEST_CASE("shell_sort") {
    check_sorts_like_std([](auto f, auto l) { lab::shell_sort(f, l); });
    check_custom_compare([](auto f, auto l) { lab::shell_sort(f, l, std::greater<>{}); });
    CHECK_FALSE(lab::observed_stable(
        [](std::vector<lab::KeyIdx>& v) { lab::shell_sort(v.begin(), v.end()); }));
}

TEST_CASE("counting_sort / radix_sort / bucket_sort: sort like std::sort") {
    check_sorts_like_std([](auto f, auto l) { lab::counting_sort(f, l); });
    check_sorts_like_std([](auto f, auto l) { lab::radix_sort(f, l); });
    check_sorts_like_std([](auto f, auto l) { lab::bucket_sort(f, l); });
}

TEST_CASE("non-comparison sorts: stability via KeyFn") {
    auto by_key = lab::KeyIdxKey{};
    CHECK(lab::observed_stable([&](std::vector<lab::KeyIdx>& v) {
        lab::counting_sort(v.begin(), v.end(), by_key);
    }));
    CHECK(lab::observed_stable([&](std::vector<lab::KeyIdx>& v) {
        lab::radix_sort(v.begin(), v.end(), by_key);
    }));
    CHECK(lab::observed_stable([&](std::vector<lab::KeyIdx>& v) {
        lab::bucket_sort(v.begin(), v.end(), by_key);
    }));
}

TEST_CASE("non-comparison sorts: negative keys are rejected") {
    std::vector<int> v{3, -1, 2};
    CHECK_THROWS_AS(lab::counting_sort(v.begin(), v.end()), std::invalid_argument);
    CHECK_THROWS_AS(lab::radix_sort(v.begin(), v.end()), std::invalid_argument);
    CHECK_THROWS_AS(lab::bucket_sort(v.begin(), v.end()), std::invalid_argument);
}

TEST_CASE("counting_sort: oversized key range is rejected") {
    std::vector<int> v{0, 1 << 26};  // max_key + 1 exceeds kMaxCountingRange
    CHECK_THROWS_AS(lab::counting_sort(v.begin(), v.end()), std::length_error);
    // radix has no such limit: same data must sort fine.
    lab::radix_sort(v.begin(), v.end());
    CHECK(v[0] == 0);
    CHECK(v[1] == (1 << 26));
}
```

- [ ] **Step 2: Run to verify failure**

```bash
cd cpp_algo_lab && make test
```

Expected: FAIL — `sorting/all.hpp: No such file or directory`.

- [ ] **Step 3: Implement the five headers + all.hpp**

`cpp_algo_lab/sorting/include/sorting/keys.hpp`:

```cpp
#pragma once
// Key extraction for non-comparison sorts (counting/radix/bucket).
// The default IntegralKey maps a non-negative integral element to uint64_t;
// pass a custom KeyFn (e.g. lab::KeyIdxKey, or a lambda over Counted<int>)
// to sort other element types by an integer key.
#include <cstdint>
#include <stdexcept>
#include <type_traits>

namespace lab {

struct IntegralKey {
    template <class T>
    std::uint64_t operator()(const T& v) const {
        static_assert(std::is_integral_v<T>,
                      "IntegralKey requires an integral element type; pass a custom KeyFn");
        if (v < 0) throw std::invalid_argument("non-comparison sort: negative key");
        return static_cast<std::uint64_t>(v);
    }
};

}  // namespace lab
```

`cpp_algo_lab/sorting/include/sorting/shell.hpp`:

```cpp
#pragma once
// Shell sort with the Ciura gap sequence (extended by x2.25): gapped insertion
// sort, subquadratic in practice (~n^1.3), not stable. The bridge between the
// quadratic family and the O(n log n) family.
#include <functional>
#include <iterator>
#include <utility>
#include <vector>

namespace lab {

template <class RandomIt, class Compare = std::less<>>
void shell_sort(RandomIt first, RandomIt last, Compare comp = {}) {
    using diff_t = typename std::iterator_traits<RandomIt>::difference_type;
    const diff_t n = last - first;
    if (n < 2) return;
    // Ciura (2001) empirically best-known prefix, then *2.25.
    std::vector<diff_t> gaps{1, 4, 10, 23, 57, 132, 301, 701, 1750};
    while (gaps.back() < n / 2) gaps.push_back(gaps.back() * 9 / 4);
    for (auto g = gaps.rbegin(); g != gaps.rend(); ++g) {
        const diff_t gap = *g;
        if (gap >= n) continue;
        for (auto it = first + gap; it != last; ++it) {
            auto key = std::move(*it);
            auto hole = it;
            while (hole - first >= gap && comp(key, *(hole - gap))) {
                *hole = std::move(*(hole - gap));
                hole -= gap;
            }
            *hole = std::move(key);
        }
    }
}

}  // namespace lab
```

`cpp_algo_lab/sorting/include/sorting/counting.hpp`:

```cpp
#pragma once
// Counting sort: O(n + k) where k = key range. No comparisons at all — the
// histogram + exclusive prefix sum + forward scatter make it stable. Only
// viable while k stays small; kMaxCountingRange guards the histogram size.
#include <algorithm>
#include <cstdint>
#include <iterator>
#include <stdexcept>
#include <utility>
#include <vector>

#include "sorting/keys.hpp"

namespace lab {

inline constexpr std::uint64_t kMaxCountingRange = std::uint64_t{1} << 26;  // 64M counters

template <class RandomIt, class KeyFn = IntegralKey>
void counting_sort(RandomIt first, RandomIt last, KeyFn key = {}) {
    const auto n = static_cast<std::size_t>(last - first);
    if (n < 2) return;
    std::uint64_t max_key = 0;
    for (auto it = first; it != last; ++it) max_key = std::max(max_key, key(*it));
    if (max_key + 1 > kMaxCountingRange)
        throw std::length_error("counting_sort: key range too large");

    std::vector<std::size_t> count(static_cast<std::size_t>(max_key) + 1, 0);
    for (auto it = first; it != last; ++it) ++count[key(*it)];
    std::size_t sum = 0;  // exclusive prefix sum -> stable scatter positions
    for (auto& c : count) {
        const std::size_t old = c;
        c = sum;
        sum += old;
    }
    using T = typename std::iterator_traits<RandomIt>::value_type;
    std::vector<T> out(n);
    for (auto it = first; it != last; ++it) out[count[key(*it)]++] = std::move(*it);
    std::move(out.begin(), out.end(), first);
}

}  // namespace lab
```

`cpp_algo_lab/sorting/include/sorting/radix.hpp`:

```cpp
#pragma once
// LSD radix sort, base 256: O(passes * n) with passes = significant bytes of
// the max key. Stable (each pass is a stable counting sort by one byte).
// Writes back into the range after every pass so traces show the progress.
#include <algorithm>
#include <cstdint>
#include <iterator>
#include <utility>
#include <vector>

#include "sorting/keys.hpp"

namespace lab {

template <class RandomIt, class KeyFn = IntegralKey>
void radix_sort(RandomIt first, RandomIt last, KeyFn key = {}) {
    const auto n = static_cast<std::size_t>(last - first);
    if (n < 2) return;
    std::uint64_t max_key = 0;
    for (auto it = first; it != last; ++it) max_key = std::max(max_key, key(*it));

    using T = typename std::iterator_traits<RandomIt>::value_type;
    std::vector<T> out(n);
    for (int shift = 0; shift == 0 || (shift < 64 && (max_key >> shift) != 0); shift += 8) {
        std::size_t count[257] = {};  // count[b+1] trick -> exclusive prefix in place
        for (auto it = first; it != last; ++it)
            ++count[((key(*it) >> shift) & 0xFF) + 1];
        for (int b = 0; b < 256; ++b) count[b + 1] += count[b];
        for (auto it = first; it != last; ++it)
            out[count[(key(*it) >> shift) & 0xFF]++] = std::move(*it);
        std::move(out.begin(), out.end(), first);
    }
}

}  // namespace lab
```

`cpp_algo_lab/sorting/include/sorting/bucket.hpp`:

```cpp
#pragma once
// Bucket sort: distribute into n buckets by scaled key, insertion-sort each
// bucket, concatenate. O(n) expected on uniform keys; degrades toward
// insertion sort when keys clump into few buckets. Stable as long as
// operator< is consistent with the key.
#include <algorithm>
#include <cstdint>
#include <iterator>
#include <utility>
#include <vector>

#include "sorting/insertion.hpp"
#include "sorting/keys.hpp"

namespace lab {

template <class RandomIt, class KeyFn = IntegralKey>
void bucket_sort(RandomIt first, RandomIt last, KeyFn key = {}) {
    const auto n = static_cast<std::size_t>(last - first);
    if (n < 2) return;
    std::uint64_t max_key = 0;
    for (auto it = first; it != last; ++it) max_key = std::max(max_key, key(*it));

    using T = typename std::iterator_traits<RandomIt>::value_type;
    std::vector<std::vector<T>> buckets(n);
    const long double scale =
        static_cast<long double>(n) / (static_cast<long double>(max_key) + 1.0L);
    for (auto it = first; it != last; ++it) {
        const auto b = static_cast<std::size_t>(static_cast<long double>(key(*it)) * scale);
        buckets[b].push_back(std::move(*it));
    }
    auto out = first;
    for (auto& b : buckets) {
        insertion_sort(b.begin(), b.end());
        out = std::move(b.begin(), b.end(), out);
    }
}

}  // namespace lab
```

`cpp_algo_lab/sorting/include/sorting/all.hpp`:

```cpp
#pragma once
// Convenience umbrella header: all 10 sorting algorithms + key extraction.
#include "sorting/bubble.hpp"
#include "sorting/bucket.hpp"
#include "sorting/counting.hpp"
#include "sorting/heap.hpp"
#include "sorting/insertion.hpp"
#include "sorting/keys.hpp"
#include "sorting/merge.hpp"
#include "sorting/quick.hpp"
#include "sorting/radix.hpp"
#include "sorting/selection.hpp"
#include "sorting/shell.hpp"
```

- [ ] **Step 4: Run tests**

```bash
cd cpp_algo_lab && make test
```

Expected: `Status: SUCCESS!`. Note the oversized-range test allocates a 64M-entry histogram guard check only (no allocation happens — the throw fires first); the radix path sorts 2 elements.

Note (2026-07-14, during execution): the original plan version of the radix pass
loop lacked the `shift < 64` guard, so `max_key >= 2^56` evaluated `max_key >> 64`
(undefined behavior). Found in task review; fixed with the guard above plus a
regression test (`radix_sort: keys above 2^56 terminate without UB`) in commit
`5a8710a`.

- [ ] **Step 5: Commit**

```bash
git add cpp_algo_lab/sorting
git commit -m "feat(cpp_algo_lab): add shell, counting, radix, bucket sorts and umbrella header"
```

---

### Task 8: Benchmark executable — times, operation counts, properties

**Files:**
- Create: `cpp_algo_lab/sorting/bench/bench_sorting.cpp`

**Interfaces:**
- Consumes: everything from Tasks 2–7 (`sorting/all.hpp`, `lab/counted.hpp`, `lab/datagen.hpp`, `lab/timer.hpp`, `lab/csv.hpp`, `lab/table.hpp`, `lab/stability.hpp`).
- Produces (consumed by Task 10's plot script — column names are load-bearing):
  - `results/sorting_times.csv` — header `algo,family,dist,n,repeats,median_ms`
  - `results/sorting_ops.csv` — header `algo,family,dist,n,comparisons,moves,swaps`
  - `results/sorting_props.csv` — header `algo,family,comparison_based,stable_observed,n_cap`
  - Algo names: `bubble insertion selection shell merge quick heap std_sort std_stable_sort counting radix bucket`; families exactly `n2 | nlogn | linear` (per Fixed design values).
  - CLI: no args = full bench; `--quick` = reduced sweep. (`--trace` is added in Task 9.)

- [ ] **Step 1: Write the benchmark**

`cpp_algo_lab/sorting/bench/bench_sorting.cpp`:

```cpp
// Sorting benchmark: wall-clock times (plain int), operation counts
// (Counted<int>), and observed properties (stability probe) -> results/*.csv.
// Run from cpp_algo_lab/ (paths are relative). Full run takes a few minutes,
// dominated by the quadratic sorts at n=32768.
#include <algorithm>
#include <cstring>
#include <functional>
#include <iostream>
#include <string>
#include <vector>

#include "lab/counted.hpp"
#include "lab/csv.hpp"
#include "lab/datagen.hpp"
#include "lab/stability.hpp"
#include "lab/table.hpp"
#include "lab/timer.hpp"
#include "sorting/all.hpp"

namespace {

using IntVec = std::vector<int>;
using CountedVec = std::vector<lab::Counted<int>>;
using KeyIdxVec = std::vector<lab::KeyIdx>;

struct AlgoSpec {
    std::string name;
    std::string family;  // "n2" | "nlogn" | "linear"
    bool comparison_based = true;
    std::size_t n_cap = 1u << 20;
    std::function<void(IntVec&)> run_int;
    std::function<void(CountedVec&)> run_counted;
    std::function<void(KeyIdxVec&)> run_keyidx;
};

// Key extractors for non-comparison sorts over wrapper types.
const auto kCountedKey = [](const lab::Counted<int>& c) {
    return lab::IntegralKey{}(c.value());
};

std::vector<AlgoSpec> make_registry() {
    std::vector<AlgoSpec> r;
    auto comparison = [&](std::string name, std::string family, std::size_t cap, auto fn) {
        r.push_back({std::move(name), std::move(family), true, cap,
                     [fn](IntVec& v) { fn(v.begin(), v.end()); },
                     [fn](CountedVec& v) { fn(v.begin(), v.end()); },
                     [fn](KeyIdxVec& v) { fn(v.begin(), v.end()); }});
    };
    auto keyed = [&](std::string name, auto fn) {
        r.push_back({std::move(name), "linear", false, 1u << 20,
                     [fn](IntVec& v) { fn(v.begin(), v.end(), lab::IntegralKey{}); },
                     [fn](CountedVec& v) { fn(v.begin(), v.end(), kCountedKey); },
                     [fn](KeyIdxVec& v) { fn(v.begin(), v.end(), lab::KeyIdxKey{}); }});
    };
    const std::size_t quad_cap = 32768;
    comparison("bubble", "n2", quad_cap,
               [](auto f, auto l) { lab::bubble_sort(f, l); });
    comparison("insertion", "n2", quad_cap,
               [](auto f, auto l) { lab::insertion_sort(f, l); });
    comparison("selection", "n2", quad_cap,
               [](auto f, auto l) { lab::selection_sort(f, l); });
    comparison("shell", "n2", 1u << 20,
               [](auto f, auto l) { lab::shell_sort(f, l); });
    comparison("merge", "nlogn", 1u << 20,
               [](auto f, auto l) { lab::merge_sort(f, l); });
    comparison("quick", "nlogn", 1u << 20,
               [](auto f, auto l) { lab::quick_sort(f, l); });
    comparison("heap", "nlogn", 1u << 20,
               [](auto f, auto l) { lab::heap_sort(f, l); });
    comparison("std_sort", "nlogn", 1u << 20,
               [](auto f, auto l) { std::sort(f, l); });
    comparison("std_stable_sort", "nlogn", 1u << 20,
               [](auto f, auto l) { std::stable_sort(f, l); });
    keyed("counting", [](auto f, auto l, auto k) { lab::counting_sort(f, l, k); });
    keyed("radix", [](auto f, auto l, auto k) { lab::radix_sort(f, l, k); });
    keyed("bucket", [](auto f, auto l, auto k) { lab::bucket_sort(f, l, k); });
    return r;
}

std::vector<std::size_t> sweep_for(const AlgoSpec& a, bool quick) {
    std::vector<std::size_t> base =
        quick ? std::vector<std::size_t>{256, 1024, 4096}
              : std::vector<std::size_t>{256,   1024,   4096,   16384,
                                         32768, 65536,  262144, 1048576};
    std::vector<std::size_t> out;
    for (std::size_t n : base)
        if (n <= a.n_cap) out.push_back(n);
    return out;
}

bool verify_sorted_permutation(const IntVec& sorted_out, IntVec reference) {
    std::sort(reference.begin(), reference.end());
    return sorted_out == reference;  // sorted AND a permutation of the input
}

void run_bench(bool quick) {
    const int repeats = quick ? 2 : 5;
    const std::uint32_t seed = 42;
    auto registry = make_registry();

    lab::CsvWriter times("results/sorting_times.csv",
                         {"algo", "family", "dist", "n", "repeats", "median_ms"});
    lab::CsvWriter ops("results/sorting_ops.csv",
                       {"algo", "family", "dist", "n", "comparisons", "moves", "swaps"});
    lab::CsvWriter props("results/sorting_props.csv",
                         {"algo", "family", "comparison_based", "stable_observed", "n_cap"});

    std::vector<std::vector<std::string>> summary_rows;
    for (const auto& a : registry) {
        const bool stable = lab::observed_stable(a.run_keyidx);
        props.write_row({a.name, a.family, a.comparison_based ? "yes" : "no",
                         stable ? "yes" : "no", lab::cell(a.n_cap)});
        summary_rows.push_back(
            {a.name, a.family, a.comparison_based ? "yes" : "no", stable ? "yes" : "no"});

        for (const lab::Dist d : lab::all_dists()) {
            for (const std::size_t n : sweep_for(a, quick)) {
                const IntVec data = lab::generate(d, n, seed);
                // Wall-clock: median over fresh copies.
                std::vector<double> ts;
                for (int r = 0; r < repeats; ++r) {
                    IntVec v = data;
                    ts.push_back(lab::time_ms([&] { a.run_int(v); }));
                    if (r == 0 && !verify_sorted_permutation(v, data)) {
                        std::cerr << "FATAL: " << a.name << " mis-sorted n=" << n
                                  << " dist=" << lab::dist_name(d) << "\n";
                        std::exit(1);
                    }
                }
                times.write_row({a.name, a.family, std::string(lab::dist_name(d)),
                                 lab::cell(n), lab::cell(repeats),
                                 lab::cell(lab::median(ts))});
                // Operation counts: one deterministic Counted run.
                CountedVec cv(data.begin(), data.end());
                lab::Counted<int>::reset_counters();
                a.run_counted(cv);
                const auto& c = lab::Counted<int>::counters();
                ops.write_row({a.name, a.family, std::string(lab::dist_name(d)),
                               lab::cell(n), lab::cell(c.comparisons), lab::cell(c.moves),
                               lab::cell(c.swaps)});
            }
        }
        std::cout << "done: " << a.name << "\n";
    }

    std::cout << "\nAlgorithm properties (observed):\n";
    lab::print_table({"algo", "family", "comparison", "stable"}, summary_rows);
    std::cout << "\nCSV written to results/sorting_{times,ops,props}.csv\n";
}

}  // namespace

int main(int argc, char** argv) {
    bool quick = false;
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--quick") == 0) quick = true;
    }
    run_bench(quick);
    return 0;
}
```

- [ ] **Step 2: Build and run quick mode**

```bash
cd cpp_algo_lab && make bench-quick
```

Expected: prints `done: <algo>` for 12 algorithms, the properties table (bubble/insertion/merge/counting/radix/bucket/std_stable_sort stable=yes; selection/shell/quick/heap stable=no; std_sort typically no), and creates the three CSVs.

- [ ] **Step 3: Sanity-check CSV contents**

```bash
head -3 cpp_algo_lab/results/sorting_times.csv cpp_algo_lab/results/sorting_ops.csv cpp_algo_lab/results/sorting_props.csv
awk -F, 'NR>1 && $1=="insertion" && $3=="sorted" {print}' cpp_algo_lab/results/sorting_ops.csv | head -3
```

Expected: headers match the Interfaces block exactly; insertion on sorted input shows `comparisons == n-1`, `moves == 2*(n-1)`, `swaps == 0`.

- [ ] **Step 4: Commit (binaries and full results not yet — quick CSVs are fine to commit as placeholders)**

```bash
git add cpp_algo_lab/sorting/bench cpp_algo_lab/results
git commit -m "feat(cpp_algo_lab): add sorting benchmark (times, op counts, properties)"
```

---

### Task 9: Trace mode (`--trace`) for sorting visualizations

**Files:**
- Modify: `cpp_algo_lab/sorting/bench/bench_sorting.cpp`

**Interfaces:**
- Consumes: Task 8 registry.
- Produces (consumed by Task 10): `results/traces/trace_<algo>.csv` for the 10 lab algorithms (not std_sort/std_stable_sort), header `frame,p0,p1,...,p255`; each row is a full snapshot of the 256-element array (random dist, seed 42) taken every `total_events / 119` events (≤ 121 rows including the final sorted state). "Event" = one comparison (comparison sorts) or one key extraction (non-comparison sorts).

- [ ] **Step 1: Add trace support to the benchmark**

In `cpp_algo_lab/sorting/bench/bench_sorting.cpp`:

(a) Add two fields to `AlgoSpec` (after `run_keyidx`):

```cpp
    // Trace hooks: run the algorithm on ints with an instrumented comparator /
    // key extractor. Exactly one of these is set.
    std::function<void(IntVec&, std::function<bool(const int&, const int&)>)> run_traced_comp;
    std::function<void(IntVec&, std::function<std::uint64_t(const int&)>)> run_traced_key;
```

(b) In `make_registry()`, extend the two factory lambdas — replace their `r.push_back` calls with:

```cpp
    auto comparison = [&](std::string name, std::string family, std::size_t cap, auto fn) {
        AlgoSpec s{std::move(name), std::move(family), true, cap,
                   [fn](IntVec& v) { fn(v.begin(), v.end(), std::less<>{}); },
                   [fn](CountedVec& v) { fn(v.begin(), v.end(), std::less<>{}); },
                   [fn](KeyIdxVec& v) { fn(v.begin(), v.end(), std::less<>{}); },
                   nullptr, nullptr};
        s.run_traced_comp = [fn](IntVec& v, std::function<bool(const int&, const int&)> c) {
            fn(v.begin(), v.end(), c);
        };
        r.push_back(std::move(s));
    };
    auto keyed = [&](std::string name, auto fn) {
        AlgoSpec s{std::move(name), "linear", false, 1u << 20,
                   [fn](IntVec& v) { fn(v.begin(), v.end(), lab::IntegralKey{}); },
                   [fn](CountedVec& v) { fn(v.begin(), v.end(), kCountedKey); },
                   [fn](KeyIdxVec& v) { fn(v.begin(), v.end(), lab::KeyIdxKey{}); },
                   nullptr, nullptr};
        s.run_traced_key = [fn](IntVec& v, std::function<std::uint64_t(const int&)> k) {
            fn(v.begin(), v.end(), k);
        };
        r.push_back(std::move(s));
    };
```

and pass an explicit comparator through the comparison-sort wrappers, i.e. change each registration to forward `comp`:

```cpp
    comparison("bubble", "n2", quad_cap,
               [](auto f, auto l, auto comp) { lab::bubble_sort(f, l, comp); });
    comparison("insertion", "n2", quad_cap,
               [](auto f, auto l, auto comp) { lab::insertion_sort(f, l, comp); });
    comparison("selection", "n2", quad_cap,
               [](auto f, auto l, auto comp) { lab::selection_sort(f, l, comp); });
    comparison("shell", "n2", 1u << 20,
               [](auto f, auto l, auto comp) { lab::shell_sort(f, l, comp); });
    comparison("merge", "nlogn", 1u << 20,
               [](auto f, auto l, auto comp) { lab::merge_sort(f, l, comp); });
    comparison("quick", "nlogn", 1u << 20,
               [](auto f, auto l, auto comp) { lab::quick_sort(f, l, comp); });
    comparison("heap", "nlogn", 1u << 20,
               [](auto f, auto l, auto comp) { lab::heap_sort(f, l, comp); });
    comparison("std_sort", "nlogn", 1u << 20,
               [](auto f, auto l, auto comp) { std::sort(f, l, comp); });
    comparison("std_stable_sort", "nlogn", 1u << 20,
               [](auto f, auto l, auto comp) { std::stable_sort(f, l, comp); });
```

(`keyed(...)` registrations are unchanged.)

(c) Add the trace runner (before `main`):

```cpp
void run_traces() {
    constexpr std::size_t kTraceN = 256;
    constexpr std::size_t kMaxFrames = 120;
    const IntVec data = lab::generate(lab::Dist::random_uniform, kTraceN, 42);

    for (const auto& a : make_registry()) {
        if (a.name == "std_sort" || a.name == "std_stable_sort") continue;

        // Pass 1: count events (comparisons or key extractions).
        unsigned long long total = 0;
        {
            IntVec v = data;
            if (a.run_traced_comp)
                a.run_traced_comp(v, [&total](const int& x, const int& y) {
                    ++total;
                    return x < y;
                });
            else
                a.run_traced_key(v, [&total](const int& x) {
                    ++total;
                    return lab::IntegralKey{}(x);
                });
        }
        const unsigned long long interval = std::max<unsigned long long>(1, total / 119);

        // Pass 2: snapshot the array every `interval` events.
        IntVec v = data;
        std::vector<IntVec> frames;
        unsigned long long events = 0;
        auto maybe_snapshot = [&] {
            if (events % interval == 0 && frames.size() < kMaxFrames) frames.push_back(v);
            ++events;
        };
        if (a.run_traced_comp)
            a.run_traced_comp(v, [&](const int& x, const int& y) {
                maybe_snapshot();
                return x < y;
            });
        else
            a.run_traced_key(v, [&](const int& x) {
                maybe_snapshot();
                return lab::IntegralKey{}(x);
            });
        frames.push_back(v);  // final sorted state

        std::vector<std::string> header{"frame"};
        for (std::size_t i = 0; i < kTraceN; ++i) header.push_back("p" + std::to_string(i));
        lab::CsvWriter w("results/traces/trace_" + a.name + ".csv", header);
        for (std::size_t f = 0; f < frames.size(); ++f) {
            std::vector<std::string> row{lab::cell(f)};
            for (int x : frames[f]) row.push_back(lab::cell(x));
            w.write_row(row);
        }
        std::cout << "trace: " << a.name << " (" << frames.size() << " frames, " << total
                  << " events)\n";
    }
}
```

(d) Extend `main`:

```cpp
int main(int argc, char** argv) {
    bool quick = false, trace = false;
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--quick") == 0) quick = true;
        if (std::strcmp(argv[i], "--trace") == 0) trace = true;
    }
    if (trace) {
        run_traces();
        return 0;
    }
    run_bench(quick);
    return 0;
}
```

- [ ] **Step 2: Build and run traces**

```bash
cd cpp_algo_lab && make trace
ls results/traces/ | wc -l
head -2 results/traces/trace_bubble.csv | cut -c1-80
```

Expected: 10 trace CSVs; `trace: <algo> (N frames, M events)` lines with frames ≤ 121; first CSV column header `frame,p0,p1,...`; frame 0 shows the unsorted random array. Also re-run `make bench-quick` to confirm the registry refactor didn't break the normal path (12 × `done:` lines).

- [ ] **Step 3: Commit**

```bash
git add cpp_algo_lab/sorting/bench cpp_algo_lab/results/traces
git commit -m "feat(cpp_algo_lab): add --trace snapshots for sorting visualizations"
```

---

### Task 10: Plot script (matplotlib) — 6 figures

**Files:**
- Create: `cpp_algo_lab/scripts/plot_results.py`

**Interfaces:**
- Consumes: `results/sorting_times.csv`, `results/sorting_ops.csv`, `results/sorting_props.csv`, `results/traces/trace_*.csv` (Tasks 8–9; column names as specified there).
- Produces: `results/plots/{time_vs_n,time_by_dist,heatmap_dist,ops_vs_n,ops_theory,traces}.png` (consumed by docs in Task 12).

Design (dataviz reference palette, light mode, entity-stable colors):

| Figure | Content |
|---|---|
| `time_vs_n.png` | 1×3 log-log panels by family (n2 / nlogn / linear); std baselines gray dashed in nlogn+linear panels; empirical slope annotation (fit over last 3 points) at each line end |
| `time_by_dist.png` | 3 family rows × 5 distribution columns, log-log, shared y per row |
| `heatmap_dist.png` | algo × dist median_ms at n=16384, LogNorm, sequential blue ramp, values annotated in cells |
| `ops_vs_n.png` | 2 log-log panels (comparisons; moves+swaps), comparison sorts + std_sort, dist=random |
| `ops_theory.png` | measured comparisons vs theory guides: insertion ≈ n²/4, merge ≈ n·log₂n, and reference lines n, n log₂ n, n² |
| `traces.png` | 2×5 montage: imshow of each trace matrix (x=frame, y=position, color=value), sequential ramp |

- [ ] **Step 1: Validate the categorical palette (dataviz rule: compute, don't eyeball)**

```bash
node /tmp/claude-1000/bundled-skills/2.1.209/65d5001b67b22dca878c58ca127c88b7/dataviz/scripts/validate_palette.js \
  "#2a78d6,#1baf7a,#eda100,#008300" --mode light
```

Expected: PASS on CVD separation (reference palette slots 1–4 in validated order; documented worst adjacent ΔE 24.2). A contrast WARN on aqua/yellow is expected and mitigated: every figure has a legend, direct end-labels, and the underlying CSVs serve as the table view. (If the skill cache path is missing, note the palette is the pre-validated dataviz reference instance and continue.)

- [ ] **Step 2: Write the plot script**

`cpp_algo_lab/scripts/plot_results.py`:

```python
"""Render sorting benchmark CSVs into PNG figures.

Run from repo root:  uv run --no-sync python cpp_algo_lab/scripts/plot_results.py
(or `make plot` inside cpp_algo_lab/). Reads results/*.csv relative to this
file's parent project directory, writes results/plots/*.png.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, LogNorm

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE / "results"
PLOTS = RESULTS / "plots"

# --- dataviz reference palette (light mode) ---------------------------------
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SLOTS = ["#2a78d6", "#1baf7a", "#eda100", "#008300"]  # validated fixed order
SEQ_STEPS = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
    "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
]
SEQ_CMAP = LinearSegmentedColormap.from_list("lab_blue", SEQ_STEPS)

FAMILIES = ["n2", "nlogn", "linear"]
FAMILY_TITLES = {"n2": "quadratic family", "nlogn": "O(n log n) family",
                 "linear": "non-comparison family"}
# Entity-stable colors: an algorithm keeps its slot in every figure.
FAMILY_SERIES = {
    "n2": ["bubble", "insertion", "selection", "shell"],
    "nlogn": ["merge", "quick", "heap"],
    "linear": ["counting", "radix", "bucket"],
}
BASELINES = ["std_sort", "std_stable_sort"]
COLOR = {}
for fam, algos in FAMILY_SERIES.items():
    for i, a in enumerate(algos):
        COLOR[a] = SLOTS[i]
DISTS = ["random", "sorted", "reversed", "nearly_sorted", "few_unique"]
TRACE_ALGOS = [
    "bubble", "insertion", "selection", "shell", "merge",
    "quick", "heap", "counting", "radix", "bucket",
]

plt.rcParams.update({
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
})


def save(fig: plt.Figure, name: str) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    out = PLOTS / name
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out.relative_to(BASE.parent)}")


def slope_label(n: np.ndarray, y: np.ndarray) -> str:
    """Empirical exponent from the last 3 points of a log-log series."""
    if len(n) < 3 or np.any(y[-3:] <= 0):
        return ""
    k = np.polyfit(np.log(n[-3:]), np.log(y[-3:]), 1)[0]
    return f" n^{k:.2f}"


def plot_series(ax, sub: pd.DataFrame, algo: str, color: str, dashed: bool = False) -> None:
    s = sub[sub["algo"] == algo].sort_values("n")
    if s.empty:
        return
    n, y = s["n"].to_numpy(float), s["median_ms"].to_numpy(float)
    ax.loglog(n, y, color=color, linestyle="--" if dashed else "-",
              marker="o", markersize=4)
    ax.annotate(f"{algo}{slope_label(n, y)}", (n[-1], y[-1]),
                textcoords="offset points", xytext=(6, 0),
                fontsize=8, color=INK_2, va="center")


def fig_time_vs_n(times: pd.DataFrame) -> None:
    sub = times[times["dist"] == "random"]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
    for ax, fam in zip(axes, FAMILIES):
        for algo in FAMILY_SERIES[fam]:
            plot_series(ax, sub, algo, COLOR[algo])
        if fam in ("nlogn", "linear"):
            plot_series(ax, sub, "std_sort", MUTED, dashed=True)
        if fam == "nlogn":
            plot_series(ax, sub, "std_stable_sort", BASELINE, dashed=True)
        ax.set_title(FAMILY_TITLES[fam], color=INK)
        ax.set_xlabel("n (elements)")
        ax.margins(x=0.25)
    axes[0].set_ylabel("median wall time [ms]")
    fig.suptitle("Sorting: time vs n (random input, log-log) — slope ≈ complexity exponent",
                 color=INK)
    save(fig, "time_vs_n.png")


def fig_time_by_dist(times: pd.DataFrame) -> None:
    fig, axes = plt.subplots(3, 5, figsize=(18, 10), sharex=False, sharey="row")
    for ri, fam in enumerate(FAMILIES):
        for ci, dist in enumerate(DISTS):
            ax = axes[ri][ci]
            sub = times[times["dist"] == dist]
            for algo in FAMILY_SERIES[fam]:
                s = sub[sub["algo"] == algo].sort_values("n")
                if not s.empty:
                    ax.loglog(s["n"], s["median_ms"], color=COLOR[algo], marker="o",
                              markersize=3, label=algo)
            s = sub[sub["algo"] == "std_sort"].sort_values("n")
            ax.loglog(s["n"], s["median_ms"], color=MUTED, linestyle="--", label="std_sort")
            if ri == 0:
                ax.set_title(dist, color=INK)
            if ci == 0:
                ax.set_ylabel(f"{FAMILY_TITLES[fam]}\nmedian ms", color=INK_2)
            if ci == 4:
                ax.legend(fontsize=7, framealpha=0.9)
    fig.suptitle("Sorting: time vs n per input distribution", color=INK)
    fig.tight_layout()
    save(fig, "time_by_dist.png")


def fig_heatmap(times: pd.DataFrame) -> None:
    # Largest n present for every algorithm (16384 on a full run, smaller on --quick).
    target_n = int(times.groupby("algo")["n"].max().min())
    target_n = min(target_n, 16384)
    at_n = times[times["n"] == target_n]
    order = [a for fam in FAMILIES for a in FAMILY_SERIES[fam]] + BASELINES
    pivot = at_n.pivot_table(index="algo", columns="dist", values="median_ms")
    pivot = pivot.reindex(index=order, columns=DISTS)
    fig, ax = plt.subplots(figsize=(8, 6.5))
    im = ax.imshow(pivot.to_numpy(), cmap=SEQ_CMAP,
                   norm=LogNorm(vmin=max(pivot.min().min(), 1e-3),
                                vmax=pivot.max().max()),
                   aspect="auto")
    ax.set_xticks(range(len(DISTS)), DISTS, rotation=20)
    ax.set_yticks(range(len(order)), order)
    ax.grid(False)
    mid = np.sqrt(pivot.min().min() * pivot.max().max())
    for r in range(pivot.shape[0]):
        for c in range(pivot.shape[1]):
            v = pivot.iloc[r, c]
            ax.text(c, r, f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color="#ffffff" if v > mid else INK)
    fig.colorbar(im, ax=ax, label="median ms (log scale)")
    ax.set_title(f"Sorting: median time [ms] at n={target_n}", color=INK)
    save(fig, "heatmap_dist.png")


def fig_ops(ops: pd.DataFrame) -> None:
    sub = ops[ops["dist"] == "random"]
    comp_algos = ["bubble", "insertion", "selection", "shell", "merge", "quick", "heap"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, col, title in zip(
            axes, ["comparisons", "movesswaps"],
            ["comparisons", "moves + swaps (element writes)"]):
        for algo in comp_algos:
            s = sub[sub["algo"] == algo].sort_values("n")
            if s.empty:
                continue
            y = (s["comparisons"] if col == "comparisons"
                 else s["moves"] + s["swaps"]).to_numpy(float)
            n = s["n"].to_numpy(float)
            keep = y > 0
            ax.loglog(n[keep], y[keep], color=COLOR[algo], marker="o", markersize=3)
            if keep.any():
                ax.annotate(algo, (n[keep][-1], y[keep][-1]),
                            textcoords="offset points", xytext=(6, 0), fontsize=8,
                            color=INK_2, va="center")
        s = sub[sub["algo"] == "std_sort"].sort_values("n")
        y = (s["comparisons"] if col == "comparisons"
             else s["moves"] + s["swaps"]).to_numpy(float)
        ax.loglog(s["n"], y, color=MUTED, linestyle="--")
        ax.set_title(title, color=INK)
        ax.set_xlabel("n")
        ax.margins(x=0.25)
    axes[0].set_ylabel("operation count")
    fig.suptitle("Sorting: operation counts vs n (random input)", color=INK)
    save(fig, "ops_vs_n.png")


def fig_ops_theory(ops: pd.DataFrame) -> None:
    sub = ops[ops["dist"] == "random"]
    fig, ax = plt.subplots(figsize=(7.5, 5.2))
    for algo in ["insertion", "merge"]:
        s = sub[sub["algo"] == algo].sort_values("n")
        ax.loglog(s["n"], s["comparisons"], color=COLOR[algo], marker="o",
                  markersize=4, label=f"{algo} (measured)")
    n = np.array(sorted(sub["n"].unique()), dtype=float)
    ax.loglog(n, n * n / 4, color=COLOR["insertion"], linestyle=":",
              label="insertion theory: n²/4")
    ax.loglog(n, n * np.log2(n), color=COLOR["merge"], linestyle=":",
              label="merge theory: n·log₂n")
    ax.set_xlabel("n")
    ax.set_ylabel("comparisons")
    ax.set_title("Measured comparisons vs theory (random input)", color=INK)
    ax.legend(fontsize=8)
    save(fig, "ops_theory.png")


def fig_traces() -> None:
    fig, axes = plt.subplots(2, 5, figsize=(16, 6.4))
    for ax, algo in zip(axes.ravel(), TRACE_ALGOS):
        path = RESULTS / "traces" / f"trace_{algo}.csv"
        df = pd.read_csv(path)
        mat = df.drop(columns=["frame"]).to_numpy(float)  # frames x positions
        ax.imshow(mat.T, aspect="auto", origin="lower", cmap=SEQ_CMAP,
                  interpolation="nearest")
        ax.set_title(algo, color=INK, fontsize=10)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
    fig.suptitle("Array state over time (x: progress, y: position, color: value) — "
                 "n=256, random input", color=INK)
    fig.tight_layout()
    save(fig, "traces.png")


def main() -> None:
    times = pd.read_csv(RESULTS / "sorting_times.csv")
    ops = pd.read_csv(RESULTS / "sorting_ops.csv")
    fig_time_vs_n(times)
    fig_time_by_dist(times)
    fig_heatmap(times)
    fig_ops(ops)
    fig_ops_theory(ops)
    fig_traces()
    print("all figures written to", PLOTS)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run against quick-bench data and eyeball every PNG**

```bash
cd cpp_algo_lab && make trace && make bench-quick && make plot
```

Expected: 6 PNGs in `cpp_algo_lab/results/plots/`. Open each (or send to the user) and check: no label collisions, slope annotations readable, heatmap cell text legible on both light and dark cells, traces montage shows 10 distinct patterns (bubble: diagonal sweep; quick: recursive blocks; merge: block merges; counting: 1–2 frame jump — that *is* the lesson). Fix any layout issue before committing.

```bash
cd .. && uv run --no-sync ruff check cpp_algo_lab/scripts/ && uv run --no-sync ruff format --check cpp_algo_lab/scripts/
```

Expected: clean (repo lint covers Python only).

- [ ] **Step 4: Commit**

```bash
git add cpp_algo_lab/scripts cpp_algo_lab/results/plots
git commit -m "feat(cpp_algo_lab): add matplotlib figures for times, ops, and traces"
```

---

### Task 11: Full benchmark run, committed results

**Files:**
- Modify: `cpp_algo_lab/results/*.csv`, `cpp_algo_lab/results/plots/*.png`, `cpp_algo_lab/results/traces/*.csv` (regenerated)

**Interfaces:**
- Consumes: Tasks 8–10.
- Produces: final committed Phase-1 data: full sweep CSVs + final PNGs (referenced by docs in Task 12).

- [ ] **Step 1: Full run (few minutes, quadratic sorts dominate)**

```bash
cd cpp_algo_lab && make test && make bench && make trace && make plot
```

Expected: tests green first (guard), then `done:` × 12, traces × 10, 6 PNGs. Full bench ≈ 2–5 min on this machine (quadratic sorts at n=32768 × 5 dists × 5 repeats).

- [ ] **Step 2: Sanity-check the physics of the results**

```bash
awk -F, 'NR>1 && $1=="bubble" && $3=="random" {print $4, $6}' cpp_algo_lab/results/sorting_times.csv
awk -F, 'NR>1 && $1=="quick" && $3=="random" {print $4, $6}' cpp_algo_lab/results/sorting_times.csv
```

Expected: bubble time grows ~4× per N doubling-by-4 step (quadratic); quick grows just over ~4× per 4× N step (n log n). Insertion on `sorted` must be dramatically faster than on `random`. If numbers look off (e.g. all zeros), investigate before committing.

- [ ] **Step 3: Commit results**

```bash
git add cpp_algo_lab/results
git commit -m "feat(cpp_algo_lab): commit full sorting benchmark results and figures"
```

---

### Task 12: Documentation (Japanese) + workspace integration

**Files:**
- Create: `cpp_algo_lab/README.md`
- Create: `cpp_algo_lab/docs/sorting.md`
- Create: `cpp_algo_lab/docs/references.md`
- Modify: root `README.md` (project index table, after the `shortest_path` row)
- Modify: root `Makefile` (help text "Outside the workspace" line)

**Interfaces:**
- Consumes: figures/CSVs from Task 11 (referenced by relative path), spec `docs/superpowers/specs/2026-07-14-cpp-algo-lab-design.md` §5 (references list).
- Produces: Phase-1 learning documentation. Prose in Japanese; code identifiers stay English.

- [ ] **Step 1: Write `cpp_algo_lab/README.md`**

Japanese. Required sections and content (write full prose, not bullets-only):

1. **概要** — C++学習のためのアルゴリズム実験室。Phase 1 = ソート10種の実装と4軸評価（実測時間・操作回数・分布別・安定性）。スペックへのリンク（`../docs/superpowers/specs/2026-07-14-cpp-algo-lab-design.md`）。
2. **クイックスタート** — 表で: `make test`（sanitizer付き全テスト）/ `make bench`（フル計測、数分）/ `make bench-quick` / `make trace` / `make plot`（リポジトリルートのuv環境でPNG生成）/ `make clean`。「make はこのディレクトリで実行」「ベンチ中は他の重い処理を避ける（WSL2の計測ばらつき）」を明記。
3. **構成** — ディレクトリツリー（Task 1の構造）と各ディレクトリの1行説明。`common/lab/` は計測基盤、`sorting/include/sorting/` は1アルゴリズム=1ヘッダ、`results/` はコミット対象。
4. **学習ロードマップ** — 推奨順: ① `docs/sorting.md` を読む → ② ヘッダを読む（bubble→insertion→selection→shell→merge→quick→heap→counting→radix→bucket の順） → ③ `make bench && make plot` で図を再生成 → ④ `results/plots/` の6図を `docs/sorting.md` の「結果の読み方」と突き合わせる。
5. **Phase 状況表** — Phase 1 ✅ / Phase 2 検索 ⬜ / Phase 3 CPU並列 ⬜ / Phase 4 GPU ⬜ / Phase 5 docs仕上げ ⬜。
6. **依存** — g++ 13 (C++20) と make のみでビルド可。doctest は `third_party/` に同梱。図化のみ uv workspace（pandas/matplotlib）。

- [ ] **Step 2: Write `cpp_algo_lab/docs/sorting.md`**

Japanese, this is the centerpiece doc (アルゴリズム説明に力を入れる指示への回答). Required structure:

1. **導入** — ソートを題材に選ぶ理由（同じ仕様に対する設計戦略の多様性が見える）。比較ソートの下界 $\Omega(n \log n)$ の直感（決定木の葉が $n!$ 枚必要、深さ $\ge \log_2 n! \approx n \log_2 n$）と、非比較ソートがなぜその外側にいるか。
2. **計算量総覧表** — この表をそのまま含める:

| アルゴリズム | 最良 | 平均 | 最悪 | 追加空間 | 安定 | 主な操作 |
|---|---|---|---|---|---|---|
| bubble | O(n) | O(n²) | O(n²) | O(1) | ✅ | 隣接swap |
| insertion | O(n) | O(n²) | O(n²) | O(1) | ✅ | shift (move) |
| selection | O(n²) | O(n²) | O(n²) | O(1) | ❌ | 遠距離swap |
| shell (Ciura) | O(n log n) | ~n^1.3 | (gap依存) | O(1) | ❌ | gap付きshift |
| merge | O(n log n) | O(n log n) | O(n log n) | O(n) | ✅ | バッファへmove |
| quick (mo3+Hoare) | O(n log n) | O(n log n) | O(n²)* | O(log n) stack | ❌ | swap |
| heap | O(n log n) | O(n log n) | O(n log n) | O(1) | ❌ | sift-down swap |
| counting | O(n+k) | O(n+k) | O(n+k) | O(n+k) | ✅ | 散布 (move) |
| radix (LSD 256) | O(d·n) | O(d·n) | O(d·n) | O(n) | ✅ | パス毎move |
| bucket | O(n) | O(n) | O(n²)** | O(n) | ✅*** | 分配+挿入 |

脚注: * median-of-three で実用上ほぼ回避（理論保証なし＝introsortがdepth監視でheapに切替える理由）。** キーが1バケツに集中した場合。*** operator< とキーが整合する場合。

3. **各アルゴリズム節（10節）** — 各節に必ず4項目: (a) **動き** — 平易な日本語説明。bubble/insertion/selection には8要素 `[5,2,7,1,9,3,8,6]` の手動トレース表（パスごとの配列状態）を含める。merge は分割木と併合の図式（テキスト図）、quick は median-of-three の選択例と Hoare の i/j 走査例、heap は配列の木表現（インデックス親子関係 `2i+1, 2i+2`）、shell は gap 列 `[1750, 701, ...]` の意味、counting はヒストグラム→累積和→散布の3段階を小例で、radix はバイト毎パスの小例、bucket は分配の図式。 (b) **C++実装ポイント** — ヘッダの該当行に対応: bubble=early-exitフラグと`std::iter_swap`、insertion=`std::move`によるshift（swapとの差がopsに出る）、selection=イテレータ2重ループ、shell=`difference_type`とgap生成、merge=一時バッファ再利用と`std::make_move_iterator`相当のmove、安定性を守る `comp(*r, *l)` の向き、quick=値pivotの理由（イテレータ無効化ではなく位置が動くため）と小さい側再帰でstack O(log n)、heap=`first[child]`のランダムアクセスイテレータ添字、counting/radix/bucket=KeyFnカスタマイズポイント（`IntegralKey`のstatic_assert、`Counted<int>`にはlambdaを渡す）、radix=`count[b+1]`トリック。 (c) **予想** — 図を見る前の理論予想（例: selectionのswapsはn-1以下、insertionはnearly_sortedでほぼ線形）。 (d) **結果の読み方** — `results/plots/` のどの図のどこを見るか。
4. **評価ハーネスの説明** — `Counted<T>` の仕組み（演算子オーバーロードで計数、時間計測は素のintで歪みゼロ）、median採用理由、`observed_stable` プローブの原理（key,idx対）、trace の撮り方（比較/キー抽出をフックして配列スナップショット）。
5. **6つの図の解説** — 各図1段落: 何が描いてあるか、注目点（time_vs_n の傾き≒指数、time_by_dist の insertion×nearly_sorted、heatmap の few_unique 列、ops_vs_n の selection の moves+swaps の少なさ、ops_theory の実測と理論の重なり、traces の各アルゴリズムの「模様」の意味 — quickの再帰ブロック、mergeのブロック併合、countingがほぼ一撃=非比較の本質）。
6. **std::sort / std::stable_sort との対比** — introsort（quick+heap+insertionのハイブリッド）とmerge系である背景、自作との性能差はどこから来るか（分岐予測、キャッシュ、カットオフ）。

- [ ] **Step 3: Write `cpp_algo_lab/docs/references.md`**

Japanese annotations, English titles. Content = spec §5 list, formatted:

```markdown
# 参考文献と本ラボの対応

## ソート（Phase 1 / Phase 3–4 で使用）
- **Sorting with GPUs: A Survey** (arXiv:1709.02520) — GPUソートは radix / merge / sample / quick の4系統。Phase 4 の見取り図。
- **Onesweep** (Adinets & Merrill, NVIDIA 2022; 解説: AMD GPUOpen "Boosting GPU radix sort") — 現行SOTAのLSD radix。`thrust::sort`（整数キー）はこの系譜。Phase 4 で「自作bitonic vs 30年分の研究」を対比する基準線。
- **K. E. Batcher, Sorting Networks and their Applications (1968)** — bitonic sorting network。Phase 4 の自作カーネル題材。
- **IPS⁴o: In-place Parallel Super Scalar Samplesort** (Axtmann et al., ESA 2017 / ACM TOPC 2022, github.com/ips4o) — CPU並列ソートSOTA。同梱せず、Phase 3 の「現実の到達点」参照値。
- **Ciura, Best Increments for the Average Case of Shellsort (2001)** — shell.hpp の gap 列の出典。

## 文字列検索（Phase 2/4 で使用予定）
- **Kouzinopoulos & Margaritis, String Matching on a multicore GPU using CUDA** — naive/KMP/BMH/Quick-Search のCUDA比較（最大24×）。Phase 4 検索カーネルの答え合わせ先。
- **PFAC: Parallel Failureless Aho-Corasick**（Lin et al.; DNA最適化版 arXiv:1811.10498） — failure遷移を捨て1スレッド=1開始位置。本ラボのGPU naiveカーネルはこの思想の単一パターン版。
- **Efficient Parallel KMP for Multi-GPUs** (Springer) — KMPのfailure関数の逐次依存はGPU並列化の障害という教訓の出典。
- **GPUs for Pattern Matching** (arXiv:1412.7789) — サーベイ。

各文献の「何を縮小再現するか」は docs/sorting.md（Phase 2 以降は各モジュールのノート）の該当節から参照する。
```

- [ ] **Step 4: Workspace integration (2 one-line edits)**

Root `README.md`: after the `shortest_path` row in the project index table, add:

```markdown
| [`cpp_algo_lab/`](cpp_algo_lab/) | C++学習ラボ：ソート/文字列検索/CPU・GPU並列化の実装と計測（Phase 1: ソート10種+評価4軸） | C++20 / make / doctest |
```

Root `Makefile`: change the help line

```make
	@echo "  rates_volatility_model, notebooks, shortest_path (manual envs)"
```

to

```make
	@echo "  rates_volatility_model, notebooks, shortest_path, cpp_algo_lab (manual envs)"
```

- [ ] **Step 5: Verify docs render and links resolve**

```bash
grep -roh 'plots/[a-z_]*\.png' cpp_algo_lab/README.md cpp_algo_lab/docs/ | sort -u | while read f; do
  test -f "cpp_algo_lab/results/$f" && echo "OK $f" || echo "MISSING $f"
done
```

Expected: all `OK` (every figure referenced from the docs exists; docs must reference figures as `results/plots/<name>.png` relative paths). Also `cd cpp_algo_lab && make test` one final time (green).

- [ ] **Step 6: Commit**

```bash
git add cpp_algo_lab/README.md cpp_algo_lab/docs README.md Makefile
git commit -m "docs(cpp_algo_lab): add Japanese sorting guide, references, README; register in workspace index"
```

---

## Phase 1 acceptance check (after Task 12)

Run in order, all must hold (spec §8 items 1–2 restricted to sorting):

1. `cd cpp_algo_lab && make test` — all doctest binaries green under ASan/UBSan.
2. `make bench && make trace && make plot` — regenerates 3 CSVs + 10 traces + 6 PNGs without error.
3. `results/plots/time_vs_n.png` shows slope ≈ 2 for the quadratic family and ≈ 1 for the linear family; `ops_theory.png` shows measured points on the theory curves.
4. `git status` clean, `make lint` (repo root) unaffected.
