# cpp_algo_lab Phase 4–5 (GPU Ladder and Final Documentation) Implementation Plan

**Goal:** Complete the GPU rungs of the sorting/search ladder on the verified RTX 5080: an educational CUDA bitonic sort, a `thrust::sort` baseline, and a one-thread-per-start CUDA naive search, with honest kernel-only versus end-to-end timings, committed CSVs/figures, Japanese learning notes, and final project documentation.

**Scope:** Phase 4 implements and measures GPU code. Phase 5 closes documentation and the project roadmap. Multi-pattern PFAC, production GPU libraries beyond Thrust, autotuning, and GUI/web output remain out of scope.

**Verified environment (2026-07-18):**

- `/usr/local/cuda-12.9/bin/nvcc`, CUDA 12.9.41
- NVIDIA GeForce RTX 5080, compute capability 12.0 (`sm_120`), 16,303 MiB
- Thrust headers from CUDA 12.9
- Compute Sanitizer 2025.2
- Host compiler g++ 13.3; `.cu` sources use C++20

## Architecture and invariants

- GPU code lives below `cpp_algo_lab/parallel/gpu/`; CPU targets remain independent of CUDA.
- Makefile defaults to `/usr/local/cuda-12.9/bin/nvcc -arch=sm_120`; `CUDA_HOME` and `GPU_ARCH` can be overridden explicitly for another verified environment.
- Public host wrappers use `namespace lab::gpu` and throw `std::runtime_error` on CUDA API failure.
- `bitonic_sort` accepts arbitrary vector sizes by padding to the next power of two with `INT_MAX`; the benchmark uses exactly $2^{24}$ elements and therefore needs no padding.
- The bitonic kernel implements ascending compare-exchange stages. It is educational $O(n\log^2 n)$ code, not presented as a competitive integer sort.
- `thrust_sort` is the optimized library baseline and is compared with sequential `std::sort` under the same unstable-sort contract.
- CUDA naive search assigns one candidate start position to one CUDA thread. It writes one byte flag per candidate; the host gathers flags in ascending order, preserving the Phase 2 API including empty-pattern and overlapping-match conventions.
- Every correctness test compares with `std::sort` or `lab::naive_search`. Every timed repeat is also checked outside its timed interval.
- GPU tests are separate: ordinary `make test` and CPU `make bench` never require CUDA.

## Measurement contract

- Seed 42, one untimed warm-up, five timed repeats, median + MAD.
- Full sort workload: $n=2^{24}$ random integers.
- Full search workload: $n=2^{26}$, $m=16$, texts `{english, dna}`.
- Quick workload: sort $n=2^{20}$, search $n=2^{22}$, two repeats; output only below ignored `build/`.
- Full output is staged under `build/` and published to `results/` only after all benchmark sections succeed.
- **kernel mode:** CUDA events measure device algorithm execution with allocations and input copies outside the interval. Result copies for validation are also outside the interval.
- **end_to_end mode:** `steady_clock` measures the complete host wrapper: allocation, H2D, kernel/library execution, D2H, host result materialization, and cleanup.
- **host mode:** `steady_clock` measures the CPU baseline.
- `results/gpu_sort.csv` schema: `algo,mode,n,repeats,median_ms,mad_ms`.
- `results/gpu_search.csv` schema: `algo,text,mode,n,m,repeats,median_ms,mad_ms,occurrences`.

## Static chart contract

The repository explicitly selects reproducible static Matplotlib PNGs as the delivery surface.

### `gpu_sort_times.png`

- Analytical question: how do bitonic and Thrust change when transfers are included, and how do they compare with CPU `std::sort`?
- Supported takeaway: kernel-only numbers are not end-user latency; Thrust and bitonic must be judged under both modes.
- Family/variant: comparison, horizontal dot-and-MAD interval plot on a log-time axis; five full-sweep rows.
- Encoding: neutral CPU reference, one blue root for kernel points, one orange/gold root for end-to-end points; marker shape also distinguishes mode.
- Context: title identifies GPU sort time; subtitle includes $n$, repeats, and median ± MAD.

### `gpu_search_times.png`

- Analytical question: how does one-thread-per-start CUDA naive search compare with CPU naive/BMH for english and DNA?
- Supported takeaway: the GPU kernel exposes massive alignment parallelism, while end-to-end time honestly includes the large flag transfer and host materialization.
- Family/variant: two-facet horizontal dot-and-MAD interval plot on a shared log-time axis; four rows per text.
- Encoding: mode roots and marker shapes match the sort figure; facets carry text identity without adding redundant colors.

### `gpu_transfer_tax.png`

- Analytical question: what multiple does end-to-end latency add over kernel-only execution?
- Supported takeaway: transfer/materialization tax differs by algorithm and output volume.
- Family/variant: horizontal zero-based bar chart of `end_to_end/kernel` for bitonic, Thrust, CUDA naive english, and CUDA naive DNA.
- Encoding: one restrained root, direct multiplier labels, no redundant legend.

### Visual QA

- Validate exact schemas, full row sets, workload sizes, repeat counts, positive medians, non-negative MAD, and constant occurrence counts before plotting.
- Use explicit palette values from `labviz`; do not rely on Matplotlib defaults or color alone.
- Titles remain neutral/descriptive. Interpretive claims belong in `parallel_gpu.md`.
- Inspect the three exported PNGs at their real resolution for clipping, overlaps, honest log/zero scales, and legible uncertainty.

