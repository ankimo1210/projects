# Bounded saved teacher checker：独立source／transportレビュー

**固定ソースと小N保存transportを限定承認。正式 pilot/main・金融資格・予算 lock・phase 完了・N65536／全M6 RSS・全正式容量／速度予測は未承認。**

## 固定対象

- checker SHA：a37626ff56e6ae74e08d6841c66ca9ec5712596d491930e623620d35607bce5b
- 専用test SHA：ce679b219491725e82da021c34326d06ca782fcf76f3d3b1285c7400854fde20
- 正式 canonical identity：408f2bc271a3379fb5aa8a1c96be0839f090cd3b2452bcd8b8a94c4af7bb7652（実 .venv の run_reference._digest(execution_source_identity)）。
- 実 closure 81 files／dynamic imports 0。前後SHA一致。先行 d4a721… は payload_digest の別算式で、正式identityへ採用しない。作者旧記録・算式訂正は保持されている。

旧70関数のASTで変更は check_teacher_grid_record と _raw_job_check の2関数のみ、private helper 2関数を追加。check_teacher_record のsignature/body/default full returnと他全関数は不変。旧80 source（checker以外）・native codec・primitive/SDE/金融数式・driver/seed/原軸を変更していない。source closure/countは実ファイルで確認した。reviewerはsource/tests/docs/Git/CASを変更していない。

## 独立検査：7 positive／11 negative拒否

| 境界 | 独立結果 |
|---|---|
| full default／bounded | 既存108節点×元N16×calendar24の全比較、cacheと全gate要約approx一致。各modeは saved SDE chunk324件を実検算。全11 sample fieldsを含むlabel全field/shape/dtype参照一致 |
| 配列保持 | raw_checksへN×K sample／block／covarianceを保持しない。cache=Noneで全108件検算し、比較済みsample/cov/block weakrefの残存0 |
| 復元・保存比較 | 同じ保存値だけで作ったtransport containerを複製し、元rootを実際に不在化。Path型contextでfull cached bounded reportを全検算し、元report／保存読戻しとsemantic一致。runtime contextはreportへ保存されない |
| 最後節点の数値tamper | fresh literal保存・正しい新由来receipt/bindingを持つGreek sample、joint covariance、16block means、statusの4変形を全て拒否。由来SHA失敗だけの検査ではない |
| geometry／cache | 最終node欠落・重複・元有限cache値→NaNの3変形を拒否 |
| report semantic | 正しい新receipt付きreportの最後reference index、Greek dtype、全N比較flagの3変形を拒否 |
| 原unknown／cap／legacy | 保存済invalid pathの元N16／NaN SE／unknown／SDE未検証、保存済capの未実行16／unclosed108中1節点、旧raw_sha256 literal参照を保持し、金融資格を昇格しない |
| formal consumers／mode | 2つの正式grid callerがboundedを明示（AST）。無効modeを拒否 |

全N saved SDE再計算・全11 labels/stat/16block/3cov/NaN/status比較の既存完了後にだけcompactするソース順序を確認した。新reportの由来は元raw path＋physical root/pack bindingまたは旧literal SHAであり、金融float digestを追加していない。金融比較は既存rtol=2e-9／atol=2e-10を維持。descriptorや完了flagだけで数学をskipする方式ではない。

今回の実行は保存済み小N16/calendar24 source-unitだけ。N<=16・残step<=24のsaved SDEをガードし、新RNG／teacher生成を明示禁止。M6金融rawや大規模SDE/CF/PDEは再実行していない。原author fixture全filesの前後SHAも不変。独立prototypeの新transportは原保存値だけをwriter/readへ通したD内の検査用containerで、モデル値や原実験を作り直していない。作者17専用PASS／46 affected PASSは独立PASS数へ含めていない。

## 費用・保持した失敗

成功検査の外側 wall 33.411481659 秒、child CPU 33.393128000 秒、child kernel peak RSS 822591488 B（小source-unitの観測値）。初回は元からNaNの末尾cacheセルをNaN化したため反例が成立せずprobeがFAILした。元値NaNを確認し、有限セル→NaNへ訂正、初回script/log/cost/explanationを保持。source欠陥へ読み替えていない。両probeの測定済み包含費用は wall 58.563895359 秒／CPU 58.530274000 秒。探索/import/最終receipt・report保存のその他費用はunknown。

## 次の境界

新canonical source identityをrootの実closure／新予算へ結合した後、元M6保存rawの全N再検算・write/readを別承認部品として測定できる。本小NのRSS、通過時間、transport結果はN1024／N65536の実上限・金融精度・正式全容量／速度の資格へ広げない。旧M6の3実RSScap、原生成費用／失敗／unknown／source snapshotを保持する。

詳細：task-5-teacher-check-report-bounded-independent-v1-results.json、task-5-teacher-check-report-bounded-independent-v1-AST.json、task-5-teacher-check-report-bounded-independent-v1-parent-cost.json、task-5-teacher-check-report-bounded-independent-v1-decision.json。
