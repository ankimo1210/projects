# RB-F05 learner review fixes

2026-10-09. Own files only:
- deep_hedge_price/src/deep_hedge_price/_short_maturity_dml.py
- deep_hedge_price/tests/test_short_maturity_dml.py

Fixed L1 [P2], L2 [P2], L3 [P3] from /tmp/rbf05-learner-cross-review.md.

## Changes

- The CPU learner seeds only torch.random.default_generator.manual_seed(seed) inside CPU-only fork_rng. CUDA/MPS/XPU seeding is never entered.
- Initialization, objective, Adam creation and actual updates execute inside torch.device("cpu") and torch.enable_grad(); the nested contexts restore the caller's ambient device and grad mode.
- predict enables grad inside a CPU context when computing physical Delta and Gamma from the same scalar price, including calls from torch.no_grad().
- Numerical map, scaling, paired initialization/batches, non-clipped raw outputs, actual completed updates, exception outcomes and observed timing accounting are unchanged.

## TDD evidence

Added6 parameter-expanded tests. Witnessed RED: 6 failed,19 deselected in1.72s:
- accelerator seeding trap catches torch.manual_seed's CUDA call;
- price-only and DML Adam execution under ambient meta return incomplete updates0;
- predict under ambient no_grad raises missing grad_fn;
- price-only and DML training under ambient no_grad raise missing grad_fn.

GREEN after the small source fix:25 passed in1.48s.
Formatted the regression test file; final verification:25 passed in1.57s; ruff check PASS; ruff format --check reports2 files already formatted.

The meta regression executes2 actual updates in each method, checks every tensor-valued Adam state is CPU, and checks ambient meta is restored. CPU-seed trap forbids CUDA/MPS/XPU seed functions and confirms the CPU RNG state is restored. no_grad regressions check the caller remains in no_grad; predictions match ordinary calls. Existing Torch/NumPy/three-width spot-FD, paired streams, time cap/overrun/failure and thread/RNG-restoration tests remain green.

Commands:
env PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/deep_hedge_price/src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/kazumasa/projects/.venv/bin/python -m pytest -q /home/kazumasa/worktrees/johnhull-research-roadmap/deep_hedge_price/tests/test_short_maturity_dml.py
/home/kazumasa/projects/.venv/bin/python -m ruff check <owned source> <owned tests>
/home/kazumasa/projects/.venv/bin/python -m ruff format --check <owned source> <owned tests>

## Limits / ownership

No new production dependency, public API, hullkit import, docs, financial source outside the learner, Git or heavy experiment was changed/run. GPU availability/state was not tested on hardware; the tests forbid accelerator seed entry points. Ambient torch.inference_mode is not part of the specified no_grad contract and is not claimed supported. Full pilot, freeze, actual6 fits, main accuracy/performance/adoption and final suite are parent-owned and remain unverified here.

The separate core/protocol read-only review is /tmp/rbf05-core-protocol-cross-review.md with tiny independent probes in /tmp/rbf05-cross-review-probes.json.
