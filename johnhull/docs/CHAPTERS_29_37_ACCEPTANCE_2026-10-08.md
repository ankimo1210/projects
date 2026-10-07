# Ch29–37 軽量受入 — 2026-10-08

目的：残り45節を受け入れ、全306節の判定を確定する。
対象45節・149要件、計算40節・説明中心5節。基点`0d07def7`、
ローカル`codex/johnhull-acceptance`で実施する。
方針は[fast-v1](FAST_ACCEPTANCE_GUIDE.md)、判定の正本は台帳と
[統合記録](validation/fast-ch29-37/acceptance-check.json)。

## 対象と検証

Hull 11e Global Editionの要求ID・本文・読みを保持し、
日本語補足を`report/site/chapters/ch29.html`〜`ch37.html`へ配布する。

- Ch29–34の既存28 suiteとCh35–37の既存10 suiteは独立実行済み、計314 tests PASS。
  P7のprivate3モジュール・10 testは開発branch `b8ea5695`から新規ファイルだけ取り込む。
  旧共有計算・公開API・依存を変更しない。
- §33.2と§36.4は回収資料を用いてprivate計算と独立検証を補完する。
  新2モデル48 testsと受入guard27 testsを含む対象389ケースPASS。台帳41ケースも最終検証する。
  新guardは未実装importのREDから27 PASS、2モデルはTDDのREDから計48 PASS。
  要求は数値124・説明25。verifiedは各要件の宣言した式・計算・caller指定契約を指す。
  不足する原典契約、歴史価格、市場較正を再現したとはしない。
- 全45節・149要件を1280pxでブラウザ確認し、数式・表・節リンク・本文の意味・overflow・runtimeを検査する。
  要求欠落・本文改変のnegative control、各章の代表1画像、計9画像を対象とする。
- 旧261 accepted行と対象外261行の完全一致、全306 accepted行のnative artifact、summary、releaseを確認する。
  数値sourceと変動する台帳件数testを分離し、件数testは台帳証跡で固定する。
- 新計算・教材・recipe・証跡を独立レビューする。最終指摘と修正検証は
  [レビュー記録](validation/fast-ch29-37/review-check.json)に保存する。

## 原典入力とモデルの制限

- Ch29–30：半年複利yieldとduration、capletのfixing/payment、swaptionのannuity測度、
  convexity/timing/quantoの向きと時点を区別する。CMSやloading凍結は近似で、全市場fitではない。
- Ch31：§31.4の8664観測を使う。P/Qのrisk priceとrate単位、CIRのzero atomとEuler bias、
  OU/CIR/Rendleman–Bartterの経路割引・離散化を区別する。実測fitの一意最適は証明しない。
- Ch32：著者の終端1日規約と細分格子を分け、較正・tree・Bermudanの数値を検証する。
  小さい全履歴木の契約検証を大規模市場のBermudan評価へ広げない。
- §33.2：単一curve LMMのmeasure drift、bootstrap、reset freeze、割引、caller指定のcaplet/
  ratchet/sticky/最初の5回のITM flexicap、frozen-forward swaption/PCAを対象とする。
  sticky初期strikeとflexicapのstrike/eligible fixing/paymentが不足し、原典価格3.43/3.58/3.61等は未再現。
  CEV/Bermudanは紹介で、追加pricing実装の受入ではない。
  原典ratchet/sticky60値は、callerがK0=F0と指定した80,000 pathsの条件付き比較で誤差帯内。
  個別原典SE/seed/離散化がないため無条件の原典価格pinではない。
  [全価格・SE・仮定](acceptance/final-bgm-reference-comparison.json)を保存する。
- Ch34：元本/通貨/FXの向き、reset・payment lag、複利残高と行使を区別する。
  本文にない歴史的価格や指標を合成入力で再現したとはしない。
- Ch35：商品futuresは通常到達確率で較正する。天候の指数payoffと非取引指数のprice仮定を分ける。
  §35.4のroot1.48対1.501100501、年2最下11.10対11.094790584、I8.90対8.905209416は不一致を残す。
  §35.6の原典long/short文の不整合、station/basisと観測データの限界を明示する。
- §36.4：[原論文](https://www.anderson.ucla.edu/faculty/eduardo.schwartz/articles/70.pdf)から四半期パラメータを回収。
  売上log Euler、成長率OU、税損失繰越、cash、倒産、終価と明示した資本構成を検証する。
  原著式18の余分なsqrt(dt)はdt=1では同値だが、細分時は正しいOU分散を使う。
  会計の売上時点/終価利益期間とemployee optionの基準日/満期等は未確定。
  原著5457M、倒産27.9%、株価12.42を再現済みとはしない。
  明示した期首売上・quarterly終価利益の100,000 paths比較は8387.42M（SE51.14）、
  倒産30.729%（SE.1088 percentage point）で、原著との差を残す。
  [会計条件別の比較](acceptance/final-business-reference-comparison.json)を参照。
- §36.5：単独option値は一致。共同4状態option3.217896081Mは単独和3.000467371Mより大きく、
  原典脚注の「相互作用なし」を再現できない。状態や費用時点を省いて印刷値へ合わせない。
- Ch37：独立trial・等相関の数値と統制の説明を分ける。歴史的損失/制度の再推定や現行適用は対象外。

## 独立レビューと修正

モデルreviewerは新2モデル48 testsを独立再実行し、追加の連続OU求積、非等間隔LMMの
Euler/PC×3測度、ZCB/Black、同時PC更新、first5 ITMの先読み拒否を確認した。
モデルのCritical 0 / Important 0。原著未再現とcaller条件の境界を保持する。

教材レビューで§34.6の旧Ch26リンク切れと§31.4の回収前「未検証」表示を修正。
§29.3/36.4/36.5の古い検証状態も現在値へ整合した。原prepの要求149件は変更しない。
Swaption近似は単純annuity重みではなくfull forward Jacobianで説明し、
裸数値のドル記号、草稿見出し、空の強調記号を除いた。
画面検査で検出したdisplay TeXの崩れは、新教材の空行・行頭書式だけで修正した。
旧renderer/coreや261受入のsource/evidenceは変更しない。
全45節・598数式・22表・9画像を確認し、要求欠落/改変の両negative controlはPASS。
教材の最終判定はCritical 0 / Important 0 / Minor 0。

## 省略と作業範囲

承認済みfast-v1により全suite、全Book rebuild、2幅、全節画像、両保管庫復元を省略。
補足教材の受入であり、既存Book本文の改訂・main統合・push/公開は別工程。
旧P4の後続レビュー修正やP8は開発側branch/mainの報告と、この受入branchの内容を区別する。

## 再検証

WSLのrepo rootから共通venvと既存PYTHONPATHを使う。
新しい証跡を作る場合のみbuild→test→browser→check→registerを実行する。

```bash
python johnhull/scripts/fast_acceptance_final.py build
python johnhull/scripts/fast_acceptance_final.py test
node johnhull/scripts/verify_fast_acceptance_options_browser.cjs docs/acceptance/fast-ch29-37.json
python johnhull/scripts/fast_acceptance_final.py check
python johnhull/scripts/fast_acceptance_final.py register
```

登録後は`python johnhull/scripts/fast_acceptance_final.py verify`でread-only再確認する。
数式表示にはオンラインMathJax接続が必要。
