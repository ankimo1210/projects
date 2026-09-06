# Rates UI Lab — Tremor Implementation Plan

> **For agentic workers:** 実装時は `superpowers:executing-plans` を使い、下記のチェック項目を順番に進める。初回の依頼では計画を作成し、その後の「complete the plan」に基づいて実装タスク1〜5を実行した。外部公開は行っていない。

**Goal:** Tremor の完成テンプレートを JGB の金利画面へ置き換え、Blocks の交換による見た目・操作感・改造のしやすさを評価する。

**Architecture:** 独立した `rates-ui-lab` プロジェクトに実験アプリを置く。Tremor の元画面、金利への置換画面、Blocks を組み替えた画面を比較する。金利データと計算を表示部品から分離し、次の 21st.dev 実験でも同じデータ・評価課題を使う。

**Tech Stack:** 公式 OSS Dashboard の Next.js / React / TypeScript / Tailwind CSS / Tremor Raw / Recharts を継承する。初回はローカルの固定 JSON を使用。

**Spec:** 本文の「実験設計」「データと表示の契約」を設計仕様とする。ユーザーが提示した Dashboard → 金利データ置換案を出発点とする。

## Global Constraints

- 実装対象は `/home/kazumasa/projects/rates-ui-lab/`。既存の金融分析プロジェクトには結合しない。
- 初回は JPY / JGB、固定の合成データ、2D、ローカル起動を対象とする。
- テンプレートの余白・色・書体・角丸を保ち、Tremor 自体の UI を評価する。独自デザインへの全面変更はしない。
- アプリの UI 比較であり、ワークスペースの HTML 分析レポート用テーマは適用しない。
- 元リポジトリの取得コミット、取得日、URL、ライセンスを記録する。親リポジトリ内に入れ子の `.git` を作らない。
- 取得時の package.json / lockfile と互換性を優先し、Next.js / React / Tailwind のメジャー更新を実験に混ぜない。
- 本番依存の追加、公開、デプロイ、リモート変更は別途の明示承認が必要。Tremor 実験は既存依存で構成する。
- ブラウザに「DEMO / 仮データ」と基準日を常時表示する。現在の実勢金利を装わない。
- 各実験のデータ・計算・評価条件を揃える。ライブラリ固有の CSS や依存関係は各実験アプリ内に置く。
- コミット・push はこの計画作成では行わない。実装でも既存のユーザー変更を保持する。

## 調査で確認したこと

確認日: 2026-09-06。Web の表示内容と公開ソースを確認した。依存インストールやブラウザでの動作確認はまだ行っていない。

