# health — Agent guide

Google Health APIの本人データを原本保存し、Next.jsで閲覧するローカル専用ポータル。
応答・ドキュメントは日本語、code/identifier/commitは英語。

- `source_catalog.json`が公開型・取得method・scope・検証根拠の正本。
  API形状は`docs/google-health-source-contracts.md`を参照。
  `endpoints.py`の`CATALOG`は表示できる既存14metricの投影定義であり、取得対象の上限ではない。
- `client.request_page`は解析・401 refresh前に受け取った全本文をcaptureする。
  `Archive.put`の耐久保存成功後にindexを記録し、その後にparser・cursorを進める。
  token endpoint・Authorization headerは原本に含めない。
- 原本は不変のcontent-addressed gzip。未知フィールド・複数source・版を保持する。
  再取得時に過去原本を削除しない。`raw_json`は互換用の解析済みJSONで原本の代用ではない。
- `ArchiveIndex`はStoreと同じconnection、CLIが唯一のwriter。
  新規/変更DDL前に`backup_database`でcheckpoint・close・durable backupを完了させる。
  legacy importのindex書き込みはtransactionとmarkerで一度だけ行う。
- `confirm_terminal`は保存・解析できた成功最終pageでのみ行う。
  期間指定なし・空応答・min/max日付だけで全履歴の証明にしない。
  未確認のhistoryは`unknown_history`として既知の成功区間と分離する。
- `archive_sync`はpage cursorを永続化し、型間を公平に進める。
  403/型別APIエラーは他型を続行。429/AuthError/保存失敗では停止する。
  API予算には401 retryを含む物理sendを数える。paceはclient責務。
- typed rowsの格納先は`Metric.storage_tables`で決め、`full_history`から再判定しない。
  `replace_chunk()`はtyped rows・旧raw・watermarkをchunk単位で原子的に置換する。
  DELETEは実際に取得した`covered_start`/`covered_end`だけに限定する。
  aligned chunk keyまでDELETEを広げると未取得の既存行を消すので禁止。
- `sync_state`のwatermarkは実際に取得した日付を記録する。
  history floorを広げる際は以前クリップされた境界chunkの欠落を修復する。
  原本に5年/30日の期限はない。期間下限が証明できない場合はその状態を明示する。
- `web_analytics`は全履歴でbaseline/移動平均を計算してから表示期間を切り出す。
  相関は期間ごとに計算、欠損を0にせず、civil timeにUTC offsetを補わない。
- `web_export`は日内の全点を保持し、全file成功後にmetaを原子的に切り替える。
  `docs/web-data-contract.md`がPython/TypeScriptの共有契約。
- `web/`は静的Next.js、API route・認可・同期はCLI側。間引きは描画時のみで、
  ズーム時に元の点へ戻る。7画面の解析・エラー・空データ表示を維持する。
- `.env`、`data/`、`web/public/data/`、`web/out/`はprivateかつgitignored。
  token、実データ、probe、生成JSONをcommitしない。配信は127.0.0.1。
- Health Planetは`healthplanet.py` / `healthplanet_auth.py`で独立して扱う。
  `data/healthplanet/`のSQLite・原本・tokenを使う。Webの正規体重・体脂肪率は
  Health Planetの各日最終測定を採用し、Google側の原本とtyped storeは保持する。
  SQLiteの初期化は非公開の一時DBからatomicに公開し、既存schemaは変更しない。
  最大3か月ごとの要求・60回/時間の永続台帳・単一writer lock・未完了rescanを保持する。
  公式APIにないrefresh grantを推測せず、認可はHTTPS成功画面のコード入力方式。
  筋肉量など提供終了項目を明示し、履歴の最古日を確認できない場合は取得済みと断定しない。
- Pythonはworkspace rootで`uv run --no-sync pytest health/tests -q`。
  `web/`でtypecheck/lint/test/build。自動テストはfake HTTPと架空fixtureのみ。
  UI用DBは`seed_demo.py --db-path <temporary path>`で生成し、実dataを上書きしない。
