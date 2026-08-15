# Windows / WSL 環境整備ハンドオフ

作成日: 2026-08-09
対象: Windows 11、WSL2 Ubuntu、CUDA、Docker Desktop、主要Windowsアプリ

## 結論

環境は概ね正常。Docker整理、Windows開発設定、主要アプリ更新、CUDA実動検証まで完了した。

残作業はWindowsの通常再起動後に、Windows Installerの競合で失敗した以下3件を更新すること。

- Node.js `22.23.1` → `22.23.2`
- Tailscale `1.98.9` → `1.102.2`
- Visual Studio Community 2022 → `17.14.37`

SSDおよびBIOSファームウェアは、安全条件を確認するため未適用。

## 実施済み

### Docker

- 停止から約4か月経過していたコンテナを削除:
  - `local-chatgpt-orchestrator-1`
- 現在のコンテナ数: `0`
- `docker system prune --force` を実施
  - 未使用ネットワーク `local-chatgpt_default` を削除
  - タグなしイメージと未使用ビルドキャッシュを削除
  - Docker内部で `1.637 GB` を解放
- ボリューム `local-chatgpt_sqlite_data` は保持
  - サイズは約 `45 KB`
- Docker Desktopは停止済み
- Docker Desktopの自動起動は元から無効
- Docker Desktopバージョン: `4.85.0`

名前付きイメージは意図的に保持している。合計使用量は約 `52.04 GB`。

| Image | Approx. size | Note |
|---|---:|---|
| `nvcr.io/nvidia/tensorflow:25.02-tf2-py3-kazumasa` | 51.6 GB | ローカルのカスタム版。明示承認なしで削除しない |
| `nvcr.io/nvidia/tensorflow:25.02-tf2-py3` | 27.8 GB | 上記とレイヤーを共有 |
| `local-chatgpt-orchestrator:latest` | 372 MB | 再ビルド可否を確認してから削除 |
| `python:3.12-slim` | 179 MB | 再取得可能 |

イメージ削除は、ユーザーが `delete images too` と明示した場合のみ行う。カスタムイメージは再ビルド手段を確認すること。

### Windows設定

- Win32 long pathsを有効化:
  - `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled = 1`
- BitLocker / Device Encryption:
  - Cドライブは暗号化されていない
  - `VolumeStatus=0`
  - `ProtectionStatus=0`
  - `EncryptionMethod=0`
- Defender:
  - リアルタイム保護有効
  - 最終確認時の定義バージョン `1.457.75.0`
- 電源プランを「バランス」に2回設定したが、ASUS側ソフトウェアにより自動的に以下へ復帰した:
  - `GameTurbo (High Performance)`
  - GUID `8f6f89b0-7105-44e4-bac1-3b3029703232`
- ASUS Armoury Crate等のプロファイル制御が原因と考えられる。サービスを強制無効化しないこと。

### 更新成功済みアプリ

| Application | Installed version |
|---|---|
| Microsoft Teams | `26198.304.4946.9672` |
| Zoom Workplace | `7.1.5 (43453)` |
| Ollama | `0.32.6` |
| Cursor | `3.14.27` |
| CPUID ROG CPU-Z | `2.20.2` |
| AIDA64 Extreme | `8.35` |
| Unity Hub | `3.20.0` |
| Samsung Magician | `9.0.1.950` |

注意: AIDA64の旧版 `7.70` も登録に残っている。Windows Installer復旧後、不要ならアンインストールを検討する。

Anacondaは意図的に更新対象外。`2024.10-1` → `2025.12-2` は大幅更新なので、既存環境をエクスポートして別作業として扱う。

## Windows Installerのブロッカー

管理者権限での更新中、以下3件がWindows Installerエラー `1618` で失敗した。

- `OpenJS.NodeJS.22`
- `Tailscale.Tailscale`
- `Microsoft.VisualStudio.2022.Community`

確認内容:

- 孤立した `msiexec.exe` がPID `44848` として残っていた
- 作成時刻は `2026-08-09 15:48:00 JST`
- `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Installer\InProgress` は存在しなかった
- `msiserver` は `Running` だが、正常停止に応答しなかった
- 更新を間隔付きで3回再試行しても `1618` が継続した
- 安全のため `msiexec.exe` の強制終了は行っていない

