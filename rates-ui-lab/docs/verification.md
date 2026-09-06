# 検証記録

2026-09-06。Tremor比較、21st.dev Stats Bento / Prism Hero、Meshyflix風の3D金利メッシュ、最大100万行の Massive data を対象に検証した。実データ、RV/DV01/Carry の実計算は後続工程。

## 実行結果

| 検証 | 結果 | 証跡 |
|---|---|---|
| 固定依存の install | 成功（`--frozen-lockfile --ignore-scripts`） | 取得コミットと方法は [sources.md](sources.md) |
| 計算・データ生成 | 28 tests passed、0 failed | `metrics.test.ts`、`view-model.test.ts`、`stress.test.ts`、`mesh.test.ts`、`generate-jgb-demo.test.mjs` |
| TypeScript | exit 0 | `pnpm typecheck` |
| ESLint | exit 0、warning/error なし | `pnpm lint` |
| Production build | exit 0、10ページ生成、`/rates-21st` は static route | `pnpm build` の最終実行 |
| Production E2E | 28 passed、0 failed、0 flaky、25.7s | `tests/rates.spec.ts`、`tests/meshy.spec.ts` |
| 100万行 stress | ready、16.2 MiB、初期DOM 19行、50%移動成功 | Worker生成・座標境界・仮想rangeを unit / E2E で確認 |
| 参考実測 | Worker生成 30.9 ms | headless Chromium、1440px。端末依存のため性能保証値ではない |
| Windows からの localhost 接続 | HTTP 200 | PowerShell Invoke-WebRequest で確認 |
| 元画面→金利画面の遷移 | HTTP 200、browser/console errors なし | [navigation-smoke.json](navigation-smoke.json) |
| 比較画像 | 既存19枚＋21st.dev 7枚＋Meshyflix 2枚 | [screenshots/](screenshots/) |
| コードレビュー | 指摘2件を修正・再レビュー済み、未解決 P1/P2 なし | 修正内容は下記 |

環境: Node 26.7.0 / pnpm 11.1.0 / Playwright 1.58.2 / Chromium 145.0.7632.6。全ワークスペースの Python テストは今回の変更対象外。

Node 26 のテスト実行では typeless TypeScript と Playwright の deprecated loader の警告がある。build では取得テンプレートの Browserslist データ更新通知が出る。いずれもコマンドは成功し、最終の金利画面の console error / pageerror はない。

## 計画との照合

| 要求 | 現在の実装・確認根拠 |
|---|---|
| 元テンプレートを保存し比較 | 元 Overview を保持。外部 clone の追跡ファイルだけを展開し、アプリ内 `.git` はなし。固定コミット・ライセンスを保存 |
| 既存スタックを維持 | Dashboard は Next 14 / React 18 のまま。Prism 用の Three.js、Fiber 8、Drei 9、Motion だけを追加 |
| 仮JGB・60観測日・7年限 | 生成テストで日付・最終値・件数を検証。正本4ケースとアプリコピーの SHA-256 一致 |
| 10Y / 30Y / 2s10s / 5s30s | unit と E2E で値・単位・前営業日比を検証。最終スプレッドは +93.0 / +123.0 bp |
| 全表示が同一データに連動 | 共通 view-model を KPI・カーブ・変化幅・表へ渡す。日付変更時の連動を E2E で確認 |
| カーブの数値年限軸 | SVG の点間隔比が 10/3 であることを E2E で確認。目盛り・点を画像で確認 |
| bp変化幅・比較期間 | 基準日−比較日の差分。5/20観測日前のボタンが期待日に変更されることを E2E で確認 |
| 表・ソート・年限選択 | 列ソート、10Y強調、解除、layout切替時の保持を E2E で確認 |
| Blocks を実際に交換 | KPI Card 1/14 と Filterbar 4/11 を翻案。Card/SparkChart を取得。出典・MIT本文を保存 |
| レイアウト間の状態保持 | 日付・比較日・KPI値・軸範囲・年限・凡例・表ソートが保持される E2E |
| 欠損・負金利・フラット | 4ケースを実装。欠損 `—`、線の分断、負の領域、ゼロスプレッド、欠損tooltipを検証 |
| light/dark・画面幅 | 各案を1440/1280/390pxで確認。ページ横溢れ・KPI文字溢れなし、日付欄150px以上 |
| キーボード | Selectの開閉・Endでの移動・Enterで確定、layout・themeの操作を E2E で確認 |
| 日本語・DEMO・基準日 | ヘッダー常時表示、表とツールチップに単位。市場の営業日を再現しない旨を表示 |
| 文書・画像・次の実験 | [README](../README.md)、[比較メモ](comparison.md)、出典・生成スクリプト・検証記録を保存 |
| 21st.dev sample | 同じ10Y / 2s10s / 5s30s / 30Y と数値年限カーブを Stats Bento 構成で表示。出典リンクと registry 未取得の範囲を明記 |
| Prism Hero | 屈折する3Dプリズムと JGB 指標を表示。動的読込、画面幅別品質、画面外停止、reduced motion、静止fallbackを実装 |
| Meshyflix study | 既存60観測日×7年限から3D面を構築。年限・暦日の間隔、負金利、欠損セル除去、CSV出力をunitで検証。表示・ケース切替、指標の連動、CSVダウンロードをE2Eで確認 |
| Meshyflix 3D操作 | drag / zoom / wireframe 切替の前後でCanvas画像が変わることをブラウザで確認。desktop 1440pxとmobile 390pxの画像を保存 |
| Massive data | 1万 / 10万 / 100万行、Web Worker、17 bytes/row の TypedArray、10Y最大600点、仮想表を実装 |
| 仮想表の実描画 | 先頭行の座標がスクロール領域内にあること、50%移動後のrange更新、DOM行数50未満をE2Eで確認 |
| 21st responsive | overview light 390、overview dark 1440、massive dark 390、prism light 390で横溢れ・console/page errorなし。内部の表だけ横スクロール |

