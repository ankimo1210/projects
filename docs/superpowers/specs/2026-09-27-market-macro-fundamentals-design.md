# 工程3b: マクロ・財務データの時点別取得

更新日: 2026-09-27。承認済みの[統合仕様](2026-09-27-market-research-design.md) §5.2、F06–F07、Q06–Q08を実装できる粒度へ補う。
[価格取得・保存](../plans/2026-09-27-market-data-ingestion.md)の不変snapshot、HTTPの上限・秘匿、明示取得とオフライン読取を使う。
目的は、過去の意思決定時点に利用できた版と、後に分かった改定値を同じ値として扱わないこと。

## 採用範囲

| 系列 | 新入口で扱う情報 | 時刻の根拠と vintage_kind | 今回の境界 |
|---|---|---|---|
| ALFRED | 指定series・期間の全realtime版。`.`は欠損 | `realtime_start` は**日付だけ**。その日の終了後（翌日00:00 America/New_York）から利用可能とする保守的な時刻、`estimated`。元の日付を別保持 | `limit/offset/count` を追い、狭い窓の先頭を初回公表と呼ばない |
| ESRI GDP | 公表カレンダーと、指定回の速報CSVが含む全四半期 | XMLのJST公表分を `actual`。将来予定は数値と分離。CSV URLはメニューのラベルとstemから発見 | 参考系列 `knritu` を混入させない。未取得回から期待値を確定しない |
| MoF JGB | 履歴CSVと当月CSVを併合した指定年限 | CSVに行ごとの公表時刻がないため、取得完了時刻からの `snapshot`。基準日を公表日としない | 両CSV成功時にだけ完成。欠損年限はゼロ補完しない |
| e-Stat | 明示した統計表IDと分類コードの単一系列 | APIにrealtime版がないため完成snapshotの取得時刻からの `snapshot` | VALUEの分類・単位・時刻コードを照合し、曖昧なら拒否。NEXT_KEYで継続 |
| SEC companyfacts | 明示したCIK・taxonomy・concept・unitの10-K/10-Qファクト | `filed` は日付だけ。翌日00:00 America/New_Yorkからの `estimated`。`accn`を版IDに保持 | 会計対象期と提出日を分離。単位・期間・formの違いを混ぜない |

根拠: [ALFRED観測API](https://fred.stlouisfed.org/docs/api/fred/series_observations.html)、[ESRI公表予定](https://www.esri.cao.go.jp/jp/sna/kouhyou/kouhyou_top.html)、[MoF金利Q&A](https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/qa.htm)、[e-Stat API 3.0](https://www.e-stat.go.jp/api/api-info/e-stat-manual)、[SEC companyfacts](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)と[アクセス条件](https://www.sec.gov/about/webmaster-frequently-asked-questions)。上表の保守的な時刻は、この仕様からの**実装上の推定**であり、実際の公表分を示すものではない。

## 契約と保存

- `MacroObservation` は既存の指標・期間・source・release_at・vintage_idに加え、単位、頻度、季調、公表時刻の精度、元の公表日、取得時刻、raw hash、source_refを任意フィールドとして持つ。既存の合成デモ呼出は維持する。`snapshot` の release_at は完成データの取得完了時刻。`estimated` の日時は実測と区別する。
- 財務は別契約 `FundamentalObservation`。CIK、taxonomy、concept、unit、対象期の始終、filed日、form、accession、利用可能時刻、取得時刻、raw hash、値を保存する。CIK単位の値と数値単位を混ぜない。
- マクロ・財務を価格と同じDuckDBのmanifest、raw SHA256、行transactionへ結び付ける。取得元・ID・期間・分類・単位・正規化版をcache keyに含める。完成manifestだけを読取対象とし、競合行はbatch全体を戻す。部分ページとcursorを保管しても完成した値や期待値として公開しない。
- `as_of` はUTC化可能な日時を必須とし、その時刻に利用可能だった版を返す。`latest` は明示的な別操作。ALFRED・ESRI・SECの歴史版は公表日/提出日に基づく保守的な時刻を使う。MoF・e-Statは収集を始めた時点以降だけをPITとして扱う。
- ESRI公表カレンダーは取得時点の予定と実績を区別して保管し、時点より前の取得版を参照する。予定を過ぎただけで実績へ自動昇格させない。
- `FRED_API_KEY`、`ESTAT_APP_ID`は環境変数から取得。SECは識別可能な `SEC_USER_AGENT` を必須とする。鍵・User-Agentの個人部分、URLクエリ、response bodyをログ・例外・manifestへ含めない。e-Stat応答が入力パラメータを反復しても認証値を除去して保存する。

## 利用と受入

- CLIは `fetch-macro`、`macro`、`fetch-fundamentals`、`fundamentals`、`releases` を明示操作として追加。読取コマンドは通信しない。取得失敗時の古い完成snapshot利用は `--allow-stale` に限定し、失敗理由と取得時刻を表示する。
- Q06: 公表・提出の直前、同時、直後で読み、過去期の改定とnaive日時を検査。
- Q07: 同じ版の冪等性、値が異なる同一版の競合、狭いALFRED窓、e-Stat途中ページの再開、完成前の読取拒否。
- Q08: ESRIのJST公表時刻と予定、年末年始の境界、GDP途中取込、e-Statの月/年コードと次ページを検査。期待値計算は工程3cで接続し、未完成を確定値として使わないことを工程3bのゲートにする。
- 外部キーや本人識別を要するライブ疎通は、環境に設定済みの場合だけ行う。公開ESRI/MoFの小範囲疎通はfixture検証と分けて記録。実レスポンスや個人口座データをGitへ入れない。

既存の [`macrokit`](../../../macrokit/README.md)・[`quantkit`](../../../quantkit/README.md)は比較用に読む。新入口の常設依存にはしない。BLS/BEA/Census/BoJ/EDINET、分析画面、旧入口切替、既存DB移管は後続工程。
