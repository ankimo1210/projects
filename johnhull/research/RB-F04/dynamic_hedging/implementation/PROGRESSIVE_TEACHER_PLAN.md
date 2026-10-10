# 段階教師選択と最終mixed pilot計画

2026-10-10。正式pilot/freeze/mainは未実施。metadata構造の承認を、金融source/精度・予算・正式lockの承認へ広げない。

## 独立確認した段階選択

[独立判断](progressive-plan-evidence/progressive-preflight-decision.json)・[レビュー](progressive-plan-evidence/progressive-preflight-review.md)はselection-only metadataとして承認、Critical/Important0。元N1024/4096/16384/65536とcoarse/highの順序を保持する。

| 項目 | 保存済み計画の件数 |
|---|---:|
| 実依存を持つjobs | 2,748 |
| 教師候補stage | 16 |
| 原18状態×両modelのstage照合 | 288 |
| 原12日付×両modelのstage照合 | 192 |
| Greek/bandのpaired比較 | 1,792 |
| 元pilotケース / 確認項目 | 121 / 51（この時点では最終投影はpending） |

各stageは自modelの候補を変え、他modelの基準教師は原N1024/coarseで固定する。次の原Nを参照に使い、最大Nだけは元reserved独立streamを使う。同じ実driver/教師を共有するが、別modelのgateで高Nを誤って活性化しない。選択後に最終mixed比較を再実行する。stageではNNを学習せず、tiny4fitsは最終選択後に一度行う。

count/signature/topologyだけのroot検査は自己整合の改変10件を通してしまった。独立guardは同10件を拒否し、cache/base-refined/model、seed/N、oracle、幅、共有driverのactivation、field、121/51の同一性を確認した。この結果はbasic dryrun単独で正式lockを承認できない根拠である。

[保管庫manifest](progressive-plan-evidence/progressive-preflight-root-cas-manifest-v2.json)は46 entries / 51,908,416 bytes。両copyの原byte復元PASS、金融semantic実験は未実施。成功内側wall1.713678秒/CPU0.407651秒。元一覧の重複pathを再追加した先行失敗はscript/logを保持し、費用未測定を残した。

## 最終mixed計画の接続中

[root draftの実検査](progressive-plan-evidence/full-mixed-draft/task-5-full-progressive-pilot-plan-dry-run-v1.json)は3,138jobs・121ケース・51確認項目、実worker signatures/依存順序PASS。36stateと24dateには実選択stageのproducer/Nを結び、元market/fit/QのNは固定する。principal/next/grid/追加日付の8typed adapters、追加日付4件、最終all16比較、tiny4fits、全44cell、3precision候補を接続した。金融worker/RNGは実行していない。新compilerのmetadata独立検査は下記。金融source・予算・正式lockは旧selection-only承認に含まれない。

選択により元Nが変わる7確認項目（teacher_N/gridの4件、domain、frequency24/48）は、実adapter/selectorから元producerとNを認証するbridgeを実装。case/date/refinementには実control仕事を含め、selector自身の実wall capでも元N・失敗・子の数値未実行を保持する。[固定v54検査](pilot-execution-evidence/task-5-v54-root-source-verification-v2.json)は131件PASS（57.62秒）・3Python Ruff/format PASS。旧fixture2件に必須kindが無い失敗と、selector引数喪失の原traceを保存した。 [独立control cap検査](pilot-execution-evidence/task-5-pilot-v54-independent-control-cap-v4-results.json)も両modelの実wall cap・元N65536・case/dateの同じparent・子数値未実行・独立job続行・saved resumeを確認（state/date数値checkerはmetadata stub、金融資格unknown）。自由な件数変更や全未使用候補の混入は認めない。

[現行3,138-jobの独立metadata検査](pilot-execution-evidence/task-5-full-mixed-independent-preflight.json)は元121/51・15,281 typed producer参照（controlを含み数値仕事量ではない）・final44/16・全seed/fee/Q/frequency/precision・actual descendant cap scopeを別実装で照合。[補足の独立判断](pilot-execution-evidence/task-5-full-mixed-independent-review.md)はphysical teacher48件と全semantic cap scopeを確認し、自己整合の改変計25件を拒否。旧compiler v2のselector18states/12dates scope欠落はv3で修正済み。金融worker値・v54のA結合・正式lockは承認範囲外。

