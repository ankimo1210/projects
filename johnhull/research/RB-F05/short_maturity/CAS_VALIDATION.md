# RB-F05 main/fresh dual-store semantic validation

- Result: all four independent restoration/semantic checks PASS.
- Financial10/current frozen source registry and protected canonical records unchanged.
- Both stores were read independently with restore([single_store]); no fallback or alternate-store recovery.
- RNG sampling, learner.train, Torch Adam/SGD/AdamW/RMSprop constructors and Torch/NumPy sampling APIs trapped.
- SeedSequence deterministic reservation validation is provenance derivation, not resampling observations.
- Main restoration used canonical reference.json and serialization_cost.json with each independently restored NPZ.
- Fresh restoration used each independently restored fresh NPZ plus canonical byte-preserved JSON/code/cost proof, and a symlink to the same role's independent main restoration (no canonical NPZ fallback).
- Each fresh helper.check_saved really repeats main saved semantic validation, then fresh original-N primitives/references/15-vector moments and cost/source bindings.

| Artifact | Store | Restore seconds | Archive-load seconds | Semantic seconds | Binding seconds | Copy wall seconds |
|---|---|---:|---:|---:|---:|---:|
| main | primary | 0.79161202 | 1.00675396 | 9.80043699 | 0.11547619 | 11.71927743 |
| main | mirror | 0.69702482 | 1.06024085 | 9.80342634 | 0.11581372 | 11.68079834 |
| fresh | primary | 0.79803842 | included in semantic | 13.61839933 | 0.01518657 | 14.43451267 |
| fresh | mirror | 0.83393532 | included in semantic | 13.81783566 | 0.01333112 | 14.66836041 |

## Cost scope / unique charges

- main/cas_restore_validate: 24.47709552s including shared module/trap setup once.
- fresh/store_put: 5.27869236s (both copies and new manifest).
- fresh/cas_restore_validate: 29.10293352s.
- Unique categorized outer expense sum: 58.85872140s.
- Do not add per-copy wall to its restore/load/semantic/binding inner components again.
- Fresh semantic time includes the real repeated main check. This is separately executed paid verification, not reuse; its inner main phase is not added again.
- Shared setup is owned/charged only by main/cas_restore_validate. Fresh receipt shows it descriptively, without charging it again.
- These are additional archive-reproducibility costs, separate from original generation/cold serving/fresh-generation/fresh-saved-replay costs. They are not production-pricing startup requirements.
- The categorized outer sum is not a complete new interpreter CLI wall measurement; receipt serialization/control overhead outside these clocks is not inferred as zero.

## Repository outputs (only four owned new receipts)

- main_cas_validation.json
- fresh_manifest.json
- fresh_store_cost.json
- fresh_cas_validation.json

## Restore locations

- main primary: /tmp/rbf05-main-cas-primary-gxgock1v
- main mirror: /tmp/rbf05-main-cas-mirror-_c9rgntd
- fresh primary: /tmp/rbf05-fresh-cas-primary-jv8h10lq
- fresh mirror: /tmp/rbf05-fresh-cas-mirror-hdmiknc4

## Script / commands

- /tmp/rbf05_cas_validation.py (supports frozen-source metadata binding and per-store semantic checks).
- Shared Python, both project src PYTHONPATH, BLAS/OMP/MKL=1.
- Command: python /tmp/rbf05_cas_validation.py --primary /mnt/c/Users/Kazumasa/ProjectArtifacts/projects --mirror /mnt/f/ProjectArtifacts/projects-backup
- Program exit0; /tmp/rbf05-cas-validation-summary.json.
- No new observations, training, checkpoint/labels/model selection, financial source edits or Git operations.
