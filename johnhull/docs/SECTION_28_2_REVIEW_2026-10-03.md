# §28.2 複数状態変数：原典照合とレビュー

日付2026-10-03、Hull 11e GE pp.674–675、main基点010a2bc3。
原典の2頁を本文と画像で確認。式28.11–28.13の係数・共通リスク基底、正負/ゼロのλs、Example28.3の超過6%、無価格追加因子の条件、APT/CAPMの関係を照合。
印刷値6%は総収益ではない。総期待収益10%は教材追加のr=4%の合成例。
math.fsumの独立参照12市場、SVD局所hedge、4直交回転、単因子縮約、条件付きCAPMを照合し、保存4改変/API4変異を拒否。
新11セル/計235、旧224本文/出力/Plotly保持とfresh全文出力一致、notebook4改変、16表示状態/16画像を検査。
1000pxのBook寄与図、portal hedge/validationを目視し、4新図をfull rowへ拡大。幅700px以上の負の検査をRED→GREENで確認。

## 回帰

既受入26節のbrowser・runtime probe・個別pytest計1,995件・C:/F:両保管庫復元はPASS。0節再利用・26節再描画。共有CSS変更による保守的な再描画。採用記録の再描画画像payloadは19,126,473バイトで、重複排除後の保管庫の実増加容量は未測定。採用D1パスとSHA-256を固定。

## 最終レビュー

全hullkit+report **3,925 passed・6 skipped・既存warning2件（167.04s）**。変更Python20ファイルruff、4--check、台帳--check-artifactsはPASS。独立レビューImportant1は消費時検査の回帰12件で修正済み（17 passed）、Minor/Declinedなし。

## 最終レビュー指摘への対応

1名の新規gpt-6-astra/high、範囲010a2bc3..b60a2dc8。Critical0 / Important1 / Minor0 / Declined0。
重要度は通常ビルドで66%という誤った教材を生成できる実害からImportantのままとした。
1回の修正で、保存API結果の1次元長さ・有限実数・独立参照との差1e−12を消費時に検査し、検査した値だけを描画へ渡す。数値記録と参照は各1回の読込。
12回帰テスト（変更/欠落/短縮/延長/NaN/±Inf/入れ子/文字列/bool/nullと二重読込）がRED 12 failed・既存5 passed → GREEN 17 passed（0.69s）。
共有図は保存4図と一致、fresh全文出力・旧224セル保持PASS。実画面16状態/16画像と統合26D1の現在hash/両保管庫はPASS。図の値・本文・生成済みページは変化しないため、旧26D1は採用記録を継続した。
修正後全suiteは3,925 passed・6 skipped・既存warning2件（167.04s）。再レビューは依頼しない。

## 独立レビュアーの原文（修正前）

### Strengths

- `factor_risk.py`はbroadcast前に最終因子軸の正の長さと一致を確認し、最後の軸だけを合計しています。金利は合計後のbatchとbroadcastされ、符号・空batch・complex・非有限・overflowの境界を対象テストで確認しました。
- Hull GE pp.674–675の原文と照合し、Example 28.3の**超過6%**と教材追加の総期待収益10%、負寄与と総volatility、CAPMの条件付き結論が適切に区別されています。直交回転では両ベクトルを回転し、相関の二重適用もありません。
- 独立`math.fsum`参照、SVD局所hedge、実API変異、旧224セルの本文・出力・Plotly保持が揃っています。
- 統合ゲートは記録自身に依存せず必須ハッシュを再構成し、採用D1のpath/SHAと両保管庫を検証します。台帳更新前の検証順序も適切です。
- 1000pxのBook/portal各4図、計8保存画像を目視しました。寄与、3面hedge、12市場比較の文字や凡例に重なり・欠けは見られませんでした。

### Issues

#### Critical

なし。

#### Important

1. **通常の教材生成が、改変された保存API結果を検証済みの結果として描画する**

   - **箇所:** `johnhull/hullkit/src/hullkit/_factor_risk_lesson.py:112`（関連する検証は同ファイル`:22`）。
   - **問題:** `_load_reference()`はPASS、節番号、参照ファイルとソースのハッシュを確認しますが、描画に使う`api_excess_returns`の内容・長さ・有限性を検証しません。その後、`_figures()`は記録を再読込して配列を直接描画します。
   - **再現:** 現行`numerical-check.json`のコピーを`/tmp`に作り、`api_excess_returns[0]`だけを`0.06`から`0.66`へ変更。プロセス内で`_RECORD`をそのコピーへ向けて`_figures()`を呼ぶと、例外なく生成され、参照棒は`0.06`、API棒は`0.66`となりました。PASS・全ハッシュは変更していません。
   - **影響:** 通常の共有図生成を使う教材・portalの再ビルドで、誤った66%を「factor API」の検証結果として表示できます。現在保存されている図は正しいものの、結果配列の偶発的な変更を消費時に拒否できません。
   - **既存防御との関係:** `build_factor_risk_acceptance_record.py:294`の再計算比較とbrowserの全trace照合は、この変更を拒否します。ただし通常の教材生成にはそのゲートが必須でないため、消費境界の問題は残ります。
   - **修正案:** ハッシュ確認済みの参照値に対し、保存API配列のshape・有限実数・許容差`1e-12`を軽量に検証し、その検証済みデータを描画へ渡してください。記録の二重読込も避けてください。既存ハッシュを保持したまま結果を変更・欠落・短縮・非有限化した場合に、通常の`_figures()`が拒否する回帰テストを追加してください。教材ビルドで全数値検証を再実行する必要はありません。

#### Minor

なし。

### Recommendations

上記1件をRED→GREENで修正し、依存するnotebook・表示証跡・ハッシュ記録を更新して既定の最終検証を完了してください。

今回、レビュー担当が独立に実行・確認した範囲は次のとおりです。

- 新規対象8テストファイル：**64 passed（15.45秒）**
- reference、numerics、notebook、integrated acceptanceの**4本の`--check`：PASS**
- 原典pp.674–675の本文、p.674のページ画像、1000px保存画像8枚の目視
- consumer境界の保存結果改変再現
- 終了時の作業ツリーはclean、HEADは`b60a2dc8635fc95d4a97d59e1b86edc1a0868c92`のまま

全suite **3,913 passed / 6 skipped**とライブbrowser実行は著者の実行記録を確認したもので、レビュー担当による再実行ではありません。trackedファイル・index・HEAD・branchは変更していません。

### DECLINED TO JUDGE

なし。検討した問題を「仕様外」という理由で除外していません。

### Assessment

**Ready to merge? With fixes**

数値API、原典との整合、既存教材の保持、統合受入ゲートは良好です。通常の教材生成で保存API結果の改変を受け入れるImportant 1件を修正してから統合してください。
