---
title: WSL Ubuntu の仮想ディスクを圧縮して 232.2 GiB 回収した記録
created: 2026-09-16
updated: 2026-09-16
tags: [dev, recipe]
status: draft
sources: [session]
sensitivity: normal
public: false
---

# WSL Ubuntu の仮想ディスクを圧縮した記録

## 何をしたか

Ubuntu の仮想ディスク `ext4.vhdx` に残っていた未使用領域を整理し、Windows 側のディスク領域を回収した。今回、新たにユーザーファイルを削除する操作はしていない。

WSL 2 の Ubuntu は、Linux のファイルシステムを Windows 上の VHDX ファイルに保存している。Linux 内でファイルを削除しても、その空き領域が Windows 側にすぐ返るとは限らず、VHDX が大きいまま残ることがある。

今回の流れは **TRIM → WSL 停止 → DiskPart による圧縮 → 起動確認**。

- `fstrim`：Linux の未使用ブロックを下位のストレージに通知する。
- `wsl --shutdown`：ディスクを操作できるように WSL 全体を停止する。これだけで縮小が完了するわけではない。
- `compact vdisk`：動的仮想ディスクの不要な割り当てを整理して、VHDX の物理サイズを減らす。ZIP 化や Ubuntu の容量上限の変更ではない。

## 実測結果

2026-09-16、WSL 2.7.13.0、Ubuntu で実施。単位は GiB（1 GiB = 1,073,741,824 bytes）。

| 項目 | 結果 |
|---|---:|
| 圧縮前の VHDX | 590.5 GiB（634,057,129,984 bytes） |
| 圧縮後の VHDX | 358.3 GiB（384,762,380,288 bytes） |
| VHDX の削減量 | **232.2 GiB** |
| 作業後の C: 空き容量 | 約409.1 GiB |
| Ubuntu 内の使用量 | 約348 GiB |

C: の空き容量は他のアプリやファイルの変化にも影響されるため、この作業による削減量は VHDX の前後差で記録した。

対象は Ubuntu の次のファイルだけ。docker-desktop と NVIDIA-Workbench の VHDX は圧縮していない。

```text
C:\Users\Kazumasa\AppData\Local\wsl\{36d4fb1b-1a86-4a64-8019-47ed5b019263}\ext4.vhdx
```

## スパース化を使わなかった理由

先に実行された `wsl --manage Ubuntu --set-sparse true` は、データ破損の可能性を理由に拒否された（`Wsl/Service/E_INVALIDARG`）。今回は `--allow-unsafe` で強制せず、手動の圧縮を選んだ。圧縮後も VHDX に SparseFile 属性は付いていない。

「スパース化」と「ファイルの長さが縮むこと」は同じではない。スパースファイルでは、PowerShell の `.Length` が変わらなくても実際の割り当て量が減ることがある。実使用量はファイルのプロパティの「ディスク上のサイズ」やドライブの空き容量でも確認する。

## 次回の手順

重要データのバックアップを確保する。WSL 内の作業を保存し、テスト・エージェント処理などの終了を待つ。WSL に接続した VS Code、Ubuntu のターミナル、Docker Desktop など、WSL を起動し直すアプリを閉じる。

以下は Windows の管理者 PowerShell で実行する。再インストールやディストリビューション移動後は、上の VHDX パスが今も正しいか確認する。

```powershell
# 実行前の C: 空き容量（GiB）を記録
[math]::Round((Get-PSDrive C).Free / 1GB, 2)

# Ubuntu の未使用領域を通知
wsl -d Ubuntu -u root -- fstrim -v /
```

TRIM が成功したことを確認してから続ける。

```powershell
wsl --shutdown
wsl --list --verbose
```

停止を確認し、以降は圧縮完了まで WSL を起動しない。

```powershell
diskpart
```

`DISKPART>` 内で以下を一行ずつ実行する。対象ファイルの選択が成功したことを確認してから圧縮する。

```text
select vdisk file="C:\Users\Kazumasa\AppData\Local\wsl\{36d4fb1b-1a86-4a64-8019-47ed5b019263}\ext4.vhdx"
compact vdisk
exit
```

「仮想ディスク ファイルは正常に圧縮されました」を確認する。対象が使用中などのエラーになったら、原因を確認してから再試行する。

PowerShell に戻って容量と Ubuntu の状態を確認する。

```powershell
(Get-Item -LiteralPath 'C:\Users\Kazumasa\AppData\Local\wsl\{36d4fb1b-1a86-4a64-8019-47ed5b019263}\ext4.vhdx').Length / 1GB
[math]::Round((Get-PSDrive C).Free / 1GB, 2)
wsl -d Ubuntu -- df -h /
wsl -d Ubuntu -- findmnt -n -o TARGET,FSTYPE,OPTIONS /
```

## 今回つまずいた点と検証範囲

- 最初の試行では、停止直後に別のテスト処理が Ubuntu を起動し直した。VHDX の排他アクセス検査で使用中と判定し、圧縮前に停止した。テストを中断せず終了を待った。
- 次の管理者プロセス起動は Windows の権限確認でキャンセルされた。「起動を要求した」だけでは圧縮の開始・完了を意味しない。
- 再試行時は VS Code の WSL 接続が残っていたため、ウィンドウとターミナルを閉じてから実行した。
- 進捗が42%付近でしばらく動かなく見えたが、ログの更新を確認して待つと進んだ。割合だけで停止と判断しない。
- 最終試行では DiskPart の成功メッセージ、終了コード0、VHDX の前後差を確認した。
- 圧縮後に Ubuntu が起動し、ルートが ext4・`rw`（読み書き可能）でマウントされ、`/home/kazumasa/projects` が存在することを確認した。全ファイルの内容検証やファイルシステム全体の整合性検査は行っていない。

## Sources

- 2026-09-16 Codex session：WSL のスパース化拒否を受け、TRIM と DiskPart で Ubuntu VHDX を圧縮。実行ログと容量計測、起動確認から蒸留した記録。
- [Microsoft Learn: compact vdisk](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/compact-vdisk)（本セッションで参照）
- [Microsoft Learn: Sparse Files](https://learn.microsoft.com/en-us/windows/win32/fileio/sparse-files)（本セッションで参照）
- [microsoft/WSL issue #13075: Sparse VHD support is currently disabled](https://github.com/microsoft/WSL/issues/13075)（同じエラーの報告。将来の WSL バージョンの挙動を保証するものではない）