| 対象 | 確認結果・計画への反映 |
|---|---|
| [OSS Dashboard](https://github.com/tremorlabs/template-dashboard-oss) | README は Tremor Raw + Next.js、Apache 2.0 と記載。OSS 版と full 版のプレビューは別 URL。full 版の機能がすべて OSS に含まれるとは扱わない。 |
| [実際の package.json](https://github.com/tremorlabs/template-dashboard-oss/blob/main/package.json) | 確認時点で Next 14.2.23 / React 18.3.1 / Tailwind ^3.4.18 / Recharts ^2.15.4。pnpm-lock.yaml が存在する。これは取得対象の構成であり、最新推奨バージョンという意味ではない。 |
| [公式 Templates](https://blocks.tremor.so/templates) | Overview には 4 つの dashboard ページがあり、Next 15 / React 19 / Tailwind 3.4 の構成が案内されている。初回の対象はユーザーの出発案に合わせ OSS Dashboard に固定する。 |
| [Tremor Raw インストール説明](https://www.tremor.so/docs/getting-started/installation) | 現行説明は Tailwind 4.0+ を要求。Tailwind 3 のテンプレートに現行セットアップ手順をそのまま混ぜない。 |
| [Blocks カテゴリ](https://blocks.tremor.so/blocks) | KPI Cards / Line Charts / Filterbar / Tables / Spark Charts 等がある。 [Blocks のライセンスページ](https://blocks.tremor.so/license)は MIT。OSS テンプレートのライセンス表示とは分けて出典を記録する。 |
| [21st.dev](https://21st.dev/) | React コンポーネント・テンプレート・テーマを扱い、React + Tailwind / shadcn の慣例を案内。後続では部品ごとの依存とライセンスを確認して採用する。 |
| [財務省・国債金利情報](https://www.mof.go.jp/jgbs/reference/interest_rate/index.htm) | 現在・過去の金利情報への導線がある。実データ接続時の候補とし、初回の表示実験には依存させない。 |

公開ソースで `src/app/(main)/overview/page.tsx`、`src/components/ui/overview/`、`src/data/`、`src/components/LineChart.tsx` を確認した。既存 Overview は SaaS 指標を扱うので、数値配列だけでなく単位・比較の意味も変更する。既存 LineChart は数値の年限軸を設定していないため、金利カーブ専用の小さな Recharts コンポーネントを作る。

なお、この調査では OSS ライブプレビューと KPI Cards 個別ページを取得できなかった。実装時にブラウザ表示・コピーできるコードを確認し、未確認のブロック番号や見た目を採用済みと記録しない。

## 実験設計

選択肢は次の 3 つ。A を採用案とする。

| 案 | 利点 | 負担 |
|---|---|---|
| A. OSS Dashboard を取得し、金利画面を追加 | すぐに完成 UI を基準として比較でき、提示された出発案に一致 | SaaS 用の指標・単位を金利向けに置換する必要がある |
| B. Overview から開始 | 複数ページや高度な表を最初から参考にできる | 初回に触る画面・構成が増える |
| C. 新規 React アプリに Blocks を集める | 部品の自由度が高い | 完成画面の評価までの組み立てが増える |

初回の成果物は、同じアプリで次の画面を行き来できる状態とする。

1. `/overview`: 元テンプレートを参照する画面。改造前のスクリーンショットも保存する。
2. `/rates?layout=template`: 元の配置・スタイルを活かした金利画面。
3. `/rates?layout=blocks`: 同じデータで KPI Cards と Filterbar を組み替えた画面。

画面に置くもの:

| 領域 | 内容 | 試す UI |
|---|---|---|
| ヘッダー | JGB Rates Analytics、基準日、比較日、テーマ、レイアウト切替 | ページ構成、選択操作 |
| KPI 4 枚 | 10Y、30Y、2s10s、5s30s と各前営業日比 | 数字の可読性、符号、カード密度 |
| Yield Curve | 選択日と比較日の 2 曲線、2 / 5 / 7 / 10 / 20 / 30 / 40 年 | 凡例、ツールチップ、数値軸 |
| Curve Move | 年限別の変化幅を bp の棒グラフで表示 | 正負の色、ゼロ基準、比較期間 |
| Tenor Table | 年限、利回り、前営業日比、5 営業日前比 | ソート、桁揃え、行選択 |
| 補助表示 | DEMO、データの出典、選択中の比較条件 | 状態の理解しやすさ |

初回で実際に動かす操作は、基準日選択、比較日選択、凡例の表示切替、テーブルソート、行選択による年限の強調、light/dark、template/blocks の切替。JPY 固定のため、動かない通貨選択は置かない。

DV01 はポジション等の前提が必要なため、最初の 4 枚では 30Y 利回りを使う。RV は下記の追加実験とし、単一の年限カーブから計算できたようには表示しない。

## データと表示の契約

UI 比較用の正本は `rates-ui-lab/data/jgb-demo.json`。各実験に配布するときは同じファイルをコピーし、ハッシュ一致を検証する。初回から共通パッケージやモノレポ用ビルド基盤は導入しない。

```ts
type TenorYears = 2 | 5 | 7 | 10 | 20 | 30 | 40

type YieldPoint = {
  tenorYears: TenorYears
  yieldPct: number | null // 1.85 means 1.85%, not 185% or 0.0185%
}

type CurveSnapshot = {
  date: string // YYYY-MM-DD; synthetic observation date
  points: YieldPoint[]
}

type RatesDataset = {
  schemaVersion: 1
  dataKind: "synthetic"
  currency: "JPY"
  curve: "JGB"
  sourceLabel: string
  snapshots: CurveSnapshot[]
}
```

- 固定された約 60 観測日のデータを用意し、リロードで乱数を発生させない。日付は合成の観測日であり、実データの営業日カレンダーを再現したとは扱わない。
- 最終観測日は 2026-09-04 とする。最終カーブは、提示例に 7Y を補った合成値 `[0.92, 1.28, 1.54, 1.85, 2.34, 2.51, 2.63]` とする。
- `yieldPct` を唯一の利回り表現とし、差分の bp は `100 * (currentPct - referencePct)`。
- 2s10s は `100 * (y10 - y2)`、5s30s は `100 * (y30 - y5)`。上記の最終カーブでは、それぞれ +93.0 bp、+123.0 bp。
- スプレッドの前営業日比は「当日のスプレッド − 前営業日のスプレッド」。利回りの騰落率に置き換えない。
- UI 上の「前営業日」は直前に存在する観測日。「5 営業日前」は 5 観測日前。休日を暦日減算で推測しない。
- 数値は利回りを小数第 3 位まで、bp を小数第 1 位まで表示。計算途中では丸めない。
- 横軸は `tenorYears` の数値軸。2Y→5Y と 10Y→20Y を同じ距離にしない。直線で観測点を結び、平滑補間を暗黙に加えない。
- 利回り上昇・低下として色と符号を表示し、収益の良し悪しに読み替えない。ゼロは中立表示。
- 欠損は `null`、画面は `—`。ゼロ埋めや欠損を跨ぐ線の接続をしない。比較データ不足時は該当差分を `—` とする。
- 欠損、負金利、フラットなカーブの専用 fixture も用意する。通常の比較画面のデータには混ぜない。

## ファイル配置案

以下の `rates-ui-lab/` はすべて `/home/kazumasa/projects/` からの相対位置。

```text
rates-ui-lab/
  README.md                         起動方法、実験一覧、初回の結論
  data/jgb-demo.json                比較実験で共通の正本データ
  docs/comparison.md                同じ評価課題・条件・所感
  docs/sources.md                   取得元、コミット、各 Block の出典
  docs/screenshots/                 改造前と金利画面の比較画像
  experiments/tremor-dashboard/     公式 OSS テンプレートの取得物
    src/app/(main)/overview/page.tsx 既存画面
    src/app/(main)/rates/page.tsx    金利画面の入口
    src/components/rates/           カード、カーブ、変化幅、表、フィルター
    src/data/rates/                  配布した JSON と異常系 fixture
    src/lib/rates/types.ts           データ型
    src/lib/rates/metrics.ts         bp、スプレッド、比較日の選択
    src/lib/rates/metrics.test.ts    金利計算と欠損の検証
    src/lib/rates/view-model.ts      共通データから画面用の値を作る
```

21st.dev 用のアプリディレクトリは、その実験を始める時点で作る。先行して共通 UI インターフェースや空のアプリは増やさない。

## 実装タスク

### 1. 元テンプレートをローカルで再現する

成果物: 公式の元画面が表示され、金利版と比較できる。

- [x] 一時ディレクトリへ公式リポジトリを取得し、コミットを確定する。追跡対象ファイルを `experiments/tremor-dashboard/` に取り込み、入れ子の `.git` を持ち込まない。
- [x] README / package.json / lockfile / ライセンス関連ファイルを確認し、取得元を `docs/sources.md` に記録する。
- [x] テンプレートと lockfile に適合する pnpm を固定する。この環境では pnpm が PATH にない可能性があるため、利用可能な Node と pnpm を確認してから実行方法を README に残す。
- [x] 依存を取得し、`pnpm dev --hostname 127.0.0.1 --port 3100` で起動する。実際には確認した pnpm の呼び出し方を使う。
- [x] `/overview` を light/dark、幅 1440 / 1280 / 390 px で表示し、スクリーンショットとコンソールエラーの有無を記録する。
- [x] 改造前の `pnpm exec tsc --noEmit`、`pnpm lint`、`pnpm build` を記録する。起動・ビルドを妨げる問題は原因を切り分け、同じ修復を 3 回失敗したら状況を報告する。

### 2. 金利データと計算を用意する

成果物: どの UI 案でも同じ利回り・差分になる。

- [x] 上記のスキーマで固定 JSON と欠損・負金利・フラットの fixture を作成する。日付・年限の重複、有限数、昇順、必要年限を検査する。
- [x] `metrics.ts` に bp 差分、2s10s、5s30s、観測日ベースの比較日選択を実装する。
- [x] 1.85% − 1.80% = 5.0 bp、1.85% − 0.92% = 93.0 bp、2.51% − 1.28% = 123.0 bp を許容誤差付きで検証する。
- [x] 金利が欠けた場合のスプレッドは欠損、過去観測日が足りない場合の変化幅も欠損になることを検証する。
- [x] 既存のテスト環境がない場合は、互換性を確認した最小限の開発用テストランナーを追加する。本番依存は増やさない。
- [x] `view-model.ts` で共通の選択状態から KPI、カーブ、変化幅、表を生成する。各カード内に別々の固定値を書かない。

### 3. テンプレートの見た目を保った JGB 画面を作る

成果物: `/rates?layout=template` で金利を比較できる。

- [x] `/rates` と金利専用コンポーネントを追加し、既存のカード、選択部品、表、テーマを再利用する。元 Overview の SaaS データを壊さない。
- [x] KPI 4 枚、2 曲線のカーブ、年限別 bp 棒グラフ、年限表を接続する。
- [x] カーブではインストール済みの Recharts の数値 XAxis を使う。見た目はテンプレートに合わせ、共通 LineChart の既存利用先を変更しない。
- [x] 基準日・比較日・選択年限・レイアウトをページで一元管理する。`layout` は URL query に反映する。
- [x] DEMO と基準日を表示し、ツールチップ・凡例・表まで単位と比較日の表記を揃える。
- [x] 全操作と欠損データをブラウザで確認し、KPI と表の値が一致することを確かめる。

### 4. Tremor Blocks を交換して比較する

成果物: `/rates?layout=blocks` で見た目を切り替えられる。

- [x] 公式 KPI Cards から「シンプルな数値中心」と「推移を添えた Spark Chart」の 2 種を確認する。Filterbar も公式例を 1 種選び、実際の URL と採用ファイルを記録する。
- [x] Tailwind 3 の取得テンプレートに適合するソースを使う。現行 Raw のセットアップ全体をコピーせず、必要な部品だけ組み込む。
- [x] template 版は数値中心、blocks 版は Spark Chart 付きカードと別 Filterbar を採用する。同じ基準日・比較日・計算結果を渡す。
- [x] レイアウトを切り替えても選択状態を保持する。UI 差によってチャートの数値・軸範囲が変わらないようにする。
- [x] 比較時には情報密度、余白、数値の読みやすさ、選択操作の手数、コード修正量を記録する。

### 5. 確認して、次の実験に渡す

成果物: 動くローカルアプリ、比較画像、再現手順、採用・不採用の理由。

- [x] 金利計算テスト、TypeScript、lint、build を通す。未実行のものは理由とともに分けて記録する。
- [x] 1440 / 1280 / 390 px、light/dark で表示を確認する。表の横スクロールは許容し、ページ全体の意図しない横スクロールは解消する。
- [x] キーボードでフィルター・テーマ・レイアウトを操作し、フォーカス位置、色以外の正負表現、長い数値、欠損を確認する。
- [x] 元画面・template 版・blocks 版を同じ条件で撮影する。
- [x] `docs/comparison.md` に評価結果、使いたい部品、窮屈だった箇所、追加依存、修正したファイル数を残す。作業時間は計測できた場合だけ記録する。
- [x] `README.md` に実行コマンド、URL、DEMO の意味、データ正本、テスト結果、次の実験への入口を記載する。

## 初回の完了条件

- 元テンプレートと 2 つの金利 UI 案をローカルで見比べられる。
- 表示する KPI / カーブ / 変化幅 / 表が同じデータに基づいて更新される。
- 基準日・比較日・年限選択・ソート・light/dark・レイアウト切替が動く。
- 少なくとも 2 種の KPI 表現と別 Filterbar を試し、元テンプレートの置換だけで終わらない。
- 数値軸、% / bp、符号、欠損の扱いを検証済み。
- テスト・型・lint・build と実ブラウザでの確認結果が残る。
- 同一条件のスクリーンショットと具体的な比較所感がある。

## 後続の進め方

1. **Tremor の追加実験:** 必要なら Curve Move を小さな日付×年限ヒートマップへ変更する。RV 表は独立したモックとして、Rich/Cheap・Z-score・Carry の表の密度を試す。数値は「RV デモ・未計算」と明示し、残差の正負や Carry の期間を定義してから表示する。
2. **21st.dev:** 別の実験アプリで同じ正本 JSON を使い、同じ KPI / カーブ / 表を作る。シェル、ナビ、カード、選択操作を比較対象にする。チャートエンジンはできるだけ Recharts に揃え、UI とチャートライブラリの違いを分けて評価する。
3. **実データ:** 財務省の公開 JGB データを一度取得して共通スキーマへ変換し、ソース・取得時刻・観測日・単位・年限を検証する。ブラウザからの直接取得や Python API を最初から必須にしない。公表された年限別金利と個別銘柄の実勢利回りを区別する。
4. **高度な可視化・計算:** 日付×年限×利回りを見たい段階で Plotly の 3D Surface を別実験にする。React Three Fiber はカメラ・アニメーションに具体的な要件が生じた場合に検討する。DV01 / RV / Carry はデータ・モデル・ポジションの前提を定めた後に計算 API へ接続する。

UI の比較と、実データ・分析機能の拡張は別の進行軸にする。最初の着地点は「Tremor のどの表現が金利画面に合うかを、触って判断できる状態」。

## 実装結果（2026-09-06）

初回の完了条件をすべて検証済み。計算・生成テスト21件、production E2E18件、TypeScript、lint、buildが成功。比較画像19枚（元6・金利12・プレビュー1）を保存した。

- 起動と操作: [Rates UI Lab README](/home/kazumasa/projects/rates-ui-lab/README.md)
- 比較結果: [comparison.md](/home/kazumasa/projects/rates-ui-lab/docs/comparison.md)
- 条件ごとの証跡: [verification.md](/home/kazumasa/projects/rates-ui-lab/docs/verification.md)
- 実行結果とソース・データハッシュ: [check-results.json](/home/kazumasa/projects/rates-ui-lab/docs/check-results.json)

「後続の進め方」の21st.dev、実データ、3D、RV等は次の実験として残す。
