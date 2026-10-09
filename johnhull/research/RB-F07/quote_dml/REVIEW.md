# quote DML — 実装レビュー（2026-10-09）

研究成果の最終レビューは未完了。以下は本学習前のコード検査と修正。

| 対象 | 指摘・対応 | 検証 |
|---|---|---|
| 固定protocol | P2: payout/lrなどを変更しても実計算に反映されない。v1が対応する契約・学習条件を明示して改変を拒否 | 追加7件RED→GREEN |
| CPU学習隔離 | P2: default device変更がbufferとAdam stateへ漏れ、CPU以外のRNGもseedされた。局所CPU contextとCPU generatorを使用 | meta default・アクセラレータ呼出禁止の2件RED→GREEN。learner24件PASS |
| 配列からの再検査 | P1/P2: market/contract IDs、固定shock・費用軸、train尺度、fit roster、失敗記録の検査不足。protocol照合・train再計算・部分成果返却を追加 | 契約・価格・Greek・群ID・shock・尺度・失敗保持をsmokeで検査 |
| offline費用 | P2: 全分割の教師費用を1方式導入費用へ混同。サイズ別train教師時間と全比較実験費用を分離 | market生成/較正時間を別配列に保持。本計時・費用評価は後続 |

別担当による金融式の確認では、割引を含むLRM、条件付き期待値、独立brentq/complex-step/積分、固定CF、元本・bp費用、物理autogradとA転置、ridge損失の平均・正則化に追加の重要問題なし。
この記録は本実験30fits・計時・採否の承認を意味しない。
