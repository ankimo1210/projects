# Windows の GPU 応答停止と画面崩れ

初回確認: 2026-10-28、10:46–10:55 JST。対応更新: 同日 12:32 JST。

**エクスプローラーの画面崩れと同じ時間帯に、NVIDIA GPU の応答タイムアウトを確認した。**
GPU 本体の故障か、ドライバーやアプリとの組み合わせによる問題かは未確定。
ドライバー 621.01 は 10-25 に入れたばかりで、この版の動画再生中の黒画面とフリーズを
NVIDIA が認めて調査中と報じられている（後述）。
Windows 再起動後にも再発したため、12:21 JST に表示ドライバーを 617.42 へ切り戻した。
音声ドライバーの復元に伴う Windows 再起動と、その後の最終確認が残っている。
写真バックアップのエラー調査は別件として未着手。

## 現在の対応状況

**表示ドライバー 617.42 の実反映と WSL の CUDA 計算成功を確認済み。Windows 再起動待ち。**

- 621.01 のまま Windows を再起動した後、11:47:21 JST に `nvlddmkm` 153、
  11:47:30 / 11:47:46 JST に同一障害の `LiveKernelEvent 141` が再発した。
- [NVIDIA フォーラムの一次報告](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/591981/geforce-grd-62101-feedback-thread-released-102126/3630822/)
  にも、RTX 5080・Windows 26300.9711 での同形の障害と、617.42 への切戻しによる改善報告がある。
  621.01 の不具合が有力だが、この PC での因果関係と長期安定性はまだ確定していない。

### 実施した変更

