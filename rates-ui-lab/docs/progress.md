# 実行記録 — rates-ui-lab-tremor

計画: ../../docs/superpowers/plans/2026-09-06-rates-ui-lab-tremor.md

2026-09-06: ユーザーの「complete the plan」により計画を実装開始。

- 判断: 新規の rates-ui-lab ディレクトリ内で作業し、既存プロジェクトは変更しない。指定されたローカルパスを保つため checkout はそのまま、codex/rates-ui-lab ブランチを作成した。
- 判断: 21st.dev・実データ・3D は計画の後続工程。今回の完了対象は実装タスク 1〜5 と初回の完了条件。
- 判断: サイト作成スキルのローカル専用経路を使用。公開・Site 登録・デプロイは対象外。
- タスク 1: 実行中。公式ソース a20f619680e4582122c331bacf2efdef6daf460f を取得。元の LICENSE.md を保持。
- タスク 2〜5: 未着手。

- タスク 1: 完了。baseline typecheck/lint/build 成功。6条件の画像と `baseline.json` を保存。runtime page errors/ページ横溢れなし。
- タスク 2: 完了。60観測日と4ケース、21テストが成功。詳細は最終検証記録へ統合する。
- タスク 3: 主画面実装済み。最初の E2E は /rates 不在で失敗することを確認後、実装して成功。
- タスク 4: 実装済み。公式 KPI Cards 1/14、Filterbar 4/11 を翻案。source/license を記録。
- タスク 5: 操作・全画面幅・テーマ・欠損/負金利/フラットのブラウザ検証中。
- 修正: コピー元 SparkChart に、こちらに存在しない ESLint rule の disable コメントがあった。設定全体や依存を増やさずそのコメントだけ除去し、lint 成功。

## 完了

タスク1〜5: complete。計画の29項目を実装・確認済み。最終結果は verification.md / check-results.json、比較は comparison.md を参照。検証用の別ポートサーバーは終了し、3100番で本番ビルドを起動している。ローカル変更として保持し、commit/push/merge/deploy は行っていない。

追加修正: 不正 case の own-property チェック、欠損 tooltip の null 保持、表示ゼロの符号、モバイルの日付欄の縦並び。指摘2件は再レビューで解消確認。

## 21st.dev / Massive data 追加

2026-09-06: ユーザーの追加依頼により、同じ Next.js アプリへ `/rates-21st` を追加。

- 21st.dev の公開 Stats Bento パターンを JGB 指標へ翻案。registry source code は API key が必要なため取得せず、既存 Recharts と共通 view-model を再利用。
- 1万 / 10万 / 100万行を Web Worker で決定的に生成。17 bytes/row の TypedArray、10Y最大600点、32px固定高の仮想表を実装。
- unit 25件、typecheck、lint、production build、E2E 23件が成功。100万行の生成・50%移動・DOM行数上限・座標・mobile/darkを確認。
- 3100番で最終 production build を起動。公開・commit・push・mergeは行っていない。

## 21st.dev Prism Hero 追加

2026-09-06: ユーザー指定の BEVEL UI Prism Hero を JGB 用に追加。

- 公開されている MIT の構図と機能説明を参照し、registry source code は取得せず独自実装した。
- Three.js / React Three Fiber / Drei / Motion を追加。外部画像や HDRI は使わず、見出しテクスチャと照明を手続き的に生成する。
- 画面幅別の描画品質、画面外停止、reduced motion、WebGL失敗時の静止 fallback を実装した。
- デスクトップと390pxを目視し、モバイルの CTA とメタ情報の重なりを修正した。
- unit 25件、typecheck、lint、production build、全E2E 26件が成功。3100番で最終 production build を起動している。

## Meshyflix UI study 追加

2026-09-06: ユーザーが「見た目・3D操作を金利UIへ追加」を選択したため、既存の比較画面へ `view=meshy` を追加。

- Meshyflixの大きな見出し・黒とライム色・半透明パネル・形状検査・ギャラリーをJGB用に独自実装。既存のThree.js依存を再利用した。
- 60観測日×7年限を年限・利回り・暦日の3軸へ配置。欠損点と接するセルは描画せず、標準・欠損・負金利・フラットを同じ軸スケールで切替できる。
- 面・ワイヤー・点の切替、ドラッグ回転、ボタンによる拡大縮小、リセット、自動回転、CSV保存を追加。
- 画面外・非表示タブで自動回転を停止。reduced motionでは自動回転を無効化した。
- デスクトップ1440pxとモバイル390pxを目視し、軸ラベルの重なり・下端の切れを修正。検証結果はverification.md / check-results.jsonを参照。
- unit 28件、typecheck、lint、production build、E2E 28件が成功。3100番で本番ビルドを起動し、ローカル変更として保持。
