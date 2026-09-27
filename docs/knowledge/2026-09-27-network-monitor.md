# Windows のネットワーク状態を記録する

確認日: 2026-09-27（スクリプトの静的照合。今回、実ネットワーク測定は未実施）。

[network-monitor.ps1](network-monitor.ps1) は、既定の IPv4 ルートのアダプターを選び、
ゲートウェイと外部宛ての ping、DNS、HTTPS、アダプターのエラー数を CSV に追記する補助ツールです。
有線接続の不調調査を想定していますが、アダプターを有線に限定する実装ではありません。

## 実行

Windows PowerShell と Windows の `curl.exe` が必要です。WSL の Bash では実行しません。
PowerShell で、このファイルとスクリプトのある `docs/knowledge` ディレクトリを開いて実行します。
WSL 内のチェックアウトを Windows から開く場合は、そのチェックアウトに対応する UNC パスを使ってください。

```powershell
# 約1分ごとに5回。ダウンロード測定は無効（ping / DNS / HTTPS 通信は行う）
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\network-monitor.ps1 -MaxSamples 5 -DownloadEverySamples 0

# 既定設定で継続。終了は Ctrl+C
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\network-monitor.ps1
```

| 引数 | 既定値 | 意味 |
|---|---|---|
| `-IntervalSeconds` | 60 | 測定開始の間隔（秒）。測定自体が長ければ間隔も延びる |
| `-MaxSamples` | 0 | 0 は無制限。正数なら指定回数で終了 |
| `-DownloadEverySamples` | 30 | 初回と以後30サンプルごとにダウンロード測定。0 で無効 |
| `-DownloadBytes` | 10000000 | 1回の転送量（10 MB） |
| `-OutputPath` | Windows の LocalAppData 配下 | CSV の出力先。既存ファイルには追記 |

既定のダウンロード量は約480 MB/日です（60秒間隔で連続稼働した場合）。
測定先は ping が `1.1.1.1`、DNS / HTTPS が Cloudflare、ダウンロードが `speed.cloudflare.com`。
ping は各対象3回で損失率と遅延を計算し、HTTPS は応答コード・初動時間・総時間を記録します。

## 結果の読み方と限界

- ゲートウェイへの損失と外部への損失を見比べ、ローカル区間とその先の切り分けに使う。
- ping の損失だけでは断線と断定しない。ICMP の制限もあるため DNS / HTTPS と併せて見る。
- ダウンロード欄の空欄は、測定しなかった回または失敗。0 Mbps と同一視しない。
- 監視するアダプターとゲートウェイは起動時に決まる。回線を切り替えたら再起動する。
- CSV には端末のネットワーク情報が含まれる。公開リポジトリには測定結果を追加しない。