1. [NVIDIA 公式の 617.42 WHQL パッケージ](https://www.nvidia.com/en-us/drivers/details/280103/)を取得。
   配布 EXE と展開後のインストーラーの NVIDIA 署名、ドライバーカタログの署名、
   RTX 5080 の対応を確認した。
2. 使用中の 621.01 の表示ドライバーを `pnputil /export-driver` で退避し、
   NVIDIA プロファイル 3 ファイルも退避した。
3. 通常の NVIDIA インストーラーは、付属音声ドライバーの処理でアクセス拒否となり終了した。
   この時点では表示ドライバーは 621.01 のままだった。保護ファイルの所有権や ACL は変更していない。
4. [Windows 標準のドライバー更新 API](https://learn.microsoft.com/en-us/windows/win32/api/newdev/nf-newdev-updatedriverforplugandplaydevicesw)
   で、検証済みの表示用 INF を対象 GPU に適用した。
   古い版への切戻しを指定し、署名検証を無効にする操作は行っていない。
   12:21:35 JST に成功し、32.0.16.1742（617.42）が選択された。
5. 最初のインストーラーで変更された NVIDIA HD Audio の登録を、元の署名済み 1.4.6.6 で復元した。
   `pnputil /add-driver /install` は成功し、終了コード 3010（Windows 再起動が必要）を返した。
   `NVHDA` は Running / Manual に戻り、NVIDIA High Definition Audio、Realtek USB Audio、
   NVIDIA Virtual Audio Device はすべて状態 OK・問題コード 0。

Intel Graphics の版は 32.0.101.9150 のまま。表示モードは 5120 × 2160・120 Hz を維持。
クリーンインストール指定や、HAGS・MPO・TDR のレジストリ変更は行っていない。
退避データ、配布パッケージ、操作結果の私有 JSON とログは、Windows のダウンロードフォルダー内の
当日付 `GpuRepair-*` フォルダーに保管し、リポジトリには入れない。

### 再起動前の検証

- `nvidia-smi` でも実際に読み込まれた版が **617.42** であることを確認。
  Windows の GPU 状態と問題コードは OK / 0。
- 12:27 JST、既存の WSL 環境で PyTorch 2.11.0+cu128 / CUDA 12.8 を使い、
  GPU 上の 256 × 256 行列積と結果の一致を確認した。
- 12:32:34 JST 時点で、切替後 **11 分間**の新しい `nvlddmkm` と `LiveKernelEvent` はともに 0 件。
  GPU は 44℃・使用率 0%。この短時間の観測で恒久解決とは断定しない。
- エクスプローラーと Citrix の再起動後の目視確認は未完了。

### 次の確認

未保存の作業を保存して Windows を再起動し、617.42 の維持、音声デバイス、WSL 起動・CUDA、
エクスプローラーと Citrix の描画、および `nvlddmkm` 153 / `LiveKernelEvent 141` の再発を確認する。
Windows の再起動は、この更新時点では実行していない。

## 症状とログ

- 添付画像では、エクスプローラーの一覧背景が黒く抜け、白い表示領域の境界が崩れていた。
- ユーザーから、Citrix Workspace の画面もフリーズしたとの申告があった。
- Application ログの Windows Error Reporting に、異なる障害レポートが 3 件あった。
  - 10:40:15 / 10:40:32: `LiveKernelEvent 141`。10:39 の WATCHDOG ダンプを参照。
  - 10:42:28 / 10:42:44: `LiveKernelEvent 141`。10:42 の WATCHDOG ダンプを参照。
  - 11:47:30 / 11:47:46: `LiveKernelEvent 141`。Windows 再起動後、11:47 の WATCHDOG ダンプを参照。
  - 各組は同一レポートのキュー投入と集計の記録で、計 6 回の障害とは数えない。
  - 障害バケットは `LKD_0x141_Tdr:6_IMAGE_nvlddmkm.sys_Blackwell`。
- System ログには、10:42:22 に `nvlddmkm` のイベント ID 153 が 3 件あり、
  `Error occurred on GPUID: 200` と記録されていた。

`0x141` は描画エンジンが所定時間内に応答しなかったことを示す。
画像の崩れは GPU 停止と整合するが、Citrix の停止との因果関係は確定していない。
参照: [Microsoft の 0x141 の説明](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/bug-check-0x141---video-engine-timeout-detected)。

## 初回調査時の構成と状態

| 項目 | 観測値 |
|---|---|
| Windows | Windows 11 Home 26H2、26300.9711 |
| 最終起動 | 2026-10-25 11:17 JST |
| GPU | NVIDIA GeForce RTX 5080、ドライバー 621.01（32.0.16.2101） |
| 内蔵 GPU | Intel Graphics、ドライバー 32.0.101.9150 |
| 表示モード | 5120 × 2160、120 Hz |
| Citrix Workspace | 2603 x64、26.3.20.31 |
| GPU の観測値 | 約 41.4℃、使用率 1%、メモリー 2,184 / 16,303 MiB |
| RAM | 63.27 GiB 中、空き 30.84 GiB |
| C: の空き | 273.51 GiB |

エクスプローラーとデスクトップ描画プロセス `dwm` は応答中だった。
直近 7 日の System ログでは WHEA と Resource Exhaustion のイベントは見つからなかった。
確認時点で過熱やメモリー不足の兆候はなかったが、障害発生時の状態を示す計測ではない。
以前の [GPU 温度測定](2026-10-03-gpu-thermal.md) は別日の短時間測定で、今回の原因を除外する証拠にはしない。

## ドライバーの導入時期と既知の不具合

10:47–10:55 JST に WSL から追加で確認した。

- 621.01 は 2026-10-25 11:07 JST に入った（System ログの `Microsoft-Windows-UserPnp` 20003）。
  NVIDIA App 11.0.9.565 も同じ日に入り、11:17 の最終起動はこの直後にあたる。
  その前のドライバーは 2026-10-11 17:36 JST に入っていた。
- 過去 30 日で、`nvlddmkm`・`Display` と `LiveKernelEvent 141 / 117` の記録は今回の 2 回だけだった。
  10:43–10:53 JST に再発はなかった。
- 過去 30 日の Windows Update は、10-03 の 26H2、10-16 のセキュリティ更新 KB5127648（26300.9711）、
  .NET・PowerShell・Store アプリ・Defender の定義で、ディスプレイ ドライバーは含まない。
- DriverStore に残っている NVIDIA の表示用パッケージは 621.01（`nv_dispi.inf`、32.0.16.2101）だけだった。
  旧版のパッケージがないので、デバイス マネージャーの「ドライバーを元に戻す」は使えない見込み。

[PC Games Hardware の記事](https://www.pcgameshardware.de/Grafikkarten-Grafikkarte-97980/News/Geforce-62101-Nvidia-bestaetigt-Probleme-1557703/)（2026-10-24）によると、
621.01 では動画の再生中に映像が止まり、数秒間画面が黒くなる問題を NVIDIA が認め、調査を始めた。
報告はブラウザー（Chrome、Edge）と VLC で、RTX 5080 が多い。
利用者は `nvlddmkm` の 153 と `LiveKernelEvent 141 / 117` を挙げていて、今回の記録と同じ形である。
617.42 に戻すと直るという利用者の報告がある。修正版と時期は未発表。
記事の出典は [NVIDIA フォーラムの 621.01 フィードバック スレッド](https://www.nvidia.com/en-us/geforce/forums/game-ready-drivers/13/591981/geforce-grd-62101-feedback-thread-released-102126/) で、
NVIDIA の投稿そのものは確認していない。障害の時刻に動画を再生していたかも確認していない。

## 初回調査時の WSL 確認

- WSL から GPU（`/dev/dxg`）を開いている処理はなかった。
  `nvidia-smi` は 42℃、41 W、使用率 2% で、ハードウェアと温度による減速はなかった。
- Claude Code の端末は 220 × 90、`TERM=xterm-256color`、`LANG=C.UTF-8` で、端末の設定に異常はなかった。
- 別件として、09:15 JST に `wslhost.exe` 2.7.13.0 が「応答なし」で閉じられていた。
  WSL 本体は 10-26 09:09 JST から動き続けている。

## 初回調査時の再起動方針

再起動の前に、崩れたウィンドウを開き直すか、Win + Ctrl + Shift + B で
グラフィック ドライバーを再起動すると直ることがある。

1. Citrix を含め未保存の作業を保存し、Windows の通常の「再起動」を行う。
2. 再起動後、エクスプローラーの表示と Citrix の動作を確認する。
   再発時刻を控え、System の `nvlddmkm` と Application の `LiveKernelEvent 141` を照合する。
3. 再発する場合は NVIDIA ドライバーの既知不具合、更新・旧版への切戻しを検討する。
   戻す先は、利用者の報告で直ったとされる 617.42。旧版は DriverStore にないので、NVIDIA のサイトから入れる。
   ドライバー変更や負荷試験を今回実施したものとして扱わない。

ここまでの初回調査では設定・ドライバーを変更していなかった。
その後の再発と対応結果は、冒頭の「現在の対応状況」を参照。

## 調べ方（WSL から、読み取りのみ）

管理者権限は要らない。

- PowerShell のスクリプトを WSL 側に書き、
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(wslpath -w script.ps1)"` で実行する。
  日本語の Windows では出力が化けるので、先頭で `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` にする。
- 応答停止の記録は、System ログの出元 `nvlddmkm` と `Display`（4101）、
  Application ログの WER 1001 のうち `LiveKernelEvent` で `P1: 141` か `117` のものを見る。
- ドライバーを入れた日時は、System ログの `Microsoft-Windows-UserPnp` 20003（サービス `nvlddmkm` の追加）で分かる。
  残っている旧版は、`C:\Windows\System32\DriverStore\FileRepository` で `nvlddmkm.sys` を含むフォルダーを探す。
- パフォーマンス カウンターの名前は日本語になっているので、GPU の使用率は
  WMI の `Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine` で読む。1 回目は 0 になるので 2 回目を読む。
- プロセス別の `GPUProcessMemory` は、今回 `dwm` の値（3,876 MB）が `nvidia-smi` の GPU 全体（2,208 MiB）を
  超えていたので、合計や比較には使わない。
- WSL の処理が GPU を使っているかは、`/dev/dxg` を開いているプロセスで分かる。
  `nvidia-smi` は WSL からも温度と使用率を返すが、プロセス一覧は出ない。

## 写真バックアップの未確認事項

10:49 JST 時点で、Windows タスク `Kazumasa iCloud Photo Archive` は `Ready` で、
既知の写真アーカイブ処理は実行中ではなかった。
最終実行は **2026-10-27 20:00 JST、終了コード 30**。次回予定は 2026-10-28 20:00 JST。
これはバックアップ完了の証拠ではなく、エラーの原因と未保存分を確認する必要がある。
このエラーと GPU 停止との関連は未確認。

再開時はタスクの最新結果と実行ログを確認し、
[写真アーカイブの運用資料](photo-archive/README.md) に沿って調べる。
写真や移行元の保留ファイルの削除は、この調査では行っていない。
