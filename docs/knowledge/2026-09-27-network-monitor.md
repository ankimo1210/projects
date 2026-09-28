# Windows のネットワーク状態を記録する

確認日: 2026-09-28（両スクリプトの静的照合と PowerShell 構文検査。今回、実ネットワーク測定は未実施）。

[network-monitor.ps1](network-monitor.ps1) は、既定の IPv4 ルートのアダプターを選び、
ゲートウェイと外部宛ての ping、DNS、HTTPS、ダウンロード速度、アダプターの通信量とエラー数を CSV に追記する補助ツールです。
[network-ping-monitor.ps1](network-ping-monitor.ps1) は、ゲートウェイ・Cloudflare・Google への ping を同時に送り、
1 秒単位の結果とアダプターの通信量を日別 CSV に記録します。
有線接続の不調調査を想定していますが、アダプターを有線に限定する実装ではありません。

## 実行

Windows PowerShell で実行します。詳細監視には Windows の `curl.exe` も必要です。WSL の Bash では実行しません。
PowerShell で、スクリプトのある `docs/knowledge` ディレクトリを開いて実行します。
WSL 内のチェックアウトを Windows から開く場合は、そのチェックアウトに対応する UNC パスを使ってください。

```powershell
# 約1分ごとに5回。ダウンロード測定は無効（ping / DNS / HTTPS 通信は行う）
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\network-monitor.ps1 -MaxSamples 5 -DownloadEverySamples 0

# 既定設定で継続。終了は Ctrl+C
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\network-monitor.ps1

# 1秒ごとの ping を5回だけ記録。継続する場合は -MaxSamples を外す
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\network-ping-monitor.ps1 -MaxSamples 5
```

### 詳細監視 `network-monitor.ps1`

| 引数 | 既定値 | 意味 |
|---|---|---|
| `-IntervalSeconds` | 60 | 測定開始の間隔（秒）。測定自体が長ければ間隔も延びる |
| `-MaxSamples` | 0 | 0 は無制限。正数なら指定回数で終了 |
| `-DownloadEverySamples` | 30 | 初回と以後30サンプルごとにダウンロード測定。0 で無効 |
| `-DownloadBytes` | 10000000 | 1回の転送量（10 MB） |
| `-LowSpeedThresholdMbps` | 150 | Cloudflare の速度がこれ未満、または測定不能なら Google でも確認 |
| `-OutputPath` | `%LOCALAPPDATA%\NetworkMonitor\network-history-detailed.csv` | CSV の出力先。既存ファイルには追記 |

既定の Cloudflare ダウンロード量は約480 MB/日です（60秒間隔で連続稼働した場合）。
低速または測定不能の回には Google の配布ファイルの先頭 10 MB を追加取得するため、最大で約960 MB/日です。
測定先は ping が `1.1.1.1`、DNS が Cloudflare、HTTPS が Cloudflare と Google、通常のダウンロードが `speed.cloudflare.com` です。
ping は各対象3回で損失率と遅延を計算し、HTTPS は応答コード・接続段階ごとの時間・総時間を記録します。

### 1秒 ping `network-ping-monitor.ps1`

| 引数 | 既定値 | 意味 |
|---|---|---|
| `-IntervalSeconds` | 1 | 測定開始の間隔（秒）。処理が長ければ間隔も延びる |
| `-PingTimeoutMs` | 900 | 各 ping のタイムアウト（ミリ秒） |
| `-MaxSamples` | 0 | 0 は無制限。正数なら指定回数で終了 |
| `-OutputDirectory` | `%LOCALAPPDATA%\NetworkMonitor` | 日別の `network-ping-detailed-YYYYMMDD.csv` の保存先 |

3対象へ同時に ping を送り、応答状態・往復時間とアダプターの通信量を記録します。
日付が変わると Windows のローカル時刻に従って出力ファイルが切り替わります。

## 結果の読み方と限界

- ゲートウェイへの損失と外部への損失を見比べ、ローカル区間とその先の切り分けに使う。
- ping の損失だけでは断線と断定しない。ICMP の制限もあるため DNS / HTTPS と併せて見る。
- ダウンロード欄の空欄は、測定しなかった回または失敗。0 Mbps と同一視しない。Google の再測定は Cloudflare の値が低速または測定不能の回だけ行う。
- 監視するアダプターとゲートウェイは起動時に決まる。回線を切り替えたら再起動する。
- CSV には端末のネットワーク情報が含まれる。公開リポジトリには測定結果を追加しない。
