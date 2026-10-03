# Windows PC の性能測定

測定日: 2026-10-03、12:35:17–12:45:08 JST。[基準構成](2026-10-03-windows-pc-baseline.md) の設定変更前の比較用記録。
CPU・メモリ・GPU・SSD・小ファイル操作・通信・Windows / WSL の呼び出し時間を測定した。
以下は短い合成ベンチマークの実測値。表は明記した例外を除き、複数試行の中央値。
ウォームアップやキャッシュの条件は各節に記載した。

## 測定条件

| 項目 | 条件 |
|---|---|
| ハードウェア | Core Ultra 9 285K、RTX 5080 16 GB、DDR5 64 GB、990 PRO、USB NVMe |
| メモリ速度 | Windows の報告値は 4800 MT/s × 2 枚。XMP / BIOS は変更していない |
| 電源プラン | GameTurbo (High Performance) |
| Windows 計算環境 | Python 3.12.12、NumPy 1.26.4、MKL 2023.1-Product、24 論理 CPU |
| WSL 計算環境 | Python 3.12.3、NumPy 2.4.6、OpenBLAS 0.3.31.188.0、20 論理 CPU |
| GPU 計算環境 | WSL、PyTorch 2.11.0+cu128、同梱 CUDA runtime 12.8、NVIDIA driver 617.14 |
| GPU capability | 12.0。Windows PATH の nvcc は 13.3.73、WSL のシステム nvcc は 12.0.140 |
| 背景負荷 | 普段のアプリを開いたまま。事前の CPU 使用率は約 7%、GPU 使用率 0%、GPU メモリ約 2.2 GiB 使用 |
| 実行 | 項目を順番に測定。設定変更、新しい依存のインストール、アプリ停止はしていない |

異なる BLAS、Python / NumPy、スレッド数、ファイルシステムを含む環境比較。
Windows と WSL の差から、仮想化だけの影響を切り出すことはできない。
GB/s・MB/s は十進、GiB・MiB は二進。スループットは大きいほど、遅延は小さいほど速い。

## CPU

| 処理 | 単位 | Windows（最大 24 スレッド） | WSL（最大 20 スレッド） |
|---|---|---|---|
| FP64 行列積・1 スレッド | GFLOP/s | 78.29 | 75.77 |
| FP64 行列積・最大 | GFLOP/s | 1,053.04 | 838.79 |
| FP32 行列積・1 スレッド | GFLOP/s | 154.00 | 160.58 |
| FP32 行列積・最大 | GFLOP/s | 1,868.98 | 1,649.18 |
| SHA-256・1 スレッド | MiB/s | 4,566.73 | 4,176.56 |
| SHA-256・最大 | MiB/s | 43,866.66 | 41,481.33 |
| zlib level 6・1 スレッド | MiB/s | 64.16 | 78.96 |
| zlib level 6・最大 | MiB/s | 996.25 | 1,154.77 |

行列積は 2048 × 2048、`2n³ / 時間` で計算。1 回のウォームアップ後に 5 回測定し、BLAS のスレッド数を固定した。
SHA-256 と zlib は、シードを固定した圧縮しにくい 8 MiB のデータを使い、3 回測定。
並列時は各スレッドが同じデータを処理するため、キャッシュの影響を含む。
行列積の代表要素、ハッシュ、圧縮データの復元を検査した。

## メモリ

### 配列コピー

| スレッド数 | Windows GB/s | WSL GB/s |
|---|---|---|
| 1 | 43.85 | 46.72 |
| 4 | 65.38 | 65.03 |
| 8 | 71.31 | 69.81 |
| 最大（Windows 24 / WSL 20） | 70.95 | 59.16 |

float64 配列を送信元 / 送信先それぞれ 256 MiB 確保。各試行で全体を 5 回コピーし、4 回測定。
`2 × 配列 bytes × 5 / 時間` として読み取りと書き込みの合計を数え、コピー結果の全要素を検査した。
CPU、キャッシュ、OS、WSL を含む実効値で、物理 DRAM の転送量を直接測った値ではない。
今回の条件では 8 スレッド付近で頭打ちとなり、最大スレッド数へ増やしても速くならなかった。

### 依存するランダム読み出し

| 環境 | 中央値 ns / load |
|---|---:|
| Windows | 130.67 |
| WSL | 129.20 |

256 MiB の配列上で、64 byte ごとのノードをランダムな単一の輪につなぐ。
Numba のコンパイル後に 4,194,304 回の依存ロードを 3 回測定し、出発点へ戻ることを検査した。
キャッシュ、TLB、CPU のロード経路を含む遅延で、DRAM の CAS レイテンシを表してはいない。

## GPU

| 処理 | 入力 / 計数 | 中央値 |
|---|---|---|
| FP32 IEEE | 4096 × 4096 | 37.89 TFLOP/s |
| TF32 許可 | 8192 × 8192 | 59.10 TFLOP/s |
| FP16 | 8192 × 8192 | 118.34 TFLOP/s |
| BF16 | 8192 × 8192 | 118.97 TFLOP/s |
| VRAM 内コピー | 1 GiB × 2 配列、read + write | 819.09 GB/s |
| CPU → GPU | 128 MiB、pinned memory | 53.00 GB/s |
| GPU → CPU | 128 MiB、pinned memory | 39.13 GB/s |

