# 正式 pilot producer 事前設計レビュー

**判定: request changes。正式 lock / 金融実行の開始は未承認。** Critical 0、Important 4。2026-10-10。

## 確認結果

- 実原18states、月次24queries、1/24・1/48追加代表例を保持。
- 独立RNG禁止 dry-run: **121 cases / 51 attempts / 532 jobs**、worker signature 0 errors、DAG順序正常。
- 全532 raw cap_scopeをDAG子孫とcase/attemptへ独立照合。欠落0。独立親capの伝播は実装済み。
- 高N financial child identityは作者修正後にメタデータのみで確認。Heston high156/local high1344 children、各N65536 child=50,331,648 path-steps<=1e9。
- 構造PASSは金融精度、最小qualified N、正式pilot/main完了の認証ではない。raw closedもA lifecycle closureの代替ではない。
- 金融MC/PDE/教師/学習、正式lockは実行していない。コード/Git/正本docs/原raw・receiptを変更していない。

## I1: 段階選択・higher-N oracle・残りprefix閉鎖

監査draftの実teacherは両MそれぞれN1024/coarse、N4096/coarse、N1024/high。N16384/65536はmetadataのみ、独立oracle36件は全てN1024。selected_teacher_trialは計算baseでありqualified選択証拠ではない。

元ordered4Nを予約し、全原case/fullN/16blocksで実precisionを評価。必要なnext prefix、coarse/high、higher-N独立oracle(all13queries/3幅/768+1536)を実行する。未実行prefixは真正な下位qualified証拠又は独立事前承認budget/teacher revision＋actual parent cap費用へ結合。metadataや自由記述だけで実試行と数えない。failed/unknown stateを除外して最小Nを選ばない。最高N未達はunknown/revision、N262144や閾値緩和は不可。全N×全gridの無条件直積は要求しない。

## I2: Aの全121case/51groupへの費用・上限写像

raw quote original_n=37に対しA各quoteは1。raw37を保持してaliasへ写す。全51 attempt_planはoriginal_n欠落。prior plan・raw parent・N・expense_id・cap・first_failure_date・candidate/source/domains/plan/record verificationの再結合が必要。

全121+51にdistinct実inclusive expense alias、shared親はincludes_children forestで二重加算せず全独立capを保持。actual parentが1800秒cap到達なら0秒inspectionをcase費用に流用できない。

必須10現行external費用: cold_imports, source_registry, code_review, math_review, pilot_review, serialization, saved_check, CAS_primary, CAS_mirror, domain_selection。raw worker時計は保存前に終了するためserialization/check/CASのactual interval wall/CPUは別計測が必要。

root入力準備JSONのelapsed wall/CPUはinterval endpointsがなく、正式expense認証へ転用不可。歴史unknownを0へ書き換えず、未測定のspeedup/paybackを支持しない。

## I3: 正式controls・domain・bytes・予算

監査draftは532 expanded bytes=None、budgetなし、全date domains=None、initial PDE stages=[]、call dates月次13。source dry-run placeholderである。

元49date call supergrid、37quotes、元CF/PDE/refinement controls、pilot-only finite contiguous box決定規則、全child work/expanded boundary bytes、全jobの事前独立予算を固定後lockする。domain未支持ならunknownを保持するが、未検査の全Noneを最終選択にしない。

24/48は元追加代表dateとselected Greek/band診断scope。欠けた追加日時をunknownと表示する場合、完全24/48価格・経済比較成功とは呼ばない。全24/48teacher格子やNN再訓練へscopeを広げる指摘ではない。

## I4: 4fit空gate（root限定修復担当）

現Aは空gates/measurementをvacuous Trueにし、optimizer completed＋validation unknownの真のrawをmeasured_precision_failureへ写すと拒否。一方空measurementのみのqualifiedを数値gateで止められない。

4fitのみtyped fit_validation receiptを要求するroot案は妥当。prior training/validation N、fit ID、raw evidence SHA、first_failureを再結合。qualified/unknownはcheckerが実raw validationから再算術し、flag改竄negative testsが必要。実行completedと金融gate失敗を混同しない。strict v1、非空numeric gates、empty attempts、cap/構造拒否は維持。最終修復SHAの再レビューが必要。

## 事前予算候補（まだ正式承認不可）

詳しい数式・全元Nの候補表・実測SHAは task-5-formal-plan-preflight-review-budget-policy.json。

- 原4Nを予約し、実N1024/4096、元coarse/high、必要なhigher-N oracleを計画。未実行の義務閉鎖は別認証。
- teacher旧whole-child実測82,247,680 steps/45.11710144 sec=1,822,982.36 steps/s。元全node/date条件付きworkの3倍、300秒単位へ切上げ、最小300秒候補。別driver/IO/check/CAS費用追加。現正式sourceの実測速度ではない。
- local coarse N65536計算cap約6.33時間、local high約15.92時間。**capは所要時間ではない**。
- 高grid両M refit+analytic Asian平均1.461msから両M2ms/path/date/queryを保守的候補floor、3倍。12date risk component cap: N1024=300s、8192=600s、16384=1200s、32768=2400s。13queries N1024=1200s。whole-worker/IO別。
- 実query平均はunknown/no_root早期returnを含む。診断bumps(.05/.01)は正式(.02/1e-4)と異なる。実訪問state/教師/MC/統計精度/正式wall未測定。floorと係数で未測定が消えるわけではない。
- 49date call componentは6date実測の49/6換算＋余裕で両M各300s候補。正式controls実cost未測定。
- 独立direct oracleへteacher旧rateを実測oracle速度として流用しない。job-specific独立事前見積もりとoriginal-N観測が必要。未確定を隠した全budget mapは作れない。
- expanded境界<=256MiB、child work<=1e9。driver/primitive/status/16blocks/serializer全量、総保存bytesは別。
- phase capで独立tailを閉じるならactual enclosing phase-parent時計と全子孫bindingが必要。現per-job DAG capだけでphase時計を製造しない。

## 開始・終了時刻の見通し

実験開始前の実装・専用tests・独立再レビューは**2–6時間程度**の粗い見積もりで、約束ではない。金融runtime未測定。旧速度換算local high N65536教師約5.29時間、全4N coarse両M約3.37時間（必要時のみ、oracle/IO/学習別）。高N/複数格子が必要なら半日以上の余地があり、全体完了ETAは固定できない。

## 証跡・並行変更の扱い

dry-run.jsonとimmutable draft-source-unit: RNG禁止構造検査。audit.json: 原counts/N/input/A不足。cap-scope.json: 全532独立照合。decision.json: 監査SHAと終了時snapshotを分離。budget-policy.json: 実測SHA・候補数式・未測定。

作者の並行整形/修正でsourceが変わった場合、旧監査SHAの結果を自動転用しない。最終source停止・SHA固定後、full original-budget dry-run/negative tests/saved-only再レビューが必要。
