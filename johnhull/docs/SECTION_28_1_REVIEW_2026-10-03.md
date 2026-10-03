# §28.1 市場リスクの価格：原典照合とレビュー

日付2026-10-03、Hull 11e GE pp.671–674、main基点32751a0d。

## 原典照合

4頁を抽出/画像で確認し、同一Brownianの無配当取引証券、株数hedgeとλの共通性、
正負のsigned loadingと通常volatility、Examples28.1/28.2、消費財の注意、Girsanovを照合した。
原典は一般の状態/時点依存を許す。定数GBMは教材の合成実験として区別した。
印刷値.2/−.15/1.5%を独立再計算。12市場/6power給付/4raw RN MC、4保存改変/4API変異、
旧213セル保持とfresh出力、16表示状態、1000pxの2画像目視を確認。

## 実装者の判断

Ruling: 承認済みP3節受入を進め、design/planを再承認待ちにしない。
利用者は次の実装を明示し、pipelineと契約は確立済み。誤りなら§28.1の選択範囲を修正する費用が生じる。
M25統合後のcleanな作業場所を再利用し、M26へ名前を変更してmainから新branchを作成。
Task4テストは先にscratchで未実装FAILを確認し、cleanなTask3commitからD1を実行してからprojectに保存する。

## 回帰

既受入25節のbrowser・runtime probe・個別pytest計1,931件・C:/F:両保管庫復元はPASS。24節再利用・1節再描画。採用記録の再描画画像は456,055バイト（保管庫の実際の増加容量とは区別）。採用D1パスとSHA-256を固定。

## 独立最終レビュー

未実施。全task検証後、executing-plans規約に従ってfresh-context reviewer一名を呼ぶ。
Critical/Importantは効果で再判定し一度のRED→GREEN修正と全suite、Minorは保留。
判断を留保した項目は理由/誤りの場合の費用を記録する。
