# 共通研究資料（B/Dのみ）

原論文を同梱PDFで読み、以下を研究の入口として使う。これは結果の保証でも
推奨パラメータの答えでもない。資料の読書時間も60分に含める。

## Waggoner, Spline Methods for Extracting Interest Rate Curves from Coupon Bond Prices (1997)

年限によって粗さへのペナルティを変えるフォワード・スプラインの研究。
短期で必要な柔軟性と、長期の不必要な振動を抑える性質の両立を検討する。
今回のデータ・ノイズに最適なペナルティ値を与える論文ではない。
固定ペナルティとの一要素比較、年限別の検証、欠損時の安定性を確認する。

Source: https://fraser.stlouisfed.org/files/docs/historical/frbatl/wp/frbatl_wp_1997-10.pdf

## Hagan & West, Methods for Constructing a Yield Curve (2008)

補間とブートストラップは独立の後処理ではなく、共同で価格・形状を決める。
局所性、入力の摂動に対する安定性、フォワード形状という観点を確認する。
正金利に基づく割引係数単調性の議論を、負金利を許す今回の契約へ無条件に
適用しない。ノイズのある全観測への完全適合と真のカーブ推定も区別する。

Source: https://dlu-umich.github.io/docs/HaganWest.pdf

## 検証の記録

主張／適用できる前提／今回の仮説／変更要素／採用基準／結果を対応付ける。
論文の方法を使わなかった場合にも理由を記録する。原論文は研究閲覧用であり、
権利確認なしに公開リポジトリへ再配布しない。