[固定v54原byte保管庫](pilot-execution-evidence/task-5-v54-root-checkpoint-cas-v2.json)は159 entries / 131,106,011 bytesをC/Fから別々に復元し一致。金融semanticは未実施。成功内側wall6.839343秒/CPU1.237617秒、parent-inclusive wall7秒台。先行v1の境界assert失敗と実測費用も保存、startup/authoringは未測定。

独立native Q検査で、元入力を削除するとSDE照合を回避できることと、元worker入力とraw.parametersが未結合の2境界を[実反例](pilot-execution-evidence/task-5-pilot-v54-independent-native-Q-results.json)として検出。固定v55は必須入力・locked producer結合を修復し、[独立レビュー](pilot-execution-evidence/task-5-pilot-v55-independent-review.md)で限定承認。190専用tests/Ruff PASS、独立37件PASS、旧保存4件を新RNGなしで再使用し105反例を拒否した。既存131tests/helperは保持。原N32のsource算術を金融精度・正式pilotへ転用しない。

## 正式lock前の残り

- conditional metadata bridgeとnative local Q修正を含む、現行金融sourceの独立確認。
- full mixed graphの独立レビュー、原入力/支持域/solver controlsの確定。
- 原work/expanded bytes・実測rate/事前予算・各実parent cap optionの固定。
- 現行10費用receiptの実測・inclusive会計、元失敗/unknown/historyの保持。

教師全20cacheを必要とする最大計算量は約1,295億path-stepで、保存後再計算やoracle等は別である。lower qualified停止と実capにより実仕事は変わる。これを所要時間や、金融資格が得られる保証として扱わない。

## 現source封鎖と資源（2026-10-10）

v55の動的import3件が正式source封鎖を妨げることを実検査で確認し、[v56 source封鎖](pilot-execution-evidence/task-5-formal-pilot-source-closure-v56-main3.md)はhashlibとunpack_inputsを静的importへ置換するだけで修復。191専用tests/Ruff PASS、80実source・dynamic import0、既存115test/helperと金融ロジックを保持。[独立限定承認](pilot-execution-evidence/task-5-pilot-v56-independent-review.md)を完了。旧v54 sourceを記録したdraftは保存し、正式lockで現identityへ再結合する。

初期37quoteの現在fieldは同dxの幅2.4を追加計測し、価格/幅差を独立保存算術で確認。全20最大gridの現sample保存下限1.44TiBはvolume空き560.8GiBを超える。既存1e9 capは子計算で全20を許容し、[独立資源候補レビュー](pilot-execution-evidence/task-5-formal-controls-review-report.md)でも全体storage上限の代わりにならないことを確認。全候補を保持し、whole-storage予算/revision・実worker rates/bytes・10費用receipt・A cap optionsの確定が正式pilot前に残る。


## 現在の教師保存source（2026-10-10）

教師専用primitive recipeとphysical node bindingを限定実装し、現在closureは81files/dynamic0。元数学/N/casesを変えず、全primitive・元16block/stat/statusを保持する。100 storage/protocol・191 pilot・14 closure・7 main transport/resume tests、Ruff/format、独立15正例/60反例がPASS。全status付き原N65536/65thresholdの合成I/Oも独立保存検査PASS、外側wall10.928秒・peakRSS3.467GB。詳細は[予算測定](PILOT_BUDGET_MEASUREMENTS.md)。旧v56 source80の原測定/失敗/unknownを保持する。圧縮率はgenuine教師のbudgetへ転用せず、正式lock/volume budgetは未承認。原N1024四class/2,128節点を元共通driver二本で実測し、全生成rawを保存した。Hcoarse検査完了・他3classは検査工程の実RSS cap、外側wall1,401.807秒を保持。現在は全Nのsaved SDE/label/cache比較を維持するboundedレポート修復と元raw保存再検算へ進む。M7の元N4096/13queries/2schemeの事前候補は準備済み・金融未実行。全phase予算/正式lockは引き続き未承認。
