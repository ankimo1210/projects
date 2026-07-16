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

.PHONY: all test bench bench-sorting bench-search bench-quick bench-search-quick trace plot plot-sorting plot-search clean

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

plot: plot-sorting plot-search

plot-sorting:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_results.py

plot-search:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_search.py

clean:
	rm -rf $(BUILD)
