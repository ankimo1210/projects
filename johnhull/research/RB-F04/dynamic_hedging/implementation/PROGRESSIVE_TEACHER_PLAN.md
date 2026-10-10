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

[root draftの実検査](progressive-plan-evidence/full-mixed-draft/task-5-full-progressive-pilot-plan-dry-run-v1.json)は3,138jobs・121ケース・51確認項目、実worker signatures/依存順序PASS。36stateと24dateには実選択stageのproducer/Nを結び、元market/fit/QのNは固定する。principal/next/grid/追加日付の8typed adapters、追加日付4件、最終all16比較、tiny4fits、全44cell、3precision候補を接続した。金融worker/RNGは実行していない。新compilerは独立レビュー前であり、段階選択の旧承認には含めない。

選択により元Nが変わる7確認項目（teacher_N/gridの4件、domain、frequency24/48）は、実adapter/selectorから元producerとNを認証する限定metadata bridgeが必要。自由な件数変更や、全候補を列挙して未使用仕事を混ぜる方法は使わない。

## 正式lock前の残り

- conditional metadata bridgeとnative local Q修正を含む、現行金融sourceの独立確認。
- full mixed graphの独立レビュー、原入力/支持域/solver controlsの確定。
- 原work/expanded bytes・実測rate/事前予算・各実parent cap optionの固定。
- 現行10費用receiptの実測・inclusive会計、元失敗/unknown/historyの保持。

教師全20cacheを必要とする最大計算量は約1,295億path-stepで、保存後再計算やoracle等は別である。lower qualified停止と実capにより実仕事は変わる。これを所要時間や、金融資格が得られる保証として扱わない。
