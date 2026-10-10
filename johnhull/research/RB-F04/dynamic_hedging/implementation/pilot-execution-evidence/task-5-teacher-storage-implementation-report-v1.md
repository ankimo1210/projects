# 教師専用保存の限定実装

## 完了した範囲

native completed root teacher のみに固定 recipe を適用した。全 primitive・原 N/path/cluster/driver/calendar/threshold・全 summary/status/16block/covariance・外包を物理保存し、固定 11 sample fields を全 N×threshold で再構成する。原 raw を変更せず、writer は原全 label と比較、reader は独立保存した原 summary と比較してから、原 summary を保持したまま全標本を戻す。

金融比較は既存 runner._same の rtol=2e-9 / atol=2e-10。配列の shape/dtype、NaN/inf、文字列/status は保持する。SHA は原物理 primitive/summary/source/input/driver/receipt 由来の検査に使い、省略・再構成した 11 金融標本のビット一致には使わない。

- 新 helper: _teacher_storage.py。固定 source-bound primitive_labels recipe のみ。eval / arbitrary callable / dynamic import / generic dtype codec / bitpack は追加していない。
- run_pilot: root teacher 専用 write/read、compressed physical packs、明示 node binding。
- check_pilot: 旧 raw_sha256 と新 raw_binding を区別。既存 SDE/primitive/cache の数値検査は継続。
- protocol: private write_artifact に compress=False 既定の kw option。当該 teacher pack だけ True。展開 256MiB/parts/shape/dtype/receipt 検査はそのまま。
- 旧 completed literal、cap/source defect、nested teacher、他 artifact は従来全 payload/default 無圧縮を維持。
- 新 node は teacher_recipe_physical_v1 として root＋全 physical pack receipts/source/原返却 producer の物理由来を固定。別 producer/raw や未知kindへの差替えを拒否する。grid の literal cache/selector/adapter/resume producer/input SHA を緩めていない。

数学 / 原 N / 原 cases / whole policy / public init / 依存 / docs / Git / CAS は変更していない。production変更は指定4 filesと新test1 fileの計5 files。金融資格は unknown。

## 検査・証跡

- 初期 RED: 36 failed / 3 passed。初期 atom fixture の theta=0 は constructor が拒否する不正入力だったため、native local の zero field に修正した。保存 v56 writer に修正済み atom test を適用し、missing storage metadata の期待する RED を別途保存した。
- 原39 cases GREEN。追加 producer差替えの RED は 1 failed / 6 passed、物理 origin/input/driver binding を追加後 GREEN。
- 最終 storage46＋protocol54 = 100 passed。
- 既存 pilot 専用 191 passed（69.01s）。metadata selector / adapter / native Q / cap / resume の既存 source regressions を保持。
- main transport/resume subset 7 passed / 87 deselected、source closure subset 14 passed / 37 deselected。
- Ruff 5 files / format check PASS。
- runtime closure 81 files / dynamic imports 0。identity SHA: 4e8f8b7bad48b9f6bf89b655cd115de835a9a486d89dd6d9ffafcad2b3cb64b0。
- snapshot: task-5-teacher-storage-source-snapshot-v1/。AST delta/source diff、各 command の実 clock/CPU と失敗ログを D へ保存。
- 独立 review 用に合格済み N32 deterministic source test の native physical 5種類と old literal 1種類を D/task-5-teacher-storage-source-unit-fixtures-native-v1/へ固定保存した（6 selected tests PASS）。元 /tmp fixture は pytest cleanup で消えたため、同じ限定 test を D basetemp で保存した。新 RNG/CF/PDE/optimizer や正式金融ジョブは追加していない。

## 未検証・次

全3suite、正式 pilot/main、実 N65536 I/O、genuine N1024 whole教師、C/F 両 CAS、容量成立・金融精度は未検証。source独立レビュー後に root が事前承認した I/O部品計測と genuine whole教師計測へ進む。圧縮率や正式全体 runtime はまだ推計していない。
