# Research runner second review

Source checkpoint review only; formal pilot/main not accepted.

- Source SHA: c7347038a5741a8863f1bfffd58475fb6bd4cad8394020c9ab3f2908e5206937
- Tests SHA: cdd7583688cf65f4072e17f81369f1d5c2a65680b6d67203d2de6b8e8fca198b
- Scoped tests: 25 passed in 22.33s.

## RUN2 — Important

Validated selections remain aliased across the main test loader. The independent real protocol gate probe changes the already-selected Heston/U1 band from width0 to width0.2 inside the loader. Every subsequent Heston/U1 evaluation receives width0.2. Fits are detached, but validation selections are not. Detach the validated selection records before opening test data, and use only the fixed records for evaluation.

Probe and raw output: task-5-runner-review-selection-alias-probe.py/json. Synthetic financial gate receipts are structural unit scaffolding; no real pilot/main qualification is claimed.
