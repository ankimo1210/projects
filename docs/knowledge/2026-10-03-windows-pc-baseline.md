# Windows PC の基準構成

確認日: 2026-10-03。ローカル LLM、CUDA、WSL と Docker、PC のアップグレードを相談するときの基準。
Windows の CIM / PnP / インストール情報、WSL 内のコマンド、メモリコピー測定から記録した。
構成変更時は変更した項目と確認日を更新する。障害調査では関係する項目の現在値を再確認する。

## 本体

| 項目 | 確認した構成 |
|---|---|
| CPU | Intel Core Ultra 9 285K、24 コア / 24 スレッド |
| GPU | NVIDIA GeForce RTX 5080、16 GB GDDR7。GPU のメーカー別製品型番は未特定 |
| 内蔵 GPU | Intel Graphics |
| マザーボード | ASUS ROG STRIX Z890-A GAMING WIFI、Rev 1.xx |
| BIOS | American Megatrends、3305、2026-07-27 付 |
| メモリ | G.SKILL DDR5、32 GB × 2、合計 64 GB。OS の型番表示は `F5-6400J3239G32G` |
| メモリ速度 | Windows の `ConfiguredClockSpeed` / `Speed` は両方とも 4800 MT/s。BIOS 写真の DRAM Freq. も 4800 MHz と表示 |
| 内蔵 SSD | Samsung SSD 990 PRO 2TB、NVMe |
| 外付け SSD | USB 接続、1 TB。OS の表示は `ASMT 2462 NVME`。SSD 本体のメーカー / 型番は未特定 |
| 電源とケース | 型番未確認 |
| スリープ | S3、休止状態、高速スタートアップに対応。S0 Modern Standby は利用不可 |

メモリは Channel A / B に各 1 枚認識され、各モジュールの DataWidth は 64 bit。
この情報だけでは実行時のチャネル動作やタイミングを確定できない。完全な販売型番の末尾も未特定。

## モニターと周辺機器

| 項目 | 確認した構成と状態 |
|---|---|
| モニター | Dell UltraSharp U4025QW、40 型曲面。実行時の表示は 5120 × 2160、120 Hz、DisplayPort 接続。アクティブなモニターは 1 台 |
| キーボード | HHKB Studio。USB の識別名は `HHKB-Studio`、Bluetooth の登録名は `HHKB-Studio1` |
| マウスと受信機 | HID 準拠マウス、Logicool LIGHTSPEED Receiver を認識。マウスの製品型番や受信機との対応は未特定 |
| USB ハブ | `Anker USB-C Hub` を認識。具体的な製品型番は未特定 |
| 冷却機器 | USB の識別名は `NZXT Kraken Base`。具体的な型番 / ラジエーターサイズは未特定 |
| 照明機器 | NZXT RGB Controller、ASUS AURA LED Controller |
| 充電機器 | Apple Watch Magnetic Charging Cable |
| オーディオ | Realtek USB Audio、Realtek Digital Output、NVIDIA High Definition Audio |
| Bluetooth 登録 | AirPods Pro（世代未特定）、iPhone 16 Pro（登録名から判別）、Xbox Wireless Controller、HHKB Studio |
| 有線 LAN | Intel Ethernet Controller I226-V。確認時は Up、リンク速度 1 Gbps |
| Wi-Fi | Intel Wi-Fi 7 BE200 320MHz。確認時は Disconnected |
| Bluetooth アダプター | Intel Wireless Bluetooth |

