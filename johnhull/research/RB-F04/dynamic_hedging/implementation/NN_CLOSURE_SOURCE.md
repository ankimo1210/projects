# 12本の学習・検証の接続 — source確認

2026-10-10。限定source承認済み。正式pilot、金融精度、実験freeze、main実行・研究受入は未完了。

## 実装範囲

- Private `deep_hedge_price._dynamic_hedging_closure:training_validation_closure`：元candidateの2生成モデル×2取引集合×3初期値、計12本を8,192経路・512更新で試みる。学習用scaleだけを使い、固定last checkpointを元2,048検証経路で評価する。
- Private `deep_hedge_price._dynamic_hedging_closure:check_training_closure`：保存した重みからNumPyの保有量・cash・元損益を再計算し、12本のNN検証と4集合×14候補のbaseline選択を照合する。fit、optimizer、teacher、乱数生成を開かない。
- 原path IDs、月次12fixing、payoff、金利0.03、half-spreads、train/validationの予約seedとdriver IDを照合。premiumはcallerが渡した共通の事前選択値にbindする。その独立推定・byte由来の認証はcallerの責任。
- 有限な損益でも資格unknownならcheckpoint/baselineを選ばない。失敗NNをno-hedgeや直前保有で置き換えない。
- optimizer/source defectはunclosed。観測された非有限入力、元300秒cap超過、未支持の学習・検証は理由とrawを保持する。connector capでouterがfailed・rawがcompletedの場合もraw重みを消さず、選択から外す。
- training12件・NN検証12件・baseline選択4件、計28件の実費用を別scopeで保存する。原inclusive training時間とraw時間・cap・overrunの整合を照合する。baseline内の14子rolloutを親費用へ二重加算しない。
- checkerの金融 `qualification` はunknown。NN/baseline検証の算術上の資格を別名で返す。過去optimizer履歴や実RNG由来を認証したとは主張しない。

## 検証

| 検査 | 結果・範囲 |
|---|---|
| 著者のscoped tests | 38 PASS、45.24秒。初期3 RED、追加のscale/identity/保存replay/数式・cap・費用反例のREDを保持 |
| 独立scoped tests | 38 PASS、46.13秒 |
| 独立追加probe | 6群PASS、16.30秒。非ゼロstock/call保有の独立手計算cashとの差は最大5.28e-14。全12 unknown、56baseline全None、unknown学習の有限raw保持、cap、source defect、seed・scale・checkpoint反例、RNG/optimizer禁止replay |
| 索引/docstring | 1,129 PASS、2.27秒。以前のguard件数と足し合わせない |
| 変更Python2ファイル | Ruff check / format PASS |
| 最終sourceレビュー | Critical / Important / Minor各0。宣言したsource・保存算術の限定承認 |

## 元件数での実runtime（合成のsource検査）

実optimizerを使う12本すべてが8,192経路・512更新を完了。各NNを2,048経路で検証し、4×14baselineを実cashで計算した。全体34.512秒。データは決定的な合成検査用経路で、Heston/localの正式市場シミュレーションや金融精度の証明ではない。

最初の一括保存は256 MiB上限で失敗し、rawメモリはterminal例外で失われた。残る観測記録と旧scriptを保持し、完全な費用やrawを保存したとは主張しない。次の分割保存probeは別試行として測定した。途中のimport失敗もlogに残す。

分割probeは元配列を保持して書き込み・読み込み・checkerを完了。ローカルrawは `.superpowers/sdd/2026-10-09-dynamic-cross-model-hedging/task-6-full-count-unit-runtime-split/` に保持する。実expanded bytesは608,050,240、receipt chunksは3,270、最大chunkは1,769,600 bytes。原256 MiBの制約を拡張していない。rawはsource-unitのローカル資料で、このsource checkpointへは含めない。

実学習はsource `5ea85d5e...`、最終cost guardを加えたcheckerはsource `c34a9aab...`。同じ保存rawを最終checkerで4.160秒に再検算し、fit/optimizer/default_rng/SeedSequence禁止でPASS。再学習して最終sourceの実績に付け替えていない。

## sourceと原証拠

| 対象 | SHA-256（由来を結ぶ用途） |
|---|---|
| 最終module | `c34a9aab22e216a512deafd1205c222fb17e9cc6b60ef46b7ff3267b64417902` |
| 最終tests | `7ca8bd46194081eeaba2d5662ded14607a6b587ecf702dbec3363468fd0a9ad5` |
| 実学習時module | `5ea85d5eec969482d04760a11827464dad4fcdd7a81deb0f472d938e2332c15e` |

[原証拠一覧](nn-source-evidence/files.json)。RED/途中FAIL/最終検査/独立レビュー/実runtime script・log・summaryを原byteで保存する。`.py` の原証拠は `.txt` の末尾を付ける。数値の検算にSHAは使わない。`full-count-unit-current-replay` のsummaryにはローカルraw全receiptの由来を残すが、raw自体の配布・保管庫復元はこのsource確認の範囲外。

## 次に進める条件

正式pilotの全121case/51obligation、全教師N/grid候補、実call/Greek/条件付きoracle/SDE/P&L/Q/頻度診断と実費用を検算する。保存入力・sourceと事前fresh planをbindしてからfreezeし、元12fit・検証を確定した後で全3seed×3level×44cell=396件を実行する。源泉未実装と金融精度未達は別に保持する。

source-unitの実測は、この正式pilot、実premium個票、両CASの復元、artifact-only3図、章の最終全3suite・独立受入・main統合を代替しない。private実装の単位処理は一括returnであり、各fitの途中ディスク保存/resumeは正式job adapter側で整える。
