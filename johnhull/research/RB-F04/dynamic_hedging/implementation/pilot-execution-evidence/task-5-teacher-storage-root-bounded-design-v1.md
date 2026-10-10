# 教師専用保存表現の限定実装方針

2026-10-10。研究9の元科学条件、全N、全case、全teacher grid、全primitive、全16block、元failed/unknownと全返却payloadを保持する。金融精度や正式pilot/mainを承認する文書ではない。

## 採用する実装範囲

root native completed teacherだけを対象に、明示された10種類の派生N×threshold標本とf_samples aliasを全primitive＋元thresholdから復元する。元全summary/status/16block/covarianceと外包は物理保存する。新規金融model、数値閾値、公開API、依存は追加しない。cap/source defect/未実行は従来literal表現で保存。既存literal全配列artifactをそのまま読める。

限定private helperは研究ディレクトリの _teacher_storage.py とし、必要なrun_pilot.write/read/node binding、check_pilotのnode binding、private protocolのcompress=False既定オプションへ接続する。他artifactの保存方式は変えない。protocolがtyped書式をそのまま圧縮保存する場合、NPZの展開chunk上限・全shape/dtype/parts/receipt検査は維持する。

## 原数値と由来の境界

1. writerは元rawを破壊せず、完全なprimitive、元path順/元N、threshold、blocks=16から原全labelを再計算する。global driver IDとdate_indexの既存metadata操作を明示し、全原標本・alias・summary・status・covarianceをshape/dtype/NaN/infを保った許容差付き比較で検査してから固定11fieldsだけ収納上省略する。欠落、不整合、未知recipeは拒否する。
2. readerは固定recipe/version/source bindingだけを許可。arbitrary callable/eval/dynamic importは禁止。全物理primitive/元summaryを読んで全N×threshold標本を再構成し、独立保存した元summary/status/16block/covarianceへ許容差付き比較する。保存summaryを再計算結果で上書きして自己一致を作らない。全旧payload key/値/shapeと原未知性を返す。
3. byte/source/input/driver由来はimmutable receiptへbind。新teacher nodeにはphysical artifact receipt binding kindを明示して物理由来を検算する。再生成された金融floatの全payload SHA一致を合否に使わない。旧literal nodeは旧bindingで互換を保持。node -> grid -> selector -> adapter/resumeでbinding種別が維持されることを確認する。
4. 原saved-driver SDE -> primitive、primitive law/control/失敗診断、全cache/Greeks/covariance検査を残す。単なるlabel再構成をSDEや金融accuracy検証と呼ばない。量子化/float32、成功path抽出、平均だけの保存、部分Nの救済は行わない。

## 検証と実装順

- source前にscoped failing testsを書く。全種類標本/原summaryとstatus、linear/atom/underresolved/invalid1path、原N/CRN/path順、旧literalと新表現、原cap/source defect保存、readonly元dictを確認。
- writer標本変更、alias変更、reader原mean/block/joint covariance変更、未知recipe/source/dtype/shape、missing/extra/parts、receipt/binding変更、scope縮小を拒否する意味ある反例を追加。
- scoped tests + ruff/formatを実行。既存pilot/mainのnode/selector/resumeに影響する範囲を確認し、関係ない全suiteは実行しない。最終全3suiteはphase受入で1回。
- 80 -> 新closureの全runtime sourceを確認、動的import0を保ち、限定source独立レビューを受ける。
- 原N65536・65threshold・全65536×768status・16blocksのnative I/O部品計測でcombined RSS/write/read/再構成費用・物理/展開bytesを測る。genuine N1024 whole教師と測定を共用して確認し、C/F各1copy＋WSL原本/復元の同時占有を別volumeで予測する。

## 未確定

元全20gridのmandatory primitive/統計/共有driverの展開下限は353606441728 bytes。C空き340566458368/F空き185710804992/WSL空き601683951616 bytes。圧縮で収まる比やstorage budgetは実測・独立確認まで主張しない。個票の跨環境微小差は金融許容差で扱い、元sample byte完全復元保証とは呼ばない。

参照: task-5-formal-storage-options-review.md、task-5-teacher-primitive-storage-independent-math-boundary-v1.md。両静的調査は条件を整理したもので、実装・金融資格・正式予算を承認していない。
