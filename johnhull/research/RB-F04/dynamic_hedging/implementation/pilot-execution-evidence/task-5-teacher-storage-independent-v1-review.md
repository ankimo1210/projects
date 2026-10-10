# 教師保存形式 v1：限定独立レビュー

## 判断

**固定された codec の source / 保存 transport を限定承認する。** 正式 finance・容量予算・pilot/main・phase の受入は承認しない。金融資格は unknown。

独立の saved-only probe は **15 正例 PASS、60 改変・自己整合反例 REJECTED**。作者の 100/191/14/7 PASS は背景資料であり、独立 PASS 数へ加算していない。新 RNG・CF・PDE・SDE・金融 worker・全 suite の実行は 0。変更は D 内の検査証跡だけ。

## 固定範囲と数式

runtime 4 files と新 test の計 5 SHA を snapshot/current/検査前後で照合した。独立 snapshot を保存した。実 execution_source_identity は **81 files / dynamic imports 0**、identity **4e8f8b7bad48b9f6bf89b655cd115de835a9a486d89dd6d9ffafcad2b3cb64b0** と一致。

AST 比較で runtime 差分は新 helper、run_pilot の root write/read と grid node binding、check_pilot の node binding、private protocol の write_artifact のみに限定される。protocol は compress=False 引数と保存関数選択の **厳密な 2 置換だけ**で、候補 roster/元 N/seed/grid/case/obligation の定義は不変。金融 primitive_labels / SDE / CF / PDE の source は変更されていない。

固定 recipe は primitive_labels-global-driver-date-v1。全 primitive・元 N/path/cluster/calendar/driver/閾値・42 summary fields を物理保存し、固定 11 sample fields だけ省略する。再構成は同じ全 N、全閾値、16 blocks。f_samples は cv_samples の alias に戻る。

writer は省略前に全元 labels と許容差比較し、reader は保存済み原 summary の全 key/shape/dtype/status と再構成値を比較してから、原 summary を上書きせず sample fields を補う。金融比較は rtol=2e-9 / atol=2e-10。数値比較に再構成 sample の SHA 一致を要求しない。SHA は静的 source・物理保存 bytes・入力/driver/receipt の由来を認証する。

## 保存済み 5 種と互換性

N32・全6閾値 [-.25,0,3,6,8,30]、16 contiguous blocks の保存済み Heston/local ordinary、Heston invalid1path、local atom、Heston underresolved を読戻し・再保存した。

- 全 root/primitive/label key、配列 shape/dtype、NaN/±inf mask、全11標本、42 summary fields、block/joint covariance、全12step status を保持。
- invalid1path は全 N を維持し、全閾値 unknown_invalid_primitives を保持。atom/underresolved/linear の status を保持。
- 原 full returned teacher を writer が変更しないことを確認。新 pack は ZIP_DEFLATED。旧 completed literal は全 key/dtype と旧 raw_sha256 で読める。
- cap/source-defect と nested/unrelated teacher は全原 raw/unknown/未処理数を literal 保存し、従来 ZIP_STORED を維持。
- 原 fixture 36 files と固定 source 5 files は検査前後不変。

初期 author atom fixture の theta=0 は constructor が拒否する不正入力だった。修正済みの local zero-field atom と corrected-v56-baseline RED が保存されている。独立検査で使った atom はこの local fixture であり、Heston atom と誤記しない。

## 改変拒否と由来の伝播

60 反例は、元各11 sample の改変、保存原 summary 22 field の改変、recipe/source/manifest/shape/dtype/N/path/cluster/閾値/status encoding 等の19改変、別 producer/未知 binding kind、node root/pack digest 3改変、実 pack の metadata/NPZ/receipt 3 byte 改変。summary/scope 反例では物理 SHA と origin を改変側へ更新し、単なる内部 hash 不一致ではない数値・範囲境界による拒否も確認した。

root receipt と全 physical pack receipts、閉じた recipe source、元 returned producer の物理由来が teacher_recipe_physical_v1 binding を構成する。原 source/input/driver/summary を持たない別 returned producer への差替えは拒否する。未知 kind は旧 literal hash に fallback しない。1e-12 の sample 差は金融許容差内なら読戻し可能で、再構成 full payload SHA が異なっても物理 node binding は通る。

grid は新 binding を node に保存し、checker が node→raw を認証してから既存 SDE/primitive/cache 数値検査へ進む。selector/adapter/resume の producer/input binding 定義は AST 不変で、literal grid の node binding を包含する。独立検査は個別物理 node と互換性までの限定範囲で、正式 whole-grid/selector/resume の新金融実行はしていない。作者の既存専用 regression を独立承認として数えない。

## 実費と残り

独立 source probe：外側 wall **3.378153877 s**、child CPU **3.195890 s**、自己 RSS peak **635486208 B**。読取/準備/報告保存の未測定部分は unknown。I/O 候補 AST 検査の初回 reviewer assertion 失敗も別 JSON に保存し、source 欠陥と混同していない。

source approval は容量成立・genuine 全教師圧縮・金融速度/精度・正式 pilot/main/phase の承認へ拡張しない。全 N65536 の合成 I/O は別独立観測 decision に記載する。旧 v56 source と M0〜M5 観測・原失敗は保持した。

証跡：task-5-teacher-storage-independent-v1-probe.py/log/results.json/parent-cost.json/snapshot/。全 case と固定 SHA は results/decision を参照。
