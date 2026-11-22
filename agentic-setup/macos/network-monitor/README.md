# macOS のネットワーク疎通監視

ユーザーの断続的な通信停止・遅延を切り分けるための、小さな定期バッチ。
Python 標準ライブラリ、macOS 標準の `ping` / `dig` / `curl`、CoreWLAN の
読み取り専用 Swift ヘルパーを使う。定期実行に LLM や API キーは使わない。

## 動作

- 15 秒ごとに既定ゲートウェイと外部 2 宛先へ各 2 回 ping。
- 60 秒ごと、および ping 欠落時に DNS と 4 宛先の HTTPS を検査。
  詳細検査の最短間隔は 15 秒。全コマンドにタイムアウトを付ける。
- HTTPS は毎回新規接続。DNS / 接続 / TLS / 初回応答 / 全体の時間を記録。
  API の 401 / 404 は疎通できた応答として扱い、正常な API 操作とは区別する。
- Wi-Fi の RSSI、ノイズ、チャンネル、帯域幅、リンク速度を記録。
  周囲の電波スキャンや設定変更は行わない。SSID / BSSID / MAC は収集しない。
- IPv6 が利用可能な場合だけ IPv6 HTTPS も検査。未提供を障害扱いしない。
- ping 欠落だけでは回線障害と判定せず `probe_loss_only` と記録。
  複数宛先の HTTPS 失敗は `*_suspected` とし、原因の断定とは区別する。
- 条件変化、経路・Wi-Fi チャンネル変化、再起動・スリープ等の観測欠損を
  別のイベントにする。観測欠損の時間を通信障害時間に加算しない。
- **5 分ごとに実効速度を測定**。Cloudflare に下り 2 MB・上り 1 MB の
  合成テストデータを転送し、完了したバイト数 ÷ 所要時間から Mbps を算出。
  ユーザーのファイルは送らない。2 方向は順番に測り、失敗・途中終了を
  速度 0 と混同しない。別ジョブ・別ロックで疎通監視を止めない。
- 速度ジョブは `ProcessType=Standard`・通常 nice 値で実行する。
  macOS の Darwin background 状態ではネットワーク I/O 自体も抑制されるため、
  その状態を検出した測定は速度値として採用しない。方式変更前の試験記録も
  新方式の速度集計・比較基準から除く。
- 小容量・単一接続の実効速度であり、回線の最大容量を測る負荷試験ではない。
  同じ経路・同じデータ量の直近 24 時間の中央値と比較し、比較対象が 3 回以上
  ある場合は 30% 未満への低下を `below_recent_baseline` と記録する。
  基準不足の最初の測定は `measured` であり、速度正常という判定ではない。
- 最大要求データ量は通常約 864 MB/日（終日起動の場合）。異常終了も含め
  1 GB/日のテストデータ予算を開始時に予約する。ヘッダー等はこの予算外。
  回線変更後も適用されるので、従量制回線では下記の速度ジョブを停止する。

## 配置と起動

このディレクトリは復元・レビュー用。実行ファイルを Documents の外へ
コピーすることで、LaunchAgent の Documents アクセス制限を避ける。

| 用途 | 配置 |
|---|---|
| 実行コードと検証済みバックアップ | `~/Library/Application Support/NetworkMonitor/` |
| 日別ログ・最新状態 | `~/Library/Logs/NetworkMonitor/` |
| 自動起動設定 | `~/Library/LaunchAgents/com.ankimo.network-monitor.plist` |
| 速度測定の自動起動設定 | `~/Library/LaunchAgents/com.ankimo.network-speed.plist` |

```sh
python3 -m unittest discover -s agentic-setup/macos/network-monitor -v
python3 agentic-setup/macos/network-monitor/install.py
```

インストーラーは既存 plist の解析・対象キー確認、バックアップの SHA-256
照合、コードの構文検証、Swift のコンパイル、`plutil -lint` を先に行う。
成功した場合だけ配置・読み込みへ進む。読み込み後は `launchctl print` で
プログラムと疎通 15 秒・速度 300 秒の間隔を確認する。再インストール前にもバックアップする。

ログイン後に自動起動する。ログアウト・電源断・スリープ中は監視せず、
復帰後の観測欠損を記録する。端末や Codex のセッションに依存しない。
省電力設定やルーターの設定は変更しない。

## 状態と記録の確認

```sh
launchctl print "gui/$(id -u)/com.ankimo.network-monitor"
python3 "$HOME/Library/Application Support/NetworkMonitor/network_monitor.py" --report --hours 24
```

`latest.json` は最新状態。実行時の例外は容量固定の `last-error.json` に残る。
レポートの `monitor_fresh` が false のときは監視処理の停止も確認する。
`samples-YYYY-MM-DD.jsonl.gz` は各検査、
`events-YYYY-MM-DD.jsonl.gz` は変化の履歴。日付・時刻は日本時間。
圧縮 JSONL は gzip の連結メンバー形式で、Python の `gzip.open` で読める。
各周期を追記し、古いログを自動削除・上書きしない。
通常は概算で数 MB/日。ファイルは 600、ログディレクトリは 700。
ログや最新状態を Git に入れない。外部通知・メール送信は行わない。

## 純正ルーターの読み取り監視

`router_monitor.py` は BUFFALO WXR-5950AX12 の純正管理画面が使う参照処理だけを
利用する別プロセス。設定保存、再起動、Wi-Fi スキャン、大容量転送は実行しない。

- 60 秒ごとに接続台数・端末別通信量・WAN/2.4 GHz/5 GHz の表示カウンターを記録。
- 300 秒ごとに既存ルーターログを取得し、重複を除いて Mac に追記保存。
  syslog 転送設定を変えずに収集する。ルーター停止直前の未取得ログまでは保証しない。