行列積は dense、3 回のウォームアップ後、1 試行で 10 回、5 試行。FP32 IEEE は TF32 を使わない設定、TF32 行は許可する設定。
FP16 / BF16 の reduced-precision reduction は無効。代表要素を float64 計算と照合した。
FP32 とその他では行列サイズが異なるため、精度だけによる速度比とは解釈しない。
VRAM コピーは 20 回、CPU / GPU 間は 10 回を 1 試行として、5 試行。コピー結果の代表部分を検査した。

GPU は非同期に動くため、CUDA Event と同期によってデバイス上の経過時間を測った。
設定の意味は [PyTorch CUDA semantics](https://docs.pytorch.org/docs/2.11/notes/cuda.html) を参照。
これらは dense 行列積とコピーの値で、FP4 / sparsity の広告値や LLM の tokens/s とは別の指標。
クロック / 電力制限は変更せず、負荷中の温度やスロットリングは計測していない。

## SSD

| 場所 | 順次書込 MB/s | 順次読出 MB/s | 4 KiB ランダム読出 QD1 IOPS |
|---|---|---|---|
| Windows C: / 990 PRO / NTFS | 6,239.88 | 6,007.38 | 19,880 |
| Windows F: / USB NVMe / exFAT | 958.38 | 951.16 | 9,438 |
| WSL ext4 / C: 上の VHDX | 2,733.22 | 5,184.90 | 13,109 |

1 GiB の新規一時ファイル、8 MiB ブロック、同期 QD1、書き込み / 読み出し各 3 回。
専用のウォームアップはなく、最初の試行も含む。
ランダム読み出しは 4 KiB × 2,048 回を 3 試行。書き込み総量は各場所 3 GiB。
Windows は `NO_BUFFERING | WRITE_THROUGH` と aligned buffer、WSL は `O_DIRECT | O_DSYNC` を使い、書き込み後に flush した。
OS のデータキャッシュを避けているが、SSD のコントローラー / SLC キャッシュは影響する。
短い測定のため、キャッシュを使い切った後の持続速度や高 QD のピーク性能は未測定。

測定用ファイルは排他的に新規作成し、代表部分の内容検査後に削除した。既存ファイルは使っていない。
Windows の制約は [File buffering](https://learn.microsoft.com/en-us/windows/win32/fileio/file-buffering) を参照。
WSL の書き込みには VHDX と ext4、Windows では NTFS / exFAT と別の API が関わるため、単純な仮想化倍率ではない。

## 小ファイルとファイル情報取得

| 場所 | 作成 files/s（1 試行） | warm stat files/s（5 試行中央値） |
|---|---|---|
| Windows C: / NTFS | 4,424 | 28,670 |
| WSL / ext4 | 26,424 | 1,601,076 |
| WSL / /mnt/c / DrvFs | 455 | 975 |

1 KiB × 200 ファイルを新規の一時ディレクトリへ作成。作成は 1 試行で fsync なし。
続けて `Path.stat()` を繰り返し、全体のファイルサイズ合計を検査した。ファイルと一時ディレクトリは削除済み。
stat はキャッシュが温まった状態で、Python のループ時間も含む。cold cache の測定ではない。

今回の小ファイル操作では WSL の ext4 が `/mnt/c` より速かった。
Linux の Git / ビルド用ファイルを現在の `/home/kazumasa/projects` に置く運用を続ける根拠になる。
すべての I/O がこの倍率で速くなるという意味ではない。

## 通信

| 測定先 / 処理 | 中央値 | 条件 |
|---|---|---|
| 既定ゲートウェイ | 0 ms | 0 / 5 件損失 |
| Cloudflare 1.1.1.1 | 1 ms | 0 / 5 件損失 |
| Google 8.8.8.8 | 1 ms | 0 / 5 件損失 |
| Cloudflare HTTPS 下り | 465.8 Mbps | 10 MB × 3、範囲 437.0–522.7 Mbps |
| HTTPS 最初の応答（TTFB） | 55.64 ms | DNS / 接続 / TLS / サーバー待ちを含む |

有線 NIC のリンク報告値は 1 Gbps。Wi-Fi は Disconnected。
ping は各 5 件、2 秒のタイムアウト、1 ms 単位。表示値 0 ms は遅延ゼロを意味しない。
HTTPS は curl で 10,000,000 bytes を 3 回ダウンロードし、HTTP 200 と受信バイト数を検査。
速度は接続 / 最初の応答待ちを含む `curl speed_download` の値。
短時間の特定サーバーへの測定なので、回線や LAN の最大性能、上り速度、長時間の安定性は確定できない。
プライベートなゲートウェイ IP は保存していない。

## Windows / WSL の呼び出し

| 処理 | 中央値 |
|---|---|
| Windows cmd /c exit 0 | 9.48 ms |
| Windows → WSL /bin/true | 70.33 ms |

PowerShell からの呼び出しを Stopwatch で測定。各 2 回のウォームアップ後、5 回測定。
WSL は既に動作した状態で、`wsl.exe -d Ubuntu --cd /tmp --exec /bin/true` を呼び出した。
Windows の cmd は Windows の一時フォルダーを作業ディレクトリにした。
Windows / WSL の境界を毎回またぐ小さなコマンドの費用を含む。PC 起動や WSL の cold boot 時間ではない。

## 今後の比較で使うポイント

- メモリは 4800 MT/s のまま。XMP を試す場合は同じコピー測定と実際の処理時間を再測定する。
- PyTorch の CUDA runtime 12.8 で RTX 5080 の演算と転送が動作した。システムの nvcc 12.0 との差だけで障害と断定しない。
- Linux の作業ファイルは WSL ext4 に置き、短いコマンドは WSL 内でまとめて実行する。
- CPU 最大並列の Windows / WSL 比較はソフトウェアと割当 CPU 数が違う。原因を調べる際は条件を揃える。

## 未測定

Ollama のローカル API が応答しなかったため、LLM の tokens/s は未測定。
モデルのダウンロードやサーバーの起動はしていない。
3D / ゲーム、アプリの実務処理時間、モニター / 入力の遅延、長時間の発熱、cold boot、上り通信、耐久性も未測定。
この短時間の測定から、これらの性能や安定性を推測で埋めない。

## 生データと再測定

[Python 測定スクリプト](pc-performance-benchmark.py) と [Windows 通信 / 呼び出しスクリプト](pc-performance-windows.ps1)。
依存は既存の NumPy / threadpoolctl、遅延測定に Numba、GPU 測定に PyTorch を利用した。
JSON は各試行、環境、実行時刻、スクリプトの SHA-256、一時ファイルの削除結果を保持する。
ローカルアカウント、PC 名、シリアル番号、プライベート IP、個人ファイルの内容は保存していない。

- [windows-c-storage.json](pc-performance-results/2026-10-03/windows-c-storage.json)
- [windows-cpu.json](pc-performance-results/2026-10-03/windows-cpu.json)
- [windows-f-storage.json](pc-performance-results/2026-10-03/windows-f-storage.json)
- [windows-filesystem.json](pc-performance-results/2026-10-03/windows-filesystem.json)
- [windows-memory.json](pc-performance-results/2026-10-03/windows-memory.json)
- [windows-network-startup.json](pc-performance-results/2026-10-03/windows-network-startup.json)
- [wsl-cpu.json](pc-performance-results/2026-10-03/wsl-cpu.json)
- [wsl-drvfs-filesystem.json](pc-performance-results/2026-10-03/wsl-drvfs-filesystem.json)
- [wsl-ext4-filesystem.json](pc-performance-results/2026-10-03/wsl-ext4-filesystem.json)
- [wsl-gpu.json](pc-performance-results/2026-10-03/wsl-gpu.json)
- [wsl-memory.json](pc-performance-results/2026-10-03/wsl-memory.json)
- [wsl-storage.json](pc-performance-results/2026-10-03/wsl-storage.json)

以下は再測定の例。今回の JSON を上書きせず、一時フォルダーへ別名で保存する。
負荷が重ならないように順番に実行する。

```bash
# Ubuntu WSL 内。uv はリポジトリのルートから実行する。
cd /home/kazumasa/projects
uv run --no-sync python docs/knowledge/pc-performance-benchmark.py cpu --threads 20 --label WSL --output /tmp/pc-cpu-repeat.json
uv run --no-sync python docs/knowledge/pc-performance-benchmark.py gpu --label WSL-CUDA --output /tmp/pc-gpu-repeat.json
```

```powershell
# Windows PowerShell 7。Windows Python と WSL のパスを混ぜない。
$repo = '\\wsl.localhost\Ubuntu\home\kazumasa\projects'
& "$env:USERPROFILE\anaconda3\python.exe" "$repo\docs\knowledge\pc-performance-benchmark.py" memory --threads 24 --label Windows --output "$env:TEMP\pc-memory-repeat.json"
& pwsh -NoProfile -ExecutionPolicy Bypass -File "$repo\docs\knowledge\pc-performance-windows.ps1" -OutputPath "$env:TEMP\pc-network-repeat.json"
```

`ExecutionPolicy Bypass` はこの子プロセスだけに適用し、永続設定は変更しない。
Python スクリプトの項目は `cpu` / `memory` / `gpu` / `storage` / `filesystem`。
保存先の親フォルダーは事前に存在させる。ストレージ / 小ファイル測定の `--directory` は既存の一時フォルダーを指定する。
両者は新しい測定用ファイルだけを作成・削除するが、`storage` は指定場所に約 1 GiB の空きと合計 3 GiB の書き込みが必要。
結果を比較する際は電源プラン、背景負荷、スレッド数、ライブラリー、ファイルシステム、データサイズを揃える。