## 原版の確認

- 元の production build で6条件の画像を保存。[baseline.json](baseline.json) は HTTP 200 / pageerrorなし / 横溢れなし。
- 後から pristine upstream を別ポートで起動して開発時の console も検証。[baseline-console.json](baseline-console.json) に、全6条件で `Extra attributes from the server: class,style` が記録された。
- これは `next-themes` が `<html>` を変更する挙動に対して原版の suppressHydrationWarning が body にしか設定されていないため。インストール済み next-themes README の手順に従い html に適用し、金利版の開発時・本番時の検証を通した。

## 検出して修正したもの

1. **元の SparkChart の lint コメント:** 存在しない rule の disable 行だけを削除。lint成功。
2. **表示の −0.0 / +0.0 bp:** 表示桁に丸めた結果がゼロの場合は符号を付けない。計算途中の丸めは加えない。回帰テストで red→green。
3. **URL の不正な case:** `__proto__` / `constructor` 等が object の継承プロパティを指す問題を own-property ガードで修正。標準データへ戻ることを E2E で確認。
4. **欠損の tooltip:** Recharts の既定 `filterNull` が null payload を落とすため、両tooltipでfalseを指定。欠損年限でも `—` を表示。
5. **モバイルの日付欄:** Flex shrink で26pxまで縮んだ欄を、小さい画面では全幅・縦並びに変更。最小幅150px以上の検証を追加。修正後の画像も目視確認。
6. **キーボード検証の同期:** Radix Select は開いた直後に遅れて選択項目へフォーカスするため、実際のフォーカス移動を待ってから End / Enter を送る。UI のキー動作は変更しない。
7. **仮想行の基準位置:** 巨大スペーサーの後ろが absolute row の static position になり、100万行では先頭行が約32,001,004px下に置かれた。行を `top: 0` に固定し、viewportとの座標比較テストを追加。
8. **Bento反転カード:** 共通 `bg-white` と個別 `bg-gray-950` が競合し、5s30sの白文字が白背景になった。共通カードに排他的な tone を追加し、computed background / foreground が異なることをE2Eで確認。
9. **21st.dev カーブ軸:** 自動tickの浮動小数表示が長くなった。Y軸を小数2桁へ固定し、全tickの形式をE2Eで確認。
10. **Prism のモバイル重なり:** 390pxで下部メタ情報と CTA が重なった。指標を上部の小型表示へ移し、下部メタ情報を隠して配置を分離。画像とE2Eで確認。
11. **Meshyflixの3D軸ラベル:** 40Yと開始日のラベルが重なったため日付を外側へ移動し、初期カメラの画角と注視点を調整。重なりとCanvas下端からのはみ出しをE2Eの座標比較で検証。

## 残る範囲

これは固定した OSS テンプレートと公開されている21st.dev構成によるローカル UI 比較。市場データ接続、計算モデル、ポジションリスク、外部公開は実装していない。Prism は表示用3Dであり、金利サーフェスの分析ではない。21st.dev registry の source code は API key が必要なため取得せず、公開パターンから独自実装した。

Meshyflix study も公開UIを参考にした独自実装で、同サービスへの接続やAI生成は行わない。3Dの頂点は最大420点。100万行のブラウザ内処理と、100万頂点のGPU性能を同じ結果として扱わない。FPSの端末横断ベンチマークは未実施。
