# SDD ledger — plan: johnhull/docs/superpowers/plans/2026-10-03-section-26-8-chooser.md
Ruling: Create the isolated worktree using WSL Git after the native tool rejected UNC dubious ownership — avoid modifying shared Windows Git trust settings, preserve the authorized isolation — cost if wrong: manual lifecycle tracking.
Pre-flight: Task 1→2: reference figure keys choice/package/timing and MC are consumed by _figures; exact four chooser keys agree.
Pre-flight: Task 2→3: §4.15 starts before ## 5, 213 cells and 4 shared figures; registry/browser agree.
Pre-flight: Tasks 1–3→4: source hashes, 16 browser states, 24 predecessor D1 and CH01–CH06 agree with spec.
Task 1: complete (commits 79a203a..9c2f783, tests: python -m pytest johnhull/hullkit/tests/test_chooser.py johnhull/hullkit/tests/test_chooser_reference.py johnhull/hullkit/tests/test_chooser_numerics.py johnhull/hullkit/tests/test_reference_builders_independent.py -q → 65 passed in 1.00s)
Task 2: complete (commits 9c2f783..1fd5671, tests: python -m pytest johnhull/hullkit/tests/test_chooser_lesson.py johnhull/report/tests/test_chooser_notebook.py johnhull/report/tests/test_compound_notebook.py johnhull/report/tests/test_cliquet_notebook.py johnhull/report/tests/test_forward_start_notebook.py -q → 13 passed in 4.43s)
Task 3: complete (commits 1fd5671..a5279b2, tests: python -m pytest johnhull/report/tests/test_chooser_registry.py johnhull/report/tests/test_report_build.py -q → 16 passed in 13.95s)
Verification: API 26 and reference/gate 11 tests failed first on missing features, then passed. Lesson/notebook 6 and registry 1 failed first, then passed. Acceptance/updater 13 and real ledger failed first, then passed.
Verification: initial baseline used main namespace due cwd; corrected worktree root/PYTHONPATH passed its failing path test. F: redraw fallback needed Windows PowerShell directory on PATH; resumed at §26.7, 24 D1 PASS.
Verification: full pytest 3738 passed/6 skipped, existing 2 warnings; four --check, ledger --check-artifacts, ruff 20 changed files, release PASS.
Task 4: complete (commits a5279b2..721f14f, tests: python -m pytest johnhull/hullkit/tests johnhull/report/tests -q → 3738 passed, 6 skipped, 2 warnings in 146.67s (0:02:26))
Final review: fresh-context gpt-6-astra high, range 5013f2d4..721f14f4, one reviewer; Critical 0, Important I1, Minor M1. Re-graded by effect: I1 can return a price after silently discarding an imaginary part; M1 returns no prices and remains Minor.
Final: minor (deferred): M1 — invalid finite market settings can pass when broadcasting with an empty batch; no incorrect prices returned.
Final: Ruling: M22 diagram/example use different maturities — retain the unchanged accepted lesson and its existing deferral — cost if wrong: readers may misread the diagram as the numerical example.
Final: Ruling: M23 historical gate does not reject an API NaN mutation — retain the existing gate; chooser explicitly checks finite outputs — cost if wrong: the old gate can miss a nonfinite pricing regression.
Final: Ruling: M24 compound integration can fail around a 32-microsecond expiry gap — retain the documented existing limitation — cost if wrong: extremely close-expiry users cannot obtain a compound price.
Final: Ruling: no complete fresh mathematical derivation of all 24 earlier models — rely on their existing acceptance plus current D1 runtime/browser/pytest/storage checks — cost if wrong: an older mathematical defect may remain undetected.
Final: Ruling: complex chooser/American/smile/stochastic rate or volatility/discrete dividends — retain explicit simple-European constant-GBM scope — cost if wrong: applying this API outside its assumptions produces unsuitable valuations.
Final: Ruling: arbitrary extreme-market accuracy of the independent quadrature — support the fixed 64 cases and lesson curves, not a universal [-12,12] error guarantee — cost if wrong: outside-range reference prices may be inaccurate.
Final: Ruling: reviewer did not rerun every browser state or visually inspect every image — accept author's 16-state rerun and two-image visual checks plus reviewer's code/hash/two-image checks — cost if wrong: layout issues in other states may remain unseen.
Final: Ruling: reviewer did not rerun the entire suite — require author's fresh whole-suite run after I1; reviewer's 57 checks are supplementary — cost if wrong: independent review may miss interactions beyond its subset.

Final: fixed I1 — test_numpy_complex_market_inputs_in_object_arrays_are_rejected + test_object_complex_scalar_and_mixed_zero_imaginary_inputs_are_rejected 18 RED→GREEN; valid real-object regression passed; API 45 passed.
Final: whole suite — 3757 passed, 6 skipped, 2 warnings in 144.27s (0:02:24) passed, 6 skipped, 2 existing warnings in 144.27s (0:02:24); first run 3756 passed/1 failed was stale review-document ledger hash, fixed by re-registration without production changes.
Final: source/numeric/notebook refresh, 16 browser states/16 screenshots, 24 unchanged D1 dependencies/artifacts/C:/F: copies, four --check, ledger --check-artifacts, ruff 20 files, tracked release PASS.
Final: review clean for Critical/Important after one fix pass; Minor M1 deferred; no re-review. Branch is complete; main integration and push await choice.
