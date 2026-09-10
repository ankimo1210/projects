# Web data contract v1

Health Planet追加: `healthplanet.json`も同じ世代のenvelopeで出力する。
旧世代でこのファイルがない場合もGoogle画面は利用可能。
`data`は`provider: "healthplanet"`, `timeBasis: "civil"`,
`status: "not_connected" | "pending" | "partial" | "available"`,
`historyComplete: false`, `sources: SourceCoverage[]`,
`measurements: {id, metric, tag, timestamp, value, unit, model}[]`,
`unsupported: {metric, label, reason}[]`, `quality: {unparsedRecords: number}`。
測定は日時・項目・機器・ID順。`healthplanet.json`は日内の全測定を保持する。
`daily.json`の正規系列は体重・体脂肪率だけHealth Planetの各日最終測定を採用し、
それ以外はGoogleを採用する。Googleの体重・体脂肪の原本とtyped storeは削除しない。
測定IDがないためIDは元レコードと応答内の出現回数のハッシュ。上流修正の観測版も保持する。
timestampはオフセットを推測しないcivil日時。未知項目や非有限値は原本に残し、
投影できなかったレコード数をqualityへ記録する（再走査も含む応答ごとの合計）。
プロフィール・未知フィールド・原本・tokenは公開用JSONへ含めない。
SQLiteの読み取りsnapshotはGoogle DBとは独立し、取得状態・日時はproviderごとに示す。
`available`は要求区間の成功を表し、全履歴の保証ではない。

Tasks 8/9 と Next.js の共有契約。以下の TypeScript 型が JSON の具体的な構造を定義する。
すべての数値は有限値。欠損・NaN・Infinity は `null`。日付は `YYYY-MM-DD`。

```typescript
export type Period = "30" | "90" | "180" | "365" | "all";
export type Snapshot<T> = { schemaVersion: 1; generation: string; data: T };
export type Meta = {
  schemaVersion: 1; generation: string; generatedAt: string;
  basePath: string; // generations/<safe-id>/
  files: Record<string, string>; // key=relative path, value=same relative path
  freshness: { archiveStatus: string; projectionStatus: string };
};
export type Daily = {
  dates: string[]; // sorted, every civil day between first/last saved daily row
  series: Record<string, (number | null)[]>; // every column has dates.length
  units: Record<string, string>;
  providers?: Record<string, "google" | "healthplanet">; // absent in older snapshots
};
export type SleepSession = {
  provider_id: string; date: string; start_ts: string | null; end_ts: string | null;
  minutes_asleep: number | null; minutes_deep: number | null;
  minutes_light: number | null; minutes_rem: number | null;
  minutes_wake: number | null; efficiency: number | null; is_main: boolean | null;
};
export type Sleep = { sessions: SleepSession[]; timeBasis: "civil" };
export type Intraday = {
  date: string; metric: string; timeBasis: "civil";
  timeUnit: "microseconds_since_local_midnight";
  points: [number, number | null][];
};
export type IntradayIndex = {
  metrics: Record<string, { unit: string; days: {
    date: string; path: string; count: number;
  }[] }>;
};
export type Baseline = {
  date: string; value: number | null; baseline: number | null;
  sd: number | null; z: number | null;
};
export type Correlation = {
  x: string; y: string; lag: number; n: number; spearman: number | null;
  reason: "insufficient_pairs" | "constant_series" | null;
};
export type CoverageDay = { date: string; has_data: boolean };
export type Analytics = {
  baselines: Record<string, Baseline[]>;
  movingAverages: Record<string, { date: string; value: number | null }[]>;
  periods: Record<Period, {
    startDate: string | null; endDate: string | null;
    correlations: Correlation[];
    coverage: Record<string, CoverageDay[]>;
  }>;
  socialJetlag: {
    hours: number | null; scope: "all_saved_sleep";
    firstDate: string | null; lastDate: string | null;
  };
};
export type SourceCoverage = {
  stream_id: string; data_type: string; label: string; representation: string;
  status: string; method: string | null;
  requested_start: string | null; requested_end: string | null;
  history_complete: boolean;
  intervals: { start: string | null; end: string | null; status?: "complete" | "empty" }[];
  pages: number; points: number; last_attempt_at: string | null;
  stored_pages: number; stored_points: number;
  reason: string | null; http_status: number | null; projection_status: string;
};
export type Inventory = {
  sources: SourceCoverage[];
  series: { metric: string; storage: "daily" | "intraday" | "sleep";
    n: number; first_date: string | null; last_date: string | null; unit: string }[];
  quality: { path: string; reason: "non_finite_number"; count: number }[];
};
```

## ファイルと読み込み

