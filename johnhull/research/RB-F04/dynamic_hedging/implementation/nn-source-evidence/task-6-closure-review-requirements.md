# Task 6 closure initial contract audit

source/testが変更中のため、最終findingや承認ではなく必要な反例の整理。
最初に読んだsource/test SHA、capture時の全7bindingsはJSONに記録。

- 全12slots/G2/U2/init11,29,47、train8192/validation2048、requested512を固定。
- fit_rosterのvalidation_status=not_runを完了へ投影しない。全12固定checkpointをNN holdoutで別評価。
- raw optimizer identity、6weight shapes、train-only scaler、batches/events/last-finite checkpointを保持。
- completed/raw completed/512済みでもconnector elapsed>300ならtime_cap失敗。weightsは診断用に残す。
- 有限P&Lでもmarket/全original pathがunknownなら失敗。全failed baselineはNone、部分分母へ削らない。
- optimizer/source/shape/solver defectを4許可failure_kindへ変換しない。
- study raw費用はflat/completed。A用ledgerへのnormalization、timing3keys、親子scopeは明示し、0捏造をしない。
- rate/fees/calendar/fixing/memory/payoff規約が原candidateと整合する入力境界を確認。
- 保存checkerのcandidate照合からSeedSequenceへ辿る経路も禁止されたtestを維持する。
- 最終policy/scaler/train P&L/2048 validation loss/masks/cashを再計算しても、過去optimizer履歴や実RNGを認証したとは言わない。
- 一括メモリreturnだけではfit境界のディスク保存/resumeを実装済みとclaimしない。

現時点のscoped suiteは未実行。source安定後に独立数値probeと専用testsを実施する。
元Task5 review/measurement証跡を変更していない。source/docs/Git変更0。