CBSおよびWindows Updateの正式な再起動待ちはなかったが、`PendingFileRenameOperations` は存在する。次の安全な修復手順はWindowsの通常再起動。

## 再起動後の手順

1. Windowsの「再起動」を実行する。シャットダウンではなく再起動を使用する。
2. 管理者PowerShellでWindows Installer状態を確認する。

```powershell
Get-Process msiexec -ErrorAction SilentlyContinue
Get-Service msiserver
```

3. 以下を1件ずつ更新する。同時実行しない。

```powershell
winget upgrade --id OpenJS.NodeJS.22 --exact --silent --disable-interactivity --accept-package-agreements --accept-source-agreements
winget upgrade --id Tailscale.Tailscale --exact --silent --disable-interactivity --accept-package-agreements --accept-source-agreements
winget upgrade --id Microsoft.VisualStudio.2022.Community --exact --silent --disable-interactivity --accept-package-agreements --accept-source-agreements
```

4. 残りの更新を確認する。

```powershell
winget upgrade --accept-source-agreements
```

想定される残件はAnacondaのみ。AIDA64 `7.70` の重複登録も確認する。

5. Long paths設定を確認する。

```powershell
Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem -Name LongPathsEnabled
```

期待値: `LongPathsEnabled = 1`

## CUDA / WSL 検証結果

- GPU: `NVIDIA GeForce RTX 5080`
- Windows NVIDIA driver: `610.88`
- VRAM: `16303 MiB`
- `nvcc`: CUDA Toolkit `12.0`
- PyTorch: `2.11.0+cu128`
- PyTorch CUDA availability: `True`
- CuPy: `14.0.1`
- PyTorchとCuPyの双方でGPU上の総和計算を実行し、期待値 `523776.0` と一致
- `nvidia-smi` 正常
- WSL側の `libcuda.so.1` は `/usr/lib/wsl/lib` が優先されている

WSLにインストール済みのNVIDIAユーザーランドパッケージ:

- `libnvidia-compute-535 535.309.01-0ubuntu0.24.04.2`
- `libnvidia-compute-580 580.173.02-0ubuntu0.24.04.1`

GPU処理は正常なので、現時点でNVIDIAパッケージを追加変更しない。

Ubuntu側には以下4件のApport更新が保留されている。ユーザー合意により待機中で、緊急性はない。

- `apport`
- `apport-core-dump-handler`
- `python3-apport`
- `python3-problem-report`

## SSD / BIOS

### Samsung 990 PRO

- 現在のSSDファームウェア: `5B2QJXD7`
- Samsung公式で確認した候補: `8B2QJXD7`
- Samsung Magicianは `9.0.1.950` へ更新済み
- BitLockerは無効だが、SSDファームウェア更新前に重要データのバックアップを確認すること
- ファームウェア本体は未更新

公式: <https://semiconductor.samsung.com/consumer-storage/support/tools/>

### ASUS BIOS

- Motherboard: `ROG STRIX Z890-A GAMING WIFI`
- 現在のBIOS: `3002`
- ASUS公式ページの機械可読表示では `2302` が最新として返り、現在値より古く矛盾していた
- ダウングレード事故を避けるため未更新
- MyASUS、ASUS DriverHub、または正確な製品ページ上で `3002` より新しい安定版が明示されるまで適用しない

公式: <https://rog.asus.com/motherboards/rog-strix/rog-strix-z890-a-gaming-wifi/helpdesk_bios/>

## 残存リスク

- Windows再起動前はWindows Installerの孤立状態が残っている可能性がある
- Dockerの名前付きイメージ約52GBは保持中
- Docker内部の空き容量が増えても、Windows上のVHDXファイルサイズは直ちに縮小しない場合がある
- SSDファームウェア更新にはバックアップと更新中の電源安定性が必要
- BIOS情報に公式ページとの不整合があるため、自動更新やダウングレードを行わない
- GameTurboはASUSソフトウェアにより再適用されるため、変更するならArmoury Crateのプロファイル側から行う

## 作業ファイル

管理者更新用に作成した一時PowerShellスクリプトとログは、確認後すべて削除済み。このハンドオフ以外のリポジトリファイルは変更していない。
