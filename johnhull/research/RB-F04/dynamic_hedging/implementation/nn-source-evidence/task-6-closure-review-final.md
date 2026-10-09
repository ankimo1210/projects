# Task 6 closure 独立レビュー

## 判定

限定承認。**Critical 0 / Important 0 / Minor 0**。対象は全12 fit の固定チェックポイント・原本Nを保持したvalidation closureと保存数値replayの実装契約です。金融精度、正式pilot/freeze/mainの承認ではありません。

- Source SHA: c34a9aab22e216a512deafd1205c222fb17e9cc6b60ef46b7ff3267b64417902
- Test SHA: 7ca8bd46194081eeaba2d5662ded14607a6b587ecf702dbec3363468fd0a9ad5
- 独立対象テスト: **38 passed in 46.13s**
- 独立反例: **6群PASS**（raw原出力は下記）
- Ruff check / format --check: PASS、検証前後のsource/test SHA一致。

## 確認したこと

1. 全2生成モデル×2universe×3init、12原slot、train8192・validation2048・512要求updatesを保持。trainのみの正規化、6tensorのshape、固定last_finite_completedを照合。
2. 株0.5・U2 call0.25を固定保有する価格経路で、初期購入、金利成長、初期/終端spread、終端清算、Asian支払いの手計算と全12×2048のloss/MSEを比較。最大cash絶対誤差 **5.284661597215745e-14**。
3. 診断損益が有限でもtraining/validation unknownはqualified selectionに昇格せず、rawの最後の有限weightsと原2048個の損益を保持。全validation unknownでも全12fit/56baseline候補が残り、selected_baselineはNone。
4. outerfailed/rawcompletedの実connector capケースで、rawweightsは保持しcheckpoint選択は拒否。optimizer_errorはsource_or_optimizer_defectでunclosed。欠落rawと非有限marketの分類は対象テストでも確認。
5. raw/config/scale/batch/path/seed/global-driver/calendar/fee/sharedpremiumの変更は拒否。測定elapsed、原300秒cap、overrun、raw≤inclusive elapsedの4反例は最終38テストに含まれる。
6. 保存replayでfit/optimizer/default_rng/SeedSequenceを禁止してPASS。teacher/新金融経路/テストstreamは開かない。全28件の費用原本を交差照合する。
7. checker全体qualificationは常にunknown。NN/baselineの診断qualificationは別フィールド。金融資格や乱数由来の認証を代替しない。

## 初期review懸念の解消

- **NN completion must be separate from baseline validation and training completion**: All12 fixed raw checkpoints get original2048 validation; 4x14 baseline candidates retained separately; all-failed selected_baseline stays None.
- **Finite numeric losses with unknown market/teacher qualification could rescue checkpoint**: Unknown training or validation creates failed selection and checkpoint None, retains finite diagnostic loss/last weights; checker overall qualification always unknown.
- **Outer failed/raw completed over-cap connector could rescue completed raw optimizer**: Inclusive connector overrun classified time_cap; original raw completed weights retained but original2048 validation unknown. Actual elapsed/cap/overrun checked before producer closes.
- **Optimizer/source defects could be relabeled as recognized finance failure**: Optimizer_error and missing raw on finite input stay source_or_optimizer_defect/unclosed. Direct nonfinite market numbers allow explicit unqualified_training_data.
- **Inputs/weights/scaler could drift from original fixed candidate**: Monthly calendar/rate/halfspreads/Asian memory/payoff/shared premium/path IDs/declared reserved seeds and global driver IDs checked; six weights/shapes/config/512 attempts/checkpoint and train-only scales checked.
- **No-RNG saved replay could construct SeedSequence or claim history authentication**: Cached original candidate; replay recomputes fixed train/validation cash and selections without fit/RNG, returns history and RNG authenticity False. Independent probe confirmed plausible earlier batch/loss history can remain structurally valid: this is explicitly unverified.
- **Costs might drop validation or double-charge children**: All28 inclusive root cost IDs retained/cross-bound; 12 training+12 NN validation+4 baseline selection, measured wall/cpu finite; metadata is a raw study ledger, not A normalized timing receipts.

## 承認の境界

- Approval covers this private closure source contract and synthetic original-count saved arithmetic replay only.
- No actual model teacher precision, calibration/Q correctness, random-stream provenance, earlier optimizer-step history, external source bytes registry, or fresh main financial qualification is certified.
- Declared stream seeds/IDs are checked for isolation; actual raw driver bytes/history require external receipts and caller-owned source checks.
- Recorded timings are cross-bound metadata; reviewer did not authenticate original wall-clock history or recreate actual optimization.
- A normalized execution-expense metadata producer/runner integration is outside this module approval; raw study expenses are not already A receipt objects.
- Disk fit-boundary checkpoint resumption, real formal pilot/freeze/main/NN main, test streams, and full suites were not opened.
- Parent actual full-count source-unit optimization and split disk evidence retain their historical5ea85d source SHA; reviewer neither relabeled them nor reran training.

入力fixtureはsynthetic原本Nのsource-unit証拠であり、Heston/local実市場の検証ではありません。履歴上のbatch IDs・lossを構造的に妥当な値へ変更しても最終weights/cash契約が変わらなければauditは通ります。この限界を独立probeで確認し、実装がhistory_authenticated=Falseと明記するため欠陥扱いにはしていません。

## 証跡

- task-6-closure-review-probes.py/json/txt
- task-6-closure-review-tests.txt（38件の独立原出力）
- task-6-closure-review-ruff.json
- task-6-closure-review-run.json
- task-6-closure-review-final.json（全source binding・証跡SHA・限定承認）
- 初期task-6-closure-review-requirements.md/jsonは変更していない。

source/tests/docs/Gitの変更は行っていません。
