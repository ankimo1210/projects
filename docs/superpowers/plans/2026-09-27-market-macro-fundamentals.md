# 工程3b: マクロ・財務取得の実装計画

更新日: 2026-09-27。実装場所は `codex/market-macro-stage3b` の専用 worktree。
[承認済みの統合仕様](../specs/2026-09-27-market-research-design.md)と
[取得元別の設計](../specs/2026-09-27-market-macro-fundamentals-design.md)に従う。
前工程の価格ブランチ `codex/market-data-stage3b` に重ね、main は変更しない。

## 完了条件

- ALFRED、ESRI GDP、MoF JGB、e-Stat、SEC companyfacts を新入口から明示取得し、
  raw hash、出典、版、取得時刻を一緒に保存できる。
- オフライン読取は完成snapshotだけを使い、公表・提出の直前には未来の版を返さない。
  時刻が日付だけの資料は `estimated`、収集後しか追えない資料は `snapshot` と示す。
- ページの途中失敗を完成データに見せず、再開可能な提供元では再開する。
  資格情報や応答本文がエラー、ログ、manifestに漏れない。
- Q06–Q08に対応するfixtureテスト、既存market-researchテスト、ruff、
  pre-commit、CLI疎通、公開元の小範囲ライブ確認を記録する。

## 作業順

### 1. 契約と保存

対象: `market-research/src/market_research/{contracts,storage,macro}.py` と専用テスト。

1. 公表時刻の精度・単位・頻度・取得時刻・raw hashを保持する失敗テストを書く。
   財務契約はCIK、taxonomy、concept、unit、会計対象期、form、accnを分離する。
2. テストのREDを確認してから、後方互換の任意フィールドと
   `fundamental` 行のtransaction/復号/時点読取を追加する。
3. 未完成snapshotは時点読取に現れないこと、同一版の競合時は全行rollbackすることを確認する。
4. 専用テストとmember全体を実行し、小さくコミットする。

### 2. ALFRED

対象: 新しいALFRED adapter、ingestion、専用テスト。

1. 複数ページ、`.`、狭いrealtime窓、日付だけの公表日と夏冬時刻、
   途中失敗・再開、鍵の非表示についてREDテストを作る。
2. `FRED_API_KEY` を環境から取り、`limit/offset/count` を上限付きで取得する。
   値のある行のみ正規化し、翌NY暦日00時を推定利用可能時刻とする。
3. 元の公表日と窓を保存し、完成後だけ照会できるようにする。
   旧 `macrokit` のコードへ常設依存しない。memberテスト後コミットする。

### 3. ESRI GDPと公表カレンダー

1. 公表XMLのJST時刻・予定、GDPメニューのリンク選択、CP932四半期CSV、
   改定、途中失敗をfixtureでREDにする。
2. 対象の公表回を指定し、カレンダーと一致するメニューから本表だけ取得する。
   参考 `knritu` は除外し、1回分の全歴史四半期を同じ公表版で保存する。
3. 予定と実績を取得時点ごとの別レコードで保存する。memberテスト後コミットする。

### 4. MoF JGB

1. 履歴・当月の両CSV、重複、和暦、欠損、片方失敗時の不可視化をREDにする。
2. 両方成功した時だけ指定年限のsnapshotを完成させる。
   `release_at`は取得完了時刻にし、価格と混ぜない。memberテスト後コミットする。

### 5. e-StatとSEC

1. e-Statの明示分類、月/年時刻コード、NEXT_KEY、単位不一致、
   認証値の反復、SECの同一対象期の改定・単位・form・NY日付境界をREDにする。
2. e-Statは分類を厳密に選び、途中ページを再開してからsnapshotを完成させる。
   SECは識別可能なUser-Agentを必須とし、companyfactsの対象conceptだけ保存する。
3. 財務の時点照会を確認し、memberテスト後コミットする。

### 6. CLI・記録・最終検証

1. `fetch-macro` / `macro` / `releases` / `fetch-fundamentals` /
   `fundamentals` の明示取得とオフライン読取、`--allow-stale` をREDにする。
2. CLI、README/DATA、`docs/STATUS.md`を更新する。旧入口切替や既存DB移管はしない。
3. 全memberテスト、ruff、pre-commit、相対リンク、`uv lock --check`、
   公開元の小範囲ライブ確認を実行。認証元は設定済みの場合だけ確認する。
4. 独立レビューを受け、重大・重要指摘はRED→GREENで一度の修正パスにまとめる。
   レビュー用ブランチに論理単位でコミットして共有する。

## レビュー重点

資格情報の例外連鎖・保存漏れ、rawと正規化行のhash結合、日付だけの公表時刻、
狭いALFRED窓の初回版誤認、GDP参考系列の混入、MoF/e-Statの過去値先読み、
ページ途中の公開、会計対象期とfiled日・unit・formの混同を重点確認する。