PnP での認識や Bluetooth の登録は、現在接続中 / 使用中であることを保証しない。
モニターの製品仕様は [Dell U4025QW](https://www.dell.com/en-us/shop/dell-ultrasharp-40-curved-thunderbolt-hub-monitor-u4025qw/apd/210-bmdp/monitors-monitor-accessories) を参照。

## Windows と主要ソフトウェア

Windows 11 Home、64 bit、ビルド 26300。`wsl --version` が報告した Windows バージョンは `10.0.26300.9550`。
以下はインストール登録 / Appx パッケージ情報。実際の使用頻度や PATH で選ばれる実行ファイルは確認していない。

| 分類 | 主なソフトウェアと登録バージョン |
|---|---|
| AI | Codex Desktop 26.930.3748.0、Claude Desktop 2.19675.0.0、OpenCode 1.18.30、Ollama 0.34.0 |
| エディターと IDE | VS Code 1.140.0、Cursor 3.19.7、Visual Studio Community 2022 17.14.37 |
| ターミナル | PowerShell 7.6.6、Windows Terminal 1.24.11911.0 |
| 開発 | Git 2.55.0.3、GitHub Desktop 3.6.5、Node.js 22.23.2、Anaconda 2024.10-1（Python 3.12.7） |
| .NET | SDK 9.0.316 を `dotnet --list-sdks` で確認。各種ランタイムも登録あり |
| コンテナ | Docker Desktop 4.90.0 |
| GPU | NVIDIA ドライバー 617.14（`nvidia-smi` でも確認）、NVIDIA App 11.0.9.251、NVIDIA AI Workbench 0.157.15-13 |
| CUDA | Toolkit 12.9 / 13.3 / 13.4 が登録。旧 11.8 の構成要素も残存 |
| ブラウザー | Chrome 154.0.8037.93、Edge 154.0.4258.48 |
| Office と PDF | Office Home and Business 2021（16.0.20326.20158）、Adobe Acrobat 26.002.21931 |
| 制作 | Blender 5.2.1、Unity Hub 3.21.2 |
| 連絡 | Teams 26198.304.4946.9672、Discord 1.0.9204、LINE 26.2.0.3894、Zoom Workplace 7.1.9 |
| 同期とリモート接続 | Google Drive 132.0.0.0、OneDrive 26.173.0906.0008、iCloud 15.10.39.0、Tailscale 1.102.4、Chrome Remote Desktop、Citrix Workspace 2603 |
| ハードウェア管理 | Armoury Crate 6.5.14.0、AURA Creator 4.5.5.0、NZXT CAM 4.76.5、Logicool G HUB 2026.6.981214、HHKB Studio キーマップ変更ツール 1.1.0.4、Samsung Magician 9.0.2.500 |
| 診断 | HWiNFO 8.50、AIDA64 7.70 / 8.35 が登録、ROG CPU-Z 2.20.2、3DMark Demo |
| その他 | PowerToys、Steam、Epic Games Launcher、Apple Music、Apple Devices、IBKR Desktop、Trader Workstation |

同日の[性能測定](2026-10-03-windows-pc-performance.md)で、Windows Anaconda の実行時 Python は 3.12.12、
PATH の `nvcc` は 13.3.73 と確認した。登録情報の Python 3.12.7 とは区別する。
WSL の PyTorch は 2.11.0+cu128 / 同梱 CUDA runtime 12.8 で GPU 演算が動作した。

## WSL 環境

| 項目 | 確認した構成 |
|---|---|
| WSL | 2.7.13.0、既定バージョン 2 |
| 既定ディストリビューション | `Ubuntu`、Ubuntu 24.04.4 LTS、Noble Numbat。確認時は Running |
| カーネル | `6.18.33.2-microsoft-standard-WSL2` |
| WSLg | 1.0.73.2 |
| アーキテクチャとシェル | x86_64、Bash |
| `.wslconfig` の設定 | `memory=48GB`、`processors=20`、`swap=16GB`、`autoMemoryReclaim=gradual` |
| Ubuntu 内の取得値 | 20 論理 CPU、MemTotal 約 47.04 GiB。swap の設定値に対する実行時容量は未確認 |
| 他のディストリビューション | `docker-desktop` と `NVIDIA-Workbench`、どちらも WSL 2。確認時は Stopped |
| リポジトリ | WSL: `/home/kazumasa/projects`、Windows: `\\wsl.localhost\Ubuntu\home\kazumasa\projects` |

Git とビルドは WSL の Linux パスで実行する。Windows 側のリンクや操作には対応する UNC パスを使う。

### Ubuntu 内の開発ツール

| ツール | 実行して確認したバージョン |
|---|---|
| Python | システムとワークスペース `.venv` はどちらも 3.12.3 |
| uv | 0.11.12 |
| Node.js と npm | 26.7.0、11.19.0 |
| Git | 2.43.0 |
| GCC と Make | 13.3.0、4.3 |
| CUDA nvcc | 12.0.140 |
| Codex CLI | 0.160.0。ログインシェルで確認 |
| Claude Code | 2.1.120 |
| Docker CLI | 確認時の Ubuntu では利用できず、WSL integration の案内を表示 |

Rust / Cargo、.NET、Swift、pnpm は、確認した通常シェル / ログインシェルの PATH で見つからなかった。
未インストールと断定する情報ではない。Windows と WSL のツールのバージョンを区別して調査する。

## メモリ帯域と改善候補

### 速度の報告値と理論帯域

2 チャンネルが動作する前提では、理論帯域は `転送速度 × 8 bytes × 2 channels`。
GB/s は十進単位（1 GB = 10^9 bytes）で示す。

| 設定 | 転送速度 | 理論上の最大帯域 |
|---|---:|---:|
| 現在の OS 報告値 | 4800 MT/s | 76.8 GB/s |
| 同じ型番系列の XMP 仕様 | 6400 MT/s | 102.4 GB/s |

同じ基本型番系列の [G.SKILL 仕様例](https://www.gskill.com/specification/165/374/1688609098/F5-6400J3239G32GX2-TZ5RW-Specification) は、
標準 SPD が 4800 MT/s / 1.10 V、XMP が 6400 MT/s / CL32-39-39-102 / 1.40 V。
実機の SPD / XMP プロファイル全体と BIOS の Ai Overclock Tuner 設定は未確認。
XMP が未有効である可能性はあるが、原因や 6400 MT/s での安定動作は確定していない。
理論上の増加は約 33.3%。アプリの処理速度が同じ割合で上がるとは限らない。

### WSL 上のコピー実測

Ubuntu のワークスペース Python 3.12.3 / NumPy 2.4.6 で測定した。
float64 配列を送信元 / 送信先それぞれ 256 MiB 確保し、ウォームアップ後に `numpy.copyto` を実行。
並列時は配列を各スレッドへ均等分割する。各測定で全体を 5 回コピーし、4 回の測定の中央値を採用した。
実効帯域は `2 × 配列 bytes × 5 / 経過秒` として、読み取りと書き込みの合計を数えた。

| スレッド数 | 中央値 GB/s | 最小 GB/s | 最大 GB/s |
|---|---:|---:|---:|
| 1 | 44.02 | 41.24 | 46.19 |
| 4 | 66.06 | 65.94 | 66.29 |
| 8 | 69.39 | 68.61 | 70.43 |

CPU、キャッシュ、WSL、背景負荷の影響を含むコピー測定。物理 DRAM の転送量や遅延を直接測定した値ではない。
設定を変えたら同じ測定条件と普段の処理時間で比較する。
この最初のコピー測定ではレイテンシを測っていない。
後続の[性能測定](2026-10-03-windows-pc-performance.md)に Windows / WSL のコピー帯域と依存ロードの遅延を記録した。

### 後で調べる項目

以下は候補で、設定変更や整理は未実施。

| 項目 | 次に確認すること |
|---|---|
| メモリ 4800 MT/s | 実機の XMP プロファイルを確認。`Ai Tweaker → Ai Overclock Tuner → XMP II` が候補。6400 MT/s での起動、メモリテスト、処理時間を確認する |
| CUDA の複数バージョン | 対象プロジェクトで選ばれる compiler / runtime / driver を確認。Windows と WSL の差や複数 Toolkit の登録だけで障害と断定しない |
| Ubuntu の Docker CLI | Docker Desktop の状態と Ubuntu の連携設定を確認。確認時は関連 WSL ディストリビューションが停止していた |
| 有線リンク 1 Gbps | 対向ポート、ハブ、配線経路を確認。NIC の表示名とリンク速度だけでは制約の場所を特定できない |

XMP はオーバークロック設定。[ASUS Z890 BIOS 説明書](https://dlcdnets.asus.com/pub/ASUS/mb/13MANUAL/E25597_ROG_STRIX_Z890_Series_BIOS_Manual_EM_WEB.pdf) の 19 ページでは、
XMP II は DIMM の完全な既定 XMP プロファイルを読み込む設定と説明されている。

## CPU・GPU・SSD・通信などの性能

同日の[性能測定記録](2026-10-03-windows-pc-performance.md)に、設定変更前の実測値、測定条件、
各試行の JSON、再測定用スクリプトを保存した。LLM の tokens/s、長時間の発熱、3D 性能などは未測定。
