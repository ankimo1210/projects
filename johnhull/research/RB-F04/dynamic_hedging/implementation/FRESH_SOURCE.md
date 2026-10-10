# 独立再計算と保存checker — 限定source確認

2026-10-10。**fresh対象4 sourceの独立レビューapproved・未解決0。正式金融pilot/fresh/premium/main・研究受入は未完了。**

## 実装

reference_methods.py の独立CF/PDE・全13 S/Q再較正・768/1536 direct MCと、run_fresh.py/check_fresh.pyのimmutable実行・保存算術を接続した。原N/grid/seed・固定3width・16blocks・失敗/unknownを維持する。private計算関数に optional deadline_wall を追加し、親jobの実absolute deadlineを渡す。単一solver内部のhard cancellationは行わず、境界で停止し実overrunを残す。

typed local fieldの全parameterをsolver/RNG前に照合する。境界上の正当なunique rootは残し、固定central derivativeが計算できない場合はunknownとする。bump/domainを縮めない。CLIは実bundleのpayload/receiptを正しく取り出す。

source-staleを拒否し、元pretest planをposttest mainのreceiptで書き換えない。保存checkerはraw値からCF/PDE/refinement/root/cluster/Greek/費用を算術で再計算し、乱数や新solverを呼ばない。

## 独立指摘と修正

| 指摘 | 最終処理 |
|---|---|
| I1：typed field/evaluator parameter拘束 | 計算前に全parameterを照合 |
| I2：境界unique rootと固定derivative | 元13queries/Nを保持、未計算derivativeはunknown |
| I3：保存raw上限と親budgetの不一致 | effective budget/start/deadline・子残予算・実区間を親job/phaseへ結合 |
| I4：CPU時計欠落/NaNの費用認証 | 有限・非負start/stop/elapsed必須、elapsed再計算。wall-only capをCPU費用と区別 |

原request-changes、14failed/1passedのcap/cost RED、CPU非負の追加RED、最終修正・再レビューを原byteで残す。原rawをresealして修正成功にしない。

## 検証

| 検査 | 結果・範囲 |
|---|---|
| 著者専用scope | **82 PASS、41.29秒** |
| 独立専用scope | **82 PASS、41.85秒**、同suite再実行のため164件とは数えない |
| 変更Python4ファイル | Ruff check / format PASS |
| 独立actual source-unit | N1024・全13queries・paired768/1536・16blocksの新規immutable save/load/check/save PASS |
| 保存算術 | RNG/CF/PDE/direct MC/production teacherを明示禁止してPASS |
| 改変対照 | 元5＋内部整合wrong-parent-budget3変種、全8拒否 |
| 旧normal API | Heston/localのsamples/mean/SE/covariance/3widthの10比較allclose、観測最大差0 |
| source/raw保存 | 対象4 SHA前後不変、source-unit全registry前後不変、旧2rawのstale拒否・metadata不変 |

actual source-unitは合成metadataを使った小さい実金融算術のsource検査。正式元121case/51obligation・12fits・396件、全premium・earlier SDEの全raw再生・CAS復元・3図/notebook・全3suite・最終受入を示さない。比較ゲートの金融資格はunknownのまま。

[全source SHAと原証拠](fresh-source-evidence/files.json)。raw binaryは既存の管理外directoryに保持しreceiptを記録した。今回のsource確認だけで両CAS復元を認証しない。SHAは由来の照合に使い、数値をビット一致で判定しない。

## 次

正式pilot実行器とmainのchunk/保存算術を独立確認し、全jobの元入力・共通source・事前budget/cap scopeを固定する。実pilotの保存検算と独立結果レビュー後にpretest freeze、元12fits・主396件・fresh/全費用、両CAS/図/notebook/最終全suite・研究受入・main統合へ進む。
