# 出典と取り込み記録

## OSS Dashboard

- URL: https://github.com/tremorlabs/template-dashboard-oss
- 取得日: 2026-09-06
- コミット: `a20f619680e4582122c331bacf2efdef6daf460f`
- 取り込み先: `experiments/tremor-dashboard/`
- ライセンス: Apache-2.0。元の `LICENSE.md` と `README.md` を保持。
- 方法: `/tmp` に shallow clone し `git archive` の追跡ファイルを展開。入れ子の `.git` は含まない。
- 元構成: Next 14.2.23 / React 18.3.1 / Tailwind ^3.4.18 / Recharts ^2.15.4。
- pnpm: 11.1.0。取得した lockfile で frozen install。

## データ

金利データは UI 比較用に作成する決定的な合成値。市場データを取得したものではない。

## Tremor Blocks

- URL: https://github.com/tremorlabs/tremor-blocks
- 固定コミット: `b319e8d3d3678a4f60f4802f7e85bc1abc52d598`
- 取得日: 2026-09-06
- ライセンス: MIT (Copyright 2025 Tremor Labs, Inc.)。アプリの `licenses/tremor-blocks-MIT.md` に全文を保持。
- 元スタック: Next 14.2.23 / React 18.3.1 / Tailwind 3.4.17 / Recharts 2.15.0。

