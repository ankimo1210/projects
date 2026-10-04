# §28.4 Alternative Choices for the Numeraire — M29受入

日付2026-10-04、原典Hull 11e GE pp.676–679、main基点88e03d3f。

## 完了条件と範囲

原典12要点N01–N12/式28.16–28.25/脚注5,6をNC01–NC06の5軸へ割当。無収入口座の再投資・確率割引、支払日債券測度、一般theta forwardとfutures、term fixing T/overnight realizing UのU支払、OIS annuity Aとprojection Vを区別。原典に本節の印刷価格pinはなく、数値例は明示的な合成市場。

- 既存HWのdocumented Q zero-mean OU状態にbond exponent −B*c(t)を追加。条件付きintegrated-rate 3件/tower1件の独立RED→GREEN。公開signatureと依存は保持。Jamshidian/較正は数学的に不変、vol26のprice3点の最後桁とnotebookを再生成。
- private exact Gaussianの順序(X_T,∫r ds,W_T−W_t)、rank2直接sampler、small-ah、sigma0/負rate/条件付き状態/時刻0を照合。同一callのQ経路割引とT測度、term/overnight支払、annuityのpayment Gaussian混合を評価。
- projectionは決定的な加算simple-rate basis。AにはOIS、Vだけbasis。別の乗算basisは対比oracleであり教材へ混用しない。
- 独立kernel求積63fixture（joint6/stock18/rates21/annuity18、うち別basis6）、実API57と対比6、直接iid MC10行×262144標本。raw RNを自己正規化しない。最大API差9.947598300641403e−14、MC最大1.9887701280938437SE。price1e−9/rate2e−12、受入5SE、表示95%区間。保存/API計8変異拒否。
- 新6C.1–6C.6の11セル/全257、旧246本文/保存出力/Plotly保持、fresh全文一致、notebook4変異と消費破損拒否。
- 4共有図、Book/portal×1440/1000の16状態/16画像、trace/誤差棒/MathJax/幅700px/変異検査PASS。portal1000の全4図、Book1440の全4図を目視。
- portal194図/12テーマ（exotics82）、public72/private31。Book144 warningsは既存140+新Plotly4。

## 既受入節の回帰

既受入28節のD1をclean c3303574から実行し、browser・runtime probe・個別pytest・C:/F:両保管庫復元を確認。採用パス/SHA-256はm29-checkで固定。HW dependency closure変更による再描画。画像payload合計とpytest数は下記最終検証に追記。実容量の増加は未測定。

## 台帳・検証

受入29/未評価277、P3 4/37へ更新するための統合gateがPASS。全suite・fresh独立最終レビュー・main統合は進行中。この記録は工程途中であり、それらの完了をまだ主張しない。

## 最終検証（統合前）

既受入28節のbrowser・runtime probe・個別pytest計2,157件・C:/F:両保管庫復元はPASS。0節再利用・28節再描画。HW/共有registryの依存変更による再描画。採用画像payloadは19,960,718バイト、全462画像。重複排除後の保管庫の実増加容量は未測定。採用D1パスとSHA-256を固定。

全hullkit+report 4,125 passed・6 skipped・既存warnings2（213.52s）。15 gate/ledger tests PASS、4--check/ruff/台帳成果物/tracked releaseを確認してfresh独立レビューへ渡す。main統合は後続工程。

## 独立最終レビュー

Critical0/Important0/Minor3、対象96tests/4checks/100条件付きprobe/42不正入力/4画像を独立確認。Minor3はレビュー文書の再現例と限界を保存してdeferred。受入を止める問題はなく、main統合は次工程。
