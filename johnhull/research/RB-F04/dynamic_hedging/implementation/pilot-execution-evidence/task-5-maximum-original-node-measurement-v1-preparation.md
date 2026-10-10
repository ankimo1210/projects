# 最大原節点の計測準備と容量小計

## 準備結果

D 内だけで測定器・初期義務・false 予算候補を作成。純行政 preflight **71 PASS**、3 ファイルの Ruff / format PASS。金融配列の decode・乱数・SDE・solver・worker 実行は **0**。本体 source / tests / docs / Git / CAS は変更していません。

- 母 job: teacher:local:N65536:high:raw（原1344節点を保持）。
- 対象: 原 node17、date0、spot100、state1、K65、N65536、16 blocks。
- 原 bank: teacher-driver:local:N65536、seed1345225788、calendar769、chunk256。全256 chunksを生成・保存・認証します。
- current field257×321、原3138 jobs / 121 cases / 51 attempts、元 job arguments / axes / prepared inputs を先に SHA で結合。
- runtime source81: canonical 408f2bc…。本体81ファイル・43入力の実bytes一致を最終確認。旧生成source 4e8…、旧M6費用・cap・unknownは文脈として保持し、新費用へ加算しません。

候補は root_preapproved:false、新component承認はnull。**親を含む総wall300秒、親子個別RSS4GiB**という行政上限の提案です。所要時間や4GiB適合の予測ではありません。実行前にrootが別名でpriorを固定します。

## 測定契約

共有 bank 生成だけで Generator を1回作り、その後の node / codec / saved checker の default_rng を拒否します。1節点を全格子や全金融受入の完了として扱いません。

bank生成、bank保存・read・認証、原節点生成、原raw保存・read・物理由来検査、全N saved SDE / 全11 label / 全16 block・covariance照合、bounded報告保存・read、物理 / 展開byte、source/input安定を別checkpointにします。区間費用は親inclusive費用の内訳です。元raw・全11 labelは検算終了まで保持し、巨大な検算報告だけ既存bounded helperで省きます。

実cap、native declared cap、source/solver例外、checkpoint不足を分離します。killでraw未保存なら原Nの初期NaN / unprocessed義務と未知を残します。capと例外の先後は証拠がなければunknown。親時計はprogress / file index / RSS観測を含み、最後のreceipt作成・保存費用はroot外側receiptで補います。

## 全phase容量の確定部分

20教師候補が全て完了し全原N・全失敗状態を保存するシナリオでの**非圧縮配列**です。unused / cap実行時の実容量やcompressed CASの下界ではありません。

| 範囲 | bytes |
|---|---:|
| 元の必須配列部分（9vector・fullstatus・failures・stats・共有bank） | 353,606,441,728 |
| 現codecの原node配列（dictionaryを基点と同形） | 355,868,451,168 |
| bank・raw/domain cache・bounded報告を加えた限定配列小計 | 364,185,768,816 |

小計にはmetadata / receipts / headers、初期義務、旧費用・cap履歴、残り3088 jobs、diagnostics、selected cacheコピー、main wrapper、CAS staging / restoreを含めていません。M6 genuine N1024の圧縮率も、合成N65536 transportも、全Nの容量・実SDE速度・メモリを保証しません。

C と F は各々単独で「実圧縮成果物T + staging + 残す履歴 + reserve」が必要です。Tは未確定。10/10 05:45 UTCの読取時空きは C314,778,112,000 / F185,710,804,992 bytes。両方を合算して1保管庫分とは扱えません。WSLで原本＋逐次1復元を共存させるなら2T＋作業領域です。

M6 bounded報告の4class・全2128 nodeはmetadata / file statだけ再確認しました。Lhighはpayload174,543,348 / physical198,357,752 bytes。数値の独立レビューは別担当で、この読取から資格を追加していません。

## 次へ渡せるもの / 未確定

全3138 jobs / 20 candidatesの元count、N/grid依存の論理byte、共有driverの1回計上、bounded報告差分、保管庫の同時存在式は予算へ使えます。全体physicalT・genuine65536ピークRSS・教師/保存/再検算rate・remaining jobsの展開byte・全phase時間は未確定です。

root報告ではM6 saved4classとM7元2oracleが終了。正式pilot / main / wholephaseの金融資格はunknownのままです。次は今回のfalse候補をrootが固定し、最大形状1原節点を実測する段階です。

詳細算術は task-5-whole-phase-capacity-static-v1-results.json と元report、計測契約は今回のinitial-description / budget-candidate / script、検査と実費はverification-v3 / final-validation-cost、固定一覧はmanifestを参照してください。