| 出典 | 使用箇所・変更 |
|---|---|
| [KPI Card 1](https://github.com/tremorlabs/tremor-blocks/blob/b319e8d3d3678a4f60f4802f7e85bc1abc52d598/src/content/components/kpi-cards/kpi-card-01.tsx) | `KpiCards.tsx` の template 表示。4指標、%/bp、前営業日差分に変更。 |
| [KPI Card 14](https://github.com/tremorlabs/tremor-blocks/blob/b319e8d3d3678a4f60f4802f7e85bc1abc52d598/src/content/components/kpi-cards/kpi-card-14.tsx) | `KpiCards.tsx` の blocks 表示。金利推移を SparkAreaChart へ接続。価格騰落率と損益の色分けを除去。 |
| [Filterbar 4](https://github.com/tremorlabs/tremor-blocks/blob/b319e8d3d3678a4f60f4802f7e85bc1abc52d598/src/content/components/filterbar/filterbar-04.tsx) | `RatesFilters.tsx` の期間ボタン。前営業日/5観測日前/20観測日前を実装し、選択状態・disabled・aria-pressed を追加。Tooltip 依存は増やさずラベルを常時表示。 |
| [Filterbar 11](https://github.com/tremorlabs/tremor-blocks/blob/b319e8d3d3678a4f60f4802f7e85bc1abc52d598/src/content/components/filterbar/filterbar-11.tsx) | `RatesFilters.tsx` のラベル付き選択欄。国/決済条件から基準日/比較日に翻案し、既存の Select / Label を再利用。 |
| [Card](https://github.com/tremorlabs/tremor-blocks/blob/b319e8d3d3678a4f60f4802f7e85bc1abc52d598/src/components/Card.tsx) | `src/components/Card.tsx`。ダーク背景・境界を取得 Dashboard の gray-950/800 に統一。 |
| [SparkChart](https://github.com/tremorlabs/tremor-blocks/blob/b319e8d3d3678a4f60f4802f7e85bc1abc52d598/src/components/SparkChart.tsx) | `src/components/SparkChart.tsx` に取り込み。既存 chartUtils を使用。取得先に存在しない ESLint rule の disable コメントを除去。 |

`obfuscate` と公式デモ用の固定高さ/フェードは取り込まず、アプリの内容に合わせている。

## 構成の差分

Stats Bento と Massive data までは既存の Recharts を再利用した。Prism Hero の実装では、公開ページが指定する `three` 0.185.1、`motion` 13.2.0、React 18 と互換性のある `@react-three/fiber` 8.18.0、`@react-three/drei` 9.122.0 を本番依存へ追加した。開発用は `@playwright/test` 1.58.2 と `@types/three` 0.185.0。Node の組み込みテストで金利計算を検証するため Node 22.18+ を使用する。`pnpm install --ignore-scripts` で native postinstall を実行せず、型/lint/build/ブラウザで必要機能を確認する。

## 21st.dev sample

- URL: https://21st.dev/@uilayout.contact/components/stats-bento
- 参照日: 2026-09-06
- 作者 / Library: ui layout / UI Layouts
- 公開ページ上のライセンス: MIT
- 公開ページ上の説明: KPI を大きさの異なるカードへ置く responsive bento-grid stats section。
- 使用箇所: `src/components/twentyfirst/TwentyFirstOverview.tsx` のカード階層・大きい主指標と小さい補助指標の配置。
- 変更: market share 等の例示指標を JGB 10Y / 30Y / 2s10s / 5s30s へ差し替え、既存の Recharts と共通 view-model を接続。
- registry install は `API_KEY_21ST` が必要。今回は公開パターンから独自実装し、registry の source code は取得・同梱していない。

21st.dev の公式 dashboard guide も、shell・metric cards・charts・table を組み合わせ、chart library を1つに絞る構成を案内している。今回も Recharts を追加せず再利用した。

## 21st.dev Prism Hero

- URL: https://21st.dev/@bevelui/components/prism-hero
- 参照日: 2026-09-06
- 作者 / Library: BEVEL UI
- 公開ページ上のライセンス: MIT
- 公開ページ上の説明: transmission と chromatic dispersion を使い、スクロールで動く手続き型の3Dヒーロー。外部アセットを使わず、画質調整・画面外停止・静止進捗・reduced motion に対応する。
- 使用箇所: `src/components/twentyfirst/PrismRatesHero.tsx`。JGB 10Y / 2s10s / 5s30s を重ね、屈折対象の見出しテクスチャも Canvas で生成する。
- 性能対応: 画面幅に応じて DPR・samples・render target 解像度を下げる。IntersectionObserver で画面外の連続描画を止め、reduced motion では静止状態にする。
- registry install は `API_KEY_21ST` が必要。source code は取得せず、公開説明と表示を参照した金利向けの独自実装である。

公開ページが示す依存4件を採用し、React 18 / Next 14 の既存テンプレートに合わせて Fiber 8 と Drei 9 を固定した。通常の Overview / Massive data では3Dコードを読み込まないよう、Prism コンポーネントを client-side dynamic import に分離している。

## Massive data

外部データセットは使用しない。`src/lib/rates/stress.ts` の決定的な式で1万・10万・100万行を生成する。Web Worker、TypedArray、600点のチャートサンプル、固定高の仮想表はいずれもこの実験用の独自実装。

## Meshyflix study

- URL: https://meshyflix.com/
- 参照日: 2026-09-06
- 参照した構成: 黒い背景、大きなタイポグラフィ、ライム色のCTA、半透明の情報パネル、形状のプレビュー、ワイヤーフレーム、モデル一覧と数値の帯。
- Meshyflix は3D生成・販売サービスの公開サイト。OSSライブラリとして取り込んだものではなく、MITライセンスの適用も確認していない。
- 元サイトのソース・モデル・画像はアプリへ含めない。外観と操作の発想を参考に、`MeshyRatesStudio.tsx` / CSS module / `RatesMeshScene.tsx` を独自に実装した。
- `src/lib/rates/mesh.ts` が4ケースのJGB合成データを頂点・色・面へ変換し、CSVも同じデータから生成する。欠損には頂点を作らず、接するセルを除去する。
- React Three Fiber、Drei、Three.js、Motionは導入済みの依存を再利用。新規依存、API key、外部モデル取得、AI生成リクエストは不要。
- 既存の `/rates-21st` に `view=meshy` を追加し、表示時にコードを動的読込する。
