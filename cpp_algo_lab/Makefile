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

.PHONY: all test bench bench-sorting bench-search bench-parallel bench-quick bench-search-quick bench-parallel-quick trace plot plot-sorting plot-search plot-parallel clean

all: $(BUILD)/test_common $(BUILD)/test_sorting $(BUILD)/test_search $(BUILD)/test_parallel $(BUILD)/bench_sorting $(BUILD)/bench_search $(BUILD)/bench_parallel

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

$(BUILD)/bench_parallel: parallel/bench/bench_parallel.cpp $(PAR_HDRS) $(SEARCH_HDRS) $(SORT_HDRS) $(COMMON_HDRS) | $(BUILD)
	$(CXX) $(BENCHFLAGS) $(OMPFLAGS) $< -o $@ $(TBBLIB)

test: $(BUILD)/test_common $(BUILD)/test_sorting $(BUILD)/test_search $(BUILD)/test_parallel
	$(BUILD)/test_common
	$(BUILD)/test_sorting
	$(BUILD)/test_search
	$(BUILD)/test_parallel

bench: bench-sorting bench-search bench-parallel

bench-sorting: $(BUILD)/bench_sorting
	$(BUILD)/bench_sorting

bench-search: $(BUILD)/bench_search
	$(BUILD)/bench_search

bench-quick: $(BUILD)/bench_sorting
	$(BUILD)/bench_sorting --quick

bench-search-quick: $(BUILD)/bench_search
	$(BUILD)/bench_search --quick

bench-parallel: $(BUILD)/bench_parallel
	$(BUILD)/bench_parallel

bench-parallel-quick: $(BUILD)/bench_parallel
	$(BUILD)/bench_parallel --quick

trace: $(BUILD)/bench_sorting
	$(BUILD)/bench_sorting --trace

plot: plot-sorting plot-search plot-parallel

plot-sorting:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_results.py

plot-search:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_search.py

plot-parallel:
	cd .. && uv run --no-sync python cpp_algo_lab/scripts/plot_parallel.py

clean:
	rm -rf $(BUILD)