- 正常パケット数やエラー数はルーターの表示値。高速化機能などによる集計範囲の
  制約があり、パケット損失率や無線占有率そのものではない。
- 管理パスワードは macOS キーチェーンの `com.ankimo.network-router` / `admin`。
  Swift 補助プログラム内で RSA 暗号化し、Python に平文を返さない。
- 初回登録は補助プログラムの標準入力で行う。パスワードをコマンド引数・環境変数・
  設定ファイル・ログに含めない。既存のキーチェーン項目は自動上書きしない。
- 端末別サンプルに端末名・MAC・IP・SSID は記録せず、端末はローカル鍵による
  匿名 ID で識別する。既存ログの文面では MAC・IP・既定 SSID・認証項目を伏せる。
  任意のホスト名等まで完全に匿名化する保証はないため、ログは Mac 内だけに保存する。
  接続先は既定ゲートウェイ・機種・公開鍵等で照合する。ARP が参照できる環境では
  MAC のハッシュも照合し、参照できなければ Cookie 送信前に公開鍵を匿名接続で照合。
- 認証の失敗やセッション喪失時は 15 分間ログインを再試行しない。キーチェーンが
  読めない場合も対話 UI を要求せず `unavailable` を記録する。
- `router-monitor.json` は実行先だけの非公開設定。機種・ゲートウェイ・鍵のハッシュと
  匿名化用の鍵を保存する。ルーターが変わった場合に自動で認証先を変更しない。

復元用ソースはこのディレクトリ、実行先とログは従来の NetworkMonitor と同じ。
`install_router_monitor.py --prepare` はコードと認証補助だけを配置し、
初回のキーチェーン登録・接続先の照合設定後に次を実行する。

```sh
python3 agentic-setup/macos/network-monitor/install_router_monitor.py
launchctl print "gui/$(id -u)/com.ankimo.network-router"
```

インストーラーは既存設定の解析、実機での読み取り、バックアップのハッシュ照合を
完了してから起動設定を反映する。既存の疎通・速度ジョブは再読み込みしない。
キーチェーンの識別情報を保つため、認証補助のバイナリーは同一ソースなら再生成しない。
ソース・配置済みバイナリーのハッシュが変わっている場合は自動更新せず停止する。

`router-latest.json` / `router-samples-YYYY-MM-DD.jsonl.gz` が台数・通信量・表示カウンター、
`router-events-YYYY-MM-DD.jsonl.gz` が取得したルーターログ。
`router-log-seen.json` は重複防止用のハッシュだけを保持する。

`speed-YYYY-MM-DD.jsonl.gz` と `speed-latest.json` が速度測定、
`speed-error.json` が速度ジョブ内部のエラー。レポートの `throughput` に
最新の Mbps・最小・中央値・最大・失敗回数・相対低下回数が含まれる。
疎通の `healthy` は速度の正常性を保証しない。速度テストに重なった疎通検査は
`speed_test_overlap` を付け、自分の負荷と区別できるようにする。

ネットワーク障害と、launchd の権限不足でコマンドが失敗するケースは区別が
必要。導入時は実際の LaunchAgent が生成した複数周期のログを検証する。

## 一時停止・再開

```sh
launchctl bootout "gui/$(id -u)/com.ankimo.network-monitor"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.ankimo.network-monitor.plist"
# 速度測定だけを停止・再開
launchctl bootout "gui/$(id -u)/com.ankimo.network-speed"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.ankimo.network-speed.plist"
```

管理画面の認証情報・実機固有の識別情報は Git に含めない。DFS と WAN のどちらが原因かの確定には、
発生時刻に対応するルーター側ログや、有線端末との比較が別途必要。

## 導入時の検証（2026-11-15）

- 誤判定、DNS 障害、IPv4 のみの障害、スリープ・再起動欠損、追記、排他、
  状態ファイル破損時の停止、HTTPS 異常後の再検査を含む 13 テストが成功。
- 実際の LaunchAgent が 15 秒間隔で複数回正常終了し、LAN / DNS / HTTPS /
  CoreWLAN の値を取得。実行コードと復元元のハッシュ、plist 構文・読み込み、
  更新前バックアップのハッシュも確認。
- 初期の監視では長い通信停止を再現せず。前夜からの Mac のログにも明確な
  新規切断・レーダー検知記録は見つからず、原因は未確定。
  数分以上続く症状のため、DFS だけに絞らずルーターの WAN 再接続等も照合する。
- 実効速度追加後は計 23 テストが成功。実際の速度 LaunchAgent が通常優先度・
  Darwin background=false で上下り転送を完了し、300 秒間隔で登録されていること、
  既存の 15 秒監視が継続していることを確認。

2026-11-16 のルーター監視追加では計 35 テストが成功。実機のキーチェーン認証、
毎分の自動収集、5 分周期の既存ログ取得・重複排除を確認した。
起動設定の解析・配置前バックアップ・配置後の実プロセスとソースの照合も実施。
ルーター設定は変更しておらず、導入作業中および導入後の観測範囲では
LAN 応答欠落・DNS 失敗・HTTPS 接続失敗はいずれも 0 件だった。

launchd の仕様は [Apple の定期実行ガイド](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html)
と、対象 Mac の `man launchd.plist` を参照。

速度の送受信 API は [Cloudflare の公開仕様](https://github.com/cloudflare/speedtest/blob/main/README.md)
に基づく。ブラウザ版の負荷試験一式や結果送信機能は使わず、限定サイズの
GET / POST のみ行う。
