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

test: $(BUILD)/test_common $(BUILD)/test_sorting
	$(BUILD)/test_common
	$(BUILD)/test_sorting

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
