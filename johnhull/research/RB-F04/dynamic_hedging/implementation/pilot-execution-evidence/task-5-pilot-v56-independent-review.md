# v56 static import / source 封鎖の独立限定レビュー

2026-10-10。

**3 import置換とsource封鎖修復を限定承認する。** v55の保存Q・metadata限定承認を保持する。
開発source checkpointでは今回の固定v56/current main3 identityへ結合できる。
正式金融plan、pilot/main実行、budget、金融資格、phase受入は本承認に含まれない。

## 固定・変更範囲

- johnhull/research/RB-F04/dynamic_hedging/run_pilot.py: 4e4765f4bc7ae1cc0a7020fa3bb1fab1ad4eabec4e89fca511589cd5a799b829
- johnhull/research/RB-F04/dynamic_hedging/check_pilot.py: a36e691498a92a4e7ee13deb1f7a2f51e25b511e760ca7150fe814a83cb7f5a7
- deep_hedge_price/tests/test_dynamic_hedging_pilot.py: 0bb854a66ba5aad9174b036b90ed48683d10018930a560a609d5a2b10589e90b

- run_pilotはv55からbyte不変。
- checkerの変更はcheck_teacher_recordとcheck_resolved_job_argumentsの2関数のみ。
- __import__('hashlib')2件 → module-level import hashlib、__import__('run_pilot').unpack_inputs1件 → 関数内from run_pilot import unpack_inputs。
- 独立AST比較で、3 import置換を正規化すると変更2関数は等価。金融式、入出力、原N/seed/failure/capを変更していない。
- v55のtest/helper115定義はAST不変。追加は実source封鎖の回帰1件だけ。public APIやproduction dependencyの追加なし。

## 実source封鎖

実registered checkoutのreadonly moduleを使って_pilot_sourceと_locked_bindingsを検査した。
80ファイル・動的import0。別のAST走査で局所import405参照を解決し、未登録0。
v56 3本とmain3 3本の6固定sourceについて、実ファイル/保存コピー/SHAが一致。
80実sourceと固定3snapshotは検査中不変だった。

source identity objectは作者inventoryと一致。
inventoryのcompact sorted JSON SHAはb04ce2e63dce80eb17e5dae917369e04d661c6dba0d3dc6a08e7178da2610688。
_locked_bindingsのpayload_digestは別のcanonical表現でa99fe94579d0cbd280f8908d1db539f5c7f0b03cd4a42a59896f586f4fe9072c。
2つのdigest方式を混同しない。source bytesの差異ではない。

旧v55のdynamic3を含む保存identityを同じguardへ渡すと拒否。locked source SHAの差替えも拒否された。
保存mixed graphは3138jobs/28operations/原121cases・51attemptsで、実dispatchの37対応operationsに収まる。
これはsource欠落/typed operation対応の検査で、金融workerの数値branchが正しいという承認ではない。
保存draftのformal_plan_lockedはfalseのまま。旧checker v54を記録したdry-runを上書きしていない。

## 既存証跡を使った再検査

- 37限定metadata/control tests PASS、154 deselected、pytest1.79秒。全191は再実行していない。
- 元v54保存Q4件を再使用（Heston/local×正常/失敗、N32の解析toy call cache）。保存normal SDE再計算、原入力結合、独立cash式はPASS。
- 元105 counterexamplesをそのまま再検査し、全拒否。
- native cap入口2件はNoDraw sentinelで実時計cap。追加RNG0、新金融path0、原N/未実行mask/unknown保持。
- v53/v54の元失敗、v55限定decision、作者RED191・元source closure失敗は保持する。作者191 PASSを独立37へ加算しない。

## probe失敗と費用

初回はfixed snapshotのpathからrun_pilotをimportし、実registered checkoutのmodule originと違うため
loaded source differs from registered checkout: run_pilotで拒否された。
source封鎖が正しく機能した結果。原script/log/親時計を保持し、例外を回避せず、
実source6本がfixed copiesと同じSHAであることを確かめてregistered pathから再検査した。
初期summary読取のjson import欠落もprobe側の小失敗として記録した。

- static: parent subprocess wall 2.673484715秒、exit 1。
- static-v2: parent subprocess wall 5.553719062秒、exit 0。
- native-saved: parent subprocess wall 1.743970140秒、exit 0。
- tests: parent subprocess wall 3.650219188秒、exit 0。

測定済み4子process区間合計は13.621393105秒。未測定の読取・準備・報告時間を含む全費用はunknown。

source/docs/Git編集なし、正式金融実行・全suiteなし。
今回のregistry、短いsource-unit検査、allocation component観測を全teacherのRSS・速度・価格精度へ転用しない。

証跡はtask-5-pilot-v56-independent-{static-v2,native-saved,tests}のscript/log/results/parent、
fixed snapshot、v55との差分、decision/manifest。元Q artifactとv55 decisionは不変。
