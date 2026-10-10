# 外部10費用と元receiptの対応台帳

2026-10-11。**全10費用は未閉鎖、金融判定は unknown**。閉じた7件のmetadata・proof・限定レビューreceiptだけを参照した。production/source82、live pilot、raw、許可、Git、CASは変更していない。

この台帳は対応資料であり、native checkerへ投入する外部費用event rowsではない。現行run_pilot snapshotには外部費用集約event rowsがなく、投入は未対応。全範囲の wall_seconds / cpu_seconds と4つの start/stop nsは **None**。durationやUTCから端点を作っていない。

## 原10 ID（正本の順序）

| ID | 既存の部品証跡／欠測 | 閉じるためのproducer |
|---|---|---|
| cold_imports | 専用の元import時計なし。enclosing時計への包含も分離不可 | 元source82のcold bootstrap/module load実時計 |
| source_registry | R1のsource/input検査に包含。単独時計なし | 元82source・typed入力・locked planのregistry検査event |
| code_review | R5/R6のhelper限定probe。全レビュー・outer/tail不明 | 原金融source/protocolの独立レビュー全工程event |
| math_review | この集合に全数式レビューreceiptなし | 元モデル・scheme・推定量に束縛した数学レビューevent |
| pilot_review | R7はprior metadataの構造確認。全pilot数値レビューではない | 終了後、元全roster/native/source/inputに束縛した独立レビュー |
| serialization | R1のmetadata writerに包含。金融raw/checkpoint/final resultの単独全時計なし | 元全payloadのwrite/read/最終receipt時計と包含関係 |
| saved_check | R3は準備proofのCAS。実数値検算は未実施 | 終了・root許可後の全hydration/replay/保存/readbackを含むobserver |
| CAS_primary | R2/R3/R4は両保管庫合計のmetadata/proof時計。金融raw全体・primary専用時計なし | 原金融closed corpusのprimary保存・認証・必要復元実時計 |
| CAS_mirror | 同じ両保管庫合計時計。金融raw全体・mirror専用時計なし | 同じmanifest/corpusのmirror保存・認証・必要復元実時計 |
| domain_selection | 閉じた専用外部event未参照。live selector/kernelを未読 | 原N/grid/driver/選択raw/親に束縛したselector実時計・alias |

**正本**：check_pilot.py:1622–1635 は wall/cpu の integer start/stop nsとduration一致を必須とする。1781–1807 は全required ID、重複、欠測を検査し、4545–4557 はcurrent IDのcomplete/failed状態と実eventsを要求する。DESIGN.md:339–345,350–355,411 の全費用・包含・原義務は維持した。

## 時計と包含

| 元ref | 原keyと値（秒） | 境界・包含 |
|---|---|---|
| R1 | wall_seconds=97.25502551400132; parent_CPU_seconds=0.161982783; children_CPU_seconds=94.993546 | metadata生成全体（source/input・cap展開・writer・manifest）。registryとserializationへ各々全量を加算不可。最終receipt/stdout費用 None |
| R2 | wall_seconds=19.749798559998453; process_CPU_seconds=0.39302102 | 新prior metadata＋proofの両CAS合計。receipt最終writeは未観測 |
| R3 | elapsed_seconds_before_receipt_write=1.1758773649926297; CPU_seconds_before_receipt_write=0.046353993 | saved-check準備proofの両CAS。tail unknown。旧v1失敗費用は再加算なし |
| R4 | elapsed_seconds_before_receipt_write=6.687689614002011; CPU_seconds_before_receipt_write=0.0896268 | terminal-byte helper proofの両CAS。tail unknown。実nativeなし |
| R5/R6 | R5 wall_before_result_write=0.05114637299266178; CPU_before_result_write=0.036744126。R6は同値を probe_* で参照 | 同一probe1件。二重加算不可。helper source/mechanics限定で、全code/math/pilotレビュー費用への読み替え不可。outer/tail unknown |
| R7 | script_inclusive_wall_seconds_before_receipt_write=19.498324011001387; script_inclusive_CPU_seconds_before_receipt_write=19.364342044999997 | 独立metadata確認はR1と別attempt。内側のR1引用は追加費用ではない。enclosing wall/CPU・full review/tail None |

両CAS合計をprimary/mirrorへ全量二重配賦したり、半分ずつと推測したりしていない。R7のtool waitはprocessのenclosing wallではないので加算しない。**proof/metadata CASと全金融raw CASを区別**し、費用総額・ETA・精度達成は主張しない。

## 元ref一覧

- R1: [parent-cost-and-status.json](/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec/task-5-formal-prior-lock-materialization-root-observation-v3/parent-cost-and-status.json)
  - SHA256: 94a8bd84a5587cbd7862c77b0cacc10b847ea0d8e7d0e81211c66fffc31ce733（1463 bytes）
- R2: [root-new82-prior-metadata-and-closed-proof-store-receipt-v1.json](/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec/root-new82-prior-metadata-and-closed-proof-store-receipt-v1.json)
  - SHA256: 6a84c665b4d7c896ea6271f9b9410690f99a7878525d861a0c968eadc7b785a3（1545 bytes）
- R3: [root-saved-check-preparation-closed-proof-store-receipt-v2.json](/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec/root-saved-check-preparation-closed-proof-store-receipt-v2.json)
  - SHA256: 2fdc63f03ee07aabd66a1324a0fc3af2789f0d96d6d7c1b166ad490f7df43f58（1077 bytes）
- R4: [root-terminal-byte-helper-closed-proof-store-receipt-v1.json](/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec/root-terminal-byte-helper-closed-proof-store-receipt-v1.json)
  - SHA256: 063d086609412ddfb4fb35da119aa4b64a2462582b8aee8abde43168c949d5d7（1074 bytes）
- R5: [independent-terminal-byte-helper-v2-results.json](/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec/independent-terminal-byte-helper-v2-results.json)
  - SHA256: 186b291152200e5c4a7e6725fedd1698a3bf235d492d9fe54e8ab259f73e6427（4437 bytes）
- R6: [independent-terminal-byte-helper-v2-decision.json](/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec/independent-terminal-byte-helper-v2-decision.json)
  - SHA256: 49beef645c167862a7740214eb20627422c208903265551fe6cbb83221da6359（2422 bytes）
- R7: [independent-materialized-prior-v5-tool-enclosing-receipt-v1.json](/home/kazumasa/worktrees/johnhull-storage-codec/.superpowers/sdd/2026-10-10-dynamic-storage-codec/independent-materialized-prior-v5-tool-enclosing-receipt-v1.json)
  - SHA256: 6f2a694bd9d7f4fe6c948350cf9512ebe4db467236e00252ef9538774090d532（1731 bytes）

## 検証・次の作業

7件の元byte SHA、10 IDの順序、None/unknown保持を確認。source5ファイルの固定SHAも一致。新tests・金融・CAS操作は0。JSONに原clock key、scope、包含、将来producerと必要raw clocksを保存した。

終了後の実費producerが、元scope/source/input/plan/receiptに結合した **実端点** とstatusを出すことが必要。実現していないevent rowをこの台帳で補完しない。既存root guard/capの承認は追加していない。
