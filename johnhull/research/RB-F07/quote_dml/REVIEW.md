# quote DML — 実装レビュー（2026-10-09）

独立最終成果レビューを承認済み。関連suiteの表示不具合を是正済み。`a25345e1`のmain統合後、全関連suiteとrelease gateを確認済み。以下は実装時の指摘と、最終レビュー範囲。

| 対象 | 指摘・対応 | 検証 |
|---|---|---|
| 固定protocol | P2: payout/lrなどを変更しても実計算に反映されない。v1が対応する契約・学習条件を明示して改変を拒否 | 追加7件RED→GREEN |
| CPU学習隔離 | P2: default device変更がbufferとAdam stateへ漏れ、CPU以外のRNGもseedされた。局所CPU contextとCPU generatorを使用 | meta default・アクセラレータ呼出禁止の2件RED→GREEN。learner24件PASS |
| 配列からの再検査 | P1/P2: market/contract IDs、固定shock・費用軸、train尺度、fit roster、失敗記録の検査不足。protocol照合・train再計算・部分成果返却を追加 | 契約・価格・Greek・群ID・shock・尺度・失敗保持をsmokeで検査 |
| offline費用 | P2: 全分割の教師費用を1方式導入費用へ混同。サイズ別train教師時間と全比較実験費用を分離 | market生成/較正時間を別配列に保持。本計時・費用評価は後続 |

別担当による金融式の確認では、割引を含むLRM、条件付き期待値、独立brentq/complex-step/積分、固定CF、元本・bp費用、物理autogradとA転置、ridge損失の平均・正則化に追加の重要問題なし。
この記録は本実験30fits・計時・採否の承認を意味しない。


## 最終成果レビュー（2026-10-09）

別担当が学習・再計時・Git操作を行わず、保存根拠を独立再計算した。
34方式×6列、H1/H2全6組、H3群別比、310計時raw、35 loader系列、
288原価対照のmedian/p95・train-only/deployment・call/query budget、
H4の15範囲表と5償却case、safe/OODを照合してPASS。
金融式・固定CF/FRA終端決済・A転置・bp/元本単位・群CI・公平対照を確認した。

| 最終指摘 | 対応・証拠 |
|---|---|
| fit metadataとsaved discountの検査不足 | budget/kind/mode/seed/負時間・discount改変の6 RED→GREEN。固定ID/尺度/時刻を検査 |
| timing registryの欠測・属性/回数付替え | 修正前snapshotで24 RED、現行34 tests PASS。310実測の旧記録互換も確認 |
| loader/原価・batch単位 | raw100標本からmedian/p95再計算、15 costs tests PASS。端数queryはfull batchへ切上げ |
| 強いcached解析対照が図から落ちる | 図のRED→5 notebook tests PASS。preparedとmarket較正を別panelに表示 |
| H3の太字が金利群改善まで否定する | 「35ショック混合」へ限定。rate-only改善/spot悪化の分解を保持 |

教材・接続研究として保持、Q-DMLを価格/Greek/速度標準器へ昇格しない採否を承認。
一次4URLも再openし、本文の使用範囲と未再現の性能・Strata比較を確認した。
保存notebookは3画像・error0。画像目視と23,498,066 bytesの両保管庫復元は実行担当の証跡に依拠する。
この承認は固定合成quote-DML v1の研究成果までで、全研究ロードマップの完了とは別。


関連3suiteの初回は6,915 passed / 4 failed / 6 skipped。
4件はheadless親のMPLBACKEND=Aggがkernelへ継承されてPNGを出さない表示不具合。
Agg環境で単独REDを再現し、notebook内のinline backend明示で是正。
kernel終了時のimport guardはdefault引数にoriginal importを保持する。
Agg環境のnbplot＋notebook 11件がPASS。金融・教師・学習・保存配列は変更していない。
その後、`a25345e1`をmainへfast-forward統合し、hullkit・report・deep_hedge_priceの
全関連3suiteを再実行した。6,919 passed / 6 skipped、334.02秒、終了コード0。
2件の既存deprecation warningが残る。candidateおよび統合後mainの
`verify_release.py --require-tracked`はともにPASS。
