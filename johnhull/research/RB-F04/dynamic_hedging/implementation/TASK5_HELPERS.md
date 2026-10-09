# Task5 統計・実験管理helperのソース確認

2026-10-09。**2 private helperの実装・独立レビュー完了、未解決0。開発branchのみ。Task5全体・正式pilot/freeze/main・研究受入は未完了。**

| 部分 | 内容 | 実装者の対象検査 |
|---|---|---:|
| `hullkit._dynamic_hedging_statistics` | 元個票d/r、64path blocks・seed層別保存bootstrap、個別ES95、数値誤差付きstrict閾値、全3init IUT、unknown/overflow | 41 |
| `deep_hedge_price._dynamic_hedging_protocol` | 固定12fits/44cells、用途別seed、候補/source/receipt同一性、test開封前の選択、全費用、immutable JSON/非object NPZ | 54 |

親による[変更範囲＋両索引/docstring検査](task-5-checkpoint-tests.txt)は **1200 passed（2.59秒）**。[実行記録](task-5-checkpoint-run.json)の5Python ruff/check/formatもPASS（helper4ファイル＋非production多曲線probe1ファイル）。関係全3suiteは最終gateで1回実行する予定で、今回は未実施。以前の1193件と索引/docstringが重なるため、両件数を足し合わせない。

- [初回sourceレビュー](task-5-helpers-review.md)・[JSON](task-5-helpers-review.json)：Critical/Important0、Minor M1。
- [修正差分](task-5-protocol-fix.diff)・[最新source指紋](task-5-protocol-fix-source.json)：truthy整数/文字列で子費用を除外できたM1を、bool以外のreceipt拒否で解消。正常boolの集計・raw失敗・pendingを維持。
- [独立再レビュー](task-5-helpers-rereview.md)・[JSON](task-5-helpers-rereview.json)：不正flag6種類拒否、通常ledger14/10、pending Noneを独立確認。M1解消・未解決0、両helperのsource proceed承認。
- [統計RED/GREEN・契約](task-5-statistics-report.md)・[protocol最新報告](task-5-protocol-report.md)・[protocol初回報告](task-5-protocol-initial-report.md)。
- [現在source/レビュー/run/候補の照合](helpers-source-validation.json)。SHAは同定用。数値は許容誤差/SEで比較。
- [候補](../candidate.json)・[全実験枠](../roster.json)：sourceから生成した未凍結候補。金融データ・正式freezeのreceiptではない。

初回のreview-package.diff、review-source.json、1198件のrun/logを保持した。修正後のテスト追加2件を含む最新runが1200件。原失敗/分母/費用を削除して成功扱いしない。

## Task5の残り

後続の[接続・予備測定](TASK5_CONNECTORS.md)でbounded runnerと保存金融rawのcheckerを実装・レビューした。正式pilotと主実験lifecycleは未完了。receiptのchecker名やSHAだけで金融精度や真正性は確認できない。次の義務を統合する。

1. call/Asian支持域の交差、全original N、NaN/未測定誤差の不適格化、共通teacher covariance/Ctheta誤差のIFT伝播。
2. transitive source closure、全attempt/重み/phaseのrequired expense IDs、raw failure/計時/超過の保存。
3. 37quotes/18states/教師/position/P&L/Q/momentの実pilot、tiny44cells/4fits、独立数学・code・pilot review。
4. 正式freeze後の12fitsとvalidationを完了してからtestを開く。保存indicesを全method/G/initへ共用し、独立数値envelope/Q/訓練完了を判定へ結合。
5. 主実験、saved/fresh/CAS semantic再検査、3図、最終suite・研究受入・main統合。

helperのsource承認は上記金融実験の達成を示さない。全体の次工程は[実施計画](../../../../docs/superpowers/plans/2026-10-09-dynamic-cross-model-hedging.md)。
