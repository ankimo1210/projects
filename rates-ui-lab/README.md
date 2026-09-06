# Rates UI Lab

Tremor の元 Dashboard・金利版・Blocks 版、21st.dev の Bento・Prism Hero、Meshyflix風の3D金利メッシュと大量データ表示を触って比較する、ローカル専用の UI 実験。

## 起動

Node.js **22.18 以上**と npm が必要です。pnpm は次の固定バージョンで呼び出せます。

```bash
cd /home/kazumasa/projects/rates-ui-lab/experiments/tremor-dashboard
npx --yes pnpm@11.1.0 install --frozen-lockfile --ignore-scripts
NEXT_TELEMETRY_DISABLED=1 npx --yes pnpm@11.1.0 dev --hostname 127.0.0.1 --port 3100
```

- [Blocks 版](http://localhost:3100/rates?layout=blocks): Spark Chart 付きの KPI と期間ボタン
- [Template 版](http://localhost:3100/rates?layout=template): 数字中心の KPI と日付選択
- [21st.dev sample](http://localhost:3100/rates-21st): Stats Bento 構成で同じ金利指標を表示
- [Prism Hero](http://localhost:3100/rates-21st?view=prism): 屈折する3Dプリズムに JGB 指標を重ねる WebGL 実験
- [Meshyflix study](http://localhost:3100/rates-21st?view=meshy): 60観測日×7年限の金利メッシュを回転・拡大し、Surface / Wireframe / Pointsで比較
- [Massive data lab](http://localhost:3100/rates-21st?view=massive&rows=1000000): 1万・10万・100万行を切り替え
- [元の Dashboard](http://localhost:3100/overview): 改造元の SaaS サンプル

`--ignore-scripts` は取得テンプレートに含まれる native postinstall を実行しない設定です。この設定で起動・型・lint・build を検証しています。

## 試せること

1. 基準日を変えて、KPI・金利カーブ・変化幅・表が同時に更新されることを確認。
2. Blocks 版で前営業日・5営業日前・20営業日前の比較を切り替える。
3. Template / Blocks を切り替え、同じ基準日・比較日・表ソート・選択年限・凡例で見比べる。
4. 表の列見出しでソートし、年限ボタンでカーブの点と変化幅のバーを強調する。
5. 凡例でカーブを隠す。ヘッダーの Light / Dark でテーマを変える。
6. 下部の「仮データのケース」で標準・欠損・負金利・フラットを切り替える。
7. 21st.dev sample で同じ 10Y / 2s10s / 5s30s とカーブを Bento 配置で読み比べる。
8. Massive data で1万・10万・100万行を切り替え、生成時間・メモリ量・DOM行数を確認し、表をスクロールする。
9. Prism Hero でスクロール・ポインターに追従する屈折表現、画面幅別の描画品質、reduced motion 時の静止表示を確認する。
10. Meshyflix study で標準・欠損・負金利・フラットの面を切り替え、回転・拡大・視点リセットを試す。Download CSV で選択した全観測値を保存する。

画面内のラベルは日本語、指標名・チャート名は英語です。元の Dashboard は取得時の内容と表示を保ち、金利画面に戻るリンクだけ追加しています。

## 金利データ

**すべて仮データです。実勢金利や投資判断用の分析結果ではありません。**

- 正本: `data/jgb-demo.json`。60 観測日、2026-06-15〜2026-09-04、7 年限。
- ケース: `jgb-demo-missing.json` / `jgb-demo-negative.json` / `jgb-demo-flat.json`。
- 再生成: `node scripts/generate-jgb-demo.mjs`（このプロジェクトのディレクトリから実行）。正本とアプリ内コピーを同時更新。
- 型・計算: `experiments/tremor-dashboard/src/lib/rates/`。
- `yieldPct: 1.85` は **1.85%**。変化幅は `100 × 利回りの差` で bp に換算。
- 2s10s = 10Y − 2Y、5s30s = 30Y − 5Y。最終日の値は +93.0 bp / +123.0 bp。
- 「前営業日」「5営業日前」は存在する観測日の順序で決める。合成データは平日だけを使い、日本の祝日を再現しない。
- 欠損は `null` / `—`。チャートをゼロで補完せず、線を分断する。
- 色は上昇（indigo）・低下（amber）・変化なし（gray）を表す。収益の良否を表すものではない。
- Massive data は固定 JSON を肥大化させず、ブラウザの Web Worker で決定的に生成する。7年限を交互に並べた列指向 TypedArray で、1行17 bytes（100万行で約16.2 MiB）。
- 100万行をすべてDOMへ置かず、32px固定高の仮想スクロールで表示範囲と前後6行だけを描画する。10Yチャートは最大600点へ等間隔サンプリングする。

カーブの X 軸は年限の実間隔です。金利変化幅の棒グラフは年限をカテゴリとして並べます。

Meshyflix study は X=年限、Y=利回り%、Z=暦日。標準データは420頂点・708三角形で、隣接4点が揃った場所だけを接続します。欠損をまたぐ面は作りません。4ケースで軸のスケールを固定し、同じ日付のフラットカーブも日付間の水準変化は残します。

## 検証

アプリのディレクトリから実行します。

```bash
npx --yes pnpm@11.1.0 test
npx --yes pnpm@11.1.0 typecheck
npx --yes pnpm@11.1.0 lint
NEXT_TELEMETRY_DISABLED=1 npx --yes pnpm@11.1.0 build
```

E2E は **3100番で起動済みのアプリ**を対象とします。初回はブラウザを準備してください。

```bash
npx --yes pnpm@11.1.0 exec playwright install chromium
npx --yes pnpm@11.1.0 test:e2e
```

- 別 URL: `RATES_BASE_URL=http://127.0.0.1:3101 npx --yes pnpm@11.1.0 test:e2e`
- 別 Chromium: 環境変数 `RATES_CHROMIUM_PATH` に実行ファイルの絶対パスを指定。
- スクリーンショットは `docs/screenshots/` に保存。テストの一時出力は Git 管理外。
- dev と build は同じ `.next` を使用するため、build 前に dev を止める。build 後は `pnpm start --hostname 127.0.0.1 --port 3100` で本番ビルドを確認できる。

最新の実行結果は [検証記録](docs/verification.md)、見た目の比較は [比較メモ](docs/comparison.md) を参照。

## 構成と出典

```text
data/                          比較実験で共通の正本 JSON
scripts/                       再現可能な生成処理とそのテスト
docs/                          比較メモ・出典・検証記録・画像
experiments/tremor-dashboard/   独立した Next.js アプリ
```

- [OSS Dashboard](https://github.com/tremorlabs/template-dashboard-oss): Apache-2.0。元 `LICENSE.md` / `README.md` を保持。
- [Tremor Blocks](https://github.com/tremorlabs/tremor-blocks): MIT。KPI Card 1 / 14、Filterbar 4 / 11、Card / SparkChart を取り込み・翻案。
- [21st.dev Stats Bento](https://21st.dev/@uilayout.contact/components/stats-bento): MIT。公開されている Bento の構成と視覚パターンを金利向けに翻案。API key が必要な registry source code は取得・同梱していない。
- [21st.dev Prism Hero](https://21st.dev/@bevelui/components/prism-hero): MIT。公開されている BEVEL UI の3Dヒーロー表現を、外部画像なしの JGB 用シーンとして独自実装。registry source code は取得・同梱していない。
- [Meshyflix](https://meshyflix.com/): 公開画面の大きな見出し・半透明パネル・ライム色・3D検査UIを参考にした独自実装。サイトのソース・モデル・画像は取り込まず、既存の仮JGBデータから形状を生成。AI生成サービスへの接続は行わない。
- 固定コミットと翻案内容は [出典](docs/sources.md) を参照。
- Prism 用に Three.js、React Three Fiber、Drei、Motion を互換バージョンで追加。開発用に Playwright 1.58.2 と Three.js の型定義を追加。
- この版は取得テンプレートの構成を保ったローカル実験。公開用途への変更時は依存と構成を別途確認する。

## 次の実験

Tremor・21st.dev・Meshyflix study を同じ指標・操作課題で比較し、採用するカード密度とナビ構成を決める。実データ接続、RV / DV01 / Carry の計算、Plotlyとの3D操作比較は後続工程。

実装計画: [2026-09-06-rates-ui-lab-tremor.md](../docs/superpowers/plans/2026-09-06-rates-ui-lab-tremor.md)
