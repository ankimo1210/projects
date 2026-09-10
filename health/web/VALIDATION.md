# Tasks 10–12 検証記録

2026-09-07。対象は `health/web/` のみ。実健康データ・token・.env は未読込・未変更。
コミット、stage、デプロイ、外部システム変更は行っていません。

## 自動チェック

作業ディレクトリ:
`/home/kazumasa/projects/.claude/worktrees/health-full-archive-nextjs/health/web`

```bash
npm run typecheck && npm run lint && npm test && npm run build
```

すべて exit 0。Vitest 3 files / 34 tests passed。Next.js **16.3.4** のproduction
static buildで `/`, `/insights/`, `/sleep/`, `/activity/`, `/heart/`, `/body/`,
`/inventory/` を出力（加えてNext標準404とローカルSVGアイコン）。
Node 26.7.0 / npm 11.19.0。インストール時の npm audit は脆弱性0件。

TDDでは最初にloader・samplingの23失敗、次に表示ロジック5失敗、さらに
interval status・manifest継承キー・暦上の欠損日3失敗を観測してから実装を通した。
テスト対象は世代混在、HTTP/404/JSON、形状・有限数・長さ・日付順・パス、abort、
原配列非変更、端点・両極値・欠損境界、全点からの再ズーム、前日比較、睡眠分類、CSV。

## Python exporterとの実接続

既存 `health/scripts/seed_demo.py` をweb内部の一時DBに対して実行。
`PYTHONPATH=/home/kazumasa/projects/.claude/worktrees/health-full-archive-nextjs/health/src`
および `/home/kazumasa/projects/.venv/bin/python` を使用した。
実Storeに約36,500点の架空日内心拍を追加し、`health.web_export.export_web` で
`demo-qa-20260907` を生成。元の5分間隔fixtureを含め2026-09-07は36,544点。
日次90日、過去日2026-09-06の日内データも使用。原本索引未取得のpendingを保持したまま、
すべての画面が正式envelopeを読み込めることを確認した。

元の生成物とは別に、以下を含む検証専用fixtureを作成:

- 保存900 points / 12 pagesがあり最新試行failed
- completeかつ表示未対応、empty、403、partial、unknown_history、storage_error
- 離れた2確認区間とinterval status（隙間を1区間にまとめない）
- 詳細ステージ、Classic、stage不明、昼寝、日次欠損、古い最終値

fixtureとDBは `node_modules/.cache/health-qa/` の一時ファイルのみ。
実データに似せた数値を本体のfallbackとして同梱していない。

## ブラウザ

既存キャッシュの Playwright 1.62.1 / Chromiumを一時ハーネスで使用。
package.json / lockにPlaywright等のE2E依存を追加していない。

- 7route × light/dark × 1440/390 px = **28画面**。通常exportと異常ケースfixtureで確認。
- 全画面で読込エラー・pageerror・document横はみ出しなし。
- 36,544点をブラシまたは時刻入力でズーム、20秒の範囲は**11点**へ復元。
- 全日へ戻す操作で全範囲に復帰。過去日選択では288点へ切替。
- 旧日の応答を遅延させても、再選択した日の36,544点を上書きしない。
- 30日期間選択が別routeへ引き継がれる。テーマ切替、mobile sidebar開閉／遷移。
- 失敗フィルタは3行を表示し、保存済み900 pointsを保持。表示中のCSVをダウンロード。
- Classic6件・不明1件を区別し、昼寝表示toggleでsessionが1件増える。
- 404、HTTP500、invalid JSON、古い書き出し、世代不一致、正常emptyを別表示。
- chart surface上のline_safe contrast（順序通り）:
  light **4.30 / 3.12 / 4.82**、dark **4.79 / 4.48 / 3.52**。すべて3:1以上。

一時ハーネス（cwdは上記webディレクトリ）:

```bash
node node_modules/.cache/health-qa/browser-check.cjs
node node_modules/.cache/health-qa/interactions.cjs
node node_modules/.cache/health-qa/states.cjs
```

利用したランタイム:
`/home/kazumasa/.npm/_npx/e41f203b7505f1fb/node_modules/playwright`
ブラウザキャッシュ: `/home/kazumasa/.cache/ms-playwright/`。
スクリーンショット／JSON結果も `node_modules/.cache/health-qa/` に保存。

## 引き継ぎ

- 読み込むmeta: `/data/meta.json`。filesはfilenameキー。`Inventory.sources`と
  任意の`intervals[].status`を正式契約どおり保持・表示。
- `.gitignore`は担当外のため未変更。親側で `.next/`, `out/`, `public/data/`,
  `node_modules/`, `*.tsbuildinfo` 等の除外を確定してから実データを出力すること。
- 一時静的サーバーは127.0.0.1:3100、配信元`health/web/out`。
  確認中の生成物は架空fixture。次のbuildはoutを再生成するのでexportをやり直す。
- ブラウザ確認済みのデータは架空のみ。本人データの取得完全性は未判定。
- lintはNext同梱のReactプラグインとの互換性のためESLint9.39.5に固定。

## 追加修正: 棚卸し互換性・短区間の極値

2026-09-07、親レビュー後の4点のみを追加修正。

- `Inventory.series` の必須型・件数/区分/日付範囲/単位の検証、保存系列表と専用CSV。
- 全有限区間の最小/最大をbucket配分前に確保。短い区間のスパイクと負の極値を保持。
  区間境界・極値の必要数がtargetを超える場合は保持を優先。
- KPIからlegacy_jsonだけを除外し、projection取得streamは含める。
- 任意のstored_pages/stored_pointsを優先し、最新試行と累積保存を分離。
  旧sourceレコードのfallbackと明示的な0値を検証。

先にロジック6件、実コンポーネント描画2件の失敗を再現してから修正した。
追加した表示テストはReactの実InventoryViewをサーバーレンダリングし、保存行数・期間、
累積件数・最新失敗、CSVの区別、空のtyped系列表が出力されることを検証する。
恒久的なブラウザ/E2E依存は追加していない。

検証コマンド（上記webディレクトリ）:

```bash
npm test -- src/components/inventory-page.test.ts src/lib/inventory.test.ts src/lib/downsample.test.ts
npm run typecheck && npm run lint && npm test && npm run build
```

既存の広範囲なブラウザ確認は再実行せず、今回の修正に限定。
現在の実データexportは未読込・未編集。build後のout/dataは親側で再エクスポートする。

追加修正後の最終結果: targeted Vitest 14件成功。続くtypecheck・lint・全Vitest
**5 files / 43 tests**・Next.js 16.3.4 static buildがすべてexit 0（2026-09-07）。
7画面のroute出力を確認。`git diff --check`も成功。backendの更新契約ではstored件数が
出力されることを確認し、フロントは旧sourceレコードとの互換性のため任意フィールドとして扱う。

### 最終修正: 親ファミリーの未確認状態を保持

KPIは保存page/pointの合計ではなく状態件数なので、詳細ファミリーの親を除外しない。
metaと同様にlegacy_jsonだけを除外し、親unknown_history・list完了・子完了の例で
未完了1件を保持する。旧親除外テストをこの回帰テストに置き換え、失敗（未完了0件）を
再現してから親除外ロジックと対応する画面説明を削除した。
