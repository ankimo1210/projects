# Mathematics Foundations Phase One Implementation Plan

**Goal:** HTML中心の方針を維持し、入門8章・微積分Ⅰ11章・既存の回転接続章を読める学習経路にする。ユーザーの「このまま進めよう」を受けた第1段階の継続。

**Architecture:** 原稿HTMLと共通テンプレートは維持。章情報を `catalog.json` に集約し、生成・入口・科目別目次・前後移動を同期する。数値実験は独立したclassic scriptを追加し、ビルド時に埋め込む。生成物のみを更新し、既存教材は移動・改稿しない。

**Tech Stack:** Python標準ライブラリ、HTML/MathML/SVG、依存なしのJavaScript、Node組み込みテスト。

## 完了条件と範囲

- 入門: observation, logic, sets-maps, proofs, induction, invariants, inequalities, numbers（既存）。
- 微積分Ⅰ: limits, continuity（既存）, derivatives, mean-value, approximation, integration, fundamental-theorem, integration-methods, series, taylor, elementary-functions。
- 接続: rotation（既存）。計20章＋入口1ページ。既存3章のURLを保持する。
- 各章は問い、定義の動機、短い証明、条件と反例、本文に接続したコラム、3演習と段階ヒント・完全解答、振り返りを持つ。
- 数値観察と証明を区別する。借用する定理は前提として明示し、循環論法を避ける。
- 新規実験は接線・区分求積・幾何級数。定義できない点や収束しない領域を明示する。
- 本文はインストールなしで閲覧できる自己完結HTML。ノートブックは任意の将来の実験用。
- 本番依存、公開、外部送信、ブランチ変更を行わない。現在の未コミット作業と引き継ぎ文書を保全する。

## Tasks

- [x] Task 1: 入門の新規7章を執筆し、証明・演習解答・相互リンクを確認する。
- [x] Task 2: 微積分Ⅰの前半5章（limits, derivatives, mean-value, approximation, integration）を執筆する。
- [x] Task 3: 微積分Ⅰの後半5章（fundamental-theorem, integration-methods, series, taylor, elementary-functions）を執筆する。
- [x] Task 4: 20章のカタログと科目別入口・目次・前後移動を実装する。21ページの生成とリンク整合を先にテストして失敗を確認する。
- [x] Task 5: 接線・求積・級数の純粋関数を既知値、誤差評価、非収束、境界値でテストしてから実装し、ブラウザ操作へ接続する。
- [x] Task 6: 再ビルド、数値・リンク・構文・整形検査、ブラウザの表示と操作、独立した内容レビューを終えてSTATUSとREADMEを更新する。

## 検証の重点

科目をまたぐリンクと目次、定理の前提、微分と平均値定理の区別、Riemann積分と基本定理の循環、級数の和と有限の部分和の区別、スマホでの長い目次、既存3章の退行を確認する。

基準実行: Python 2件、Node 11件が実装前に成功。生成物は数MiB程度の見込みで、大きな計算や中間データは作らない。
