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

[現行3,138-jobの独立metadata検査](pilot-execution-evidence/task-5-full-mixed-independent-preflight.json)は元121/51・15,281数値依存辺・final44/16・全seed/fee/Q/frequency/precision・actual descendant cap scopeを別実装で照合し、自己整合の改変14件を拒否。旧compiler v2のselector18states/12dates scope欠落はv3で修正済み。金融worker値・v54のA結合・正式lockは承認範囲外。

[固定v54原byte保管庫](pilot-execution-evidence/task-5-v54-root-checkpoint-cas-v2.json)は159 entries / 131,106,011 bytesをC/Fから別々に復元し一致。金融semanticは未実施。成功内側wall6.839343秒/CPU1.237617秒、parent-inclusive wall7秒台。先行v1の境界assert失敗と実測費用も保存、startup/authoringは未測定。

独立native Q検査で、元入力を削除するとSDE照合を回避できることと、元worker入力とraw.parametersが未結合の2境界を[実反例](pilot-execution-evidence/task-5-pilot-v54-independent-native-Q-results.json)として検出。v55で必須入力・locked producer結合を修正し、再レビューする。131件PASSをこの2境界の承認へ広げない。

## 正式lock前の残り

- conditional metadata bridgeとnative local Q修正を含む、現行金融sourceの独立確認。
- full mixed graphの独立レビュー、原入力/支持域/solver controlsの確定。
- 原work/expanded bytes・実測rate/事前予算・各実parent cap optionの固定。
- 現行10費用receiptの実測・inclusive会計、元失敗/unknown/historyの保持。

教師全20cacheを必要とする最大計算量は約1,295億path-stepで、保存後再計算やoracle等は別である。lower qualified停止と実capにより実仕事は変わる。これを所要時間や、金融資格が得られる保証として扱わない。
