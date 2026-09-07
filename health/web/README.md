# Health Archive Web

日本語7画面のローカル閲覧専用ダッシュボードです。Next.js 16.3.4 / React 19.2.8、
Tailwind CSS 4、shadcn/ui、Recharts を使用します。実データもデモデータも同梱しません。
エクスポートがない状態では、案内を表示し、架空の数値に置き換えません。

## 起動

Node.js 22.12+（検証環境は26.7.0）、npm、静的配信用の Python 3 が必要です。
`health/web` で実行します。

```bash
npm ci
npm run dev
# http://127.0.0.1:3000
```

Python CLI の `health export-web --out-dir <web の絶対パス>/public/data` で
書き出したデータを開発サーバーが読みます。データ契約は
[../docs/web-data-contract.md](../docs/web-data-contract.md) が正本です。
認可・同期・原本管理は Python 側の操作です。

```bash
npm run typecheck
npm run lint
npm test
npm run build
npm start
# http://127.0.0.1:3000
```

`npm start` は `out` を127.0.0.1だけで配信します。静的 export なので
`next start` と file:// 直開きは使いません。ビルド後にデータを更新する場合は
`health export-web --out-dir <web の絶対パス>/out/data` を使用します。
次のビルドで `out` は再生成されるため、必要に応じて再エクスポートしてください。

## 画面とデータの意味

| URL           | 画面                                                               |
| ------------- | ------------------------------------------------------------------ |
| `/`           | 概要・値の日付・暦上前日比・スパークライン                         |
| `/insights/`  | 全履歴ベースライン、期間別相関と標本数、睡眠リズム、欠損カレンダー |
| `/sleep/`     | 主睡眠・昼寝、詳細/Classic/不明、7日平均、効率、就寝起床、曜日     |
| `/activity/`  | 歩数・7日平均、強度、距離、エネルギー、週間分布、日内歩数          |
| `/heart/`     | 安静時心拍、平均/深睡眠HRV、日内心拍                               |
| `/body/`      | 体重、体脂肪、SpO2範囲、呼吸、皮膚温                               |
| `/inventory/` | 全期間の原本取得・表示対応・成功区間・失敗・品質・CSV              |

表示期間30/90/180/365日・全期間はページ間で共有され、保存最新日を基準にします。
棚卸しとソーシャル・ジェットラグは全保存期間が対象です。書き出し日時、測定日、
原本取得状態、typed表示の有無を別々に示します。7日以上前の書き出しには案内が出ます。

日内データは選択日の全点を読み込みます。約2,000点への min/max 間引きは描画のみで、
範囲変更時に全点から再計算します。欠損の両端・区間端点・各連続区間の最小／最大を優先するため、必要な点数が
多い場合は目標点数を超えます。null と5分超の時刻の飛びを線でつなぎません。
最小・最大は表示範囲の全点から算出します。civil time に UTC offset を補いません。

ローダーは schema version・形状・有限数・世代・同一オリジン配下の相対パスを検証します。
外部へのredirectは拒否します。ページ／日付の切替・更新で古いリクエストを中断し、
後から届く旧結果も適用しません。相関・ベースラインをブラウザで再計算しません。

## 採用元と検証

- [Next.js static export](https://nextjs.org/docs/app/guides/static-exports)
- [Next.js support policy](https://nextjs.org/support-policy)
- [Studio Admin](https://github.com/arhamkhnz/next-shadcn-admin-dashboard):
  shell/header/sidebar構成と必要なUI部品のみ。採用commitとMIT全文は
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
- パッケージの具体的バージョンは `package.json` / `package-lock.json`。
  Next同梱のReact lintプラグインがESLint10 APIに対応していないため、lintは9.39.5に固定。
- チャートの categorical順序・line_safe・sequential は旧 `health/app/theme.py` から移植。
  shellはNeutral系、フォントはシステムフォントで外部取得なし。
- Vitestはローダー、期間・睡眠分類・CSV、間引きと全点からの再ズームを検証します。
  常設のE2Eパッケージはありません。実描画の記録は [VALIDATION.md](VALIDATION.md)。

このディレクトリの変更にAPI route、認証画面、同期ボタン、クラウド公開設定はありません。

## 棚卸しの互換性

`Inventory.series` は必須で、日次・日内・睡眠の保存行数、開始日、最終日、単位を
型検証して別表へ表示します。「保存系列をCSV」はこのtyped系列表を、
「取得状況をCSV」は検索・失敗フィルタ適用後の原本取得表を保存します。
`n` はNULL値を含む保存行数で、原本のpage/point件数とは合算しません。

棚卸しKPIは `representation === "legacy_json"` を除外します。
表示用projectionの取得streamは除外しません。旧JSONは明示して表に残します。
詳細ファミリーの親行も状態件数に含めます。発見済みの子が完了していても、親の
unknown_historyは未完了として残ります。これはmetaの取得状態と同じ対象です。
親子の行は表・CSVの両方に保持します。KPIは状態件数で、保存page/pointの合計は計算しません。

`SourceCoverage.stored_pages?` / `stored_points?` は全試行を通じた保存件数として
優先表示し、従来の `pages` / `points` は最終試行の件数として差があるときに併記します。
追加フィールドがない旧形式には `pages` / `points` を表示し、累積値未提供と明示します。
ゼロの累積値を旧値で上書きしません。各任意フィールドも非負の整数として検証します。