## Task 1: CUDA utilities and GPU algorithms

- [x] Create `parallel/gpu/include/gpu/cuda_utils.cuh` with checked CUDA calls, RAII device buffers, and event timing.
- [x] Create `parallel/gpu/include/gpu/sort.cuh` with bitonic device stages, arbitrary-size host wrapper, Thrust device operation, and host wrapper.
- [x] Create `parallel/gpu/include/gpu/search.cuh` with the flags kernel, device launch helper, flag gathering, and host wrapper.
- [x] Keep all comments and identifiers English and make headers self-contained.

## Task 2: GPU correctness tests and isolated build targets

- [x] Create `parallel/gpu/tests/test_gpu.cu` using vendored doctest.
- [x] Cover empty/single/non-power-of-two/duplicates/negative/`INT_MAX` sort cases and generated larger inputs.
- [x] Cover empty pattern, pattern longer than text, exact/overlapping results, CUDA block boundaries, all text generators, and larger generated corpora.
- [x] Add `gpu`, `gpu-test`, and `gpu-sanitize` Makefile targets with CUDA 12.9 and `sm_120` defaults.
- [x] Run `make gpu-test` and Compute Sanitizer memcheck successfully. (`gpu-test`: 66/66; memcheck: 0 errors after directing sanitizer temporary FIFOs to Linux `/tmp`.)

## Task 3: GPU benchmark and committed results

- [x] Create `parallel/gpu/bench/bench_gpu.cu` with warm-up, shuffled rounds, median/MAD, every-repeat verification, quick output isolation, and staged full publication.
- [x] Sort rows: `std_sort_cpu/host`, `bitonic/kernel`, `bitonic/end_to_end`, `thrust/kernel`, `thrust/end_to_end`.
- [x] Search rows per text: `naive_cpu/host`, `bmh_cpu/host`, `cuda_naive/kernel`, `cuda_naive/end_to_end`.
- [x] Add `gpu-bench` and `gpu-bench-quick` Makefile targets.
- [x] Verify quick execution leaves canonical GPU CSVs untouched once they exist.
- [x] Run the full benchmark twice on an otherwise idle machine; keep the latest non-cherry-picked successful run and describe unstable points through MAD.

## Task 4: GPU figures

- [x] Create `scripts/plot_gpu.py` implementing the chart contract and strict full-input validation.
- [x] Add `plot-gpu`; make the aggregate `plot` target render 6 sorting + 5 search + 3 CPU parallel + 3 GPU figures.
- [x] Run both Ruff gates and inspect all three GPU PNGs.

## Task 5: Phase 4 learning documentation

- [x] Create Japanese `docs/parallel_gpu.md` (roughly 250+ lines).
- [x] Explain SIMT/grid/block/thread indexing, bitonic network stages, padding, Thrust contract differences, naive-search flags, CUDA error handling, and synchronization.
- [x] Explain kernel-only versus end-to-end measurement without treating transfer as an implementation defect.
- [x] Quote only committed CSV values or exact derivations; show MAD and distinguish evidence from causal hypotheses.
- [x] Connect the implementation to Batcher, GPU sorting surveys/Onesweep, CUDA search literature, and PFAC without claiming the single-pattern naive kernel is PFAC.

## Task 6: Phase 5 closure

- [x] Update `cpp_algo_lab/README.md`: commands, tree, 17 figures, GPU dependencies, roadmap, Phase 4/5 completion.
- [x] Update `docs/references.md` so GPU sources point to the concrete experiment and `parallel_gpu.md`.
- [x] Confirm the workspace root README and Makefile already index/exclude `cpp_algo_lab`; change them only if stale.
- [x] Run CPU tests, GPU tests, Compute Sanitizer, quick/full benchmark checks, all plots, Ruff, local-link validation, and `git diff --check`.
- [x] Commit Phase 4 implementation/results and Phase 5 documentation locally; do not push or publish without explicit approval.

## Acceptance criteria

1. `make test` remains green under ASan/UBSan without CUDA.
2. `make gpu-test` passes on RTX 5080 `sm_120`; `make gpu-sanitize` reports zero errors.
3. `make gpu-bench` produces complete, validated transfer-included/excluded CSVs and no correctness failures.
4. `make plot` produces all 17 PNGs; GPU figures pass the chart contract and visual inspection.
5. `parallel_gpu.md`, README, and references quote only validated data and state semantic/fairness caveats.
6. Phase 4 and Phase 5 are marked complete, with changes committed locally and remote publication performed only after explicit user approval.

## Execution record (2026-07-18)

- **PASS:** CPU ASan/UBSan tests: 58 test cases, 15,204 assertions.
- **PASS:** ordinary CUDA tests: 8 test cases, 66 assertions on RTX 5080 `sm_120`.
- **PASS:** Compute Sanitizer memcheck, initcheck, and synccheck report 0 errors; racecheck reports 0 hazards. The original exit 13 was traced to unsupported FIFO creation on the Windows DrvFS temporary directory and fixed by using Linux `/tmp`.
- **PASS:** quick-output hash isolation and two complete full GPU benchmark runs; the latest non-cherry-picked run is retained.
- **PASS:** exact GPU CSV validation, all 17 plots, both Ruff gates, visual inspection of the three GPU plots, 79 local Markdown links, and `git diff --check`.
- **PASS:** the original Phase 4 branch was pushed only after explicit user approval; finalization work continues on a clean local branch based at `28af90f`.
