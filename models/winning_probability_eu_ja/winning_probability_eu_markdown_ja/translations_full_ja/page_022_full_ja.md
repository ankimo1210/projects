# Page 022 - 全文日本語訳

![Page 22](../assets/page_images/page_022.png)

## 日本語全文訳

モルガン・スタンレー
機密

残存期間
yearsToMaturity
maturityDate — 期日
lifeRemaining =~ ToMaturity
+ yearsSinceLastSuccess ~ maturityDate
— issueDate
(12)
残存期間が低いほど、流動性は低下するためリスクが高まります。上記で詳細に説明したロジックに基づき、lifeRemainingパラメータが一定の状態を保つ場合、その値が減少すると勝率が増加することが期待されます。

+ dpdy: 各金融商品のdpdy。
これはリスクの指標であり、証券の価格変動と利回り変動との関係を測定します。dpdyが高いほどリスクも高くなります。上記で詳細に説明したロジックに基づき、log1Oquantityの特徴量と同じようにxが一定の場合、dpdyの増加は勝率の増加につながると予想されます。

モデルのターゲット変数は入札結果であり、これは勝敗の結果を表します。以下のように表現できます：
.
1,
if inquiryState が Done の場合，
(as)
win =
0,
if inquiryState が TradedAway, TiedTradedAway, Covered, CoverTied のいずれかの場合。

3.4 モデル出力
オフラインの校正では選択された特徴量に対する係数を出力します。生産用の下流価格計算コンポーネントによる消費には、出力データへの変換は必要ありません。
具体的には以下の係数が得られます：
Bo: 截距（定数）。
+
Bi: 百分比TwSpreadの係数。
+
By: log1Oquantityの係数。
+
B3: dealerCountReciprocalの係数。
+
B4: lifeRemainingの係数。
+ B5: dpdyの係数。

モデルのオンライン実装では、各入札要請（RFQ）に対する勝率曲線を出力します。これは式5を使用して計算されます。これらの曲線は、入札が属する校正セグメントに関連するモデル係数を使って生成されます。

3.5 モデルの校正とパラメータ推定
入札データセットは内部MS BMETデータベースから取得され、共有ドライブの場所に保存されます。プロセス障害や新しい情報の追加がある場合など、ファイルはバックフィルできます。

最初に以下の手順でデータを精査します：
.
勝率モデル
EUGV RFQ価格設定

第22ページ / 73ページ

[git]
= ブランチ:
ir.eugy-hit-rate-curve @9676cba
= リリース:
(2025-03-12)

## 翻訳ソース

- OCR: `source_en_pages/page_022.md`
- ページ画像: `../assets/page_images/page_022.png`
- 注意: OCR崩れがある箇所は、ページ画像を正として確認してください。
