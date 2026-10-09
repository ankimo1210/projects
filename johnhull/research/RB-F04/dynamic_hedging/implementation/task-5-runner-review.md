# Task5 research runner — 独立レビュー

## 結論

**限定したソースチェックポイントを承認。未解決 Critical / Important / Minor は各0件。Task5全体、正式pilot、main実験の受入は未承認。**

- 対象 source: f96d768f5f4755d1495170b61f9e86e82413ee48498b30127d95050f77de94cd
- 対象 tests: 4af2f331c8c7254afd2f0cad77338578d0e8d3ab4f88f7d964dec5bacd16606a
- 変更したソース・Git・docs・indexはありません。自分が修正したstudyはレビューしていません。
- 設計とTask5/6/7計画に照らし、main読込順序、original N/slot/identity、保存済み金融会計、費用・unknownを検査しました。

## 発見と修正

| 指摘 | 元の反例 | 最終確認 |
|---|---|---|
| RUN1 Important | 選択ゲート後のtest artifactから同IDの別weightsを評価へ渡せた | preclosed fits必須、実payloadとprior receipt bind、全raw identity、固定コピーを使用。差替はconsumer前拒否 |
| RUN2 Important | loaderが検証済みband width0をwidth0.2へ変えると評価へ反映 | 全pretest入力をdeepcopy。weights/validation/candidate/frozenN/source/rawlossの同時変更後も全36評価で固定値維持 |
| RUN3 Important | 同じ数値配列でもsorted JSON保存/読込でpayload SHAが変わった | dictのcanonical順序を使用。小反例と実12checkpointの保存roundtrip SHAが一致 |

RUN3の最初の発見者はrunner担当です。レビュー側でも元c7347038を凍結して独立再現しました。RUN1/RUN2の元反例と両候補ソースも保存してあります。

## 検証

- scoped対象tests: **27 passed in 26.48s**。生出力: task-5-runner-review-final-tests.txt。
- 独立mainゲートprobe: **18件PASS**。実source registryと実freeze/assert_main_readyを使用し、4選択×14候補×原始2048lossを確認。
- 正式ゲートの金融receiptはsynthetic unit scaffoldです。expensive study consumerだけを観測用stubに置き換えました。これから金融精度・性能・正式freezeの達成は主張しません。
- 最終tiny artifactの完全saved checkerを**1回**実行し、RNG・training・先行SDE生成・CF/PDEの26操作を禁止してPASS。
- actual tiny: original N32/model、12fit・44policy slot、Heston48/local196 teacher groups、金融source71件。14候補×4の選択、cash/cost/原始lossは保存済みprimitive境界から数値再計算。
- 12fit消失、shared driver改変、必須費用消失を早期拒否。原artifactは変更していません。
- artifact receipt: 9336075541939a609a8f643b78e8d21c7021fac57f3afd4de195130c8678a6d5
- 全suiteは実行していません。

## 証明した範囲

mainのtest loader前にactual source/environment、12slotのG/U/init/原N、checkpoint、request/update数、finite weights/scaler、prior payload、4×14 validation loss/minima、実protocol gateを検査します。固定した選択とモデルだけを使用し、原Nや原slotを減らして通すことはできません。

tiny保存checkerはglobal driver/slice provenance、last-step条件付きlabelとcache、保存marketからmonthly memory/call/gain、quote targetとpolicy/cashの整合性、44slot、費用台帳の必須ID/inclusive親を確認します。unknownをqualifiedへ昇格させません。

## 未検証の範囲

以下はsource自身の固定unverified一覧です。callerのflagで消せません。

- earlier_SDE_and_global_driver_generation
- independent_call_and_Asian_precision
- train_only_scaler_and_training_data_origin
- exported_weights_binding_to_actual_training_events
- original_training_loss_update_and_cap_history
- original_expense_timing_measurement
- conditional_and_binned_Q_accuracy
- formal37quote_and18states
- premium
- full_pilot
- freeze
- main_statistics
- independent_refinements
- fresh
- CAS
- plots

scalerのsource文字列・training_path_count、原始loss historyを変えてもraw identity確認単体は通ることを、別copyで確認しました。これは明示された未検証範囲であり、training由来や実測時間を認証するcheckerはまだありません。完全saved checkerの合格をこれらの認証に読み替えてはいけません。

## 次の実装・受入

正式18state/37quote・条件付き教師と価格/position/SDE/grid精度、独立premium/Q、worst-SEによるN/grid選定、training-to-weights/scaler/history/費用の実証、独立pilot reviewとformal freezeが残ります。その後に全3seed/3level/44slotの主実験・paired統計/誤差envelope・fresh/両CAS/全費用/3図、最終3suite/release/main統合です。
