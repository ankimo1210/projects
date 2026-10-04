# §28.4 原典照合とレビュー

2026-10-04、Hull GE pp.676–679/脚注5,6/式28.16–28.25。原典12要点は設計メモと独立Gaussian参照へ割り当て、NC01–NC06で説明/実装/独立検証/可視化/実配布を照合。

HW Q状態の独立integrated-rate/tower RED→GREEN、既存Jamshidian・較正の利用者影響は[caller audit](validation/section-28-4/hw-caller-impact.md)を参照。確率割引を外側定数DFへ置き換えず、同一給付をQ/Tで比較。固定日と支払日、term/overnight、projection V/OIS A、加算basis/別モデルの乗算basisを区別。

63独立fixture、API57と対比6、raw iid MC10行、保存/API8変異、消費破損、旧246本文/出力/Plotly保持、fresh257全文、16表示状態、28D1/両保管庫と現行source hashesを確認。

## 最終レビュー

全suiteのfresh検証後に1名の独立レビューを行い、原文とroot判断を追記する。現時点ではレビュー結果を主張しない。

## 最終検証（統合前）

既受入28節のbrowser・runtime probe・個別pytest計2,157件・C:/F:両保管庫復元はPASS。0節再利用・28節再描画。HW/共有registryの依存変更による再描画。採用画像payloadは19,960,718バイト、全462画像。重複排除後の保管庫の実増加容量は未測定。採用D1パスとSHA-256を固定。

全hullkit+report 4,125 passed・6 skipped・既存warnings2（213.52s）。15 gate/ledger tests PASS、4--check/ruff/台帳成果物/tracked releaseを確認してfresh独立レビューへ渡す。main統合は後続工程。
