# Task 5 execution runner final independent review

## 結論

**限定されたprivate runnerの入口・source provider・CLI配線を承認。**
Critical 0 / Important 0 / Minor 0。原I1・I2は解消。

- runner: bb7e7f6ecee12e56444ae24ced496328fcc5e1e1a142630f3fd985c94f3790d6
- tests: 65dd78525041e2fd75af25309265548413d2a9cabd9048e757fd2b43b0ea3b23
- A source: 473d1352fbcebd2c1255e093e1d4757274c7e51a04add5d6f00c58850c229494
- A tests / replay / B surfacesを含む全6bindingsは同名JSONに記録。全検証後も不変。

実run_fresh.pyは未実装のため、実execution入口は
`required execution source missing: run_fresh`でloader前に停止する。
正式pilot/freeze/mainが開ける状態とは承認しない。

## I1・I2の確認

I1: execution_source_identityは専用5入口の存在を明示確認し、全推移的importsを登録する。
旧run_main/tinyのsource_identity rootsは維持し、shared boundaryは入口ごとのproviderを使う。
未実装sourceを外部libraryとして黙って通すことはない。

I2: CLIもphaseごとのproviderを選び、execution-mainには専用registry、
mainには旧registryを渡す。source providerのみを合成registryに差し替えた単体検証で、
実Aguard/rawfit/validationを保持したexecution CLIがtrain→testの順で到達する。
旧main CLIは同じexecution-only freezeを厳格gateで拒否し、test loader0・保存0。

## 独立検証

- 対象runner suite: **39 passed in 28.10s**（process wall 28.991s）。
- 追加独立 **16 probes、unexpected 0**。
- Ruff check / Ruff format --check: PASS（対象2files、整形編集なし）。

16 probesは、実missing-source拒否、実Aguardとraw closureの合成正常到達、
candidate元N・frozen precision・source・rawfit元N・weights・prior checkpoint digest・
rawloss truncation・baseline救済・expense削除・closure bindingの10反例、
旧strict gate拒否、loaderによる6入力mutationからsnapshotの保全、両CLI入口の隔離を確認する。

全12fit attempt・4×14 validation candidateの原2048lossを保持し、全baseline None、
precision_selection unavailable、qualification unknownを保持した。
snapshot確認の18case×2universe=36評価はstudy mockと元N metadataによる単体検証。
実32768経路の金融計算ではない。

## 証跡と承認範囲

同名 .py / .json / .txt / -tests.txt / -ruff.txt に再現コード・6source SHA・原出力を保存した。
初回I1 review、I2 rereview/-cli原本と失敗probeも変更していない。
最初のprobeのexternal evidence SHA解釈を訂正した事実はI2 rereviewに記録済み。

成功probeはsource registry providerのみを合成証跡へ差し替え、Aguardは実装そのまま使用。
CLI artifact load/writeは合成fixtureで、source bytesの実証でも実金融freezeでもない。
probeの金融RNG・teacher・solver・trainは呼出禁止。suite内のtiny生成は既定の限定単体検証。

金融source・数学的精度・元教師精度・本物pilot/freeze/main・main generation/statistics・
Q/refinement・expense実測・fresh実装・CAS復元・main統合を承認しない。
保存/入力再計算の既存金融境界に追加の資格を与えない。source/Git/canonical docs変更0。