root `meta.json` のみ envelope なし。他の全ファイルは `Snapshot<T>`。
`files` は `analytics.json`, `daily.json`, `intraday-index.json`, `inventory.json`,
`sleep.json` と全日内ファイルを辞書順で列挙する。値は generation 相対パス。
loader は最初に meta を読み、`basePath + files[key]` から同じ generation のみ読む。
`generation` は `[A-Za-z0-9][A-Za-z0-9_-]{0,127}`。既存 ID は上書きしない。
全ファイル完成後、最後に meta を atomic replace。失敗時は前の meta と generation を維持する。
`generatedAt` は timezone 付き ISO 8601。これは測定日時ではない。

## 17日次系列・単位・7ページ

| Series | Unit | 主なページ |
|---|---|---|
| steps | steps | 概要・活動・気づき |
| distance_km | km | 活動 |
| calories | kcal | 活動 |
| minutes_lightly_active / minutes_fairly_active / minutes_very_active | min | 活動 |
| weight_kg（Health Planet各日最終測定） | kg | 身体 |
| fat_pct（Health Planet各日最終測定） | % | 身体 |
| resting_hr | bpm | 概要・心臓・気づき |
| hrv_rmssd / hrv_deep_rmssd | ms | 心臓・気づき |
| spo2_avg / spo2_lower_bound / spo2_upper_bound | % | 身体 |
| temp_skin_relative | °C | 身体・気づき |
| breathing_rate | breaths/min | 身体 |
| sleep_minutes | min | 概要・気づき |

睡眠ページは `sleep.json`、棚卸しページは `inventory.json`。日内 `hr` は bpm、
`steps` は steps。未知の typed metric も保持し、単位不明は `unknown` とする。
日内データは型付き projection の全点。source-level raw archive の代用ではない。
同時刻 source の統合は既存 Store の責務で、export は独自の集約・間引きをしない。

## 分析と睡眠の意味

- `baselines` は resting_hr / hrv_rmssd / temp_skin_relative。全履歴で既存
  `rolling_baseline_z` を計算してから UI が表示期間を切り出す。
- `movingAverages.steps` は7暦日平均。`movingAverages.sleep_main_minutes` は
  主睡眠 session の minutes_asleep の7暦日平均。欠損を0にしない。両者とも全履歴で計算。
- 相関は sleep_minutes→resting_hr、sleep_minutes→hrv_rmssd、steps→sleep_minutes、
  lag 0/1/2/3。日次全体の最終日を共通 end とし、両方の日が期間内にある組を使う。
  20組未満は null + insufficient_pairs、一定系列は null + constant_series。
- 各期間は閉区間 `[end-(days-1), end]`。coverage は全日次系列の各暦日の記録有無。
  `all` は最初から最後の保存日。日次が空なら日付 null・coverage 空配列。
- socialJetlag は全保存睡眠を既存関数へ渡す（内部で主睡眠を選択）。平日・土日
  それぞれ2晩未満なら null。firstDate/lastDate は入力の全保存睡眠範囲。
- SleepSession は Store の実際の11列を保持。start_ts/end_ts は offset なしの
  ISO civil timestamp（マイクロ秒を保持）。主睡眠グラフは `is_main === true`。
  昼寝を捨てず、ステージ null を0や架空ステージに変換しない。日次 sleep_minutes は昼寝込み。
  duration・efficiency・曜日平均・前日正午基準の就寝起床区間は session から描画できる。

## 棚卸し・品質・プライバシー

SourceCoverage は ArchiveIndex.coverage() の snake_case に一致。intervals の start/end は
成功した確認範囲。raw 本文・cursor・request・token・絶対パスは出力しない。
`pages` / `points` は最新試行の件数。`stored_pages` / `stored_points` は同じ stream の
全試行を通じた保存総数（legacy を含む）。保存ページ数は失敗レスポンスも含む観測件数で、
同じ内容を再取得した場合も数える。保存 point 数は成功レスポンスの既知の解析件数の合計で、
未解析・legacy の不明件数は0寄与とする。どちらも一意な健康記録数や全履歴完了の証明ではない。
detail prototype の保存総数は子 resource stream の保存総数の合計。prototype と子を
さらに合算すると重複する。pending の保存総数は両方0。後続試行の失敗で過去の保存総数は減らない。
reason はエラー本文を転送せず status から安全な説明へ変換する。
ArchiveIndex が未導入の旧 DB では source inventory をメモリ上で pending として構築し、
DB の schema/migration/書き込みを行わない。旧 projection が存在しても原本の取得完了にはしない。
series は実保存 typed 行の件数・期間（NULL 値を含む行数）。日次・日内・睡眠を区別し、
睡眠行は metric=sleep_sessions、unit=sessions。原本 page/point 件数とは別。
quality は非有限 typed 数値が存在したファイルと件数。通常の欠損 null は品質エラーとしない。
freshness.archiveStatus は legacy_json を除いた取得 stream が存在し、すべての
history_complete が真で状態が complete/empty のときだけ
complete、未試行は pending、その他は partial。projectionStatus は typed データありで available、
なしで empty（同期完了や最新性を意味しない）。新規 directory は0700、ファイルは0600。
