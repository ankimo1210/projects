# 日内データの実時間を保持する

## 目的と承認

Google Fitbit データの同期で、時差の変化により現地時刻が重複しても、異なる観測を欠落させない。ユーザーの `resume` は、直前に提示した保存方式の修正と既存 DB の移行への承認として扱う。個人データ、認可情報、実データの値を公開文書に含めない。

## 契約

- `physicalTime` / interval の `startTime` を UTC の観測識別子にする。現地時刻と明示された UTC offset も保持する。同じ UTC の二重観測は引き続きエラーにし、勝手に選択・平均しない。
- physical time がない旧レスポンスは、現地時刻と明示 offset が両方あれば UTC を復元する。現地時刻だけなら UTC を不明のまま保存する。タイムゾーンを推測しない。
- 旧 `intraday(metric, ts, value)` はトランザクション内で移行し、元テーブルを `intraday_legacy` として保持する。移行前に private な DB バックアップを作る。繰り返し開いても再移行しない。
- 保存済みの完全な raw JSON またはアーカイブから、日ごとに offline で再構築する。ページの欠落、継続 token、HTTP 失敗、解析エラーがある入力を完全とは扱わない。原本・過去の失敗記録を変更しない。
- 再構築は日ごとの typed 行だけを置き換える。日次・睡眠・他プロバイダー、raw JSON の取得日時、他メトリクスの checkpoint を維持する。checkpoint は既存の到達日から連続して完全に復元できた範囲だけ進める。
- 日内 JSON は UTC が全点で判明する日には UTC の epoch microseconds を横軸に使い、現地時刻・offset を並行配列で保存する。旧 civil 形式も読める。UTC が一部不明の日は civil 形式で保持する。
- 画面は UTC の時間軸と、元の現地時刻・offset の tooltip を使う。旧形式は現地時計表示を維持する。ズーム・間引きは実時間に従い、保存値を変更しない。

## 完了条件

合成データによる重複時計・厳密な二重観測・旧 DB 移行・再実行・不完全原本・checkpoint の穴の回帰テスト、health の Python 一式、Web の typecheck/lint/test/build が通る。コピー DB で検証した後、現用コードへローカル統合し、実 DB をバックアップ・再構築・export して件数と JSON 契約を確認する。全履歴の取得完了やリモートへの公開は範囲に含めない。

## 仕様の根拠

[Google Health v4 DataPoints](https://developers.google.com/health/reference/rest/v4/users.dataTypes.dataPoints) の ObservationSampleTime は physicalTime、utcOffset、civilTime を別の項目として定義する。Python/DuckDB の既存精度に合わせ microseconds を保持し、nanoseconds 以下の精度向上は今回の対象にしない。
